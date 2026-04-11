"""
CLI — 命令行界面

Classical Chinese commands:
  啟 (qǐ) — Initialize / show banner
  譯 (yì) — Translate (compile & disassemble)
  行 (xíng) — Execute (compile & run)
  觀 (guān) — Inspect (show registers, context, logs)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, __title__
from .interpreter import WenyanInterpreter, tokenize, tokens_to_string


BANNER = r"""
╔══════════════════════════════════════════════╗
║     流星 · 文言 programming                  ║
║     FLUX — Classical Chinese Runtime         ║
║                                              ║
║     零语法 · 纯概念 · 四字成程                ║
║     No grammar · Pure concept · 4 chars       ║
║                                              ║
║     加三于四  → 7                              ║
║     以 R0 为七  → R0 = 7                      ║
║     三乘四  → 12                               ║
╚══════════════════════════════════════════════╝
"""


def cmd_init(args: argparse.Namespace) -> None:
    """啟 — Initialize: show banner and system info."""
    print(BANNER)
    print(f"  版本 / Version: {__version__}")
    print(f"  标题 / Title:    {__title__}")
    print()
    print("  指令 / Commands:")
    print("    啟 (init)     显示此信息 / Show this banner")
    print("    譯 (compile)  编译并反汇编 / Compile & disassemble")
    print("    行 (run)      执行程序 / Execute program")
    print("    觀 (inspect)  查看状态 / Inspect state")
    print()
    print("  用法 / Usage:")
    print("    flux-wen 啟")
    print("    flux-wen 譯 '加三于四'")
    print("    flux-wen 行 '加三于四'")
    print("    flux-wen 行 -f program.wen")
    print("    flux-wen 觀 -f program.wen")


def cmd_compile(args: argparse.Namespace) -> None:
    """譯 — Compile and disassemble."""
    source = _read_source(args)
    if source is None:
        return

    interp = WenyanInterpreter()
    interp.compile(source)

    print(f"  源 / Source: {source}")
    print(f"  指令数 / Instructions: {len(interp.program)}")
    print()
    print("  反汇编 / Disassembly:")
    for line in interp.disassemble():
        print(f"    {line}")

    # Show tokens
    print()
    print("  字 / Tokens:")
    tokens = tokenize(source)
    for t in tokens:
        print(f"    [{t.category}] {t.char}")


def cmd_run(args: argparse.Namespace) -> None:
    """行 — Execute a program."""
    source = _read_source(args)
    if source is None:
        return

    interp = WenyanInterpreter()

    print(f"  执行 / Running: {source}")
    print()

    result = interp.run(source)

    print()
    print(f"  结果 / Result (R0): {result}")
    print(f"  寄存器 / Registers: {interp.registers()}")
    if interp.log:
        print()
        print("  执行日志 / Execution log:")
        for entry in interp.log:
            print(f"    {entry}")


def cmd_inspect(args: argparse.Namespace) -> None:
    """觀 — Inspect state after compilation/execution."""
    source = _read_source(args)
    if source is None:
        return

    interp = WenyanInterpreter()
    interp.compile(source)

    if args.execute:
        interp.run()

    print(f"  源 / Source: {source}")
    print()
    print(f"  指令 / Instructions:")
    for i, instr in enumerate(interp.program):
        print(f"    {i}: {instr}")
    print()
    print(f"  寄存器 / Registers: {interp.registers()}")
    print(f"  境深 / Context depth: {interp.context.depth}")
    print(f"  境域 / Domain: {interp.context.current.domain.value}")
    if interp.log:
        print()
        print("  志 / Log:")
        for entry in interp.log:
            print(f"    {entry}")


def _read_source(args: argparse.Namespace) -> str | None:
    """Read source from file or command line argument."""
    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"  错 / Error: 文件不存在 / File not found: {path}")
            return None
        return path.read_text(encoding="utf-8")

    if args.source:
        return args.source

    # Read from stdin
    if not sys.stdin.isatty():
        return sys.stdin.read()

    print("  错 / Error: 请提供程序源码 / Please provide source code")
    print("    flux-wen 行 '加三于四'")
    print("    flux-wen 行 -f program.wen")
    return None


def main() -> None:
    """Main entry point — flux-wen CLI."""
    parser = argparse.ArgumentParser(
        prog="flux-wen",
        description="流星 · 文言编程 — Classical Chinese Programming Runtime",
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="命令 / Command")

    # 啟 — init
    p_init = subparsers.add_parser("啟", aliases=["init"], help="初始化 / Initialize")
    p_init.set_defaults(func=cmd_init)

    # 譯 — compile
    p_compile = subparsers.add_parser("譯", aliases=["compile"], help="编译 / Compile")
    p_compile.add_argument("source", nargs="?", help="源码 / Source code")
    p_compile.add_argument("-f", "--file", help="文件路径 / File path")
    p_compile.set_defaults(func=cmd_compile)

    # 行 — run
    p_run = subparsers.add_parser("行", aliases=["run"], help="执行 / Execute")
    p_run.add_argument("source", nargs="?", help="源码 / Source code")
    p_run.add_argument("-f", "--file", help="文件路径 / File path")
    p_run.set_defaults(func=cmd_run)

    # 觀 — inspect
    p_inspect = subparsers.add_parser("觀", aliases=["inspect"], help="查看 / Inspect")
    p_inspect.add_argument("source", nargs="?", help="源码 / Source code")
    p_inspect.add_argument("-f", "--file", help="文件路径 / File path")
    p_inspect.add_argument("-x", "--execute", action="store_true", help="也执行 / Also execute")
    p_inspect.set_defaults(func=cmd_inspect)

    args = parser.parse_args()

    if args.command:
        args.func(args)
    else:
        # Default: show banner
        cmd_init(args)


if __name__ == "__main__":
    main()
