# 选定 Double Q 的独立留出验证

本次只验证固定 5 bp 门槛的规则引导 Double Q，不在新测试集上重新挑门槛，也不重跑其余 Q 变体。
测试主种子为 `20261112`；每类 B 对手、每个场景使用 50 个配对种子，费用为 30 bp。
B 随机策略保留 0.5/1.5 TWAP 随机节奏，但加入按剩余步数计算的最低可行成交量，避免它把未完成订单带入终局。
完单约束控制对比 1000 组随机流：修正前 438 局未完成（平均剩余 2555.0 股），修正后 0 局未完成。

## 成本和完成率

成本为总实施缺口，越低越好。每个 Q 训练种子只使用一次；区间反映 250 个对手×随机种子配对格的评估波动，不包含训练种子不确定性。

| 场景 | 策略 | 平均成本 (bp) | A 完成率 | B 完成率 |
|---|---|---:|---:|---:|
| normal | G0_TWAP | 38.337 ± 8.024 | 100.000% | 100.000% |
| normal | G1_dynamic_rule | 38.386 ± 8.250 | 100.000% | 100.000% |
| normal | rule_guided_double_Q_m5 | 38.400 ± 8.259 | 100.000% | 100.000% |
| high_volatility | G0_TWAP | 38.188 ± 16.694 | 100.000% | 100.000% |
| high_volatility | G1_dynamic_rule | 38.229 ± 16.497 | 100.000% | 100.000% |
| high_volatility | rule_guided_double_Q_m5 | 38.217 ± 16.497 | 100.000% | 100.000% |

## 配对成本差（Double Q 减基线）

负数有利于 Double Q；区间为近似 95% 配对区间。

| 场景 | B 对手 | 基线 | 配对格 | 平均差 (bp) | 近似 95% 区间 |
|---|---|---|---:|---:|---:|
| normal | twap | G1_dynamic_rule | 50 | 0.015 | [-0.014, 0.044] |
| normal | twap | G0_TWAP | 50 | 0.075 | [-0.193, 0.342] |
| normal | frontloaded | G1_dynamic_rule | 50 | 0.001 | [-0.007, 0.010] |
| normal | frontloaded | G0_TWAP | 50 | 0.050 | [-0.267, 0.367] |
| normal | backloaded | G1_dynamic_rule | 50 | 0.044 | [-0.003, 0.091] |
| normal | backloaded | G0_TWAP | 50 | 0.006 | [-0.241, 0.253] |
| normal | bursty | G1_dynamic_rule | 50 | 0.000 | [0.000, 0.000] |
| normal | bursty | G0_TWAP | 50 | 0.034 | [-0.213, 0.282] |
| normal | randomized | G1_dynamic_rule | 50 | 0.008 | [-0.011, 0.028] |
| normal | randomized | G0_TWAP | 50 | 0.149 | [-0.102, 0.400] |
| normal | ALL_EQUAL_WEIGHTED | G1_dynamic_rule | 250 | 0.014 | [0.002, 0.026] |
| normal | ALL_EQUAL_WEIGHTED | G0_TWAP | 250 | 0.063 | [-0.056, 0.182] |
| high_volatility | twap | G1_dynamic_rule | 50 | 0.000 | [0.000, 0.000] |
| high_volatility | twap | G0_TWAP | 50 | 0.574 | [-0.284, 1.432] |
| high_volatility | frontloaded | G1_dynamic_rule | 50 | -0.013 | [-0.091, 0.064] |
| high_volatility | frontloaded | G0_TWAP | 50 | 0.169 | [-0.689, 1.026] |
| high_volatility | backloaded | G1_dynamic_rule | 50 | 0.045 | [-0.074, 0.164] |
| high_volatility | backloaded | G0_TWAP | 50 | 0.306 | [-0.346, 0.958] |
| high_volatility | bursty | G1_dynamic_rule | 50 | 0.000 | [0.000, 0.000] |
| high_volatility | bursty | G0_TWAP | 50 | -0.508 | [-1.121, 0.104] |
| high_volatility | randomized | G1_dynamic_rule | 50 | -0.093 | [-0.180, -0.007] |
| high_volatility | randomized | G0_TWAP | 50 | -0.395 | [-0.929, 0.139] |
| high_volatility | ALL_EQUAL_WEIGHTED | G1_dynamic_rule | 250 | -0.012 | [-0.046, 0.021] |
| high_volatility | ALL_EQUAL_WEIGHTED | G0_TWAP | 250 | 0.029 | [-0.292, 0.350] |

## 动作一致性

一致率逐时点比较 Double Q 与动态规则在相同对手、场景、种子下的动作；策略改变市场路径，因此后续状态可以不同。

| 场景 | B 对手 | Q 与动态规则动作一致率 |
|---|---|---:|
| high_volatility | backloaded | 94.93% |
| high_volatility | bursty | 100.00% |
| high_volatility | frontloaded | 95.17% |
| high_volatility | randomized | 96.23% |
| high_volatility | twap | 100.00% |
| normal | backloaded | 94.57% |
| normal | bursty | 100.00% |
| normal | frontloaded | 98.80% |
| normal | randomized | 96.20% |
| normal | twap | 94.63% |

## γ 与冻结策略检查

训练配置 γ = 0.98。非终止样例目标：`−2 + γ × (−10) = -11.800`；终止样例不 bootstrap：`-2.000`。Double Q 更新使用 `reward + γ × evaluator_Q(next_state, argmax(chosen_Q(next_state)))`。
评估前后策略表与访问计数字典的 SHA-256 一致：**True**。冻结后若发生学习更新会直接报错。

## 动作量分解

各行动作档位的次数和成交股数见 `action_summary.csv`；每条逐回合动作序列保存在 `followup_raw.csv`。

## 范围说明

这是一项小范围独立验证：仅训练一个 Double Q 种子；TWAP 和动态规则不训练。测试种子与此前主比较、验证集和长训集分开。由于只用一个 Q 训练种子，成本区间不能表示训练随机性。
历史主实验中的随机 B 结果产生于本次完单修正之前；本报告用修正后的随机 B 规则重新评估选定策略，不回写或伪装成旧实验的复算结果。
