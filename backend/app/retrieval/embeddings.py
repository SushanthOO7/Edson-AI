class EmbeddingProvider:
    async def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError("Embeddings are planned for the pgvector phase.")
