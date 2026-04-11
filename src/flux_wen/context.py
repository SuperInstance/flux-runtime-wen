"""
Context Stack — 文境 (Wénjìng: textual context)

Classical Chinese meaning emerges entirely from context.
The same character string produces different operations
depending on the surrounding textual environment.

This maps directly to runtime polymorphic dispatch:
以文意定義 — meaning determined by textual intent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ContextDomain(Enum):
    """Textual domain — determines interpretation mode."""
    MATHEMATICS = "算"      # Calculation / arithmetic
    CONFUCIAN = "儒"        # Confucian / ethical operations
    MILITARY = "兵"         # Military / strategic operations
    GENERAL = "常"          # General purpose
    AGENT = "使"            # Agent communication
    CONTROL = "制"          # Control flow


@dataclass
class ContextFrame:
    """A single layer of interpretation context.

    In 文言, the same characters shift meaning
    based on their textual neighborhood. Each frame
    represents one such neighborhood.
    """
    domain: ContextDomain
    topic: str = ""
    register_focus: int | None = None  # which register is active
    agent_name: str = ""               # which agent is being addressed
    depth: int = 0                     # nesting depth (for loops/conditionals)

    def clone(self) -> ContextFrame:
        return ContextFrame(
            domain=self.domain,
            topic=self.topic,
            register_focus=self.register_focus,
            agent_name=self.agent_name,
            depth=self.depth,
        )


class ContextStack:
    """Stack of interpretation contexts.

    The core insight of 文言编程: meaning is NOT encoded in grammar
    (there is none), but in context. Pushing a new context frame
    changes how ALL subsequent characters are interpreted.

    同字異義 — same character, different meaning, by context.
    """

    def __init__(self) -> None:
        self._frames: list[ContextFrame] = [ContextFrame(domain=ContextDomain.GENERAL)]
        self._variables: dict[str, Any] = {}

    # ── Stack operations ──────────────────────────────────────

    def push(self, domain: ContextDomain = ContextDomain.GENERAL,
             topic: str = "", **kwargs: Any) -> None:
        """Enter a new context — like entering a clause in classical prose."""
        parent = self.current
        frame = parent.clone()
        frame.domain = domain
        frame.topic = topic or parent.topic
        frame.depth = parent.depth + 1
        for k, v in kwargs.items():
            if hasattr(frame, k):
                setattr(frame, k, v)
        self._frames.append(frame)

    def pop(self) -> ContextFrame:
        """Exit current context — like a clause ending in classical prose."""
        if len(self._frames) <= 1:
            raise RuntimeError("境空: cannot pop root context")
        return self._frames.pop()

    @property
    def current(self) -> ContextFrame:
        return self._frames[-1]

    @property
    def depth(self) -> int:
        return len(self._frames) - 1

    # ── Variable / register access ────────────────────────────

    def set_var(self, name: str, value: Any) -> None:
        self._variables[name] = value

    def get_var(self, name: str, default: Any = None) -> Any:
        return self._variables.get(name, default)

    def set_register(self, index: int, value: int) -> None:
        self._variables[f"R{index}"] = value

    def get_register(self, index: int) -> int:
        return self._variables.get(f"R{index}", 0)

    # ── Polymorphic lookup ────────────────────────────────────

    def resolve(self, char: str) -> str:
        """Resolve a character to its operation meaning in current context.

        This is the core of 以文意定義 (meaning by context).
        The same character maps to different VM instructions
        depending on the active domain.
        """
        domain = self.current.domain
        # Domain-specific character resolution
        return _POLYMORPHIC_MAP.get((domain, char), char)


# ── Polymorphic character map ────────────────────────────────
# In 文言, one character = one concept, but which concept
# depends entirely on context.

_POLYMORPHIC_MAP: dict[tuple[ContextDomain, str], str] = {
    # 加: add (math) / distribute (confucian)
    (ContextDomain.MATHEMATICS, "加"): "IADD",
    (ContextDomain.CONFUCIAN, "加"): "DISTRIBUTE",

    # 乘: multiply (math) / ride upon (military)
    (ContextDomain.MATHEMATICS, "乘"): "IMUL",
    (ContextDomain.MILITARY, "乘"): "ADVANCE",

    # 信: trust/verify (confucian) / message (general)
    (ContextDomain.CONFUCIAN, "信"): "VERIFY",
    (ContextDomain.GENERAL, "信"): "MESSAGE",

    # 知: wisdom/optimize (confucian) / know (general)
    (ContextDomain.CONFUCIAN, "知"): "OPTIMIZE",
    (ContextDomain.GENERAL, "知"): "KNOW",

    # 攻: attack (military) / compute (math, in compound)
    (ContextDomain.MILITARY, "攻"): "ATTACK",
    (ContextDomain.MATHEMATICS, "攻"): "COMPUTE",

    # 守: defend (military) / hold (control)
    (ContextDomain.MILITARY, "守"): "DEFEND",
    (ContextDomain.CONTROL, "守"): "HOLD",
}


# ── 数字映射 (Number mapping) ────────────────────────────────
# Classical Chinese numerals → integers

CNUMERALS: dict[str, int] = {
    "零": 0, "〇": 0, "一": 1, "壹": 1,
    "二": 2, "贰": 2, "兩": 2,
    "三": 3, "叁": 3,
    "四": 4, "肆": 4,
    "五": 5, "伍": 5,
    "六": 6, "陆": 6,
    "七": 7, "柒": 7,
    "八": 8, "捌": 8,
    "九": 9, "玖": 9,
    "十": 10, "拾": 10,
    "百": 100, "佰": 100,
    "千": 1000, "仟": 1000,
    "万": 10000, "萬": 10000,
}


def parse_chinese_number(s: str) -> int | None:
    """Parse a classical Chinese numeral string into an integer.

    Handles simple cases: single digits, 十, and compound 十-based numbers.
    Examples: 一→1, 十→10, 三→3, 十五→15, 三十二→32
    """
    s = s.strip()
    if not s:
        return None

    # Single character
    if len(s) == 1:
        return CNUMERALS.get(s)

    # Check if all characters are digit characters (compound like 三十二)
    total = 0
    current = 0
    for ch in s:
        if ch not in CNUMERALS:
            return None
        val = CNUMERALS[ch]
        if val >= 10:  # positional multiplier (十百千万)
            if current == 0:
                current = 1  # 十 = 10, not 0*10
            total += current * val
            current = 0
        else:
            current = val
    total += current
    return total if total > 0 else None
