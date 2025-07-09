from typing import Dict, List, Any
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from src.find_recommendations import OutfitRecommendationAgent
from deepmerge import always_merger

CONFIDENCE_THRESHOLD = 0.7


class AttributeValue(BaseModel):
    """Represents a single attribute value with its confidence score."""

    value: str
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score between 0 and 1"
    )


class ProductAttributes(BaseModel):
    """Contains all product attributes with their values and confidence scores."""

    category: List[AttributeValue]
    available_sizes: List[AttributeValue]
    fit: List[AttributeValue]
    fabric: List[AttributeValue]
    sleeve_length: List[AttributeValue]
    color_or_print: List[AttributeValue]
    occasion: List[AttributeValue]
    neckline: List[AttributeValue]
    length: List[AttributeValue]
    pant_type: List[AttributeValue]
    budget_min: List[AttributeValue]
    budget_max: List[AttributeValue]


class AttributeExtraction(BaseModel):
    """Main model containing product attributes and follow-up questions."""

    attributes: ProductAttributes = Field(
        description="Extracted clothing attributes with confidence scores"
    )
    follow_ups: List[str] = Field(
        description="Follow-up questions for low-confidence attributes"
    )


class VibeShoppingAgent:
    def __init__(self):
        """Initialize the LLM-based vibe shopping agent"""
        self.conversation = []
        self.attributes: dict[str, list[dict[str, Any]]] = {}
        self.follow_up_count = 0
        self.max_follow_ups = 2
        self.recommendation_agent = OutfitRecommendationAgent()

        self.llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.7)

        # Initialize parsers
        self.attribute_parser = JsonOutputParser(pydantic_object=AttributeExtraction)

        # System prompts
        self.attribute_extraction_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content="""You are a fashion item conversion agent. Your job is to take a vibe description and convert it into a structured JSON format with the following fields:

## Available Choices (use these when possible):

**category**: top, dress, skirt, pants

**available_sizes**: XS,S,M,L,XL (or subsets like XS,S,M or S,M,L,XL) - ONLY specify if explicitly mentioned by user, otherwise leave empty with confidence 0.0

**fit**: Relaxed, Stretch to fit, Body hugging, Tailored, Flowy, Bodycon, Oversized, Sleek and straight, Slim

**fabric**: Linen, Silk, Cotton, Rayon, Satin, Modal jersey, Crepe, Tencel, Chambray, Velvet, Silk chiffon, Bamboo jersey, Linen blend, Ribbed knit, Tweed, Organza overlay, Sequined velvet, Cotton-blend, Crushed velvet, Tulle, Denim, Wool-blend, Scuba knit, Linen-blend, Polyester georgette, Cotton twill, Ribbed jersey, Poly-crepe, Viscose voile, Vegan leather, Lamé, Polyester twill, Stretch denim, Tencel-blend, Chiffon, Cotton poplin, Cotton gauze, Lace overlay, Tencel twill, Sequined mesh, Viscose

**sleeve_length**: Short Flutter Sleeves, Cropped, Long sleeves with button cuffs, Sleeveless, Full sleeves, Short sleeves, Quarter sleeves, Straps, Long sleeves, Spaghetti straps, Short flutter sleeves, Tube, Balloon sleeves, Halter, Bishop sleeves, One-shoulder, Cap sleeves, Cropped long sleeves, Bell sleeves, Short puff sleeves

**color_or_print**: Pastel yellow, Deep blue, Floral print, Red, Off-white, Pastel pink, Aqua blue, Green floral, Charcoal, Pastel coral, Dusty rose, Seafoam green, Multicolor mosaic print, Pastel floral, Storm grey, Cobalt blue, Blush pink, Sunflower yellow, Aqua wave print, Black iridescent, Orchid purple, Amber gold, Watercolor petals, Stone/black stripe, Sage green, Ruby red, Soft teal, Charcoal marled, Lavender, Ombre sunset, Coral stripe, Jet black, Olive green, Mustard yellow, Silver metallic, Teal abstract print, Lavender haze, Warm taupe, Black polka dot, Midnight navy sequin, Sunshine yellow, Charcoal pinstripe, Plum purple, Mid-wash indigo, Emerald green, Mustard windowpane check, Sand beige, Ruby red micro–dot, Terracotta, Heather quartz, Goldenrod yellow, Deep-wash indigo, Sapphire blue, Peony watercolor print, Slate grey, Emerald green grid check, Bronze metallic, Classic indigo, Stone beige, Sand taupe, Graphite grey, Platinum grey

**occasion**: Party, Vacation, Everyday, Evening, Work, Vocation

**neckline**: Sweetheart, Square neck, V neck, Boat neck, Tubetop, Halter, Cowl neck, One-shoulder, Collar, Illusion bateau, Round neck, Polo collar

**length**: Mini, Short, Midi, Maxi

**pant_type**: Wide-legged, Ankle length, Flared, Wide hem, Straight ankle, Mid-rise, Low-rise

**budget_min**: Minimum price range (e.g., 10, 20, 30, 50, 100)

**budget_max**: Maximum price range (e.g., 50, 100, 150, 200, 300)

## Instructions:

1. **Think step by step** about the vibe provided. Consider the mood, style, occasion, and any specific details mentioned. Prioritize occasion and category, if they are not clearly mentioned, prioritize asking for them in the follow-up questions.

2. **Provide multiple suggestions** for each attribute when appropriate. Each attribute should be an array of options with confidence scores.

3. **Match to available choices** when possible. If a choice isn't available, create something appropriate that captures the sentiment or uses words from the prompt.

4. **Fill in logical defaults** for missing information based on the vibe and other selected attributes.

5. **Assign confidence scores** (0.0 to 1.0) to each attribute based on how certain you are about the choice given the vibe.

6. **Generate follow-up questions** for attributes with confidence < 0.5 to gather more specific information. Keep the follow-up questions short, targeted and not too specific. Try for follow-ups that answer multiple attributes at once yet seem like a single meaningful question.

7. **Size Handling**: NEVER assume all sizes are available. Only specify sizes if explicitly mentioned by the user. If no sizes are mentioned, leave available_sizes empty with confidence 0.0 and ask about it in follow-ups.
    - If the user mentions a size, make sure to include it in the available_sizes array.
    - Look for phrases like i'm skinny or tall or petite or plus size or small or medium and so on.

8. **Response format**: Return a JSON object with two main sections:
   - `attributes`: All fields with their values and confidence scores as arrays
   - `follow_ups`: Precise questions to improve low-confidence attributes

9. **Budget Range Handling**: 
   - CRITICAL: Always look for budget-related phrases and extract numeric values
   - Extract budget information from phrases like:
     * "under $50" → budget_max: 50
     * "between $30 and $100" → budget_min: 30, budget_max: 100
     * "from $30 to $100" → budget_min: 30, budget_max: 100
     * "$30-$100" → budget_min: 30, budget_max: 100
     * "around $75" → budget_max: 75
     * "budget-friendly" → budget_max: 50
     * "affordable" → budget_max: 60
     * "luxury" → budget_min: 200
     * "expensive" → budget_min: 150
   - When a range is specified (e.g., "between X and Y"), ALWAYS extract BOTH values
   - If only one budget value is mentioned, use it as budget_max
   - If no budget is mentioned, leave budget_min and budget_max empty with confidence 0.0
   - Budget values should be numeric without dollar signs (e.g., 50, 100, 200)

10. **Existing User Attributes:** If the user has already provided attributes, its upto you to decide if you should use them or ask for them again. If a user mentions an attribute that is not in the Existing User Attributes, feel free to add it to the attributes.

11. **Previous User Inputs:** Use the previous user inputs to form an understanding of the user's preferences and needs. Ensure you don't ask the same question again.

12. If you are confident about the attributes, you can skip the follow-up questions.

## Previous User Inputs:

{previous_questions}

## Existing User Attributes:

{current_attributes}

## Format instructions:

{format_instructions}

## Example Input/Output:

**Input**: "Cozy coffee shop vibes for a weekend brunch between $30 and $75"
**Output**: 
```json
{
  "attributes": {
    "category": [{"value": "top", "confidence": 0.8}, {"value": "dress", "confidence": 0.6}],
    "available_sizes": [{"value": "", "confidence": 0.0}],
    "fit": [{"value": "Relaxed", "confidence": 0.9}, {"value": "Flowy", "confidence": 0.7}],
    "fabric": [{"value": "Cotton", "confidence": 0.7}, {"value": "Modal jersey", "confidence": 0.6}],
    "sleeve_length": [{"value": "Long sleeves", "confidence": 0.6}, {"value": "Short sleeves", "confidence": 0.5}],
    "color_or_print": [{"value": "Warm taupe", "confidence": 0.5}, {"value": "Charcoal", "confidence": 0.4}],
    "occasion": [{"value": "Everyday", "confidence": 0.8}],
    "neckline": [{"value": "Round neck", "confidence": 0.6}, {"value": "V neck", "confidence": 0.5}],
    "length": [{"value": "", "confidence": 0.0}],
    "pant_type": [{"value": "", "confidence": 0.0}],
    "budget_min": [{"value": "30", "confidence": 0.9}],
    "budget_max": [{"value": "75", "confidence": 0.9}]
  },
  "follow_ups": [
    “Any must-haves like sleeveless, budget or size to keep in mind?”,
    "Any preferred colors or prints? Neutral tones, earth tones, or something more vibrant?",
    "What neckline style appeals to you - round neck, V neck, or something else?"
  ]
}
"""
                ),
                HumanMessage(
                    content="Convert the following vibe into JSON format: {user_input}"
                ),
            ]
        )

    def process_query(self, user_input: str) -> None:
        """Main method to process user input and return appropriate response"""
        self.conversation.append({"role": "user", "content": user_input})

        attributes_new, follow_ups = self._extract_attributes_llm(user_input)
        # self.attributes = always_merger.merge(self.attributes, attributes_new)
        self.attributes = attributes_new

        if follow_ups and self.follow_up_count < self.max_follow_ups:
            self.follow_up_count += 1
            response = f"Great! I found some lovely options for '{user_input}'. "
            response += f"To help me find the perfect pieces for you, {follow_ups[0]}"

            self.conversation.append({"role": "assistant", "content": response})
        else:
            response = self._generate_recommendations()
            self.conversation.append({"role": "assistant", "content": response})

    def _extract_attributes_llm(self, user_input: str) -> Dict[str, Any]:
        """Extract attributes from user input using LLM"""
        try:
            previous_questions = [
                message["content"]
                for message in self.conversation
                if message["role"] == "user"
            ]

            chain = self.attribute_extraction_prompt | self.llm | self.attribute_parser
            result: dict = chain.invoke(
                {
                    "user_input": user_input,
                    "format_instructions": self.attribute_parser.get_format_instructions(),
                    "previous_questions": json.dumps(previous_questions),
                    "current_attributes": json.dumps(self.attributes),
                }
            )

            # Extract attributes from the new format
            raw_attributes = result.get("attributes", {})
            follow_ups = result.get("follow_ups", [])

            print(f"📝 Follow-up questions available: {follow_ups}")
            print(
                f"🔍 Extracted attributes for '{user_input}': {json.dumps(raw_attributes, indent=2)}"
            )

            # Keep the full format with confidence scores for better attribute handling
            extracted_attrs = {}
            for key, attr_list in raw_attributes.items():
                if not isinstance(attr_list, list):
                    continue

                if key not in extracted_attrs:
                    extracted_attrs[key] = []

                for attr_item in attr_list:
                    if not isinstance(attr_item, dict):
                        continue

                    value = attr_item.get("value", "")
                    confidence = attr_item.get("confidence", 0.0)

                    # Only include attributes with values and decent confidence
                    if not value or confidence < CONFIDENCE_THRESHOLD:
                        continue

                    # Preserve the full AttributeValue structure
                    extracted_attrs[key].append(
                        {"value": value, "confidence": confidence}
                    )

            print(
                f"🔍 Extracted attributes for '{user_input}': {json.dumps(extracted_attrs, indent=2)}"
            )

            return extracted_attrs, follow_ups
        except Exception as e:
            print(f"Error extracting attributes: {e}")
            return {}, []

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

            # if len(matches) > 3:
            #     response += "Would you like to see more options?"

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


if __name__ == "__main__":
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
