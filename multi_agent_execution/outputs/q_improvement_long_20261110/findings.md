# 规则策略与 Q-learning 配对比较

- 运行参数：手续费 30 bp；成本对齐候选训练 5 个种子 × 1200 回合，阈值对齐双 Q 每个种子先用 5000 条规则轨迹初始化，再训练 30000 回合；每个固定 B 对手/场景 50 个配对评估种子。
- 固定 TWAP、动态规则、历史 G2/G3、当前双边自博弈 A 策略及改进候选 Q 策略均调用同一个 run_standard_benchmark.run_episode 市场模拟器。
- 每个 B 对手、波动场景和评估种子对所有 A 策略完全相同；策略随机数、对手随机数和市场冲击使用隔离随机流。费用、母单、期限、价差、冲击和成交假设相同。
- 改进候选使用紧凑的时间/执行进度状态编码、全部测试对手训练、成本对齐的 TD 奖励，并修复未尝试动作的零初始化 Q 值虚高问题。实际市场清算与评价口径没有改变。
- 阈值对齐双 Q 候选使用 5 步时间阶段、规则阈值对齐的状态边界、双 Q 表降低最大化偏差，并用训练集动态规则轨迹的 Monte Carlo 回报初始化；训练覆盖两种波动场景和全部固定对手。
- 成本差定义为学习策略减规则策略；负值有利于学习策略。区间是按配对评估种子计算的近似 95% 区间；训练种子先在同一评估种子内取均值。

## 各策略汇总

下表对五类固定 B 对手等权汇总，详细分层结果见 matched_comparison_summary.csv。

| A 策略 | 场景 | 平均成本 (bp) | 完成率 | 局数 |
|---|---|---:|---:|---:|
| G0_TWAP | high_volatility | 37.977 | 1.000 | 250 |
| G0_TWAP | normal | 38.481 | 1.000 | 250 |
| G1_dynamic_rule | high_volatility | 37.630 | 1.000 | 250 |
| G1_dynamic_rule | normal | 38.475 | 1.000 | 250 |
| G2_Q_learning_existing | high_volatility | 39.597 | 1.000 | 250 |
| G2_Q_learning_existing | normal | 40.187 | 1.000 | 250 |
| G3_opponent_aware_Q_existing | high_volatility | 39.510 | 1.000 | 250 |
| G3_opponent_aware_Q_existing | normal | 40.031 | 1.000 | 250 |
| cost_aligned_schedule_Q_run1 | high_volatility | 38.769 | 1.000 | 250 |
| cost_aligned_schedule_Q_run1 | normal | 39.531 | 1.000 | 250 |
| cost_aligned_schedule_Q_run2 | high_volatility | 38.779 | 1.000 | 250 |
| cost_aligned_schedule_Q_run2 | normal | 39.247 | 1.000 | 250 |
| cost_aligned_schedule_Q_run3 | high_volatility | 38.823 | 1.000 | 250 |
| cost_aligned_schedule_Q_run3 | normal | 39.280 | 1.000 | 250 |
| cost_aligned_schedule_Q_run4 | high_volatility | 38.261 | 1.000 | 250 |
| cost_aligned_schedule_Q_run4 | normal | 39.148 | 1.000 | 250 |
| cost_aligned_schedule_Q_run5 | high_volatility | 38.782 | 1.000 | 250 |
| cost_aligned_schedule_Q_run5 | normal | 39.415 | 1.000 | 250 |
| rule_guided_double_Q_m10_run1 | high_volatility | 37.631 | 1.000 | 250 |
| rule_guided_double_Q_m10_run1 | normal | 38.476 | 1.000 | 250 |
| rule_guided_double_Q_m10_run2 | high_volatility | 37.633 | 1.000 | 250 |
| rule_guided_double_Q_m10_run2 | normal | 38.475 | 1.000 | 250 |
| rule_guided_double_Q_m10_run3 | high_volatility | 37.633 | 1.000 | 250 |
| rule_guided_double_Q_m10_run3 | normal | 38.475 | 1.000 | 250 |
| rule_guided_double_Q_m10_run4 | high_volatility | 37.626 | 1.000 | 250 |
| rule_guided_double_Q_m10_run4 | normal | 38.475 | 1.000 | 250 |
| rule_guided_double_Q_m10_run5 | high_volatility | 37.627 | 1.000 | 250 |
| rule_guided_double_Q_m10_run5 | normal | 38.475 | 1.000 | 250 |
| rule_guided_double_Q_m1_run1 | high_volatility | 37.717 | 1.000 | 250 |
| rule_guided_double_Q_m1_run1 | normal | 38.501 | 1.000 | 250 |
| rule_guided_double_Q_m1_run2 | high_volatility | 37.679 | 1.000 | 250 |
| rule_guided_double_Q_m1_run2 | normal | 38.557 | 1.000 | 250 |
| rule_guided_double_Q_m1_run3 | high_volatility | 37.819 | 1.000 | 250 |
| rule_guided_double_Q_m1_run3 | normal | 38.453 | 1.000 | 250 |
| rule_guided_double_Q_m1_run4 | high_volatility | 37.724 | 1.000 | 250 |
| rule_guided_double_Q_m1_run4 | normal | 38.471 | 1.000 | 250 |
| rule_guided_double_Q_m1_run5 | high_volatility | 37.655 | 1.000 | 250 |
| rule_guided_double_Q_m1_run5 | normal | 38.506 | 1.000 | 250 |
| rule_guided_double_Q_m2_run1 | high_volatility | 37.649 | 1.000 | 250 |
| rule_guided_double_Q_m2_run1 | normal | 38.527 | 1.000 | 250 |
| rule_guided_double_Q_m2_run2 | high_volatility | 37.622 | 1.000 | 250 |
| rule_guided_double_Q_m2_run2 | normal | 38.508 | 1.000 | 250 |
| rule_guided_double_Q_m2_run3 | high_volatility | 37.852 | 1.000 | 250 |
| rule_guided_double_Q_m2_run3 | normal | 38.444 | 1.000 | 250 |
| rule_guided_double_Q_m2_run4 | high_volatility | 37.713 | 1.000 | 250 |
| rule_guided_double_Q_m2_run4 | normal | 38.474 | 1.000 | 250 |
| rule_guided_double_Q_m2_run5 | high_volatility | 37.615 | 1.000 | 250 |
| rule_guided_double_Q_m2_run5 | normal | 38.477 | 1.000 | 250 |
| rule_guided_double_Q_m5_run1 | high_volatility | 37.649 | 1.000 | 250 |
| rule_guided_double_Q_m5_run1 | normal | 38.499 | 1.000 | 250 |
| rule_guided_double_Q_m5_run2 | high_volatility | 37.647 | 1.000 | 250 |
| rule_guided_double_Q_m5_run2 | normal | 38.499 | 1.000 | 250 |
| rule_guided_double_Q_m5_run3 | high_volatility | 37.619 | 1.000 | 250 |
| rule_guided_double_Q_m5_run3 | normal | 38.502 | 1.000 | 250 |
| rule_guided_double_Q_m5_run4 | high_volatility | 37.639 | 1.000 | 250 |
| rule_guided_double_Q_m5_run4 | normal | 38.497 | 1.000 | 250 |
| rule_guided_double_Q_m5_run5 | high_volatility | 37.643 | 1.000 | 250 |
| rule_guided_double_Q_m5_run5 | normal | 38.496 | 1.000 | 250 |
| selfplay_Q_A_run1 | high_volatility | 39.247 | 1.000 | 250 |
| selfplay_Q_A_run1 | normal | 39.609 | 1.000 | 250 |
| selfplay_Q_A_run2 | high_volatility | 38.844 | 1.000 | 250 |
| selfplay_Q_A_run2 | normal | 39.293 | 1.000 | 250 |
| selfplay_Q_A_run3 | high_volatility | 39.092 | 1.000 | 250 |
| selfplay_Q_A_run3 | normal | 39.582 | 1.000 | 250 |
| selfplay_Q_A_run4 | high_volatility | 39.257 | 1.000 | 250 |
| selfplay_Q_A_run4 | normal | 39.717 | 1.000 | 250 |
| selfplay_Q_A_run5 | high_volatility | 39.281 | 1.000 | 250 |
| selfplay_Q_A_run5 | normal | 39.831 | 1.000 | 250 |

## 配对成本差

| 学习策略 | 对照规则 | B 对手 | 场景 | 配对种子 | 成本差 (bp) | 近似 95% 区间 |
|---|---|---|---|---:|---:|---:|
| G2_Q_learning_existing | G0_TWAP | backloaded | high_volatility | 50 | 2.973 | [1.045, 4.902] |
| G2_Q_learning_existing | G1_dynamic_rule | backloaded | high_volatility | 50 | 2.900 | [0.912, 4.889] |
| G2_Q_learning_existing | G0_TWAP | backloaded | normal | 50 | 1.803 | [0.770, 2.836] |
| G2_Q_learning_existing | G1_dynamic_rule | backloaded | normal | 50 | 1.691 | [0.544, 2.839] |
| G2_Q_learning_existing | G0_TWAP | bursty | high_volatility | 50 | 0.329 | [-1.868, 2.525] |
| G2_Q_learning_existing | G1_dynamic_rule | bursty | high_volatility | 50 | 0.835 | [-1.576, 3.246] |
| G2_Q_learning_existing | G0_TWAP | bursty | normal | 50 | 0.720 | [-0.318, 1.758] |
| G2_Q_learning_existing | G1_dynamic_rule | bursty | normal | 50 | 0.729 | [-0.315, 1.774] |
| G2_Q_learning_existing | G0_TWAP | frontloaded | high_volatility | 50 | 1.075 | [-0.912, 3.062] |
| G2_Q_learning_existing | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.717 | [-0.677, 4.111] |
| G2_Q_learning_existing | G0_TWAP | frontloaded | normal | 50 | 1.585 | [0.610, 2.560] |
| G2_Q_learning_existing | G1_dynamic_rule | frontloaded | normal | 50 | 1.741 | [0.735, 2.748] |
| G2_Q_learning_existing | G0_TWAP | randomized | high_volatility | 50 | 3.007 | [1.245, 4.769] |
| G2_Q_learning_existing | G1_dynamic_rule | randomized | high_volatility | 50 | 3.416 | [1.604, 5.229] |
| G2_Q_learning_existing | G0_TWAP | randomized | normal | 50 | 2.596 | [1.804, 3.387] |
| G2_Q_learning_existing | G1_dynamic_rule | randomized | normal | 50 | 2.500 | [1.775, 3.225] |
| G2_Q_learning_existing | G0_TWAP | twap | high_volatility | 50 | 0.715 | [-1.194, 2.623] |
| G2_Q_learning_existing | G1_dynamic_rule | twap | high_volatility | 50 | 0.967 | [-1.313, 3.247] |
| G2_Q_learning_existing | G0_TWAP | twap | normal | 50 | 1.827 | [0.818, 2.835] |
| G2_Q_learning_existing | G1_dynamic_rule | twap | normal | 50 | 1.901 | [0.936, 2.866] |
| G3_opponent_aware_Q_existing | G0_TWAP | backloaded | high_volatility | 50 | 3.033 | [1.051, 5.016] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | backloaded | high_volatility | 50 | 2.960 | [0.933, 4.987] |
| G3_opponent_aware_Q_existing | G0_TWAP | backloaded | normal | 50 | 1.828 | [0.755, 2.902] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | backloaded | normal | 50 | 1.717 | [0.539, 2.895] |
| G3_opponent_aware_Q_existing | G0_TWAP | bursty | high_volatility | 50 | 0.160 | [-0.787, 1.106] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | bursty | high_volatility | 50 | 0.666 | [-0.489, 1.821] |
| G3_opponent_aware_Q_existing | G0_TWAP | bursty | normal | 50 | 0.307 | [-0.134, 0.749] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | bursty | normal | 50 | 0.317 | [-0.173, 0.807] |
| G3_opponent_aware_Q_existing | G0_TWAP | frontloaded | high_volatility | 50 | 0.944 | [-0.942, 2.829] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.586 | [-0.701, 3.872] |
| G3_opponent_aware_Q_existing | G0_TWAP | frontloaded | normal | 50 | 1.365 | [0.453, 2.277] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | frontloaded | normal | 50 | 1.521 | [0.574, 2.469] |
| G3_opponent_aware_Q_existing | G0_TWAP | randomized | high_volatility | 50 | 2.768 | [1.177, 4.358] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | randomized | high_volatility | 50 | 3.177 | [1.527, 4.827] |
| G3_opponent_aware_Q_existing | G0_TWAP | randomized | normal | 50 | 2.325 | [1.596, 3.055] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | randomized | normal | 50 | 2.230 | [1.564, 2.895] |
| G3_opponent_aware_Q_existing | G0_TWAP | twap | high_volatility | 50 | 0.757 | [-1.144, 2.657] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | twap | high_volatility | 50 | 1.009 | [-1.268, 3.286] |
| G3_opponent_aware_Q_existing | G0_TWAP | twap | normal | 50 | 1.925 | [0.889, 2.960] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | twap | normal | 50 | 1.999 | [1.009, 2.988] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | backloaded | high_volatility | 50 | 1.547 | [0.473, 2.622] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.474 | [0.394, 2.554] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | backloaded | normal | 50 | 1.448 | [0.818, 2.078] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | backloaded | normal | 50 | 1.337 | [0.647, 2.026] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | bursty | high_volatility | 50 | 0.494 | [-0.737, 1.726] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.001 | [-0.420, 2.422] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | bursty | normal | 50 | 0.456 | [-0.172, 1.084] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | bursty | normal | 50 | 0.466 | [-0.194, 1.125] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | frontloaded | high_volatility | 50 | 0.294 | [-0.944, 1.532] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.936 | [-0.416, 2.289] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | frontloaded | normal | 50 | 0.862 | [0.148, 1.576] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 1.018 | [0.354, 1.683] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | randomized | high_volatility | 50 | 1.118 | [0.135, 2.101] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.528 | [0.572, 2.483] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | randomized | normal | 50 | 1.506 | [0.967, 2.046] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | randomized | normal | 50 | 1.410 | [0.897, 1.924] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | twap | high_volatility | 50 | 0.505 | [-0.461, 1.470] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | twap | high_volatility | 50 | 0.757 | [-0.329, 1.844] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | twap | normal | 50 | 0.975 | [0.374, 1.575] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | twap | normal | 50 | 1.049 | [0.515, 1.582] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | backloaded | high_volatility | 50 | 1.055 | [0.147, 1.964] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.982 | [0.065, 1.898] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | backloaded | normal | 50 | 1.182 | [0.585, 1.779] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | backloaded | normal | 50 | 1.070 | [0.423, 1.718] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | bursty | high_volatility | 50 | 1.361 | [0.540, 2.183] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.868 | [0.649, 3.087] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | bursty | normal | 50 | 0.427 | [-0.138, 0.993] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.437 | [-0.230, 1.103] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | frontloaded | high_volatility | 50 | 0.833 | [0.063, 1.603] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.475 | [0.173, 2.777] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | frontloaded | normal | 50 | 0.741 | [0.266, 1.217] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.898 | [0.268, 1.527] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | randomized | high_volatility | 50 | 0.552 | [-0.089, 1.193] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.962 | [0.112, 1.812] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | randomized | normal | 50 | 1.112 | [0.708, 1.516] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | randomized | normal | 50 | 1.016 | [0.571, 1.461] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | twap | high_volatility | 50 | 0.209 | [-0.368, 0.787] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | twap | high_volatility | 50 | 0.462 | [-0.323, 1.246] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | twap | normal | 50 | 0.369 | [-0.092, 0.830] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | twap | normal | 50 | 0.443 | [-0.049, 0.935] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | backloaded | high_volatility | 50 | 0.885 | [-0.407, 2.177] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.812 | [-0.706, 2.329] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | backloaded | normal | 50 | 0.676 | [0.028, 1.325] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | backloaded | normal | 50 | 0.565 | [-0.290, 1.419] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | bursty | high_volatility | 50 | 0.042 | [-1.441, 1.526] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.549 | [-1.136, 2.234] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | bursty | normal | 50 | 0.766 | [0.044, 1.488] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.776 | [0.006, 1.546] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | frontloaded | high_volatility | 50 | 0.722 | [-0.840, 2.284] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.364 | [-0.665, 3.393] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | frontloaded | normal | 50 | 0.947 | [0.258, 1.635] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 1.103 | [0.333, 1.873] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | randomized | high_volatility | 50 | 2.533 | [1.255, 3.811] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 2.943 | [1.568, 4.317] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | randomized | normal | 50 | 1.166 | [0.616, 1.716] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | randomized | normal | 50 | 1.070 | [0.533, 1.608] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | twap | high_volatility | 50 | 0.047 | [-0.995, 1.089] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | twap | high_volatility | 50 | 0.299 | [-1.304, 1.903] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | twap | normal | 50 | 0.439 | [-0.183, 1.060] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | twap | normal | 50 | 0.513 | [-0.187, 1.212] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | backloaded | high_volatility | 50 | 0.456 | [-0.662, 1.574] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.383 | [-0.976, 1.742] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | backloaded | normal | 50 | 1.133 | [0.411, 1.855] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | backloaded | normal | 50 | 1.022 | [0.100, 1.944] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | bursty | high_volatility | 50 | 0.043 | [-0.561, 0.647] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.550 | [-0.413, 1.512] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | bursty | normal | 50 | 0.119 | [-0.110, 0.348] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.128 | [-0.281, 0.538] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | frontloaded | high_volatility | 50 | -0.242 | [-0.874, 0.391] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.400 | [-0.418, 1.219] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | frontloaded | normal | 50 | 0.100 | [-0.391, 0.591] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 0.256 | [-0.264, 0.776] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | randomized | high_volatility | 50 | 1.396 | [0.453, 2.339] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.805 | [0.687, 2.923] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | randomized | normal | 50 | 1.089 | [0.577, 1.601] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | randomized | normal | 50 | 0.993 | [0.511, 1.476] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | twap | high_volatility | 50 | -0.235 | [-1.399, 0.929] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 0.018 | [-1.416, 1.452] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | twap | normal | 50 | 0.895 | [0.241, 1.548] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | twap | normal | 50 | 0.969 | [0.301, 1.637] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | backloaded | high_volatility | 50 | 1.145 | [0.149, 2.140] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.071 | [-0.269, 2.411] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | backloaded | normal | 50 | 1.238 | [0.484, 1.993] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | backloaded | normal | 50 | 1.127 | [0.161, 2.093] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | bursty | high_volatility | 50 | 0.453 | [-0.736, 1.642] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.959 | [-0.396, 2.314] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | bursty | normal | 50 | 0.039 | [-0.412, 0.490] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.049 | [-0.505, 0.602] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | frontloaded | high_volatility | 50 | 0.792 | [-0.820, 2.405] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.435 | [-0.601, 3.470] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | frontloaded | normal | 50 | 0.940 | [0.196, 1.684] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 1.096 | [0.278, 1.914] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | randomized | high_volatility | 50 | 1.328 | [0.267, 2.390] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.738 | [0.450, 3.026] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | randomized | normal | 50 | 1.357 | [0.809, 1.906] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | randomized | normal | 50 | 1.261 | [0.693, 1.830] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | twap | high_volatility | 50 | 0.305 | [-0.875, 1.485] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | twap | high_volatility | 50 | 0.557 | [-1.171, 2.285] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | twap | normal | 50 | 1.096 | [0.411, 1.782] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | twap | normal | 50 | 1.170 | [0.418, 1.922] |
| rule_guided_double_Q_m10_run1 | G0_TWAP | backloaded | high_volatility | 50 | 0.073 | [-0.480, 0.627] |
| rule_guided_double_Q_m10_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run1 | G0_TWAP | backloaded | normal | 50 | 0.112 | [-0.257, 0.480] |
| rule_guided_double_Q_m10_run1 | G1_dynamic_rule | backloaded | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run1 | G0_TWAP | bursty | high_volatility | 50 | -0.506 | [-1.030, 0.017] |
| rule_guided_double_Q_m10_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run1 | G0_TWAP | bursty | normal | 50 | -0.010 | [-0.275, 0.256] |
| rule_guided_double_Q_m10_run1 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run1 | G0_TWAP | frontloaded | high_volatility | 50 | -0.644 | [-1.385, 0.097] |
| rule_guided_double_Q_m10_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | -0.002 | [-0.018, 0.014] |
| rule_guided_double_Q_m10_run1 | G0_TWAP | frontloaded | normal | 50 | -0.150 | [-0.405, 0.105] |
| rule_guided_double_Q_m10_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 0.006 | [-0.003, 0.016] |
| rule_guided_double_Q_m10_run1 | G0_TWAP | randomized | high_volatility | 50 | -0.402 | [-0.952, 0.148] |
| rule_guided_double_Q_m10_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.008 | [-0.005, 0.020] |
| rule_guided_double_Q_m10_run1 | G0_TWAP | randomized | normal | 50 | 0.096 | [-0.089, 0.281] |
| rule_guided_double_Q_m10_run1 | G1_dynamic_rule | randomized | normal | 50 | 0.000 | [-0.002, 0.003] |
| rule_guided_double_Q_m10_run1 | G0_TWAP | twap | high_volatility | 50 | -0.254 | [-0.983, 0.475] |
| rule_guided_double_Q_m10_run1 | G1_dynamic_rule | twap | high_volatility | 50 | -0.001 | [-0.019, 0.016] |
| rule_guided_double_Q_m10_run1 | G0_TWAP | twap | normal | 50 | -0.074 | [-0.306, 0.158] |
| rule_guided_double_Q_m10_run1 | G1_dynamic_rule | twap | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run2 | G0_TWAP | backloaded | high_volatility | 50 | 0.073 | [-0.480, 0.627] |
| rule_guided_double_Q_m10_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run2 | G0_TWAP | backloaded | normal | 50 | 0.112 | [-0.257, 0.480] |
| rule_guided_double_Q_m10_run2 | G1_dynamic_rule | backloaded | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run2 | G0_TWAP | bursty | high_volatility | 50 | -0.488 | [-1.018, 0.042] |
| rule_guided_double_Q_m10_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.019 | [-0.012, 0.049] |
| rule_guided_double_Q_m10_run2 | G0_TWAP | bursty | normal | 50 | -0.010 | [-0.275, 0.256] |
| rule_guided_double_Q_m10_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run2 | G0_TWAP | frontloaded | high_volatility | 50 | -0.642 | [-1.383, 0.098] |
| rule_guided_double_Q_m10_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run2 | G0_TWAP | frontloaded | normal | 50 | -0.156 | [-0.410, 0.097] |
| rule_guided_double_Q_m10_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run2 | G0_TWAP | randomized | high_volatility | 50 | -0.410 | [-0.958, 0.139] |
| rule_guided_double_Q_m10_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run2 | G0_TWAP | randomized | normal | 50 | 0.096 | [-0.089, 0.280] |
| rule_guided_double_Q_m10_run2 | G1_dynamic_rule | randomized | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run2 | G0_TWAP | twap | high_volatility | 50 | -0.254 | [-0.983, 0.475] |
| rule_guided_double_Q_m10_run2 | G1_dynamic_rule | twap | high_volatility | 50 | -0.001 | [-0.019, 0.016] |
| rule_guided_double_Q_m10_run2 | G0_TWAP | twap | normal | 50 | -0.074 | [-0.306, 0.158] |
| rule_guided_double_Q_m10_run2 | G1_dynamic_rule | twap | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run3 | G0_TWAP | backloaded | high_volatility | 50 | 0.089 | [-0.469, 0.647] |
| rule_guided_double_Q_m10_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.016 | [-0.010, 0.042] |
| rule_guided_double_Q_m10_run3 | G0_TWAP | backloaded | normal | 50 | 0.112 | [-0.257, 0.480] |
| rule_guided_double_Q_m10_run3 | G1_dynamic_rule | backloaded | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run3 | G0_TWAP | bursty | high_volatility | 50 | -0.506 | [-1.030, 0.017] |
| rule_guided_double_Q_m10_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run3 | G0_TWAP | bursty | normal | 50 | -0.010 | [-0.275, 0.256] |
| rule_guided_double_Q_m10_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run3 | G0_TWAP | frontloaded | high_volatility | 50 | -0.642 | [-1.383, 0.098] |
| rule_guided_double_Q_m10_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run3 | G0_TWAP | frontloaded | normal | 50 | -0.156 | [-0.410, 0.097] |
| rule_guided_double_Q_m10_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run3 | G0_TWAP | randomized | high_volatility | 50 | -0.407 | [-0.956, 0.143] |
| rule_guided_double_Q_m10_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.003 | [-0.007, 0.013] |
| rule_guided_double_Q_m10_run3 | G0_TWAP | randomized | normal | 50 | 0.096 | [-0.089, 0.280] |
| rule_guided_double_Q_m10_run3 | G1_dynamic_rule | randomized | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run3 | G0_TWAP | twap | high_volatility | 50 | -0.254 | [-0.983, 0.475] |
| rule_guided_double_Q_m10_run3 | G1_dynamic_rule | twap | high_volatility | 50 | -0.001 | [-0.019, 0.016] |
| rule_guided_double_Q_m10_run3 | G0_TWAP | twap | normal | 50 | -0.074 | [-0.306, 0.158] |
| rule_guided_double_Q_m10_run3 | G1_dynamic_rule | twap | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run4 | G0_TWAP | backloaded | high_volatility | 50 | 0.073 | [-0.480, 0.627] |
| rule_guided_double_Q_m10_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run4 | G0_TWAP | backloaded | normal | 50 | 0.112 | [-0.257, 0.480] |
| rule_guided_double_Q_m10_run4 | G1_dynamic_rule | backloaded | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run4 | G0_TWAP | bursty | high_volatility | 50 | -0.506 | [-1.030, 0.017] |
| rule_guided_double_Q_m10_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run4 | G0_TWAP | bursty | normal | 50 | -0.010 | [-0.275, 0.256] |
| rule_guided_double_Q_m10_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run4 | G0_TWAP | frontloaded | high_volatility | 50 | -0.644 | [-1.385, 0.097] |
| rule_guided_double_Q_m10_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | -0.002 | [-0.018, 0.014] |
| rule_guided_double_Q_m10_run4 | G0_TWAP | frontloaded | normal | 50 | -0.156 | [-0.410, 0.097] |
| rule_guided_double_Q_m10_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run4 | G0_TWAP | randomized | high_volatility | 50 | -0.406 | [-0.956, 0.143] |
| rule_guided_double_Q_m10_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.003 | [-0.012, 0.019] |
| rule_guided_double_Q_m10_run4 | G0_TWAP | randomized | normal | 50 | 0.096 | [-0.089, 0.280] |
| rule_guided_double_Q_m10_run4 | G1_dynamic_rule | randomized | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run4 | G0_TWAP | twap | high_volatility | 50 | -0.275 | [-1.018, 0.468] |
| rule_guided_double_Q_m10_run4 | G1_dynamic_rule | twap | high_volatility | 50 | -0.023 | [-0.127, 0.082] |
| rule_guided_double_Q_m10_run4 | G0_TWAP | twap | normal | 50 | -0.074 | [-0.306, 0.158] |
| rule_guided_double_Q_m10_run4 | G1_dynamic_rule | twap | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run5 | G0_TWAP | backloaded | high_volatility | 50 | 0.073 | [-0.480, 0.627] |
| rule_guided_double_Q_m10_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run5 | G0_TWAP | backloaded | normal | 50 | 0.112 | [-0.257, 0.480] |
| rule_guided_double_Q_m10_run5 | G1_dynamic_rule | backloaded | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run5 | G0_TWAP | bursty | high_volatility | 50 | -0.506 | [-1.030, 0.017] |
| rule_guided_double_Q_m10_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run5 | G0_TWAP | bursty | normal | 50 | -0.010 | [-0.275, 0.256] |
| rule_guided_double_Q_m10_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run5 | G0_TWAP | frontloaded | high_volatility | 50 | -0.644 | [-1.385, 0.097] |
| rule_guided_double_Q_m10_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | -0.002 | [-0.018, 0.014] |
| rule_guided_double_Q_m10_run5 | G0_TWAP | frontloaded | normal | 50 | -0.156 | [-0.410, 0.097] |
| rule_guided_double_Q_m10_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run5 | G0_TWAP | randomized | high_volatility | 50 | -0.404 | [-0.954, 0.146] |
| rule_guided_double_Q_m10_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.006 | [-0.008, 0.019] |
| rule_guided_double_Q_m10_run5 | G0_TWAP | randomized | normal | 50 | 0.096 | [-0.089, 0.280] |
| rule_guided_double_Q_m10_run5 | G1_dynamic_rule | randomized | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m10_run5 | G0_TWAP | twap | high_volatility | 50 | -0.270 | [-1.009, 0.470] |
| rule_guided_double_Q_m10_run5 | G1_dynamic_rule | twap | high_volatility | 50 | -0.017 | [-0.109, 0.075] |
| rule_guided_double_Q_m10_run5 | G0_TWAP | twap | normal | 50 | -0.074 | [-0.306, 0.158] |
| rule_guided_double_Q_m10_run5 | G1_dynamic_rule | twap | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | backloaded | high_volatility | 50 | 0.329 | [-0.344, 1.002] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.256 | [-0.001, 0.513] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | backloaded | normal | 50 | 0.197 | [-0.179, 0.574] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | backloaded | normal | 50 | 0.086 | [0.020, 0.152] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | bursty | high_volatility | 50 | -0.419 | [-0.983, 0.145] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.087 | [-0.024, 0.198] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | bursty | normal | 50 | 0.009 | [-0.266, 0.284] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | bursty | normal | 50 | 0.018 | [-0.049, 0.085] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | frontloaded | high_volatility | 50 | -0.597 | [-1.362, 0.168] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.045 | [-0.101, 0.191] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | frontloaded | normal | 50 | -0.152 | [-0.405, 0.101] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 0.004 | [-0.046, 0.053] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | randomized | high_volatility | 50 | -0.355 | [-0.922, 0.212] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.055 | [-0.058, 0.167] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | randomized | normal | 50 | 0.164 | [-0.041, 0.370] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | randomized | normal | 50 | 0.069 | [-0.001, 0.138] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | twap | high_volatility | 50 | -0.259 | [-1.169, 0.652] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | twap | high_volatility | 50 | -0.006 | [-0.461, 0.449] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | twap | normal | 50 | -0.120 | [-0.336, 0.096] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | twap | normal | 50 | -0.046 | [-0.082, -0.010] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | backloaded | high_volatility | 50 | 0.151 | [-0.472, 0.774] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.078 | [-0.120, 0.275] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | backloaded | normal | 50 | 0.235 | [-0.196, 0.665] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | backloaded | normal | 50 | 0.123 | [-0.064, 0.310] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | bursty | high_volatility | 50 | -0.439 | [-1.001, 0.123] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.068 | [-0.045, 0.180] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | bursty | normal | 50 | 0.047 | [-0.225, 0.319] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.057 | [0.004, 0.110] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | frontloaded | high_volatility | 50 | -0.733 | [-1.483, 0.017] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | -0.091 | [-0.188, 0.006] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | frontloaded | normal | 50 | -0.073 | [-0.352, 0.205] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.083 | [0.015, 0.151] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | randomized | high_volatility | 50 | -0.219 | [-0.838, 0.401] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.191 | [0.005, 0.376] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | randomized | normal | 50 | 0.214 | [-0.074, 0.501] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | randomized | normal | 50 | 0.118 | [-0.047, 0.283] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | twap | high_volatility | 50 | -0.253 | [-0.973, 0.467] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | twap | high_volatility | 50 | -0.001 | [-0.083, 0.081] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | twap | normal | 50 | -0.041 | [-0.276, 0.195] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | twap | normal | 50 | 0.033 | [-0.035, 0.101] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | backloaded | high_volatility | 50 | 0.517 | [-0.579, 1.612] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.444 | [-0.343, 1.230] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | backloaded | normal | 50 | 0.068 | [-0.292, 0.428] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | backloaded | normal | 50 | -0.044 | [-0.093, 0.006] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | bursty | high_volatility | 50 | -0.440 | [-1.003, 0.123] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.066 | [-0.046, 0.179] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | bursty | normal | 50 | 0.015 | [-0.263, 0.292] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.024 | [-0.032, 0.080] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | frontloaded | high_volatility | 50 | -0.756 | [-1.863, 0.351] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | -0.114 | [-0.809, 0.581] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | frontloaded | normal | 50 | -0.194 | [-0.432, 0.043] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | frontloaded | normal | 50 | -0.038 | [-0.085, 0.009] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | randomized | high_volatility | 50 | 0.106 | [-0.740, 0.951] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.515 | [0.049, 0.981] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | randomized | normal | 50 | 0.078 | [-0.110, 0.265] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | randomized | normal | 50 | -0.018 | [-0.079, 0.043] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | twap | high_volatility | 50 | -0.220 | [-0.939, 0.499] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | twap | high_volatility | 50 | 0.032 | [-0.096, 0.160] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | twap | normal | 50 | -0.108 | [-0.329, 0.114] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | twap | normal | 50 | -0.034 | [-0.078, 0.010] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | backloaded | high_volatility | 50 | 0.223 | [-0.410, 0.857] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.150 | [-0.047, 0.348] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | backloaded | normal | 50 | 0.102 | [-0.263, 0.467] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | backloaded | normal | 50 | -0.010 | [-0.046, 0.026] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | bursty | high_volatility | 50 | -0.439 | [-1.002, 0.124] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.067 | [-0.045, 0.180] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | bursty | normal | 50 | 0.022 | [-0.254, 0.299] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.032 | [-0.006, 0.070] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | frontloaded | high_volatility | 50 | -0.622 | [-1.409, 0.166] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.020 | [-0.130, 0.170] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | frontloaded | normal | 50 | -0.118 | [-0.373, 0.137] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 0.038 | [-0.013, 0.090] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | randomized | high_volatility | 50 | -0.205 | [-0.886, 0.477] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.205 | [-0.063, 0.472] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | randomized | normal | 50 | 0.054 | [-0.122, 0.230] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | randomized | normal | 50 | -0.042 | [-0.094, 0.010] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | twap | high_volatility | 50 | -0.224 | [-0.945, 0.498] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 0.029 | [-0.064, 0.122] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | twap | normal | 50 | -0.110 | [-0.326, 0.107] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | twap | normal | 50 | -0.036 | [-0.073, 0.002] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | backloaded | high_volatility | 50 | -0.024 | [-0.546, 0.498] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | -0.097 | [-0.198, 0.004] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | backloaded | normal | 50 | 0.241 | [-0.155, 0.637] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | backloaded | normal | 50 | 0.130 | [-0.012, 0.271] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | bursty | high_volatility | 50 | -0.534 | [-1.056, -0.011] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | -0.027 | [-0.076, 0.021] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | bursty | normal | 50 | 0.027 | [-0.250, 0.304] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.036 | [-0.005, 0.078] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | frontloaded | high_volatility | 50 | -0.626 | [-1.362, 0.111] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.017 | [-0.039, 0.072] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | frontloaded | normal | 50 | -0.123 | [-0.423, 0.177] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 0.033 | [-0.093, 0.159] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | randomized | high_volatility | 50 | -0.315 | [-0.910, 0.279] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.094 | [-0.063, 0.252] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | randomized | normal | 50 | 0.081 | [-0.099, 0.262] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | randomized | normal | 50 | -0.014 | [-0.062, 0.033] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | twap | high_volatility | 50 | -0.115 | [-0.957, 0.727] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | twap | high_volatility | 50 | 0.137 | [-0.227, 0.501] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | twap | normal | 50 | -0.100 | [-0.321, 0.121] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | twap | normal | 50 | -0.026 | [-0.059, 0.007] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | backloaded | high_volatility | 50 | 0.097 | [-0.471, 0.665] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.024 | [-0.074, 0.121] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | backloaded | normal | 50 | 0.178 | [-0.220, 0.576] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | backloaded | normal | 50 | 0.067 | [-0.032, 0.165] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | bursty | high_volatility | 50 | -0.437 | [-1.000, 0.126] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.069 | [-0.043, 0.181] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | bursty | normal | 50 | 0.016 | [-0.255, 0.287] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | bursty | normal | 50 | 0.025 | [0.002, 0.049] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | frontloaded | high_volatility | 50 | -0.637 | [-1.382, 0.107] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.005 | [-0.052, 0.062] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | frontloaded | normal | 50 | -0.055 | [-0.349, 0.240] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 0.101 | [0.006, 0.197] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | randomized | high_volatility | 50 | -0.388 | [-0.930, 0.154] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.021 | [-0.043, 0.086] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | randomized | normal | 50 | 0.111 | [-0.092, 0.313] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | randomized | normal | 50 | 0.015 | [-0.062, 0.092] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | twap | high_volatility | 50 | -0.274 | [-1.019, 0.471] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | twap | high_volatility | 50 | -0.022 | [-0.139, 0.096] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | twap | normal | 50 | -0.023 | [-0.284, 0.239] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | twap | normal | 50 | 0.051 | [-0.009, 0.112] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | backloaded | high_volatility | 50 | 0.001 | [-0.536, 0.538] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | -0.073 | [-0.134, -0.011] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | backloaded | normal | 50 | 0.109 | [-0.272, 0.491] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | backloaded | normal | 50 | -0.002 | [-0.065, 0.061] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | bursty | high_volatility | 50 | -0.442 | [-1.004, 0.120] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.065 | [-0.048, 0.177] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | bursty | normal | 50 | 0.029 | [-0.247, 0.306] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.039 | [-0.003, 0.081] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | frontloaded | high_volatility | 50 | -0.663 | [-1.404, 0.077] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | -0.021 | [-0.054, 0.012] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | frontloaded | normal | 50 | -0.073 | [-0.352, 0.205] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.083 | [0.015, 0.151] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | randomized | high_volatility | 50 | -0.437 | [-0.977, 0.104] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | -0.027 | [-0.076, 0.021] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | randomized | normal | 50 | 0.068 | [-0.124, 0.260] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | randomized | normal | 50 | -0.028 | [-0.083, 0.028] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | twap | high_volatility | 50 | -0.238 | [-0.960, 0.484] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | twap | high_volatility | 50 | 0.014 | [-0.060, 0.089] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | twap | normal | 50 | -0.002 | [-0.262, 0.258] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | twap | normal | 50 | 0.072 | [0.020, 0.124] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | backloaded | high_volatility | 50 | 0.241 | [-0.564, 1.046] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.168 | [-0.322, 0.657] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | backloaded | normal | 50 | 0.053 | [-0.306, 0.413] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | backloaded | normal | 50 | -0.058 | [-0.103, -0.013] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | bursty | high_volatility | 50 | -0.440 | [-1.003, 0.123] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.066 | [-0.046, 0.179] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | bursty | normal | 50 | 0.027 | [-0.250, 0.305] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.037 | [-0.005, 0.079] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | frontloaded | high_volatility | 50 | -0.273 | [-1.308, 0.763] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.369 | [-0.216, 0.955] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | frontloaded | normal | 50 | -0.193 | [-0.432, 0.046] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | frontloaded | normal | 50 | -0.037 | [-0.084, 0.010] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | randomized | high_volatility | 50 | 0.106 | [-0.745, 0.957] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.515 | [0.049, 0.982] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | randomized | normal | 50 | 0.036 | [-0.133, 0.204] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | randomized | normal | 50 | -0.060 | [-0.106, -0.014] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | twap | high_volatility | 50 | -0.258 | [-0.976, 0.460] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | twap | high_volatility | 50 | -0.006 | [-0.096, 0.084] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | twap | normal | 50 | -0.109 | [-0.328, 0.110] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | twap | normal | 50 | -0.035 | [-0.076, 0.006] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | backloaded | high_volatility | 50 | 0.309 | [-0.435, 1.053] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.236 | [-0.100, 0.572] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | backloaded | normal | 50 | 0.093 | [-0.274, 0.460] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | backloaded | normal | 50 | -0.018 | [-0.057, 0.020] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | bursty | high_volatility | 50 | -0.441 | [-1.004, 0.122] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.065 | [-0.047, 0.178] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | bursty | normal | 50 | 0.021 | [-0.255, 0.297] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.030 | [-0.007, 0.068] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | frontloaded | high_volatility | 50 | -0.648 | [-1.393, 0.097] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | -0.006 | [-0.066, 0.054] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | frontloaded | normal | 50 | -0.124 | [-0.377, 0.129] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 0.032 | [-0.012, 0.075] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | randomized | high_volatility | 50 | -0.292 | [-0.887, 0.303] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.117 | [-0.013, 0.248] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | randomized | normal | 50 | 0.061 | [-0.115, 0.237] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | randomized | normal | 50 | -0.035 | [-0.078, 0.009] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | twap | high_volatility | 50 | -0.251 | [-0.972, 0.469] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 0.001 | [-0.080, 0.083] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | twap | normal | 50 | -0.085 | [-0.312, 0.142] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | twap | normal | 50 | -0.011 | [-0.047, 0.025] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | backloaded | high_volatility | 50 | -0.027 | [-0.551, 0.497] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | -0.100 | [-0.196, -0.004] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | backloaded | normal | 50 | 0.088 | [-0.275, 0.451] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | backloaded | normal | 50 | -0.024 | [-0.061, 0.013] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | bursty | high_volatility | 50 | -0.438 | [-1.002, 0.125] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.068 | [-0.044, 0.181] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | bursty | normal | 50 | 0.026 | [-0.251, 0.303] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.036 | [-0.006, 0.077] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | frontloaded | high_volatility | 50 | -0.627 | [-1.363, 0.109] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.015 | [-0.040, 0.071] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | frontloaded | normal | 50 | -0.187 | [-0.433, 0.058] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | frontloaded | normal | 50 | -0.031 | [-0.068, 0.006] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | randomized | high_volatility | 50 | -0.480 | [-1.009, 0.048] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | -0.071 | [-0.139, -0.003] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | randomized | normal | 50 | 0.074 | [-0.100, 0.247] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | randomized | normal | 50 | -0.022 | [-0.056, 0.012] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | twap | high_volatility | 50 | -0.238 | [-1.098, 0.622] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | twap | high_volatility | 50 | 0.014 | [-0.329, 0.358] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | twap | normal | 50 | -0.020 | [-0.281, 0.241] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | twap | normal | 50 | 0.054 | [-0.006, 0.114] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | backloaded | high_volatility | 50 | 0.114 | [-0.467, 0.695] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.041 | [-0.053, 0.135] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | backloaded | normal | 50 | 0.104 | [-0.277, 0.486] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | backloaded | normal | 50 | -0.007 | [-0.069, 0.055] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | bursty | high_volatility | 50 | -0.438 | [-1.001, 0.125] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.068 | [-0.043, 0.180] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | bursty | normal | 50 | 0.014 | [-0.257, 0.284] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | bursty | normal | 50 | 0.023 | [0.000, 0.047] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | frontloaded | high_volatility | 50 | -0.644 | [-1.390, 0.101] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | -0.002 | [-0.057, 0.052] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | frontloaded | normal | 50 | -0.077 | [-0.354, 0.201] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 0.080 | [0.012, 0.147] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | randomized | high_volatility | 50 | -0.399 | [-0.947, 0.148] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.010 | [-0.055, 0.075] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | randomized | normal | 50 | 0.064 | [-0.126, 0.254] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | randomized | normal | 50 | -0.031 | [-0.082, 0.019] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | twap | high_volatility | 50 | -0.276 | [-1.020, 0.469] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | twap | high_volatility | 50 | -0.023 | [-0.140, 0.093] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | twap | normal | 50 | -0.015 | [-0.276, 0.245] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | twap | normal | 50 | 0.059 | [0.000, 0.117] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | backloaded | high_volatility | 50 | 0.114 | [-0.467, 0.695] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.041 | [-0.053, 0.135] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | backloaded | normal | 50 | 0.109 | [-0.272, 0.490] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | backloaded | normal | 50 | -0.002 | [-0.064, 0.059] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | bursty | high_volatility | 50 | -0.440 | [-1.002, 0.122] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.066 | [-0.046, 0.179] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | bursty | normal | 50 | 0.006 | [-0.265, 0.277] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.016 | [-0.017, 0.048] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | frontloaded | high_volatility | 50 | -0.647 | [-1.392, 0.097] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | -0.005 | [-0.060, 0.049] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | frontloaded | normal | 50 | -0.077 | [-0.354, 0.201] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.080 | [0.012, 0.147] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | randomized | high_volatility | 50 | -0.399 | [-0.944, 0.147] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.011 | [-0.053, 0.075] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | randomized | normal | 50 | 0.064 | [-0.126, 0.254] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | randomized | normal | 50 | -0.032 | [-0.082, 0.019] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | twap | high_volatility | 50 | -0.278 | [-1.021, 0.466] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | twap | high_volatility | 50 | -0.025 | [-0.137, 0.086] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | twap | normal | 50 | -0.013 | [-0.274, 0.247] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | twap | normal | 50 | 0.061 | [0.003, 0.118] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | backloaded | high_volatility | 50 | 0.022 | [-0.513, 0.556] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | -0.051 | [-0.121, 0.019] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | backloaded | normal | 50 | 0.104 | [-0.277, 0.486] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | backloaded | normal | 50 | -0.007 | [-0.069, 0.055] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | bursty | high_volatility | 50 | -0.440 | [-1.003, 0.123] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.066 | [-0.046, 0.178] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | bursty | normal | 50 | 0.030 | [-0.248, 0.307] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.039 | [-0.002, 0.081] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | frontloaded | high_volatility | 50 | -0.646 | [-1.384, 0.092] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | -0.004 | [-0.044, 0.036] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | frontloaded | normal | 50 | -0.077 | [-0.354, 0.201] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 0.080 | [0.012, 0.147] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | randomized | high_volatility | 50 | -0.460 | [-0.996, 0.076] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | -0.050 | [-0.108, 0.008] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | randomized | normal | 50 | 0.064 | [-0.126, 0.254] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | randomized | normal | 50 | -0.031 | [-0.082, 0.019] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | twap | high_volatility | 50 | -0.270 | [-1.011, 0.471] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | twap | high_volatility | 50 | -0.018 | [-0.116, 0.081] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | twap | normal | 50 | -0.015 | [-0.276, 0.245] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | twap | normal | 50 | 0.058 | [0.000, 0.117] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | backloaded | high_volatility | 50 | 0.112 | [-0.470, 0.693] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.038 | [-0.056, 0.132] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | backloaded | normal | 50 | 0.109 | [-0.272, 0.490] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | backloaded | normal | 50 | -0.002 | [-0.064, 0.059] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | bursty | high_volatility | 50 | -0.479 | [-1.013, 0.054] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.027 | [-0.011, 0.065] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | bursty | normal | 50 | -0.002 | [-0.268, 0.264] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.008 | [-0.003, 0.018] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | frontloaded | high_volatility | 50 | -0.647 | [-1.392, 0.097] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | -0.005 | [-0.060, 0.049] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | frontloaded | normal | 50 | -0.077 | [-0.354, 0.201] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 0.080 | [0.012, 0.147] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | randomized | high_volatility | 50 | -0.401 | [-0.945, 0.144] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.009 | [-0.056, 0.074] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | randomized | normal | 50 | 0.063 | [-0.127, 0.253] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | randomized | normal | 50 | -0.033 | [-0.083, 0.018] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | twap | high_volatility | 50 | -0.276 | [-1.020, 0.468] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | twap | high_volatility | 50 | -0.023 | [-0.138, 0.091] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | twap | normal | 50 | -0.017 | [-0.277, 0.244] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | twap | normal | 50 | 0.057 | [-0.001, 0.116] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | backloaded | high_volatility | 50 | 0.114 | [-0.467, 0.695] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.041 | [-0.053, 0.135] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | backloaded | normal | 50 | 0.109 | [-0.272, 0.490] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | backloaded | normal | 50 | -0.002 | [-0.064, 0.059] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | bursty | high_volatility | 50 | -0.474 | [-1.014, 0.066] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.033 | [-0.026, 0.091] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | bursty | normal | 50 | -0.001 | [-0.268, 0.266] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.009 | [-0.006, 0.024] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | frontloaded | high_volatility | 50 | -0.644 | [-1.390, 0.101] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | -0.002 | [-0.057, 0.052] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | frontloaded | normal | 50 | -0.085 | [-0.362, 0.192] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 0.071 | [0.005, 0.137] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | randomized | high_volatility | 50 | -0.396 | [-0.942, 0.151] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.014 | [-0.051, 0.078] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | randomized | normal | 50 | 0.066 | [-0.124, 0.257] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | randomized | normal | 50 | -0.030 | [-0.081, 0.022] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | twap | high_volatility | 50 | -0.270 | [-1.011, 0.470] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | twap | high_volatility | 50 | -0.018 | [-0.117, 0.081] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | twap | normal | 50 | -0.015 | [-0.276, 0.246] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | twap | normal | 50 | 0.059 | [0.001, 0.117] |
| selfplay_Q_A_run1 | G0_TWAP | backloaded | high_volatility | 50 | 1.702 | [0.424, 2.980] |
| selfplay_Q_A_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.629 | [0.258, 2.999] |
| selfplay_Q_A_run1 | G0_TWAP | backloaded | normal | 50 | 1.266 | [0.616, 1.916] |
| selfplay_Q_A_run1 | G1_dynamic_rule | backloaded | normal | 50 | 1.154 | [0.332, 1.976] |
| selfplay_Q_A_run1 | G0_TWAP | bursty | high_volatility | 50 | 0.589 | [-1.138, 2.315] |
| selfplay_Q_A_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.095 | [-0.859, 3.049] |
| selfplay_Q_A_run1 | G0_TWAP | bursty | normal | 50 | 0.610 | [-0.220, 1.441] |
| selfplay_Q_A_run1 | G1_dynamic_rule | bursty | normal | 50 | 0.620 | [-0.251, 1.491] |
| selfplay_Q_A_run1 | G0_TWAP | frontloaded | high_volatility | 50 | 1.103 | [0.031, 2.175] |
| selfplay_Q_A_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.745 | [0.239, 3.252] |
| selfplay_Q_A_run1 | G0_TWAP | frontloaded | normal | 50 | 1.035 | [0.507, 1.563] |
| selfplay_Q_A_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 1.191 | [0.602, 1.781] |
| selfplay_Q_A_run1 | G0_TWAP | randomized | high_volatility | 50 | 2.629 | [1.418, 3.841] |
| selfplay_Q_A_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 3.039 | [1.771, 4.307] |
| selfplay_Q_A_run1 | G0_TWAP | randomized | normal | 50 | 1.606 | [0.976, 2.236] |
| selfplay_Q_A_run1 | G1_dynamic_rule | randomized | normal | 50 | 1.510 | [0.915, 2.105] |
| selfplay_Q_A_run1 | G0_TWAP | twap | high_volatility | 50 | 0.325 | [-0.903, 1.553] |
| selfplay_Q_A_run1 | G1_dynamic_rule | twap | high_volatility | 50 | 0.578 | [-1.060, 2.215] |
| selfplay_Q_A_run1 | G0_TWAP | twap | normal | 50 | 1.123 | [0.466, 1.780] |
| selfplay_Q_A_run1 | G1_dynamic_rule | twap | normal | 50 | 1.197 | [0.543, 1.851] |
| selfplay_Q_A_run2 | G0_TWAP | backloaded | high_volatility | 50 | 1.307 | [0.165, 2.449] |
| selfplay_Q_A_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.234 | [-0.136, 2.603] |
| selfplay_Q_A_run2 | G0_TWAP | backloaded | normal | 50 | 0.690 | [0.047, 1.334] |
| selfplay_Q_A_run2 | G1_dynamic_rule | backloaded | normal | 50 | 0.579 | [-0.287, 1.444] |
| selfplay_Q_A_run2 | G0_TWAP | bursty | high_volatility | 50 | 0.285 | [-0.696, 1.267] |
| selfplay_Q_A_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.792 | [-0.362, 1.945] |
| selfplay_Q_A_run2 | G0_TWAP | bursty | normal | 50 | 0.507 | [-0.337, 1.350] |
| selfplay_Q_A_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.516 | [-0.348, 1.380] |
| selfplay_Q_A_run2 | G0_TWAP | frontloaded | high_volatility | 50 | 0.783 | [-0.128, 1.695] |
| selfplay_Q_A_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.426 | [-0.068, 2.920] |
| selfplay_Q_A_run2 | G0_TWAP | frontloaded | normal | 50 | 0.885 | [0.338, 1.431] |
| selfplay_Q_A_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 1.041 | [0.407, 1.675] |
| selfplay_Q_A_run2 | G0_TWAP | randomized | high_volatility | 50 | 1.455 | [0.684, 2.227] |
| selfplay_Q_A_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.865 | [0.826, 2.904] |
| selfplay_Q_A_run2 | G0_TWAP | randomized | normal | 50 | 1.279 | [0.784, 1.774] |
| selfplay_Q_A_run2 | G1_dynamic_rule | randomized | normal | 50 | 1.184 | [0.663, 1.704] |
| selfplay_Q_A_run2 | G0_TWAP | twap | high_volatility | 50 | 0.501 | [-0.536, 1.539] |
| selfplay_Q_A_run2 | G1_dynamic_rule | twap | high_volatility | 50 | 0.754 | [-0.847, 2.355] |
| selfplay_Q_A_run2 | G0_TWAP | twap | normal | 50 | 0.697 | [0.146, 1.247] |
| selfplay_Q_A_run2 | G1_dynamic_rule | twap | normal | 50 | 0.771 | [0.117, 1.424] |
| selfplay_Q_A_run3 | G0_TWAP | backloaded | high_volatility | 50 | 1.873 | [0.601, 3.145] |
| selfplay_Q_A_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.800 | [0.347, 3.253] |
| selfplay_Q_A_run3 | G0_TWAP | backloaded | normal | 50 | 1.391 | [0.670, 2.112] |
| selfplay_Q_A_run3 | G1_dynamic_rule | backloaded | normal | 50 | 1.279 | [0.387, 2.172] |
| selfplay_Q_A_run3 | G0_TWAP | bursty | high_volatility | 50 | 0.385 | [-1.271, 2.040] |
| selfplay_Q_A_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.891 | [-1.001, 2.783] |
| selfplay_Q_A_run3 | G0_TWAP | bursty | normal | 50 | 0.618 | [-0.213, 1.448] |
| selfplay_Q_A_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.627 | [-0.236, 1.490] |
| selfplay_Q_A_run3 | G0_TWAP | frontloaded | high_volatility | 50 | 0.796 | [-0.320, 1.912] |
| selfplay_Q_A_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.438 | [-0.201, 3.076] |
| selfplay_Q_A_run3 | G0_TWAP | frontloaded | normal | 50 | 0.974 | [0.343, 1.606] |
| selfplay_Q_A_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 1.131 | [0.407, 1.854] |
| selfplay_Q_A_run3 | G0_TWAP | randomized | high_volatility | 50 | 2.157 | [1.128, 3.186] |
| selfplay_Q_A_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 2.566 | [1.335, 3.798] |
| selfplay_Q_A_run3 | G0_TWAP | randomized | normal | 50 | 1.365 | [0.816, 1.914] |
| selfplay_Q_A_run3 | G1_dynamic_rule | randomized | normal | 50 | 1.269 | [0.735, 1.804] |
| selfplay_Q_A_run3 | G0_TWAP | twap | high_volatility | 50 | 0.364 | [-0.906, 1.633] |
| selfplay_Q_A_run3 | G1_dynamic_rule | twap | high_volatility | 50 | 0.616 | [-1.116, 2.349] |
| selfplay_Q_A_run3 | G0_TWAP | twap | normal | 50 | 1.158 | [0.568, 1.748] |
| selfplay_Q_A_run3 | G1_dynamic_rule | twap | normal | 50 | 1.232 | [0.627, 1.837] |
| selfplay_Q_A_run4 | G0_TWAP | backloaded | high_volatility | 50 | 2.144 | [0.676, 3.611] |
| selfplay_Q_A_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 2.071 | [0.501, 3.640] |
| selfplay_Q_A_run4 | G0_TWAP | backloaded | normal | 50 | 1.464 | [0.618, 2.311] |
| selfplay_Q_A_run4 | G1_dynamic_rule | backloaded | normal | 50 | 1.353 | [0.351, 2.355] |
| selfplay_Q_A_run4 | G0_TWAP | bursty | high_volatility | 50 | 0.868 | [-0.490, 2.226] |
| selfplay_Q_A_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.374 | [-0.291, 3.039] |
| selfplay_Q_A_run4 | G0_TWAP | bursty | normal | 50 | 0.425 | [-0.267, 1.118] |
| selfplay_Q_A_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.435 | [-0.328, 1.197] |
| selfplay_Q_A_run4 | G0_TWAP | frontloaded | high_volatility | 50 | 0.462 | [-0.890, 1.814] |
| selfplay_Q_A_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.104 | [-0.592, 2.800] |
| selfplay_Q_A_run4 | G0_TWAP | frontloaded | normal | 50 | 1.170 | [0.417, 1.922] |
| selfplay_Q_A_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 1.326 | [0.529, 2.123] |
| selfplay_Q_A_run4 | G0_TWAP | randomized | high_volatility | 50 | 2.402 | [1.317, 3.488] |
| selfplay_Q_A_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 2.812 | [1.550, 4.074] |
| selfplay_Q_A_run4 | G0_TWAP | randomized | normal | 50 | 1.685 | [1.100, 2.269] |
| selfplay_Q_A_run4 | G1_dynamic_rule | randomized | normal | 50 | 1.589 | [1.039, 2.139] |
| selfplay_Q_A_run4 | G0_TWAP | twap | high_volatility | 50 | 0.523 | [-0.917, 1.964] |
| selfplay_Q_A_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 0.776 | [-1.080, 2.632] |
| selfplay_Q_A_run4 | G0_TWAP | twap | normal | 50 | 1.435 | [0.717, 2.153] |
| selfplay_Q_A_run4 | G1_dynamic_rule | twap | normal | 50 | 1.509 | [0.814, 2.204] |
| selfplay_Q_A_run5 | G0_TWAP | backloaded | high_volatility | 50 | 2.377 | [0.696, 4.058] |
| selfplay_Q_A_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | 2.304 | [0.522, 4.085] |
| selfplay_Q_A_run5 | G0_TWAP | backloaded | normal | 50 | 1.563 | [0.641, 2.485] |
| selfplay_Q_A_run5 | G1_dynamic_rule | backloaded | normal | 50 | 1.452 | [0.385, 2.519] |
| selfplay_Q_A_run5 | G0_TWAP | bursty | high_volatility | 50 | 0.436 | [-0.921, 1.794] |
| selfplay_Q_A_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.943 | [-0.644, 2.529] |
| selfplay_Q_A_run5 | G0_TWAP | bursty | normal | 50 | 0.473 | [-0.267, 1.213] |
| selfplay_Q_A_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.483 | [-0.280, 1.245] |
| selfplay_Q_A_run5 | G0_TWAP | frontloaded | high_volatility | 50 | 0.447 | [-0.974, 1.868] |
| selfplay_Q_A_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.089 | [-0.638, 2.816] |
| selfplay_Q_A_run5 | G0_TWAP | frontloaded | normal | 50 | 1.169 | [0.331, 2.008] |
| selfplay_Q_A_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 1.326 | [0.448, 2.204] |
| selfplay_Q_A_run5 | G0_TWAP | randomized | high_volatility | 50 | 2.596 | [1.236, 3.957] |
| selfplay_Q_A_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | 3.006 | [1.559, 4.453] |
| selfplay_Q_A_run5 | G0_TWAP | randomized | normal | 50 | 1.992 | [1.325, 2.659] |
| selfplay_Q_A_run5 | G1_dynamic_rule | randomized | normal | 50 | 1.896 | [1.283, 2.510] |
| selfplay_Q_A_run5 | G0_TWAP | twap | high_volatility | 50 | 0.661 | [-1.005, 2.326] |
| selfplay_Q_A_run5 | G1_dynamic_rule | twap | high_volatility | 50 | 0.913 | [-1.185, 3.011] |
| selfplay_Q_A_run5 | G0_TWAP | twap | normal | 50 | 1.550 | [0.766, 2.335] |
| selfplay_Q_A_run5 | G1_dynamic_rule | twap | normal | 50 | 1.624 | [0.858, 2.390] |

## 汇总配对差

下表将五类固定 B 对手和 50 个评估种子作为 250 个配对测试格；学习策略的 5 个训练种子先在格内取均值。成本差为学习策略减规则策略。

| 学习策略 | 规则基线 | 场景 | 配对格数 | 平均成本差 (bp) | 近似 95% 区间 |
|---|---|---|---:|---:|---:|
| G2_Q_learning_existing | G0_TWAP | normal | 250 | 1.706 | [1.268, 2.144] |
| G2_Q_learning_existing | G0_TWAP | high_volatility | 250 | 1.620 | [0.738, 2.501] |
| G2_Q_learning_existing | G1_dynamic_rule | normal | 250 | 1.713 | [1.269, 2.156] |
| G2_Q_learning_existing | G1_dynamic_rule | high_volatility | 250 | 1.967 | [0.987, 2.947] |
| G3_opponent_aware_Q_existing | G0_TWAP | normal | 250 | 1.550 | [1.155, 1.945] |
| G3_opponent_aware_Q_existing | G0_TWAP | high_volatility | 250 | 1.532 | [0.763, 2.302] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | normal | 250 | 1.557 | [1.154, 1.959] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | high_volatility | 250 | 1.880 | [1.015, 2.744] |
| cost_aligned_schedule_Q | G0_TWAP | normal | 250 | 0.843 | [0.620, 1.066] |
| cost_aligned_schedule_Q | G0_TWAP | high_volatility | 250 | 0.706 | [0.328, 1.083] |
| cost_aligned_schedule_Q | G1_dynamic_rule | normal | 250 | 0.850 | [0.593, 1.107] |
| cost_aligned_schedule_Q | G1_dynamic_rule | high_volatility | 250 | 1.053 | [0.538, 1.568] |
| rule_guided_double_Q_m1 | G0_TWAP | normal | 250 | 0.017 | [-0.104, 0.138] |
| rule_guided_double_Q_m1 | G0_TWAP | high_volatility | 250 | -0.259 | [-0.564, 0.047] |
| rule_guided_double_Q_m1 | G1_dynamic_rule | normal | 250 | 0.023 | [0.006, 0.040] |
| rule_guided_double_Q_m1 | G1_dynamic_rule | high_volatility | 250 | 0.089 | [0.017, 0.161] |
| rule_guided_double_Q_m10 | G0_TWAP | normal | 250 | -0.006 | [-0.126, 0.113] |
| rule_guided_double_Q_m10 | G0_TWAP | high_volatility | 250 | -0.347 | [-0.627, -0.067] |
| rule_guided_double_Q_m10 | G1_dynamic_rule | normal | 250 | 0.000 | [-0.000, 0.001] |
| rule_guided_double_Q_m10 | G1_dynamic_rule | high_volatility | 250 | 0.000 | [-0.009, 0.009] |
| rule_guided_double_Q_m2 | G0_TWAP | normal | 250 | 0.005 | [-0.117, 0.126] |
| rule_guided_double_Q_m2 | G0_TWAP | high_volatility | 250 | -0.287 | [-0.581, 0.007] |
| rule_guided_double_Q_m2 | G1_dynamic_rule | normal | 250 | 0.011 | [-0.005, 0.027] |
| rule_guided_double_Q_m2 | G1_dynamic_rule | high_volatility | 250 | 0.060 | [0.010, 0.111] |
| rule_guided_double_Q_m5 | G0_TWAP | normal | 250 | 0.018 | [-0.108, 0.143] |
| rule_guided_double_Q_m5 | G0_TWAP | high_volatility | 250 | -0.338 | [-0.622, -0.054] |
| rule_guided_double_Q_m5 | G1_dynamic_rule | normal | 250 | 0.024 | [-0.000, 0.049] |
| rule_guided_double_Q_m5 | G1_dynamic_rule | high_volatility | 250 | 0.010 | [-0.024, 0.043] |
| selfplay_Q_A | G0_TWAP | normal | 250 | 1.125 | [0.829, 1.422] |
| selfplay_Q_A | G0_TWAP | high_volatility | 250 | 1.167 | [0.617, 1.717] |
| selfplay_Q_A | G1_dynamic_rule | normal | 250 | 1.132 | [0.809, 1.455] |
| selfplay_Q_A | G1_dynamic_rule | high_volatility | 250 | 1.514 | [0.835, 2.193] |

## 解释限制

本比较检验的是：A 的不同执行策略面对相同固定 B 规则时的表现。双边自博弈 Q 表是在另一个学习型 B 的训练分布中得到，再冻结到相同固定对手环境测试；此项衡量迁移表现。改进候选在固定规则对手混合分布中训练。规则策略若成本更低，应如实保留为结果，不因改进候选的训练设置而宣称 Q-learning 必然更优。
当前环境仍假设每个提交的子单全额成交，并以共同可行性下界保证母单在截止前可完成；因此 100% 完成率不是不同策略的区分性证据。
成本降低是该模拟设定下的结果，不意味着真实市场中同样有效。
