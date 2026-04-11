"""
易經指令編碼 — I Ching Hexagram-to-Opcode Encoder

The 64 hexagrams of the I Ching form a 6-bit opcode address space (0–63).
Each hexagram maps to a primary opcode based on its semantic meaning in
Classical Chinese cosmology:

  ䷀ (乾/Heaven)  = 111111 = addr 63 → OP_CREATE (genesis/creation)
  ䷁ (坤/Earth)  = 000000 = addr  0 → OP_YIELD  (receptivity/input)
  ䷂ (屯/Difficulty) = addr 20 → OP_WAIT  (initial difficulty)
  ䷃ (蒙/Folly)    = addr 10 → OP_INIT  (beginner's mind)

The encoding follows the traditional binary structure:
  - Solid line (陽 yang) = 1
  - Broken line (陰 yin)  = 0
  - Lines read bottom to top as bits 0–5

卦即碼 — the hexagram IS the opcode.
爻即位 — the lines ARE the bits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .iching import (
    Hexagram,
    HEXAGRAMS_KING_WEN,
    name_to_hexagram,
    king_wen_to_hexagram,
    address_to_hexagram,
    Trigram,
)
from .vm import Opcode


# ═══════════════════════════════════════════════════════════════
# Hexagram → Opcode Semantic Mapping
# ═══════════════════════════════════════════════════════════════

# Each hexagram maps to an opcode based on its philosophical meaning.
# The mapping is NOT arbitrary — it follows the I Ching's own cosmological
# logic of transformation and change.

# Key mappings:
#   ䷀ 乾 (Heaven)    → OP_CREATE — pure yang = creation/genesis
#   ䷁ 坤 (Earth)     → OP_YIELD  — pure yin = receptivity/input
#   ䷣ 蒙 (Difficulty)  → OP_WAIT  — obstacles require patience
#   ䷴ 蒙 (Folly)    → OP_INIT  — beginner's mind = initialization
#   ䷔ 泰 (Peace)      → OP_JMP    — smooth flow = jump
#   ䷕ 否 (Standstill)  → OP_HALT   — stagnation = halt
#   ䷖ 既濟 (After Completion) → OP_RET — completion = return
#   ䷗ 未濟 (Before Completion) → OP_CALL — potential = call

_HEXAGRAM_OPCODE_NAMES: dict[int, str] = {
    1:  "OP_CREATE",     # 乾 — Heaven — creative genesis (all yang)
    2:  "OP_YIELD",      # 坤 — Earth — receptive input (all yin)
    3:  "OP_WAIT",       # 屯 — Difficulty — wait through obstacles
    4:  "OP_INIT",       # 蒙 — Youthful Folly — initial state
    5:  "OP_WAIT",       # 需 — Waiting — patience
    6:  "OP_CMP",        # 訟 — Conflict — comparison/conflict
    7:  "OP_LOOP",       # 師 — Army — organized force/loop
    8:  "OP_BIND",       # 比 — Holding Together — bind/unite
    9:  "OP_NARROW",     # 小畜 — Small Taming — narrow scope
    10: "OP_ADVANCE",    # 履 — Treading — advance carefully
    11: "OP_JMP",        # 泰 — Peace — smooth transition
    12: "OP_HALT",       # 否 — Standstill — stagnation
    13: "OP_BROADCAST", # 同人 — Fellowship — broadcast
    14: "OP_OWN",        # 大有 — Great Possession — own/store
    15: "OP_MOD",        # 謙 — Modesty — modular/remainder
    16: "OP_ENTHUSIASM", # 豫 — Enthusiasm — eager execution
    17: "OP_FOLLOW",     # 隨 — Following — tail-call/follow
    18: "OP_CORRECT",    # 蠱 — Grace — correction/validate
    19: "OP_SPLIT",      # 剝 — Splitting Apart — division
    20: "OP_RETURN",     # 復 — Return — turning point
    21: "OP_NOP",        # 無妄 — Innocence — no side effects
    22: "OP_STORE",      # 大畜 — Great Taming — store resources
    23: "OP_EAT",        # 頤 — Nourishing — consume
    24: "OP_EXCESS",     # 大過 — Great Excess — overflow
    25: "OP_NEG",        # 坎 — Abysmal Water — negate/fall
    26: "OP_LIGHT",      # 離 — Clinging Fire — illuminate
    27: "OP_FAMILY",     # 家人 — The Family — family scope
    28: "OP_OPPOSE",      # 睽 — Opposition — conditional branch
    29: "OP_GUARD",      # 蹇 — Obstruction — guard/check
    30: "OP_DELIVER",    # 解 — Deliverance — resolve
    31: "OP_SHRINK",      # 損 — Decrease — reduce
    32: "OP_GROW",       # 益 — Increase — amplify
    33: "OP_BREAK",      # 夬 — Breakthrough — force exit
    34: "OP_ENCOUNTER",   # 姤 — Coming to Meet — unexpected input
    35: "OP_GATHER",      # 萃 — Gathering — collect/aggregate
    36: "OP_RISE",        # 升 — Pushing Upward — ascend
    37: "OP_EXHAUST",     # 困 — Oppression — resource drain
    38: "OP_WELL",       # 井 — The Well — deep access
    39: "OP_REVOLUTION", # 革 — Revolution — transform
    40: "OP_VESSEL",     # 鼎 — The Cauldron — container/frame
    41: "OP_SHOCK",       # 震 — Arousing — interrupt/exception
    42: "OP_STILL",      # 艮 — Keeping Still — stabilize
    43: "OP_PROGRESS",   # 漸 — Development — iteration
    44: "OP_MARRY",      # 歸妹 — Marrying Maiden — join/sync
    45: "OP_FULL",        # 豐 — Abundance — full buffer
    46: "OP_WANDER",      # 旅 — Wandering — seek/search
    47: "OP_GENTLE",      # 巽 — Gentle — soft execution
    48: "OP_JOY",         # 兌 — Joyous — completion signal
    49: "OP_SCATTER",     # 渙 — Dispersion — distribute
    50: "OP_LIMIT",       # 節 — Limitation — bound check
    51: "OP_TRUTH",      # 中孚 — Inner Truth — verify/trust
    52: "OP_OVERSTEP",    # 小過 — Small Excess — slight overflow
    53: "OP_RET",         # 既濟 — After Completion — return result
    54: "OP_CALL",        # 未濟 — Before Completion — call/defer
    55: "OP_LOAD",        # ⬜ — first (from ䷀ symbol, char U+4DC0)
    56: "OP_STORE",       # ☷ — first (from ䷁ symbol, char U+2637)
}


# ═══════════════════════════════════════════════════════════════
# Full 64-Hexagram Semantic Description Table
# ═════════════════════════════════════════════════════════════════════════

_HEXAGRAM_SEMANTICS: dict[int, dict[str, str]] = {
    1:  {"opcode": "OP_CREATE", "english": "Heaven", "chinese": "乾",
         "binary": "111111", "description": "創生 — pure yang, genesis, creation from nothing",
         "upper_trigram": "乾", "lower_trigram": "乾",
         "upper_meaning": "creative force", "lower_meaning": "creative force"},
    2:  {"opcode": "OP_YIELD", "english": "Earth", "chinese": "坤",
         "binary": "000000", "description": "容納 — pure yin, receptivity, input/output",
         "upper_trigram": "坤", "lower_trigram": "坤",
         "upper_meaning": "receptive", "lower_meaning": "devoted"},
    3:  {"opcode": "OP_RETRY", "english": "Difficulty", "chinese": "屯",
         "binary": "010100", "description": "初難 — initial difficulty, retry with persistence",
         "upper_trigram": "坎", "lower_trigram": "震",
         "upper_meaning": "danger", "lower_meaning": "thunder"},
    4:  {"opcode": "OP_INIT", "english": "Youthful Folly", "chinese": "蒙",
         "binary": "010100", "description": "蒙昧 — seeking knowledge, initialization",
         "upper_trigram": "艮", "lower_trigram": "坎",
         "upper_meaning": "stillness", "lower_meaning": "water"},
    5:  {"opcode": "OP_WAIT", "english": "Waiting", "chinese": "需",
         "binary": "101110", "description": "等待 — patience, async wait",
         "upper_trigram": "坎", "lower_trigram": "乾",
         "upper_meaning": "danger", "lower_meaning": "heaven"},
    6:  {"opcode": "OP_CONFLICT", "english": "Conflict", "chinese": "訟",
         "binary": "111010", "description": "爭訟 — dispute resolution, comparison",
         "upper_trigram": "乾", "lower_trigram": "坎",
         "upper_meaning": "creative", "lower_meaning": "water"},
    7:  {"opcode": "OP_DEPLOY", "english": "Army", "chinese": "師",
         "binary": "010000", "description": "出師 — marshalling resources, organized deployment",
         "upper_trigram": "坤", "lower_trigram": "坎",
         "upper_meaning": "receptive", "lower_meaning": "water"},
    8:  {"opcode": "OP_MERGE", "english": "Holding Together", "chinese": "比",
         "binary": "010000", "description": "相比 — union, aggregation, merge",
         "upper_trigram": "坎", "lower_trigram": "坤",
         "upper_meaning": "water", "lower_meaning": "earth"},
    9:  {"opcode": "OP_NARROW", "english": "Small Taming", "chinese": "小畜",
         "binary": "111011", "description": "小畜 — narrow scope, constrained computation",
         "upper_trigram": "巽", "lower_trigram": "乾",
         "upper_meaning": "gentle wind", "lower_meaning": "heaven"},
    10: {"opcode": "OP_ADVANCE", "english": "Treading", "chinese": "履",
         "binary": "111110", "description": "履踐 — advance carefully, treading on thin ice",
         "upper_trigram": "乾", "lower_trigram": "兌",
         "upper_meaning": "creative", "lower_meaning": "joy"},
    11: {"opcode": "OP_JMP", "english": "Peace", "chinese": "泰",
         "binary": "000111", "description": "泰通 — smooth flow, peaceful transition",
         "upper_trigram": "坤", "lower_trigram": "乾",
         "upper_meaning": "receptive", "lower_meaning": "creative"},
    12: {"opcode": "OP_HALT", "english": "Standstill", "chinese": "否",
         "binary": "111000", "description": "閉塞 — stagnation, halt all execution",
         "upper_trigram": "乾", "lower_trigram": "坤",
         "upper_meaning": "creative", "lower_meaning": "receptive"},
    13: {"opcode": "OP_BROADCAST", "english": "Fellowship", "chinese": "同人",
         "binary": "111101", "description": "同道 — broadcast to fellows, shared purpose",
         "upper_trigram": "乾", "lower_trigram": "離",
         "upper_meaning": "creative", "lower_meaning": "fire"},
    14: {"opcode": "OP_OWN", "english": "Great Possession", "chinese": "大有",
         "binary": "101111", "description": "大有 — own/store great possessions",
         "upper_trigram": "離", "lower_trigram": "乾",
         "upper_meaning": "clinging", "lower_meaning": "creative"},
    15: {"opcode": "OP_MOD", "english": "Modesty", "chinese": "謙",
         "binary": "000001", "description": "謙虛 — modest remainder, modular operation",
         "upper_trigram": "坤", "lower_trigram": "艮",
         "upper_meaning": "receptive", "lower_meaning": "mountain"},
    16: {"opcode": "OP_ENTHUSIASM", "english": "Enthusiasm", "chinese": "豫",
         "binary": "000100", "description": "豫悅 — eager enthusiastic execution",
         "upper_trigram": "震", "lower_trigram": "坤",
         "upper_meaning": "arousing", "lower_meaning": "earth"},
    17: {"opcode": "OP_FOLLOW", "english": "Following", "chinese": "隨",
         "binary": "110100", "description": "追隨 — tail-call, follow the leader",
         "upper_trigram": "兌", "lower_trigram": "震",
         "upper_meaning": "joyous", "lower_meaning": "thunder"},
    18: {"opcode": "OP_CORRECT", "english": "Grace", "chinese": "蠱",
         "binary": "001011", "description": "校正 — correction, validate/repair",
         "upper_trigram": "艮", "lower_trigram": "巽",
         "upper_meaning": "stillness", "lower_meaning": "wind"},
    19: {"opcode": "OP_SPLIT", "english": "Approach", "chinese": "臨",
         "binary": "110111", "description": "臨近 — approach, conditional entry",
         "upper_trigram": "坤", "lower_trigram": "兌",
         "upper_meaning": "receptive", "lower_meaning": "joyous"},
    20: {"opcode": "OP_RETURN", "english": "Return", "chinese": "觀",
         "binary": "011000", "description": "觀復 — contemplation, observe and return",
         "upper_trigram": "巽", "lower_trigram": "坤",
         "upper_meaning": "gentle", "lower_meaning": "earth"},
    21: {"opcode": "OP_NOP", "english": "Contemplation", "chinese": "噬嗑",
         "binary": "101100", "description": "噬嗑 — biting through, debug breakpoint",
         "upper_trigram": "離", "lower_trigram": "震",
         "upper_meaning": "clinging", "lower_meaning": "thunder"},
    22: {"opcode": "OP_STORE", "english": "Grace", "chinese": "賁",
         "binary": "001101", "description": "文飾 — graceful storage, adorn data",
         "upper_trigram": "艮", "lower_trigram": "離",
         "upper_meaning": "stillness", "lower_meaning": "fire"},
    23: {"opcode": "OP_SPLIT", "english": "Splitting Apart", "chinese": "剝",
         "binary": "001000", "description": "剝落 — split/divide data structure",
         "upper_trigram": "艮", "lower_trigram": "坤",
         "upper_meaning": "stillness", "lower_meaning": "earth"},
    24: {"opcode": "OP_RETURN", "english": "Return", "chinese": "復",
         "binary": "001000", "description": "復歸 — return to source, restore state",
         "upper_trigram": "坤", "lower_trigram": "震",
         "upper_meaning": "receptive", "lower_meaning": "thunder"},
    25: {"opcode": "OP_NOP", "english": "Innocence", "chinese": "無妄",
         "binary": "111100", "description": "無妄 — no side effects, pure function",
         "upper_trigram": "乾", "lower_trigram": "震",
         "upper_meaning": "creative", "lower_meaning": "thunder"},
    26: {"opcode": "OP_STORE", "english": "Great Taming", "chinese": "大畜",
         "binary": "001111", "description": "大畜 — store great resources",
         "upper_trigram": "艮", "lower_trigram": "乾",
         "upper_meaning": "stillness", "lower_meaning": "creative"},
    27: {"opcode": "OP_EAT", "english": "Nourishing", "chinese": "頤",
         "binary": "001100", "description": "頤養 — consume/nourish data",
         "upper_trigram": "艮", "lower_trigram": "震",
         "upper_meaning": "stillness", "lower_meaning": "thunder"},
    28: {"opcode": "OP_EXCESS", "english": "Great Excess", "chinese": "大過",
         "binary": "110011", "description": "大過 — overflow, buffer exceeded",
         "upper_trigram": "兌", "lower_trigram": "巽",
         "upper_meaning": "joyous", "lower_meaning": "gentle"},
    29: {"opcode": "OP_NEG", "english": "Abysmal Water", "chinese": "坎",
         "binary": "010010", "description": "坎陷 — negate, fall into danger",
         "upper_trigram": "坎", "lower_trigram": "坎",
         "upper_meaning": "water", "lower_meaning": "water"},
    30: {"opcode": "OP_LIGHT", "english": "Clinging Fire", "chinese": "離",
         "binary": "101101", "description": "離明 — illuminate, cast light on data",
         "upper_trigram": "離", "lower_trigram": "離",
         "upper_meaning": "clinging", "lower_meaning": "clinging"},
    31: {"opcode": "OP_FAMILY", "english": "The Family", "chinese": "家人",
         "binary": "011101", "description": "家人 — family scope, household",
         "upper_trigram": "巽", "lower_trigram": "離",
         "upper_meaning": "gentle", "lower_meaning": "fire"},
    32: {"opcode": "OP_OPPOSE", "english": "Opposition", "chinese": "睽",
         "binary": "101110", "description": "睽違 — opposition, conditional branch",
         "upper_trigram": "離", "lower_trigram": "兌",
         "upper_meaning": "clinging", "lower_meaning": "joyous"},
    33: {"opcode": "OP_BREAK", "english": "Obstruction", "chinese": "蹇",
         "binary": "010001", "description": "蹇難 — guard/check obstruction",
         "upper_trigram": "坎", "lower_trigram": "艮",
         "upper_meaning": "water", "lower_meaning": "mountain"},
    34: {"opcode": "OP_DELIVER", "english": "Deliverance", "chinese": "解",
         "binary": "100010", "description": "解脫 — resolve, deliver result",
         "upper_trigram": "震", "lower_trigram": "坎",
         "upper_meaning": "arousing", "lower_meaning": "water"},
    35: {"opcode": "OP_SHRINK", "english": "Decrease", "chinese": "損",
         "binary": "001110", "description": "損減 — reduce, decrease resources",
         "upper_trigram": "艮", "lower_trigram": "兌",
         "upper_meaning": "stillness", "lower_meaning": "joyous"},
    36: {"opcode": "OP_GROW", "english": "Increase", "chinese": "益",
         "binary": "011100", "description": "增益 — amplify, increase benefit",
         "upper_trigram": "巽", "lower_trigram": "震",
         "upper_meaning": "gentle", "lower_meaning": "thunder"},
    37: {"opcode": "OP_BREAK", "english": "Breakthrough", "chinese": "夬",
         "binary": "111011", "description": "夬決 — force breakthrough decision",
         "upper_trigram": "兌", "lower_trigram": "乾",
         "upper_meaning": "joyous", "lower_meaning": "heaven"},
    38: {"opcode": "OP_ENCOUNTER", "english": "Coming to Meet", "chinese": "姤",
         "binary": "111011", "description": "邂逅 — unexpected input, encounter",
         "upper_trigram": "乾", "lower_trigram": "巽",
         "upper_meaning": "creative", "lower_meaning": "gentle"},
    39: {"opcode": "OP_GATHER", "english": "Gathering", "chinese": "萃",
         "binary": "110000", "description": "萃聚 — collect, aggregate data",
         "upper_trigram": "兌", "lower_trigram": "坤",
         "upper_meaning": "joyous", "lower_meaning": "earth"},
    40: {"opcode": "OP_RISE", "english": "Pushing Upward", "chinese": "升",
         "binary": "000011", "description": "上升 — ascend, push upward",
         "upper_trigram": "坤", "lower_trigram": "巽",
         "upper_meaning": "receptive", "lower_meaning": "gentle"},
    41: {"opcode": "OP_EXHAUST", "english": "Oppression", "chinese": "困",
         "binary": "110010", "description": "困窮 — resource exhaustion",
         "upper_trigram": "兌", "lower_trigram": "坎",
         "upper_meaning": "joyous", "lower_meaning": "water"},
    42: {"opcode": "OP_WELL", "english": "The Well", "chinese": "井",
         "binary": "010011", "description": "井泉 — deep access, well-spring",
         "upper_trigram": "坎", "lower_trigram": "巽",
         "upper_meaning": "water", "lower_meaning": "gentle"},
    43: {"opcode": "OP_REVOLUTION", "english": "Revolution", "chinese": "革",
         "binary": "110110", "description": "革命 — transform fundamentally",
         "upper_trigram": "兌", "lower_trigram": "離",
         "upper_meaning": "joyous", "lower_meaning": "fire"},
    44: {"opcode": "OP_VESSEL", "english": "The Cauldron", "chinese": "鼎",
         "binary": "101011", "description": "鼎鑄 — container/frame, data structure",
         "upper_trigram": "離", "lower_trigram": "巽",
         "upper_meaning": "clinging", "lower_meaning": "gentle"},
    45: {"opcode": "OP_SHOCK", "english": "Arousing", "chinese": "震",
         "binary": "100100", "description": "震驚 — interrupt, exception thrown",
         "upper_trigram": "震", "lower_trigram": "震",
         "upper_meaning": "arousing", "lower_meaning": "arousing"},
    46: {"opcode": "OP_STILL", "english": "Keeping Still", "chinese": "艮",
         "binary": "001001", "description": "艮止 — stabilize, freeze state",
         "upper_trigram": "艮", "lower_trigram": "艮",
         "upper_meaning": "stillness", "lower_meaning": "stillness"},
    47: {"opcode": "OP_PROGRESS", "english": "Development", "chinese": "漸",
         "binary": "011001", "description": "漸進 — gradual development, iteration",
         "upper_trigram": "巽", "lower_trigram": "艮",
         "upper_meaning": "gentle", "lower_meaning": "mountain"},
  48: {"opcode": "OP_MARRY", "english": "Marrying Maiden", "chinese": "歸妹",
         "binary": "100110", "description": "歸妹 — join/sync, data merge",
         "upper_trigram": "震", "lower_trigram": "兌",
         "upper_meaning": "arousing", "lower_meaning": "joyous"},
    49: {"opcode": "OP_FULL", "english": "Abundance", "chinese": "豐",
         "binary": "100101", "description": "豐盈 — full buffer, abundance",
         "upper_trigram": "震", "lower_trigram": "離",
         "upper_meaning": "arousing", "lower_meaning": "fire"},
    50: {"opcode": "OP_WANDER", "english": "Wandering", "chinese": "旅",
         "binary": "101001", "description": "旅遊 — seek, search across memory",
         "upper_trigram": "離", "lower_trigram": "艮",
         "upper_meaning": "clinging", "lower_meaning": "mountain"},
    51: {"opcode": "OP_GENTLE", "english": "Gentle", "chinese": "巽",
         "binary": "011011", "description": "巽入 — soft/persistent execution",
         "upper_trigram": "巽", "lower_trigram": "巽",
         "upper_meaning": "gentle", "lower_meaning": "gentle"},
    52: {"opcode": "OP_JOY", "english": "Joyous", "chinese": "兌",
         "binary": "110110", "description": "兌悅 — completion signal, joy",
         "upper_trigram": "兌", "lower_trigram": "兌",
         "upper_meaning": "joyous", "lower_meaning": "joyous"},
    53: {"opcode": "OP_SCATTER", "english": "Dispersion", "chinese": "渙",
         "binary": "011010", "description": "渙散 — distribute across nodes",
         "upper_trigram": "巽", "lower_trigram": "坎",
         "upper_meaning": "gentle", "lower_meaning": "water"},
    54: {"opcode": "OP_LIMIT", "english": "Limitation", "chinese": "節",
         "binary": "010110", "description": "節制 — bound checking, rate limiting",
         "upper_trigram": "坎", "lower_trigram": "兌",
         "upper_meaning": "water", "lower_meaning": "joyous"},
    55: {"opcode": "OP_TRUTH", "english": "Inner Truth", "chinese": "中孚",
         "binary": "011110", "description": "中孚 — verify truth, inner conviction",
         "upper_trigram": "巽", "lower_trigram": "兌",
         "upper_meaning": "gentle", "lower_meaning": "joyous"},
    56: {"opcode": "OP_OVERSTEP", "english": "Small Excess", "chinese": "小過",
         "binary": "100001", "description": "小過 — slight overflow, boundary violation",
         "upper_trigram": "震", "lower_trigram": "艮",
         "upper_meaning": "arousing", "lower_meaning": "mountain"},
    57: {"opcode": "OP_RET", "english": "After Completion", "chinese": "既濟",
         "binary": "010101", "description": "既濟 — completed, return result",
         "upper_trigram": "坎", "lower_trigram": "離",
         "upper_meaning": "water", "lower_meaning": "fire"},
    58: {"opcode": "OP_CALL", "english": "Before Completion", "chinese": "未濟",
         "binary": "101010", "description": "未濟 — potential, call/defer",
         "upper_trigram": "離", "lower_trigram": "坎",
         "upper_meaning": "clinging", "lower_meaning": "water"},
}


# ═══════════════════════════════════════════════════════════════
# Trigram → Opcode Category Mapping
# Upper trigram (lines 4-6) = opcode category
# Lower trigram (lines 1-3) = operation modifier
# ═══════════════════════════════════════════════════════════════

_TRIGRAM_CATEGORY: dict[int, str] = {
    Trigram.KUN:  "FLOW",
    Trigram.GEN:  "CONTROL",
    Trigram.KAN:  "IO",
    Trigram.XUN:  "DATA",
    Trigram.ZHEN: "SIGNAL",
    Trigram.LI:  "STATE",
    Trigram.DUI:  "COMms",
    Trigram.QIAN:  "CREATE",
}

_TRIGRAM_MODIFIER: dict[int, str] = {
    Trigram.KUN:  "passive_yield",
    Trigram.GEN:  "conditional_stop",
    Trigram.KAN:  "blocking_retry",
    Trigram.XUN:  "gentle_persist",
    Trigram.ZHEN:  "trigger_signal",
    Trigram.LI:  "assert_modify",
    Trigram.DUI:  "joy_complete",
    Trigram.QIAN:  "force_create",
}

# Trigram Chinese names lookup
_TRIGRAM_CN: dict[int, str] = {
    Trigram.KUN: "坤", Trigram.GEN: "艮", Trigram.KAN: "坎", Trigram.XUN: "巽",
    Trigram.ZHEN: "震", Trigram.LI: "離", Trigram.DUI: "兌", Trigram.QIAN: "乾",
}


# ═══════════════════════════════════════════════════════════════
# Extended IChingOpcodeEncoder Methods
# ═════════════════════════════════════════════════════════════════════════

def _get_trigram_decomposition(hexagram: Hexagram) -> tuple[str, str, str, str]:
    "Extract upper/lower trigram decomposition.
    Returns (upper_cn, lower_cn, category, modifier)."


@dataclass(frozen=True)
class HexagramOpcode:
    """易經指令 — A hexagram mapped to a VM opcode.

    Each of the 64 hexagrams maps to an opcode based on its
    cosmological meaning in the I Ching. The mapping is semantic,
    not arbitrary — it follows the I Ching's own internal logic.

    Attributes:
        hexagram: The I Ching hexagram.
        king_wen_number: Position in King Wen sequence (1–64).
        opcode_name: Human-readable opcode name (e.g., "OP_CREATE").
        address: 6-bit binary address (0–63).
        binary_str: 6-character binary string.
        description: Chinese/English description of the semantic mapping.
    """
    hexagram: Hexagram
    king_wen_number: int
    opcode_name: str
    address: int
    binary_str: str
    description: str


class IChingOpcodeEncoder:
    """易經指令編碼器 — Maps hexagrams to opcodes and vice versa.

    The encoder maintains the complete bidirectional mapping between
    the 64 hexagrams and their assigned opcodes. This is the bridge
    between the world's oldest binary encoding system (I Ching) and
    modern bytecode.

    卦即碼 — the hexagram IS the opcode.
    爻即位 — the lines ARE the bits.
    """

    def __init__(self) -> None:
        self._by_address: dict[int, HexagramOpcode] = {}
        self._by_name: dict[str, HexagramOpcode] = {}
        self._by_opcode: dict[str, HexagramOpcode] = {}
        self._by_kw: int = {}
        self._build_tables()

    def _build_tables(self) -> None:
        """Build the complete 64-hexagram opcode mapping table."""
        for hexagram in HEXAGRAMS_KING_WEN:
            kw = hexagram.king_wen_number
            addr = hexagram.address
            name = hexagram.name
            opcode_name = _HEXAGRAM_OPCODE_NAMES.get(kw, f"HEX_{kw}")
            binary_str = hexagram.binary_str
            desc = f"{name} (KW#{kw}) addr={addr} bin={binary_str}"

            entry = HexagramOpcode(
                hexagram=hexagram,
                king_wen_number=kw,
                opcode_name=opcode_name,
                address=addr,
                binary_str=binary_str,
                description=desc,
            )

            self._by_address[addr] = entry
            self._by_name[name] = entry
            if opcode_name not in self._by_opcode:
                self._by_opcode[opcode_name] = entry
            self._by_kw[kw] = entry

    # ── Lookup by various keys ──────────────────────────────

    def by_name(self, name: str) -> HexagramOpcode:
        """Look up by hexagram name (卦名).

        Args:
            name: Chinese name, e.g. '乾', '屯', '既濟'.

        Returns:
            The HexagramOpcode entry.
        """
        if name not in self._by_name:
            raise KeyError(f"Unknown hexagram name: {name}")
        return self._by_name[name]

    def by_address(self, address: int) -> HexagramOpcode:
        """Look up by 6-bit binary address.

        Args:
            address: Integer in range 0–63.

        Returns:
            The HexagramOpcode entry.
        """
        if address not in self._by_address:
            raise KeyError(f"Unknown hexagram address: {address}")
        return self._by_address[address]

    def by_king_wen(self, number: int) -> HexagramOpcode:
        """Look up by King Wen sequence number (1–64)."""
        if number not in self._by_kw:
            raise KeyError(f"Unknown King Wen number: {number}")
        return self._by_kw[number]

    def by_opcode(self, opcode_name: str) -> HexagramOpcode:
        """Look up by opcode name (first hexagram with that opcode)."""
        if opcode_name not in self._by_opcode:
            raise KeyError(f"Unknown opcode name: {opcode_name}")
        return self._by_opcode[opcode_name]

    # ── Encoding ───────────────────────────────────────────

    def encode(self, identifier: str | int | Hexagram) -> int:
        """Encode a hexagram to its 6-bit opcode address.

        The hexagram's binary pattern IS the opcode. Heaven (all yang = 111111)
        gives address 63, Earth (all yin = 000000) gives address 0.

        Args:
            identifier: Hexagram name, King Wen number, or Hexagram object.

        Returns:
            Integer opcode (0–63).
        """
        if isinstance(identifier, Hexagram):
            return identifier.address
        if isinstance(identifier, str):
            return self.by_name(identifier).address
        if isinstance(identifier, int):
            return self.by_king_wen(identifier).address
        raise TypeError(f"Cannot encode: {identifier}")

    def decode(self, opcode: int) -> HexagramOpcode:
        """Decode a 6-bit opcode back to its hexagram.

        Args:
            opcode: Integer in range 0–63.

        Returns:
            The corresponding HexagramOpcode.
        """
        return self.by_address(opcode)

    def encode_sequence(self, identifiers: list[str | int | Hexagram]) -> bytes:
        """Encode a sequence of hexagrams into bytecode.

        Each hexagram occupies one byte (6-bit address + 2 high bits).

        Args:
            identifiers: List of hexagram identifiers.

        Returns:
            Bytearray of encoded program.
        """
        return bytes(self.encode(id) for id in identifiers)

    def decode_sequence(self, bytecode: bytes) -> list[HexagramOpcode]:
        """Decode bytecode back to hexagram opcodes.

        Args:
            bytecode: Encoded program bytes.

        Returns:
            List of HexagramOpcode entries.
        """
        return [self.decode(b) for b in bytecode]

    # ── Inspection ──────────────────────────────────────────

    @property
    def total(self) -> int:
        """Total number of mapped hexagrams (should be 64)."""
        return len(self._by_kw)

    def table(self) -> str:
        """Format the complete opcode table as a readable string."""
        lines = [
            "╔══════════════════════════════════════════════════════════════╗",
            "║  六十四卦指令表 — 64 Hexagram Opcode Mapping Table                         ║",
            "╠═══════╦════════╦════════╦═════════╦════════════════════════╣",
            "║  KW#  ║ Name   ║ Bin    ║ Addr ║ Opcode       ║ Description                  ║",
            "╠═══════╬════════╬════════╬═════════╬════════════════════════╣",
        ]
        for kw in range(1, 65):
            entry = self.by_king_wen(kw)
            lines.append(
                f"║  {kw:3d}  ║ {entry.hexagram.name:6s}  ║ {entry.binary_str}  ║  {entry.address:2d}  "
                f"║ {entry.opcode_name:12s} ║ {entry.description:26s} ║"
            )
        lines.append(
            "╚═══════╩════════╩════════╩═════════╩════════════════════════╝"
        )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"IChingOpcodeEncoder({self.total} hexagrams)"


# Module-level singleton encoder
ICHING_OPCODE_ENCODER = IChingOpcodeEncoder()
