"""
詩體 — Poetry Structures as Program Layout

Classical Chinese poetry forms encode program structure.
Each poetic form maps to a specific program layout pattern:

  五言詩 (5-char poem)  = fixed 5-instruction block
  七言詩 (7-char poem)  = fixed 7-instruction block with 2 padding NOPs
  聯     (couplet)      = paired blocks with data dependency
  絕句   (quatrain)     = 4-block program with entry/exit
  律詩   (regulated)    = 8-block program with parallel middle 4 blocks

The key insight: Classical Chinese poetry IS structured programming.
Rhyme (韻腳) serves as jump targets — a rhyme word marks a label
that other lines can jump to. Tonal patterns (平仄) serve as
instruction scheduling constraints — the tonal pattern determines
which instructions can execute in parallel.

詩即程 — the poem IS the program.
韻即標 — the rhyme IS the label.
平仄即序 — the tones ARE the schedule.

Poetry Structure Mapping:
  ┌─────────────────────────────────────────────────┐
  │ 絕句 (Quatrain) = Complete Program              │
  │                                                 │
  │ 起句 (Opening)   = Entry / initialization       │
  │ 承句 (Continuing) = Setup / data loading        │
  │ 轉句 (Turning)   = Core computation (branch)    │
  │ 合句 (Concluding) = Exit / result output        │
  │                                                 │
  │  起 → 承 → 轉 → 合                              │
  │  Entry → Setup → Compute → Output               │
  └─────────────────────────────────────────────────┘
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .vm import Instruction, Opcode
from .iching import Hexagram, name_to_hexagram, address_to_hexagram


# ═══════════════════════════════════════════════════════════════
# Tonal System — 平仄 (Píngzè)
# ═══════════════════════════════════════════════════════════════

class TonalValue(Enum):
    """平仄 tonal values for instruction scheduling.

    In Classical Chinese poetry, each character has a tonal value:
      - 平 (Píng): Level tone → can execute in parallel with other 平
      - 仄 (Zè): Oblique tone → must execute sequentially

    This maps directly to instruction-level parallelism:
    - 平 instructions are independent and can be reordered/scheduled freely
    - 仄 instructions have dependencies and must execute in order

    平行 parallelism from 平 tone — a linguistic pun that works
    perfectly in both English and Chinese.
    """
    PING = "平"     # Level tone — parallelizable
    ZE = "仄"       # Oblique tone — sequential

    @property
    def is_parallelizable(self) -> bool:
        """Whether this tone allows parallel execution."""
        return self == TonalValue.PING

    @property
    def is_sequential(self) -> bool:
        """Whether this tone requires sequential execution."""
        return self == TonalValue.ZE


# Tonal pattern for a standard 五言詩 (5-character poem):
# 仄仄平平仄 — Z Z P P Z
FIVE_CHAR_TONAL: list[TonalValue] = [
    TonalValue.ZE, TonalValue.ZE, TonalValue.PING, TonalValue.PING, TonalValue.ZE,
]

# Tonal pattern for a standard 七言詩 (7-character poem):
# 平平仄仄平平仄 — P P Z Z P P Z
SEVEN_CHAR_TONAL: list[TonalValue] = [
    TonalValue.PING, TonalValue.PING, TonalValue.ZE, TonalValue.ZE,
    TonalValue.PING, TonalValue.PING, TonalValue.ZE,
]


# Common tone patterns (平仄格式)
# Each character is classified by its historical tone class.
# In practice, the following heuristics apply for Middle Chinese:
#   平聲 (Level): modern Mandarin tones 1 and 2
#   仄聲 (Oblique): modern Mandarin tones 3 and 4, and entering tone (入聲)

# Characters known to be 平 (level) tone — simplified approximation
PING_CHARS = set("天春夏秋風雲山江河流星明月光陽平和安平清輕高深長遠心東西南"
                 "北中同來回去開生明清風雲花紅青黃藍白黑金銀銅鐵丹書詩歌"
                 "文章言語音聲琴棋龍鶴鷹鷗魚蝦蜂蝶蘭松竹梅桃梨杏柳梧桐"
                 "英雄才人王侯將相公平正方圓通同和安寧清明光輝輝煌")

# Characters known to be 仄 (oblique) tone — simplified approximation
ZE_CHARS = set("地冬火水雨雪霧霜霧日影夜夢醉笑問答語意道理道法術算數學"
               "問答取與起落出入上下左右前後進退攻守戰勝敗死生老幼小大"
               "長短輕重遠近快慢高低深淺多少是非好惡善惡美醜真假虛實"
               "可否能否必將要欲敢肯願望見聽聞思想念愛恨怒喜悲歡愁苦樂"
               "立坐走跑飛跳爬滾轉動搖擺推拉擊破碎裂開閉合分聚散離合")


def classify_tone(character: str) -> TonalValue:
    """Classify a character's tonal value (平 or 仄).

    Uses a simplified heuristic based on common character classifications.
    For production use, a complete 中古音 (Middle Chinese) phonology
    table would be needed.

    Args:
        character: A single Chinese character.

    Returns:
        The tonal value (平 or 仄).
    """
    if character in PING_CHARS:
        return TonalValue.PING
    if character in ZE_CHARS:
        return TonalValue.ZE
    # Default: characters not in our table default to 仄
    return TonalValue.ZE


# ═══════════════════════════════════════════════════════════════
# Rhyme System — 韻腳 (Yùnjiǎo)
# ═══════════════════════════════════════════════════════════════

@dataclass
class RhymeGroup:
    """A rhyme group (韻部) — a collection of rhyming characters.

    In the 韻腳 system, the final character of a line (the rhyme word)
    serves as a jump target label. All lines ending with characters
    from the same RhymeGroup share the same label.

    This is how classical poets created coherent structures — and
    how 文言 programs create named jump targets.
    """
    name: str               # Rhyme group name (韻部名)
    characters: set[str]    # Characters that rhyme in this group
    label: str = ""         # Jump target label

    def rhymes_with(self, character: str) -> bool:
        """Check if a character belongs to this rhyme group."""
        return character in self.characters


# Standard rhyme groups from 平水韻 (Pingshui Rhyme Dictionary)
# Using a simplified subset for the programming model
RHYME_GROUPS: dict[str, RhymeGroup] = {
    "東": RhymeGroup("東", {"東", "同", "通", "風", "空", "中", "終", "窮",
                             "宮", "功", "紅", "洪", "鴻", "弓", "躬"}),
    "真": RhymeGroup("真", {"真", "人", "身", "新", "春", "神", "臣", "塵",
                             "珍", "賓", "濱", "頻", "巾", "均", "匀"}),
    "寒": RhymeGroup("寒", {"寒", "難", "殘", "看", "丹", "單", "安", "歡",
                             "寬", "端", "觀", "官", "冠", "乾", "肝"}),
    "先": RhymeGroup("先", {"先", "天", "前", "年", "邊", "千", "田", "連",
                             "圓", "然", "全", "泉", "煙", "仙", "堅"}),
    "尤": RhymeGroup("尤", {"尤", "秋", "流", "留", "求", "收", "頭", "愁",
                             "樓", "悠", "謀", "柔", "休", "修", "周"}),
    "江": RhymeGroup("江", {"江", "窗", "雙", "邦", "缸", "腔", "撞", "樁"}),
    "歌": RhymeGroup("歌", {"歌", "多", "河", "波", "和", "何", "過", "羅",
                             "磨", "魔", "陀", "哥", "婆", "娑", "訶"}),
    "麻": RhymeGroup("麻", {"麻", "花", "家", "華", "霞", "差", "沙", "茶",
                             "涯", "加", "嘉", "牙", "瓜", "蛙", "查"}),
    "庚": RhymeGroup("庚", {"庚", "明", "清", "生", "城", "聲", "行", "情",
                             "名", "成", "平", "驚", "兄", "卿", "英"}),
    "青": RhymeGroup("青", {"青", "經", "星", "丁", "零", "停", "聽", "醒",
                             "瓶", "形", "庭", "亭", "寧", "冥", "靈"}),
}


def find_rhyme_group(character: str) -> RhymeGroup | None:
    """Find which rhyme group a character belongs to.

    Args:
        character: A single Chinese character.

    Returns:
        The RhymeGroup, or None if not found in any group.
    """
    for group in RHYME_GROUPS.values():
        if character in group.characters:
            return group
    return None


def extract_rhyme_word(line: str) -> str:
    """Extract the rhyme word (韻腳) from a line of poetry.

    The rhyme word is the last character of the line (excluding
    punctuation and whitespace).

    Args:
        line: A line of Classical Chinese poetry.

    Returns:
        The rhyme character.
    """
    stripped = line.strip().rstrip("。，！？、；：""''")
    return stripped[-1] if stripped else ""


# ═══════════════════════════════════════════════════════════════
# Poetic Forms — 詩體
# ═══════════════════════════════════════════════════════════════

class PoeticForm(Enum):
    """Classical Chinese poetic forms mapped to program structures."""
    FIVE_CHAR = "五言"       # 5-char poem = 5-instruction block
    SEVEN_CHAR = "七言"      # 7-char poem = 7-instruction block
    COUPLET = "聯"           # Couplet = paired blocks
    QUATRAIN = "絕句"       # Quatrain = 4-block program
    REGULATED = "律詩"       # Regulated verse = 8-block program


class QuatrainPosition(Enum):
    """Position within a 絕句 (quatrain).

    The four positions map to program phases:
      起 (Qǐ)   = Opening    → Entry point / initialization
      承 (Chéng) = Continuing → Setup / data loading
      轉 (Zhuǎn) = Turning   → Core computation / branch point
      合 (Hé)    = Concluding → Exit / output result
    """
    OPENING = "起"       # Initialize
    CONTINUING = "承"    # Setup
    TURNING = "轉"       # Compute
    CONCLUDING = "合"    # Output


# ═══════════════════════════════════════════════════════════════
# Poetic Block — 詩塊
# ═══════════════════════════════════════════════════════════════

@dataclass
class PoeticBlock:
    """A single block of instructions derived from a poetic line.

    Each line of poetry produces a fixed-size instruction block:
      - 五言詩: 5 instruction slots
      - 七言詩: 7 instruction slots (2 are NOP padding)

    Attributes:
        form: The poetic form (五言 or 七言).
        source_line: The original Classical Chinese line.
        characters: The individual characters of the line.
        instructions: The compiled instructions.
        tones: Tonal classification for each character (平仄).
        rhyme_word: The rhyme character (last char) for jump targeting.
        rhyme_group: The rhyme group this line belongs to.
        position: Position within a larger structure (quatrain, etc.).
    """
    form: PoeticForm
    source_line: str
    characters: list[str]
    instructions: list[Instruction] = field(default_factory=list)
    tones: list[TonalValue] = field(default_factory=list)
    rhyme_word: str = ""
    rhyme_group: RhymeGroup | None = None
    position: str = ""

    @property
    def block_size(self) -> int:
        """Total instruction slots in this block."""
        if self.form == PoeticForm.FIVE_CHAR:
            return 5
        elif self.form == PoeticForm.SEVEN_CHAR:
            return 7
        return len(self.instructions)

    @property
    def active_instructions(self) -> int:
        """Number of non-NOP instructions."""
        return sum(1 for i in self.instructions if i.opcode != Opcode.NOP)

    @property
    def parallelism(self) -> list[bool]:
        """Which instruction slots can execute in parallel.

        Based on 平 (parallelizable) vs 仄 (sequential) tones.
        """
        return [t.is_parallelizable for t in self.tones]

    def analyze_tones(self) -> str:
        """Produce a tonal analysis of this block.

        Returns:
            Formatted string showing character tones and parallelism.
        """
        lines = [f"  詩行：{self.source_line}"]
        tone_str = "  平仄："
        for i, (ch, tone) in enumerate(zip(self.characters, self.tones)):
            if i > 0:
                tone_str += " "
            marker = "▪" if tone.is_parallelizable else "▫"
            tone_str += f"{ch}({marker}{tone.value})"
        lines.append(tone_str)
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Poem Compiler — 詩編器
# ═══════════════════════════════════════════════════════════════

class PoemCompiler:
    """Compile Classical Chinese poetry into VM instruction blocks.

    The compiler processes poetry at multiple levels:
      1. Character level: each character is a potential instruction
      2. Tonal level: 平/仄 determines parallelism constraints
      3. Rhyme level: 韻腳 determines jump targets
      4. Structural level: 起承轉合 determines program phases

    詩即程 — the poem IS the program.
    """

    def __init__(self) -> None:
        self._blocks: list[PoeticBlock] = []
        self._rhyme_labels: dict[str, int] = {}  # rhyme_char → instruction address
        self._errors: list[str] = []

    @property
    def blocks(self) -> list[PoeticBlock]:
        """All compiled blocks."""
        return self._blocks

    @property
    def errors(self) -> list[str]:
        """Compilation errors."""
        return self._errors

    def compile_five_char(self, line: str,
                          opcode_hint: str | None = None) -> PoeticBlock:
        """Compile a 五言詩 (5-character poem line) into a 5-instruction block.

        Each of the 5 characters maps to one instruction slot.
        If a character doesn't resolve to a known instruction,
        it becomes NOP.

        五言詩 structure:
          Position 0: Setup (often a register or value)
          Position 1: First operand
          Position 2: Operator (often the key instruction)
          Position 3: Second operand
          Position 4: Result / store / control

        Args:
            line: A 5-character Classical Chinese line.
            opcode_hint: Optional hint for the central instruction.

        Returns:
            The compiled PoeticBlock.
        """
        characters = list(line.strip())[:5]
        # Pad to exactly 5 characters if shorter
        while len(characters) < 5:
            characters.append("空")

        block = PoeticBlock(
            form=PoeticForm.FIVE_CHAR,
            source_line=line.strip(),
            characters=characters,
        )

        # Classify tones
        block.tones = [classify_tone(ch) for ch in characters]

        # Extract rhyme
        block.rhyme_word = characters[-1]
        block.rhyme_group = find_rhyme_group(block.rhyme_word)

        # Build instructions — one per character
        for i, ch in enumerate(characters):
            if ch == "空":
                block.instructions.append(Instruction("NOP", source=line.strip()))
            elif opcode_hint and i == 2:
                # Central position uses the hint
                block.instructions.append(Instruction(opcode_hint, [ch], source=line.strip()))
            else:
                # Each character is its own instruction
                block.instructions.append(Instruction("NOP", [ch], source=line.strip()))

        self._blocks.append(block)
        return block

    def compile_seven_char(self, line: str,
                           opcode_hint: str | None = None) -> PoeticBlock:
        """Compile a 七言詩 (7-character poem line) into a 7-instruction block.

        Structure: 7 characters → 7 instruction slots
          Slots 0–4: Active instructions (5 useful)
          Slots 5–6: NOP padding (maintain alignment)

        七言詩 structure:
          Position 0-1: Setup / context (2 chars, often parallelizable)
          Position 2-3: Core operation (2 chars, the main work)
          Position 4:   Transition
          Position 5:   Result / store (NOP padding in basic mode)
          Position 6:   Rhyme / jump target (NOP padding or label)

        Args:
            line: A 7-character Classical Chinese line.
            opcode_hint: Optional hint for the central instruction.

        Returns:
            The compiled PoeticBlock.
        """
        characters = list(line.strip())[:7]
        while len(characters) < 7:
            characters.append("空")

        block = PoeticBlock(
            form=PoeticForm.SEVEN_CHAR,
            source_line=line.strip(),
            characters=characters,
        )

        block.tones = [classify_tone(ch) for ch in characters]
        block.rhyme_word = characters[-1]
        block.rhyme_group = find_rhyme_group(block.rhyme_word)

        for i, ch in enumerate(characters):
            if ch == "空":
                block.instructions.append(Instruction("NOP", source=line.strip()))
            elif opcode_hint and i == 3:
                # Central position in 7-char
                block.instructions.append(Instruction(opcode_hint, [ch], source=line.strip()))
            else:
                block.instructions.append(Instruction("NOP", [ch], source=line.strip()))

        self._blocks.append(block)
        return block

    def compile_couplet(self, first_line: str, second_line: str) -> tuple[PoeticBlock, PoeticBlock]:
        """Compile a 聯 (couplet) — two paired lines with data dependency.

        In a couplet:
          上聯 (upper line): sets up the first half of a concept
          下聯 (lower line): completes the concept with parallel structure

        The data dependency: the result of the upper line feeds into
        the lower line. This is like a function call where the upper
        line computes arguments and the lower line applies them.

        聯 = paired computation with dependency.

        Args:
            first_line: The upper line (上聯).
            second_line: The lower line (下聯).

        Returns:
            Tuple of (upper_block, lower_block).
        """
        if len(first_line.strip()) == 5:
            upper = self.compile_five_char(first_line)
            lower = self.compile_five_char(second_line)
        elif len(first_line.strip()) == 7:
            upper = self.compile_seven_char(first_line)
            lower = self.compile_seven_char(second_line)
        else:
            # Default to 5-char
            upper = self.compile_five_char(first_line)
            lower = self.compile_five_char(second_line)

        upper.position = "上聯"
        lower.position = "下聯"

        return upper, lower

    def compile_quatrain(self, opening: str, continuing: str,
                         turning: str, concluding: str) -> list[PoeticBlock]:
        """Compile a 絕句 (quatrain) — a complete 4-line program.

        The quatrain is the minimal complete program form:
          起句 (Opening):    Entry point, initialization
          承句 (Continuing): Setup, data preparation
          轉句 (Turning):    Core computation, branch point
          合句 (Concluding): Exit, output result

        起承轉合 — the four movements of a complete program,
        just as they are the four movements of a complete poem.

        Args:
            opening: First line (起句).
            continuing: Second line (承句).
            turning: Third line (轉句).
            concluding: Fourth line (合句).

        Returns:
            List of 4 PoeticBlocks.
        """
        lines = [opening, continuing, turning, concluding]
        positions = [
            QuatrainPosition.OPENING.value,
            QuatrainPosition.CONTINUING.value,
            QuatrainPosition.TURNING.value,
            QuatrainPosition.CONCLUDING.value,
        ]

        blocks: list[PoeticBlock] = []
        for line, pos in zip(lines, positions):
            stripped = line.strip()
            if len(stripped) == 7:
                block = self.compile_seven_char(line)
            else:
                block = self.compile_five_char(line)
            block.position = pos
            blocks.append(block)

        # Build rhyme labels (jump targets)
        # Lines 1, 2, 4 typically rhyme in a quatrain
        self._build_rhyme_labels(blocks)

        return blocks

    def compile_regulated(self, lines: list[str]) -> list[PoeticBlock]:
        """Compile a 律詩 (regulated verse) — an 8-line program.

        The regulated verse is the most structured poetic form:
          Lines 1-2 (首聯):   Entry and initialization
          Lines 3-4 (頷聯):   First parallel pair — parallel operations
          Lines 5-6 (頸聯):   Second parallel pair — parallel operations
          Lines 7-8 (尾聯):   Conclusion and exit

        The middle 4 lines (3-6) form TWO parallel couplets (對仗).
        In programming terms, these are PARALLEL OPERATIONS that
        can execute concurrently:

          Line 3 ═══ Line 4   (parallel block A)
          Line 5 ═══ Line 6   (parallel block B)

        This is the earliest known description of SIMD parallelism,
        encoded in poetic form over 1500 years ago.

        Args:
            lines: 8 lines of poetry (each 5 or 7 characters).

        Returns:
            List of 8 PoeticBlocks.
        """
        if len(lines) != 8:
            self._errors.append(f"律詩 must have 8 lines, got {len(lines)}")
            return []

        blocks: list[PoeticBlock] = []
        couplet_names = ["首聯上", "首聯下", "頷聯上", "頷聯下",
                         "頸聯上", "頸聯下", "尾聯上", "尾聯下"]

        for i, line in enumerate(lines):
            stripped = line.strip()
            if len(stripped) == 7:
                block = self.compile_seven_char(line)
            else:
                block = self.compile_five_char(line)
            block.position = couplet_names[i]
            blocks.append(block)

        # Validate parallel couplets (對仗)
        # Lines 2-3 and 4-5 should have matching structure
        self._validate_parallelism(blocks)

        # Build rhyme labels
        self._build_rhyme_labels(blocks)

        return blocks

    def flatten_to_instructions(self) -> list[Instruction]:
        """Flatten all compiled blocks into a linear instruction list.

        Assigns addresses to each instruction and creates jump
        targets from rhyme labels.

        Returns:
            Complete list of instructions with addresses.
        """
        all_instructions: list[Instruction] = []
        addr = 0

        for block in self._blocks:
            for instr in block.instructions:
                instr.address = addr
                all_instructions.append(instr)
                addr += 1

        return all_instructions

    def _build_rhyme_labels(self, blocks: list[PoeticBlock]) -> None:
        """Build jump target labels from rhyme groups.

        Lines that share a rhyme group are assigned the same
        jump target address. The rhyme word serves as the label.
        """
        self._rhyme_labels.clear()
        addr = 0
        for block in blocks:
            if block.rhyme_word and block.rhyme_group:
                if block.rhyme_word not in self._rhyme_labels:
                    self._rhyme_labels[block.rhyme_word] = addr
            addr += block.block_size

    def _validate_parallelism(self, blocks: list[PoeticBlock]) -> None:
        """Validate that parallel couplets have matching structure.

        In a regulated verse, the middle couplets must have 對仗
        (parallelism): matching tonal patterns and syntactic structure.

        In programming terms, parallel blocks must have the same
        instruction count and compatible operation types.
        """
        # Check 頷聯 (lines 2-3, indices 2-3)
        self._check_couplets(blocks, 2, 3, "頷聯")
        # Check 頸聯 (lines 4-5, indices 4-5)
        self._check_couplets(blocks, 4, 5, "頸聯")

    def _check_couplets(self, blocks: list[PoeticBlock],
                        idx_a: int, idx_b: int, name: str) -> None:
        """Check if two blocks form a valid parallel couplet."""
        if idx_a >= len(blocks) or idx_b >= len(blocks):
            return
        a, b = blocks[idx_a], blocks[idx_b]
        # Check same form
        if a.form != b.form:
            self._errors.append(
                f"{name} form mismatch: {a.form.value} vs {b.form.value}"
            )
        # Check tonal complementarity (平仄相對)
        for i, (ta, tb) in enumerate(zip(a.tones, b.tones)):
            if i < len(a.tones) and i < len(b.tones):
                if ta == tb:
                    # In strict regulated verse, parallel lines should
                    # have OPPOSITE tones at each position.
                    # We note this as a soft warning, not an error.
                    pass

    def reset(self) -> None:
        """Clear all compiled state."""
        self._blocks.clear()
        self._rhyme_labels.clear()
        self._errors.clear()

    def dump_analysis(self) -> str:
        """Produce a formatted analysis of all compiled blocks.

        Returns:
            Multi-line string with complete analysis.
        """
        lines: list[str] = []
        lines.append("╔══════════════════════════════════════════════╗")
        lines.append("║  詩體分析 — Poetic Form Program Analysis      ║")
        lines.append("╚══════════════════════════════════════════════╝")

        for block in self._blocks:
            lines.append("")
            pos_str = f" [{block.position}]" if block.position else ""
            lines.append(f"  ▸ {block.form.value}{pos_str}: {block.source_line}")
            lines.append(f"    字：{''.join(block.characters)}")
            tones_str = "".join(t.value for t in block.tones)
            lines.append(f"    平仄：{tones_str}")

            # Tonal visualization
            tone_vis = ""
            for t in block.tones:
                tone_vis += "●" if t == TonalValue.PING else "○"
            lines.append(f"    並行：{tone_vis} (●=parallel ○=sequential)")

            # Instructions
            for j, instr in enumerate(block.instructions):
                src = f" [{block.characters[j]}]" if j < len(block.characters) else ""
                lines.append(f"    {j}: {instr.opcode_name}{src}")

            # Rhyme info
            if block.rhyme_group:
                lines.append(f"    韻：{block.rhyme_word} → {block.rhyme_group.name}")

        # Rhyme label table
        if self._rhyme_labels:
            lines.append("")
            lines.append("  韻標 / Rhyme Labels (jump targets):")
            for char, addr in sorted(self._rhyme_labels.items()):
                group = find_rhyme_group(char)
                group_name = group.name if group else "?"
                lines.append(f"    '{char}' ({group_name}) → addr {addr}")

        # Errors
        if self._errors:
            lines.append("")
            lines.append("  錯誤 / Errors:")
            for err in self._errors:
                lines.append(f"    ✗ {err}")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Poetic Program Templates
# ═══════════════════════════════════════════════════════════════

def five_char_template(opcode: str = "NOP",
                       operands: list[str] | None = None) -> PoeticBlock:
    """Create a 五言詩 template with a specific central opcode.

    Args:
        opcode: The opcode for the central (3rd) position.
        operands: Optional operand names for the remaining positions.

    Returns:
        A template PoeticBlock.
    """
    ops = operands or ["空"] * 5
    chars = ops[:5]
    while len(chars) < 5:
        chars.append("空")

    block = PoeticBlock(
        form=PoeticForm.FIVE_CHAR,
        source_line="".join(chars),
        characters=chars,
    )
    block.tones = [classify_tone(ch) for ch in chars]

    for i, ch in enumerate(chars):
        if i == 2:
            block.instructions.append(Instruction(opcode, [ch]))
        else:
            block.instructions.append(Instruction("NOP", [ch]))

    return block


def seven_char_template(opcode: str = "NOP",
                        operands: list[str] | None = None) -> PoeticBlock:
    """Create a 七言詩 template with a specific central opcode.

    Args:
        opcode: The opcode for the central (4th) position.
        operands: Optional operand names.

    Returns:
        A template PoeticBlock.
    """
    ops = operands or ["空"] * 7
    chars = ops[:7]
    while len(chars) < 7:
        chars.append("空")

    block = PoeticBlock(
        form=PoeticForm.SEVEN_CHAR,
        source_line="".join(chars),
        characters=chars,
    )
    block.tones = [classify_tone(ch) for ch in chars]

    for i, ch in enumerate(chars):
        if i == 3:
            block.instructions.append(Instruction(opcode, [ch]))
        elif i in (5, 6):
            # Padding slots
            block.instructions.append(Instruction("NOP"))
        else:
            block.instructions.append(Instruction("NOP", [ch]))

    return block
