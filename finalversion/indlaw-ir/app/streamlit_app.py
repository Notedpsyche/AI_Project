"""Streamlit chat UI for the local Doc2Dial retrieval prototype."""

from pathlib import Path

import streamlit as st

from doc2dial_retrieval.search import SearchEngine, result_dicts

ROOT = Path(__file__).resolve().parents[1]


@st.cache_resource
def load_resources() -> SearchEngine:
    return SearchEngine(ROOT)


st.set_page_config(page_title="Doc2Dial Retrieval", page_icon="🔎", layout="wide")
st.title("Doc2Dial Semantic Retrieval")
st.caption("Transparent BM25, semantic BGE, and hybrid evidence retrieval")

engine = load_resources()
mode = st.sidebar.selectbox("Retrieval mode", ["hybrid", "semantic", "bm25"])
top_k = st.sidebar.slider("Top K", min_value=1, max_value=5, value=5)
show_debug = st.sidebar.checkbox("Show retrieval explanation", value=True)

if "messages" not in st.session_state:
    st.session_state.messages = []
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        for result in message.get("results", []):
            heading = result["heading_path"][-1] if result["heading_path"] else result["title"]
            with st.expander(f"{result['rank']}. {heading}"):
                st.write(result["text"])
                if show_debug:
                    debug_keys = (
                        "doc_id", "domain", "semantic_score", "semantic_rank",
                        "bm25_score", "bm25_rank", "rrf_score",
                    )
                    st.json({key: result.get(key) for key in debug_keys})

if query := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)
    history = [
        {"role": item["role"], "content": item["content"]}
        for item in st.session_state.messages[:-1]
    ]
    results, best_score = engine.search(query, history=history, mode=mode)
    threshold = engine.config["retrieval"]["semantic_threshold"]
    with st.chat_message("assistant"):
        if threshold is not None and best_score < threshold:
            st.warning("No reliable evidence was found in the knowledge base.")
        else:
            st.write("Retrieved evidence:")
            for rank, result in enumerate(result_dicts(results[:top_k]), 1):
                result["rank"] = rank
                heading = result["heading_path"][-1] if result["heading_path"] else result["title"]
                with st.expander(f"{rank}. {heading}", expanded=rank == 1):
                    st.write(result["text"])
                    if show_debug:
                        debug_keys = (
                            "doc_id", "domain", "semantic_score", "semantic_rank",
                            "bm25_score", "bm25_rank", "rrf_score",
                        )
                        st.json({key: result.get(key) for key in debug_keys})
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": "Retrieved evidence",
            "results": result_dicts(results[:top_k]),
        }
    )
