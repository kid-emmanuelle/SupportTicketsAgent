"""Language frequency baselines and helper functions for English and German.

This module provides:
- EN_FREQ: letter frequency for English
- DE_FREQ: letter frequency for German
- _letter_frequency(): utility to compute letter frequencies
- _cosine_similarity(): utility for vector similarity
"""

from collections import Counter
from importlib.resources import files
import json
import math
import re


EN_FREQ = json.loads(
    (files("support_agent.freq_baseline") / "en_freq.json").read_text(
        encoding="utf-8"
    )
)

DE_FREQ = json.loads(
    (files("support_agent.freq_baseline") / "de_freq.json").read_text(
        encoding="utf-8"
    )
)


def _letter_frequency(text: str) -> dict[str, float]:
    text = text.lower()
    letters = re.findall(r"[a-zäöüß]", text)

    counts = Counter(letters)
    total = sum(counts.values())

    freq = {chr(c): 0.0 for c in range(ord("a"), ord("z") + 1)}
    for ch in ["ä", "ö", "ü", "ß"]:
        freq[ch] = 0.0

    if total == 0:
        return freq

    for ch in freq:
        freq[ch] = counts.get(ch, 0) / total

    return freq


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    dot = sum(a[k] * b.get(k, 0.0) for k in a)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
