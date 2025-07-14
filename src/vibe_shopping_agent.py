from typing import Dict, List
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from src.find_recommendations import OutfitRecommendationAgent, RecommendationResult

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
    follow_up: str = Field(
        description="A precise question to improve low-confidence attributes"
    )


class Product(BaseModel):
    name: str = Field(description="The name of the product")
    price: str = Field(description="The price of the product")


class ProductWithJustification(BaseModel):
    product: Product = Field(description="The product details")
    justification: str = Field(description="The justification for the product")


class BatchProductsWithJustification(BaseModel):
    """Model for batch processing of product justifications"""

    products: List[ProductWithJustification] = Field(
        description="List of products with their justifications"
    )


class VibeShoppingAgent:
    def __init__(self):
        """Initialize the LLM-based vibe shopping agent"""
        self.conversation = []
        self.attributes: ProductAttributes = {}
        self.follow_up_count = 0
        self.max_follow_ups = 2
        self.recommendation_agent = OutfitRecommendationAgent()

        self.llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.7)

        # Initialize parsers
        self.attribute_parser = JsonOutputParser(pydantic_object=AttributeExtraction)
        self.justification_parser = JsonOutputParser(
            pydantic_object=BatchProductsWithJustification
        )

    def process_query(self, user_input: str) -> None:
        """Main method to process user input and return appropriate response"""
        self.conversation.append({"role": "user", "content": user_input})

        attributes_new, follow_up = self._extract_attributes_llm()
        # self.attributes = always_merger.merge(self.attributes, attributes_new)
        self.attributes = attributes_new

        if follow_up and self.follow_up_count < self.max_follow_ups:
            self.follow_up_count += 1
            response = f"Great! I found some lovely options for '{user_input}'. "
            response += f"To help me find the perfect pieces for you, {follow_up}"

            self.conversation.append({"role": "assistant", "content": response})
        else:
            response = self._generate_recommendations()
            self.conversation.append({"role": "assistant", "content": response})

    def _get_system_prompt(self) -> str:
        return """You are a fashion item conversion agent. Your job is to take a vibe description and convert it into a structured JSON format with the following fields:

## Available Choices (use these when possible):

**category**: top, dress, skirt, pants

**available_sizes**: XS,S,M,L,XL (or subsets like XS,S,M or S,M,L,XL)

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

* **Think step by step** about the vibe provided. Consider the mood, style, occasion, and any specific details mentioned.

* **Provide multiple suggestions** for each attribute when appropriate. Each attribute should be an array of options with confidence scores.

* **Match to available choices** when possible. If a choice isn't available, create something appropriate that captures the sentiment or uses words from the prompt.

* **Fill in logical defaults** for missing information based on the vibe and other selected attributes.

* **Assign confidence scores** (0.0 to 1.0) to each attribute based on how certain you are about the choice given the vibe.

* **Generate follow-up questions** for attributes with confidence < {confidence_threshold} to gather more specific information.
    - Keep the follow-up questions short, targeted and not too specific.
    - Try for follow-ups that answer multiple attributes at once yet seem like a single meaningful question.
    - If you are confident about the attributes, you can skip the follow-up questions.

* **Response format**: Return a JSON object with two main sections:
    - `attributes`: All fields with their values and confidence scores as arrays
    - `follow_up`: A precise question to improve low-confidence attributes

* **Budget Range Handling**: 
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

* **Occasion and Category:** If you don't understand the occasion and category, prioritize asking the user to elaborate the vibe in the follow-up questions

* **Size Handling**: Look for size related phrases like skinny or tall or petite or plus size or small or medium and so on to make judgements.

* **Existing System Generated Attributes:** Attributes generated by you in previous iterations are available to you.
    - Use them to improve your understanding of the user's preferences and needs.
    - Add and remove attributes as per improvement in your understanding of the user's preferences and needs.

## Existing System Generated Attributes:
{current_attributes}

## Format instructions:
{format_instructions}

## Example Input/Output:

**Input**: "Cozy coffee shop vibes for a weekend brunch between $30 and $75"
**Output**: 
```json
{{
    "attributes": {{
        "category": [{{"value": "top", "confidence": 0.8}}, {{"value": "dress", "confidence": 0.6}}],
        "available_sizes": [{{"value": "", "confidence": 0.0}}],
        "fit": [{{"value": "Relaxed", "confidence": 0.9}}, {{"value": "Flowy", "confidence": 0.7}}],
        "fabric": [{{"value": "Cotton", "confidence": 0.7}}, {{"value": "Modal jersey", "confidence": 0.6}}],
        "sleeve_length": [{{"value": "Long sleeves", "confidence": 0.6}}, {{"value": "Short sleeves", "confidence": 0.5}}],
        "color_or_print": [{{"value": "Warm taupe", "confidence": 0.5}}, {{"value": "Charcoal", "confidence": 0.4}}],
        "occasion": [{{"value": "Everyday", "confidence": 0.8}}],
        "neckline": [{{"value": "Round neck", "confidence": 0.6}}, {{"value": "V neck", "confidence": 0.5}}],
        "length": [{{"value": "", "confidence": 0.0}}],
        "pant_type": [{{"value": "", "confidence": 0.0}}],
        "budget_min": [{{"value": "30", "confidence": 0.9}}],
        "budget_max": [{{"value": "75", "confidence": 0.9}}]
    }},
    "follow_up": "Any must-haves like sleeveless, budget or size to keep in mind?",
}}
```
"""

    def _extract_attributes_llm(self):
        """Extract attributes from user input using LLM"""
        try:
            system_content = self._get_system_prompt().format(
                current_attributes=json.dumps(self.attributes),
                format_instructions=self.attribute_parser.get_format_instructions(),
                confidence_threshold=0.5,
            )
            messages: List[BaseMessage] = [SystemMessage(content=system_content)]

            # Add conversation history
            for msg in self.conversation:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

            # Create chain and invoke
            chain = self.llm | self.attribute_parser
            result: Dict = chain.invoke(messages)

            # Extract attributes from the new format
            raw_attributes: Dict = result.get("attributes", {})
            follow_up: str = result.get("follow_up", "")

            # Keep the full format with confidence scores for better attribute handling
            extracted_attrs = {}
            for key, attr_list in raw_attributes.items():
                if not isinstance(attr_list, List):
                    continue

                if key not in extracted_attrs:
                    extracted_attrs[key] = []

                for attr_item in attr_list:
                    if not isinstance(attr_item, Dict):
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

            return extracted_attrs, follow_up
        except Exception as e:
            print(f"Error extracting attributes: {e}")
            return {}, ""

    def _generate_recommendations(self) -> str:
        """Generate product recommendations using the recommendation agent"""
        try:
            matches = self.recommendation_agent.find_recommendations(self.attributes)

            if not matches:
                return "I couldn't find any matches for your preferences. Would you like to try a different style or adjust your requirements?"

            # Get top 3 recommendations
            top_matches = matches[:3]

            products_with_justifications = self._generate_justification_llm(top_matches)

            # Generate response with LLM-enhanced justifications
            response = "Here are my top picks for you:\n\n"
            for i, match in enumerate(products_with_justifications, 1):
                response += f"{i}. **{match.product.name}** (${match.product.price})\n {match.justification}\n\n"

            return response

        except ValueError as e:
            return str(e)
        except Exception as e:
            print(f"Error finding recommendations: {str(e)}")
            return "I encountered an error finding recommendations. Please try again."

    def _generate_justification_llm(
        self, matches: List[RecommendationResult]
    ) -> List[ProductWithJustification]:
        """Generate LLM-based justification for product recommendations"""
        results = []

        try:
            system_message = f"""You are a fashion stylist explaining why products match a customer's request.

## Instructions:

* Create a brief, enthusiastic justifications (1-2 sentences each) that highlight the key features that make each item perfect for them.
* **Conversation history**: Messages sent by the customer to build the customer's preferences.
* **Style Preferences**: Customer's style preferences.
* **Products to justify**: Products that match the customer's preferences from the catalog.
* **Think step by step** about the customer's conversation history and style preferences and how they match the products. Consider the mood, style, occasion, and any specific details mentioned.
* Focus on the matched attributes and make it personal and engaging.

## Format instructions:
{self.justification_parser.get_format_instructions()}
"""

            products_info: List[Dict] = []
            for i, match in enumerate(matches, 1):
                product_details = match.product_details
                price = product_details.get("price", "Price not available")

                product_info = {
                    "number": i,
                    "name": match.product_name,
                    "price": str(price),
                    "match_score": match.match_score,
                    "matched_attributes": match.matched_attributes,
                    "product_details": product_details,
                    "reasoning": match.reasoning,
                }
                products_info.append(product_info)

            user_message = f"""
## Conversation history:
{json.dumps([msg["content"] for msg in self.conversation if msg["role"] == "user"], indent=2)}

## Style preferences:
{json.dumps(self.attributes, indent=2)}

## Products to justify:
{json.dumps(products_info, indent=2)}

Please provide enthusiastic justifications for each product explaining why it matches the customer's preferences."""

            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_message),
            ]

            # Use the JSON parser for structured output
            chain = self.llm | self.justification_parser
            response: Dict = chain.invoke(messages)

            for match in response.get("products", []):
                results.append(ProductWithJustification(**match))

        except Exception as e:
            print(f"Error generating justifications: {e}")
            # Return fallback justifications if LLM fails
            for match in matches:
                product_details = match.product_details
                price = product_details.get("price", "Price not available")

                results.append(
                    ProductWithJustification(
                        product=Product(name=match.product_name, price=str(price)),
                        justification=f"A versatile {product_details.get('category', 'piece')} that matches your style perfectly with a {match.match_score:.2f} compatibility score.",
                    )
                )

        return results

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
