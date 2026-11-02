# 多智能体最优执行模拟：本次运行记录

运行时间（UTC）：2026-11-02 13:01:50
模拟设置：每方母单 100,000 股，执行窗口 30 分钟、每 30 秒一步（共 60 步）；A/B 同时决策。
训练：每个手续费档、每种 Q 策略 1200 回合；评估：每个手续费×波动场景×策略×对手组合 30 个配对随机种子。

## 怎样解读

以下结果由本地模拟器实际生成。价格、冲击、价差和对手规则均为明确的教学模拟设定，不是历史市场估计。成本与奖励口径不同：执行缺口按成交均价对初始参考价计算，训练奖励另包含库存风险和未完成惩罚。Q 值受奖励刻度、训练轮数和随机种子影响，不能单独作为策略优劣结论。

## 按成本档的平均结果

表中对每种 A 策略在全部五类 B 对手上的评估均值再取平均；详细的逐对手结果见 `evaluation_summary.csv`。

| 手续费 | 波动场景 | A 策略 | 平均执行缺口 (bp) | 完成率 | 平均奖励 | 等待动作占比 | 人工复核率 |
|---:|---|---|---:|---:|---:|---:|---:|
| 0.1% | normal | G0_TWAP | 15.23 | 1.000 | -15.60 | 0.000 | 0.000 |
| 0.1% | normal | G1_dynamic_rule | 15.43 | 1.000 | -15.77 | 0.000 | 0.000 |
| 0.1% | normal | G2_Q_learning | 15.40 | 1.000 | -15.95 | 0.440 | 0.000 |
| 0.1% | normal | G3_opponent_aware_Q | 15.42 | 1.000 | -15.94 | 0.362 | 0.000 |
| 0.1% | high_volatility | G0_TWAP | 12.21 | 1.000 | -12.95 | 0.000 | 1.000 |
| 0.1% | high_volatility | G1_dynamic_rule | 13.00 | 1.000 | -13.66 | 0.000 | 1.000 |
| 0.1% | high_volatility | G2_Q_learning | 11.11 | 1.000 | -12.20 | 0.443 | 1.000 |
| 0.1% | high_volatility | G3_opponent_aware_Q | 11.32 | 1.000 | -12.37 | 0.361 | 1.000 |
| 0.3% | normal | G0_TWAP | 40.32 | 1.000 | -40.69 | 0.000 | 0.000 |
| 0.3% | normal | G1_dynamic_rule | 40.35 | 1.000 | -40.72 | 0.000 | 0.000 |
| 0.3% | normal | G2_Q_learning | 42.51 | 1.000 | -43.06 | 0.472 | 0.000 |
| 0.3% | normal | G3_opponent_aware_Q | 42.16 | 1.000 | -42.68 | 0.373 | 0.000 |
| 0.3% | high_volatility | G0_TWAP | 42.40 | 1.000 | -43.14 | 0.000 | 0.933 |
| 0.3% | high_volatility | G1_dynamic_rule | 42.36 | 1.000 | -43.07 | 0.000 | 0.933 |
| 0.3% | high_volatility | G2_Q_learning | 45.25 | 1.000 | -46.36 | 0.473 | 0.933 |
| 0.3% | high_volatility | G3_opponent_aware_Q | 44.75 | 1.000 | -45.80 | 0.371 | 0.933 |
| 0.5% | normal | G0_TWAP | 58.21 | 1.000 | -58.58 | 0.000 | 0.000 |
| 0.5% | normal | G1_dynamic_rule | 58.02 | 1.000 | -58.39 | 0.000 | 0.000 |
| 0.5% | normal | G2_Q_learning | 59.37 | 1.000 | -59.92 | 0.464 | 0.000 |
| 0.5% | normal | G3_opponent_aware_Q | 59.17 | 1.000 | -59.70 | 0.382 | 0.000 |
| 0.5% | high_volatility | G0_TWAP | 58.15 | 1.000 | -58.89 | 0.000 | 0.867 |
| 0.5% | high_volatility | G1_dynamic_rule | 57.86 | 1.000 | -58.57 | 0.000 | 0.867 |
| 0.5% | high_volatility | G2_Q_learning | 58.92 | 1.000 | -60.03 | 0.470 | 0.867 |
| 0.5% | high_volatility | G3_opponent_aware_Q | 58.78 | 1.000 | -59.83 | 0.379 | 0.867 |

## 同种子配对差异

正的成本差表示策略比基线成本高，负值表示低。区间为正态近似 95% 区间；逐种子原始结果在 `evaluation_raw.csv`，完整比较在 `paired_comparisons.csv`。

| 手续费 | 波动场景 | B 对手 | 假设对照 | 成本差 bp (策略−基线) | 近似 95% 区间 | 完成率差 |
|---:|---|---|---|---:|---:|---:|
| 0.1% | normal | twap | H1 dynamic feedback vs fixed TWAP | 0.19 | [-0.26, 0.64] | 0.000 |
| 0.1% | normal | twap | H2 Q-learning vs dynamic rule | 0.05 | [-1.55, 1.65] | 0.000 |
| 0.1% | normal | twap | H3 opponent information vs none | -0.00 | [-0.04, 0.04] | 0.000 |
| 0.1% | normal | frontloaded | H1 dynamic feedback vs fixed TWAP | 0.24 | [-0.19, 0.67] | 0.000 |
| 0.1% | normal | frontloaded | H2 Q-learning vs dynamic rule | -0.19 | [-1.76, 1.39] | 0.000 |
| 0.1% | normal | frontloaded | H3 opponent information vs none | 0.11 | [-0.03, 0.24] | 0.000 |
| 0.1% | normal | backloaded | H1 dynamic feedback vs fixed TWAP | 0.20 | [-0.27, 0.67] | 0.000 |
| 0.1% | normal | backloaded | H2 Q-learning vs dynamic rule | -0.08 | [-1.71, 1.54] | 0.000 |
| 0.1% | normal | backloaded | H3 opponent information vs none | 0.03 | [-0.03, 0.08] | 0.000 |
| 0.1% | normal | bursty | H1 dynamic feedback vs fixed TWAP | 0.20 | [-0.25, 0.65] | 0.000 |
| 0.1% | normal | bursty | H2 Q-learning vs dynamic rule | 0.05 | [-1.56, 1.65] | 0.000 |
| 0.1% | normal | bursty | H3 opponent information vs none | -0.02 | [-0.74, 0.70] | 0.000 |
| 0.1% | normal | randomized | H1 dynamic feedback vs fixed TWAP | 0.19 | [-0.27, 0.65] | 0.000 |
| 0.1% | normal | randomized | H2 Q-learning vs dynamic rule | 0.04 | [-1.59, 1.66] | 0.000 |
| 0.1% | normal | randomized | H3 opponent information vs none | -0.04 | [-0.27, 0.18] | 0.000 |
| 0.1% | high_volatility | twap | H1 dynamic feedback vs fixed TWAP | 0.78 | [-0.29, 1.86] | 0.000 |
| 0.1% | high_volatility | twap | H2 Q-learning vs dynamic rule | -1.82 | [-5.34, 1.70] | 0.000 |
| 0.1% | high_volatility | twap | H3 opponent information vs none | 0.01 | [-0.08, 0.10] | 0.000 |
| 0.1% | high_volatility | frontloaded | H1 dynamic feedback vs fixed TWAP | 0.80 | [-0.25, 1.85] | 0.000 |
| 0.1% | high_volatility | frontloaded | H2 Q-learning vs dynamic rule | -2.03 | [-5.51, 1.44] | 0.000 |
| 0.1% | high_volatility | frontloaded | H3 opponent information vs none | 0.26 | [-0.03, 0.54] | 0.000 |
| 0.1% | high_volatility | backloaded | H1 dynamic feedback vs fixed TWAP | 0.79 | [-0.30, 1.89] | 0.000 |
| 0.1% | high_volatility | backloaded | H2 Q-learning vs dynamic rule | -1.98 | [-5.53, 1.56] | 0.000 |
| 0.1% | high_volatility | backloaded | H3 opponent information vs none | 0.02 | [-0.07, 0.10] | 0.000 |
| 0.1% | high_volatility | bursty | H1 dynamic feedback vs fixed TWAP | 0.77 | [-0.30, 1.85] | 0.000 |
| 0.1% | high_volatility | bursty | H2 Q-learning vs dynamic rule | -1.81 | [-5.33, 1.71] | 0.000 |
| 0.1% | high_volatility | bursty | H3 opponent information vs none | 0.78 | [-0.87, 2.44] | 0.000 |
| 0.1% | high_volatility | randomized | H1 dynamic feedback vs fixed TWAP | 0.77 | [-0.29, 1.84] | 0.000 |
| 0.1% | high_volatility | randomized | H2 Q-learning vs dynamic rule | -1.82 | [-5.35, 1.72] | 0.000 |
| 0.1% | high_volatility | randomized | H3 opponent information vs none | 0.01 | [-0.41, 0.44] | 0.000 |
| 0.3% | normal | twap | H1 dynamic feedback vs fixed TWAP | 0.01 | [-0.25, 0.27] | 0.000 |
| 0.3% | normal | twap | H2 Q-learning vs dynamic rule | 2.23 | [1.16, 3.30] | 0.000 |
| 0.3% | normal | twap | H3 opponent information vs none | -0.02 | [-0.06, 0.03] | 0.000 |
| 0.3% | normal | frontloaded | H1 dynamic feedback vs fixed TWAP | 0.08 | [-0.16, 0.32] | 0.000 |
| 0.3% | normal | frontloaded | H2 Q-learning vs dynamic rule | 1.98 | [0.93, 3.03] | 0.000 |
| 0.3% | normal | frontloaded | H3 opponent information vs none | -0.08 | [-0.17, 0.01] | 0.000 |
| 0.3% | normal | backloaded | H1 dynamic feedback vs fixed TWAP | 0.00 | [-0.27, 0.27] | 0.000 |
| 0.3% | normal | backloaded | H2 Q-learning vs dynamic rule | 2.11 | [1.02, 3.19] | 0.000 |
| 0.3% | normal | backloaded | H3 opponent information vs none | -0.03 | [-0.08, 0.01] | 0.000 |
| 0.3% | normal | bursty | H1 dynamic feedback vs fixed TWAP | 0.01 | [-0.24, 0.27] | 0.000 |
| 0.3% | normal | bursty | H2 Q-learning vs dynamic rule | 2.23 | [1.15, 3.30] | 0.000 |
| 0.3% | normal | bursty | H3 opponent information vs none | -1.29 | [-2.03, -0.54] | 0.000 |
| 0.3% | normal | randomized | H1 dynamic feedback vs fixed TWAP | 0.03 | [-0.22, 0.28] | 0.000 |
| 0.3% | normal | randomized | H2 Q-learning vs dynamic rule | 2.23 | [1.19, 3.27] | 0.000 |
| 0.3% | normal | randomized | H3 opponent information vs none | -0.31 | [-0.50, -0.13] | 0.000 |
| 0.3% | high_volatility | twap | H1 dynamic feedback vs fixed TWAP | -0.05 | [-0.64, 0.54] | 0.000 |
| 0.3% | high_volatility | twap | H2 Q-learning vs dynamic rule | 2.96 | [0.58, 5.35] | 0.000 |
| 0.3% | high_volatility | twap | H3 opponent information vs none | -0.04 | [-0.10, 0.02] | 0.000 |
| 0.3% | high_volatility | frontloaded | H1 dynamic feedback vs fixed TWAP | 0.05 | [-0.50, 0.61] | 0.000 |
| 0.3% | high_volatility | frontloaded | H2 Q-learning vs dynamic rule | 2.67 | [0.33, 5.00] | 0.000 |
| 0.3% | high_volatility | frontloaded | H3 opponent information vs none | -0.18 | [-0.45, 0.09] | 0.000 |
| 0.3% | high_volatility | backloaded | H1 dynamic feedback vs fixed TWAP | -0.12 | [-0.73, 0.49] | 0.000 |
| 0.3% | high_volatility | backloaded | H2 Q-learning vs dynamic rule | 2.91 | [0.50, 5.32] | 0.000 |
| 0.3% | high_volatility | backloaded | H3 opponent information vs none | -0.03 | [-0.09, 0.03] | 0.000 |
| 0.3% | high_volatility | bursty | H1 dynamic feedback vs fixed TWAP | -0.05 | [-0.64, 0.54] | 0.000 |
| 0.3% | high_volatility | bursty | H2 Q-learning vs dynamic rule | 2.97 | [0.59, 5.36] | 0.000 |
| 0.3% | high_volatility | bursty | H3 opponent information vs none | -1.76 | [-3.25, -0.27] | 0.000 |
| 0.3% | high_volatility | randomized | H1 dynamic feedback vs fixed TWAP | -0.04 | [-0.63, 0.55] | 0.000 |
| 0.3% | high_volatility | randomized | H2 Q-learning vs dynamic rule | 2.96 | [0.60, 5.32] | 0.000 |
| 0.3% | high_volatility | randomized | H3 opponent information vs none | -0.49 | [-0.88, -0.11] | 0.000 |
| 0.5% | normal | twap | H1 dynamic feedback vs fixed TWAP | -0.19 | [-0.42, 0.04] | 0.000 |
| 0.5% | normal | twap | H2 Q-learning vs dynamic rule | 1.43 | [0.45, 2.40] | 0.000 |
| 0.5% | normal | twap | H3 opponent information vs none | -0.03 | [-0.08, 0.02] | 0.000 |
| 0.5% | normal | frontloaded | H1 dynamic feedback vs fixed TWAP | -0.17 | [-0.40, 0.07] | 0.000 |
| 0.5% | normal | frontloaded | H2 Q-learning vs dynamic rule | 1.23 | [0.27, 2.19] | 0.000 |
| 0.5% | normal | frontloaded | H3 opponent information vs none | -0.13 | [-0.27, 0.02] | 0.000 |
| 0.5% | normal | backloaded | H1 dynamic feedback vs fixed TWAP | -0.19 | [-0.43, 0.05] | 0.000 |
| 0.5% | normal | backloaded | H2 Q-learning vs dynamic rule | 1.28 | [0.30, 2.25] | 0.000 |
| 0.5% | normal | backloaded | H3 opponent information vs none | -0.02 | [-0.08, 0.03] | 0.000 |
| 0.5% | normal | bursty | H1 dynamic feedback vs fixed TWAP | -0.19 | [-0.42, 0.04] | 0.000 |
| 0.5% | normal | bursty | H2 Q-learning vs dynamic rule | 1.42 | [0.45, 2.40] | 0.000 |
| 0.5% | normal | bursty | H3 opponent information vs none | -0.71 | [-1.44, 0.02] | 0.000 |
| 0.5% | normal | randomized | H1 dynamic feedback vs fixed TWAP | -0.19 | [-0.42, 0.04] | 0.000 |
| 0.5% | normal | randomized | H2 Q-learning vs dynamic rule | 1.37 | [0.40, 2.33] | 0.000 |
| 0.5% | normal | randomized | H3 opponent information vs none | -0.09 | [-0.33, 0.16] | 0.000 |
| 0.5% | high_volatility | twap | H1 dynamic feedback vs fixed TWAP | -0.30 | [-0.76, 0.16] | 0.000 |
| 0.5% | high_volatility | twap | H2 Q-learning vs dynamic rule | 1.14 | [-0.96, 3.23] | 0.000 |
| 0.5% | high_volatility | twap | H3 opponent information vs none | -0.03 | [-0.09, 0.04] | 0.000 |
| 0.5% | high_volatility | frontloaded | H1 dynamic feedback vs fixed TWAP | -0.24 | [-0.69, 0.20] | 0.000 |
| 0.5% | high_volatility | frontloaded | H2 Q-learning vs dynamic rule | 0.90 | [-1.16, 2.96] | 0.000 |
| 0.5% | high_volatility | frontloaded | H3 opponent information vs none | -0.05 | [-0.31, 0.21] | 0.000 |
| 0.5% | high_volatility | backloaded | H1 dynamic feedback vs fixed TWAP | -0.32 | [-0.78, 0.14] | 0.000 |
| 0.5% | high_volatility | backloaded | H2 Q-learning vs dynamic rule | 1.02 | [-1.08, 3.12] | 0.000 |
| 0.5% | high_volatility | backloaded | H3 opponent information vs none | 0.01 | [-0.06, 0.07] | 0.000 |
| 0.5% | high_volatility | bursty | H1 dynamic feedback vs fixed TWAP | -0.30 | [-0.75, 0.16] | 0.000 |
| 0.5% | high_volatility | bursty | H2 Q-learning vs dynamic rule | 1.14 | [-0.95, 3.23] | 0.000 |
| 0.5% | high_volatility | bursty | H3 opponent information vs none | -0.55 | [-2.07, 0.96] | 0.000 |
| 0.5% | high_volatility | randomized | H1 dynamic feedback vs fixed TWAP | -0.30 | [-0.76, 0.16] | 0.000 |
| 0.5% | high_volatility | randomized | H2 Q-learning vs dynamic rule | 1.10 | [-0.99, 3.19] | 0.000 |
| 0.5% | high_volatility | randomized | H3 opponent information vs none | -0.09 | [-0.60, 0.42] | 0.000 |

## 学习诊断

| 手续费 | 学习器 | 训练回合 | 最近 100 回合平均奖励 | 前 100 回合平均奖励 | 初始状态 max Q | 已访问状态数 |
|---:|---|---:|---:|---:|---:|---:|
| 0.1% | G2_Q_learning | 1200 | -21.58 | -20.83 | -0.06 | 1106 |
| 0.1% | G3_opponent_aware_Q | 1200 | -20.06 | -20.12 | -0.04 | 1533 |
| 0.3% | G2_Q_learning | 1200 | -38.90 | -40.47 | -0.06 | 1123 |
| 0.3% | G3_opponent_aware_Q | 1200 | -37.65 | -39.55 | -0.04 | 1491 |
| 0.5% | G2_Q_learning | 1200 | -59.32 | -59.25 | -0.06 | 1011 |
| 0.5% | G3_opponent_aware_Q | 1200 | -57.62 | -60.68 | -0.03 | 1554 |

## 实验限制与下一步

- 这是单一资产、单一离散时间步长的模拟，不包含真实订单簿撮合、队列优先级、隐藏流动性、市场制度或历史逐笔行情。
- G2/G3 以多个规则对手混合训练；`bursty` 与 `randomized` 留作未见测试对手。冻结策略后的换对手测试衡量泛化，不代表在线适应。
- 每个策略与对手组合共享相同外生随机种子；策略引发的价格路径差异是市场内生反馈。策略必须满足相同母单、期限和单步动作集合。所有 A 策略共享可行性约束：若继续等待会导致在剩余时段最大下单量下也无法完成，则屏蔽过小动作。
- 结果不保证 Q-learning 胜出。若结果不稳定，应增加训练轮数、检查状态覆盖，或重新设计离散状态；不能把未收敛结果包装为有效结论。
- RiskReviewAgent 只触发模拟结果复核标记，不执行真实交易。该系统没有券商接口或真实下单功能。
- 本次未调用生成式模型服务，因此没有模型 API 阻塞；仿真和 Q-learning 使用可重现的本地随机种子。

## 产物

- `evaluation_summary.csv`：成本、完成率、奖励、动作分布和复核率。
- `paired_comparisons.csv`：同随机种子配对的策略差异与近似 95% 区间。
- `evaluation_raw.csv`：逐回合种子结果，可复核或重新统计。
- `training_diagnostics.csv`：训练奖励、初始状态 Q 值及状态访问情况。
- `sample_episode_trace.csv`：0.5% 手续费、高波动下 G3 对 bursty 对手的一回合逐步记录，含状态、Q 值、判断、动作、反馈和解释。
- `qtable_*.json`：每个成本档训练后的 Q 表。
- `run_manifest.json`：参数、种子和运行配置。
