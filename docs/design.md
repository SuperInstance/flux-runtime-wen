# Design: Zero-Grammar Programming with Classical Chinese

## 流星 · 文言编程 — 设计文档

## 1. Thesis: Classical Chinese as the Most Minimal NL Programming Language

### 1.1 Why Classical Chinese?

Classical Chinese (文言文) is the most extreme test of topic-comment programming because it strips language down to its absolute essentials:

- **No inflection**: No verb conjugation, no noun declension, no agreement
- **No articles**: No "the", "a", equivalent
- **No grammatical particles for case**: No markers for subject/object distinction
- **No word boundaries**: Spaces are optional; character = concept
- **Extreme concision**: A complete sentence can be 4 characters

This makes it the most information-dense natural language ever constructed. Every character carries maximum semantic weight.

### 1.2 The Mapping to Programming

| Classical Chinese Feature | Programming Equivalent |
|--------------------------|----------------------|
| 字即词 (character = word) | Token = atomic concept |
| 无语法 (no grammar) | No AST needed; pattern → action |
| 词序定旨 (word order = meaning) | Positional parameter passing |
| 同字異義 (context-dependent meaning) | Polymorphic dispatch |
| 四字成程 (4-char programs) | Minimal program expression |

## 2. Architecture

### 2.1 No Grammar Engine

Traditional NL programming systems build parse trees. FLUX-wen does NOT. There is no grammar to parse. Instead:

1. **Character tokenization**: Each character is one token
2. **Pattern matching**: Source lines matched against regex patterns
3. **Context resolution**: Operands resolved through context stack
4. **Direct execution**: VM instructions executed against register machine

This is fundamentally different from compilers or interpreters that require grammars. It's closer to how a human reader of classical Chinese processes text — through pattern recognition and contextual inference.

### 2.2 Context Stack (文境)

The `ContextStack` is the central innovation. It maintains:

- **Domain**: Which interpretation domain is active (math, confucian, military, agent, control)
- **Topic**: What subject is being discussed
- **Register focus**: Which register is currently "in view"
- **Agent name**: Which agent is being addressed
- **Depth**: Nesting level (for loops, conditionals)

The same characters produce different instructions based on context:

```
In math context:     加 → IADD (addition)
In confucian context: 加 → DISTRIBUTE (benevolence/distribution)
In military context:  乘 → ADVANCE (ride upon)
```

This is `以文意定義` (meaning determined by textual intent) — the core principle of classical Chinese interpretation applied to programming.

### 2.3 Register Machine

The VM is a simple register machine with 8 registers (R0-R7). R0 is the accumulator / return value register.

- `MOVI Rn, v` — Set register to value
- `IADD a, b` — Add, store in R0
- `ISUB a, b` — Subtract, store in R0
- `IMUL a, b` — Multiply, store in R0
- `IDIV a, b` — Integer divide, store in R0
- `RANGE_SUM a, b` — Sum from a to b, store in R0
- `RET n` — Set R0 to value of Rn, halt
- `HALT` — Stop execution
- `WHILENZ Rn` — While register not zero
- `COND Rn, c` — Conditional on register
- `TELL agent, msg` — Send message to agent
- `ASK agent, topic` — Query agent
- `BROADCAST msg` — Message all agents

## 3. The Five Constants (五常) as Programming Primitives

### 3.1 Mapping

| Virtue (德) | Character | Operation | Programming Concept |
|-------------|-----------|-----------|-------------------|
| 仁 Benevolence | 仁 | DISTRIBUTE | Fan-out, parallel dispatch |
| 义 Righteousness | 义 | VALIDATE | Type checking, assertions |
| 礼 Ritual | 礼 | ORCHESTRATE | Workflow, sequencing |
| 智 Wisdom | 智 | OPTIMIZE | Compilation, optimization |
| 信 Trust | 信 | VERIFY | Testing, integrity checks |

### 3.2 Why This Mapping Works

The Five Constants (仁义礼智信) describe the complete set of operations needed for a well-functioning system:

1. **仁 (Distribute)**: Before computation can happen, resources must be distributed
2. **义 (Validate)**: Input must be validated / type-checked
3. **礼 (Orchestrate)**: Processes must be properly sequenced
4. **智 (Optimize)**: The system must find optimal paths
5. **信 (Verify)**: Results must be verified for correctness

This is not merely a linguistic exercise. It maps to real systems architecture: load balancing → validation → orchestration → optimization → verification.

## 4. The Art of War as Strategy Patterns

Sun Tzu's Art of War (孙子兵法) maps to distributed systems strategies:

| Military Concept | Character | System Operation |
|-----------------|-----------|-----------------|
| Attack | 攻 | SEND / push |
| Defend | 守 | RECEIVE / buffer |
| Withdraw | 退 | BACKOFF / retry |
| Advance | 进 | PROCEED / next phase |
| Ambush | 伏 | LAZY_EVAL / on-demand |
| Surround | 围 | ROUND_ROBIN |
| Divide | 分 | PARTITION / shard |
| Unite | 合 | MERGE / aggregate |

The famous principle "不战而屈人之兵" (subdue the enemy without fighting) maps to **cache hits** — resolving a request without computation.

## 4. Character-Level Tokenization

### 4.1 Categories

Each character is classified into one of five categories:

1. **number**: 一二三四五六七八九十百千万 (classical numerals) + Arabic digits
2. **register**: R followed by digit(s)
3. **operator**: 加减乘除
4. **keyword**: 于与为以合归当若告问遍止仁义礼智信攻守退进注
5. **text**: anything else

### 4.2 Zero Ambiguity Principle

In a well-written classical Chinese program, each character should be unambiguous in its category. This is the "zero ambiguity principle" — if a character could be read multiple ways, add context.

## 5. Four-Character Programs

The ultimate expression of concision. Valid programs in 4 characters:

| Program | Meaning | Result |
|---------|---------|--------|
| 加三于四 | add 3 to 4 | 7 |
| 三乘四 | 3 multiply 4 | 12 |
| 七减二 | 7 subtract 2 | 5 |
| 以零七 | take 0 as 7 | R0=7 |

Theoretical minimum for a useful computation: **3 characters** (三加四 = 3+4).

## 6. Limitations and Future Work

### 6.1 Current Limitations

- No nested control flow (loops are recognized but not fully executed)
- Limited error reporting (文言 error messages)
- No type system beyond register integers
- Pattern matching is regex-based (could be ML-based)

### 6.2 Future Directions

- **以...為...** pattern for type casting between domains
- **Stochastic interpretation**: ML model for ambiguous patterns
- **Full 四书五经 integration**: Confucian classics as importable modules
- **Multi-agent orchestration**: 告/问/遍告 as real agent communication
- **Ideographic rendering**: Visual program representation using character layout
