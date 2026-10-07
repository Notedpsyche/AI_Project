from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_NAME = "BAAI/bge-base-en-v1.5"
REFUSAL = (
    "I couldn't find enough information in the available documents to answer that reliably."
)
