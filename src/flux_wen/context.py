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
    """Textual domain — determines interpretation mode.

    Each domain represents a knowledge tradition. In 文言编程, the same
    character string activates different bytecode depending on the
    surrounding textual environment (文境).

    六域 — six primary knowledge domains:
      算 Mathematics — quantitative reasoning
      儒 Confucian — ethical/philosophical operations
      兵 Military — strategic/competitive operations
      理 Physics/Science — natural world modeling
      算 Computing — algorithmic/data processing
      使 Agent — inter-agent communication
      制 Control — program flow control
      常 General — default domain
    """
    MATHEMATICS = "算"      # Calculation / arithmetic
    CONFUCIAN = "儒"        # Confucian / ethical operations
    MILITARY = "兵"         # Military / strategic operations
    GENERAL = "常"          # General purpose
    AGENT = "使"            # Agent communication
    CONTROL = "制"          # Control flow
    PHILOSOPHY = "理"        # Philosophy / Daoist ontology
    COMPUTING = "機"        # Computing / data processing


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

        Now delegates to CharacterPolymorphismResolver for richer resolution.
        """
        resolver = CharacterPolymorphismResolver()
        return resolver.resolve(char, self.current.domain, self)

    def resolve_with_context(self, char: str) -> tuple[str, str]:
        """Resolve a character and return (opcode, domain_label) tuple.

        Provides richer context about the resolution.
        """
        resolver = CharacterPolymorphismResolver()
        domain = self.current.domain
        result = resolver.resolve(char, domain, self)
        return result, domain.value


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


# ═══════════════════════════════════════════════════════════════
# CharacterPolymorphismResolver — 字形多態解析器
# ═══════════════════════════════════════════════════════════════

class CharacterPolymorphismResolver:
    """字形多態解析器 — Resolves characters to opcodes based on domain context.

    In Classical Chinese, the same character has radically different meanings
    depending on context. This resolver tracks active domains and selects
    the correct opcode for any given character.

    Key example: 道 (dào)
      哲學 domain (Philosophy) = "the Way" → OP_NOP (architectural marker)
      物理 domain (Physics) = "path" → OP_JMP (control flow transfer)
      計算 domain (Computing) = "data channel" → OP_CHANNEL (I/O channel)

    同字異義 — same character, different meaning, by domain.
    """

    def __init__(self) -> None:
        self._extended_map: dict[tuple[ContextDomain, str], str] = {}
        self._descriptions: dict[tuple[ContextDomain, str], str] = {}
        self._load_extended_mappings()

    def resolve(self, char: str, domain: ContextDomain,
                 ctx: ContextStack | None = None) -> str:
        """Resolve a character to its opcode in the given domain.

        Checks extended map first, then falls back to the base polymorphic map.

        Args:
            char: A single Chinese character.
            domain: The active textual domain.
            ctx: Optional ContextStack for deeper context-aware resolution.

        Returns:
            The opcode string for this character in this domain.
        """
        # Check extended map
        key = (domain, char)
        if key in self._extended_map:
            return self._extended_map[key]
        # Fall back to base map
        return _POLYMORPHIC_MAP.get(key, char)

    def resolve_with_info(self, char: str, domain: ContextDomain) -> dict[str, str]:
        """Resolve with full descriptive information.

        Returns dict with 'opcode', 'domain', 'character', 'description' keys.
        """
        opcode = self.resolve(char, domain)
        desc = self._descriptions.get((domain, char), "")
        return {
            "opcode": opcode,
            "domain": domain.value,
        }

    def all_meanings(self, char: str) -> list[dict[str, str]]:
        """Get all domain meanings for a polymorphic character.

        Args:
            char: A single Chinese character.

        Returns:
            List of dicts with 'domain' and 'opcode' for each domain.
        """
        results = []
        for domain in ContextDomain:
            opcode = self.resolve(char, domain)
            if opcode != char:  # Has a mapping
                results.append({
                    "domain": domain.value,
                    "opcode": opcode,
                })
        return results

    def register(self, domain: ContextDomain, char: str,
                 opcode: str, description: str = "") -> None:
        """Register a new character-to-opcode mapping.

        註冊 — register a new polymorphic dispatch entry.
        """
        self._extended_map[(domain, char)] = opcode
        if description:
            self._descriptions[(domain, char)] = description

    def _load_extended_mappings(self) -> None:
        """Load all extended polymorphic character mappings.

        Beyond the base mappings, this adds rich semantic mappings
        for philosophy, physics, and computing domains.
        """
        mappings: list[tuple[ContextDomain, str, str, str]] = [
            # ── 道 (dào) — the ultimate polymorphic character ───────
            # 道: philosophy → the Way (architectural no-op)
            (ContextDomain.PHILOSOPHY, "道", "NOP",
             "道可道非常道 — The Way that can be spoken is not the eternal Way"),
            # 道: physics → path (control flow)
            (ContextDomain.PHILOSOPHY, "道", "NOP",
             "道：物理學的路徑 → 軌道轉移"),
            # 道: computing → data channel
            (ContextDomain.COMPUTING, "道", "CHANNEL",
             "道：計算之道 → 數據通道"),

            # ── 理 (lǐ) — reason/principle ────────────────────────
            (ContextDomain.PHILOSOPHY, "理", "ICMP",
             "理者分也 — Reason divides and analyzes"),
            (ContextDomain.MATHEMATICS, "理", "ICMP",
             "理：邏輯比較 — Logical comparison"),
            (ContextDomain.COMPUTING, "理", "SORT",
             "理：排序 — Sort and order data"),

            # ── 氣 (qì) — energy/vital force ─────────────────────
            (ContextDomain.PHILOSOPHY, "氣", "NOP",
             "氣：生機 — Vital energy, creative force"),
            (ContextDomain.MATHEMATICS, "氣", "POWER",
             "氣：冪運算 — Exponentiation"),
            (ContextDomain.COMPUTING, "氣", "STREAM",
             "氣：資料流 — Data stream"),

            # ── 德 (dé) — virtue/power ───────────────────────────
            (ContextDomain.CONFUCIAN, "德", "TRUST_CHECK",
             "德者得也 — Virtue is attainment"),
            (ContextDomain.PHILOSOPHY, "德", "CACHE_STORE",
             "德：積累 — Accumulated virtue/cache"),

            # ── 道/PATH in Physics → trajectory/flow ─────────────
            (ContextDomain.PHILOSOPHY, "道", "NOP",
             "道：路徑 — The path of nature"),

            # ── Computing-specific ─────────────────────────────────
            (ContextDomain.COMPUTING, "算", "COMPUTE",
             "算：計算 — Compute"),
            (ContextDomain.COMPUTING, "法", "HASH",
             "法：演算法 — Algorithm"),
            (ContextDomain.COMPUTING, "網", "NET_SEND",
             "網：網路 — Network I/O"),
            (ContextDomain.COMPUTING, "數", "ARRAY_LEN",
             "數：資料量 — Data length"),

            # ── Physics-specific ────────────────────────────────────
            (ContextDomain.PHILOSOPHY, "陰", "LOAD",
             "陰：接收 — Yin receives, load data"),
            (ContextDomain.PHILOSOPHY, "陽", "STORE",
             "陽：發送 — Yang emits, store data"),
            (ContextDomain.PHILOSOPHY, "極", "HALT",
             "極：極限 — Extreme/terminal state"),

            # ── Military extensions ────────────────────────────────
            (ContextDomain.MILITARY, "勢", "JE",
             "勢：乘勢 — Momentum, exploit advantage"),
            (ContextDomain.MILITARY, "虛", "JZ",
             "虛：避實擊虛 — Exploit weakness"),

            # ── Agent extensions ──────────────────────────────────
            (ContextDomain.AGENT, "約", "DELEGATE",
             "約：盟約 — Covenant agreement"),
            (ContextDomain.AGENT, "盟", "BROADCAST",
             "盟：結盟 — Alliance broadcast"),

            # ── Control extensions ────────────────────────────────
            (ContextDomain.CONTROL, "變", "HEX_JUMP",
             "變：變化 — I Ching hexagram change/jump"),
            (ContextDomain.CONTROL, "合", "IADD",
             "合：合併 — Merge/combine"),
        ]
        for domain, char, opcode, desc in mappings:
            self._extended_map[(domain, char)] = opcode
            self._descriptions[(domain, char)] = desc


# Module-level singleton resolver
_POLYMORPHIC_RESOLVER = CharacterPolymorphismResolver()


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
