"""
虛機 — Virtual Machine with Context-Domain Dispatch

A 64-register virtual machine where each register is identified by a
hexagram from the I Ching (易經). The VM executes FLUX opcodes with
context-domain aware dispatch: the SAME opcode produces different behavior
depending on the active textual domain (from 文境 context.py).

以文意定義 — meaning determined by textual intent.
以境定行 — behavior determined by context.

Register Architecture (六十四卦寄存器):
  R0  乾 (Qián)    Heaven         — Accumulator / return value
  R1  坤 (Kūn)     Earth          — Base pointer / data store
  R2  屯 (Zhūn)    Difficulty     — Stack pointer
  R3  蒙 (Méng)    Youthful Folly — Instruction pointer
  R4  需 (Xū)      Waiting        — Condition register
  R5  訟 (Sòng)    Conflict       — Comparison result
  R6  師 (Shī)     Army           — Loop counter
  R7  比 (Bǐ)      Holding        — Index register
  ...
  R62 中孚         Inner Truth    — Trust state
  R63 主題 (Zhǔtí) Topic          — Topic register (zero-anaphora)

The Topic Register (R63 主題寄存器):
  In Classical Chinese, the topic of discourse is implicit — carried by
  context rather than explicit pronouns. R63 holds the current "topic"
  (implicit subject/object). Operations on R63 resolve zero-anaphora
  by using the current topic value. 零形回指 (zero anaphora resolution).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable

from .context import (
    ContextDomain,
    ContextStack,
    parse_chinese_number,
    CNUMERALS,
)
from .iching import (
    Hexagram,
    Trigram,
    name_to_hexagram,
    king_wen_to_hexagram,
    address_to_hexagram,
    HEXAGRAMS_KING_WEN,
)


# ═══════════════════════════════════════════════════════════════
# Opcodes — 指令集 (Zhǐlìngjí)
# ═══════════════════════════════════════════════════════════════

class Opcode(IntEnum):
    """FLUX instruction set — complete opcode enumeration.

    All opcodes the VM can execute. Opcodes are context-domain aware:
    the same opcode may produce different side effects depending on
    the active domain in the context stack.
    """
    # ── Core operations ────────────────────────────────────────
    NOP          = 0x00   # 無 — No operation
    MOV          = 0x01   # 移 — Move between registers
    LOAD         = 0x02   # 載 — Load from memory
    STORE        = 0x03   # 存 — Store to memory
    JMP          = 0x04   # 跳 — Unconditional jump
    JZ           = 0x05   # 若零 — Jump if zero
    JNZ          = 0x06   # 若非零 — Jump if not zero
    CALL         = 0x07   # 呼 — Call subroutine
    RET          = 0x08   # 歸 — Return from subroutine
    HALT         = 0x09   # 終 — Halt execution
    PRINT        = 0x0A   # 示 — Print / display

    # ── Integer arithmetic ─────────────────────────────────────
    IADD         = 0x10   # 加 — Integer add
    ISUB         = 0x11   # 減 — Integer subtract
    IMUL         = 0x12   # 乘 — Integer multiply
    IDIV         = 0x13   # 除 — Integer divide
    IMOD         = 0x14   # 餘 — Integer modulo
    INEG         = 0x15   # 負 — Integer negate
    INC          = 0x16   # 增 — Increment
    DEC          = 0x17   # 減一 — Decrement
    IEQ          = 0x18   # 等於 — Integer equal
    IGT          = 0x19   # 大於 — Integer greater than
    ILT          = 0x1A   # 小於 — Integer less than
    ICMP         = 0x1B   # 比 — Compare (sets flags)

    # ── Stack operations ───────────────────────────────────────
    PUSH         = 0x20   # 壓 — Push onto stack
    POP          = 0x21   # 彈 — Pop from stack
    MOVI         = 0x22   # 設 — Move immediate value

    # ── Branch / conditional ───────────────────────────────────
    JE           = 0x30   # 若等 — Jump if equal
    JNE          = 0x31   # 若不等 — Jump if not equal

    # ── Agent communication ────────────────────────────────────
    TELL         = 0x40   # 告 — Tell agent (send message)
    ASK          = 0x41   # 問 — Ask agent (query)
    DELEGATE     = 0x42   # 命 — Delegate task to agent
    BROADCAST    = 0x43   # 令 — Broadcast to all agents

    # ── Trust & capability system ──────────────────────────────
    TRUST_CHECK  = 0x50   # 審信 — Verify trust relationship
    CAP_REQUIRE  = 0x51   # 求能 — Require capability

    # ── Domain-specific extensions ─────────────────────────────
    # Mathematical (算)
    IEXP         = 0x60   # 冪 — Exponentiation
    IROOT        = 0x61   # 根 — Square root

    # Confucian (儒) — 五常 operations
    VERIFY_TRUST = 0x70   # 信 — Verify trust / integrity
    CHECK_BOUNDS = 0x71   # 義 — Check bounds / validate
    OPTIMIZE     = 0x72   # 智 — Optimize execution path

    # Military (兵)
    ATTACK       = 0x80   # 攻 — Attack / push data
    DEFEND       = 0x81   # 守 — Defend / buffer data
    ADVANCE      = 0x82   # 進 — Advance / proceed
    RETREAT      = 0x83   # 退 — Retreat / backoff

    # Control (制)
    SEQUENCE     = 0x90   # 則 — Sequential execution
    LOOP         = 0x91   # 循 — Loop

    # ── I Ching operations ─────────────────────────────────────
    HEX_JUMP     = 0xA0   # 變卦 — Jump to hexagram address
    HEX_CALL     = 0xA1   # 卦呼 — Call hexagram subroutine
    TRIGRAM_ADDR = 0xA2   # 八卦址 — Trigram-based addressing

    # ── Topic register operations ──────────────────────────────
    SET_TOPIC    = 0xB0   # 定題 — Set topic register
    USE_TOPIC    = 0xB1   # 用題 — Use topic as implicit operand
    CLEAR_TOPIC  = 0xB2   # 清題 — Clear topic register


# Opcode name → Opcode enum lookup (case-insensitive)
OPCODE_MAP: dict[str, Opcode] = {op.name: op for op in Opcode}


# ═══════════════════════════════════════════════════════════════
# Register File — 六十四卦寄存器
# ═══════════════════════════════════════════════════════════════

# King Wen sequence → register index
# R0 = Hexagram #1 (乾), R1 = Hexagram #2 (坤), etc.
HEXAGRAM_REGISTER_NAMES: dict[str, int] = {}
HEXAGRAM_REGISTER_MNEMONICS: dict[int, str] = {}

for _i, _h in enumerate(HEXAGRAMS_KING_WEN):
    HEXAGRAM_REGISTER_NAMES[_h.name] = _i
    HEXAGRAM_REGISTER_MNEMONICS[_i] = _h.name

# Special register names
SPECIAL_REGISTERS: dict[str, int] = {
    "主題": 63,   # Topic register — R63
    "題": 63,     # Abbreviated topic
}

# Merge hexagram names with special names
ALL_REGISTER_NAMES: dict[str, int] = {**HEXAGRAM_REGISTER_NAMES, **SPECIAL_REGISTERS}

# Classical Chinese number system — extended
CHINESE_NUMBERS_EXTENDED: dict[str, int] = {
    **CNUMERALS,
    "億": 100_000_000,
    "亿": 100_000_000,
    "兆": 1_000_000_000_000,
    "京": 10_000_000_000_000_000,
    "垓": 10**20,
    "秭": 10**24,
    "穰": 10**28,
    "溝": 10**32,
    "澗": 10**36,
    "正": 10**40,
    "載": 10**44,
    "極": 10**48,
}


def resolve_register(name: str) -> int:
    """Resolve a register name to its index.

    Accepts:
      - Hexagram name: '乾' → 0, '坤' → 1, '既濟' → 62
      - 'R' prefix: 'R0' → 0, 'R63' → 63
      - Special names: '主題' → 63
      - Classical Chinese numerals for indices: '三' → 3

    Args:
        name: Register identifier.

    Returns:
        Register index (0–63).

    Raises:
        ValueError: If name cannot be resolved.
    """
    # Direct 'R' prefix
    if name.upper().startswith('R'):
        try:
            idx = int(name[1:])
            if 0 <= idx <= 63:
                return idx
        except ValueError:
            pass

    # Hexagram name or special name
    if name in ALL_REGISTER_NAMES:
        return ALL_REGISTER_NAMES[name]

    # Classical Chinese numeral
    cn_val = parse_chinese_number(name)
    if cn_val is not None and 0 <= cn_val <= 63:
        return cn_val

    raise ValueError(f"未知寄存器 / Unknown register: '{name}'")


def register_mnemonic(index: int) -> str:
    """Get the hexagram mnemonic for a register index.

    Args:
        index: Register index (0–63).

    Returns:
        Chinese hexagram name, or 'R{n}' for the topic register (63).
    """
    if index == 63:
        return "主題"
    return HEXAGRAM_REGISTER_MNEMONICS.get(index, f"R{index}")


# ═══════════════════════════════════════════════════════════════
# Instruction — 指令
# ═══════════════════════════════════════════════════════════════

@dataclass
class Instruction:
    """A single VM instruction with operands.

    Attributes:
        opcode: The operation to perform.
        operands: List of operands (register indices, immediates, strings).
        source: Original Classical Chinese source line (for disassembly).
        line_no: Source line number.
        address: Program counter address of this instruction.
    """
    opcode: str | Opcode
    operands: list[Any] = field(default_factory=list)
    source: str = ""
    line_no: int = 0
    address: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.opcode, str):
            upper = self.opcode.upper()
            if upper in OPCODE_MAP:
                self.opcode = OPCODE_MAP[upper]

    @property
    def opcode_name(self) -> str:
        if isinstance(self.opcode, Opcode):
            return self.opcode.name
        return str(self.opcode)

    def __repr__(self) -> str:
        ops = ", ".join(str(o) for o in self.operands)
        return f"{self.opcode_name}({ops})"


# ═══════════════════════════════════════════════════════════════
# Domain Dispatch Handlers
# ═══════════════════════════════════════════════════════════════

@dataclass
class DomainEffect:
    """Side effect produced by domain-aware opcode execution.

    When an opcode executes in a specific domain, it may produce
    additional effects beyond the basic operation.
    """
    domain: ContextDomain
    effect_type: str   # "log", "capability_check", "trust_verify", etc.
    message: str
    data: Any = None


class DomainDispatcher:
    """Dispatch table for context-domain aware opcode execution.

    同碼異行 — same opcode, different behavior, by domain.

    The dispatcher wraps each opcode execution with domain-specific
    pre/post hooks. For example:
      - In CONFUCIAN domain, IADD also performs a BOUNDS CHECK (義)
      - In MILITARY domain, IMUL computes STRATEGY (計)
      - In AGENT domain, PRINT becomes TELL (告)
    """

    def __init__(self) -> None:
        self._handlers: dict[tuple[Opcode, ContextDomain],
                             Callable[..., DomainEffect | None]] = {}
        self._register_defaults()

    def register(self, opcode: Opcode, domain: ContextDomain,
                 handler: Callable[..., DomainEffect | None]) -> None:
        """Register a domain-specific handler for an opcode."""
        self._handlers[(opcode, domain)] = handler

    def dispatch(self, opcode: Opcode, domain: ContextDomain,
                 **kwargs: Any) -> DomainEffect | None:
        """Execute domain-specific dispatch for an opcode.

        Returns a DomainEffect if there's a domain-specific side effect,
        or None if the opcode should execute with default behavior.
        """
        handler = self._handlers.get((opcode, domain))
        if handler:
            return handler(**kwargs)
        return None

    def _register_defaults(self) -> None:
        """Register built-in domain dispatch rules.

        These encode the fundamental insight of 文言编程:
        the same operation has different semantics in different
        textual domains.
        """

        # ── Mathematics domain (算) ────────────────────────────
        # In math domain, operations are pure computation.
        # No additional side effects — the default behavior IS
        # the math domain behavior.

        # ── Confucian domain (儒) ──────────────────────────────
        # Every operation in Confucian domain is filtered through
        # the Five Constants (五常: 仁義禮智信).

        def _confucian_iadd(**kw: Any) -> DomainEffect:
            """加 in Confucian domain: distribute with moderation (中庸)."""
            a, b = kw.get("a", 0), kw.get("b", 0)
            return DomainEffect(
                domain=ContextDomain.CONFUCIAN,
                effect_type="bounds_check",
                message=f"義：檢查界限 — {a} + {b} 合乎禮法",
            )

        def _confucian_imul(**kw: Any) -> DomainEffect:
            """乘 in Confucian domain: multiply with wisdom (智)."""
            a, b = kw.get("a", 0), kw.get("b", 0)
            return DomainEffect(
                domain=ContextDomain.CONFUCIAN,
                effect_type="optimize",
                message=f"智：尋優 — {a} × {b} 以最善之道",
            )

        def _confucian_imod(**kw: Any) -> DomainEffect:
            """餘 in Confucian domain: remainder implies fairness (均)."""
            return DomainEffect(
                domain=ContextDomain.CONFUCIAN,
                effect_type="distribute",
                message="仁：均分餘數 — benevolent distribution",
            )

        self.register(Opcode.IADD, ContextDomain.CONFUCIAN, _confucian_iadd)
        self.register(Opcode.IMUL, ContextDomain.CONFUCIAN, _confucian_imul)
        self.register(Opcode.IMOD, ContextDomain.CONFUCIAN, _confucian_imod)

        # ── Military domain (兵) ───────────────────────────────
        # Operations in military domain compute strategy.

        def _military_iadd(**kw: Any) -> DomainEffect:
            """加 in Military domain: reinforce troops (增兵)."""
            a, b = kw.get("a", 0), kw.get("b", 0)
            return DomainEffect(
                domain=ContextDomain.MILITARY,
                effect_type="strategy",
                message=f"計：增兵 — 合力 {a + b}",
            )

        def _military_imul(**kw: Any) -> DomainEffect:
            """乘 in Military domain: exploit weakness (乘虛)."""
            a, b = kw.get("a", 0), kw.get("b", 0)
            return DomainEffect(
                domain=ContextDomain.MILITARY,
                effect_type="strategy",
                message=f"計：乘虛 — 兵力 {a} × {b}",
            )

        def _military_isub(**kw: Any) -> DomainEffect:
            """減 in Military domain: attrition (消耗)."""
            a, b = kw.get("a", 0), kw.get("b", 0)
            return DomainEffect(
                domain=ContextDomain.MILITARY,
                effect_type="strategy",
                message=f"計：消耗 — 損失 {a} - {b}",
            )

        self.register(Opcode.IADD, ContextDomain.MILITARY, _military_iadd)
        self.register(Opcode.IMUL, ContextDomain.MILITARY, _military_imul)
        self.register(Opcode.ISUB, ContextDomain.MILITARY, _military_isub)

        # ── Agent domain (使) ──────────────────────────────────
        # Operations in agent domain affect agent communication.

        def _agent_print(**kw: Any) -> DomainEffect:
            """PRINT in Agent domain becomes TELL (告)."""
            msg = kw.get("value", "")
            return DomainEffect(
                domain=ContextDomain.AGENT,
                effect_type="tell",
                message=f"告：{msg}",
                data=msg,
            )

        self.register(Opcode.PRINT, ContextDomain.AGENT, _agent_print)

        # ── Control domain (制) ────────────────────────────────
        # Operations in control domain enforce execution constraints.

        def _control_iadd(**kw: Any) -> DomainEffect:
            """加 in Control domain: append to sequence (接續)."""
            return DomainEffect(
                domain=ContextDomain.CONTROL,
                effect_type="sequence",
                message="制：接續 — sequential append",
            )

        self.register(Opcode.IADD, ContextDomain.CONTROL, _control_iadd)


# ═══════════════════════════════════════════════════════════════
# Virtual Machine — 虛機 (Xūjī)
# ═══════════════════════════════════════════════════════════════

class FluxVM:
    """FLUX Virtual Machine — 64-register, context-domain aware.

    The VM maintains:
      - 64 general-purpose registers (R0–R63), named after hexagrams
      - A call stack for subroutine invocation
      - A data stack for PUSH/POP operations
      - A context stack (文境) for domain-aware dispatch
      - A program counter (PC) tracking execution position
      - A flag register for comparison results

    Memory Model:
      - Simple key-value store (simulating memory)
      - LOAD/STORE use integer addresses
      - No memory protection (trust is enforced via TRUST_CHECK)

    Execution Model:
      - Sequential instruction execution
      - Context-domain dispatch before each opcode
      - Side effects from domain dispatcher are logged
      - Topic register (R63) provides zero-anaphora resolution
    """

    NUM_REGISTERS: int = 64
    MAX_STACK_DEPTH: int = 1024
    MAX_CALL_DEPTH: int = 256

    def __init__(self) -> None:
        # Register file — all initialized to 0
        self._registers: list[int] = [0] * self.NUM_REGISTERS

        # Stacks
        self._stack: list[int] = []           # Data stack (PUSH/POP)
        self._call_stack: list[int] = []      # Return addresses (CALL/RET)

        # Program state
        self._program: list[Instruction] = []
        self._pc: int = 0                     # Program counter
        self._halted: bool = False
        self._flag: int = 0                   # Comparison flag: -1, 0, 1

        # Context and dispatch
        self.context = ContextStack()
        self.dispatcher = DomainDispatcher()

        # Memory (simple key-value)
        self._memory: dict[int, int] = {}

        # Execution log (志 — execution record)
        self.log: list[str] = []

        # Domain effects accumulated during execution
        self.domain_effects: list[DomainEffect] = []

    # ── Register Access ────────────────────────────────────────

    def get_reg(self, index: int) -> int:
        """Read a register value. 獲寄存器.

        Args:
            index: Register index (0–63). Use resolve_register() for names.

        Returns:
            Current value of the register.
        """
        if not 0 <= index < self.NUM_REGISTERS:
            raise IndexError(f"寄存器越界 / Register out of range: {index}")
        return self._registers[index]

    def set_reg(self, index: int, value: int) -> None:
        """Write a register value. 設寄存器.

        Args:
            index: Register index (0–63).
            value: Integer value to store.
        """
        if not 0 <= index < self.NUM_REGISTERS:
            raise IndexError(f"寄存器越界 / Register out of range: {index}")
        self._registers[index] = int(value)

    def get_reg_by_name(self, name: str) -> int:
        """Read a register by its hexagram name or 'Rn' notation.

        Args:
            name: Register name ('乾', 'R0', '主題', etc.).

        Returns:
            Current value of the register.
        """
        return self.get_reg(resolve_register(name))

    def set_reg_by_name(self, name: str, value: int) -> None:
        """Write a register by its hexagram name or 'Rn' notation.

        Args:
            name: Register name.
            value: Integer value to store.
        """
        self.set_reg(resolve_register(name), value)

    @property
    def topic(self) -> int:
        """Read the topic register (R63 主題寄存器).

        The topic register holds the current discourse topic for
        zero-anaphora resolution. In Classical Chinese, the topic
        is often omitted from subsequent sentences — the reader
        (or VM) infers it from context.
        """
        return self._registers[63]

    @topic.setter
    def topic(self, value: int) -> None:
        """Set the topic register."""
        self._registers[63] = int(value)

    # ── Memory Access ──────────────────────────────────────────

    def mem_load(self, address: int) -> int:
        """Load a value from memory. 載."""
        return self._memory.get(address, 0)

    def mem_store(self, address: int, value: int) -> None:
        """Store a value to memory. 存."""
        self._memory[address] = int(value)

    # ── Stack Operations ───────────────────────────────────────

    def push(self, value: int) -> None:
        """Push a value onto the data stack. 壓."""
        if len(self._stack) >= self.MAX_STACK_DEPTH:
            raise RuntimeError("棧滿: data stack overflow")
        self._stack.append(int(value))

    def pop(self) -> int:
        """Pop a value from the data stack. 彈.

        Returns:
            The top value of the stack.

        Raises:
            RuntimeError: If stack is empty.
        """
        if not self._stack:
            raise RuntimeError("棧空: data stack underflow")
        return self._stack.pop()

    @property
    def stack_depth(self) -> int:
        """Current depth of the data stack."""
        return len(self._stack)

    # ── Operand Resolution ─────────────────────────────────────

    def _resolve_operand(self, operand: Any) -> int:
        """Resolve an operand to an integer value.

        Handles:
          - int: pass through
          - str register reference ('R0', '乾', '主題'): read register
          - str Chinese numeral ('三', '百'): parse to int
          - str topic marker ('其'): use topic register
        """
        if isinstance(operand, int):
            return operand

        s = str(operand).strip()

        # Topic reference: 其 = current topic
        if s == "其":
            return self.topic

        # Register reference
        try:
            idx = resolve_register(s)
            return self.get_reg(idx)
        except ValueError:
            pass

        # Chinese numeral (extended)
        cn = parse_chinese_number(s)
        if cn is not None:
            return cn

        # Arabic numeral
        try:
            return int(s)
        except ValueError:
            pass

        # String → hash (for non-numeric strings)
        return hash(s) & 0xFFFFFFFF

    def _resolve_register_operand(self, operand: Any) -> int:
        """Resolve an operand that should be a register INDEX."""
        if isinstance(operand, int):
            return operand
        s = str(operand).strip()
        try:
            return resolve_register(s)
        except ValueError:
            # Treat as immediate value that specifies a register index
            cn = parse_chinese_number(s)
            if cn is not None:
                return cn
            return int(s)

    # ── Program Loading ────────────────────────────────────────

    def load_program(self, instructions: list[Instruction]) -> None:
        """Load a program into the VM. 載程.

        Args:
            instructions: List of instructions to execute.
        """
        self._program = instructions
        # Assign addresses
        for i, instr in enumerate(instructions):
            instr.address = i

    @property
    def program(self) -> list[Instruction]:
        """Current loaded program."""
        return self._program

    @property
    def pc(self) -> int:
        """Current program counter."""
        return self._pc

    # ── Execution ──────────────────────────────────────────────

    def run(self, instructions: list[Instruction] | None = None) -> int:
        """Execute the loaded program. 行.

        Runs until HALT is encountered or the program ends.
        Returns the value of R0 (accumulator) after execution.

        Args:
            instructions: If provided, loaded before execution.

        Returns:
            Value of R0 (乾 register) after execution.
        """
        if instructions is not None:
            self.load_program(instructions)

        self._halted = False
        self._pc = 0
        self.log = []
        self.domain_effects = []

        while not self._halted and self._pc < len(self._program):
            instr = self._program[self._pc]
            self._execute(instr)
            if not self._halted:
                self._pc += 1

        return self.get_reg(0)

    def step(self) -> Instruction | None:
        """Execute a single instruction. 單步.

        Returns:
            The instruction that was executed, or None if halted.
        """
        if self._halted or self._pc >= len(self._program):
            return None

        instr = self._program[self._pc]
        self._execute(instr)
        if not self._halted:
            self._pc += 1
        return instr

    def reset(self) -> None:
        """Reset all VM state. 歸零.

        Clears registers, stacks, memory, and program counter.
        Does NOT clear the loaded program.
        """
        self._registers = [0] * self.NUM_REGISTERS
        self._stack.clear()
        self._call_stack.clear()
        self._pc = 0
        self._halted = False
        self._flag = 0
        self._memory.clear()
        self.log = []
        self.domain_effects = []
        # Reset context but keep the domain dispatch configuration
        self.context = ContextStack()

    def halt(self) -> None:
        """Halt execution. 終."""
        self._halted = True
        self.log.append("終 — halt")

    # ── Core Execution Engine ──────────────────────────────────

    def _execute(self, instr: Instruction) -> None:
        """Execute a single instruction with domain dispatch.

        This is the heart of 以境定行 (behavior by context).
        Before executing each opcode, the domain dispatcher is
        consulted. Any domain-specific side effects are applied.
        """
        if not isinstance(instr.opcode, Opcode):
            # Unknown opcode string — treat as NOP
            self.log.append(f"未知指令 / Unknown opcode: {instr.opcode}")
            return

        op = instr.opcode
        domain = self.context.current.domain

        # Domain dispatch — check for domain-specific behavior
        effect = self._pre_dispatch(op, domain, instr)
        if effect:
            self.domain_effects.append(effect)
            self.log.append(f"[{domain.value}] {effect.message}")

        # Execute the opcode
        handler = _OPCODE_HANDLERS.get(op)
        if handler is None:
            self.log.append(f"未實現 / Unimplemented: {op.name}")
            return

        handler(self, instr)

    def _pre_dispatch(self, opcode: Opcode, domain: ContextDomain,
                      instr: Instruction) -> DomainEffect | None:
        """Pre-execution domain dispatch.

        Consults the DomainDispatcher for any domain-specific
        side effects before executing the opcode.
        """
        # Extract values for dispatch context
        kwargs: dict[str, Any] = {}
        if len(instr.operands) >= 2:
            kwargs["a"] = self._resolve_operand(instr.operands[0])
            kwargs["b"] = self._resolve_operand(instr.operands[1])
        if len(instr.operands) >= 1:
            kwargs["value"] = self._resolve_operand(instr.operands[0])
        kwargs["registers"] = self._registers
        kwargs["_opcode"] = opcode

        return self.dispatcher.dispatch(opcode, domain, **kwargs)


# ═══════════════════════════════════════════════════════════════
# Opcode Handlers — 指令執行器
# ═══════════════════════════════════════════════════════════════

def _handle_nop(vm: FluxVM, instr: Instruction) -> None:
    """NOP — No operation. 無."""
    pass


def _handle_mov(vm: FluxVM, instr: Instruction) -> None:
    """MOV dst, src — Move value between registers. 移."""
    dst = vm._resolve_register_operand(instr.operands[0])
    src = vm._resolve_register_operand(instr.operands[1])
    vm.set_reg(dst, vm.get_reg(src))


def _handle_load(vm: FluxVM, instr: Instruction) -> None:
    """LOAD reg, addr — Load from memory into register. 載."""
    reg = vm._resolve_register_operand(instr.operands[0])
    addr = vm._resolve_operand(instr.operands[1])
    vm.set_reg(reg, vm.mem_load(addr))


def _handle_store(vm: FluxVM, instr: Instruction) -> None:
    """STORE addr, reg — Store register to memory. 存."""
    addr = vm._resolve_operand(instr.operands[0])
    reg = vm._resolve_register_operand(instr.operands[1])
    vm.mem_store(addr, vm.get_reg(reg))


def _handle_jmp(vm: FluxVM, instr: Instruction) -> None:
    """JMP addr — Unconditional jump. 跳."""
    target = vm._resolve_operand(instr.operands[0])
    vm._pc = int(target) - 1  # -1 because step() will increment


def _handle_jz(vm: FluxVM, instr: Instruction) -> None:
    """JZ addr — Jump if zero. 若零."""
    target = vm._resolve_operand(instr.operands[0])
    # Default: check accumulator (R0)
    test_reg = 0
    if len(instr.operands) >= 2:
        test_reg = vm._resolve_register_operand(instr.operands[1])
    if vm.get_reg(test_reg) == 0:
        vm._pc = int(target) - 1
        vm.log.append(f"若零：跳至 {target}")


def _handle_jnz(vm: FluxVM, instr: Instruction) -> None:
    """JNZ addr — Jump if not zero. 若非零."""
    target = vm._resolve_operand(instr.operands[0])
    test_reg = 0
    if len(instr.operands) >= 2:
        test_reg = vm._resolve_register_operand(instr.operands[1])
    if vm.get_reg(test_reg) != 0:
        vm._pc = int(target) - 1
        vm.log.append(f"若非零：跳至 {target}")


def _handle_call(vm: FluxVM, instr: Instruction) -> None:
    """CALL addr — Call subroutine. 呼."""
    target = vm._resolve_operand(instr.operands[0])
    if len(vm._call_stack) >= vm.MAX_CALL_DEPTH:
        raise RuntimeError("呼叫棧滿: call stack overflow")
    vm._call_stack.append(vm._pc)
    vm._pc = int(target) - 1
    vm.log.append(f"呼：跳至 {target}，歸址入棧")


def _handle_ret(vm: FluxVM, instr: Instruction) -> None:
    """RET — Return from subroutine. 歸."""
    if not vm._call_stack:
        vm.halt()
        return
    vm._pc = vm._call_stack.pop()
    vm.log.append("歸：返回")


def _handle_halt(vm: FluxVM, instr: Instruction) -> None:
    """HALT — Stop execution. 終."""
    vm.halt()


def _handle_print(vm: FluxVM, instr: Instruction) -> None:
    """PRINT value — Print / display a value. 示."""
    val = instr.operands[0] if instr.operands else vm.get_reg(0)
    resolved = vm._resolve_operand(val) if not isinstance(val, str) else val
    vm.log.append(f"示：{resolved}")


# ── Integer Arithmetic ────────────────────────────────────────

def _handle_iadd(vm: FluxVM, instr: Instruction) -> None:
    """IADD a, b — Integer add, store in R0. 加."""
    a = vm._resolve_operand(instr.operands[0])
    b = vm._resolve_operand(instr.operands[1])
    result = a + b
    vm.set_reg(0, result)
    vm.log.append(f"加：{a} + {b} = {result}")


def _handle_isub(vm: FluxVM, instr: Instruction) -> None:
    """ISUB a, b — Integer subtract, store in R0. 減."""
    a = vm._resolve_operand(instr.operands[0])
    b = vm._resolve_operand(instr.operands[1])
    result = a - b
    vm.set_reg(0, result)
    vm.log.append(f"減：{a} - {b} = {result}")


def _handle_imul(vm: FluxVM, instr: Instruction) -> None:
    """IMUL a, b — Integer multiply, store in R0. 乘."""
    a = vm._resolve_operand(instr.operands[0])
    b = vm._resolve_operand(instr.operands[1])
    result = a * b
    vm.set_reg(0, result)
    vm.log.append(f"乘：{a} × {b} = {result}")


def _handle_idiv(vm: FluxVM, instr: Instruction) -> None:
    """IDIV a, b — Integer divide, store in R0. 除."""
    a = vm._resolve_operand(instr.operands[0])
    b = vm._resolve_operand(instr.operands[1])
    if b == 0:
        vm.log.append("除：錯 — 除以零 / division by zero")
        vm.set_reg(0, 0)
        return
    result = int(a / b)  # Truncate toward zero
    vm.set_reg(0, result)
    vm.log.append(f"除：{a} ÷ {b} = {result}")


def _handle_imod(vm: FluxVM, instr: Instruction) -> None:
    """IMOD a, b — Integer modulo, store in R0. 餘."""
    a = vm._resolve_operand(instr.operands[0])
    b = vm._resolve_operand(instr.operands[1])
    if b == 0:
        vm.log.append("餘：錯 — 除以零")
        vm.set_reg(0, 0)
        return
    result = a % b
    vm.set_reg(0, result)
    vm.log.append(f"餘：{a} mod {b} = {result}")


def _handle_ineg(vm: FluxVM, instr: Instruction) -> None:
    """INEG a — Negate, store in R0. 負."""
    a = vm._resolve_operand(instr.operands[0])
    result = -a
    vm.set_reg(0, result)
    vm.log.append(f"負：-{a} = {result}")


def _handle_inc(vm: FluxVM, instr: Instruction) -> None:
    """INC reg — Increment register. 增."""
    reg = vm._resolve_register_operand(instr.operands[0])
    val = vm.get_reg(reg) + 1
    vm.set_reg(reg, val)
    vm.log.append(f"增：{register_mnemonic(reg)} = {val}")


def _handle_dec(vm: FluxVM, instr: Instruction) -> None:
    """DEC reg — Decrement register. 減一."""
    reg = vm._resolve_register_operand(instr.operands[0])
    val = vm.get_reg(reg) - 1
    vm.set_reg(reg, val)
    vm.log.append(f"減一：{register_mnemonic(reg)} = {val}")


def _handle_ieq(vm: FluxVM, instr: Instruction) -> None:
    """IEQ a, b — Compare equal, set flag. 等於."""
    a = vm._resolve_operand(instr.operands[0])
    b = vm._resolve_operand(instr.operands[1])
    vm._flag = 1 if a == b else 0
    vm.set_reg(0, vm._flag)
    vm.log.append(f"等於：{a} {'==' if vm._flag else '!='} {b}")


def _handle_igt(vm: FluxVM, instr: Instruction) -> None:
    """IGT a, b — Compare greater than, set flag. 大於."""
    a = vm._resolve_operand(instr.operands[0])
    b = vm._resolve_operand(instr.operands[1])
    vm._flag = 1 if a > b else 0
    vm.set_reg(0, vm._flag)
    vm.log.append(f"大於：{a} {'>' if vm._flag else '<='} {b}")


def _handle_ilt(vm: FluxVM, instr: Instruction) -> None:
    """ILT a, b — Compare less than, set flag. 小於."""
    a = vm._resolve_operand(instr.operands[0])
    b = vm._resolve_operand(instr.operands[1])
    vm._flag = 1 if a < b else 0
    vm.set_reg(0, vm._flag)
    vm.log.append(f"小於：{a} {'<' if vm._flag else '>='} {b}")


def _handle_icmp(vm: FluxVM, instr: Instruction) -> None:
    """ICMP a, b — Compare, set flag to -1/0/1. 比."""
    a = vm._resolve_operand(instr.operands[0])
    b = vm._resolve_operand(instr.operands[1])
    if a < b:
        vm._flag = -1
    elif a > b:
        vm._flag = 1
    else:
        vm._flag = 0
    vm.log.append(f"比：{a} vs {b} → flag={vm._flag}")


# ── Stack Operations ──────────────────────────────────────────

def _handle_push(vm: FluxVM, instr: Instruction) -> None:
    """PUSH value — Push onto data stack. 壓."""
    val = vm._resolve_operand(instr.operands[0])
    vm.push(val)
    vm.log.append(f"壓：{val}")


def _handle_pop(vm: FluxVM, instr: Instruction) -> None:
    """POP reg — Pop from data stack into register. 彈."""
    val = vm.pop()
    if instr.operands:
        reg = vm._resolve_register_operand(instr.operands[0])
        vm.set_reg(reg, val)
    else:
        vm.set_reg(0, val)
    vm.log.append(f"彈：{val}")


def _handle_movi(vm: FluxVM, instr: Instruction) -> None:
    """MOVI reg, value — Set register to immediate value. 設."""
    reg = vm._resolve_register_operand(instr.operands[0])
    val = vm._resolve_operand(instr.operands[1])
    vm.set_reg(reg, val)
    vm.log.append(f"設：{register_mnemonic(reg)} = {val}")


# ── Conditional Branch ────────────────────────────────────────

def _handle_je(vm: FluxVM, instr: Instruction) -> None:
    """JE addr — Jump if flag == 0 (equal). 若等."""
    target = vm._resolve_operand(instr.operands[0])
    if vm._flag == 0:
        vm._pc = int(target) - 1
        vm.log.append(f"若等：跳至 {target}")


def _handle_jne(vm: FluxVM, instr: Instruction) -> None:
    """JNE addr — Jump if flag != 0 (not equal). 若不等."""
    target = vm._resolve_operand(instr.operands[0])
    if vm._flag != 0:
        vm._pc = int(target) - 1
        vm.log.append(f"若不等：跳至 {target}")


# ── Agent Communication ───────────────────────────────────────

def _handle_tell(vm: FluxVM, instr: Instruction) -> None:
    """TELL agent, msg — Send message to agent. 告."""
    agent = str(instr.operands[0]) if instr.operands else ""
    msg = str(instr.operands[1]) if len(instr.operands) >= 2 else ""
    vm.log.append(f"告 {agent}：{msg}")


def _handle_ask(vm: FluxVM, instr: Instruction) -> None:
    """ASK agent, topic — Query agent. 問."""
    agent = str(instr.operands[0]) if instr.operands else ""
    topic = str(instr.operands[1]) if len(instr.operands) >= 2 else ""
    vm.log.append(f"問 {agent}：{topic}")


def _handle_delegate(vm: FluxVM, instr: Instruction) -> None:
    """DELEGATE agent, task — Delegate task to agent. 命."""
    agent = str(instr.operands[0]) if instr.operands else ""
    task = str(instr.operands[1]) if len(instr.operands) >= 2 else ""
    vm.log.append(f"命 {agent}：{task}")


def _handle_broadcast(vm: FluxVM, instr: Instruction) -> None:
    """BROADCAST msg — Message all agents. 令."""
    msg = str(instr.operands[0]) if instr.operands else ""
    vm.log.append(f"令（遍告）：{msg}")


# ── Trust & Capability ────────────────────────────────────────

def _handle_trust_check(vm: FluxVM, instr: Instruction) -> None:
    """TRUST_CHECK agent — Verify trust relationship. 審信."""
    agent = str(instr.operands[0]) if instr.operands else ""
    # Trust check: verify the agent exists and is trusted
    trusted = vm._resolve_operand(instr.operands[1]) if len(instr.operands) >= 2 else 1
    vm._flag = 1 if trusted else 0
    vm.log.append(f"審信 {agent}：{'可信' if vm._flag else '不可信'}")


def _handle_cap_require(vm: FluxVM, instr: Instruction) -> None:
    """CAP_REQUIRE capability — Require a capability. 求能."""
    cap = str(instr.operands[0]) if instr.operands else ""
    vm.log.append(f"求能：需要「{cap}」")


# ── Domain-Specific Opcodes ───────────────────────────────────

def _handle_iexp(vm: FluxVM, instr: Instruction) -> None:
    """IEXP base, exp — Exponentiation. 冪."""
    base = vm._resolve_operand(instr.operands[0])
    exp = vm._resolve_operand(instr.operands[1])
    result = base ** exp
    vm.set_reg(0, result)
    vm.log.append(f"冪：{base}^{exp} = {result}")


def _handle_iroot(vm: FluxVM, instr: Instruction) -> None:
    """IROOT value — Integer square root. 根."""
    val = vm._resolve_operand(instr.operands[0])
    if val < 0:
        vm.log.append("根：錯 — 負數無實根")
        vm.set_reg(0, 0)
        return
    result = int(val ** 0.5)
    vm.set_reg(0, result)
    vm.log.append(f"根：√{val} = {result}")


def _handle_verify_trust(vm: FluxVM, instr: Instruction) -> None:
    """VERIFY_TRUST target — Confucian trust verification. 信."""
    target = str(instr.operands[0]) if instr.operands else ""
    vm.log.append(f"信 — 核實：{target}")
    vm._flag = 1  # Assume trust verified


def _handle_check_bounds(vm: FluxVM, instr: Instruction) -> None:
    """CHECK_BOUNDS value, limit — Confucian bounds check. 義."""
    val = vm._resolve_operand(instr.operands[0])
    limit = vm._resolve_operand(instr.operands[1]) if len(instr.operands) >= 2 else 100
    vm._flag = 1 if 0 <= val <= limit else 0
    vm.log.append(f"義 — 檢查界限：{val} in [0, {limit}] → {'合' if vm._flag else '越'}")


def _handle_optimize(vm: FluxVM, instr: Instruction) -> None:
    """OPTIMIZE target — Confucian optimization. 智."""
    target = str(instr.operands[0]) if instr.operands else ""
    vm.log.append(f"智 — 優化：{target}")


def _handle_attack(vm: FluxVM, instr: Instruction) -> None:
    """ATTACK target — Military attack. 攻."""
    target = str(instr.operands[0]) if instr.operands else ""
    vm.log.append(f"攻：{target}")


def _handle_defend(vm: FluxVM, instr: Instruction) -> None:
    """DEFEND target — Military defend. 守."""
    target = str(instr.operands[0]) if instr.operands else ""
    vm.log.append(f"守：{target}")


def _handle_advance(vm: FluxVM, instr: Instruction) -> None:
    """ADVANCE target — Military advance. 進."""
    target = str(instr.operands[0]) if instr.operands else ""
    vm.log.append(f"進：{target}")


def _handle_retreat(vm: FluxVM, instr: Instruction) -> None:
    """RETREAT — Military retreat. 退."""
    vm.log.append("退")


def _handle_sequence(vm: FluxVM, instr: Instruction) -> None:
    """SEQUENCE — Sequential execution marker. 則."""
    vm.log.append("則 — 順序執行")


def _handle_loop(vm: FluxVM, instr: Instruction) -> None:
    """LOOP addr — Loop back to address. 循."""
    target = vm._resolve_operand(instr.operands[0])
    vm._pc = int(target) - 1
    vm.log.append(f"循：回至 {target}")


# ── I Ching Operations ────────────────────────────────────────

def _handle_hex_jump(vm: FluxVM, instr: Instruction) -> None:
    """HEX_JUMP hexagram — Jump to hexagram address. 變卦.

    The hexagram is resolved to its binary address, and the
    program counter is set to that address. This implements
    變卦 (hexagram transition) as control flow transfer.
    """
    hex_ref = instr.operands[0]
    if isinstance(hex_ref, str):
        try:
            target_hex = name_to_hexagram(hex_ref)
            addr = target_hex.address
        except KeyError:
            # Try as register containing a hexagram address
            addr = vm._resolve_operand(hex_ref)
    elif isinstance(hex_ref, int):
        addr = hex_ref
    else:
        addr = vm._resolve_operand(hex_ref)

    vm._pc = int(addr) - 1
    vm.log.append(f"變卦：跳至卦址 {addr}")


def _handle_hex_call(vm: FluxVM, instr: Instruction) -> None:
    """HEX_CALL hexagram — Call hexagram subroutine. 卦呼."""
    hex_ref = instr.operands[0]
    if isinstance(hex_ref, str):
        try:
            addr = name_to_hexagram(hex_ref).address
        except KeyError:
            addr = vm._resolve_operand(hex_ref)
    else:
        addr = vm._resolve_operand(hex_ref)

    vm._call_stack.append(vm._pc)
    vm._pc = int(addr) - 1
    vm.log.append(f"卦呼：{hex_ref}（址 {addr}），歸址入棧")


def _handle_trigram_addr(vm: FluxVM, instr: Instruction) -> None:
    """TRIGRAM_ADDR trigram, position — Get trigram address bits. 八卦址.

    Resolves a trigram name to its 3-bit value, positioned as
    either lower (bits 0–2) or upper (bits 3–5) in a hexagram address.
    """
    trig_name = str(instr.operands[0])
    position = str(instr.operands[1]) if len(instr.operands) >= 2 else "lower"

    try:
        trigram = Trigram[trig_name.upper()]
    except KeyError:
        # Try Chinese name lookup
        name_to_val = {
            "乾": Trigram.QIAN, "兌": Trigram.DUI, "離": Trigram.LI,
            "震": Trigram.ZHEN, "巽": Trigram.XUN, "坎": Trigram.KAN,
            "艮": Trigram.GEN, "坤": Trigram.KUN,
        }
        trigram = name_to_val.get(trig_name, Trigram.KUN)

    addr = (trigram << 3) if position == "upper" else trigram
    vm.set_reg(0, addr)
    vm.log.append(f"八卦址：{trig_name}({trigram.value}) → {addr}")


# ── Topic Register Operations ─────────────────────────────────

def _handle_set_topic(vm: FluxVM, instr: Instruction) -> None:
    """SET_TOPIC value — Set the topic register. 定題.

    The topic register (R63 主題寄存器) holds the current
    discourse topic for zero-anaphora resolution. In 文言,
    subsequent sentences often omit their topic — the reader
    infers it from the preceding context.
    """
    val = vm._resolve_operand(instr.operands[0])
    vm.topic = val
    vm.log.append(f"定題：主題 = {val}")


def _handle_use_topic(vm: FluxVM, instr: Instruction) -> None:
    """USE_TOPIC reg — Copy topic register to specified register. 用題."""
    reg = vm._resolve_register_operand(instr.operands[0])
    vm.set_reg(reg, vm.topic)
    vm.log.append(f"用題：{register_mnemonic(reg)} = 主題({vm.topic})")


def _handle_clear_topic(vm: FluxVM, instr: Instruction) -> None:
    """CLEAR_TOPIC — Clear the topic register. 清題."""
    vm.topic = 0
    vm.log.append("清題：主題歸零")


# ── Handler Dispatch Table ────────────────────────────────────

_OPCODE_HANDLERS: dict[Opcode, Callable[[FluxVM, Instruction], None]] = {
    Opcode.NOP:          _handle_nop,
    Opcode.MOV:          _handle_mov,
    Opcode.LOAD:         _handle_load,
    Opcode.STORE:        _handle_store,
    Opcode.JMP:          _handle_jmp,
    Opcode.JZ:           _handle_jz,
    Opcode.JNZ:          _handle_jnz,
    Opcode.CALL:         _handle_call,
    Opcode.RET:          _handle_ret,
    Opcode.HALT:         _handle_halt,
    Opcode.PRINT:        _handle_print,
    Opcode.IADD:         _handle_iadd,
    Opcode.ISUB:         _handle_isub,
    Opcode.IMUL:         _handle_imul,
    Opcode.IDIV:         _handle_idiv,
    Opcode.IMOD:         _handle_imod,
    Opcode.INEG:         _handle_ineg,
    Opcode.INC:          _handle_inc,
    Opcode.DEC:          _handle_dec,
    Opcode.IEQ:          _handle_ieq,
    Opcode.IGT:          _handle_igt,
    Opcode.ILT:          _handle_ilt,
    Opcode.ICMP:         _handle_icmp,
    Opcode.PUSH:         _handle_push,
    Opcode.POP:          _handle_pop,
    Opcode.MOVI:         _handle_movi,
    Opcode.JE:           _handle_je,
    Opcode.JNE:          _handle_jne,
    Opcode.TELL:         _handle_tell,
    Opcode.ASK:          _handle_ask,
    Opcode.DELEGATE:     _handle_delegate,
    Opcode.BROADCAST:    _handle_broadcast,
    Opcode.TRUST_CHECK:  _handle_trust_check,
    Opcode.CAP_REQUIRE:  _handle_cap_require,
    Opcode.IEXP:         _handle_iexp,
    Opcode.IROOT:        _handle_iroot,
    Opcode.VERIFY_TRUST: _handle_verify_trust,
    Opcode.CHECK_BOUNDS: _handle_check_bounds,
    Opcode.OPTIMIZE:     _handle_optimize,
    Opcode.ATTACK:       _handle_attack,
    Opcode.DEFEND:       _handle_defend,
    Opcode.ADVANCE:      _handle_advance,
    Opcode.RETREAT:      _handle_retreat,
    Opcode.SEQUENCE:     _handle_sequence,
    Opcode.LOOP:         _handle_loop,
    Opcode.HEX_JUMP:     _handle_hex_jump,
    Opcode.HEX_CALL:     _handle_hex_call,
    Opcode.TRIGRAM_ADDR: _handle_trigram_addr,
    Opcode.SET_TOPIC:    _handle_set_topic,
    Opcode.USE_TOPIC:    _handle_use_topic,
    Opcode.CLEAR_TOPIC:  _handle_clear_topic,
}


# ═══════════════════════════════════════════════════════════════
# Disassembly & Inspection
# ═══════════════════════════════════════════════════════════════

def disassemble(instructions: list[Instruction]) -> list[str]:
    """Produce a human-readable disassembly of instructions.

    Includes:
      - Address
      - Opcode name
      - Operands (with hexagram mnemonics for register indices)
      - Source comment (original Classical Chinese)

    Args:
        instructions: List of instructions to disassemble.

    Returns:
        List of formatted disassembly lines.
    """
    lines: list[str] = []
    for instr in instructions:
        addr = f"{instr.address:04d}"
        ops = []
        for op in instr.operands:
            if isinstance(op, int) and 0 <= op < 64:
                ops.append(f"{register_mnemonic(op)}(R{op})")
            else:
                ops.append(str(op))
        ops_str = ", ".join(ops)
        src = f"  ; {instr.source}" if instr.source else ""
        lines.append(f"{addr}: {instr.opcode_name:<16s} {ops_str}{src}")
    return lines


def dump_registers(vm: FluxVM, non_zero_only: bool = True) -> str:
    """Dump the VM register state in hexagram notation.

    Args:
        vm: The VM instance.
        non_zero_only: If True, only show non-zero registers.

    Returns:
        Formatted register dump string.
    """
    lines: list[str] = []
    lines.append("╔══════════════════════════════════════════════╗")
    lines.append("║  六十四卦寄存器 / Hexagram Register File     ║")
    lines.append("╠═══════╦═══════════╦══════════════════════════╣")

    shown = 0
    for i in range(vm.NUM_REGISTERS):
        val = vm.get_reg(i)
        if non_zero_only and val == 0:
            continue
        mnemonic = register_mnemonic(i)
        hexagram = address_to_hexagram(i) if i < 64 else None
        kw = f"KW#{hexagram.king_wen_number:2d}" if hexagram else ""
        addr_bin = format(i, '06b')
        lines.append(
            f"║ R{i:02d}  ║ {mnemonic:6s}    ║ {val:>12d}  "
            f"({kw} {addr_bin}) ║"
        )
        shown += 1

    if shown == 0:
        lines.append("║  (all registers zero)                            ║")

    lines.append("╚═══════╩═══════════╩══════════════════════════╝")
    lines.append(f"  主題 (R63): {vm.topic}")
    lines.append(f"  Flag: {vm._flag}")
    lines.append(f"  Stack depth: {vm.stack_depth}")
    lines.append(f"  Call depth: {len(vm._call_stack)}")
    return "\n".join(lines)
