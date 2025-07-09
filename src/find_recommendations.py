import pandas as pd
from typing import Dict, List
from dataclasses import dataclass
from abc import ABC, abstractmethod
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler


@dataclass
class RecommendationResult:
    """Result of a recommendation query"""

    product_id: str
    product_name: str
    match_score: float
    matched_attributes: List[str]
    product_details: Dict
    reasoning: str
    matching_strategy: str


class MatchingStrategy(ABC):
    """Abstract base class for matching strategies"""

    @abstractmethod
    def match(
        self, completion: Dict, products: pd.DataFrame
    ) -> List[RecommendationResult]:
        pass


class EmbeddingBasedMatcher(MatchingStrategy):
    """Embedding-based matching using sentence transformers"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.scaler = MinMaxScaler()

    def match(
        self, completion: Dict, products: pd.DataFrame
    ) -> List[RecommendationResult]:
        """Match products using embedding similarity"""
        # Create text representation of completion
        completion_text = self._dict_to_text(completion)

        # Create text representations of products
        product_texts = []
        for _, product in products.iterrows():
            product_text = self._product_to_text(product)
            product_texts.append(product_text)

        # Generate embeddings
        completion_embedding = self.model.encode([completion_text])
        product_embeddings = self.model.encode(product_texts)

        # Calculate similarities
        similarities = cosine_similarity(completion_embedding, product_embeddings)[0]

        # Create results
        results = []
        for i, (_, product) in enumerate(products.iterrows()):
            similarity = similarities[i]

            results.append(
                RecommendationResult(
                    product_id=product["id"],
                    product_name=product["name"],
                    match_score=similarity,
                    matched_attributes=[f"embedding_similarity: {similarity:.3f}"],
                    product_details=product.to_dict(),
                    reasoning=f"Embedding similarity: {similarity:.3f} - semantic match based on overall style attributes",
                    matching_strategy="embedding_based",
                )
            )

        return sorted(results, key=lambda x: x.match_score, reverse=True)

    def _dict_to_text(self, d: Dict) -> str:
        """Convert completion dictionary to text"""
        parts = []
        for key, value in d.items():
            if isinstance(value, list):
                parts.append(f"{key}: {', '.join(map(str, value))}")
            else:
                parts.append(f"{key}: {value}")

        return "; ".join(parts)

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

        # Add product name and description for better context
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
        results = self.matcher.match(completion, self.catalog)
        # Filter out very low similarity scores (below 0.3)
        results = [match for match in results if match.match_score > min_score]
        if not results:
            raise ValueError(
                "I couldn't find exact matches for your vibe. Would you like to try a different search?"
            )

        return results[:max_results]
