# Quant 项目全面审计报告

**审计日期**: 2026-05-19  
**审计范围**: `AutoQuant/` + `QuantumRandy/` 全部源代码、配置、数据、输出产物  
**审计深度**: 逐行代码审查 + 数据流追踪 + 因子挖掘方法论审计 + 回测未来函数检查

---

## 目录

1. [总体架构概述](#1-总体架构概述)
2. [未来函数与前瞻偏差审计（CRITICAL）](#2-未来函数与前瞻偏差审计)
3. [回测引擎审计](#3-回测引擎审计)
4. [因子挖掘审计](#4-因子挖掘审计)
5. [因子评价体系审计](#5-因子评价体系审计)
6. [MCTS 搜索审计](#6-mcts-搜索审计)
7. [LLM 集成审计](#7-llm-集成审计)
8. [数据管线审计](#8-数据管线审计)
9. [配置与参数审计](#9-配置与参数审计)
10. [代码质量与工程问题](#10-代码质量与工程问题)
11. [安全问题](#11-安全问题)
12. [Bug 汇总](#12-bug-汇总)
13. [改进建议优先级](#13-改进建议优先级)

---

## 1. 总体架构概述

项目包含两个子项目：

- **AutoQuant** — "STRICT4H" 策略参数优化框架：通过 Optuna/随机搜索优化 EMA + Bollinger Band + 资金费率偏差复合策略的参数，两阶段筛选（Stage I 训练排序 → Stage II 多场景稳健性检验）。
- **QuantumRandy** — 基于论文 `arXiv-2505.11122v3` 的公式化因子挖掘系统：LLM（DeepSeek）+ MCTS 搜索 alpha 公式，四步残酷筛选（"Brutal Filter"）过滤，24h 研究工作台（Dashboard + HTTP API）。

数据流方向：`Binance API → CSV → AutoQuant(optimize) → QuantumRandy(expression → backtest → evaluate → MCTS → lab/brutal filter)`

---

## 2. 未来函数与前瞻偏差审计

> **结论**: 核心回测执行链路**未发现系统性未来函数**。信号执行延迟、IC 计算、滚动窗口算子均正确使用历史数据。但存在 **3 个中等问题** 和若干边界情况。

### 2.1 信号执行延迟（PASS）

**AutoQuant `engine.py:17`**:
```python
exposure = signal.shift(execution_delay_bars).fillna(0.0)
```
**QuantumRandy `backtest.py:26`**:
```python
exposure = signal.shift(execution.delay_bars).fillna(0.0)
```
两者均配置 `delay_bars=1`，即当前 bar 生成的信号在下一根 bar 才执行。**正确，无前瞻偏差。**

### 2.2 IC/Rank IC 计算（PASS）

**QuantumRandy `backtest.py:89-91`**:
```python
future = ledger["r_mkt"].shift(-1)
ic = float(factor.corr(future))
rank_ic = float(factor.corr(future, method="spearman"))
```
此处 `shift(-1)` 取下一期收益，用于衡量因子的**预测能力**。这是学界和业界计算 Information Coefficient 的标准做法，**不是未来函数**——它评估的是"当前因子值能否预测未来收益"，而非用于生成交易信号。

### 2.3 滚动窗口算子（PASS）

`expression.py` 中所有滚动算子（`sma, ema, std, zscore, min, max, delta, ret, corr, rank, rsi`）均使用 `rolling(window)` 或 `ewm(span=window)`，这些 pandas 方法只使用到当前 bar 为止的历史数据。

- `zscore`: `(x - rolling_mean) / rolling_std` — 均值和标准差均基于滚动窗口内的历史值。
- `rank`: 使用 `x[:-1] < x[-1]` 计算当前值在窗口内的百分位排名——当前值参与比较是合理的（排名需要包含自身）。
- `delay`: 使用 `shift(window)` 显式滞后。

### 2.4 问题 1: Exposure 首 bar 处理偏差（MEDIUM）

**AutoQuant `engine.py:19` / QuantumRandy `backtest.py:27`**:
```python
delta = exposure.diff().fillna(exposure)
```
第一个 bar 的 `diff()` 为 NaN，被填充为 `exposure`（即首 bar 的完整仓位）。这意味着回测的第一个 bar 会被记录一次"完整的仓位建立"成本（手续费+滑点），相当于凭空产生了一次入场交易。

**影响**：首 bar `turnover` 虚高，`c_fee` 和 `c_slip` 被多计 ~4-6 bps。对长期回测（数千 bar）影响极小，但影响首 bar 的 ledger 记录准确性。

**建议**：改为 `delta = exposure.diff().fillna(0.0)`。

### 2.5 问题 2: Stage II 稳健检验使用验证期数据（MEDIUM）

**AutoQuant `scripts/run_stage2.py:18-19`**:
```python
ohlcv = slice_window(ohlcv_all, s.windows.training_start, s.windows.validation_end)
```
Stage II 的 `robust_summary` 在 **训练+验证全区间**上运行回测（2019-09 至 2023-01），然后用这些包含验证期结果的指标进行候选策略排序和筛选。这意味着验证期信息泄露到了"稳健性筛选"的排名中。虽然 Stage II 的本意是多成本情景压力测试而非严格的 hold-out 验证，但如果 Stage II 筛选出的策略被认为是"通过稳健检验的"，需要明确这些结果已包含验证期 forward-looking 信息。

**影响**：`stable_candidates` 的"稳健性"评估不再是纯样本外的。`maxDD_mean` 和 `switch_density_mean` 是基于含验证期的回测计算的。

**建议**：将 Stage II 的 robust_summary 限定在训练窗口内运行，或者将验证窗口作为独立评估步骤。

### 2.6 问题 3: EMA 和 zscore 的初始值偏置（LOW）

`expression.py` 中的 `ema(span=window, adjust=False)` 和 `rolling(window, min_periods=window)` 在序列起始的 `window` 个 bar 内使用不完整的历史数据。`min_periods=window` 意味着前 `window-1` 个 bar 的结果是 NaN（之后被 `fillna(0.0)` 填充为 0）。

**影响**：在数据起始的前 ~120 根 bar（约 20 天）因子值为 0，不产生信号。对于从 2019-09-08 开始的 6 年数据来说影响可忽略。

### 2.7 总结

| 检查项 | 状态 | 风险等级 |
|--------|------|----------|
| 信号执行延迟 | PASS | - |
| 滚动窗口算子 | PASS | - |
| IC/Rank IC 计算 | PASS (非未来函数) | - |
| funding_rate 对齐 | PASS | - |
| 首 bar exposure diff | FAIL | LOW |
| Stage II 验证期泄露 | FAIL | MEDIUM |
| EMA/rolling 初始值 | PASS | LOW |

---

## 3. 回测引擎审计

### 3.1 收益计算（PASS）

两个引擎使用相同的收益分解：
```python
r_mkt = close.pct_change()     # 市场价格变动
r_raw = exposure * r_mkt       # 仓位收益
r_net = r_raw - c_fee - c_slip - c_fund  # 净收益
```

### 3.2 成本建模（PASS）

- **手续费 (c_fee)**: `turnover * taker_bps / 10000` — 使用 `delta.abs()` 即换手绝对值 × taker 费率。AutoQuant 默认 4bps，QuantumRandy 默认 4bps。接近 Binance USDT 永续合约实际 taker fee（~4-5bps）。
- **滑点 (c_slip)**: 同上，AutoQuant 默认 2bps，QuantumRandy 默认 1bps。
- **资金费率 (c_fund)**: `exposure * funding_rate * 0.5 * multiplier`，0.5 系数因为 funding 每 8h 结算一次而 bar 是 4h。符号正确（long + positive funding = pay；short + positive funding = receive）。

### 3.3 问题 4: Sharpe Ratio 计算（MEDIUM）

**AutoQuant `metrics.py:26` / QuantumRandy `backtest.py:69`**:
```python
std = float(r.std(ddof=0))    # 使用总体标准差
```
两者均使用 `ddof=0`（总体标准差）而非 `ddof=1`（样本标准差）。对于 2000+ 个数据点，差异可忽略（<0.1%）。但对于分段验证集如果数据点较少（<100），样本标准差更合适。

同时注意到 AutoQuant 的 `sharpe()` 减去了无风险利率 (`risk_free_rate / bars_per_year`)，而 QuantumRandy 的 `sharpe()` **没有减去无风险利率**。这使得两个系统的 Sharpe 不可直接比较。QuantumRandy 的 Sharpe 会系统性偏高约 0.01-0.03（取决于 bars_per_year）。

### 3.4 问题 5: CAGR 的失败返回值（LOW）

```python
if years <= 0 or total <= 0:
    return -1.0
```
当策略亏光所有资金（`total <= 0`）时返回 `-1.0`（即 -100% CAGR）。这在排序中会排在微亏策略（如 CAGR=-0.05）之上，因为 `-1.0 > -0.05` 在数值上是"更大"的。实际上 `total <= 0` 意味着策略已经破产了（total=0 意味着 equity 归零），应当返回一个极差值如 `-0.999` 或 `-inf`。

### 3.5 问题 6: 回测硬编码假设（LOW）

- 总是全仓进出（`exposure` 始终为 ±1.0 或 0），无部分仓位管理。
- 无止损/止盈逻辑（尽管 theta 包含 `atr_period`, `atr_k_sl`, `atr_k_tp` 字段，信号生成中未使用）。
- 资金费率使用的 `0.5` 系数假设 funding 永远 8h 间隔，如果交易所改变间隔会出错。

---

## 4. 因子挖掘审计

### 4.1 公式 DSL 与表达式引擎

**白名单安全模型（PASS）**: 使用 AST 解析而非 `eval()`，字段和算子均有白名单限制。安全。

**算子完备性（PASS）**: 21 个算子覆盖了量化因子挖掘的核心需求：趋势（sma/ema）、波动（std）、动量（ret/delta）、均值回归（zscore）、相对强弱（rsi/rank）、相关性（corr）、滞后处理（delay）、基础运算（add/sub/mul/div/neg/abs/log/sqrt）。

### 4.2 问题 7: `rank` 算子实现存疑（LOW）

```python
def _rank_pct(x):
    n = len(x)
    if n < 2:
        return 0.5
    return float((x[:-1] < x[-1]).sum()) / max(n - 1, 1)
```
此实现计算当前值在窗口中排第几百分位。但 `x[:-1] < x[-1]` 是逐元素比较（非排序），这意味着它计算的是"有多少历史值比当前值小"的比例。这对于非平稳序列是正确的百分位排名近似，但如果窗口内有重复值的处理不精确（严格小于 `<` 而非 `<=`）。

### 4.3 问题 8: 本地生成器模板空间有限（MEDIUM）

**`proposals.py`**: 本地 `LocalProposalEngine` 仅有 15 个模板（每个维度 3 个），随机变化来自 5 个字段 × 8 个窗口参数。模板空间约 15 × 5 × choose(8,2) ≈ 2100 个组合，且有很大重叠（如 `zscore(close,120)` 和 `zscore(high,120)` 高度相关）。

**影响**: 不使用 LLM 时，约 30-50 轮迭代后新公式与旧公式的相关性急剧上升，zoo 饱和。PROJECT_LOG 已记录此问题。这是预期内的限制，但应更明确地警告用户：本地模式 100+ 轮基本不会产生有效的新因子。

### 4.4 问题 9: 种子公式质量参差（LOW）

`btcusdt.yaml` 中的 `seed_formulas`:
```yaml
seed_formulas:
  - "zscore(sub(sma(close,12),sma(close,48)),48)"
  - "neg(zscore(funding_rate,42))"
```
PROJECT_LOG 记录已从种子中移除 `zscore(ret(close,6),48)`（因为 rank_ic=-0.04）。当前两个种子质量尚可，但 `zscore(sub(sma(close,12),sma(close,48)),48)` 在训练集上的 directional_win_rate=0.4993，刚好跨过 0.49 的阈值。

---

## 5. 因子评价体系审计

### 5.1 MCTS 内部评分（5 维度）

**`evaluator.py`** 中的 `evaluate_alpha()` 计算 5 个维度分并取平均：

#### effectiveness（有效性）
```python
_percentile(metrics["rank_ic"], [prior_rank_ics...], higher_is_better=True)
```
- 与已有 alpha zoo 的 rank_ic 做百分位比较，无 prior 时用 `tanh(abs(value)*30)` 得到 0.5+ 的伪分。
- **问题**: `tanh(abs(value)*30)` 对 IC=0.02 给出 0.537，IC=0.05 给 0.905。斜率非常陡峭，IC=0.01（区分度弱但可接受的因子）只给 0.504。

#### stability（稳定性）
```python
positive = float((monthly > 0).mean())
volatility_penalty = float(np.tanh(monthly.std * 15.0))
return np.clip(0.75 * positive + 0.25 * (1.0 - volatility_penalty), 0.0, 1.0)
```
- **问题**: 月收益标准差 × 15 的系数非常 aggressive。每月收益 std=0.10（10%）时 penalty=tanh(1.5)≈0.90。两个权重 0.75/0.25 也是硬编码，缺乏理论依据。

#### turnover（换手）
```python
np.clip(1.0 - turnover * 3.0, 0.0, 1.0)
```
- 线性惩罚。turnover=0.05（5%换手率）→ 0.85 分。turnover>0.33 直接归零。对高频策略惩罚很重。

#### diversity（差异度）
```python
# Jaccard token similarity
tokens = set(_tokens(formula))
sims = [len(tokens & other_tokens) / len(tokens | other_tokens)]
return 1.0 - max(sims)
```
- **重大方法论缺陷（MEDIUM）**: 使用公式字符串的 token-level Jaccard 相似度作为"差异度"度量。`zscore(close,120)` 和 `zscore(close,48)` 有 100% 的 token 重合但信号完全不同（窗口差距 2.5×）。相反，`zscore(ret(close,6),48)` 和 `zscore(high,120)` 只有 40% token 重合但可能高度相关。

#### overfit_risk（过拟合风险代理）
```python
complexity = formula.count("(") + formula.count(",")
complexity_score = np.clip(1.0 - max(complexity - 10, 0) / 25.0, 0.0, 1.0)
drawdown_score = np.clip(1.0 - metrics["max_dd"], 0.0, 1.0)
return 0.65 * complexity_score + 0.35 * drawdown_score
```
- **问题**: 用括号和逗号的数量作为过拟合代理过于粗糙。`zscore(sub(sma(close,12),sma(close,48)),48)`（4 算子，经济含义清晰）有 6 个括号+逗号，与一些真正无意义的深度嵌套公式可能得分相近。

### 5.2 四步残酷筛选（Brutal Filter）

**`lab.py`** 中的 `run_brutal_filter()`:

**Gate 1 — 预测力初筛**: `rank_ic >= 0.01 OR directional_win_rate >= 0.49`。阈值合理，但 OR 逻辑意味着一个 rank_ic=-0.05 但 win_rate=0.50（接近随机）的因子也能通过。建议改为 AND 或加权组合。

**Gate 2 — 同质化查杀**: `max_corr_to_library < 0.70`。使用 `mature_factor_formulas() + accepted_formulas` 的因子值序列相关性。`self_formula` 参数正确排除了自相关（PROJECT_LOG 记录此前存在 bug）。

**Gate 3 — 摩擦成本绞肉机**: `cost_sharpe >= 0.30`（从最初的 1.00 下调），即在扣除手续费、滑点、资金费率后的 Sharpe 必须为正且有一定幅度。当前阈值 0.30 意味着扣费后仍有正的超额收益。对于 4h BTC，这个阈值偏宽松。

**Gate 4 — 寿命测试**: `validation_sharpe >= 0 AND halflife_bars >= 1`。半衰期 `estimate_halflife_bars()` 使用 Spearman rank correlation 在不同 forward horizon 上的衰减。`max_horizon=42`（7天）合理。

#### brutal_rank_score 权重审计

```python
0.35 * gate_score + 0.25 * rank_ic_score + 0.20 * sharpe_score + 0.15 * validation_score + 0.05 * dd_score
```
`gate_score`（4 个 gate 等权平均）占 35%，但 gate_score 本身的离散度很低（只有 0, 0.25, 0.5, 0.75, 1.0 五个值）。这意味着 brutal_score 在 gate 通过数量相同时主要由 rank_ic 和 sharpe 驱动，gate 权重看起来是 35% 但实际上区分度很低。

### 5.3 因子评价问题汇总

| 问题 | 严重程度 | 影响 |
|------|----------|------|
| diversity 用 Jaccard 而非收益相关性 | **HIGH** | 误杀优质因子，放过冗余因子 |
| overfit_risk 使用括号计数 | MEDIUM | 复杂但合理的公式被过度惩罚 |
| stability 硬编码系数 | LOW | 评分缺乏校准 |
| Gate 1 使用 OR 逻辑 | MEDIUM | 负 IC 因子可能通过 |
| brutal_score gate 权重区分度低 | LOW | 排序主要由 IC/Sharpe 驱动 |
| 各维度评分函数使用大量 magic number | MEDIUM | 不可迁移到其他品种/周期 |

---

## 6. MCTS 搜索审计

### 6.1 搜索算法

使用 UCT（Upper Confidence Bound for Trees）选择节点：
```python
exploit = node.value
explore = exploration_weight * sqrt(log(parent_visits) / visits)
virtual_expand_bonus = 0.04 / (1 + len(children))
return exploit + explore + virtual_expand_bonus
```
- `exploration_weight=1.4` 来自 YAML 配置，为标准 UCT 的合理范围。
- `virtual_expand_bonus` 给未充分扩展的节点一个额外奖励，鼓励广度搜索。

### 6.2 问题 10: Max-Backup 而非 Average-Backup（MEDIUM）

```python
def _backpropagate(self, idx, reward):
    ...
    node.value = max(node.value, reward)
```
使用 **max-backup**：父节点的 value 等于子树中最佳子节点的 value。这意味着 MCTS 树记录的是"从这个节点出发曾经找到的最好公式"，而非"从这个节点出发的平均期望分数"。

**影响**: 
- 优点：鼓励 exploitation，快速锁定有潜力的方向。
- 缺点：如果一个节点偶然产生了一个高分公式（过拟合），其 value 会被永久锁定在最高值，即使后续扩展的子节点都很差。这可能导致搜索过度集中在运气好的节点。

论文 `arXiv-2505.11122v3` 中的标准 MCTS 通常使用 average backup。建议增加一个配置选项允许切换 backup 策略。

### 6.3 Frequent Subtree Avoidance（FSA）

```python
def frequent_subtrees(formulas, top_k=8):
    counter = Counter()
    for formula in formulas:
        counter.update(set(subtrees(formula))  # 去重后计数
    return counter.most_common(top_k)
```
- 提取所有公式的抽象子树（例如 `zscore(ret(close,n),n)`），统计出现频率，禁止最频繁的 top_k 个子树被再次生成。
- **问题**: 使用 `set()` 对每个公式的子树去重意味着"一个公式内部多次出现同一子树"不会额外增加计数。但如果一个子树出现在多个不同的公式中，它会被正确统计。逻辑正确。
- `top_k=8` 且当前的 zoo 规模通常 <100 个公式，FSA 主要阻止 `zscore(x,n)` 这种极其常见的模式。

### 6.4 维度假定（Dimension Hints）

MCTS 采样"弱维度"进行定向改进，使用 LLM prompt 传入维度提示：
```python
weights = [max(1.0 - dim_score, 0.05) for dim in DIMENSIONS]
```
合理，但没有对维度之间的 trade-off 建模（如降低 turnover 往往会降低 effectiveness）。

---

## 7. LLM 集成审计

### 7.1 DeepSeek API 调用

**安全配置（PASS）**: API key 从 `.env` 文件读取，不硬编码。公式生成使用白名单 DSL，LLM 输出经过 AST 解析验证，**即使 LLM 被 prompt-injected 也无法执行任意代码**。

**超时与重试（PASS）**: `timeout=(connect_timeout=15s, read_timeout=120s)`，最多重试 2 次，已分类捕获 `ConnectionError` / `Timeout` / `RuntimeError`。

### 7.2 问题 11: JSON 提取的鲁棒性（MEDIUM）

```python
def _extract_json(content):
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        return json.loads(match.group(0))
```
`re.search(r"\{.*\}", text, re.DOTALL)` 使用贪婪匹配 `.*`。如果 LLM 输出多个 JSON 对象，此正则可能匹配过长的文本（从第一个 `{` 到最后一个 `}`），导致解析失败或得到不完整的结果。建议改为 `\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}` 或使用 `json.JSONDecoder.raw_decode()` 迭代解析。

### 7.3 问题 12: 经济学关键词检查的脆弱性（LOW）

```python
def _has_economic_rationale(description):
    desc_lower = description.lower()
    return any(kw in desc_lower for kw in ECON_KEYWORDS)
```
简单子串匹配。描述 "This formula deliberately avoids momentum and reversal strategies" 会通过检查（因为包含 "momentum"）。但考虑到这只是一个最低限度的过滤（真正的解释质量审查依赖描述长度 + 人工检视），危害有限。

### 7.4 问题 13: Prompt 中的 `>` YAML 折叠（LOW）

`btcusdt.yaml` 中的 `system_prompt: >` 使用 YAML 的折叠块标量，会将多行内容中的换行符替换为空格。这意味着 LLM 收到的 system prompt 是单行文本。虽然 LLM 仍能理解，但结构化列表（如 EXAMPLES OF FORMULAS THAT PASS）在单行中可读性较差，可能导致 LLM 忽略部分指令。

建议改为 `system_prompt: |`（literal block scalar）保留换行符。

### 7.5 API Cooldown

`research.py` 中实现 API 调用间隔控制：每次 LLM 请求后 sleep `max(0, cooldown - proposal_dur)` 秒，默认 cooldown=30s。8 小时最多 ~960 次调用。合理的成本控制。

---

## 8. 数据管线审计

### 8.1 数据读取

**AutoQuant `data.py`** 和 **QuantumRandy `data.py`** 有大量代码重复（`read_ohlcv`, `read_funding`, `align_funding_to_ohlcv`, `slice_window` 实现了几乎相同的逻辑）。这是两个独立子项目之间的代码重复（违反 DRY 原则），但不是功能 bug。

### 8.2 资金费率对齐

```python
def align_funding_to_ohlcv(ohlcv, funding):
    aligned = funding.reindex(ohlcv.index.union(funding.index)).sort_index().ffill()
    return aligned.reindex(ohlcv.index)["funding_rate"].fillna(0.0)
```
- 将 8h 频率的 funding_rate 前向填充到 4h 频率的 OHLCV bar 上。
- **问题**: 在回测开始时，如果第一条 OHLCV bar 之前没有 funding 数据，会被 `fillna(0.0)` 填为 0。对于 2019-09-08 开始的数据，第一条 funding 数据在 2019-09-10 08:00，意味着前约 11 根 bar 的 funding_rate=0。影响极小。

### 8.3 时间窗口切分

```python
out = out[out.index >= pd.Timestamp(start, tz="UTC")]
out = out[out.index < pd.Timestamp(end, tz="UTC")]   # 注意: 不包含 end
```
使用左闭右开区间，不会产生边界重叠。正确。

### 8.4 数据质量

- `BTCUSDT_4h.csv`: 从 2019-09-08 开始，约 14,000+ 根 bar，6 年数据。
- `BTCUSDT_funding.csv`: 从 2019-09-10 开始，8h 间隔。
- **数据来源**: 通过 `fetch_binance.py` 从 Binance API 直接获取，未经第三方清洗。

### 8.5 问题 14: QuantumRandy 配置路径依赖（LOW）

`btcusdt.yaml` 中的数据路径使用相对路径：
```yaml
ohlcv_csv: ../../AutoQuant/data/BTCUSDT_4h.csv
```
这是从 `configs/` 目录出发的相对路径。如果从项目根目录或绝对路径运行，`load_config()` 中的 `_resolve_path()` 会基于 config 文件所在目录解析。但如果 config 文件被移动或复制，路径会断裂。

---

## 9. 配置与参数审计

### 9.1 配置不一致问题

通过对比 `btcusdt.yaml`、`config.py` 默认值和 `PROJECT_LOG.md` 中的记录，发现以下不一致：

| 参数 | YAML | 代码默认 | PROJECT_LOG 声称 | 实际生效 |
|------|------|----------|------------------|----------|
| `max_formula_depth` | 5 | 3 | "4→5" | **5** (YAML 覆盖) |
| `max_formula_operators` | 6 | 6 | "6→8" (声称放宽) | **6** (YAML 值) |
| `complexity_penalty` | 0.02 | 0.02 | "0.025→0.05" | **0.02** (YAML 值) |
| `min_rank_ic` | 0.01 | 0.01 | "0.02→0.01" | **0.01** |
| `min_directional_win_rate` | 0.49 | 0.49 | "0.53→0.49" | **0.49** |
| `min_cost_sharpe` | 0.30 | 0.30 | "1.00→0.30" | **0.30** |

**PROJECT_LOG 声称 `complexity_penalty` 已改为 0.05，`max_formula_operators` 已放宽到 8，但当前 YAML 文件中仍是 0.02 和 6。** 这意味着之前测试中"生效"的惩罚值可能不是开发者以为的值。这是一个配置管理问题——PROJECT_LOG 作为日志和 YAML 作为真实配置源之间存在脱节。

### 9.2 窗口切分审计

AutoQuant `strict4h.yaml`:
- training: 2019-09-08 → 2021-01-01 (~16 个月)
- validation: 2021-01-01 → 2023-01-01 (~24 个月)
- blind: 2024-01-01 → 2025-11-24

QuantumRandy `btcusdt.yaml`:
- training: 2019-09-08 → 2024-01-01 (~52 个月, 含一轮完整牛熊)
- validation: 2024-01-01 → 2025-11-24 (~23 个月)

**AutoQuant 的训练集（16 个月）偏短**，只覆盖 2019 年末到 2021 年初的牛市，未经历 2021 年 5 月的暴跌和 2022 年的熊市。这导致 Stage I 优化出的参数可能在市场结构变化时表现脆弱。

**QuantumRandy 的训练集更长（52 个月）**，涵盖了完整的牛熊周期，更有利于发现稳健因子。

### 9.3 成本参数

| 参数 | AutoQuant | QuantumRandy | 评价 |
|------|-----------|--------------|------|
| taker_bps | 4.0 | 4.0 | 接近 Binance 实际费率 |
| slippage_bps | 2.0 | 1.0 | QR 更乐观 |
| funding_multiplier | 1.0 | 1.0 | 正常 |

---

## 10. 代码质量与工程问题

### 10.1 代码重复

1. **`backtest.py` 中的指标函数在 AutoQuant 和 QuantumRandy 中重复实现**: `equity_curve`, `max_drawdown`, `sharpe`, `cagr` 在两个项目中各有独立实现。AutoQuant 的 `sharpe` 含无风险利率，QuantumRandy 的不含。

2. **`data.py` 重复**: 两个项目的 `data.py` 近 80% 代码相似。

3. **`summarize_ledger` vs `summarize`**: AutoQuant 的 `metrics.py` 中有 `summarize()`，QuantumRandy 的 `backtest.py` 中有 `summarize_ledger()`，返回字段名不同但功能重叠。

### 10.2 测试覆盖

- **AutoQuant**: 零测试。
- **QuantumRandy**: 仅有 `tests/test_smoke.py`，一个 20 行的 smoke test。测试覆盖度极低。

### 10.3 错误处理

- `expression.py` 中的 `evaluate_formula` 使用 `fillna(0.0)` 静默替换所有 NaN 和 Inf。如果公式产生全 NaN（如除以零、log 负数），会在不报错的情况下返回全零序列，对应的 IC=0, Sharpe=0，然后因子被默默淘汰。
- `mcts.py` `_evaluate_proposals` 中 `except Exception: continue` 吞掉所有异常而未记录。
- `llm.py` 中 DeepSeek API 异常被分类但仍有可能有未被覆盖的异常类型（如 `requests.JSONDecodeError`）。

### 10.4 线程安全

`research.py` 使用 `threading.RLock()` 保护状态访问，但 `_audit_new_alphas()` 在锁外部操作 `self.brutal_results`（字典修改）。`_run_loop` 在持有锁的情况下修改 state 字段，但在调用 `self.mcts.run(1)` 和 `self._audit_new_alphas()` 时释放锁。整体线程安全性较好。

### 10.5 问题 15: `purge_killed()` 可能破坏 MCTS 树（MEDIUM）

```python
def purge_killed(self):
    ...
    self.mcts.nodes = [n for n in self.mcts.nodes if n.formula not in killed]
```
删除节点后，幸存节点的 `parent` 和 `children` 索引可能指向不存在的位置，导致后续 MCTS 迭代中的 `_uct()` 计算访问到错误的节点或索引越界。

---

## 11. 安全问题

### 11.1 API Key 管理（PASS with NOTE）

- `.env` 文件包含真实的 `DEEPSEEK_API_KEY`（从 sample output 中可见 `DEEPSEEK_API_KEY=sk-...`）。
- QuantumRandy 的 `.gitignore` 排除了 `.env` 文件。
- AutoQuant 没有 `.gitignore` 中的 `.env` 排除（但 AutoQuant 不使用 `.env`）。
- **建议**: 确认 `QuantumRandy/.gitignore` 中包含 `.env` 行。

### 11.2 Dashboard HTTP 安全（NOTE）

Dashboard 绑定 `127.0.0.1` 仅本地访问，不暴露到网络。但如果用户改为 `0.0.0.0`，则任何人都可访问控制按钮。`/api/start`, `/api/stop`, `/api/emergency` 无认证。建议在 README 中增加安全警告。

### 11.3 代码注入（PASS）

公式使用 AST 解析和白名单，不存在代码注入风险。

---

## 12. Bug 汇总

### Critical (0)
无。未发现导致回测结果完全无效或系统崩溃的 bug。

### High (1)

| ID | 位置 | 描述 | 影响 |
|----|------|------|------|
| **H1** | `evaluator.py:_diversity_score` | 使用公式字符串 token Jaccard 相似度而非因子值相关性衡量差异度 | 可能误杀信号不同但 token 相似的因子（如 `zscore(close,120)` vs `zscore(close,48)`），或放过信号相同但 token 不同的因子 |

### Medium (7)

| ID | 位置 | 描述 |
|----|------|------|
| **M1** | `scripts/run_stage2.py` | Stage II 稳健检验在含验证期的数据上运行，造成验证期信息泄露 |
| **M2** | `mcts.py:_backpropagate` | Max-backup 导致过拟合节点被永久锁定高分 |
| **M3** | `llm.py:_extract_json` | JSON 贪婪正则匹配可能合并多个 JSON 对象 |
| **M4** | `research.py:purge_killed` | 删除 MCTS 节点后索引断裂 |
| **M5** | `backtest.py:sharpe` (QR) | 未扣除无风险利率，与 AutoQuant 不可比 |
| **M6** | `evaluator.py` | 5 维度评分函数使用大量 magic number 硬编码系数 |
| **M7** | `lab.py:run_brutal_filter` | Gate 1 使用 OR 逻辑，负 IC 因子可通过 |

### Low (8)

| ID | 位置 | 描述 |
|----|------|------|
| **L1** | `engine.py:19` / `backtest.py:27` | `diff().fillna(exposure)` 导致首 bar 虚高 turnover |
| **L2** | `config.py` vs `btcusdt.yaml` | `complexity_penalty` 和 `max_formula_operators` YAML 值与 PROJECT_LOG 记录不一致 |
| **L3** | `optimize.py:CAGR` | `total <= 0` 返回 -1.0 导致破产策略排名高于微亏策略 |
| **L4** | `evaluator.py:_overfit_proxy` | 括号计数作为过拟合代理过于粗糙 |
| **L5** | `llm.py:_has_economic_rationale` | 关键词子串匹配可能被否定句式欺骗 |
| **L6** | `btcusdt.yaml` | `system_prompt: >` 折叠换行，影响 LLM 理解 |
| **L7** | `proposals.py` | 本地模板空间有限，无 LLM 时 zoo 快速饱和（已记录但未在代码中告警） |
| **L8** | `data.py` (两个项目) | 代码大量重复，维护负担 |

---

## 13. 改进建议优先级

### P0 — 立即修复（影响结果有效性）

1. **修复 diversity_score (H1)**: 改用因子值序列的 Pearson/Spearman 相关性代替 token Jaccard。
2. **修复 Stage II 数据泄露 (M1)**: 将 robust_summary 的回测限定在训练窗口。

### P1 — 短期改进（提升挖掘质量）

3. **Gate 1 改用 AND 逻辑 (M7)**: `rank_ic >= 0.01 AND directional_win_rate >= 0.49`。
4. **MCTS 增加 average-backup 选项 (M2)**: 允许配置 backup 策略。
5. **修复 JSON 提取正则 (M3)**: 使用非贪婪匹配或 JSONDecoder。
6. **统一 Sharpe 计算 (M5)**: QuantumRandy 的 sharpe 与 AutoQuant 对齐。
7. **修复配置不一致 (L2)**: 确认 PROJECT_LOG 中的参数变更已落地到 YAML，或反之。
8. **修复首 bar 处理 (L1)**: `diff().fillna(0.0)`。

### P2 — 中期改进（提升系统稳健性）

9. **增加 walk-forward 验证**: 多窗口滚动训练/验证，而非单次 split。
10. **增加真正 hold-out test set**: 盲测期完全不参与任何筛选。
11. **修复 purge_killed 索引断裂 (M4)**。
12. **校准评分函数参数 (M6)**: 使用历史数据回测结果校准 `tanh` 缩放因子和权重。
13. **增加测试覆盖**: 至少对回测引擎、表达式引擎、evaluator 有单元测试。
14. **因子 decay 分析**: 不仅看半衰期，还要看 IC decay profile。

### P3 — 长期改进（扩展性）

15. **消除代码重复**: 将共享模块提取到 `common/` 库。
16. **多品种支持**: 按 README 规划扩展 ETH/SOL/BNB。
17. **因子组合优化**: 实现 alpha 组合（等权/IC 加权/最优化权重）。
18. **LLM 过拟合风险评估**: 让 LLM 审查公式逻辑合理性（非仅关键词匹配）。
19. **Dashboard 安全增强**: 增加基本认证（若暴露到外网）。

---

## 附录 A: 未来函数检查清单

| 检查项 | AutoQuant | QuantumRandy | 结论 |
|--------|-----------|--------------|------|
| 信号使用未来价格 | 否 (shift(1)) | 否 (shift(delay_bars)) | PASS |
| 滚动窗口使用未来数据 | 否 (rolling) | 否 (rolling/ewm) | PASS |
| IC 计算使用未来收益 | N/A | 是，但这是标准做法 | PASS |
| zscore 使用未来均值/std | 否 | 否 | PASS |
| 训练集参数用于验证集评分 | N/A | 否 (分窗口) | PASS |
| Stage II 稳健检验在验证期 | **是** | N/A | **FAIL** |
| 首 bar 入场成本 | 虚高 | 虚高 | LOW |

## 附录 B: 评分函数 Magic Number 清单

| 位置 | Magic Number | 含义 | 建议 |
|------|-------------|------|------|
| `_percentile` | 30.0 | tanh 缩放因子 | 校准到历史 IC 分布 |
| `_stability_score` | 15.0 | 月 std 缩放 | 校准到历史月收益分布 |
| `_stability_score` | 0.75/0.25 | positive vs vol 权重 | 做消融实验确定 |
| `_turnover_score` | 3.0 | 换手惩罚斜率 | 校准到历史换手分布 |
| `_overfit_proxy` | 0.65/0.35/25.0 | 复杂度 vs 回撤权重 | 使用公式深度/算子数替代括号计数 |
| `brutal_rank_score` | 0.35/0.25/0.20/0.15/0.05 | 五因子权重 | 做权重敏感性分析 |
| `brutal_rank_score` | 0.05 (rank_ic divisor) | IC 归一化基准 | 需约等于 top 5% 因子的 IC |
| `brutal_rank_score` | 2.0 (sharpe divisor) | Sharpe 归一化基准 | 需约等于 top 10% 因子的 Sharpe
| `_uct` | 0.04 | virtual expand bonus | 可调参数 |

---

*审计完成。所有行号基于审计时的代码版本。建议在修改代码后重新运行审计。*
