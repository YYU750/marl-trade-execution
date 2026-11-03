# 规则策略与 Q-learning 配对比较

- 运行参数：手续费 30 bp；改进候选训练 5 个种子 × 1200 回合；每个固定 B 对手/场景 50 个配对评估种子。
- 固定 TWAP、动态规则、历史 G2/G3、当前双边自博弈 A 策略及改进候选 Q 策略均调用同一个 run_standard_benchmark.run_episode 市场模拟器。
- 每个 B 对手、波动场景和评估种子对所有 A 策略完全相同；策略随机数、对手随机数和市场冲击使用隔离随机流。费用、母单、期限、价差、冲击和成交假设相同。
- 改进候选使用紧凑的时间/执行进度状态编码、全部测试对手训练、成本对齐的 TD 奖励，并修复未尝试动作的零初始化 Q 值虚高问题。实际市场清算与评价口径没有改变。
- 成本差定义为学习策略减规则策略；负值有利于学习策略。区间是按配对评估种子计算的近似 95% 区间；训练种子先在同一评估种子内取均值。

## 各策略汇总

下表对五类固定 B 对手等权汇总，详细分层结果见 matched_comparison_summary.csv。

| A 策略 | 场景 | 平均成本 (bp) | 完成率 | 局数 |
|---|---|---:|---:|---:|
| G0_TWAP | high_volatility | 39.120 | 1.000 | 250 |
| G0_TWAP | normal | 38.504 | 1.000 | 250 |
| G1_dynamic_rule | high_volatility | 38.724 | 1.000 | 250 |
| G1_dynamic_rule | normal | 38.453 | 1.000 | 250 |
| G2_Q_learning_existing | high_volatility | 41.180 | 1.000 | 250 |
| G2_Q_learning_existing | normal | 40.047 | 1.000 | 250 |
| G3_opponent_aware_Q_existing | high_volatility | 40.857 | 1.000 | 250 |
| G3_opponent_aware_Q_existing | normal | 39.850 | 1.000 | 250 |
| cost_aligned_schedule_Q_run1 | high_volatility | 40.280 | 1.000 | 250 |
| cost_aligned_schedule_Q_run1 | normal | 39.580 | 1.000 | 250 |
| cost_aligned_schedule_Q_run2 | high_volatility | 39.949 | 1.000 | 250 |
| cost_aligned_schedule_Q_run2 | normal | 39.084 | 1.000 | 250 |
| cost_aligned_schedule_Q_run3 | high_volatility | 39.836 | 1.000 | 250 |
| cost_aligned_schedule_Q_run3 | normal | 39.320 | 1.000 | 250 |
| cost_aligned_schedule_Q_run4 | high_volatility | 39.903 | 1.000 | 250 |
| cost_aligned_schedule_Q_run4 | normal | 39.275 | 1.000 | 250 |
| cost_aligned_schedule_Q_run5 | high_volatility | 39.553 | 1.000 | 250 |
| cost_aligned_schedule_Q_run5 | normal | 38.920 | 1.000 | 250 |
| selfplay_Q_A_run1 | high_volatility | 40.408 | 1.000 | 250 |
| selfplay_Q_A_run1 | normal | 39.670 | 1.000 | 250 |
| selfplay_Q_A_run2 | high_volatility | 40.046 | 1.000 | 250 |
| selfplay_Q_A_run2 | normal | 39.254 | 1.000 | 250 |
| selfplay_Q_A_run3 | high_volatility | 40.437 | 1.000 | 250 |
| selfplay_Q_A_run3 | normal | 39.661 | 1.000 | 250 |
| selfplay_Q_A_run4 | high_volatility | 40.398 | 1.000 | 250 |
| selfplay_Q_A_run4 | normal | 39.741 | 1.000 | 250 |
| selfplay_Q_A_run5 | high_volatility | 40.654 | 1.000 | 250 |
| selfplay_Q_A_run5 | normal | 39.843 | 1.000 | 250 |

## 配对成本差

| 学习策略 | 对照规则 | B 对手 | 场景 | 配对种子 | 成本差 (bp) | 近似 95% 区间 |
|---|---|---|---|---:|---:|---:|
| G2_Q_learning_existing | G0_TWAP | backloaded | high_volatility | 50 | 2.592 | [0.924, 4.261] |
| G2_Q_learning_existing | G1_dynamic_rule | backloaded | high_volatility | 50 | 3.283 | [1.401, 5.165] |
| G2_Q_learning_existing | G0_TWAP | backloaded | normal | 50 | 1.656 | [0.734, 2.578] |
| G2_Q_learning_existing | G1_dynamic_rule | backloaded | normal | 50 | 1.825 | [0.892, 2.758] |
| G2_Q_learning_existing | G0_TWAP | bursty | high_volatility | 50 | 1.849 | [-0.388, 4.087] |
| G2_Q_learning_existing | G1_dynamic_rule | bursty | high_volatility | 50 | 2.048 | [-0.338, 4.435] |
| G2_Q_learning_existing | G0_TWAP | bursty | normal | 50 | 1.568 | [0.684, 2.452] |
| G2_Q_learning_existing | G1_dynamic_rule | bursty | normal | 50 | 1.732 | [0.872, 2.592] |
| G2_Q_learning_existing | G0_TWAP | frontloaded | high_volatility | 50 | 3.006 | [1.270, 4.741] |
| G2_Q_learning_existing | G1_dynamic_rule | frontloaded | high_volatility | 50 | 3.469 | [1.800, 5.138] |
| G2_Q_learning_existing | G0_TWAP | frontloaded | normal | 50 | 1.918 | [0.821, 3.015] |
| G2_Q_learning_existing | G1_dynamic_rule | frontloaded | normal | 50 | 1.672 | [0.500, 2.843] |
| G2_Q_learning_existing | G0_TWAP | randomized | high_volatility | 50 | 1.282 | [-0.897, 3.461] |
| G2_Q_learning_existing | G1_dynamic_rule | randomized | high_volatility | 50 | 1.646 | [-0.966, 4.259] |
| G2_Q_learning_existing | G0_TWAP | randomized | normal | 50 | 1.821 | [0.725, 2.917] |
| G2_Q_learning_existing | G1_dynamic_rule | randomized | normal | 50 | 1.900 | [0.787, 3.013] |
| G2_Q_learning_existing | G0_TWAP | twap | high_volatility | 50 | 1.571 | [-0.636, 3.777] |
| G2_Q_learning_existing | G1_dynamic_rule | twap | high_volatility | 50 | 1.834 | [-0.658, 4.327] |
| G2_Q_learning_existing | G0_TWAP | twap | normal | 50 | 0.749 | [-0.231, 1.729] |
| G2_Q_learning_existing | G1_dynamic_rule | twap | normal | 50 | 0.837 | [-0.188, 1.862] |
| G3_opponent_aware_Q_existing | G0_TWAP | backloaded | high_volatility | 50 | 2.378 | [0.707, 4.050] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | backloaded | high_volatility | 50 | 3.069 | [1.178, 4.960] |
| G3_opponent_aware_Q_existing | G0_TWAP | backloaded | normal | 50 | 1.620 | [0.699, 2.542] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | backloaded | normal | 50 | 1.789 | [0.854, 2.724] |
| G3_opponent_aware_Q_existing | G0_TWAP | bursty | high_volatility | 50 | 0.786 | [-0.153, 1.724] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | bursty | high_volatility | 50 | 0.985 | [-0.150, 2.120] |
| G3_opponent_aware_Q_existing | G0_TWAP | bursty | normal | 50 | 0.765 | [0.344, 1.186] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | bursty | normal | 50 | 0.929 | [0.510, 1.347] |
| G3_opponent_aware_Q_existing | G0_TWAP | frontloaded | high_volatility | 50 | 2.844 | [1.176, 4.511] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | frontloaded | high_volatility | 50 | 3.307 | [1.707, 4.906] |
| G3_opponent_aware_Q_existing | G0_TWAP | frontloaded | normal | 50 | 1.887 | [0.842, 2.932] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | frontloaded | normal | 50 | 1.641 | [0.531, 2.751] |
| G3_opponent_aware_Q_existing | G0_TWAP | randomized | high_volatility | 50 | 1.105 | [-0.874, 3.084] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | randomized | high_volatility | 50 | 1.469 | [-0.938, 3.877] |
| G3_opponent_aware_Q_existing | G0_TWAP | randomized | normal | 50 | 1.730 | [0.700, 2.759] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | randomized | normal | 50 | 1.808 | [0.765, 2.852] |
| G3_opponent_aware_Q_existing | G0_TWAP | twap | high_volatility | 50 | 1.570 | [-0.680, 3.820] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | twap | high_volatility | 50 | 1.834 | [-0.691, 4.358] |
| G3_opponent_aware_Q_existing | G0_TWAP | twap | normal | 50 | 0.726 | [-0.255, 1.708] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | twap | normal | 50 | 0.815 | [-0.212, 1.841] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | backloaded | high_volatility | 50 | 1.512 | [0.189, 2.836] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 2.203 | [0.693, 3.713] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | backloaded | normal | 50 | 1.172 | [0.571, 1.773] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | backloaded | normal | 50 | 1.341 | [0.775, 1.906] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | bursty | high_volatility | 50 | 0.884 | [-0.144, 1.912] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.083 | [-0.238, 2.405] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | bursty | normal | 50 | 1.050 | [0.454, 1.647] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | bursty | normal | 50 | 1.214 | [0.567, 1.860] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | frontloaded | high_volatility | 50 | 2.180 | [0.710, 3.651] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 2.644 | [1.220, 4.067] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | frontloaded | normal | 50 | 1.681 | [0.758, 2.605] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 1.435 | [0.446, 2.424] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | randomized | high_volatility | 50 | 0.530 | [-0.854, 1.915] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.894 | [-0.937, 2.726] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | randomized | normal | 50 | 1.259 | [0.435, 2.083] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | randomized | normal | 50 | 1.338 | [0.491, 2.185] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | twap | high_volatility | 50 | 0.692 | [-0.980, 2.364] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | twap | high_volatility | 50 | 0.956 | [-0.939, 2.851] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | twap | normal | 50 | 0.217 | [-0.424, 0.859] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | twap | normal | 50 | 0.306 | [-0.365, 0.976] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | backloaded | high_volatility | 50 | 1.208 | [-0.027, 2.442] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.898 | [0.502, 3.295] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | backloaded | normal | 50 | 1.357 | [0.663, 2.050] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | backloaded | normal | 50 | 1.525 | [0.791, 2.260] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | bursty | high_volatility | 50 | 0.596 | [-0.083, 1.275] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.795 | [-0.347, 1.937] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | bursty | normal | 50 | 0.502 | [0.204, 0.799] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.665 | [0.193, 1.137] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | frontloaded | high_volatility | 50 | 0.729 | [0.131, 1.328] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.193 | [0.333, 2.052] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | frontloaded | normal | 50 | 0.423 | [-0.109, 0.954] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.177 | [-0.512, 0.865] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | randomized | high_volatility | 50 | 0.569 | [-0.545, 1.683] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.933 | [-0.734, 2.601] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | randomized | normal | 50 | 0.199 | [-0.361, 0.759] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | randomized | normal | 50 | 0.278 | [-0.458, 1.014] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | twap | high_volatility | 50 | 1.039 | [-0.393, 2.472] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | twap | high_volatility | 50 | 1.303 | [-0.435, 3.042] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | twap | normal | 50 | 0.419 | [-0.305, 1.142] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | twap | normal | 50 | 0.507 | [-0.290, 1.304] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | backloaded | high_volatility | 50 | 1.035 | [-0.138, 2.209] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.726 | [0.538, 2.914] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | backloaded | normal | 50 | 1.323 | [0.574, 2.072] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | backloaded | normal | 50 | 1.492 | [0.743, 2.241] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | bursty | high_volatility | 50 | 0.561 | [-0.134, 1.256] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.760 | [-0.105, 1.625] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | bursty | normal | 50 | 0.487 | [0.017, 0.957] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.651 | [0.158, 1.144] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | frontloaded | high_volatility | 50 | 0.642 | [-0.255, 1.540] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.106 | [-0.018, 2.229] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | frontloaded | normal | 50 | 0.915 | [0.273, 1.556] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 0.668 | [-0.104, 1.440] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | randomized | high_volatility | 50 | 0.294 | [-0.690, 1.279] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.658 | [-0.821, 2.138] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | randomized | normal | 50 | 0.761 | [0.083, 1.439] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | randomized | normal | 50 | 0.840 | [0.146, 1.534] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | twap | high_volatility | 50 | 1.044 | [-0.579, 2.666] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | twap | high_volatility | 50 | 1.308 | [-0.507, 3.122] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | twap | normal | 50 | 0.592 | [-0.171, 1.355] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | twap | normal | 50 | 0.681 | [-0.116, 1.477] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | backloaded | high_volatility | 50 | 1.309 | [0.690, 1.929] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 2.000 | [1.085, 2.914] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | backloaded | normal | 50 | 1.195 | [0.485, 1.905] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | backloaded | normal | 50 | 1.364 | [0.638, 2.089] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | bursty | high_volatility | 50 | 0.596 | [0.035, 1.157] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.795 | [-0.198, 1.788] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | bursty | normal | 50 | 0.539 | [0.156, 0.921] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.702 | [0.211, 1.193] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | frontloaded | high_volatility | 50 | 1.226 | [0.278, 2.175] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.689 | [0.648, 2.731] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | frontloaded | normal | 50 | 0.721 | [0.041, 1.402] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 0.475 | [-0.357, 1.307] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | randomized | high_volatility | 50 | 0.396 | [-0.427, 1.219] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.760 | [-0.596, 2.117] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | randomized | normal | 50 | 0.750 | [0.077, 1.422] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | randomized | normal | 50 | 0.828 | [0.028, 1.629] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | twap | high_volatility | 50 | 0.386 | [-0.795, 1.568] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 0.650 | [-0.861, 2.161] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | twap | normal | 50 | 0.651 | [-0.013, 1.316] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | twap | normal | 50 | 0.739 | [0.027, 1.452] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | backloaded | high_volatility | 50 | 0.183 | [-0.283, 0.649] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.873 | [-0.021, 1.767] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | backloaded | normal | 50 | 0.036 | [-0.345, 0.416] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | backloaded | normal | 50 | 0.205 | [-0.270, 0.679] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | bursty | high_volatility | 50 | 0.641 | [-0.150, 1.432] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.840 | [-0.335, 2.015] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | bursty | normal | 50 | 0.672 | [0.327, 1.018] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.836 | [0.396, 1.275] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | frontloaded | high_volatility | 50 | 0.781 | [-0.036, 1.599] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.244 | [0.154, 2.335] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | frontloaded | normal | 50 | 0.879 | [0.289, 1.469] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 0.633 | [-0.101, 1.366] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | randomized | high_volatility | 50 | 0.467 | [-0.432, 1.366] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.831 | [-0.630, 2.293] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | randomized | normal | 50 | 0.380 | [-0.129, 0.888] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | randomized | normal | 50 | 0.459 | [-0.170, 1.087] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | twap | high_volatility | 50 | 0.092 | [-0.638, 0.821] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | twap | high_volatility | 50 | 0.356 | [-0.785, 1.496] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | twap | normal | 50 | 0.116 | [-0.278, 0.509] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | twap | normal | 50 | 0.204 | [-0.301, 0.708] |
| selfplay_Q_A_run1 | G0_TWAP | backloaded | high_volatility | 50 | 1.380 | [0.358, 2.403] |
| selfplay_Q_A_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 2.071 | [0.918, 3.223] |
| selfplay_Q_A_run1 | G0_TWAP | backloaded | normal | 50 | 1.495 | [0.834, 2.156] |
| selfplay_Q_A_run1 | G1_dynamic_rule | backloaded | normal | 50 | 1.664 | [0.948, 2.379] |
| selfplay_Q_A_run1 | G0_TWAP | bursty | high_volatility | 50 | 1.471 | [-0.228, 3.170] |
| selfplay_Q_A_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.670 | [-0.205, 3.544] |
| selfplay_Q_A_run1 | G0_TWAP | bursty | normal | 50 | 1.421 | [0.737, 2.105] |
| selfplay_Q_A_run1 | G1_dynamic_rule | bursty | normal | 50 | 1.584 | [0.892, 2.277] |
| selfplay_Q_A_run1 | G0_TWAP | frontloaded | high_volatility | 50 | 1.861 | [0.713, 3.009] |
| selfplay_Q_A_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 2.324 | [1.173, 3.475] |
| selfplay_Q_A_run1 | G0_TWAP | frontloaded | normal | 50 | 1.278 | [0.656, 1.899] |
| selfplay_Q_A_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 1.032 | [0.290, 1.773] |
| selfplay_Q_A_run1 | G0_TWAP | randomized | high_volatility | 50 | 0.685 | [-0.751, 2.121] |
| selfplay_Q_A_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.049 | [-0.818, 2.916] |
| selfplay_Q_A_run1 | G0_TWAP | randomized | normal | 50 | 1.195 | [0.472, 1.918] |
| selfplay_Q_A_run1 | G1_dynamic_rule | randomized | normal | 50 | 1.273 | [0.506, 2.041] |
| selfplay_Q_A_run1 | G0_TWAP | twap | high_volatility | 50 | 1.041 | [-0.423, 2.505] |
| selfplay_Q_A_run1 | G1_dynamic_rule | twap | high_volatility | 50 | 1.305 | [-0.484, 3.093] |
| selfplay_Q_A_run1 | G0_TWAP | twap | normal | 50 | 0.441 | [-0.193, 1.075] |
| selfplay_Q_A_run1 | G1_dynamic_rule | twap | normal | 50 | 0.529 | [-0.202, 1.260] |
| selfplay_Q_A_run2 | G0_TWAP | backloaded | high_volatility | 50 | 1.171 | [0.241, 2.101] |
| selfplay_Q_A_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.861 | [0.445, 3.277] |
| selfplay_Q_A_run2 | G0_TWAP | backloaded | normal | 50 | 0.617 | [0.106, 1.129] |
| selfplay_Q_A_run2 | G1_dynamic_rule | backloaded | normal | 50 | 0.786 | [0.114, 1.458] |
| selfplay_Q_A_run2 | G0_TWAP | bursty | high_volatility | 50 | 1.013 | [-0.004, 2.031] |
| selfplay_Q_A_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.212 | [0.092, 2.333] |
| selfplay_Q_A_run2 | G0_TWAP | bursty | normal | 50 | 1.193 | [0.523, 1.863] |
| selfplay_Q_A_run2 | G1_dynamic_rule | bursty | normal | 50 | 1.356 | [0.698, 2.015] |
| selfplay_Q_A_run2 | G0_TWAP | frontloaded | high_volatility | 50 | 0.740 | [0.077, 1.402] |
| selfplay_Q_A_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.203 | [0.330, 2.076] |
| selfplay_Q_A_run2 | G0_TWAP | frontloaded | normal | 50 | 1.018 | [0.470, 1.565] |
| selfplay_Q_A_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.772 | [0.059, 1.484] |
| selfplay_Q_A_run2 | G0_TWAP | randomized | high_volatility | 50 | 0.474 | [-0.523, 1.471] |
| selfplay_Q_A_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.838 | [-0.613, 2.290] |
| selfplay_Q_A_run2 | G0_TWAP | randomized | normal | 50 | 0.780 | [0.171, 1.389] |
| selfplay_Q_A_run2 | G1_dynamic_rule | randomized | normal | 50 | 0.859 | [0.210, 1.508] |
| selfplay_Q_A_run2 | G0_TWAP | twap | high_volatility | 50 | 1.229 | [0.050, 2.408] |
| selfplay_Q_A_run2 | G1_dynamic_rule | twap | high_volatility | 50 | 1.493 | [-0.157, 3.143] |
| selfplay_Q_A_run2 | G0_TWAP | twap | normal | 50 | 0.140 | [-0.501, 0.781] |
| selfplay_Q_A_run2 | G1_dynamic_rule | twap | normal | 50 | 0.229 | [-0.585, 1.042] |
| selfplay_Q_A_run3 | G0_TWAP | backloaded | high_volatility | 50 | 1.793 | [0.676, 2.910] |
| selfplay_Q_A_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | 2.484 | [1.089, 3.878] |
| selfplay_Q_A_run3 | G0_TWAP | backloaded | normal | 50 | 1.605 | [0.950, 2.260] |
| selfplay_Q_A_run3 | G1_dynamic_rule | backloaded | normal | 50 | 1.774 | [1.047, 2.501] |
| selfplay_Q_A_run3 | G0_TWAP | bursty | high_volatility | 50 | 1.240 | [-0.320, 2.800] |
| selfplay_Q_A_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.439 | [-0.312, 3.191] |
| selfplay_Q_A_run3 | G0_TWAP | bursty | normal | 50 | 1.423 | [0.751, 2.096] |
| selfplay_Q_A_run3 | G1_dynamic_rule | bursty | normal | 50 | 1.587 | [0.901, 2.273] |
| selfplay_Q_A_run3 | G0_TWAP | frontloaded | high_volatility | 50 | 1.493 | [0.443, 2.544] |
| selfplay_Q_A_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.957 | [0.845, 3.068] |
| selfplay_Q_A_run3 | G0_TWAP | frontloaded | normal | 50 | 1.113 | [0.403, 1.823] |
| selfplay_Q_A_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 0.867 | [0.029, 1.705] |
| selfplay_Q_A_run3 | G0_TWAP | randomized | high_volatility | 50 | 0.844 | [-0.454, 2.141] |
| selfplay_Q_A_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.208 | [-0.646, 3.062] |
| selfplay_Q_A_run3 | G0_TWAP | randomized | normal | 50 | 0.986 | [0.265, 1.707] |
| selfplay_Q_A_run3 | G1_dynamic_rule | randomized | normal | 50 | 1.065 | [0.274, 1.855] |
| selfplay_Q_A_run3 | G0_TWAP | twap | high_volatility | 50 | 1.211 | [-0.263, 2.685] |
| selfplay_Q_A_run3 | G1_dynamic_rule | twap | high_volatility | 50 | 1.475 | [-0.392, 3.342] |
| selfplay_Q_A_run3 | G0_TWAP | twap | normal | 50 | 0.655 | [-0.005, 1.314] |
| selfplay_Q_A_run3 | G1_dynamic_rule | twap | normal | 50 | 0.743 | [-0.037, 1.523] |
| selfplay_Q_A_run4 | G0_TWAP | backloaded | high_volatility | 50 | 1.640 | [0.375, 2.905] |
| selfplay_Q_A_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 2.331 | [0.825, 3.837] |
| selfplay_Q_A_run4 | G0_TWAP | backloaded | normal | 50 | 1.619 | [0.918, 2.321] |
| selfplay_Q_A_run4 | G1_dynamic_rule | backloaded | normal | 50 | 1.788 | [1.036, 2.540] |
| selfplay_Q_A_run4 | G0_TWAP | bursty | high_volatility | 50 | 0.974 | [-0.312, 2.260] |
| selfplay_Q_A_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.173 | [-0.379, 2.726] |
| selfplay_Q_A_run4 | G0_TWAP | bursty | normal | 50 | 1.186 | [0.602, 1.771] |
| selfplay_Q_A_run4 | G1_dynamic_rule | bursty | normal | 50 | 1.350 | [0.728, 1.971] |
| selfplay_Q_A_run4 | G0_TWAP | frontloaded | high_volatility | 50 | 1.845 | [0.465, 3.226] |
| selfplay_Q_A_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 2.308 | [0.968, 3.648] |
| selfplay_Q_A_run4 | G0_TWAP | frontloaded | normal | 50 | 1.613 | [0.766, 2.461] |
| selfplay_Q_A_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 1.367 | [0.439, 2.296] |
| selfplay_Q_A_run4 | G0_TWAP | randomized | high_volatility | 50 | 0.809 | [-0.506, 2.125] |
| selfplay_Q_A_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.174 | [-0.668, 3.015] |
| selfplay_Q_A_run4 | G0_TWAP | randomized | normal | 50 | 1.272 | [0.473, 2.070] |
| selfplay_Q_A_run4 | G1_dynamic_rule | randomized | normal | 50 | 1.350 | [0.505, 2.195] |
| selfplay_Q_A_run4 | G0_TWAP | twap | high_volatility | 50 | 1.118 | [-0.515, 2.751] |
| selfplay_Q_A_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 1.382 | [-0.628, 3.392] |
| selfplay_Q_A_run4 | G0_TWAP | twap | normal | 50 | 0.494 | [-0.231, 1.219] |
| selfplay_Q_A_run4 | G1_dynamic_rule | twap | normal | 50 | 0.583 | [-0.229, 1.394] |
| selfplay_Q_A_run5 | G0_TWAP | backloaded | high_volatility | 50 | 2.249 | [0.786, 3.712] |
| selfplay_Q_A_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | 2.939 | [1.216, 4.662] |
| selfplay_Q_A_run5 | G0_TWAP | backloaded | normal | 50 | 1.609 | [0.860, 2.359] |
| selfplay_Q_A_run5 | G1_dynamic_rule | backloaded | normal | 50 | 1.778 | [0.975, 2.581] |
| selfplay_Q_A_run5 | G0_TWAP | bursty | high_volatility | 50 | 1.114 | [-0.070, 2.298] |
| selfplay_Q_A_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.313 | [-0.091, 2.717] |
| selfplay_Q_A_run5 | G0_TWAP | bursty | normal | 50 | 1.306 | [0.674, 1.937] |
| selfplay_Q_A_run5 | G1_dynamic_rule | bursty | normal | 50 | 1.469 | [0.828, 2.111] |
| selfplay_Q_A_run5 | G0_TWAP | frontloaded | high_volatility | 50 | 2.061 | [0.594, 3.528] |
| selfplay_Q_A_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 2.524 | [1.116, 3.932] |
| selfplay_Q_A_run5 | G0_TWAP | frontloaded | normal | 50 | 1.805 | [0.940, 2.671] |
| selfplay_Q_A_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 1.559 | [0.644, 2.475] |
| selfplay_Q_A_run5 | G0_TWAP | randomized | high_volatility | 50 | 0.707 | [-0.880, 2.294] |
| selfplay_Q_A_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.071 | [-0.928, 3.070] |
| selfplay_Q_A_run5 | G0_TWAP | randomized | normal | 50 | 1.427 | [0.531, 2.323] |
| selfplay_Q_A_run5 | G1_dynamic_rule | randomized | normal | 50 | 1.505 | [0.595, 2.415] |
| selfplay_Q_A_run5 | G0_TWAP | twap | high_volatility | 50 | 1.535 | [-0.426, 3.496] |
| selfplay_Q_A_run5 | G1_dynamic_rule | twap | high_volatility | 50 | 1.799 | [-0.476, 4.075] |
| selfplay_Q_A_run5 | G0_TWAP | twap | normal | 50 | 0.549 | [-0.258, 1.356] |
| selfplay_Q_A_run5 | G1_dynamic_rule | twap | normal | 50 | 0.637 | [-0.258, 1.533] |

## 汇总配对差

下表将五类固定 B 对手和 50 个评估种子作为 250 个配对测试格；学习策略的 5 个训练种子先在格内取均值。成本差为学习策略减规则策略。

| 学习策略 | 规则基线 | 场景 | 配对格数 | 平均成本差 (bp) | 近似 95% 区间 |
|---|---|---|---:|---:|---:|
| G2_Q_learning_existing | G0_TWAP | normal | 250 | 1.542 | [1.096, 1.989] |
| G2_Q_learning_existing | G0_TWAP | high_volatility | 250 | 2.060 | [1.160, 2.960] |
| G2_Q_learning_existing | G1_dynamic_rule | normal | 250 | 1.593 | [1.135, 2.051] |
| G2_Q_learning_existing | G1_dynamic_rule | high_volatility | 250 | 2.456 | [1.459, 3.454] |
| G3_opponent_aware_Q_existing | G0_TWAP | normal | 250 | 1.346 | [0.937, 1.754] |
| G3_opponent_aware_Q_existing | G0_TWAP | high_volatility | 250 | 1.737 | [0.951, 2.522] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | normal | 250 | 1.396 | [0.976, 1.817] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | high_volatility | 250 | 2.133 | [1.247, 3.018] |
| cost_aligned_schedule_Q | G0_TWAP | normal | 250 | 0.732 | [0.507, 0.957] |
| cost_aligned_schedule_Q | G0_TWAP | high_volatility | 250 | 0.784 | [0.420, 1.147] |
| cost_aligned_schedule_Q | G1_dynamic_rule | normal | 250 | 0.782 | [0.519, 1.046] |
| cost_aligned_schedule_Q | G1_dynamic_rule | high_volatility | 250 | 1.180 | [0.660, 1.700] |
| selfplay_Q_A | G0_TWAP | normal | 250 | 1.130 | [0.835, 1.424] |
| selfplay_Q_A | G0_TWAP | high_volatility | 250 | 1.268 | [0.710, 1.826] |
| selfplay_Q_A | G1_dynamic_rule | normal | 250 | 1.180 | [0.853, 1.507] |
| selfplay_Q_A | G1_dynamic_rule | high_volatility | 250 | 1.664 | [0.976, 2.352] |

## 解释限制

本比较检验的是：A 的不同执行策略面对相同固定 B 规则时的表现。双边自博弈 Q 表是在另一个学习型 B 的训练分布中得到，再冻结到相同固定对手环境测试；此项衡量迁移表现。改进候选在固定规则对手混合分布中训练。规则策略若成本更低，应如实保留为结果，不因改进候选的训练设置而宣称 Q-learning 必然更优。
当前环境仍假设每个提交的子单全额成交，并以共同可行性下界保证母单在截止前可完成；因此 100% 完成率不是不同策略的区分性证据。
成本降低是该模拟设定下的结果，不意味着真实市场中同样有效。
