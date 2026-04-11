"""
字碼 — Character-Glyph Polymorphic Dispatch System

In Classical Chinese (文言), each character is a self-contained concept
that activates different bytecode depending on the surrounding textual
domain. There is no grammar — meaning emerges from context.

同字異碼 — same character, different bytecode, by domain.
一字多義 — one character, multiple meanings.

This module implements the polymorphic dispatch table: for each
character in each domain, we define the bytecode instruction it
compiles to. A single character like 加 (jiā) compiles to IADD in
the mathematical domain, DISTRIBUTE in the Confucian domain, and
REINFORCE in the military domain.

Architecture:
  GlyphTable maps (domain, character) → (opcode, operand_pattern)
  The operand_pattern tells the interpreter how to extract operands
  from surrounding characters.

以文意定義 — meaning determined by textual intent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .context import ContextDomain


# ═══════════════════════════════════════════════════════════════
# Operand Patterns
# ═══════════════════════════════════════════════════════════════

class OperandPattern(Enum):
    """How to extract operands from surrounding characters.

    In 文言, operand order and presence are determined entirely
    by the concept, not by grammar. Each glyph declares what
    operands it expects and how to find them.
    """
    NONE = "none"             # No operands (e.g., HALT, NOP)
    ONE_IMM = "one_imm"       # One immediate value follows
    ONE_REG = "one_reg"       # One register follows
    TWO_IMM = "two_imm"       # Two immediate values follow
    TWO_REG = "two_reg"       # Two register operands
    REG_IMM = "reg_imm"       # Register then immediate
    IMM_REG = "imm_reg"       # Immediate then register
    ONE_STR = "one_str"       # One string operand (rest of clause)
    TWO_STR = "two_str"       # Two string operands (agent, message)
    REG_REG = "reg_reg"       # Two register operands (Rn Rm)
    TOPIC = "topic"           # Implicit: use topic register (零形回指)
    FLAG = "flag"             # Uses comparison flag register
    ADDR = "addr"             # Jump target address
    ADDR_REG = "addr_reg"     # Address and condition register
    REG_ADDR = "reg_addr"     # Register to store, then address
    TRIGRAM = "trigram"       # Trigram name for addressing
    HEXAGRAM = "hexagram"     # Hexagram name for jump target
    DYN = "dynamic"           # Operands determined by following characters


# ═══════════════════════════════════════════════════════════════
# Glyph Entry — A single character's dispatch definition
# ═══════════════════════════════════════════════════════════════

@dataclass
class GlyphEntry:
    """Dispatch entry for one character in one domain.

    Attributes:
        character: The Chinese character (字).
        domain: The textual domain (境域).
        opcode: The VM opcode this character compiles to.
        operand_pattern: How operands are extracted.
        description: English description of the concept.
        classical_note: Literary or philosophical note in Classical Chinese.
        arity: Number of operands expected (0, 1, or 2).
        precedence: Operator precedence (higher = tighter binding), 0 if not an operator.
    """
    character: str
    domain: ContextDomain
    opcode: str
    operand_pattern: OperandPattern = OperandPattern.NONE
    description: str = ""
    classical_note: str = ""
    arity: int = 0
    precedence: int = 0


# ═══════════════════════════════════════════════════════════════
# Glyph Table — Complete Polymorphic Dispatch Table
# ═══════════════════════════════════════════════════════════════

class GlyphTable:
    """Complete polymorphic dispatch table for all characters.

    字典 — the dictionary of characters and their bytecode
    mappings, organized by domain. Each (domain, character)
    pair maps to exactly one GlyphEntry.

    The table contains 100+ character definitions across 5 domains:
      - 算 (Mathematics): 22 characters
      - 儒 (Confucian): 25 characters
      - 兵 (Military): 25 characters
      - 使 (Agent): 20 characters
      - 制 (Control): 20 characters
    """

    def __init__(self) -> None:
        self._table: dict[tuple[ContextDomain, str], GlyphEntry] = {}
        self._by_character: dict[str, list[GlyphEntry]] = {}
        self._load_all_domains()

    def lookup(self, domain: ContextDomain, character: str) -> GlyphEntry | None:
        """Look up a character's dispatch entry in a given domain.

        以境求字 — find the glyph by domain and character.

        Args:
            domain: The active textual domain.
            character: A single Chinese character.

        Returns:
            The GlyphEntry, or None if the character is not defined
            in this domain.
        """
        return self._table.get((domain, character))

    def lookup_all_domains(self, character: str) -> dict[ContextDomain, GlyphEntry]:
        """Look up a character across ALL domains.

        Shows the polymorphic nature of the character: how the same
        character activates different bytecode in different contexts.

        Args:
            character: A single Chinese character.

        Returns:
            Dict mapping domain → GlyphEntry for every domain
            where this character is defined.
        """
        results: dict[ContextDomain, GlyphEntry] = {}
        for domain in ContextDomain:
            entry = self._table.get((domain, character))
            if entry:
                results[domain] = entry
        return results

    def entries_for_domain(self, domain: ContextDomain) -> list[GlyphEntry]:
        """Get all glyph entries for a domain.

        Args:
            domain: The domain to query.

        Returns:
            List of all GlyphEntry objects for this domain.
        """
        return [
            entry for (d, _), entry in self._table.items()
            if d == domain
        ]

    def characters_for_domain(self, domain: ContextDomain) -> list[str]:
        """Get all character names defined in a domain."""
        return sorted(set(
            char for (d, char) in self._table if d == domain
        ))

    @property
    def total_entries(self) -> int:
        """Total number of glyph entries across all domains."""
        return len(self._table)

    def register(self, entry: GlyphEntry) -> None:
        """Register a new glyph entry. 註冊.

        Args:
            entry: The glyph entry to add.
        """
        key = (entry.domain, entry.character)
        self._table[key] = entry
        if entry.character not in self._by_character:
            self._by_character[entry.character] = []
        self._by_character[entry.character].append(entry)

    def polymorphic_info(self, character: str) -> str:
        """Show how a character behaves differently across domains.

        Args:
            character: The character to inspect.

        Returns:
            Formatted multi-line string showing all domain mappings.
        """
        entries = self._by_character.get(character, [])
        if not entries:
            return f"字「{character}」未定義 / Character '{character}' not defined"

        lines = [f"字「{character}」— {len(entries)} domains:"]
        for entry in entries:
            lines.append(
                f"  [{entry.domain.value}] {entry.opcode} "
                f"({entry.operand_pattern.value}) — {entry.description}"
            )
            if entry.classical_note:
                lines.append(f"         注：{entry.classical_note}")
        return "\n".join(lines)

    # ── Domain Loading ─────────────────────────────────────────

    def _load_all_domains(self) -> None:
        """Load glyph definitions for all five domains."""
        self._load_mathematics()
        self._load_confucian()
        self._load_military()
        self._load_agent()
        self._load_control()

    def _load_mathematics(self) -> None:
        """Load 算 (Mathematics) domain glyphs — 22 characters.

        The mathematical domain is the foundation. These characters
        map directly to arithmetic and comparison operations.

        算學 — the art of calculation, refined over millennia.
        From the 九章算術 (Nine Chapters on the Mathematical Art)
        to modern computing.
        """
        d = ContextDomain.MATHEMATICS
        entries = [
            # ── Arithmetic operators (四則) ───────────────────
            GlyphEntry("加", d, "IADD", OperandPattern.TWO_IMM,
                       "Add two values", "加法：合二為一", arity=2, precedence=10),
            GlyphEntry("減", d, "ISUB", OperandPattern.TWO_IMM,
                       "Subtract second from first", "減法：以多減少", arity=2, precedence=10),
            GlyphEntry("乘", d, "IMUL", OperandPattern.TWO_IMM,
                       "Multiply two values", "乘法：倍之又倍", arity=2, precedence=20),
            GlyphEntry("除", d, "IDIV", OperandPattern.TWO_IMM,
                       "Integer divide", "除法：均分之", arity=2, precedence=20),
            GlyphEntry("餘", d, "IMOD", OperandPattern.TWO_IMM,
                       "Modulo / remainder", "餘數：除之不尽者", arity=2, precedence=20),
            GlyphEntry("負", d, "INEG", OperandPattern.ONE_IMM,
                       "Negate a value", "負數：正負相反而已", arity=1, precedence=30),
            GlyphEntry("冪", d, "IEXP", OperandPattern.TWO_IMM,
                       "Exponentiation", "冪：自乘之數", arity=2, precedence=25),
            GlyphEntry("根", d, "IROOT", OperandPattern.ONE_IMM,
                       "Square root", "開方：求其根", arity=1, precedence=25),

            # ── Comparison operators (比較) ───────────────────
            GlyphEntry("等", d, "IEQ", OperandPattern.TWO_IMM,
                       "Compare equal", "等於：兩數相同", arity=2, precedence=5),
            GlyphEntry("等於", d, "IEQ", OperandPattern.TWO_IMM,
                       "Compare equal (compound)", "等於：兩數相同", arity=2, precedence=5),
            GlyphEntry("大於", d, "IGT", OperandPattern.TWO_IMM,
                       "Compare greater than", "大於：此多於彼", arity=2, precedence=5),
            GlyphEntry("小於", d, "ILT", OperandPattern.TWO_IMM,
                       "Compare less than", "小於：此少於彼", arity=2, precedence=5),
            GlyphEntry("比", d, "ICMP", OperandPattern.TWO_IMM,
                       "General compare", "比較：判大小", arity=2, precedence=5),

            # ── Increment / Decrement ────────────────────────
            GlyphEntry("增", d, "INC", OperandPattern.ONE_REG,
                       "Increment register", "增一：加之", arity=1),
            GlyphEntry("減一", d, "DEC", OperandPattern.ONE_REG,
                       "Decrement register", "減一：損之", arity=1),

            # ── Accumulation ─────────────────────────────────
            GlyphEntry("合", d, "IADD", OperandPattern.TWO_REG,
                       "Sum / combine registers", "合：併而計之", arity=2),
            GlyphEntry("積", d, "IMUL", OperandPattern.TWO_REG,
                       "Product of registers", "積：累乘", arity=2),
            GlyphEntry("至", d, "LOAD", OperandPattern.REG_IMM,
                       "Range upper bound", "至：自甲至乙", arity=2),

            # ── Special values ───────────────────────────────
            GlyphEntry("極", d, "MOVI", OperandPattern.REG_IMM,
                       "Maximum / extreme value", "極：至大至小", arity=2),
            GlyphEntry("算", d, "PRINT", OperandPattern.ONE_IMM,
                       "Compute and display", "算：運算以示人", arity=1),
        ]
        for e in entries:
            self.register(e)

    def _load_confucian(self) -> None:
        """Load 儒 (Confucian) domain glyphs — 25 characters.

        The Confucian domain encodes the Five Constants (五常)
        and their extensions as programming operations. Every
        operation is filtered through 仁義禮智信.

        儒學 — the way of proper conduct, applied to computation.
        As Confucius said: 仁者安仁，知者利仁。
        (The benevolent find peace in benevolence; the wise find profit in it.)
        """
        d = ContextDomain.CONFUCIAN
        entries = [
            # ── Five Constants (五常) ────────────────────────
            GlyphEntry("仁", d, "VERIFY_TRUST", OperandPattern.ONE_STR,
                       "Benevolence: verify trust and distribute",
                       "仁者愛人：信之而後布之", arity=1),
            GlyphEntry("義", d, "CHECK_BOUNDS", OperandPattern.TWO_STR,
                       "Righteousness: validate bounds and correctness",
                       "義者宜也：合乎規矩", arity=2),
            GlyphEntry("禮", d, "CAP_REQUIRE", OperandPattern.ONE_STR,
                       "Ritual: require capability and orchestrate",
                       "禮者序也：各安其位", arity=1),
            GlyphEntry("智", d, "OPTIMIZE", OperandPattern.ONE_STR,
                       "Wisdom: optimize execution path",
                       "智者知也：擇其善者而從之", arity=1),
            GlyphEntry("信", d, "VERIFY_TRUST", OperandPattern.ONE_STR,
                       "Trust: verify integrity",
                       "信者誠也：無信不立", arity=1),

            # ── Extended virtues (德) ────────────────────────
            GlyphEntry("德", d, "TRUST_CHECK", OperandPattern.ONE_STR,
                       "Virtue: comprehensive trust check",
                       "德者得也：内得於己，外得於人", arity=1),
            GlyphEntry("誠", d, "VERIFY_TRUST", OperandPattern.ONE_STR,
                       "Sincerity: verify truthfulness",
                       "誠者天之道也：思誠者人之道也", arity=1),
            GlyphEntry("敬", d, "CAP_REQUIRE", OperandPattern.ONE_STR,
                       "Reverence: require respect / capability",
                       "敬人者人恆敬之", arity=1),
            GlyphEntry("恕", d, "CHECK_BOUNDS", OperandPattern.TWO_STR,
                       "Reciprocity: do unto others (symmetric check)",
                       "己所不欲勿施於人", arity=2),
            GlyphEntry("廉", d, "CHECK_BOUNDS", OperandPattern.ONE_STR,
                       "Integrity: check purity / no corruption",
                       "廉者潔也：不苟取", arity=1),

            # ── Philosophy (道 理) ───────────────────────────
            GlyphEntry("道", d, "NOP", OperandPattern.NONE,
                       "The Way: architectural principle (no-op marker)",
                       "道可道非常道：此為程之根本", arity=0),
            GlyphEntry("理", d, "ICMP", OperandPattern.TWO_IMM,
                       "Reason: logical comparison",
                       "理者分也：條分縷析", arity=2),
            GlyphEntry("中", d, "CHECK_BOUNDS", OperandPattern.TWO_IMM,
                       "Mean: check if value is within bounds",
                       "中庸之道：不偏不倚", arity=2),
            GlyphEntry("和", d, "IADD", OperandPattern.TWO_IMM,
                       "Harmony: balanced addition",
                       "和也者天下之達道也", arity=2),
            GlyphEntry("正", d, "CHECK_BOUNDS", OperandPattern.ONE_IMM,
                       "Correctness: validate correctness",
                       "正其誼不謀其利", arity=1),

            # ── Learning (學) ────────────────────────────────
            GlyphEntry("學", d, "CALL", OperandPattern.ADDR,
                       "Learning: call a knowledge subroutine",
                       "學而時習之：調用已知之程", arity=1),
            GlyphEntry("思", d, "PRINT", OperandPattern.ONE_STR,
                       "Thinking: analyze and display",
                       "學而不思則罔", arity=1),
            GlyphEntry("習", d, "RET", OperandPattern.NONE,
                       "Practice: return from subroutine",
                       "習之結果：歸而報之", arity=0),
            GlyphEntry("知", d, "OPTIMIZE", OperandPattern.ONE_STR,
                       "Wisdom: optimize based on knowledge",
                       "知之為知之：擇善而用", arity=1),

            # ── Social hierarchy (倫理) ─────────────────────
            GlyphEntry("君", d, "DELEGATE", OperandPattern.ONE_STR,
                       "Ruler: delegate to supervisory process",
                       "君君臣臣：上令下行", arity=1),
            GlyphEntry("臣", d, "TELL", OperandPattern.TWO_STR,
                       "Minister: report to superior",
                       "臣事君以忠", arity=2),
            GlyphEntry("民", d, "STORE", OperandPattern.REG_IMM,
                       "People: store data (payload)",
                       "民為邦本：數據為程之本", arity=2),

            # ── Extended operations ──────────────────────────
            GlyphEntry("善", d, "OPTIMIZE", OperandPattern.ONE_STR,
                       "Goodness: optimize for benevolence",
                       "止於至善", arity=1),
            GlyphEntry("天", d, "BROADCAST", OperandPattern.ONE_STR,
                       "Heaven: broadcast to all",
                       "天命之謂性：遍告天下", arity=1),
        ]
        for e in entries:
            self.register(e)

    def _load_military(self) -> None:
        """Load 兵 (Military) domain glyphs — 25 characters.

        The military domain maps Sun Tzu's Art of War (孫子兵法)
        to distributed systems operations. Every military concept
        has a precise computational equivalent.

        兵法 — the art of strategy, applied to computation.
        孫子曰：兵者，國之大事，死生之地，存亡之道，不可不察也。
        (War is the gravest affair of state; the road to survival or ruin.)
        """
        d = ContextDomain.MILITARY
        entries = [
            # ── Core operations (攻守進退) ──────────────────
            GlyphEntry("攻", d, "ATTACK", OperandPattern.ONE_STR,
                       "Attack: push data / send request",
                       "攻其不備：出其不意", arity=1),
            GlyphEntry("守", d, "DEFEND", OperandPattern.ONE_STR,
                       "Defend: buffer / protect / receive",
                       "善守者藏於九地之下", arity=1),
            GlyphEntry("進", d, "ADVANCE", OperandPattern.ONE_STR,
                       "Advance: proceed to next phase",
                       "進而不可御者，衝其虛也", arity=1),
            GlyphEntry("退", d, "RETREAT", OperandPattern.NONE,
                       "Withdraw: backoff / retry",
                       "退而不可追者，速而不可及也", arity=0),

            # ── Tactical formations (陣形) ──────────────────
            GlyphEntry("伏", d, "STORE", OperandPattern.REG_IMM,
                       "Ambush: lazy evaluation / deferred compute",
                       "伏兵：待機而發", arity=2),
            GlyphEntry("圍", d, "LOOP", OperandPattern.ADDR,
                       "Surround: encircle / round-robin",
                       "十則圍之：迴環不絕", arity=1),
            GlyphEntry("分", d, "IDIV", OperandPattern.TWO_IMM,
                       "Divide: partition / shard data",
                       "分而制之：各擊一處", arity=2),
            GlyphEntry("合", d, "IADD", OperandPattern.TWO_REG,
                       "Unite: aggregate / merge results",
                       "合軍聚眾：合而為一", arity=2),

            # ── Strategy (計謀) ──────────────────────────────
            GlyphEntry("計", d, "ICMP", OperandPattern.TWO_IMM,
                       "Strategy: compute and compare",
                       "廟算：多算勝少算不勝", arity=2),
            GlyphEntry("謀", d, "OPTIMIZE", OperandPattern.ONE_STR,
                       "Plot: strategic optimization",
                       "上兵伐謀：不戰而屈人之兵", arity=1),
            GlyphEntry("略", d, "JMP", OperandPattern.ADDR,
                       "Strategy: jump to strategic position",
                       "戰略：直取要害", arity=1),
            GlyphEntry("誘", d, "PUSH", OperandPattern.ONE_IMM,
                       "Lure: push bait onto stack",
                       "利而誘之：以利動之", arity=1),

            # ── Force composition (兵勢) ────────────────────
            GlyphEntry("正", d, "IADD", OperandPattern.TWO_IMM,
                       "Direct force: synchronous path",
                       "以正合：正面對敵", arity=2),
            GlyphEntry("奇", d, "JMP", OperandPattern.ADDR,
                       "Indirect force: asynchronous path",
                       "以奇勝：出奇制勝", arity=1),
            GlyphEntry("虛", d, "STORE", OperandPattern.REG_IMM,
                       "Empty: available capacity",
                       "避實擊虛：攻其空虛", arity=2),
            GlyphEntry("實", d, "LOAD", OperandPattern.REG_IMM,
                       "Full: at capacity / loaded value",
                       "實則避之：不與爭鋒", arity=2),

            # ── Terrain (地形) ──────────────────────────────
            GlyphEntry("山", d, "DEFEND", OperandPattern.ONE_STR,
                       "Mountain: high-latency path / defend high ground",
                       "居高臨下", arity=1),
            GlyphEntry("水", d, "PUSH", OperandPattern.ONE_IMM,
                       "Water: streaming data / flow",
                       "兵形象水：避高而趨下", arity=1),
            GlyphEntry("林", d, "LOOP", OperandPattern.ADDR,
                       "Forest: dense complex topology / loop",
                       "山林險阻：複雜之境", arity=1),
            GlyphEntry("火", d, "HALT", OperandPattern.NONE,
                       "Fire: emergency purge / shutdown",
                       "火攻：焚毀以絕", arity=0),

            # ── Outcome (勝敗) ──────────────────────────────
            GlyphEntry("勝", d, "JE", OperandPattern.ADDR,
                       "Victory: jump on success",
                       "知勝之道：知己知彼", arity=1),
            GlyphEntry("敗", d, "JNE", OperandPattern.ADDR,
                       "Defeat: jump on failure",
                       "知己知彼百戰不殆", arity=1),
            GlyphEntry("降", d, "RET", OperandPattern.NONE,
                       "Surrender: return / yield",
                       "不戰而降：歸順以存", arity=0),
            GlyphEntry("截", d, "JZ", OperandPattern.ADDR_REG,
                       "Intercept: jump if zero / cut off",
                       "截斷退路", arity=2),
            GlyphEntry("營", d, "PUSH", OperandPattern.ONE_IMM,
                       "Camp: establish staging area on stack",
                       "安營紮寨", arity=1),
        ]
        for e in entries:
            self.register(e)

    def _load_agent(self) -> None:
        """Load 使 (Agent) domain glyphs — 20 characters.

        The agent domain handles inter-agent communication.
        Characters in this domain map to message passing,
        delegation, and coordination operations.

        使者 — the art of communication between agents.
        古之使者，銜命而出，傳達王命，往返如流。
        (Ancient envoys carried mandates, delivered royal commands,
        and traveled back and forth like flowing water.)
        """
        d = ContextDomain.AGENT
        entries = [
            # ── Communication (通訊) ────────────────────────
            GlyphEntry("告", d, "TELL", OperandPattern.TWO_STR,
                       "Tell: send message to agent",
                       "告訴：遣使傳言", arity=2),
            GlyphEntry("問", d, "ASK", OperandPattern.TWO_STR,
                       "Ask: query an agent",
                       "詢問：遣使求答", arity=2),
            GlyphEntry("命", d, "DELEGATE", OperandPattern.TWO_STR,
                       "Delegate: assign task to agent",
                       "命令：遣使任事", arity=2),
            GlyphEntry("令", d, "BROADCAST", OperandPattern.ONE_STR,
                       "Broadcast: send to all agents",
                       "命令：傳令天下", arity=1),
            GlyphEntry("信", d, "TELL", OperandPattern.TWO_STR,
                       "Message: send a letter / trust message",
                       "書信：傳書致意", arity=2),

            # ── Response (回應) ─────────────────────────────
            GlyphEntry("答", d, "RET", OperandPattern.NONE,
                       "Answer: return response",
                       "回答：歸報所問", arity=0),
            GlyphEntry("報", d, "TELL", OperandPattern.TWO_STR,
                       "Report: send status report",
                       "報告：上報情況", arity=2),
            GlyphEntry("應", d, "JE", OperandPattern.ADDR,
                       "Respond: jump on expected response",
                       "應答：如期而至", arity=1),

            # ── Request / Permission (請求) ─────────────────
            GlyphEntry("請", d, "ASK", OperandPattern.TWO_STR,
                       "Request: ask for something",
                       "請求：有所求於人", arity=2),
            GlyphEntry("求", d, "ASK", OperandPattern.ONE_STR,
                       "Seek: query for information",
                       "求知：索求答案", arity=1),
            GlyphEntry("許", d, "CAP_REQUIRE", OperandPattern.ONE_STR,
                       "Permit: grant capability",
                       "許可：允其所請", arity=1),
            GlyphEntry("拒", d, "RETREAT", OperandPattern.NONE,
                       "Refuse: reject / deny",
                       "拒絕：不從所請", arity=0),

            # ── Commitment (承諾) ───────────────────────────
            GlyphEntry("承", d, "PUSH", OperandPattern.ONE_IMM,
                       "Accept: commit to task (push to stack)",
                       "承諾：肩負其責", arity=1),
            GlyphEntry("諾", d, "CAP_REQUIRE", OperandPattern.ONE_STR,
                       "Promise: require capability fulfillment",
                       "諾言：一諾千金", arity=1),
            GlyphEntry("約", d, "DELEGATE", OperandPattern.TWO_STR,
                       "Agreement: establish contract",
                       "約定：盟約互信", arity=2),
            GlyphEntry("盟", d, "BROADCAST", OperandPattern.ONE_STR,
                       "Alliance: broadcast alliance formation",
                       "盟約：結盟公告", arity=1),

            # ── Dispatch (派遣) ─────────────────────────────
            GlyphEntry("使", d, "DELEGATE", OperandPattern.TWO_STR,
                       "Dispatch: send envoy",
                       "出使：遣使而行", arity=2),
            GlyphEntry("差", d, "CALL", OperandPattern.ADDR,
                       "Assign: call agent subroutine",
                       "差遣：指派任務", arity=1),
            GlyphEntry("傳", d, "TELL", OperandPattern.TWO_STR,
                       "Transmit: pass message along",
                       "傳遞：轉達其意", arity=2),
            GlyphEntry("遞", d, "PUSH", OperandPattern.ONE_IMM,
                       "Deliver: push data to destination",
                       "遞送：送達其物", arity=1),
            GlyphEntry("收", d, "POP", OperandPattern.ONE_REG,
                       "Receive: pop incoming data",
                       "收取：受其所遺", arity=1),
        ]
        for e in entries:
            self.register(e)

    def _load_control(self) -> None:
        """Load 制 (Control) domain glyphs — 20 characters.

        The control domain handles program flow: conditionals,
        loops, jumps, and execution ordering. These characters
        form the skeleton of any 文言 program.

        控制 — the art of program flow.
        若者，有所擇也。則者，有所從也。
        循者，周而復始也。終者，止也。
        """
        d = ContextDomain.CONTROL
        entries = [
            # ── Conditionals (條件) ─────────────────────────
            GlyphEntry("若", d, "JZ", OperandPattern.ADDR_REG,
                       "If / conditional: jump if zero",
                       "若：設其條件而擇", arity=2, precedence=2),
            GlyphEntry("如", d, "JZ", OperandPattern.ADDR_REG,
                       "As if: conditional (variant)",
                       "如：若然也", arity=2),
            GlyphEntry("則", d, "SEQUENCE", OperandPattern.NONE,
                       "Then: sequential execution marker",
                       "則：承上啟下", arity=0),
            GlyphEntry("否", d, "JNZ", OperandPattern.ADDR_REG,
                       "Otherwise: jump if not zero",
                       "否：不然也", arity=2),

            # ── Loops (循環) ────────────────────────────────
            GlyphEntry("循", d, "LOOP", OperandPattern.ADDR,
                       "Loop: repeat from address",
                       "循環：周而復始", arity=1),
            GlyphEntry("遍", d, "LOOP", OperandPattern.ADDR_REG,
                       "Iterate: loop over all",
                       "遍歷：逐一而行", arity=2),
            GlyphEntry("次", d, "INC", OperandPattern.ONE_REG,
                       "Next iteration: increment counter",
                       "依次：逐一加之", arity=1),
            GlyphEntry("終", d, "HALT", OperandPattern.NONE,
                       "End: halt execution",
                       "終止：至止不復", arity=0),

            # ── Jumps (跳轉) ────────────────────────────────
            GlyphEntry("跳", d, "JMP", OperandPattern.ADDR,
                       "Jump: unconditional transfer",
                       "跳轉：直達其處", arity=1),
            GlyphEntry("歸", d, "RET", OperandPattern.NONE,
                       "Return: return from subroutine",
                       "歸來：回至原處", arity=0),
            GlyphEntry("始", d, "MOVI", OperandPattern.REG_IMM,
                       "Begin: initialize register",
                       "開始：初始之值", arity=2),
            GlyphEntry("止", d, "HALT", OperandPattern.NONE,
                       "Stop: halt execution (variant of 終)",
                       "停止：不復行也", arity=0),

            # ── Continuation (延續) ──────────────────────────
            GlyphEntry("續", d, "JMP", OperandPattern.ADDR,
                       "Continue: proceed to next section",
                       "繼續：不斷而行", arity=1),
            GlyphEntry("斷", d, "HALT", OperandPattern.NONE,
                       "Break: interrupt / halt",
                       "中斷：戛然而止", arity=0),

            # ── Waiting (等待) ──────────────────────────────
            GlyphEntry("等", d, "JZ", OperandPattern.ADDR_REG,
                       "Wait: block until condition met",
                       "等待：俟其至也", arity=2),
            GlyphEntry("待", d, "JZ", OperandPattern.ADDR_REG,
                       "Await: wait for condition (variant)",
                       "期待：有所待也", arity=2),

            # ── Selection (選擇) ────────────────────────────
            GlyphEntry("擇", d, "JE", OperandPattern.ADDR,
                       "Select: branch based on comparison",
                       "選擇：擇其善者", arity=1),
            GlyphEntry("判", d, "ICMP", OperandPattern.TWO_IMM,
                       "Judge: compare and set flags",
                       "判斷：明辨是非", arity=2),
            GlyphEntry("分", d, "JE", OperandPattern.ADDR,
                       "Branch: fork execution path",
                       "分道：各行其是", arity=1),
        ]
        for e in entries:
            self.register(e)


# ═══════════════════════════════════════════════════════════════
# Module-Level Singleton
# ═══════════════════════════════════════════════════════════════

# The global glyph table — initialized once at import time
GLYPH_TABLE = GlyphTable()


# ═══════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════

def lookup_glyph(domain: ContextDomain, character: str) -> GlyphEntry | None:
    """Look up a character's dispatch entry in a given domain.

    Convenience wrapper around GLYPH_TABLE.lookup().

    Args:
        domain: The active textual domain.
        character: A single Chinese character.

    Returns:
        The GlyphEntry, or None if undefined.
    """
    return GLYPH_TABLE.lookup(domain, character)


def lookup_glyph_all(character: str) -> dict[ContextDomain, GlyphEntry]:
    """Look up a character across all domains.

    Shows the polymorphic nature: same character, different bytecode.

    Args:
        character: A single Chinese character.

    Returns:
        Dict mapping domain → GlyphEntry.
    """
    return GLYPH_TABLE.lookup_all_domains(character)


def compile_glyph(domain: ContextDomain, character: str,
                  operands: list[Any] | None = None) -> dict[str, Any] | None:
    """Compile a single character to a VM instruction representation.

    This is the core of the glyph dispatch system: given a domain
    and a character, produce the opcode and resolved operands.

    Args:
        domain: The active textual domain.
        character: The character to compile.
        operands: Optional pre-resolved operands.

    Returns:
        Dict with 'opcode', 'operand_pattern', and 'operands' keys,
        or None if the character is not defined in this domain.
    """
    entry = GLYPH_TABLE.lookup(domain, character)
    if entry is None:
        return None

    return {
        "opcode": entry.opcode,
        "operand_pattern": entry.operand_pattern.value,
        "operands": operands or [],
        "description": entry.description,
        "arity": entry.arity,
        "precedence": entry.precedence,
    }


def glyph_info(character: str) -> str:
    """Show polymorphic dispatch info for a character.

    Args:
        character: The character to inspect.

    Returns:
        Formatted string showing all domain mappings.
    """
    return GLYPH_TABLE.polymorphic_info(character)


def domain_character_count() -> dict[ContextDomain, int]:
    """Count characters defined in each domain.

    Returns:
        Dict mapping domain → character count.
    """
    counts: dict[ContextDomain, int] = {}
    for domain in ContextDomain:
        counts[domain] = len(GLYPH_TABLE.characters_for_domain(domain))
    return counts


def total_glyph_count() -> int:
    """Total number of glyph entries across all domains."""
    return GLYPH_TABLE.total_entries


def polymorphic_characters() -> list[str]:
    """Find all characters defined in more than one domain.

    These are the truly polymorphic characters — the ones that
    demonstrate 以文意定義 (meaning by context).

    Returns:
        List of characters sorted by number of domains (most first).
    """
    result: list[tuple[str, int]] = []
    for char, entries in GLYPH_TABLE._by_character.items():
        if len(entries) > 1:
            result.append((char, len(entries)))
    result.sort(key=lambda x: -x[1])
    return [char for char, _ in result]
