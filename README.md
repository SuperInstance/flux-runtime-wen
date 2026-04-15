# 流星 · 文言编程

**FLUX — Classical Chinese Programming Runtime**

> 零语法，纯概念，四字成程。
> No grammar. Pure concept. Four characters suffice.

> **This is the Classical Chinese (文言文) localization of [flux-runtime](https://github.com/SuperInstance/flux-runtime).**
> FLUX-wen is part of the FLUX internationalization fleet — a Classical Chinese-first NL runtime for the FLUX universal bytecode VM, leveraging zero-inflection grammar, context-defined semantics, and four-character program expressions.

---

## 何为文言编程？

文言文（Classical Chinese）者，华夏最精炼之语也。无屈折、无词缀、无冠词——一字一义，词序定旨。

以之为程序语言，得天独厚：

| 特性 | 文言 | 英文 | 现代中文 |
|------|------|------|----------|
| 词形变化 | 无 | 有（时态、格、数） | 无 |
| 冠词 | 无 | the/a | 的/了 |
| 量词 | 无 | 无 | 个/只/条 |
| 最短程序 | 四字 | ~10词 | ~6字 |

**四字成程**：加三于四 → 7

---

## 安装 / Install

```bash
pip install -e .
```

## 用法 / Usage

```bash
# 初始化 / Initialize
flux-wen 啟

# 编译 / Compile & disassemble
flux-wen 譯 '加三于四'
flux-wen 譯 '三乘四'

# 执行 / Run
flux-wen 行 '加三于四'          # → 7
flux-wen 行 '三乘四'            # → 12
flux-wen 行 '一至十合'           # → 55

# 查看 / Inspect
flux-wen 觀 '以 R0 为七' -x

# 文件执行 / Run from file
flux-wen 行 -f program.wen
```

## 程序示例 / Examples

### 算术 / Arithmetic

```
加三于四        # 3 + 4 = 7
三乘四          # 3 × 4 = 12
七减二          # 7 - 2 = 5
十除以三        # 10 ÷ 3 = 3
一至十合        # 1+2+...+10 = 55
```

### 寄存器 / Registers

```
以 R0 为七      # R0 = 7
以 R1 为三      # R1 = 3
R0 与 R1 合     # R0 + R1 = 10
归 R0           # return 10
```

### 智能体通信 / Agent Communication

```
告 张三 今日天晴    # tell Zhang San: weather is sunny
问 李四 明日计划    # ask Li Si: tomorrow's plan
遍告 全体注意        # broadcast: everyone pay attention
```

### 儒家操作 / Confucian Operations

```
仁 全体           # distribute to all (benevolence)
义 数据           # validate data (righteousness)
礼 流程           # orchestrate workflow (ritual)
智 算法           # optimize algorithm (wisdom)
信 结果           # verify results (trust)
```

### 完整程序 / Full Program

```
注：计算三角形面积近似值
以 R0 为三
以 R1 为四
R0 与 R1 合
以 R2 为二
R0 除以 R2
归 R0
```

---

## 设计理念 / Design Philosophy

### 以文意定義 (Context-Defined Meaning)

文言文无语法——意义全赖上下文。同一字符串，在不同语境中含义不同：

- **加**：算术中为"加法"，儒家语境中为"施仁"（分布）
- **乘**：算术中为"乘法"，兵法中为"乘势"（推进）
- **信**：儒家为"信任"（核实），通用为"信息"

此即**多态分派**——同一接口，不同实现，由上下文决定。

### 字即词 (Character = Token)

每个汉字即一个概念标记（token）。无需空格分词，无需语法树。

### 四书五经为标准库 (Classics as Stdlib)

- 仁义礼智信 → 五种核心运算
- 孙子兵法 → 策略模式
- 九章算术 → 数学运算

---

## 指令集 / Instruction Set

| 文言 | 操作 | 说明 |
|------|------|------|
| 加 a 于 b | IADD | 加法 |
| a 乘 b | IMUL | 乘法 |
| 减 a 于 b | ISUB | 减法 |
| a 除 b | IDIV | 除法 |
| a 至 b 合 | RANGE_SUM | 求和 |
| 以 Rn 为 v | MOVI | 赋值 |
| Rn 与 Rm 合 | IADD | 寄存器相加 |
| 归 Rn | RET | 返回 |
| 当 Rn 非零 | WHILENZ | 循环 |
| 若 Rn 为 c | COND | 条件 |
| 告 a m | TELL | 通知 |
| 问 a t | ASK | 查询 |
| 遍告 m | BROADCAST | 广播 |
| 仁/义/礼/智/信 | 五常运算 | 儒家操作 |
| 攻/守/退/进 | 兵法运算 | 军事操作 |
| 止 | HALT | 停止 |

---

## 项目结构 / Project Structure

```
flux-runtime-wen/
├── src/flux_wen/
│   ├── __init__.py          # 包初始化
│   ├── cli.py               # 命令行（啟譯行觀）
│   ├── interpreter.py       # 文言解释器
│   ├── context.py           # 上下文栈（文境）
│   └── vocabulary/
│       ├── confucian.ese    # 儒家词库
│       ├── military.ese     # 兵法词库
│       └── math.ese         # 算学词库
├── tests/
│   └── test_interpreter_wen.py
├── docs/
│   └── design.md
├── pyproject.toml
└── README.md
```

---

## Build & Test

```bash
# Clone the repository
git clone <repository-url>
cd flux-runtime-wen

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run the test suite
pytest tests/ -v

# Run via CLI
flux-wen 啟
```

## License

MIT

---

<img src="callsign1.jpg" width="128" alt="callsign">
