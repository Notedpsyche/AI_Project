from doc2dial_retrieval.data import Chunk
from doc2dial_retrieval.retrieval import SearchResult, hybrid


def chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(chunk_id, "doc", "domain", "title", ["heading"], "1", text, ["1"])


def test_rrf_combines_ranked_lists_deterministically() -> None:
    dense = [SearchResult(chunk("a", "semantic evidence"), semantic_score=0.9, semantic_rank=1)]
    lexical = [SearchResult(chunk("b", "lexical evidence"), bm25_score=2.0, bm25_rank=1)]
    results = hybrid(lexical, dense, rrf_k=60, final_k=2)
    assert {item.chunk.chunk_id for item in results} == {"a", "b"}
    assert results[0].rrf_score == results[1].rrf_score
