import json

from doc2dial_retrieval.data import build_chunks

# ruff: noqa: E501


def test_span_identity_includes_doc_id_and_title_only_section_is_heading(tmp_path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    payload = {
        "doc_data": {
            "dmv": {
                "doc-a": {
                    "title": "A",
                    "doc_id": "doc-a",
                    "domain": "dmv",
                    "spans": {
                        "1": {"id_sp": "1", "id_sec": "s1", "title": "Eligibility", "parent_titles": [], "text_sec": "", "text_sp": "Eligibility"},
                        "2": {"id_sp": "2", "id_sec": "s1", "title": "Eligibility", "parent_titles": [], "text_sec": "You must provide proof of identity.", "text_sp": "You must provide proof of identity."},
                    },
                }
            }
        }
    }
    (raw / "doc2dial_doc.json").write_text(json.dumps(payload), encoding="utf-8")
    chunks, stats = build_chunks(raw)
    assert len(chunks) == 1
    assert chunks[0].heading_path == ["Eligibility"]
    assert chunks[0].span_ids == ["1", "2"]
    assert stats["span_keys_seen"] == 2

