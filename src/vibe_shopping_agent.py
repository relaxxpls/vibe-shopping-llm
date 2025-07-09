from typing import Dict, List, Optional, Any
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from src.find_recommendations import OutfitRecommendationAgent
from deepmerge import always_merger


class AttributeExtraction(BaseModel):
    """Model for extracted attributes from user input"""

    attributes: Dict[str, Any] = Field(description="Extracted clothing attributes")
    confidence: float = Field(description="Confidence score 0-1")


class FollowUpDecision(BaseModel):
    """Model for follow-up decision"""

    needs_followup: bool = Field(description="Whether a follow-up question is needed")
    question: Optional[str] = Field(description="Follow-up question if needed")
    reasoning: str = Field(description="Reasoning for the decision")


class VibeShoppingAgent:
    def __init__(self):
        """Initialize the LLM-based vibe shopping agent"""
        self.conversation = []
        self.attributes = {}
        self.follow_up_count = 0
        self.max_follow_ups = 2
        self.recommendation_agent = OutfitRecommendationAgent()

        self.llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.7)

        # Initialize parsers
        self.attribute_parser = JsonOutputParser(pydantic_object=AttributeExtraction)
        self.followup_parser = JsonOutputParser(pydantic_object=FollowUpDecision)

        # System prompts
        self.attribute_extraction_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content="""You are an expert fashion stylist. Extract clothing attributes by understanding the vibe and context.

EXTRACT THESE ATTRIBUTES when mentioned or implied:
- category: "Dresses", "Tops", "Bottoms", "Outerwear", "Activewear"
- occasion: "Casual", "Business", "Evening", "Date Night", "Active", "Travel"
- fit: "Slim", "Regular", "Relaxed", "Oversized"
- fabric: "Cotton", "Linen", "Silk", "Denim", "Knit", "Chiffon"
- color: specific colors or "Neutral", "Bright", "Dark", "Pastels"
- print: "Solid", "Floral", "Geometric", "Abstract", "Animal"
- size: "XS", "S", "M", "L", "XL", etc.
- budget: "Under $50", "$50-100", "$100-200", "Over $200"
- style: "Bohemian", "Classic", "Trendy", "Minimalist", "Romantic"

KEYWORD DETECTION RULES:
1. SIZE: Look for "size", "XS", "S", "M", "L", "XL", "small", "medium", "large", "extra"
2. BUDGET: Look for "$", "dollar", "budget", "under", "over", "between", price ranges
3. OCCASION: "weekend" = "Casual", "work" = "Business", "dinner" = "Evening"
4. FABRIC: "cozy" = "Knit", "flowy" = "Chiffon", "structured" = "Cotton"

VIBE INTERPRETATION EXAMPLES:
- "Bali family vacation" → occasion: "Travel", "Casual"; fabric: "Cotton", "Linen"; fit: "Relaxed"; color: "Bright"
- "cozy weekend vibes size M under 100 dollars" → occasion: "Casual"; fabric: "Knit"; fit: "Relaxed"; size: "M"; budget: "$50-100"
- "Anniversary dinner" → occasion: "Evening", "Date Night"; style: "Romantic"; color: "Elegant"
- "Work meeting" → occasion: "Business"; fit: "Regular"; style: "Classic"

IMPORTANT: 
- ALWAYS extract size if mentioned explicitly (e.g., "size M", "large", "XL")
- ALWAYS extract budget if price/money is mentioned (e.g., "under $100", "50 dollars")
- Interpret mood/vibe words into concrete attributes
- Consider context clues (vacation → travel-friendly fabrics)
- Set confidence based on how specific the input is

You must respond with valid JSON that includes:
- attributes: Dictionary of extracted clothing attributes
- confidence: Float between 0-1 indicating confidence

{format_instructions}"""
                ),
                HumanMessage(
                    content="Extract attributes from this user input: {user_input}"
                ),
            ]
        )

        self.followup_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content="""You are a fashion stylist deciding if you need more information from the customer.

RULES:
1. Maximum 2 follow-up questions total
2. Only ask about missing key information
3. Don't ask if the information is already available in current attributes

PRIORITY ORDER (ask about the first missing item):
1. Category - if unclear whether they want dresses, tops, bottoms
2. Size - if not specified in attributes
3. Budget - if no price range mentioned

EXAMPLES:
- If missing category: "Do you prefer dresses, or tops and bottoms?"
- If missing size: "What size are you looking for?"
- If missing budget: "What's your budget range?"

WHEN NOT TO ASK:
- If current attributes already include the information
- If you already asked 2 questions
- If the user gave very specific details

You must respond with valid JSON containing:
- needs_followup: Boolean indicating if follow-up is needed
- question: String with the follow-up question (or null if not needed)
- reasoning: String explaining your decision

{format_instructions}"""
                ),
                HumanMessage(
                    content="Analyze this request and current state:\n\nUser request: {user_input}\nCurrent attributes: {current_attributes}\nFollow-up count: {followup_count}\nPrevious questions: {previous_questions}\n\nDecide if you need to ask a follow-up question."
                ),
            ]
        )

    def process_query(self, user_input: str) -> None:
        """Main method to process user input and return appropriate response"""
        self.conversation.append({"role": "user", "content": user_input})
        attributes_new = self._extract_attributes_llm(user_input)
        self.attributes = always_merger.merge(self.attributes, attributes_new)

        # Decide if follow-up is needed using LLM
        followup_decision = self._decide_followup_llm(user_input, self.attributes)

        if followup_decision.needs_followup:
            self.follow_up_count += 1

            response = f"Great! I found some lovely options for '{user_input}'. "
            response += f"To help me find the perfect pieces for you, {followup_decision.question}"

            self.conversation.append({"role": "assistant", "content": response})
            return

        response = self._generate_recommendations()
        self.conversation.append({"role": "assistant", "content": response})

    def _extract_attributes_llm(self, user_input: str) -> Dict[str, Any]:
        """Extract attributes from user input using LLM"""
        try:
            chain = self.attribute_extraction_prompt | self.llm | self.attribute_parser
            result = chain.invoke(
                {
                    "user_input": user_input,
                    "format_instructions": self.attribute_parser.get_format_instructions(),
                }
            )
            extracted_attrs = result.get("attributes", {})
            print(
                f"🔍 Extracted attributes for '{user_input}': {json.dumps(extracted_attrs, indent=2)}"
            )
            return extracted_attrs
        except Exception as e:
            print(f"Error extracting attributes: {e}")
            return {}

    def _decide_followup_llm(
        self, user_input: str, current_attributes: Dict
    ) -> FollowUpDecision:
        """Use LLM to decide if follow-up questions are needed"""
        if self.follow_up_count >= self.max_follow_ups:
            return FollowUpDecision(
                needs_followup=False, question=None, reasoning="Max follow-ups reached"
            )

        previous_questions = [
            message["content"]
            for message in self.conversation
            if message["role"] == "user"
        ]
        print(f"Previous questions: {previous_questions}")
        print(
            f"🔍 Current attributes being passed to LLM: {json.dumps(current_attributes, indent=2)}"
        )

        try:
            chain = self.followup_prompt | self.llm | self.followup_parser
            result = chain.invoke(
                {
                    "user_input": user_input,
                    "current_attributes": json.dumps(current_attributes),
                    "followup_count": self.follow_up_count,
                    "previous_questions": json.dumps(previous_questions),
                    "format_instructions": self.followup_parser.get_format_instructions(),
                }
            )
            decision = FollowUpDecision(**result)
            print(
                f"🤔 Follow-up decision: needs_followup={decision.needs_followup}, question='{decision.question}', reasoning='{decision.reasoning}'"
            )
            return decision
        except Exception as e:
            print(f"Error in follow-up decision: {e}")
            return FollowUpDecision(
                needs_followup=False, question=None, reasoning="Error in processing"
            )

    def _generate_recommendations(self) -> str:
        """Generate product recommendations using the recommendation agent"""
        try:
            matches = self.recommendation_agent.find_recommendations(self.attributes)

            if not matches:
                return "I couldn't find any matches for your preferences. Would you like to try a different style or adjust your requirements?"

            # Get top 3 recommendations
            top_matches = matches[:3]

            # Generate response with LLM-enhanced justifications
            response = "Here are my top picks for you:\n\n"

            for i, match in enumerate(top_matches, 1):
                product = match.product_details
                response += f"{i}. **{product['name']}** (${product['price']})\n"
                response += f"   {self._generate_justification_llm(product, match.matched_attributes)}\n\n"

            if len(matches) > 3:
                response += "Would you like to see more options?"

            return response

        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"I encountered an error finding recommendations: {str(e)}"

    def _generate_justification_llm(
        self, product: Dict, matched_attributes: List[str]
    ) -> str:
        """Generate LLM-based justification for product recommendations"""
        try:
            justification_prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(
                        content="""You are a fashion stylist explaining why a product matches a customer's request.
                Create a brief, enthusiastic justification (1-2 sentences) that highlights the key features that make this item perfect for them.
                Focus on the matched attributes and make it personal and engaging."""
                    ),
                    HumanMessage(
                        content="Product: {product}\nMatched attributes: {matched_attributes}\nCustomer's style preferences: {customer_attributes}"
                    ),
                ]
            )

            chain = justification_prompt | self.llm
            result = chain.invoke(
                {
                    "product": json.dumps(product),
                    "matched_attributes": ", ".join(matched_attributes),
                    "customer_attributes": json.dumps(self.attributes),
                }
            )

            return result.content.strip()

        except Exception as e:
            print(f"Error generating justification: {e}")
            return f"A versatile {product.get('category', 'piece')} that matches your style perfectly."

    def reset_conversation(self) -> None:
        """Reset the conversation state"""
        self.conversation = []
        self.attributes = {}
        self.follow_up_count = 0


# Example usage
if __name__ == "__main__":
    # Make sure to set your OpenAI API key
    # export OPENAI_API_KEY="your-api-key-here"

    agent = VibeShoppingAgent()

    print("🛍️ Welcome to your AI-powered personal styling assistant!")
    print(
        "Tell me what vibe you're going for and I'll help you find the perfect pieces.\n"
    )

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ["quit", "exit", "bye"]:
            print("Happy shopping! 👋")
            break

        if user_input.lower() == "reset":
            agent.reset_conversation()
            print("🔄 Starting fresh! What vibe are you going for?")
            continue

        try:
            response = agent.process_query(user_input)
            print(f"\nStylist: {response}\n")
        except Exception as e:
            print(f"Sorry, I encountered an error: {e}")
            print("Please try again or type 'reset' to start over.\n")
