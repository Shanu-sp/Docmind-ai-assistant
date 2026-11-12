import logging
from typing import List
from ai.services.gemini import GeminiProvider

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    High-throughput vector embedding service integrating with Google Gemini's
    embedding models, featuring Matryoshka dimension scaling (768d),
    automatic batching (50 items/request), and multi-key round-robin failover.
    """

    MODEL_NAME = "models/gemini-embedding-001"
    TARGET_DIMENSION = 768
    BATCH_SIZE = 50

    def __init__(self, provider: GeminiProvider = None):
        self.provider = provider or GeminiProvider()

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generates a 768-dimensional float embedding vector for a single text fragment.
        """
        results = self.generate_batch_embeddings([text])
        if not results:
            raise RuntimeError("Failed to generate embedding for text fragment.")
        return results[0]

    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds multiple text fragments in batches of up to 50 items per API call.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of 768-dimensional float vectors matching the input order.
        """
        if not texts:
            return []

        # Sanitize texts (Gemini rejects empty strings or strings with only whitespace)
        clean_texts = []
        for t in texts:
            cleaned = t.replace("\r\n", " ").replace("\n", " ").strip()
            clean_texts.append(cleaned if cleaned else " ")

        clients = self.provider._get_clients_to_try()
        if not clients:
            raise RuntimeError("No Gemini API clients available. Please check GEMINI_API_KEY(S) in .env.")

        all_embeddings: List[List[float]] = []

        # Process in batches
        for i in range(0, len(clean_texts), self.BATCH_SIZE):
            batch = clean_texts[i:i + self.BATCH_SIZE]
            batch_success = False
            last_error = None

            for client, key_tag in clients:
                try:
                    response = client.models.embed_content(
                        model=self.MODEL_NAME,
                        contents=batch,
                        config={"output_dimensionality": self.TARGET_DIMENSION}
                    )

                    if not response or not response.embeddings:
                        raise ValueError(f"Empty embedding response returned from Gemini [Key {key_tag}].")

                    batch_vectors = [list(e.values) for e in response.embeddings]

                    # Sanity check dimension
                    if batch_vectors and len(batch_vectors[0]) != self.TARGET_DIMENSION:
                        logger.warning(
                            f"Expected dimension {self.TARGET_DIMENSION}, got {len(batch_vectors[0])}. Dimension adjustment may be required."
                        )

                    all_embeddings.extend(batch_vectors)
                    batch_success = True
                    break
                except Exception as e:
                    err_msg = str(e)
                    logger.warning(f"Batch embedding failed on key {key_tag}: {err_msg}. Failing over to next key...")
                    last_error = e

            if not batch_success:
                logger.error(f"All Gemini keys exhausted for batch offset {i}. Final error: {last_error}")
                raise RuntimeError(f"All Gemini embedding API keys exhausted. Error: {last_error}")

        return all_embeddings
