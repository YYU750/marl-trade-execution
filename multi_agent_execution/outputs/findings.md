# 多智能体交易执行系统：实验结果与研究假设核验

运行时间（UTC）：2026-11-03 05:54:50
主实验环境：每方母单 100,000 股，执行窗口 30 分钟、每 30 秒一步（共 60 步）。
训练预算：每个手续费档、每种学习器 1200 回合；主评估：每个策略×对手×手续费×波动场景 30 个配对种子。

## 研究问题与对照逻辑

本研究不把固定 TWAP 称为‘非 Agent’。比较的是逐层增加的策略能力：G0 固定 TWAP → G1 反馈型动态规则 → G2 Q-learning → G3 加入对手历史行动的 Q-learning。
H1 比较 G1−G0，检验动态反馈相对固定计划的增量；H2 比较 G2−G1，检验学习型策略相对动态规则的增量；H3 比较 G3−G2，并结合关闭 B 对价格影响的消融，检验对手信息是否带来增量。双边同时学习暂列扩展实验，不作为本轮主要结论。

## 成本口径与公平性

总实施缺口按初始中间价为基准，分为成交部分的毛执行缺口、显式手续费和未成交订单按期末中间价计量的机会成本。训练奖励还包含库存风险项及未完成惩罚，因此奖励和实际成本不可互换。报告同时给出完成率和未成交股数，防止策略通过少成交伪装低成本。
所有策略共享母单、期限、离散动作集合和可行性约束。配对运行共享外生市场冲击及对手随机流；Agent 行为改变后产生的价格路径差异是市场内生反馈。置信区间是配对差值的正态近似 95% 区间。

## 本次运行的总体观察

下表把不同费用、波动场景和对手下的配对差值合并作描述性汇总；推断时仍应查看后面的分层结果。区间为近似值，未调整多重比较。

| 假设对照 | 策略−基线成本差 bp | 近似 95% 区间 | 配对数 |
|---|---:|---:|---:|
| H1：G1 − G0 | 0.082 | [-0.021, 0.184] | 900 |
| H2：G2 − G1 | 0.911 | [0.534, 1.289] | 900 |
| H3：G3 − G2 | -0.129 | [-0.231, -0.027] | 900 |

本轮完成率范围为 1.000–1.000，主实验未成交股数为 0。对手冲击开启时 G3−G2 为 -0.161 bp [-0.251, -0.070]（n=450）；关闭时为 0.024 bp [-0.067, 0.116]（n=450）；差上差（关闭−开启）为 0.185 bp [0.144, 0.226]（n=450）。这些结果只说明当前模拟设定下的表现差异。
TWAP 反向检验中理论与实测 TWAP 成本为 0.175 / 0.175 bp，Q-learning 为 0.335 bp；Q-learning 没有系统性击败均匀执行基准，符合该控制设定的预期。

## 主实验：各手续费档的汇总

以下结果按策略、手续费和波动场景汇总，并对五类固定规则对手取平均。逐对手统计见 evaluation_summary.csv。

| 手续费 | 场景 | A 策略 | 总缺口 bp | 毛执行缺口 bp | 手续费 bp | 机会成本 bp | 完成率 | 未成交股数 |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 0.1% | normal | G0_TWAP | 15.22 | 5.21 | 10.00 | 0.00 | 1.000 | 0.0 |
| 0.1% | normal | G1_dynamic_rule | 15.37 | 5.37 | 10.00 | 0.00 | 1.000 | 0.0 |
| 0.1% | normal | G2_Q_learning | 15.39 | 5.39 | 10.00 | 0.00 | 1.000 | 0.0 |
| 0.1% | normal | G3_opponent_aware_Q | 15.41 | 5.41 | 10.00 | 0.00 | 1.000 | 0.0 |
| 0.1% | high_volatility | G0_TWAP | 12.20 | 2.20 | 10.00 | 0.00 | 1.000 | 0.0 |
| 0.1% | high_volatility | G1_dynamic_rule | 12.98 | 2.98 | 10.00 | 0.00 | 1.000 | 0.0 |
| 0.1% | high_volatility | G2_Q_learning | 11.15 | 1.15 | 10.00 | 0.00 | 1.000 | 0.0 |
| 0.1% | high_volatility | G3_opponent_aware_Q | 11.37 | 1.37 | 10.00 | 0.00 | 1.000 | 0.0 |
| 0.3% | normal | G0_TWAP | 40.33 | 10.31 | 30.02 | 0.00 | 1.000 | 0.0 |
| 0.3% | normal | G1_dynamic_rule | 40.37 | 10.35 | 30.02 | 0.00 | 1.000 | 0.0 |
| 0.3% | normal | G2_Q_learning | 42.49 | 12.46 | 30.03 | 0.00 | 1.000 | 0.0 |
| 0.3% | normal | G3_opponent_aware_Q | 42.17 | 12.15 | 30.03 | 0.00 | 1.000 | 0.0 |
| 0.3% | high_volatility | G0_TWAP | 42.41 | 12.38 | 30.03 | 0.00 | 1.000 | 0.0 |
| 0.3% | high_volatility | G1_dynamic_rule | 42.42 | 12.39 | 30.03 | 0.00 | 1.000 | 0.0 |
| 0.3% | high_volatility | G2_Q_learning | 45.24 | 15.20 | 30.04 | 0.00 | 1.000 | 0.0 |
| 0.3% | high_volatility | G3_opponent_aware_Q | 44.86 | 14.83 | 30.04 | 0.00 | 1.000 | 0.0 |
| 0.5% | normal | G0_TWAP | 58.21 | 8.18 | 50.03 | 0.00 | 1.000 | 0.0 |
| 0.5% | normal | G1_dynamic_rule | 58.01 | 7.98 | 50.03 | 0.00 | 1.000 | 0.0 |
| 0.5% | normal | G2_Q_learning | 59.33 | 9.30 | 50.03 | 0.00 | 1.000 | 0.0 |
| 0.5% | normal | G3_opponent_aware_Q | 59.15 | 9.11 | 50.03 | 0.00 | 1.000 | 0.0 |
| 0.5% | high_volatility | G0_TWAP | 58.16 | 8.13 | 50.03 | 0.00 | 1.000 | 0.0 |
| 0.5% | high_volatility | G1_dynamic_rule | 57.85 | 7.82 | 50.03 | 0.00 | 1.000 | 0.0 |
| 0.5% | high_volatility | G2_Q_learning | 58.88 | 8.84 | 50.03 | 0.00 | 1.000 | 0.0 |
| 0.5% | high_volatility | G3_opponent_aware_Q | 58.74 | 8.71 | 50.03 | 0.00 | 1.000 | 0.0 |

## 主要假设的配对检验

成本差定义为策略成本减基线成本；负值有利于被比较策略。结果须结合区间、完成率和多重场景一致性解释，不能只挑选有利场景。

| 手续费 | 场景 | B 对手 | 检验 | 成本差 bp | 配对近似 95% 区间 | 完成率差 |
|---:|---|---|---|---:|---:|---:|
| 0.1% | normal | twap | H1 dynamic feedback vs fixed TWAP | 0.16 | [-0.25, 0.57] | 0.000 |
| 0.1% | normal | twap | H2 Q-learning vs dynamic rule | 0.08 | [-1.45, 1.62] | 0.000 |
| 0.1% | normal | twap | H3 opponent information vs none | -0.02 | [-0.16, 0.13] | 0.000 |
| 0.1% | normal | frontloaded | H1 dynamic feedback vs fixed TWAP | 0.18 | [-0.20, 0.57] | 0.000 |
| 0.1% | normal | frontloaded | H2 Q-learning vs dynamic rule | -0.13 | [-1.62, 1.35] | 0.000 |
| 0.1% | normal | frontloaded | H3 opponent information vs none | 0.03 | [-0.11, 0.18] | 0.000 |
| 0.1% | normal | backloaded | H1 dynamic feedback vs fixed TWAP | 0.15 | [-0.29, 0.58] | 0.000 |
| 0.1% | normal | backloaded | H2 Q-learning vs dynamic rule | -0.01 | [-1.56, 1.54] | 0.000 |
| 0.1% | normal | backloaded | H3 opponent information vs none | -0.01 | [-0.12, 0.11] | 0.000 |
| 0.1% | normal | bursty | H1 dynamic feedback vs fixed TWAP | 0.16 | [-0.25, 0.57] | 0.000 |
| 0.1% | normal | bursty | H2 Q-learning vs dynamic rule | 0.09 | [-1.45, 1.62] | 0.000 |
| 0.1% | normal | bursty | H3 opponent information vs none | 0.03 | [-0.70, 0.75] | 0.000 |
| 0.1% | normal | randomized | H1 dynamic feedback vs fixed TWAP | 0.15 | [-0.26, 0.55] | 0.000 |
| 0.1% | normal | randomized | H2 Q-learning vs dynamic rule | 0.08 | [-1.46, 1.61] | 0.000 |
| 0.1% | normal | randomized | H3 opponent information vs none | 0.04 | [-0.16, 0.23] | 0.000 |
| 0.1% | high_volatility | twap | H1 dynamic feedback vs fixed TWAP | 0.78 | [-0.26, 1.82] | 0.000 |
| 0.1% | high_volatility | twap | H2 Q-learning vs dynamic rule | -1.76 | [-5.17, 1.66] | 0.000 |
| 0.1% | high_volatility | twap | H3 opponent information vs none | 0.03 | [-0.20, 0.25] | 0.000 |
| 0.1% | high_volatility | frontloaded | H1 dynamic feedback vs fixed TWAP | 0.76 | [-0.26, 1.77] | 0.000 |
| 0.1% | high_volatility | frontloaded | H2 Q-learning vs dynamic rule | -1.92 | [-5.34, 1.49] | 0.000 |
| 0.1% | high_volatility | frontloaded | H3 opponent information vs none | 0.09 | [-0.20, 0.38] | 0.000 |
| 0.1% | high_volatility | backloaded | H1 dynamic feedback vs fixed TWAP | 0.81 | [-0.25, 1.88] | 0.000 |
| 0.1% | high_volatility | backloaded | H2 Q-learning vs dynamic rule | -1.92 | [-5.38, 1.55] | 0.000 |
| 0.1% | high_volatility | backloaded | H3 opponent information vs none | 0.10 | [-0.14, 0.33] | 0.000 |
| 0.1% | high_volatility | bursty | H1 dynamic feedback vs fixed TWAP | 0.76 | [-0.28, 1.80] | 0.000 |
| 0.1% | high_volatility | bursty | H2 Q-learning vs dynamic rule | -1.74 | [-5.15, 1.68] | 0.000 |
| 0.1% | high_volatility | bursty | H3 opponent information vs none | 0.75 | [-0.72, 2.23] | 0.000 |
| 0.1% | high_volatility | randomized | H1 dynamic feedback vs fixed TWAP | 0.81 | [-0.22, 1.85] | 0.000 |
| 0.1% | high_volatility | randomized | H2 Q-learning vs dynamic rule | -1.83 | [-5.27, 1.60] | 0.000 |
| 0.1% | high_volatility | randomized | H3 opponent information vs none | 0.15 | [-0.20, 0.49] | 0.000 |
| 0.3% | normal | twap | H1 dynamic feedback vs fixed TWAP | 0.02 | [-0.21, 0.26] | 0.000 |
| 0.3% | normal | twap | H2 Q-learning vs dynamic rule | 2.19 | [1.22, 3.17] | 0.000 |
| 0.3% | normal | twap | H3 opponent information vs none | -0.05 | [-0.15, 0.05] | 0.000 |
| 0.3% | normal | frontloaded | H1 dynamic feedback vs fixed TWAP | 0.09 | [-0.12, 0.31] | 0.000 |
| 0.3% | normal | frontloaded | H2 Q-learning vs dynamic rule | 1.92 | [0.98, 2.87] | 0.000 |
| 0.3% | normal | frontloaded | H3 opponent information vs none | -0.06 | [-0.21, 0.09] | 0.000 |
| 0.3% | normal | backloaded | H1 dynamic feedback vs fixed TWAP | 0.00 | [-0.26, 0.26] | 0.000 |
| 0.3% | normal | backloaded | H2 Q-learning vs dynamic rule | 2.10 | [1.11, 3.08] | 0.000 |
| 0.3% | normal | backloaded | H3 opponent information vs none | -0.03 | [-0.12, 0.06] | 0.000 |
| 0.3% | normal | bursty | H1 dynamic feedback vs fixed TWAP | 0.03 | [-0.21, 0.27] | 0.000 |
| 0.3% | normal | bursty | H2 Q-learning vs dynamic rule | 2.19 | [1.21, 3.17] | 0.000 |
| 0.3% | normal | bursty | H3 opponent information vs none | -1.21 | [-1.83, -0.58] | 0.000 |
| 0.3% | normal | randomized | H1 dynamic feedback vs fixed TWAP | 0.04 | [-0.19, 0.26] | 0.000 |
| 0.3% | normal | randomized | H2 Q-learning vs dynamic rule | 2.18 | [1.21, 3.15] | 0.000 |
| 0.3% | normal | randomized | H3 opponent information vs none | -0.22 | [-0.40, -0.03] | 0.000 |
| 0.3% | high_volatility | twap | H1 dynamic feedback vs fixed TWAP | 0.01 | [-0.53, 0.56] | 0.000 |
| 0.3% | high_volatility | twap | H2 Q-learning vs dynamic rule | 2.88 | [0.69, 5.06] | 0.000 |
| 0.3% | high_volatility | twap | H3 opponent information vs none | 0.01 | [-0.22, 0.24] | 0.000 |
| 0.3% | high_volatility | frontloaded | H1 dynamic feedback vs fixed TWAP | 0.09 | [-0.44, 0.61] | 0.000 |
| 0.3% | high_volatility | frontloaded | H2 Q-learning vs dynamic rule | 2.62 | [0.45, 4.78] | 0.000 |
| 0.3% | high_volatility | frontloaded | H3 opponent information vs none | -0.13 | [-0.40, 0.13] | 0.000 |
| 0.3% | high_volatility | backloaded | H1 dynamic feedback vs fixed TWAP | -0.07 | [-0.64, 0.51] | 0.000 |
| 0.3% | high_volatility | backloaded | H2 Q-learning vs dynamic rule | 2.84 | [0.62, 5.06] | 0.000 |
| 0.3% | high_volatility | backloaded | H3 opponent information vs none | 0.01 | [-0.22, 0.23] | 0.000 |
| 0.3% | high_volatility | bursty | H1 dynamic feedback vs fixed TWAP | 0.01 | [-0.54, 0.56] | 0.000 |
| 0.3% | high_volatility | bursty | H2 Q-learning vs dynamic rule | 2.89 | [0.70, 5.07] | 0.000 |
| 0.3% | high_volatility | bursty | H3 opponent information vs none | -1.61 | [-2.91, -0.31] | 0.000 |
| 0.3% | high_volatility | randomized | H1 dynamic feedback vs fixed TWAP | 0.03 | [-0.51, 0.57] | 0.000 |
| 0.3% | high_volatility | randomized | H2 Q-learning vs dynamic rule | 2.87 | [0.69, 5.04] | 0.000 |
| 0.3% | high_volatility | randomized | H3 opponent information vs none | -0.17 | [-0.52, 0.17] | 0.000 |
| 0.5% | normal | twap | H1 dynamic feedback vs fixed TWAP | -0.20 | [-0.43, 0.03] | 0.000 |
| 0.5% | normal | twap | H2 Q-learning vs dynamic rule | 1.38 | [0.45, 2.31] | 0.000 |
| 0.5% | normal | twap | H3 opponent information vs none | -0.03 | [-0.11, 0.05] | 0.000 |
| 0.5% | normal | frontloaded | H1 dynamic feedback vs fixed TWAP | -0.16 | [-0.40, 0.07] | 0.000 |
| 0.5% | normal | frontloaded | H2 Q-learning vs dynamic rule | 1.15 | [0.22, 2.07] | 0.000 |
| 0.5% | normal | frontloaded | H3 opponent information vs none | -0.07 | [-0.25, 0.11] | 0.000 |
| 0.5% | normal | backloaded | H1 dynamic feedback vs fixed TWAP | -0.23 | [-0.47, 0.02] | 0.000 |
| 0.5% | normal | backloaded | H2 Q-learning vs dynamic rule | 1.29 | [0.36, 2.22] | 0.000 |
| 0.5% | normal | backloaded | H3 opponent information vs none | -0.02 | [-0.08, 0.04] | 0.000 |
| 0.5% | normal | bursty | H1 dynamic feedback vs fixed TWAP | -0.20 | [-0.43, 0.03] | 0.000 |
| 0.5% | normal | bursty | H2 Q-learning vs dynamic rule | 1.39 | [0.46, 2.32] | 0.000 |
| 0.5% | normal | bursty | H3 opponent information vs none | -0.65 | [-1.38, 0.07] | 0.000 |
| 0.5% | normal | randomized | H1 dynamic feedback vs fixed TWAP | -0.21 | [-0.44, 0.02] | 0.000 |
| 0.5% | normal | randomized | H2 Q-learning vs dynamic rule | 1.40 | [0.47, 2.33] | 0.000 |
| 0.5% | normal | randomized | H3 opponent information vs none | -0.15 | [-0.37, 0.06] | 0.000 |
| 0.5% | high_volatility | twap | H1 dynamic feedback vs fixed TWAP | -0.31 | [-0.76, 0.13] | 0.000 |
| 0.5% | high_volatility | twap | H2 Q-learning vs dynamic rule | 1.10 | [-0.90, 3.10] | 0.000 |
| 0.5% | high_volatility | twap | H3 opponent information vs none | -0.05 | [-0.22, 0.12] | 0.000 |
| 0.5% | high_volatility | frontloaded | H1 dynamic feedback vs fixed TWAP | -0.25 | [-0.69, 0.19] | 0.000 |
| 0.5% | high_volatility | frontloaded | H2 Q-learning vs dynamic rule | 0.83 | [-1.14, 2.81] | 0.000 |
| 0.5% | high_volatility | frontloaded | H3 opponent information vs none | -0.06 | [-0.44, 0.32] | 0.000 |
| 0.5% | high_volatility | backloaded | H1 dynamic feedback vs fixed TWAP | -0.36 | [-0.81, 0.09] | 0.000 |
| 0.5% | high_volatility | backloaded | H2 Q-learning vs dynamic rule | 1.02 | [-1.03, 3.06] | 0.000 |
| 0.5% | high_volatility | backloaded | H3 opponent information vs none | -0.06 | [-0.25, 0.12] | 0.000 |
| 0.5% | high_volatility | bursty | H1 dynamic feedback vs fixed TWAP | -0.31 | [-0.75, 0.14] | 0.000 |
| 0.5% | high_volatility | bursty | H2 Q-learning vs dynamic rule | 1.11 | [-0.90, 3.11] | 0.000 |
| 0.5% | high_volatility | bursty | H3 opponent information vs none | -0.46 | [-2.04, 1.12] | 0.000 |
| 0.5% | high_volatility | randomized | H1 dynamic feedback vs fixed TWAP | -0.30 | [-0.76, 0.15] | 0.000 |
| 0.5% | high_volatility | randomized | H2 Q-learning vs dynamic rule | 1.07 | [-0.92, 3.06] | 0.000 |
| 0.5% | high_volatility | randomized | H3 opponent information vs none | -0.04 | [-0.53, 0.45] | 0.000 |

## 对手影响消融：G3 相对 G2

差值为 G3 成本减 G2 成本；差上差为 (关闭对手影响时的 G3−G2)−(开启时的 G3−G2)。若结果未支持预期，需如实报告；关闭 B 冲击会同时改变环境中的竞争反馈。

| 手续费 | B 对手 | 条件 | G3−G2 bp | 近似 95% 区间 |
|---:|---|---|---:|---:|
| 0.1% | twap | opponent_impact_on | -0.02 | [-0.16, 0.13] |
| 0.1% | twap | opponent_impact_off | 0.00 | [-0.04, 0.05] |
| 0.1% | twap | difference_in_differences | 0.02 | [-0.14, 0.18] |
| 0.1% | frontloaded | opponent_impact_on | 0.03 | [-0.11, 0.18] |
| 0.1% | frontloaded | opponent_impact_off | 0.07 | [-0.04, 0.19] |
| 0.1% | frontloaded | difference_in_differences | 0.04 | [-0.13, 0.20] |
| 0.1% | backloaded | opponent_impact_on | -0.01 | [-0.12, 0.11] |
| 0.1% | backloaded | opponent_impact_off | 0.00 | [-0.04, 0.05] |
| 0.1% | backloaded | difference_in_differences | 0.01 | [-0.12, 0.14] |
| 0.1% | bursty | opponent_impact_on | 0.03 | [-0.70, 0.75] |
| 0.1% | bursty | opponent_impact_off | 0.72 | [-0.05, 1.48] |
| 0.1% | bursty | difference_in_differences | 0.69 | [0.58, 0.80] |
| 0.1% | randomized | opponent_impact_on | 0.04 | [-0.16, 0.23] |
| 0.1% | randomized | opponent_impact_off | 0.15 | [-0.02, 0.32] |
| 0.1% | randomized | difference_in_differences | 0.11 | [-0.01, 0.23] |
| 0.3% | twap | opponent_impact_on | -0.05 | [-0.15, 0.05] |
| 0.3% | twap | opponent_impact_off | -0.03 | [-0.08, 0.02] |
| 0.3% | twap | difference_in_differences | 0.02 | [-0.10, 0.14] |
| 0.3% | frontloaded | opponent_impact_on | -0.06 | [-0.21, 0.09] |
| 0.3% | frontloaded | opponent_impact_off | -0.08 | [-0.24, 0.08] |
| 0.3% | frontloaded | difference_in_differences | -0.02 | [-0.20, 0.15] |
| 0.3% | backloaded | opponent_impact_on | -0.03 | [-0.12, 0.06] |
| 0.3% | backloaded | opponent_impact_off | -0.03 | [-0.08, 0.02] |
| 0.3% | backloaded | difference_in_differences | -0.00 | [-0.12, 0.12] |
| 0.3% | bursty | opponent_impact_on | -1.21 | [-1.83, -0.58] |
| 0.3% | bursty | opponent_impact_off | -0.46 | [-1.13, 0.21] |
| 0.3% | bursty | difference_in_differences | 0.75 | [0.63, 0.86] |
| 0.3% | randomized | opponent_impact_on | -0.22 | [-0.40, -0.03] |
| 0.3% | randomized | opponent_impact_off | -0.12 | [-0.35, 0.10] |
| 0.3% | randomized | difference_in_differences | 0.09 | [-0.06, 0.24] |
| 0.5% | twap | opponent_impact_on | -0.03 | [-0.11, 0.05] |
| 0.5% | twap | opponent_impact_off | 0.00 | [-0.07, 0.08] |
| 0.5% | twap | difference_in_differences | 0.03 | [-0.05, 0.11] |
| 0.5% | frontloaded | opponent_impact_on | -0.07 | [-0.25, 0.11] |
| 0.5% | frontloaded | opponent_impact_off | 0.02 | [-0.19, 0.23] |
| 0.5% | frontloaded | difference_in_differences | 0.09 | [-0.02, 0.19] |
| 0.5% | backloaded | opponent_impact_on | -0.02 | [-0.08, 0.04] |
| 0.5% | backloaded | opponent_impact_off | 0.00 | [-0.07, 0.08] |
| 0.5% | backloaded | difference_in_differences | 0.02 | [-0.04, 0.09] |
| 0.5% | bursty | opponent_impact_on | -0.65 | [-1.38, 0.07] |
| 0.5% | bursty | opponent_impact_off | 0.11 | [-0.65, 0.86] |
| 0.5% | bursty | difference_in_differences | 0.76 | [0.68, 0.85] |
| 0.5% | randomized | opponent_impact_on | -0.15 | [-0.37, 0.06] |
| 0.5% | randomized | opponent_impact_off | 0.02 | [-0.22, 0.26] |
| 0.5% | randomized | difference_in_differences | 0.17 | [0.07, 0.27] |

## 市场冲击压力测试

该组将自身和对手交易冲击系数同时提高到基准的 2 倍，使用固定基准环境训练出的策略进行迁移测试。

| A 策略 | 平均总缺口 bp | 完成率 | 平均毛执行缺口 bp | 平均手续费 bp |
|---|---:|---:|---:|---:|
| G0_TWAP | 44.18 | 1.000 | 14.14 | 30.04 |
| G1_dynamic_rule | 44.41 | 1.000 | 14.37 | 30.04 |
| G2_Q_learning | 46.78 | 1.000 | 16.74 | 30.04 |
| G3_opponent_aware_Q | 46.44 | 1.000 | 16.39 | 30.04 |

## 候选策略集内的后悔值

后悔值按同手续费、场景、固定对手和随机种子下 G0–G3 的最低实测成本计算，只代表相对本次候选集合的差距；它不是全局最优值，也不意味着达到纳什均衡。

| 策略 | 平均候选集后悔值 bp | 成为候选最佳策略的比例 | 平均完成率 |
|---|---:|---:|---:|
| G0_TWAP | 1.83 | 0.343 | 1.000 |
| G1_dynamic_rule | 1.91 | 0.246 | 1.000 |
| G2_Q_learning | 2.82 | 0.254 | 1.000 |
| G3_opponent_aware_Q | 2.69 | 0.157 | 1.000 |

## TWAP 最优性反向检验

控制环境设为零价差、零波动、零永久冲击、零手续费和零对手冲击，仅保留凸性临时冲击。均匀 TWAP 理论成本为 0.1750 bp；实测 TWAP 均值 0.1750 bp，Q-learning 均值 0.3354 bp，Q−TWAP 配对差 0.1604 bp。若 Q-learning 系统性优于理论基准，应先检查环境实现、动作限制和成本口径。

## 训练诊断

| 手续费 | 学习器 | 训练回合 | 最近 100 回合奖励 | 前 100 回合奖励 | 初始状态 max Q | 访问状态数 |
|---:|---|---:|---:|---:|---:|---:|
| 0.1% | G2_Q_learning | 1200 | -21.50 | -20.80 | -0.06 | 1058 |
| 0.1% | G3_opponent_aware_Q | 1200 | -21.46 | -20.76 | -0.05 | 1544 |
| 0.3% | G2_Q_learning | 1200 | -38.83 | -40.43 | -0.06 | 1102 |
| 0.3% | G3_opponent_aware_Q | 1200 | -38.79 | -40.40 | -0.04 | 1515 |
| 0.5% | G2_Q_learning | 1200 | -59.33 | -59.22 | -0.05 | 1127 |
| 0.5% | G3_opponent_aware_Q | 1200 | -59.32 | -59.20 | -0.04 | 1564 |

## 结果边界

- 本项目是可复现的教学模拟器，并非历史行情回测：单一资产、单一时间步长、简化冲击方程和规则化对手。没有真实订单簿、排队撮合、隐藏流动性、市场制度、外部数据或实盘下单。
- 当前核心架构是一个学习型执行机构 A 与一个固定规则机构 B 交互。G3 是对手感知策略，不等于 B 也在学习；双方同步 Q-learning 作为后续扩展。
- G2/G3 在 TWAP、前置、后置规则对手中训练；bursty 与 randomized 只用于冻结策略的未见对手测试，测的是泛化而非在线适应。
- 手续费作为显式成交成本计入。若所有订单必须完成且费率为常数，费率上升本身不会改变最优交易节奏；动态节奏主要由价格反馈和冲击环境驱动。
- 结果不预设 Q-learning 或对手感知一定胜出。训练回报、Q 值和测试成本必须分别解释；没有通过收敛性检查的结果只能视为探索性。
- RiskReviewAgent 只标记需要人工复核的模拟结果，不下真实订单。运行使用本地 Python 和固定随机流，不调用生成式模型 API。

## 主要产物

- evaluation_summary.csv、evaluation_raw.csv、paired_comparisons.csv：主实验汇总、逐种子结果和 H1–H3 配对比较。
- opponent_impact_ablation_*.csv：对手冲击开关消融及 G3−G2 差上差。
- market_impact_stress_*.csv：冲击系数翻倍压力测试与迁移评估。
- candidate_set_regret*.csv：相对 G0–G3 候选集合的后悔值。
- uniform_optimality_control*.csv：TWAP 最优性反向检验。
- training_diagnostics.csv、qtable_*.json：训练诊断与可复用 Q 表。
- sample_episode_trace.csv：30 秒一个决策步的逐步输入、判断、成交、反馈和业务解释。
- run_manifest.json：完整参数、随机种子、数据规模与运行时间。
