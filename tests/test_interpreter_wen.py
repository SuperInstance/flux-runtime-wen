"""
Tests for 文言解释器 — Classical Chinese FLUX Interpreter

Test categories:
1. Arithmetic operations (加减乘除)
2. Register operations (以 Rn 为 v)
3. Control flow (当, 若, 止)
4. Agent communication (告, 问, 遍告)
5. Confucian operations (仁义礼智信)
6. Military operations (攻守退进)
7. Context-dependent interpretation
8. Four-character programs
9. Tokenization
10. Chinese numeral parsing
11. Range/accumulation operations
12. Multi-line programs
13. Edge cases
"""

import pytest

from flux_wen.context import (
    ContextDomain,
    ContextStack,
    parse_chinese_number,
    CNUMERALS,
)
from flux_wen.interpreter import (
    Instruction,
    WenyanInterpreter,
    tokenize,
    tokens_to_string,
    resolve_operand,
)


# ═══════════════════════════════════════════════════════════════
# 1. Tokenization tests
# ═══════════════════════════════════════════════════════════════

class TestTokenization:
    """字即词 — each character is one token."""

    def test_single_chinese_number(self):
        tokens = tokenize("三")
        assert len(tokens) == 1
        assert tokens[0].char == "三"
        assert tokens[0].category == "number"

    def test_arithmetic_expression(self):
        tokens = tokenize("三加四")
        assert len(tokens) == 3
        assert tokens[0].char == "三"
        assert tokens[0].category == "number"
        assert tokens[1].char == "加"
        assert tokens[1].category == "operator"
        assert tokens[2].char == "四"
        assert tokens[2].category == "number"

    def test_register_token(self):
        tokens = tokenize("R0")
        assert len(tokens) == 1
        assert tokens[0].char == "R0"
        assert tokens[0].category == "register"

    def test_register_multi_digit(self):
        tokens = tokenize("R10")
        assert len(tokens) == 1
        assert tokens[0].char == "R10"
        assert tokens[0].category == "register"

    def test_mixed_expression(self):
        tokens = tokenize("以 R0 为七")
        chars = [t.char for t in tokens]
        assert "以" in chars
        assert "R0" in chars
        assert "为" in chars
        assert "七" in chars

    def test_whitespace_ignored(self):
        t1 = tokenize("三加四")
        t2 = tokenize("三 加 四")
        assert tokens_to_string(t1) == tokens_to_string(t2)

    def test_keyword_categories(self):
        tokens = tokenize("加于与为以合归当若告问遍止")
        keywords = [t.char for t in tokens if t.category == "keyword"]
        assert len(keywords) >= 10


# ═══════════════════════════════════════════════════════════════
# 2. Chinese numeral parsing
# ═══════════════════════════════════════════════════════════════

class TestChineseNumerals:
    """文言数字 — classical Chinese numbers."""

    def test_single_digits(self):
        assert parse_chinese_number("一") == 1
        assert parse_chinese_number("二") == 2
        assert parse_chinese_number("三") == 3
        assert parse_chinese_number("四") == 4
        assert parse_chinese_number("五") == 5
        assert parse_chinese_number("六") == 6
        assert parse_chinese_number("七") == 7
        assert parse_chinese_number("八") == 8
        assert parse_chinese_number("九") == 9
        assert parse_chinese_number("零") == 0

    def test_ten(self):
        assert parse_chinese_number("十") == 10

    def test_compound_numbers(self):
        assert parse_chinese_number("十五") == 15
        assert parse_chinese_number("三十二") == 32
        assert parse_chinese_number("一百") == 100

    def test_empty_string(self):
        assert parse_chinese_number("") is None

    def test_non_numeric(self):
        assert parse_chinese_number("加") is None


# ═══════════════════════════════════════════════════════════════
# 3. Arithmetic operations — 四字成程
# ═══════════════════════════════════════════════════════════════

class TestArithmetic:
    """加减乘除 — basic arithmetic."""

    def test_add_with_yu(self):
        """加三于四 → 7 (add three to four)"""
        interp = WenyanInterpreter()
        result = interp.run("加三于四")
        assert result == 7

    def test_add_word_order(self):
        """三加四 → 7 (three add four)"""
        interp = WenyanInterpreter()
        result = interp.run("三加四")
        assert result == 7

    def test_multiply(self):
        """三乘四 → 12"""
        interp = WenyanInterpreter()
        result = interp.run("三乘四")
        assert result == 12

    def test_subtract(self):
        """七减二 → 5"""
        interp = WenyanInterpreter()
        result = interp.run("七减二")
        assert result == 5

    def test_divide(self):
        """十除以三 → 3 (integer division)"""
        interp = WenyanInterpreter()
        result = interp.run("十除以三")
        assert result == 3

    def test_divide_by_zero_safe(self):
        """十除以零 should not crash."""
        interp = WenyanInterpreter()
        interp.run("十除以零")
        assert "除以零" in " ".join(interp.log)

    def test_larger_numbers(self):
        """五加八 → 13"""
        interp = WenyanInterpreter()
        result = interp.run("五加八")
        assert result == 13

    def test_arabic_numerals(self):
        """Arabic digits also work."""
        interp = WenyanInterpreter()
        result = interp.run("3加4")
        assert result == 7


# ═══════════════════════════════════════════════════════════════
# 4. Register operations
# ═══════════════════════════════════════════════════════════════

class TestRegisters:
    """寄存器操作 — register management."""

    def test_movi_chinese_numeral(self):
        """以 R0 为七 → R0 = 7"""
        interp = WenyanInterpreter()
        interp.run("以 R0 为七")
        assert interp.context.get_register(0) == 7

    def test_movi_arabic(self):
        """以 R0 为 42 → R0 = 42"""
        interp = WenyanInterpreter()
        interp.run("以 R0 为 42")
        assert interp.context.get_register(0) == 42

    def test_register_combine(self):
        """R0 与 R1 合 → add two registers."""
        interp = WenyanInterpreter()
        interp.compile("以 R0 为七\n以 R1 为三\nR0 与 R1 合")
        result = interp.run()
        assert result == 10

    def test_register_multiply(self):
        """R0 与 R1 乘 → multiply two registers."""
        interp = WenyanInterpreter()
        interp.compile("以 R0 为五\n以 R1 为四\nR0 与 R1 乘")
        result = interp.run()
        assert result == 20

    def test_return_register(self):
        """归 R0 → return R0's value."""
        interp = WenyanInterpreter()
        interp.compile("以 R0 为四十二\n归 R0")
        result = interp.run()
        assert result == 42


# ═══════════════════════════════════════════════════════════════
# 5. Range and accumulation
# ═══════════════════════════════════════════════════════════════

class TestRangeAccumulation:
    """至合 — range sum operations."""

    def test_range_sum_simple(self):
        """一至五合 → 1+2+3+4+5 = 15"""
        interp = WenyanInterpreter()
        result = interp.run("一至五合")
        assert result == 15

    def test_range_sum_gauss(self):
        """一至十合 → 55 (Gauss's formula)"""
        interp = WenyanInterpreter()
        result = interp.run("一至十合")
        assert result == 55

    def test_range_sum_arabic(self):
        """1至5合 → 15"""
        interp = WenyanInterpreter()
        result = interp.run("1至5合")
        assert result == 15


# ═══════════════════════════════════════════════════════════════
# 6. Control flow
# ═══════════════════════════════════════════════════════════════

class TestControlFlow:
    """当若止 — control flow."""

    def test_halt(self):
        """止 → stops execution."""
        interp = WenyanInterpreter()
        interp.run("止")
        assert not interp.running

    def test_whilenz_recognized(self):
        """当 R0 非零 → WHILENZ instruction compiled."""
        interp = WenyanInterpreter()
        interp.compile("当 R0 非零")
        assert len(interp.program) == 1
        assert interp.program[0].opcode == "WHILENZ"

    def test_cond_recognized(self):
        """若 R0 为正 → COND instruction compiled."""
        interp = WenyanInterpreter()
        interp.compile("若 R0 为正")
        assert len(interp.program) == 1
        assert interp.program[0].opcode == "COND"


# ═══════════════════════════════════════════════════════════════
# 7. Agent communication
# ═══════════════════════════════════════════════════════════════

class TestAgentCommunication:
    """告问遍告 — agent messaging."""

    def test_tell(self):
        """告 张三 你好 → TELL instruction."""
        interp = WenyanInterpreter()
        interp.compile("告 张三 你好")
        assert interp.program[0].opcode == "TELL"
        assert interp.program[0].operands[0] == "张三"
        assert interp.program[0].operands[1] == "你好"

    def test_ask(self):
        """问 李四 天气 → ASK instruction."""
        interp = WenyanInterpreter()
        interp.compile("问 李四 天气")
        assert interp.program[0].opcode == "ASK"
        assert interp.program[0].operands[0] == "李四"
        assert interp.program[0].operands[1] == "天气"

    def test_broadcast(self):
        """遍告 全体集合 → BROADCAST instruction."""
        interp = WenyanInterpreter()
        interp.compile("遍告 全体集合")
        assert interp.program[0].opcode == "BROADCAST"
        assert interp.program[0].operands[0] == "全体集合"

    def test_tell_execution_logs(self):
        """Executing TELL produces log entry."""
        interp = WenyanInterpreter()
        interp.run("告 张三 今日天晴")
        assert any("张三" in entry for entry in interp.log)


# ═══════════════════════════════════════════════════════════════
# 8. Confucian operations (五常)
# ═══════════════════════════════════════════════════════════════

class TestConfucianOperations:
    """仁义礼智信 — the five constant operations."""

    def test_ren_distribute(self):
        """仁 全体 → DISTRIBUTE."""
        interp = WenyanInterpreter()
        interp.compile("仁 全体")
        assert interp.program[0].opcode == "DISTRIBUTE"

    def test_yi_validate(self):
        """义 数据 → VALIDATE."""
        interp = WenyanInterpreter()
        interp.compile("义 数据")
        assert interp.program[0].opcode == "VALIDATE"

    def test_li_orchestrate(self):
        """礼 流程 → ORCHESTRATE."""
        interp = WenyanInterpreter()
        interp.compile("礼 流程")
        assert interp.program[0].opcode == "ORCHESTRATE"

    def test_zhi_optimize(self):
        """智 算法 → OPTIMIZE."""
        interp = WenyanInterpreter()
        interp.compile("智 算法")
        assert interp.program[0].opcode == "OPTIMIZE"

    def test_xin_verify(self):
        """信 结果 → VERIFY."""
        interp = WenyanInterpreter()
        interp.compile("信 结果")
        assert interp.program[0].opcode == "VERIFY"

    def test_confucian_execution_logs(self):
        """Confucian operations produce log entries."""
        interp = WenyanInterpreter()
        interp.run("仁 天下\n义 规矩\n礼 秩序\n智 方法\n信 承诺")
        log_text = " ".join(interp.log)
        assert "分布" in log_text
        assert "验证" in log_text
        assert "编排" in log_text
        assert "优化" in log_text
        assert "核实" in log_text


# ═══════════════════════════════════════════════════════════════
# 9. Military operations
# ═══════════════════════════════════════════════════════════════

class TestMilitaryOperations:
    """攻守退进 — military operations."""

    def test_attack(self):
        interp = WenyanInterpreter()
        interp.compile("攻 敌阵")
        assert interp.program[0].opcode == "ATTACK"

    def test_defend(self):
        interp = WenyanInterpreter()
        interp.compile("守 城池")
        assert interp.program[0].opcode == "DEFEND"

    def test_withdraw(self):
        interp = WenyanInterpreter()
        interp.compile("退")
        assert interp.program[0].opcode == "WITHDRAW"

    def test_advance(self):
        interp = WenyanInterpreter()
        interp.compile("进 前方")
        assert interp.program[0].opcode == "ADVANCE"


# ═══════════════════════════════════════════════════════════════
# 10. Context-dependent interpretation (以文意定義)
# ═══════════════════════════════════════════════════════════════

class TestContextDependent:
    """同字異義 — same character, different meaning."""

    def test_context_stack_push_pop(self):
        ctx = ContextStack()
        ctx.push(ContextDomain.MATHEMATICS)
        assert ctx.current.domain == ContextDomain.MATHEMATICS
        ctx.pop()
        assert ctx.current.domain == ContextDomain.GENERAL

    def test_context_stack_depth(self):
        ctx = ContextStack()
        assert ctx.depth == 0
        ctx.push()
        assert ctx.depth == 1
        ctx.push()
        assert ctx.depth == 2
        ctx.pop()
        assert ctx.depth == 1

    def test_polymorphic_resolve(self):
        """加 resolves differently based on domain."""
        ctx = ContextStack()
        ctx.push(ContextDomain.MATHEMATICS)
        assert ctx.resolve("加") == "IADD"
        ctx.pop()
        ctx.push(ContextDomain.CONFUCIAN)
        assert ctx.resolve("加") == "DISTRIBUTE"

    def test_polymorphic_multiply(self):
        """乘 resolves differently based on domain."""
        ctx = ContextStack()
        ctx.push(ContextDomain.MATHEMATICS)
        assert ctx.resolve("乘") == "IMUL"
        ctx.pop()
        ctx.push(ContextDomain.MILITARY)
        assert ctx.resolve("乘") == "ADVANCE"

    def test_register_storage_in_context(self):
        ctx = ContextStack()
        ctx.set_register(0, 42)
        ctx.set_register(1, 13)
        assert ctx.get_register(0) == 42
        assert ctx.get_register(1) == 13
        assert ctx.get_register(2) == 0  # default

    def test_variable_storage(self):
        ctx = ContextStack()
        ctx.set_var("name", "张三")
        assert ctx.get_var("name") == "张三"
        assert ctx.get_var("missing") is None
        assert ctx.get_var("missing", "default") == "default"


# ═══════════════════════════════════════════════════════════════
# 11. Multi-line programs
# ═══════════════════════════════════════════════════════════════

class TestMultiLine:
    """Multi-line programs — complete workflows."""

    def test_register_set_then_use(self):
        """Set register, then use in arithmetic."""
        interp = WenyanInterpreter()
        source = "以 R0 为七\n以 R1 为三\nR0 与 R1 合"
        interp.compile(source)
        assert len(interp.program) == 3
        result = interp.run(source)
        assert result == 10

    def test_multi_step_calculation(self):
        """Multiple operations in sequence."""
        interp = WenyanInterpreter()
        source = "三加四\n五乘二"
        interp.compile(source)
        assert len(interp.program) == 2
        interp.run(source)
        # R0 should be 10 (last operation: 5*2)
        assert interp.context.get_register(0) == 10

    def test_program_with_comments(self):
        """注: prefix creates NOP comments."""
        interp = WenyanInterpreter()
        source = "注：这是注释\n三加四"
        interp.compile(source)
        # First instruction is NOP (comment)
        assert interp.program[0].opcode == "NOP"
        # Second is IADD
        assert interp.program[1].opcode == "IADD"

    def test_blank_lines_ignored(self):
        interp = WenyanInterpreter()
        interp.compile("\n\n三加四\n\n")
        assert len(interp.program) == 1

    def test_hash_comments_ignored(self):
        interp = WenyanInterpreter()
        interp.compile("# comment\n三加四")
        assert len(interp.program) == 1


# ═══════════════════════════════════════════════════════════════
# 12. Operand resolution
# ═══════════════════════════════════════════════════════════════

class TestOperandResolution:
    """resolve_operand — resolving values from various formats."""

    def test_resolve_register(self):
        ctx = ContextStack()
        ctx.set_register(0, 42)
        assert resolve_operand("R0", ctx) == 42

    def test_resolve_chinese_numeral(self):
        ctx = ContextStack()
        assert resolve_operand("七", ctx) == 7

    def test_resolve_arabic_numeral(self):
        ctx = ContextStack()
        assert resolve_operand("42", ctx) == 42

    def test_resolve_string_passthrough(self):
        ctx = ContextStack()
        assert resolve_operand("张三", ctx) == "张三"

    def test_resolve_int_passthrough(self):
        ctx = ContextStack()
        assert resolve_operand(7, ctx) == 7


# ═══════════════════════════════════════════════════════════════
# 13. Disassembly and inspection
# ═══════════════════════════════════════════════════════════════

class TestDisassembly:
    """反汇编 — program inspection."""

    def test_disassemble_simple(self):
        interp = WenyanInterpreter()
        interp.compile("三加四")
        lines = interp.disassemble()
        assert len(lines) == 1
        assert "IADD" in lines[0]

    def test_disassemble_multi_line(self):
        interp = WenyanInterpreter()
        interp.compile("以 R0 为七\n三加四")
        lines = interp.disassemble()
        assert len(lines) == 2
        assert "MOVI" in lines[0]
        assert "IADD" in lines[1]

    def test_source_in_disassembly(self):
        interp = WenyanInterpreter()
        interp.compile("三加四")
        lines = interp.disassemble()
        assert "三加四" in lines[0]

    def test_registers_view(self):
        interp = WenyanInterpreter()
        interp.run("以 R0 为七\n以 R1 为三")
        regs = interp.registers()
        assert regs["R0"] == 7
        assert regs["R1"] == 3
        assert "R2" not in regs


# ═══════════════════════════════════════════════════════════════
# 14. Reset and isolation
# ═══════════════════════════════════════════════════════════════

class TestReset:
    """重置 — VM state isolation."""

    def test_reset_clears_state(self):
        interp = WenyanInterpreter()
        interp.run("以 R0 为七")
        assert interp.context.get_register(0) == 7
        interp.reset()
        assert interp.context.get_register(0) == 0
        assert len(interp.program) == 0
        assert len(interp.log) == 0

    def test_sequential_runs(self):
        """Each run should be independent."""
        interp = WenyanInterpreter()
        r1 = interp.run("三加四")
        interp.reset()
        r2 = interp.run("五乘二")
        assert r1 == 7
        assert r2 == 10


# ═══════════════════════════════════════════════════════════════
# 15. Edge cases
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases and robustness."""

    def test_unknown_line_becomes_nop(self):
        """Unrecognized lines become NOP."""
        interp = WenyanInterpreter()
        interp.compile("xyznotaword")
        assert interp.program[0].opcode == "NOP"

    def test_empty_source(self):
        interp = WenyanInterpreter()
        interp.compile("")
        assert len(interp.program) == 0

    def test_whitespace_only(self):
        interp = WenyanInterpreter()
        interp.compile("   \n  \n  ")
        assert len(interp.program) == 0

    def test_reverse_casting(self):
        """以七为 R0 — reverse form of MOVI."""
        interp = WenyanInterpreter()
        interp.compile("以七为 R0")
        assert interp.program[0].opcode == "MOVI"
        assert interp.program[0].operands[0] == 0

    def test_divide_without_yi(self):
        """十除三 — divide without 以."""
        interp = WenyanInterpreter()
        interp.compile("十除三")
        assert interp.program[0].opcode == "IDIV"

    def test_execution_log_populated(self):
        interp = WenyanInterpreter()
        interp.run("三加四")
        assert len(interp.log) > 0
        assert "加" in interp.log[0]
