"""Inspect semantic score distributions before choosing a prototype threshold."""

# ruff: noqa: E501

from pathlib import Path

from doc2dial_retrieval.data import load_dialogues
from doc2dial_retrieval.search import SearchEngine

ROOT = Path(__file__).resolve().parents[1]
OFF_TOPIC = ["How do I bake bread?", "What is the capital of Japan?", "How do I train for a marathon?", "What is quantum gravity?", "How can I grow roses?", "Which film won an award?", "What is the weather on Mars?", "How do I repair a bicycle?", "What is a good recipe for soup?", "How do I learn the piano?"]


def main() -> None:
    engine = SearchEngine(ROOT)
    validation = load_dialogues(ROOT / "data/raw/doc2dial", "validation")
    in_domain = []
    for domain in sorted(validation):
        for dialogues in validation[domain].values():
            for dialogue in dialogues:
                for turn in dialogue.get("turns", []):
                    if turn.get("references"):
                        in_domain.append(turn["utterance"])
                    if len(in_domain) == 10:
                        break
                if len(in_domain) == 10:
                    break
            if len(in_domain) == 10:
                break
        if len(in_domain) == 10:
            break
    print("IN-DOMAIN")
    for query in in_domain:
        _, score = engine.search(query, mode="semantic")
        print(f"query: {query}\ntop cosine: {score:.6f}\n")
    print("OFF-TOPIC")
    for query in OFF_TOPIC:
        _, score = engine.search(query, mode="semantic")
        print(f"query: {query}\ntop cosine: {score:.6f}\n")
    print("Prototype heuristic threshold: null; choose only after inspecting these distributions.")


if __name__ == "__main__":
    main()
