import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


@dataclass
class RecommendationResult:
    """Result of a recommendation query"""

    product_id: str
    product_name: str
    match_score: float
    matched_attributes: List[str]
    product_details: Dict
    reasoning: str
    confidence_breakdown: Dict[str, float]


class MatchingStrategy(ABC):
    """Abstract base class for matching strategies"""

    @abstractmethod
    def match(
        self, completion: Dict, products: pd.DataFrame
    ) -> List[RecommendationResult]:
        pass


class EmbeddingBasedMatcher(MatchingStrategy):
    """Confidence-weighted embedding-based matching"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        # Attribute importance weights
        self.attribute_weights = {
            "occasion": 1.5,
            "category": 1.3,
            "fit": 1.2,
            "color_or_print": 1.1,
            "fabric": 1.0,
            "budget_min": 1.0,
            "budget_max": 1.0,
            "sleeve_length": 0.8,
            "neckline": 0.8,
            "length": 0.8,
        }

    def match(
        self, completion: Dict, products: pd.DataFrame
    ) -> List[RecommendationResult]:
        """Match products using confidence-weighted embedding similarity"""
        completion_text, confidence_scores = self._extract_completion_data(completion)
        avg_confidence = self._calculate_weighted_confidence(confidence_scores)

        # Filter by budget range before embedding calculations
        filtered_products = self._filter_by_budget(completion, products)

        if filtered_products.empty:
            return []

        # Generate embeddings
        product_texts = [
            self._product_to_text(product)
            for _, product in filtered_products.iterrows()
        ]
        completion_embedding = self.model.encode([completion_text])
        product_embeddings = self.model.encode(product_texts)

        # Calculate confidence-weighted similarities
        similarities = cosine_similarity(completion_embedding, product_embeddings)[0]

        results = []
        for i, (_, product) in enumerate(filtered_products.iterrows()):
            base_similarity = similarities[i]
            confidence_weighted_score = base_similarity * avg_confidence

            matched_attrs, confidence_breakdown = self._get_matched_attributes(
                completion, product, confidence_scores
            )

            reasoning = self._build_reasoning(
                base_similarity,
                avg_confidence,
                confidence_weighted_score,
                confidence_breakdown,
            )

            results.append(
                RecommendationResult(
                    product_id=product["id"],
                    product_name=product["name"],
                    match_score=confidence_weighted_score,
                    matched_attributes=matched_attrs,
                    product_details=product.to_dict(),
                    reasoning=reasoning,
                    confidence_breakdown=confidence_breakdown,
                )
            )

        return sorted(results, key=lambda x: x.match_score, reverse=True)

    def _filter_by_budget(
        self, completion: Dict, products: pd.DataFrame
    ) -> pd.DataFrame:
        """Filter products by budget range"""
        if "budget_min" not in completion and "budget_max" not in completion:
            return products

        # Extract budget values
        budget_min = None
        budget_max = None

        if "budget_min" in completion:
            budget_min_values = completion["budget_min"]
            if isinstance(budget_min_values, list) and budget_min_values:
                # Get the first value with decent confidence
                for item in budget_min_values:
                    if isinstance(item, dict) and "value" in item:
                        try:
                            budget_min = float(item["value"])
                            break
                        except (ValueError, TypeError):
                            continue

        if "budget_max" in completion:
            budget_max_values = completion["budget_max"]
            if isinstance(budget_max_values, list) and budget_max_values:
                # Get the first value with decent confidence
                for item in budget_max_values:
                    if isinstance(item, dict) and "value" in item:
                        try:
                            budget_max = float(item["value"])
                            break
                        except (ValueError, TypeError):
                            continue

        # Apply budget filtering
        filtered_products = products.copy()

        if budget_min is not None:
            filtered_products = filtered_products[
                filtered_products["price"] >= budget_min
            ]

        if budget_max is not None:
            filtered_products = filtered_products[
                filtered_products["price"] <= budget_max
            ]

        return filtered_products

    def _extract_completion_data(
        self, completion: Dict
    ) -> Tuple[str, Dict[str, float]]:
        """Extract completion text and confidence scores"""
        parts = []
        confidence_scores = {}

        for key, value in completion.items():
            if isinstance(value, list):
                values = []
                confidences = []

                for item in value:
                    if isinstance(item, dict) and "value" in item:
                        values.append(item["value"])
                        confidences.append(float(item.get("confidence", 1.0)))
                    else:
                        values.append(str(item))
                        confidences.append(1.0)

                parts.append(f"{key}: {', '.join(values)}")
                confidence_scores[key] = np.mean(confidences) if confidences else 1.0
            else:
                parts.append(f"{key}: {value}")
                confidence_scores[key] = 1.0

        return "; ".join(parts), confidence_scores

    def _calculate_weighted_confidence(
        self, confidence_scores: Dict[str, float]
    ) -> float:
        """Calculate weighted average confidence across all attributes"""
        if not confidence_scores:
            return 1.0

        weighted_sum = 0
        total_weight = 0

        for attr, confidence in confidence_scores.items():
            weight = self.attribute_weights.get(attr, 1.0)
            weighted_sum += confidence * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 1.0

    def _get_matched_attributes(
        self, completion: Dict, product: pd.Series, confidence_scores: Dict[str, float]
    ) -> Tuple[List[str], Dict[str, float]]:
        """Get matched attributes with their confidence scores"""
        matched_attrs = []
        confidence_breakdown = {}

        for attr, confidence in confidence_scores.items():
            if attr in product and pd.notna(product[attr]):
                matched_attrs.append(f"{attr}: {confidence:.3f}")
                confidence_breakdown[attr] = confidence

        return matched_attrs, confidence_breakdown

    def _build_reasoning(
        self,
        base_similarity: float,
        avg_confidence: float,
        weighted_score: float,
        confidence_breakdown: Dict[str, float],
    ) -> str:
        """Build reasoning string with confidence information"""
        reasoning_parts = [
            f"Similarity: {base_similarity:.3f}",
            f"Confidence: {avg_confidence:.3f}",
            f"Final Score: {weighted_score:.3f}",
        ]

        if confidence_breakdown:
            high_conf = [
                attr for attr, conf in confidence_breakdown.items() if conf > 0.8
            ]
            medium_conf = [
                attr for attr, conf in confidence_breakdown.items() if 0.5 < conf <= 0.8
            ]
            low_conf = [
                attr for attr, conf in confidence_breakdown.items() if conf <= 0.5
            ]

            if high_conf:
                reasoning_parts.append(f"High confidence: {', '.join(high_conf)}")
            if medium_conf:
                reasoning_parts.append(f"Medium confidence: {', '.join(medium_conf)}")
            if low_conf:
                reasoning_parts.append(f"Low confidence: {', '.join(low_conf)}")

        return " | ".join(reasoning_parts)

    def _product_to_text(self, product: pd.Series) -> str:
        """Convert product to text representation"""
        relevant_attrs = [
            "fit",
            "fabric",
            "color_or_print",
            "occasion",
            "sleeve_length",
            "neckline",
            "length",
            "category",
        ]

        parts = []
        for attr in relevant_attrs:
            if attr in product and pd.notna(product[attr]):
                parts.append(f"{attr}: {product[attr]}")

        # Add product name and description
        if "name" in product and pd.notna(product["name"]):
            parts.append(f"name: {product['name']}")
        if "description" in product and pd.notna(product["description"]):
            parts.append(f"description: {product['description']}")

        return "; ".join(parts)


class OutfitRecommendationAgent:
    def __init__(self, catalog_path: str = "data/Apparels_shared.xlsx"):
        self.catalog = pd.read_excel(catalog_path)
        self.matcher = EmbeddingBasedMatcher()

    def find_recommendations(
        self, completion: Dict, min_score: float = 0.3, max_results: int = 10
    ) -> List[RecommendationResult]:
        """Find recommendations using confidence-weighted matching"""
        results = self.matcher.match(completion, self.catalog)

        # Check if no results due to budget filtering
        if not results:
            # Check if budget filtering was applied
            budget_min = None
            budget_max = None

            if "budget_min" in completion:
                budget_min_values = completion["budget_min"]
                if isinstance(budget_min_values, list) and budget_min_values:
                    for item in budget_min_values:
                        if isinstance(item, dict) and "value" in item:
                            try:
                                budget_min = float(item["value"])
                                break
                            except (ValueError, TypeError):
                                continue

            if "budget_max" in completion:
                budget_max_values = completion["budget_max"]
                if isinstance(budget_max_values, list) and budget_max_values:
                    for item in budget_max_values:
                        if isinstance(item, dict) and "value" in item:
                            try:
                                budget_max = float(item["value"])
                                break
                            except (ValueError, TypeError):
                                continue

            if budget_min is not None or budget_max is not None:
                budget_str = ""
                if budget_min is not None and budget_max is not None:
                    budget_str = f"between ${budget_min} and ${budget_max}"
                elif budget_max is not None:
                    budget_str = f"under ${budget_max}"
                elif budget_min is not None:
                    budget_str = f"over ${budget_min}"

                raise ValueError(
                    f"I couldn't find any products within your budget range {budget_str}. "
                    "Would you like to adjust your budget or try a different style?"
                )
            else:
                raise ValueError(
                    "I couldn't find exact matches for your vibe. Please start a new conversation."
                )

        # Filter by confidence-weighted score
        results = [match for match in results if match.match_score > min_score]

        if not results:
            raise ValueError(
                "I couldn't find exact matches for your vibe. Please start a new conversation."
            )

        return results[:max_results]
