"""Paper-inspired BERT + exact WMD experiment.

This package is intentionally not imported by the production FastAPI retrieval
path. BERT models are loaded only by the cache builder or experiment runner.
"""

from .config import WmdConfig, load_wmd_config
from .preprocessing import WmdPreprocessor

__all__ = ["WmdConfig", "WmdPreprocessor", "load_wmd_config"]
