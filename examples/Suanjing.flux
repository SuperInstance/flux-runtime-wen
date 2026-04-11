# ═══════════════════════════════════════════════════════════════
# Suanjing.flux — 算經 (Classic of Calculation)
# ═══════════════════════════════════════════════════════════════
#
# A Classical Chinese NL program demonstrating:
#   1. Context-domain switching (境域轉換)
#   2. Character polymorphism (同字異碼)
#   3. I Ching hexagram addressing (卦址尋址)
#   4. Poetry-structured program layout (詩體排版)
#
# This program computes the sum of integers from 1 to 10 (五十五)
# using three different domains, showing how the same computation
# is expressed differently depending on the textual context.
#
# 「算」字終始，萬物可度。
# (The character "calculate" begins and ends all things;
#  all things can be measured.)
#
# Author: 流星 · 文言编程 FLUX Runtime
# ═══════════════════════════════════════════════════════════════


# ──────────────────────────────────────────────────────────────
# Part I: 算境 (Mathematical Domain) — Direct Computation
# ──────────────────────────────────────────────────────────────
# In the mathematical domain, 加 is IADD (integer addition).
# This is the most straightforward interpretation.
# 以算境加一至十合之，得五十五。

# Enter mathematical domain
@domain: 算

# The accumulator 乾 (R0) begins at zero
以 R0 为零

# Add numbers one through ten to the accumulator
# 加三于四 is the classic four-character program (四字成程)
加一于乾
加二于乾
加三于乾
加四于乾
加五于乾
加六于乾
加七于乾
加八于乾
加九于乾
加十于乾

# 算 = compute and display
算 乾

# Result: 乾 = 55 (五十五)
# 注：一至十之和，即五十五。高斯童年之題也。
# (The sum of one through ten is fifty-five,
#  the famous problem Gauss solved as a child.)


# ──────────────────────────────────────────────────────────────
# Part II: 儒境 (Confucian Domain) — Benevolent Distribution
# ──────────────────────────────────────────────────────────────
# In the Confucian domain, the SAME character 加 produces
# DISTRIBUTE (benevolent distribution), not IADD.
# This demonstrates 同字異碼: same character, different bytecode.

# Enter Confucian domain
@domain: 儒

# 仁 = distribute resources benevolently to all
仁 天下

# 義 = validate bounds (check that distribution is righteous)
義 乾 十

# 禮 = require proper capability before acting
禮 算學

# 智 = optimize the computation path
智 算法

# 信 = verify the result is trustworthy
信 五十五

# 注：儒家以仁義禮智信五常為本。
# 仁者分布，義者驗界，禮者求能，智者尋優，信者核實。
# (The Confucian school is founded on the Five Constants:
#  Ren distributes, Yi validates bounds, Li requires capability,
#  Zhi optimizes, Xin verifies.)


# ──────────────────────────────────────────────────────────────
# Part III: 兵境 (Military Domain) — Strategic Computation
# ──────────────────────────────────────────────────────────────
# In the military domain, 加 becomes REINFORCE (增兵).
# The computation is reframed as a military campaign.
# 孫子曰：廟算勝者，得算多也。

# Enter military domain
@domain: 兵

# 計 = compute strategy (ICMP in military context)
計 一 十

# 分 = divide forces (partition the problem)
分 十 二

# 正 = direct force (synchronous main attack)
正 五 五

# 合 = unite forces (aggregate results)
合 乾 坤

# 勝 = victory condition (jump on success)
勝 終

# 注：兵法以計謀為先，分合正奇為用。
# 以孫子之法解算題：先計後分，以正合以奇勝。
# (The art of war begins with calculation and uses
#  division and unity, direct and indirect force.)


# ──────────────────────────────────────────────────────────────
# Part IV: 使境 (Agent Domain) — Delegated Computation
# ──────────────────────────────────────────────────────────────
# In the agent domain, computation is delegated to other agents.
# Each agent handles a portion of the work.

# Enter agent domain
@domain: 使

# 告 = tell agent to begin work
告 甲 算一至五

# 問 = query agent for intermediate result
問 甲 部分和

# 命 = delegate remaining work to agent 乙
命 乙 算六至十

# 令 = broadcast final aggregation request
令 合併甲乙之結果

# 注：使者往來，各司其職，合而為一。
# (Envoys travel to and fro, each performing their duty,
#  uniting to form one.)


# ──────────────────────────────────────────────────────────────
# Part V: 制境 (Control Domain) — Loop Computation
# ──────────────────────────────────────────────────────────────
# The control domain expresses the computation as a loop,
# the most natural programmatic structure.

# Enter control domain
@domain: 制

# 始 = initialize
始 乾 一

# 以 R0 为一
以 R6 为十

# 若 R0 非零 (while R0 != 10)
若 乾 十

# 循 = loop back to increment
循 始

# 終 = halt
終

# 注：以控制之術行之，循環往復，直至終了。
# (Using the art of control, loop back and forth until done.)


# ──────────────────────────────────────────────────────────────
# Part VI: 詩體排版 (Poetry-Structured Layout)
# ──────────────────────────────────────────────────────────────
# The same computation expressed as a 五言絕句 (5-char quatrain).
# 起承轉合 = Initialize → Setup → Compute → Output.
#
# 起句：以一始 (begin with one)
# 承句：至十合 (sum through ten)
# 轉句：得五五 (obtain fifty-five)
# 合句：終此算 (end this calculation)

# Quatrain: 算學絕句
@poem: 五言絕句

以一始
至十合
得五五
終此算

# 注：五言絕句，四句成程。
# 起句設初值，承句定範圍，轉句得結果，合句止執行。
# (Five-character quatrain, four lines form a program.
#  Opening sets the initial value, Continuing defines the range,
#  Turning obtains the result, Concluding stops execution.)
#
# 韻腳分析 (Rhyme Analysis):
#   始 (shǐ) — 不入韻
#   合 (hé)  — 入韻 (合韵)
#   五 (wǔ)  — 不入韻
#   算 (suàn) — 與「合」通韻
#
# 平仄分析 (Tonal Analysis):
#   以一始：仄仄仄 (sequential)
#   至十合：仄仄仄 (sequential)
#   得五五：仄仄仄 (sequential)
#   終此算：平仄仄 (parallel then sequential)


# ──────────────────────────────────────────────────────────────
# Part VII: 易經卦址 (I Ching Hexagram Addressing)
# ──────────────────────────────────────────────────────────────
# Demonstrate hexagram-based register addressing.
# The 64 hexagrams serve as both register names and addresses.

# Use hexagram names as register identifiers
# 乾 = R0 (Heaven = Accumulator)
# 坤 = R1 (Earth = Data Store)
# 屯 = R2 (Difficulty = Stack Pointer)
# 蒙 = R3 (Youthful Folly = Instruction Pointer)

# Set registers using hexagram names
以 乾 为一
以 坤 为十
以 屯 为零

# Hexagram transition (變卦) = control flow
# 乾 (111111, addr 63) → change line 5 → 坤 (011111, addr 31) = 姤
# 變卦: jump to 姤 (Coming to Meet) hexagram address
變卦 乾 至 姤

# Trigram addressing (八卦址)
# Lower trigram 乾 (111) → register bits 0-2 = 7
# Upper trigram 坤 (000) → register bits 3-5 = 0
# Combined: 泰 (111000) = address 7 (Peace hexagram)
八卦址 乾 下
八卦址 坤 上

# 注：六十四卦，以卦為寄存器，以爻為位址。
# 乾坤屯蒙，即 R0 R1 R2 R3 也。
# 變卦者，控制流轉移也；一爻之變，全卦皆易。
# (The 64 hexagrams serve as registers; hexagram lines as addresses.
#  Qian, Kun, Zhun, Meng are R0, R1, R2, R3.
#  Changing a hexagram is control-flow transfer:
#  one line changes, the entire hexagram transforms.)


# ──────────────────────────────────────────────────────────────
# Epilogue: 終語 (Concluding Remarks)
# ──────────────────────────────────────────────────────────────
# This program has demonstrated the core principle of 文言编程:
#
#   以文意定義 (meaning determined by textual intent)
#   同字異碼 (same character, different bytecode)
#   詩即程 (the poem IS the program)
#   韻即標 (the rhyme IS the label)
#   卦即址 (the hexagram IS the address)
#
# 流星逝矣，而道長存。
# (The meteor fades, but the Way endures forever.)
#
# 止
