"""Eisenhower-Prioritaeten A–D."""

from __future__ import annotations

import re
from dataclasses import dataclass

PRIORITIES = ("A", "B", "C", "D")

LABELS = {
    "A": "Wichtig & Dringend",
    "B": "Dringend & Unwichtig",
    "C": "Wichtig & Undringend",
    "D": "Unwichtig & Undringend",
}

_URGENT = re.compile(
    r"\b(sofort|asap|dringend|heute|deadline|eilig|urgent|jetzt|morgen)\b",
    re.IGNORECASE,
)
_IMPORTANT = re.compile(
    r"\b(wichtig|kritisch|muss|essenziell|priorit[aä]t|important|blockiert)\b",
    re.IGNORECASE,
)
_LOW = re.compile(
    r"\b(irgendwann|spaeter|später|nice.?to.?have|optional|wenn.?zeit|low)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PriorityGuess:
    priority: str | None
    confidence: float
    reason: str


def label(priority: str | None) -> str:
    if not priority:
        return ""
    return LABELS.get(priority, priority)


def format_priority(priority: str | None) -> str:
    if not priority:
        return ""
    return f"{priority} – {label(priority)}"


def guess_priority(text: str) -> PriorityGuess:
    """Grobe Heuristik; bei Unsicherheit confidence < 0.7."""
    urgent = bool(_URGENT.search(text))
    important = bool(_IMPORTANT.search(text))
    low = bool(_LOW.search(text))

    if urgent and important:
        return PriorityGuess("A", 0.85, "wichtig+dringend erkannt")
    if urgent and not important:
        return PriorityGuess("B", 0.75, "dringend erkannt")
    if important and not urgent:
        return PriorityGuess("C", 0.75, "wichtig erkannt")
    if low:
        return PriorityGuess("D", 0.7, "niedrige Prioritaet erkannt")
    return PriorityGuess(None, 0.3, "unklar")
