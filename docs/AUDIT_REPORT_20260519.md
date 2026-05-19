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
此处 `shift(-1)` 取下一期收益，用于衡量因子的**预测能力**。这是学界和业界计算 Information Coefficient 的标准做法，**不是未来函数**。

### 2.3 滚动窗口算子（PASS）

`expression.py` 中所有滚动算子均使用 `rolling(window)` 或 `ewm(span=window)`，这些 pandas 方法只使用到当前 bar 为止的历史数据。

### 2.4 问题 1: Exposure 首 bar 处理偏差（MEDIUM）

**已修复**: `diff().fillna(exposure)` → `fillna(0.0)`（2026-05-19）

### 2.5 问题 2: Stage II 稳健检验使用验证期数据（MEDIUM）

**已修复**: `slice_window(..., validation_end)` → `training_end`（2026-05-19）

### 2.6 问题 3: EMA 和 zscore 的初始值偏置（LOW）

`min_periods=window` 意味着前 window-1 个 bar 的结果是 NaN（之后被 fillna(0.0) 填充为 0）。影响可忽略。

---

## 3. 回测引擎审计

### 3.1 收益计算（PASS）
### 3.2 成本建模（PASS）

### 3.3 问题 4: Sharpe Ratio 计算（MEDIUM）

**已修复**: QuantumRandy `sharpe()` 新增 `risk_free_rate=0.03` 参数，对齐 AutoQuant（2026-05-19）

### 3.4 问题 5: CAGR 的失败返回值（LOW）

**已修复**: `return -1.0` → `return -0.9999`（2026-05-19）

---

## 4. 因子挖掘审计

### 4.1 公式 DSL 与表达式引擎（PASS）
### 4.2 问题 7: `rank` 算子实现存疑（LOW）
### 4.3 问题 8: 本地生成器模板空间有限（MEDIUM）
### 4.4 问题 9: 种子公式质量参差（LOW）

---

## 5. 因子评价体系审计

### 5.1 MCTS 内部评分（5 维度）

#### diversity（差异度）

**重大方法论缺陷（HIGH）**: 使用公式字符串的 token-level Jaccard 相似度作为"差异度"度量。
**已修复**: 改用因子值序列的 Pearson correlation（2026-05-19）

### 5.2 四步残酷筛选（Brutal Filter）

#### Gate 1 逻辑

**问题（MEDIUM）**: 使用 OR 逻辑，负 IC 因子可通过。
**已修复**: `or` → `and`（2026-05-19）

---

## 6. MCTS 搜索审计

### 6.1 搜索算法（PASS）

### 6.2 问题 10: Max-Backup 而非 Average-Backup（MEDIUM）

**已修复**: `config.py` + YAML 新增 `backup_strategy`（默认 `average`），`_backpropagate` 支持两种策略（2026-05-19）

---

## 7. LLM 集成审计

### 7.1 DeepSeek API 调用（PASS）

### 7.2 问题 11: JSON 提取的鲁棒性（MEDIUM）

**已修复**: 贪婪正则 `\{.*\}` → `json.JSONDecoder().raw_decode()`（2026-05-19）

### 7.3 问题 12: 经济学关键词检查的脆弱性（LOW）
### 7.4 问题 13: Prompt 中的 `>` YAML 折叠（LOW）

**已修复**: `system_prompt: >` → `system_prompt: |` literal block scalar（2026-05-19）

---

## 8. 数据管线审计（PASS）

---

## 9. 配置与参数审计

### 9.1 配置不一致问题

**已修复**: `complexity_penalty` YAML + 代码默认值 0.02 → 0.05，对齐 PROJECT_LOG 记录（2026-05-19）

---

## 10. 代码质量与工程问题

- 两个项目间存在代码重复（`backtest.py`, `data.py`, `metrics.py`）
- 测试覆盖极低（QuantumRandy 仅 smoke test，AutoQuant 零测试）

---

## 11. 安全问题

- API Key 管理（PASS）: `.env` 已 gitignored
- Dashboard HTTP 仅绑定 127.0.0.1
- 代码注入（PASS）: AST 白名单解析

---

## 12. Bug 汇总

### 修复状态

| ID | 严重度 | 描述 | 状态 |
|----|--------|------|------|
| H1 | HIGH | diversity_score 用 Jaccard 而非因子值相关性 | ✅ 已修复 |
| M1 | MEDIUM | Stage II 验证期泄露 | ✅ 已修复 |
| M2 | MEDIUM | MCTS max-backup | ✅ 已修复 |
| M3 | MEDIUM | JSON 贪婪正则 | ✅ 已修复 |
| M5 | MEDIUM | QR Sharpe 无风险利率 | ✅ 已修复 |
| M7 | MEDIUM | Gate 1 OR 逻辑 | ✅ 已修复 |
| L1 | LOW | 首 bar diff fillna | ✅ 已修复 |
| L2 | LOW | complexity_penalty 不一致 | ✅ 已修复 |
| L3 | LOW | CAGR 破产返回值 | ✅ 已修复 |
| L6 | LOW | YAML system_prompt > | ✅ 已修复 |
| M4 | MEDIUM | purge_killed 索引断裂 | ⏸ 暂缓 |
| M6 | MEDIUM | Magic number 硬编码 | ⏸ 暂缓 |

---

## 13. 改进建议优先级

### P0 — 已修复

1. ✅ diversity_score (H1)
2. ✅ Stage II 数据泄露 (M1)

### P1 — 已修复

3. ✅ Gate 1 AND 逻辑 (M7)
4. ✅ MCTS average-backup (M2)
5. ✅ JSON 提取正则 (M3)
6. ✅ Sharpe 统一 (M5)
7. ✅ 配置不一致 (L2)
8. ✅ 首 bar 处理 (L1)

### P2 — 中期改进

9. walk-forward 验证
10. 真正 hold-out test set
11. purge_killed 索引断裂 (M4)
12. 评分函数参数校准 (M6)
13. 测试覆盖
14. 因子 decay 分析

### P3 — 长期改进

15. 消除代码重复
16. 多品种支持
17. 因子组合优化
18. LLM 过拟合风险评估
19. Dashboard 安全增强

---

*审计完成于 2026-05-19。10/12 个问题已修复。*
