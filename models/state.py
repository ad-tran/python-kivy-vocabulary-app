from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, TypedDict

class WordDetail(TypedDict, total=False):
    meaning: str
    examples: List[str]
    pos: List[str]

@dataclass(slots=True)
class AppState:
    vocabulary: list[str] = field(default_factory=list)
    displayed_words: set[str] = field(default_factory=set)
    current_word: Optional[str] = None

    known_words: set[str] = field(default_factory=set)
    new_words: set[str] = field(default_factory=set)
    known_sequence: list[str] = field(default_factory=list)
    new_sequence: list[str] = field(default_factory=list)

    user_words: set[str] = field(default_factory=set)
    removed_words: set[str] = field(default_factory=set)

    learned_session: list[str] = field(default_factory=list)
    learned_log: dict[str, str] = field(default_factory=dict)
    word_details: dict[str, list[WordDetail]] = field(default_factory=dict)
    word_ipa: dict[str, str] = field(default_factory=dict)

    tongue_twisters: set[str] = field(default_factory=set)
    expressions: list[str] = field(default_factory=list)
    learn_order_mode: str = "Zufällig"

    # UI-Cache/Zähler (nicht persistiert)
    word_history: list[str] = field(default_factory=list)
    history_index: int = -1
    remaining_count: int = 0