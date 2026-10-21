def confidence(score: float, threshold: float = 0.67) -> float:
    return max(0.0, min(1.0, score))
