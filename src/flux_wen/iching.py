"""
易經 — I Ching Bytecode Encoding System

The I Ching (Book of Changes) encodes the universe in 64 hexagrams,
each composed of 6 lines (爻 yáo), each either solid (陽 yáng = 1)
or broken (陰 yīn = 0). This gives a 6-bit binary address space
of exactly 64 states — perfect for a VM register file.

Each hexagram (卦 guà) is formed by two trigrams (八卦 bāguà):
  - Lower trigram (內卦): bottom 3 lines → bits 0–2
  - Upper trigram (外卦): top 3 lines → bits 3–5

Address = (upper_trigram_value << 3) | lower_trigram_value

The eight trigrams map to 3-bit values:
  坤 ☷ = 000 = 0    巽 ☴ = 011 = 3    震 ☳ = 100 = 4    乾 ☰ = 111 = 7
  艮 ☶ = 001 = 1    坎 ☵ = 010 = 2    離 ☲ = 101 = 5    兌 ☱ = 110 = 6

Hexagram transitions (變卦 biànguà) serve as control-flow transfer:
when a line changes, the hexagram transforms, and the program jumps
to the new hexagram's address. This is the oldest branch mechanism
in human intellectual history.

變卦 (changing hexagram) = computed jump (indirect branch via mutation).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


# ═══════════════════════════════════════════════════════════════
# Trigrams — 八卦 (Bāguà)
# ═══════════════════════════════════════════════════════════════

class Trigram(IntEnum):
    """八卦 — the eight trigrams as 3-bit values.

    Each trigram is 3 lines read bottom-to-top as LSB-to-MSB.
    Solid line (陽) = 1, broken line (陰) = 0.

    Natural attribute mapping (自然界象):
        乾=Heaven  兌=Lake  離=Fire  震=Thunder
        巽=Wind    坎=Water 艮=Mountain 坤=Earth
    """
    KUN   = 0   # 坤 ☷ Earth      — yin yin yin
    GEN   = 1   # 艮 ☶ Mountain   — yang yin yin
    KAN   = 2   # 坎 ☵ Water      — yin yang yin
    XUN   = 3   # 巽 ☴ Wind       — yin yin yang
    ZHEN  = 4   # 震 ☳ Thunder    — yang yang yin  (actually: yin yin yang from bottom)

    # CORRECTION: Traditional binary encoding (lines bottom to top):
    # 坤: broken, broken, broken  → 0,0,0 → 0
    # 艮: yang,   yin,   yin     → 1,0,0 → 1
    # 坎: yin,    yang,  yin     → 0,1,0 → 2
    # 巽: yang,   yang,  yin     → 1,1,0 → 6  — but we use 3
    # Wait... the Fu Xi / binary ordering is: 坤0, 艮1, 坎2, 巽3, 震4, 離5, 兌6, 乾7
    # This is because the trigram lines (bottom to top) map to binary as:
    # 坤: 000, 艮: 001, 坎: 010, 巽: 011, 震: 100, 離: 101, 兌: 110, 乾: 111

    LI    = 5   # 離 ☲ Fire       — yin yang yang
    DUI   = 6   # 兌 ☱ Lake       — yang yang yin  → actually broken, yang, yang
    QIAN  = 7   # 乾 ☰ Heaven     — yang yang yang

    # Canonical name aliases (Chinese)
    @property
    def chinese(self) -> str:
        """Return the Chinese character name (卦名)."""
        return _TRIGRAM_NAMES[self]

    @property
    def nature(self) -> str:
        """Return the natural phenomenon associated with this trigram."""
        return _TRIGRAM_NATURE[self]

    @property
    def binary_str(self) -> str:
        """Return the 3-bit binary representation as a string."""
        return format(self.value, '03b')

    @property
    def lines(self) -> tuple[int, int, int]:
        """Return the three lines as a tuple (bottom, middle, top).
        Each line is 1 (yang/solid) or 0 (yin/broken).
        """
        b = self.value
        return (b & 1, (b >> 1) & 1, (b >> 2) & 1)

    @classmethod
    def from_binary(cls, value: int) -> Trigram:
        """Create a trigram from a 3-bit integer value."""
        return cls(value & 0b111)

    @classmethod
    def from_lines(cls, bottom: int, middle: int, top: int) -> Trigram:
        """Create a trigram from three line values (each 0 or 1)."""
        return cls(((top & 1) << 2) | ((middle & 1) << 1) | (bottom & 1))


_TRIGRAM_NAMES: dict[Trigram, str] = {
    Trigram.KUN:  "坤",
    Trigram.GEN:  "艮",
    Trigram.KAN:  "坎",
    Trigram.XUN:  "巽",
    Trigram.ZHEN: "震",
    Trigram.LI:   "離",
    Trigram.DUI:  "兌",
    Trigram.QIAN: "乾",
}

_TRIGRAM_NATURE: dict[Trigram, str] = {
    Trigram.KUN:  "Earth",
    Trigram.GEN:  "Mountain",
    Trigram.KAN:  "Water",
    Trigram.XUN:  "Wind",
    Trigram.ZHEN: "Thunder",
    Trigram.LI:   "Fire",
    Trigram.DUI:  "Lake",
    Trigram.QIAN: "Heaven",
}


# ═══════════════════════════════════════════════════════════════
# Hexagrams — 六十四卦 (Liùshísì Guà)
# ═══════════════════════════════════════════════════════════════

# The 64 hexagrams in King Wen (文王) sequence order.
# Each entry: (Chinese name, upper trigram, lower trigram)
# Address = (upper << 3) | lower

HEXAGRAM_KING_WEN: list[tuple[str, Trigram, Trigram]] = [
    #  1 — 8: Primal heaven/earth and their first offspring
    ("乾", Trigram.QIAN, Trigram.QIAN),   # 1  乾 — Heaven         addr 63
    ("坤", Trigram.KUN,  Trigram.KUN),    # 2  坤 — Earth          addr 0
    ("屯", Trigram.KAN,  Trigram.ZHEN),   # 3  屯 — Difficulty     addr 20
    ("蒙", Trigram.GEN,  Trigram.KAN),    # 4  蒙 — Youthful Folly addr 10
    ("需", Trigram.KAN,  Trigram.QIAN),   # 5  需 — Waiting        addr 23
    ("訟", Trigram.QIAN, Trigram.KAN),    # 6  訟 — Conflict       addr 58
    ("師", Trigram.KUN,  Trigram.KAN),    # 7  師 — Army           addr 2
    ("比", Trigram.KAN,  Trigram.KUN),    # 8  比 — Holding Together addr 16
    #  9 — 16: Taming and progress
    ("小畜", Trigram.XUN, Trigram.QIAN),  # 9   小畜 — Small Taming   addr 31
    ("履", Trigram.QIAN, Trigram.DUI),    # 10  履 — Treading         addr 62
    ("泰", Trigram.KUN,  Trigram.QIAN),   # 11  泰 — Peace           addr 7
    ("否", Trigram.QIAN, Trigram.KUN),    # 12  否 — Standstill      addr 56
    ("同人", Trigram.QIAN, Trigram.LI),    # 13  同人 — Fellowship     addr 61
    ("大有", Trigram.LI,   Trigram.QIAN),  # 14  大有 — Great Possession addr 47
    ("謙", Trigram.KUN,  Trigram.GEN),    # 15  謙 — Modesty         addr 1
    ("豫", Trigram.ZHEN, Trigram.KUN),    # 16  豫 — Enthusiasm      addr 32
    # 17 — 24: Following and decay cycle
    ("隨", Trigram.DUI,  Trigram.ZHEN),  # 17  隨 — Following       addr 52
    ("蠱", Trigram.GEN,  Trigram.XUN),   # 18  蠱 — Decay           addr 11
    ("臨", Trigram.KUN,  Trigram.DUI),    # 19  臨 — Approach         addr 6
    ("觀", Trigram.XUN,  Trigram.KUN),    # 20  觀 — Contemplation   addr 24
    ("噬嗑", Trigram.LI,  Trigram.ZHEN),  # 21  噬嗑 — Biting Through addr 44
    ("賁", Trigram.GEN,  Trigram.LI),     # 22  賁 — Grace           addr 13
    ("剝", Trigram.GEN,  Trigram.KUN),    # 23  剝 — Splitting Apart addr 8
    ("復", Trigram.KUN,  Trigram.ZHEN),   # 24  復 — Return          addr 4
    # 25 — 30: Innocence and nourishment
    ("無妄", Trigram.QIAN, Trigram.ZHEN), # 25  無妄 — Innocence     addr 60
    ("大畜", Trigram.GEN,  Trigram.QIAN), # 26  大畜 — Great Taming  addr 15
    ("頤", Trigram.GEN,  Trigram.ZHEN),   # 27  頤 — Nourishing      addr 12
    ("大過", Trigram.DUI,  Trigram.XUN),  # 28  大過 — Great Excess  addr 51
    ("坎", Trigram.KAN,  Trigram.KAN),    # 29  坎 — Abysmal Water  addr 18
    ("離", Trigram.LI,   Trigram.LI),     # 30  離 — Clinging Fire   addr 45
    # 31 — 38: Influence and duration
    ("咸", Trigram.DUI,  Trigram.GEN),    # 31  咸 — Influence      addr 49
    ("恆", Trigram.ZHEN, Trigram.XUN),    # 32  恆 — Duration       addr 35
    ("遯", Trigram.QIAN, Trigram.GEN),    # 33  遯 — Retreat         addr 57
    ("大壯", Trigram.ZHEN, Trigram.QIAN), # 34  大壯 — Great Power   addr 39
    ("晉", Trigram.LI,   Trigram.KUN),    # 35  晉 — Progress        addr 40
    ("明夷", Trigram.KUN,  Trigram.LI),    # 36  明夷 — Brilliance Injured addr 5
    ("家人", Trigram.XUN, Trigram.LI),    # 37  家人 — The Family    addr 29
    ("睽", Trigram.LI,   Trigram.DUI),    # 38  睽 — Opposition      addr 46
    # 39 — 46: Obstruction and deliverance
    ("蹇", Trigram.KAN,  Trigram.GEN),    # 39  蹇 — Obstruction    addr 17
    ("解", Trigram.ZHEN, Trigram.KAN),    # 40  解 — Deliverance    addr 34
    ("損", Trigram.GEN,  Trigram.DUI),    # 41  損 — Decrease       addr 14
    ("益", Trigram.XUN,  Trigram.ZHEN),   # 42  益 — Increase       addr 28
    ("夬", Trigram.DUI,  Trigram.QIAN),   # 43  夬 — Breakthrough   addr 55
    ("姤", Trigram.QIAN, Trigram.XUN),    # 44  姤 — Coming to Meet addr 59
    ("萃", Trigram.DUI,  Trigram.KUN),    # 45  萃 — Gathering       addr 48
    ("升", Trigram.KUN,  Trigram.XUN),    # 46  升 — Pushing Upward addr 3
    # 47 — 52: Oppression, well, revolution
    ("困", Trigram.DUI,  Trigram.KAN),    # 47  困 — Oppression     addr 50
    ("井", Trigram.KAN,  Trigram.XUN),    # 48  井 — The Well       addr 19
    ("革", Trigram.DUI,  Trigram.LI),     # 49  革 — Revolution     addr 53
    ("鼎", Trigram.LI,   Trigram.XUN),    # 50  鼎 — The Cauldron   addr 43
    ("震", Trigram.ZHEN, Trigram.ZHEN),   # 51  震 — Arousing       addr 36
    ("艮", Trigram.GEN,  Trigram.GEN),    # 52  艮 — Keeping Still  addr 9
    # 53 — 58: Development and wandering
    ("漸", Trigram.XUN,  Trigram.GEN),    # 53  漸 — Development    addr 25
    ("歸妹", Trigram.ZHEN, Trigram.DUI),  # 54  歸妹 — Marrying Maiden addr 38
    ("豐", Trigram.ZHEN, Trigram.LI),     # 55  豐 — Abundance      addr 37
    ("旅", Trigram.LI,   Trigram.GEN),    # 56  旅 — Wandering      addr 41
    ("巽", Trigram.XUN,  Trigram.XUN),    # 57  巽 — Gentle         addr 27
    ("兌", Trigram.DUI,  Trigram.DUI),    # 58  兌 — Joyous         addr 54
    # 59 — 64: Dispersion and completion
    ("渙", Trigram.XUN,  Trigram.KAN),    # 59  渙 — Dispersion     addr 26
    ("節", Trigram.KAN,  Trigram.DUI),    # 60  節 — Limitation     addr 22
    ("中孚", Trigram.XUN, Trigram.DUI),   # 61  中孚 — Inner Truth   addr 30
    ("小過", Trigram.ZHEN, Trigram.GEN),   # 62  小過 — Small Excess  addr 33
    ("既濟", Trigram.KAN, Trigram.LI),    # 63  既濟 — After Completion addr 21
    ("未濟", Trigram.LI,  Trigram.KAN),   # 64  未濟 — Before Completion addr 42
]


@dataclass(frozen=True)
class Hexagram:
    """六十四卦 — A single hexagram in the I Ching.

    A hexagram consists of 6 lines (爻), each either:
      - Solid (陽 yáng) = 1
      - Broken (陰 yīn) = 0

    The 6 lines form a 6-bit binary address.
    Lines are ordered bottom-to-top: line 0 (LSB) through line 5 (MSB).

    Attributes:
        name: Chinese name of the hexagram (卦名)
        king_wen_number: Position in the King Wen sequence (1–64)
        upper: Upper trigram (外卦, lines 3–5)
        lower: Lower trigram (內卦, lines 0–2)
        address: 6-bit binary address (0–63)
    """
    name: str
    king_wen_number: int
    upper: Trigram
    lower: Trigram

    @property
    def address(self) -> int:
        """6-bit binary address = (upper << 3) | lower."""
        return (self.upper << 3) | self.lower

    @property
    def binary_str(self) -> str:
        """6-character binary string representation (bottom to top)."""
        return format(self.address, '06b')

    @property
    def lines(self) -> tuple[int, ...]:
        """All 6 lines as a tuple (bottom=line[0] to top=line[5])."""
        b = self.address
        return tuple((b >> i) & 1 for i in range(6))

    @property
    def yang_lines(self) -> list[int]:
        """Indices of yang (solid) lines (0 = bottom, 5 = top)."""
        return [i for i in range(6) if self.lines[i] == 1]

    @property
    def yin_lines(self) -> list[int]:
        """Indices of yin (broken) lines."""
        return [i for i in range(6) if self.lines[i] == 0]

    def change_line(self, line_index: int) -> Hexagram:
        """變爻 — Change a single line (yang↔yin), producing a new hexagram.

        This is the fundamental operation of I Ching divination and
        the basis for control-flow transfer in the bytecode VM.
        A changed line produces a 變卦 (changed hexagram).

        Args:
            line_index: Which line to change (0=bottom, 5=top).

        Returns:
            The resulting hexagram after the line change.

        Raises:
            ValueError: If line_index is not in range 0–5.
        """
        if not 0 <= line_index <= 5:
            raise ValueError(f"爻位 out of range: {line_index} (must be 0–5)")
        new_addr = self.address ^ (1 << line_index)
        return address_to_hexagram(new_addr)

    def nuclear_hexagram(self) -> Hexagram:
        """互卦 — Extract the nuclear (interlocking) hexagram.

        The nuclear hexagram is formed by lines 1–4 of the original:
          Lower nuclear trigram = original lines 1, 2, 3
          Upper nuclear trigram = original lines 2, 3, 4

        This represents the hidden core of the situation.
        """
        l = self.lines
        lower_val = (l[1]) | (l[2] << 1) | (l[3] << 2)
        upper_val = (l[2]) | (l[3] << 1) | (l[4] << 2)
        new_addr = (upper_val << 3) | lower_val
        return address_to_hexagram(new_addr)

    def reversed_hexagram(self) -> Hexagram:
        """綜卦 — The reversed (overturned) hexagram.

        Swap upper and lower trigrams. Represents viewing the
        situation from the opposite perspective.
        """
        new_addr = (self.lower << 3) | self.upper
        return address_to_hexagram(new_addr)

    def complement_hexagram(self) -> Hexagram:
        """錯卦 — The complementary (opposite) hexagram.

        Invert all 6 lines. Represents the diametric opposite.
        """
        new_addr = self.address ^ 0b111111
        return address_to_hexagram(new_addr)

    def __repr__(self) -> str:
        return (f"Hexagram(name='{self.name}', kw={self.king_wen_number}, "
                f"addr={self.address}, bin='{self.binary_str}')")


# ═══════════════════════════════════════════════════════════════
# Lookup Tables
# ═══════════════════════════════════════════════════════════════

def _build_hexagram_tables() -> tuple[
    dict[int, Hexagram],     # address → Hexagram
    dict[str, Hexagram],     # name → Hexagram
    list[Hexagram],          # King Wen ordered list
]:
    """Pre-compute all lookup tables for the 64 hexagrams."""
    by_address: dict[int, Hexagram] = {}
    by_name: dict[str, Hexagram] = {}
    king_wen_list: list[Hexagram] = []

    for idx, (name, upper, lower) in enumerate(HEXAGRAM_KING_WEN):
        kw_num = idx + 1
        hexagram = Hexagram(
            name=name,
            king_wen_number=kw_num,
            upper=upper,
            lower=lower,
        )
        king_wen_list.append(hexagram)
        by_name[name] = hexagram
        by_address[hexagram.address] = hexagram

    return by_address, by_name, king_wen_list


# Module-level tables (computed once at import time)
HEXAGRAM_BY_ADDRESS: dict[int, Hexagram] = {}
HEXAGRAM_BY_NAME: dict[str, Hexagram] = {}
HEXAGRAMS_KING_WEN: list[Hexagram] = []

_HEXAGRAM_BY_KING_WEN: dict[int, Hexagram] = {}


def _initialize_tables() -> None:
    """Initialize all hexagram lookup tables."""
    global HEXAGRAM_BY_ADDRESS, HEXAGRAM_BY_NAME, HEXAGRAMS_KING_WEN
    global _HEXAGRAM_BY_KING_WEN
    HEXAGRAM_BY_ADDRESS, HEXAGRAM_BY_NAME, HEXAGRAMS_KING_WEN = _build_hexagram_tables()
    _HEXAGRAM_BY_KING_WEN = {h.king_wen_number: h for h in HEXAGRAMS_KING_WEN}


_initialize_tables()


# ═══════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════

def address_to_hexagram(address: int) -> Hexagram:
    """Look up a hexagram by its 6-bit binary address.

    Args:
        address: Integer in range 0–63.

    Returns:
        The hexagram at that address.

    Raises:
        ValueError: If address is out of range.
        KeyError: If no hexagram maps to that address (should not happen for 0–63).
    """
    if not 0 <= address <= 63:
        raise ValueError(f"Hexagram address out of range: {address} (must be 0–63)")
    return HEXAGRAM_BY_ADDRESS[address]


def name_to_hexagram(name: str) -> Hexagram:
    """Look up a hexagram by its Chinese name (卦名).

    Args:
        name: Chinese name, e.g. '乾', '屯', '既濟'.

    Returns:
        The named hexagram.

    Raises:
        KeyError: If name is not a known hexagram.
    """
    return HEXAGRAM_BY_NAME[name]


def king_wen_to_hexagram(number: int) -> Hexagram:
    """Look up a hexagram by its King Wen sequence number (1–64).

    Args:
        number: King Wen position, 1-indexed.

    Returns:
        The hexagram at that position.
    """
    if not 1 <= number <= 64:
        raise ValueError(f"King Wen number out of range: {number} (must be 1–64)")
    return _HEXAGRAM_BY_KING_WEN[number]


def hexagram_from_trigrams(upper: Trigram, lower: Trigram) -> Hexagram:
    """Construct a hexagram from its upper and lower trigrams.

    Args:
        upper: Upper trigram (外卦).
        lower: Lower trigram (內卦).

    Returns:
        The corresponding hexagram.
    """
    addr = (upper << 3) | lower
    return address_to_hexagram(addr)


def encode_transition(from_hex: Hexagram | int | str,
                      changed_lines: list[int] | tuple[int, ...]) -> int:
    """Encode a hexagram transition (變卦) as a jump target address.

    This is the control-flow primitive: changing one or more lines
    of a hexagram produces a new hexagram, and the program jumps
    to the new hexagram's address.

    Args:
        from_hex: Source hexagram (Hexagram object, address int, or name str).
        changed_lines: Indices of lines to change (0=bottom, 5=top).

    Returns:
        The target address (the resulting hexagram's address).
    """
    if isinstance(from_hex, int):
        source = address_to_hexagram(from_hex)
    elif isinstance(from_hex, str):
        source = name_to_hexagram(from_hex)
    else:
        source = from_hex

    target_addr = source.address
    for line_idx in changed_lines:
        target_addr ^= (1 << line_idx)

    return target_addr


def trigram_register_address(trigram: Trigram, position: str = "lower") -> int:
    """Get the bit-field position for a trigram within a hexagram address.

    Used for 3-bit register addressing within the 6-bit hexagram space.

    Args:
        trigram: The trigram value (0–7).
        position: 'lower' (bits 0–2) or 'upper' (bits 3–5).

    Returns:
        The 3-bit register address for the trigram in the given position.
    """
    if position == "lower":
        return trigram.value & 0b111
    elif position == "upper":
        return (trigram.value & 0b111) << 3
    else:
        raise ValueError(f"Invalid position: {position} (must be 'lower' or 'upper')")


# ═══════════════════════════════════════════════════════════════
# Bytecode Encoding Utilities
# ═══════════════════════════════════════════════════════════════

def encode_hexagram_as_byte(hexagram: Hexagram | int) -> int:
    """Encode a hexagram as a single byte (with 2 high bits zero).

    The 6-bit hexagram address fits in the low 6 bits of a byte.
    High bits can be used for flags in future extensions.

    Args:
        hexagram: Hexagram or its address.

    Returns:
        Byte value (0–63).
    """
    addr = hexagram.address if isinstance(hexagram, Hexagram) else hexagram
    return addr & 0b111111


def decode_byte_to_hexagram(byte_val: int) -> Hexagram:
    """Decode a byte value to its hexagram (low 6 bits used).

    Args:
        byte_val: Byte value (high 2 bits ignored).

    Returns:
        The hexagram at the encoded address.
    """
    return address_to_hexagram(byte_val & 0b111111)


def hexagram_program_encode(hexagram_sequence: list[int | str | Hexagram]) -> bytes:
    """Encode a sequence of hexagrams as a bytecode program.

    Each hexagram occupies one byte (6-bit address + 2 padding bits).
    A sequence of hexagrams IS a program — the order of hexagrams
    encodes the order of operations.

    Args:
        hexagram_sequence: List of hexagrams (addresses, names, or objects).

    Returns:
        Bytearray of encoded program.
    """
    program = bytearray()
    for item in hexagram_sequence:
        if isinstance(item, int):
            addr = item
        elif isinstance(item, str):
            addr = name_to_hexagram(item).address
        else:
            addr = item.address
        program.append(addr & 0xFF)
    return bytes(program)


def hexagram_program_decode(program_bytes: bytes) -> list[Hexagram]:
    """Decode a bytecode program back into a hexagram sequence.

    Args:
        program_bytes: Encoded program bytes.

    Returns:
        List of hexagrams in program order.
    """
    return [decode_byte_to_hexagram(b) for b in program_bytes]


# ═══════════════════════════════════════════════════════════════
# Display Utilities
# ═══════════════════════════════════════════════════════════════

def hexagram_visual(hexagram: Hexagram, width: int = 6) -> str:
    """Render a hexagram as Unicode block characters.

    Uses full blocks (█) for yang (solid) lines and two half-blocks
    (▄) for yin (broken) lines, rendered top-to-bottom.

    Args:
        hexagram: The hexagram to visualize.
        width: Character width of each line.

    Returns:
        Multi-line string visual representation.
    """
    lines_hex = hexagram.lines
    # Render top-to-bottom (line 5 first)
    result_lines = []
    for i in range(5, -1, -1):
        if lines_hex[i] == 1:
            result_lines.append("█" * width)
        else:
            result_lines.append("▄ " * (width // 2))
    return "\n".join(result_lines)


def hexagram_table() -> str:
    """Generate a formatted table of all 64 hexagrams.

    Returns:
        Multi-line string with all hexagrams and their addresses.
    """
    lines = []
    lines.append("╔═══════════════════════════════════════════════════════════════╗")
    lines.append("║  六十四卦 — 64 Hexagrams — Address Table                      ║")
    lines.append("╠═══════╦══════════╦═══════╦═══════╦═════════════════════════╣")
    lines.append("║  KW#  ║  Name    ║ Upper ║ Lower ║  Binary  │  Addr         ║")
    lines.append("╠═══════╬══════════╬═══════╬═══════╬═════════════════════════╣")

    for h in HEXAGRAMS_KING_WEN:
        name_display = h.name.ljust(8, "　") if len(h.name) < 4 else h.name
        upper_name = h.upper.chinese
        lower_name = h.lower.chinese
        lines.append(
            f"║  {h.king_wen_number:3d}  ║ {name_display:8s} ║   {upper_name}   ║   {lower_name}   ║"
            f"  {h.binary_str}  │  {h.address:3d} (0x{h.address:02X})"
        )

    lines.append("╚═══════╩══════════╩═══════╩═══════╩═════════════════════════╝")
    return "\n".join(lines)
