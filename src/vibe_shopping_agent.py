import pandas as pd
import json
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class ConversationState(Enum):
    INITIAL = "initial"
    FOLLOW_UP = "follow_up"
    RECOMMENDATION = "recommendation"


@dataclass
class ProductMatch:
    product: Dict
    match_score: float
    matched_attributes: List[str]


MAX_FOLLOW_UPS = 2


class VibeShoppingAgent:
    def __init__(self, catalog_file: str = "data/Apparels_shared.xlsx"):
        self.catalog = pd.read_excel(catalog_file)
        self.state = ConversationState.INITIAL
        self.conversation_history = []
        self.inferred_attributes = {}
        self.follow_up_count = 0

        # Load vibe-to-attribute mappings
        self.vibe_mappings = self._load_vibe_mappings()

    def _load_vibe_mappings(self) -> Dict:
        """Load and parse vibe-to-attribute mappings from the text file"""
        mappings = {
            # Occasion-based vibes
            "brunch": {
                "occasion": "Casual",
                "fit": "Relaxed",
                "fabric": ["Cotton", "Linen"],
            },
            "date night": {
                "fit": "Body hugging",
                "fabric": ["Satin", "Velvet", "Silk"],
                "occasion": "Party",
            },
            "office": {
                "fabric": "Cotton poplin",
                "neckline": "Collar",
                "fit": "Tailored",
            },
            "party": {
                "fit": "Body hugging",
                "fabric": ["Satin", "Silk"],
                "occasion": "Party",
            },
            "garden party": {
                "fit": "Relaxed",
                "fabric": ["Chiffon", "Linen"],
                "color_or_print": "Pastel floral",
            },
            "vacation": {"fit": "Relaxed", "fabric": "Linen", "occasion": "Vacation"},
            "beach": {
                "fit": "Relaxed",
                "fabric": "Linen",
                "color_or_print": "Seafoam green",
            },
            # Style-based vibes
            "cute": {
                "fit": "Relaxed",
                "color_or_print": ["Pastel pink", "Pastel yellow", "Floral print"],
            },
            "elegant": {
                "fit": "Tailored",
                "fabric": ["Silk", "Satin"],
                "color_or_print": "Off-white",
            },
            "casual": {"fit": "Relaxed", "fabric": ["Cotton", "Modal jersey"]},
            "comfy": {"fit": "Relaxed", "fabric": "Modal jersey"},
            "flowy": {"fit": "Relaxed"},
            "bodycon": {"fit": "Body hugging"},
            "retro": {
                "fit": "Body hugging",
                "fabric": "Stretch crepe",
                "color_or_print": "Geometric print",
            },
            # Color/print vibes
            "pastel": {"color_or_print": ["Pastel pink", "Pastel yellow"]},
            "floral": {"color_or_print": ["Floral print", "Green floral"]},
            "bold": {"color_or_print": ["Ruby red", "Cobalt blue", "Red"]},
            "neutral": {
                "color_or_print": ["Sand beige", "Off-white", "White", "Charcoal"]
            },
            # Fabric vibes
            "breathable": {"fabric": "Linen"},
            "luxurious": {"fabric": ["Velvet", "Silk", "Satin"]},
            "summer": {"fabric": "Linen"},
            "metallic": {"fabric": "Lamé"},
        }
        return mappings

    def process_query(self, user_input: str) -> str:
        """Main method to process user input and return appropriate response"""
        self.conversation_history.append({"role": "user", "content": user_input})

        if self.state == ConversationState.INITIAL:
            return self._handle_initial_query(user_input)
        elif self.state == ConversationState.FOLLOW_UP:
            return self._handle_follow_up_response(user_input)
        # else:
        #     return self._handle_additional_query(user_input)

    def _handle_initial_query(self, query: str) -> str:
        """Handle the initial vibe-based query"""
        # Extract vibe keywords and map to attributes
        self.inferred_attributes = self._extract_vibe_attributes(query)

        # Determine what follow-up questions to ask
        follow_up_questions = self._generate_follow_up_questions(
            query, self.inferred_attributes
        )

        if follow_up_questions and self.follow_up_count < self.max_follow_ups:
            self.state = ConversationState.FOLLOW_UP
            self.follow_up_count += 1

            response = f"Great! I found some lovely options for '{query}'. "
            response += f"To help me narrow down the perfect pieces for you, {follow_up_questions[0]}"

            return response
        else:
            # Skip follow-ups and go straight to recommendations
            return self._generate_recommendations()

    def _handle_follow_up_response(self, response: str) -> str:
        """Handle user's response to follow-up questions"""
        # Extract additional attributes from follow-up response
        additional_attributes = self._extract_vibe_attributes(response)

        # Merge with existing inferred attributes
        for key, value in additional_attributes.items():
            if key in self.inferred_attributes:
                # Combine values if both exist
                if isinstance(self.inferred_attributes[key], list):
                    if isinstance(value, list):
                        self.inferred_attributes[key].extend(value)
                    else:
                        self.inferred_attributes[key].append(value)
                else:
                    if isinstance(value, list):
                        self.inferred_attributes[key] = [
                            self.inferred_attributes[key]
                        ] + value
                    else:
                        self.inferred_attributes[key] = [
                            self.inferred_attributes[key],
                            value,
                        ]
            else:
                self.inferred_attributes[key] = value

        # Check if we need another follow-up
        if self.follow_up_count < self.max_follow_ups:
            follow_up_questions = self._generate_follow_up_questions(
                "", self.inferred_attributes
            )
            if follow_up_questions:
                self.follow_up_count += 1
                return f"Perfect! {follow_up_questions[0]}"

        # Generate recommendations
        self.state = ConversationState.RECOMMENDATION
        return self._generate_recommendations()

    # def _handle_additional_query(self, query: str) -> str:
    #     """Handle additional queries after recommendations"""
    #     if "show me more" in query.lower() or "other options" in query.lower():
    #         return self._generate_recommendations(offset=3)
    #     elif "different" in query.lower() or "something else" in query.lower():
    #         # Reset and start over
    #         self.state = ConversationState.INITIAL
    #         self.inferred_attributes = {}
    #         self.follow_up_count = 0
    #         return self._handle_initial_query(query)
    #     else:
    #         return "I'd be happy to help you find something else! What vibe are you going for?"

    def _extract_vibe_attributes(self, text: str) -> Dict:
        """Extract attributes from vibe-based text using keyword matching"""
        text_lower = text.lower()
        extracted_attributes = {}

        for vibe, attributes in self.vibe_mappings.items():
            if vibe in text_lower:
                for attr_key, attr_value in attributes.items():
                    if attr_key in extracted_attributes:
                        # Combine values
                        if isinstance(extracted_attributes[attr_key], list):
                            if isinstance(attr_value, list):
                                extracted_attributes[attr_key].extend(attr_value)
                            else:
                                extracted_attributes[attr_key].append(attr_value)
                        else:
                            if isinstance(attr_value, list):
                                extracted_attributes[attr_key] = [
                                    extracted_attributes[attr_key]
                                ] + attr_value
                            else:
                                extracted_attributes[attr_key] = [
                                    extracted_attributes[attr_key],
                                    attr_value,
                                ]
                    else:
                        extracted_attributes[attr_key] = attr_value

        return extracted_attributes

    def _generate_follow_up_questions(
        self, original_query: str, current_attributes: Dict
    ) -> List[str]:
        """Generate targeted follow-up questions based on missing key attributes"""
        questions = []

        # Check what's missing and ask relevant questions
        if "occasion" not in current_attributes:
            if "work" in original_query.lower() or "office" in original_query.lower():
                questions.append(
                    "are you looking for something more formal or business casual?"
                )
            elif "party" in original_query.lower() or "night" in original_query.lower():
                questions.append(
                    "is this for a casual get-together or a more formal event?"
                )
            else:
                questions.append(
                    "what's the occasion - is this for work, weekend, or a special event?"
                )

        elif "fit" not in current_attributes:
            questions.append(
                "do you prefer a more relaxed, flowy fit or something more fitted and structured?"
            )

        elif "color_or_print" not in current_attributes:
            questions.append(
                "are you drawn to any particular colors or prints - maybe something bold, neutral, or pastel?"
            )

        elif "fabric" not in current_attributes:
            questions.append(
                "any fabric preferences - something breathable like linen, luxurious like silk, or cozy like cotton?"
            )

        return questions[:1]  # Return only the first question to avoid overwhelming

    def _generate_recommendations(self, offset: int = 0) -> str:
        """Generate product recommendations based on inferred attributes"""
        # Find matching products
        matches = self._find_matching_products(self.inferred_attributes)

        if not matches:
            return "I couldn't find exact matches for your vibe, but let me suggest some versatile pieces that might work! Would you like to try a different search?"

        # Get top 3 recommendations (with offset for "show more")
        top_matches = matches[offset : offset + 3]

        if not top_matches:
            return "Those were all my best suggestions! Would you like to try a different vibe or search?"

        # Generate response with justification
        response = "Here are my top picks for you:\n\n"

        for i, match in enumerate(top_matches, 1):
            product = match.product
            response += f"{i}. **{product['name']}** (${product['price']})\n"
            response += f"   {self._generate_justification(product, match.matched_attributes)}\n\n"

        if len(matches) > offset + 3:
            response += "Would you like to see more options?"

        return response

    def _find_matching_products(self, target_attributes: Dict) -> List[ProductMatch]:
        """Find products that match the target attributes"""
        matches = []

        for _, product in self.catalog.iterrows():
            match_score = 0
            matched_attributes = []

            for attr_key, attr_value in target_attributes.items():
                if attr_key in product and pd.notna(product[attr_key]):
                    product_value = str(product[attr_key]).lower()

                    if isinstance(attr_value, list):
                        # Check if any of the target values match
                        for target_val in attr_value:
                            if str(target_val).lower() in product_value:
                                match_score += 1
                                matched_attributes.append(f"{attr_key}: {target_val}")
                                break
                    else:
                        if str(attr_value).lower() in product_value:
                            match_score += 1
                            matched_attributes.append(f"{attr_key}: {attr_value}")

            if match_score > 0:
                matches.append(
                    ProductMatch(
                        product=product.to_dict(),
                        match_score=match_score,
                        matched_attributes=matched_attributes,
                    )
                )

        # Sort by match score (descending)
        matches.sort(key=lambda x: x.match_score, reverse=True)
        return matches

    def _generate_justification(
        self, product: Dict, matched_attributes: List[str]
    ) -> str:
        """Generate a justification for why this product matches the user's vibe"""
        justifications = []

        # Create justification based on matched attributes
        if any("fit" in attr for attr in matched_attributes):
            fit = product.get("fit", "")
            if "relaxed" in fit.lower():
                justifications.append("perfect for a comfortable, effortless look")
            elif "body hugging" in fit.lower():
                justifications.append("gives you that flattering, fitted silhouette")
            elif "tailored" in fit.lower():
                justifications.append("offers a polished, structured appearance")

        if any("fabric" in attr for attr in matched_attributes):
            fabric = product.get("fabric", "")
            if "linen" in fabric.lower():
                justifications.append(
                    "the breathable linen keeps you cool and comfortable"
                )
            elif "silk" in fabric.lower():
                justifications.append("luxurious silk adds elegant sophistication")
            elif "satin" in fabric.lower():
                justifications.append("smooth satin creates a glamorous finish")

        if any("color_or_print" in attr for attr in matched_attributes):
            color = product.get("color_or_print", "")
            if "pastel" in color.lower():
                justifications.append(
                    "the soft pastel tone is perfectly sweet and feminine"
                )
            elif "floral" in color.lower():
                justifications.append(
                    "the floral print adds a romantic, garden-party vibe"
                )
            elif "blue" in color.lower():
                justifications.append(
                    "the beautiful blue shade is both versatile and striking"
                )

        if justifications:
            return " - " + ", and ".join(justifications) + "."
        else:
            return f" - a versatile {product.get('category', 'piece')} that matches your style perfectly."

    def reset_conversation(self):
        """Reset the conversation state"""
        self.state = ConversationState.INITIAL
        self.conversation_history = []
        self.inferred_attributes = {}
        self.follow_up_count = 0


# Example usage and testing
if __name__ == "__main__":
    agent = VibeShoppingAgent()

    print(
        "🛍️ Welcome to your personal styling assistant! Tell me what vibe you're going for."
    )
    print("Example: 'something cute for brunch' or 'elegant date night outfit'\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ["quit", "exit", "bye"]:
            print("Happy shopping! 👋")
            break

        if user_input.lower() == "reset":
            agent.reset_conversation()
            print("🔄 Starting fresh! What vibe are you going for?")
            continue

        response = agent.process_query(user_input)
        print(f"\nStylist: {response}\n")
