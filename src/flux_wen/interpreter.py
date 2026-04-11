"""
文言解释器 — Classical Chinese FLUX Interpreter

Character-level tokenization: each character is one conceptual token.
Patterns map classical Chinese expressions to VM instructions.

Core principle: 四字成程 — a complete program in four characters.
加三于四 → IADD(3, 4) → result 7
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .context import (
    ContextDomain,
    ContextStack,
    ContextFrame,
    parse_chinese_number,
)


# ═══════════════════════════════════════════════════════════════
# VM Instructions — all instructions the interpreter can emit
# ═══════════════════════════════════════════════════════════════

@dataclass
class Instruction:
    """A single VM instruction."""
    opcode: str
    operands: list[Any] = field(default_factory=list)
    source: str = ""          # original classical Chinese source line
    line_no: int = 0

    def __repr__(self) -> str:
        ops = ", ".join(str(o) for o in self.operands)
        return f"{self.opcode}({ops})"


# ═══════════════════════════════════════════════════════════════
# Pattern definitions — classical Chinese → instruction mappings
# ═══════════════════════════════════════════════════════════════

# Each pattern: (compiled_regex, instruction_builder)
# The regex uses named groups to extract operands.

def _build_patterns() -> list[tuple[re.Pattern[str], Any]]:
    """Build all interpretation patterns.

    Order matters: more specific patterns must come first.
    This is the grammar of 文言编程 — except it's not grammar,
    it's pattern recognition in a grammarless language.
    """
    patterns = []

    # ── Arithmetic ────────────────────────────────────────────

    # 加 $a 于 $b → IADD a, b
    # "add a to b" — classical Chinese preposition 于 marks the target
    patterns.append((
        re.compile(r"加\s*(.+?)\s*于\s*(.+)"),
        lambda m: Instruction("IADD", [m.group(1), m.group(2)]),
    ))

    # 减 $a 于 $b → ISUB a, b  (subtract a from b)
    patterns.append((
        re.compile(r"减\s*(.+?)\s*于\s*(.+)"),
        lambda m: Instruction("ISUB", [m.group(1), m.group(2)]),
    ))

    # $a 加 $b → IADD a, b  (simpler word-order variant)
    patterns.append((
        re.compile(r"^(.+?)\s*加\s*(.+)$"),
        lambda m: _maybe_arithmetic_add(m),
    ))

    # $a 减 $b → ISUB a, b  (simpler word-order variant)
    patterns.append((
        re.compile(r"^(.+?)\s*减\s*(.+)$"),
        lambda m: Instruction("ISUB", [m.group(1), m.group(2)]),
    ))

    # $a 乘 $b → IMUL a, b
    patterns.append((
        re.compile(r"^(.+?)\s*乘\s*(.+)$"),
        lambda m: _maybe_arithmetic_mul(m),
    ))

    # $a 除 $b → IDIV a, b
    patterns.append((
        re.compile(r"^(.+?)\s*除(?:以)?\s*(.+)$"),
        lambda m: Instruction("IDIV", [m.group(1), m.group(2)]),
    ))

    # $a 至 $b 合 → RANGE_SUM a, b (sum from a to b)
    patterns.append((
        re.compile(r"(.+?)\s*至\s*(.+?)\s*合"),
        lambda m: Instruction("RANGE_SUM", [m.group(1), m.group(2)]),
    ))

    # ── Register / assignment ─────────────────────────────────

    # 以 R$n 为 $v → MOVI Rn, v  (take register n as value v)
    patterns.append((
        re.compile(r"以\s*R(\d+)\s*为\s*(.+)"),
        lambda m: Instruction("MOVI", [int(m.group(1)), m.group(2).strip()]),
    ))

    # 以 $v 为 R$n → MOVI Rn, v  (reverse form)
    patterns.append((
        re.compile(r"以\s*(.+?)\s*为\s*R(\d+)"),
        lambda m: Instruction("MOVI", [int(m.group(2)), m.group(1).strip()]),
    ))

    # R$n 与 R$m 合 → IADD Rn, Rm
    patterns.append((
        re.compile(r"R(\d+)\s*与\s*R(\d+)\s*合"),
        lambda m: Instruction("IADD", [f"R{m.group(1)}", f"R{m.group(2)}"]),
    ))

    # R$n 与 R$m 乘 → IMUL Rn, Rm
    patterns.append((
        re.compile(r"R(\d+)\s*与\s*R(\d+)\s*乘"),
        lambda m: Instruction("IMUL", [f"R{m.group(1)}", f"R{m.group(2)}"]),
    ))

    # 归 R$v → RET v (set R0 and return)
    patterns.append((
        re.compile(r"归\s*R(\d+)"),
        lambda m: Instruction("RET", [f"R{m.group(1)}"]),
    ))

    # 归 $v → RET with value
    patterns.append((
        re.compile(r"归\s*(.+)"),
        lambda m: Instruction("RET", [m.group(1).strip()]),
    ))

    # ── Control flow ──────────────────────────────────────────

    # 当 R$n 非零 → WHILENZ Rn (while register n not zero)
    patterns.append((
        re.compile(r"当\s*R(\d+)\s*非零"),
        lambda m: Instruction("WHILENZ", [int(m.group(1))]),
    ))

    # 若 R$n 为 $cond → COND Rn, condition
    patterns.append((
        re.compile(r"若\s*R(\d+)\s*为\s*(.+)"),
        lambda m: Instruction("COND", [int(m.group(1)), m.group(2).strip()]),
    ))

    # 止 → HALT
    patterns.append((
        re.compile(r"^止$"),
        lambda m: Instruction("HALT"),
    ))

    # ── Agent communication ───────────────────────────────────

    # 告 $agent $msg → TELL agent, msg
    patterns.append((
        re.compile(r"告\s*(\S+)\s+(.+)"),
        lambda m: Instruction("TELL", [m.group(1), m.group(2).strip()]),
    ))

    # 问 $agent $topic → ASK agent, topic
    patterns.append((
        re.compile(r"问\s*(\S+)\s+(.+)"),
        lambda m: Instruction("ASK", [m.group(1), m.group(2).strip()]),
    ))

    # 遍告 $msg → BROADCAST msg
    patterns.append((
        re.compile(r"遍告\s*(.+)"),
        lambda m: Instruction("BROADCAST", [m.group(1).strip()]),
    ))

    # ── Confucian operations ──────────────────────────────────

    # 仁 $target → DISTRIBUTE (benevolence = distribute)
    patterns.append((
        re.compile(r"仁\s*(.+)"),
        lambda m: Instruction("DISTRIBUTE", [m.group(1).strip()]),
    ))

    # 义 $target → VALIDATE (righteousness = validate)
    patterns.append((
        re.compile(r"义\s*(.+)"),
        lambda m: Instruction("VALIDATE", [m.group(1).strip()]),
    ))

    # 礼 $target → ORCHESTRATE (ritual = orchestrate)
    patterns.append((
        re.compile(r"礼\s*(.+)"),
        lambda m: Instruction("ORCHESTRATE", [m.group(1).strip()]),
    ))

    # 智 $target → OPTIMIZE (wisdom = optimize)
    patterns.append((
        re.compile(r"智\s*(.+)"),
        lambda m: Instruction("OPTIMIZE", [m.group(1).strip()]),
    ))

    # 信 $target → VERIFY (trust = verify)
    patterns.append((
        re.compile(r"信\s*(.+)"),
        lambda m: Instruction("VERIFY", [m.group(1).strip()]),
    ))

    # ── Military / strategy operations ────────────────────────

    # 攻 $target → ATTACK
    patterns.append((
        re.compile(r"攻\s*(.+)"),
        lambda m: Instruction("ATTACK", [m.group(1).strip()]),
    ))

    # 守 $target → DEFEND
    patterns.append((
        re.compile(r"守\s*(.+)"),
        lambda m: Instruction("DEFEND", [m.group(1).strip()]),
    ))

    # 退 → WITHDRAW
    patterns.append((
        re.compile(r"^退$"),
        lambda m: Instruction("WITHDRAW"),
    ))

    # 进 $target → ADVANCE
    patterns.append((
        re.compile(r"进\s*(.+)"),
        lambda m: Instruction("ADVANCE", [m.group(1).strip()]),
    ))

    # ── NOP / comment ────────────────────────────────────────

    # 注: $text → NOP (comment)
    patterns.append((
        re.compile(r"注[：:]\s*(.*)"),
        lambda m: Instruction("NOP", [m.group(1).strip()]),
    ))

    return patterns


def _maybe_arithmetic_add(m: re.Match[str]) -> Instruction:
    """Heuristic: if both sides of 加 are numbers/registers, it's IADD."""
    left, right = m.group(1).strip(), m.group(2).strip()
    # Don't match if left looks like a domain keyword
    if left in ("仁", "义", "礼", "智", "信"):
        return Instruction("NOP", [m.group(0)])
    return Instruction("IADD", [left, right])


def _maybe_arithmetic_mul(m: re.Match[str]) -> Instruction:
    """Heuristic: if both sides of 乘 are numbers/registers, it's IMUL."""
    left, right = m.group(1).strip(), m.group(2).strip()
    if left in ("以", "当", "若", "告", "问"):
        return Instruction("NOP", [m.group(0)])
    return Instruction("IMUL", [left, right])


# ═══════════════════════════════════════════════════════════════
# Tokenizer — character-level tokenization
# ═══════════════════════════════════════════════════════════════

@dataclass
class Token:
    """A single character token."""
    char: str
    position: int
    category: str  # "number", "register", "operator", "keyword", "text"


def tokenize(source: str) -> list[Token]:
    """Tokenize classical Chinese source at the character level.

    Each character is examined individually. We identify:
    - Classical numerals: 一二三四五六七八九十百千万
    - Register references: R followed by digit
    - Known operators: 加减乘除于与为以合归当若告问遍止仁义礼智信攻守退进
    - All other characters: text tokens

    The key insight: in 文言, spaces are OPTIONAL.
    字即词 — the character IS the word.
    """
    tokens: list[Token] = []
    i = 0
    source = source.strip()

    while i < len(source):
        ch = source[i]

        # Skip whitespace (文言 has no spaces, but we tolerate them)
        if ch.isspace():
            i += 1
            continue

        # Register: R0, R1, etc.
        if ch == 'R' and i + 1 < len(source) and source[i + 1].isdigit():
            reg_num = ""
            j = i + 1
            while j < len(source) and source[j].isdigit():
                reg_num += source[j]
                j += 1
            tokens.append(Token(f"R{reg_num}", i, "register"))
            i = j
            continue

        # Determine category
        if ch in "一二三四五六七八九〇零壹贰叁肆伍陆柒捌玖拾百千万亿兆兩佰仟":
            category = "number"
        elif ch in "加减乘除":
            category = "operator"
        elif ch in "于与为以合归当若告问遍止仁义礼智信攻守退进注":
            category = "keyword"
        elif ch.isdigit():
            category = "number"
        else:
            category = "text"

        tokens.append(Token(ch, i, category))
        i += 1

    return tokens


def tokens_to_string(tokens: list[Token]) -> str:
    """Reconstruct source from tokens (strips whitespace)."""
    return "".join(t.char for t in tokens)


# ═══════════════════════════════════════════════════════════════
# Resolver — resolve operand values from registers / literals
# ═══════════════════════════════════════════════════════════════

def resolve_operand(operand: Any, ctx: ContextStack) -> Any:
    """Resolve an operand to its concrete value.

    - Register references (R0, R1...) → register value
    - Classical Chinese numerals → integer
    - Arabic digits → integer
    - Anything else → returned as-is (string)
    """
    if isinstance(operand, (int, float)):
        return operand

    s = str(operand).strip()

    # Register reference
    register_match = re.match(r"^R(\d+)$", s)
    if register_match:
        return ctx.get_register(int(register_match.group(1)))

    # Arabic numeral
    try:
        return int(s)
    except ValueError:
        pass

    # Classical Chinese numeral
    cn = parse_chinese_number(s)
    if cn is not None:
        return cn

    return s


# ═══════════════════════════════════════════════════════════════
# Interpreter — the core engine
# ═══════════════════════════════════════════════════════════════

class WenyanInterpreter:
    """Classical Chinese FLUX interpreter.

    Executes 文言 programs by:
    1. Tokenizing at character level (字即词)
    2. Matching patterns against source lines
    3. Resolving operands through context
    4. Executing VM instructions against register machine

    No grammar. No syntax tree. Pure pattern → action.
    以文意定義 — meaning determined by textual intent.
    """

    def __init__(self) -> None:
        self.context = ContextStack()
        self.patterns = _build_patterns()
        self.program: list[Instruction] = []
        self.log: list[str] = []
        self.running = False

    # ── Compilation ───────────────────────────────────────────

    def compile(self, source: str) -> list[Instruction]:
        """Compile classical Chinese source into instructions.

        Each source line is matched against patterns.
        If no pattern matches, the line is recorded as NOP with a warning.
        """
        self.program = []
        lines = source.strip().split("\n")

        for line_no, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Skip pure whitespace
            if not line.strip():
                continue

            matched = False
            for pattern, builder in self.patterns:
                m = pattern.match(line)
                if m:
                    instr = builder(m)
                    instr.source = line
                    instr.line_no = line_no
                    self.program.append(instr)
                    matched = True
                    break

            if not matched:
                # Try to treat as a simple 4-character expression
                simple = self._try_simple_expression(line)
                if simple:
                    simple.source = line
                    simple.line_no = line_no
                    self.program.append(simple)
                else:
                    nop = Instruction("NOP", [line])
                    nop.source = line
                    nop.line_no = line_no
                    self.program.append(nop)
                    self.log.append(f"行{line_no}: 未识「{line}」")

        return self.program

    def _try_simple_expression(self, line: str) -> Instruction | None:
        """Try to interpret a line as a simple expression.

        Handles ultra-concise forms like:
        - 纯数字: "七" → MOVI R0, 7
        - Single register: "R0" → NOP (reference)
        """
        tokens = tokenize(line)
        if len(tokens) == 0:
            return None

        # Pure number → set R0
        if all(t.category == "number" for t in tokens):
            num = parse_chinese_number(tokens_to_string(tokens))
            if num is not None:
                return Instruction("MOVI", [0, num])

        return None

    # ── Execution ─────────────────────────────────────────────

    def run(self, source: str | None = None) -> Any:
        """Execute a classical Chinese program.

        If source is provided, compiles first.
        Returns the value of R0 after execution.
        """
        if source is not None:
            self.compile(source)

        self.running = True
        self.log = []
        pc = 0

        while self.running and pc < len(self.program):
            instr = self.program[pc]
            self._execute_one(instr)
            pc += 1

        return self.context.get_register(0)

    def step(self) -> Instruction | None:
        """Execute one instruction from pre-compiled program.

        Returns the executed instruction, or None if program ended.
        """
        if not self.program:
            return None

        if self._pc >= len(self.program):
            return None

        instr = self.program[self._pc]
        self._execute_one(instr)
        self._pc += 1
        return instr

    def _execute_one(self, instr: Instruction) -> None:
        """Execute a single instruction against the VM state."""
        ctx = self.context

        match instr.opcode:
            case "MOVI":
                reg_idx, val = instr.operands[0], instr.operands[1]
                resolved = resolve_operand(val, ctx)
                ctx.set_register(reg_idx, resolved)

            case "IADD":
                a = resolve_operand(instr.operands[0], ctx)
                b = resolve_operand(instr.operands[1], ctx)
                # If operands are register indices (ints from pattern),
                # we already resolved them to values
                result = int(a) + int(b)
                ctx.set_register(0, result)
                self.log.append(f"加: {a} + {b} = {result}")

            case "ISUB":
                a = resolve_operand(instr.operands[0], ctx)
                b = resolve_operand(instr.operands[1], ctx)
                result = int(a) - int(b)
                ctx.set_register(0, result)
                self.log.append(f"减: {a} - {b} = {result}")

            case "IMUL":
                a = resolve_operand(instr.operands[0], ctx)
                b = resolve_operand(instr.operands[1], ctx)
                result = int(a) * int(b)
                ctx.set_register(0, result)
                self.log.append(f"乘: {a} × {b} = {result}")

            case "IDIV":
                a = resolve_operand(instr.operands[0], ctx)
                b = resolve_operand(instr.operands[1], ctx)
                if int(b) == 0:
                    self.log.append("除: 错 — 除以零")
                    return
                result = int(a) // int(b)
                ctx.set_register(0, result)
                self.log.append(f"除: {a} ÷ {b} = {result}")

            case "RANGE_SUM":
                a = resolve_operand(instr.operands[0], ctx)
                b = resolve_operand(instr.operands[1], ctx)
                result = sum(range(int(a), int(b) + 1))
                ctx.set_register(0, result)
                self.log.append(f"合: {a} 至 {b} = {result}")

            case "WHILENZ":
                reg_idx = instr.operands[0]
                val = ctx.get_register(reg_idx)
                if val == 0:
                    # Skip to matching止 or end of block
                    self.log.append(f"当 R{reg_idx} = 0, 止")

            case "COND":
                reg_idx = instr.operands[0]
                cond = instr.operands[1]
                val = ctx.get_register(reg_idx)
                self.log.append(f"若 R{reg_idx} = {val}, 条件: {cond}")

            case "RET":
                val = resolve_operand(instr.operands[0], ctx)
                ctx.set_register(0, val)
                self.log.append(f"归: R0 = {val}")
                self.running = False

            case "HALT":
                self.running = False
                self.log.append("止")

            case "TELL":
                agent, msg = instr.operands[0], instr.operands[1]
                self.log.append(f"告 {agent}: {msg}")

            case "ASK":
                agent, topic = instr.operands[0], instr.operands[1]
                self.log.append(f"问 {agent}: {topic}")

            case "BROADCAST":
                msg = instr.operands[0]
                self.log.append(f"遍告: {msg}")

            # Confucian operations
            case "DISTRIBUTE":
                target = instr.operands[0]
                self.log.append(f"仁 — 分布: {target}")

            case "VALIDATE":
                target = instr.operands[0]
                self.log.append(f"义 — 验证: {target}")

            case "ORCHESTRATE":
                target = instr.operands[0]
                self.log.append(f"礼 — 编排: {target}")

            case "OPTIMIZE":
                target = instr.operands[0]
                self.log.append(f"智 — 优化: {target}")

            case "VERIFY":
                target = instr.operands[0]
                self.log.append(f"信 — 核实: {target}")

            # Military operations
            case "ATTACK":
                target = instr.operands[0]
                self.log.append(f"攻: {target}")

            case "DEFEND":
                target = instr.operands[0]
                self.log.append(f"守: {target}")

            case "WITHDRAW":
                self.log.append("退")

            case "ADVANCE":
                target = instr.operands[0]
                self.log.append(f"进: {target}")

            case "NOP":
                pass

            case _:
                self.log.append(f"未知指令: {instr.opcode}")

    def reset(self) -> None:
        """Reset VM state."""
        self.context = ContextStack()
        self.program = []
        self.log = []
        self.running = False
        self._pc = 0

    # ── Inspection ────────────────────────────────────────────

    def registers(self) -> dict[str, int]:
        """Return current register state."""
        result = {}
        for i in range(8):
            val = self.context.get_register(i)
            if val != 0:
                result[f"R{i}"] = val
        return result

    def disassemble(self) -> list[str]:
        """Return human-readable disassembly of compiled program."""
        lines = []
        for i, instr in enumerate(self.program):
            source_comment = f"  ; {instr.source}" if instr.source else ""
            lines.append(f"{i:03d}: {instr.opcode} {', '.join(str(o) for o in instr.operands)}{source_comment}")
        return lines
