class VectorSearch:
    async def find_similar_examples(self, query_embedding: list[float], *, limit: int = 3) -> list[dict]:
        raise NotImplementedError("Vector search is planned for the pgvector phase.")
