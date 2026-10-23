from doc2dial_retrieval.wmd.fusion import rank_fuse_bm25_wmd


def test_rank_fusion_uses_ranks_and_keeps_wmd_diagnostics() -> None:
    bm25 = [{"chunk_id": "shared", "bm25_score": 8.0}, {"chunk_id": "bm25-only"}]
    wmd = [{"chunk_id": "shared", "wmd_distance": 0.2}, {"chunk_id": "wmd-only", "wmd_distance": 0.4}]

    rows = rank_fuse_bm25_wmd(bm25, wmd)

    assert rows[0]["chunk_id"] == "shared"
    assert rows[0]["wmd_distance"] == 0.2
    assert rows[0]["bm25_wmd_rrf_rank"] == 1
