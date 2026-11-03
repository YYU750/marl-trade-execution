# 规则策略与 Q-learning 配对比较

- 运行参数：手续费 30 bp；成本对齐候选训练 5 个种子 × 1200 回合，阈值对齐双 Q 每个种子先用 2500 条规则轨迹初始化，再训练 10000 回合；每个固定 B 对手/场景 50 个配对评估种子。
- 固定 TWAP、动态规则、历史 G2/G3、当前双边自博弈 A 策略及改进候选 Q 策略均调用同一个 run_standard_benchmark.run_episode 市场模拟器。
- 每个 B 对手、波动场景和评估种子对所有 A 策略完全相同；策略随机数、对手随机数和市场冲击使用隔离随机流。费用、母单、期限、价差、冲击和成交假设相同。
- 改进候选使用紧凑的时间/执行进度状态编码、全部测试对手训练、成本对齐的 TD 奖励，并修复未尝试动作的零初始化 Q 值虚高问题。实际市场清算与评价口径没有改变。
- 阈值对齐双 Q 候选使用 5 步时间阶段、规则阈值对齐的状态边界、双 Q 表降低最大化偏差，并用训练集动态规则轨迹的 Monte Carlo 回报初始化；训练覆盖两种波动场景和全部固定对手。
- 成本差定义为学习策略减规则策略；负值有利于学习策略。区间是按配对评估种子计算的近似 95% 区间；训练种子先在同一评估种子内取均值。

## 各策略汇总

下表对五类固定 B 对手等权汇总，详细分层结果见 matched_comparison_summary.csv。

| A 策略 | 场景 | 平均成本 (bp) | 完成率 | 局数 |
|---|---|---:|---:|---:|
| G0_TWAP | high_volatility | 35.852 | 1.000 | 250 |
| G0_TWAP | normal | 38.295 | 1.000 | 250 |
| G1_dynamic_rule | high_volatility | 35.802 | 1.000 | 250 |
| G1_dynamic_rule | normal | 38.364 | 1.000 | 250 |
| G2_Q_learning_existing | high_volatility | 36.529 | 1.000 | 250 |
| G2_Q_learning_existing | normal | 39.645 | 1.000 | 250 |
| G3_opponent_aware_Q_existing | high_volatility | 36.279 | 1.000 | 250 |
| G3_opponent_aware_Q_existing | normal | 39.431 | 1.000 | 250 |
| cost_aligned_schedule_Q_run1 | high_volatility | 35.993 | 1.000 | 250 |
| cost_aligned_schedule_Q_run1 | normal | 39.147 | 1.000 | 250 |
| cost_aligned_schedule_Q_run2 | high_volatility | 35.992 | 1.000 | 250 |
| cost_aligned_schedule_Q_run2 | normal | 38.812 | 1.000 | 250 |
| cost_aligned_schedule_Q_run3 | high_volatility | 36.165 | 1.000 | 250 |
| cost_aligned_schedule_Q_run3 | normal | 39.011 | 1.000 | 250 |
| cost_aligned_schedule_Q_run4 | high_volatility | 35.916 | 1.000 | 250 |
| cost_aligned_schedule_Q_run4 | normal | 38.808 | 1.000 | 250 |
| cost_aligned_schedule_Q_run5 | high_volatility | 35.981 | 1.000 | 250 |
| cost_aligned_schedule_Q_run5 | normal | 39.076 | 1.000 | 250 |
| rule_guided_double_Q_m5_run1 | high_volatility | 35.807 | 1.000 | 250 |
| rule_guided_double_Q_m5_run1 | normal | 38.372 | 1.000 | 250 |
| rule_guided_double_Q_m5_run2 | high_volatility | 35.800 | 1.000 | 250 |
| rule_guided_double_Q_m5_run2 | normal | 38.380 | 1.000 | 250 |
| rule_guided_double_Q_m5_run3 | high_volatility | 35.801 | 1.000 | 250 |
| rule_guided_double_Q_m5_run3 | normal | 38.381 | 1.000 | 250 |
| rule_guided_double_Q_m5_run4 | high_volatility | 35.806 | 1.000 | 250 |
| rule_guided_double_Q_m5_run4 | normal | 38.381 | 1.000 | 250 |
| rule_guided_double_Q_m5_run5 | high_volatility | 35.818 | 1.000 | 250 |
| rule_guided_double_Q_m5_run5 | normal | 38.380 | 1.000 | 250 |
| selfplay_Q_A_run1 | high_volatility | 36.289 | 1.000 | 250 |
| selfplay_Q_A_run1 | normal | 39.200 | 1.000 | 250 |
| selfplay_Q_A_run2 | high_volatility | 36.197 | 1.000 | 250 |
| selfplay_Q_A_run2 | normal | 38.893 | 1.000 | 250 |
| selfplay_Q_A_run3 | high_volatility | 36.340 | 1.000 | 250 |
| selfplay_Q_A_run3 | normal | 39.147 | 1.000 | 250 |
| selfplay_Q_A_run4 | high_volatility | 36.257 | 1.000 | 250 |
| selfplay_Q_A_run4 | normal | 39.253 | 1.000 | 250 |
| selfplay_Q_A_run5 | high_volatility | 36.253 | 1.000 | 250 |
| selfplay_Q_A_run5 | normal | 39.275 | 1.000 | 250 |

## 配对成本差

| 学习策略 | 对照规则 | B 对手 | 场景 | 配对种子 | 成本差 (bp) | 近似 95% 区间 |
|---|---|---|---|---:|---:|---:|
| G2_Q_learning_existing | G0_TWAP | backloaded | high_volatility | 50 | 1.073 | [-1.022, 3.169] |
| G2_Q_learning_existing | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.038 | [-1.359, 3.435] |
| G2_Q_learning_existing | G0_TWAP | backloaded | normal | 50 | 1.218 | [0.005, 2.432] |
| G2_Q_learning_existing | G1_dynamic_rule | backloaded | normal | 50 | 1.059 | [-0.134, 2.253] |
| G2_Q_learning_existing | G0_TWAP | bursty | high_volatility | 50 | 2.170 | [0.064, 4.276] |
| G2_Q_learning_existing | G1_dynamic_rule | bursty | high_volatility | 50 | 2.325 | [0.233, 4.417] |
| G2_Q_learning_existing | G0_TWAP | bursty | normal | 50 | 1.914 | [0.790, 3.037] |
| G2_Q_learning_existing | G1_dynamic_rule | bursty | normal | 50 | 1.981 | [0.888, 3.074] |
| G2_Q_learning_existing | G0_TWAP | frontloaded | high_volatility | 50 | 0.264 | [-1.742, 2.270] |
| G2_Q_learning_existing | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.378 | [-1.978, 2.734] |
| G2_Q_learning_existing | G0_TWAP | frontloaded | normal | 50 | 1.787 | [0.633, 2.941] |
| G2_Q_learning_existing | G1_dynamic_rule | frontloaded | normal | 50 | 1.762 | [0.633, 2.892] |
| G2_Q_learning_existing | G0_TWAP | randomized | high_volatility | 50 | -1.968 | [-4.225, 0.289] |
| G2_Q_learning_existing | G1_dynamic_rule | randomized | high_volatility | 50 | -2.221 | [-5.237, 0.795] |
| G2_Q_learning_existing | G0_TWAP | randomized | normal | 50 | 0.713 | [-0.273, 1.698] |
| G2_Q_learning_existing | G1_dynamic_rule | randomized | normal | 50 | 0.640 | [-0.441, 1.722] |
| G2_Q_learning_existing | G0_TWAP | twap | high_volatility | 50 | 1.845 | [0.091, 3.599] |
| G2_Q_learning_existing | G1_dynamic_rule | twap | high_volatility | 50 | 2.114 | [0.188, 4.040] |
| G2_Q_learning_existing | G0_TWAP | twap | normal | 50 | 1.121 | [0.023, 2.219] |
| G2_Q_learning_existing | G1_dynamic_rule | twap | normal | 50 | 0.966 | [-0.300, 2.231] |
| G3_opponent_aware_Q_existing | G0_TWAP | backloaded | high_volatility | 50 | 1.082 | [-1.011, 3.175] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.047 | [-1.345, 3.438] |
| G3_opponent_aware_Q_existing | G0_TWAP | backloaded | normal | 50 | 1.303 | [0.067, 2.539] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | backloaded | normal | 50 | 1.144 | [-0.067, 2.354] |
| G3_opponent_aware_Q_existing | G0_TWAP | bursty | high_volatility | 50 | 0.754 | [-0.185, 1.693] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | bursty | high_volatility | 50 | 0.909 | [-0.025, 1.842] |
| G3_opponent_aware_Q_existing | G0_TWAP | bursty | normal | 50 | 0.890 | [0.420, 1.361] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | bursty | normal | 50 | 0.958 | [0.532, 1.384] |
| G3_opponent_aware_Q_existing | G0_TWAP | frontloaded | high_volatility | 50 | 0.117 | [-1.778, 2.012] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.231 | [-1.991, 2.454] |
| G3_opponent_aware_Q_existing | G0_TWAP | frontloaded | normal | 50 | 1.654 | [0.528, 2.779] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | frontloaded | normal | 50 | 1.630 | [0.534, 2.725] |
| G3_opponent_aware_Q_existing | G0_TWAP | randomized | high_volatility | 50 | -1.738 | [-3.782, 0.307] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | randomized | high_volatility | 50 | -1.990 | [-4.796, 0.815] |
| G3_opponent_aware_Q_existing | G0_TWAP | randomized | normal | 50 | 0.640 | [-0.246, 1.527] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | randomized | normal | 50 | 0.568 | [-0.420, 1.556] |
| G3_opponent_aware_Q_existing | G0_TWAP | twap | high_volatility | 50 | 1.923 | [0.136, 3.711] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | twap | high_volatility | 50 | 2.193 | [0.248, 4.138] |
| G3_opponent_aware_Q_existing | G0_TWAP | twap | normal | 50 | 1.192 | [0.074, 2.310] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | twap | normal | 50 | 1.037 | [-0.240, 2.314] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | backloaded | high_volatility | 50 | 0.128 | [-0.604, 0.860] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.092 | [-0.927, 1.112] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | backloaded | normal | 50 | 0.853 | [0.059, 1.646] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | backloaded | normal | 50 | 0.693 | [-0.068, 1.454] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | bursty | high_volatility | 50 | 1.079 | [-0.268, 2.426] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.234 | [-0.052, 2.520] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | bursty | normal | 50 | 1.150 | [0.486, 1.814] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | bursty | normal | 50 | 1.217 | [0.590, 1.844] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | frontloaded | high_volatility | 50 | 0.175 | [-1.085, 1.435] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.289 | [-1.059, 1.637] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | frontloaded | normal | 50 | 1.242 | [0.453, 2.032] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 1.218 | [0.513, 1.924] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | randomized | high_volatility | 50 | -1.332 | [-2.329, -0.334] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | -1.585 | [-3.232, 0.063] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | randomized | normal | 50 | 0.474 | [-0.106, 1.053] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | randomized | normal | 50 | 0.401 | [-0.233, 1.036] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | twap | high_volatility | 50 | 0.656 | [-0.252, 1.564] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | twap | high_volatility | 50 | 0.926 | [-0.010, 1.862] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | twap | normal | 50 | 0.544 | [-0.020, 1.108] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | twap | normal | 50 | 0.388 | [-0.295, 1.072] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | backloaded | high_volatility | 50 | 0.762 | [-0.114, 1.639] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.727 | [-0.204, 1.658] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | backloaded | normal | 50 | 0.384 | [-0.212, 0.979] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | backloaded | normal | 50 | 0.224 | [-0.361, 0.810] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | bursty | high_volatility | 50 | -0.347 | [-1.114, 0.421] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | -0.192 | [-1.326, 0.943] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | bursty | normal | 50 | 0.616 | [0.067, 1.165] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.683 | [0.065, 1.302] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | frontloaded | high_volatility | 50 | 0.278 | [-0.543, 1.099] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.392 | [-0.900, 1.684] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | frontloaded | normal | 50 | 0.657 | [0.127, 1.186] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.632 | [0.009, 1.256] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | randomized | high_volatility | 50 | -0.399 | [-1.002, 0.204] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | -0.652 | [-1.992, 0.688] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | randomized | normal | 50 | 0.480 | [-0.055, 1.015] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | randomized | normal | 50 | 0.408 | [-0.279, 1.094] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | twap | high_volatility | 50 | 0.405 | [-0.469, 1.278] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | twap | high_volatility | 50 | 0.674 | [-0.185, 1.533] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | twap | normal | 50 | 0.449 | [0.043, 0.856] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | twap | normal | 50 | 0.294 | [-0.291, 0.879] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | backloaded | high_volatility | 50 | 0.033 | [-0.901, 0.967] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | -0.002 | [-1.454, 1.450] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | backloaded | normal | 50 | 0.581 | [-0.138, 1.300] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | backloaded | normal | 50 | 0.422 | [-0.351, 1.194] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | bursty | high_volatility | 50 | 1.148 | [-0.230, 2.527] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.303 | [-0.075, 2.682] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | bursty | normal | 50 | 1.533 | [0.823, 2.244] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | bursty | normal | 50 | 1.601 | [0.911, 2.290] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | frontloaded | high_volatility | 50 | 0.201 | [-1.338, 1.741] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.316 | [-1.634, 2.265] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | frontloaded | normal | 50 | 1.048 | [0.156, 1.940] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 1.023 | [0.130, 1.917] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | randomized | high_volatility | 50 | -1.034 | [-2.510, 0.442] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | -1.287 | [-3.561, 0.988] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | randomized | normal | 50 | 0.416 | [-0.251, 1.082] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | randomized | normal | 50 | 0.343 | [-0.455, 1.142] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | twap | high_volatility | 50 | 1.218 | [0.210, 2.226] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | twap | high_volatility | 50 | 1.488 | [0.244, 2.732] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | twap | normal | 50 | 0.002 | [-0.634, 0.637] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | twap | normal | 50 | -0.154 | [-1.097, 0.789] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | backloaded | high_volatility | 50 | -0.347 | [-1.677, 0.983] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | -0.383 | [-2.081, 1.316] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | backloaded | normal | 50 | 0.861 | [-0.071, 1.792] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | backloaded | normal | 50 | 0.701 | [-0.230, 1.633] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | bursty | high_volatility | 50 | 0.278 | [-0.157, 0.713] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.433 | [-0.216, 1.082] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | bursty | normal | 50 | 0.482 | [0.209, 0.754] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.549 | [0.235, 0.864] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | frontloaded | high_volatility | 50 | 0.321 | [-0.656, 1.298] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.436 | [-0.701, 1.573] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | frontloaded | normal | 50 | 0.576 | [0.067, 1.086] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 0.552 | [0.074, 1.031] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | randomized | high_volatility | 50 | -1.066 | [-2.349, 0.217] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | -1.319 | [-3.261, 0.623] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | randomized | normal | 50 | 0.182 | [-0.265, 0.628] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | randomized | normal | 50 | 0.109 | [-0.496, 0.715] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | twap | high_volatility | 50 | 1.134 | [0.083, 2.184] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 1.403 | [0.183, 2.623] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | twap | normal | 50 | 0.465 | [-0.197, 1.127] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | twap | normal | 50 | 0.309 | [-0.598, 1.216] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | backloaded | high_volatility | 50 | -0.124 | [-1.343, 1.095] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | -0.159 | [-1.894, 1.576] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | backloaded | normal | 50 | 0.901 | [-0.036, 1.839] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | backloaded | normal | 50 | 0.742 | [-0.221, 1.705] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | bursty | high_volatility | 50 | 0.240 | [-0.982, 1.463] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.395 | [-0.875, 1.666] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | bursty | normal | 50 | 0.874 | [0.360, 1.389] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.942 | [0.425, 1.459] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | frontloaded | high_volatility | 50 | 0.180 | [-1.399, 1.759] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.295 | [-1.618, 2.207] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | frontloaded | normal | 50 | 1.253 | [0.536, 1.971] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 1.229 | [0.515, 1.943] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | randomized | high_volatility | 50 | -1.392 | [-2.834, 0.051] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | -1.645 | [-3.809, 0.520] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | randomized | normal | 50 | 0.603 | [-0.118, 1.325] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | randomized | normal | 50 | 0.531 | [-0.314, 1.376] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | twap | high_volatility | 50 | 1.741 | [0.703, 2.778] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | twap | high_volatility | 50 | 2.010 | [0.708, 3.313] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | twap | normal | 50 | 0.274 | [-0.432, 0.980] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | twap | normal | 50 | 0.118 | [-0.889, 1.126] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | backloaded | high_volatility | 50 | 0.076 | [-0.604, 0.756] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.041 | [-0.090, 0.171] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | backloaded | normal | 50 | 0.191 | [-0.007, 0.390] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | backloaded | normal | 50 | 0.032 | [-0.014, 0.078] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | bursty | high_volatility | 50 | -0.155 | [-0.681, 0.371] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | bursty | normal | 50 | -0.067 | [-0.273, 0.139] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | frontloaded | high_volatility | 50 | -0.100 | [-0.783, 0.584] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.015 | [-0.072, 0.101] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | frontloaded | normal | 50 | 0.029 | [-0.186, 0.245] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 0.005 | [-0.006, 0.016] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | randomized | high_volatility | 50 | 0.224 | [-0.773, 1.221] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | -0.029 | [-0.061, 0.004] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | randomized | normal | 50 | 0.076 | [-0.196, 0.348] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | randomized | normal | 50 | 0.004 | [-0.016, 0.023] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | twap | high_volatility | 50 | -0.270 | [-0.788, 0.249] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | twap | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | twap | normal | 50 | 0.156 | [-0.244, 0.555] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | twap | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | backloaded | high_volatility | 50 | 0.055 | [-0.621, 0.731] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.020 | [-0.089, 0.129] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | backloaded | normal | 50 | 0.191 | [-0.007, 0.390] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | backloaded | normal | 50 | 0.032 | [-0.013, 0.078] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | bursty | high_volatility | 50 | -0.155 | [-0.681, 0.371] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | bursty | normal | 50 | -0.067 | [-0.273, 0.139] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | frontloaded | high_volatility | 50 | -0.124 | [-0.801, 0.553] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | -0.010 | [-0.073, 0.054] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | frontloaded | normal | 50 | 0.043 | [-0.174, 0.261] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.019 | [-0.025, 0.063] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | randomized | high_volatility | 50 | 0.235 | [-0.762, 1.232] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | -0.018 | [-0.046, 0.011] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | randomized | normal | 50 | 0.102 | [-0.175, 0.378] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | randomized | normal | 50 | 0.030 | [-0.013, 0.072] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | twap | high_volatility | 50 | -0.270 | [-0.788, 0.249] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | twap | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | twap | normal | 50 | 0.156 | [-0.244, 0.555] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | twap | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | backloaded | high_volatility | 50 | 0.026 | [-0.636, 0.687] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | -0.009 | [-0.030, 0.011] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | backloaded | normal | 50 | 0.191 | [-0.008, 0.389] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | backloaded | normal | 50 | 0.031 | [-0.014, 0.077] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | bursty | high_volatility | 50 | -0.155 | [-0.681, 0.371] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | bursty | normal | 50 | -0.067 | [-0.273, 0.139] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | frontloaded | high_volatility | 50 | -0.106 | [-0.785, 0.574] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.009 | [-0.059, 0.076] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | frontloaded | normal | 50 | 0.043 | [-0.176, 0.262] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 0.019 | [-0.027, 0.065] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | randomized | high_volatility | 50 | 0.253 | [-0.743, 1.249] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.000 | [-0.007, 0.007] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | randomized | normal | 50 | 0.106 | [-0.170, 0.383] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | randomized | normal | 50 | 0.034 | [-0.012, 0.080] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | twap | high_volatility | 50 | -0.270 | [-0.788, 0.249] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | twap | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | twap | normal | 50 | 0.156 | [-0.244, 0.555] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | twap | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | backloaded | high_volatility | 50 | 0.065 | [-0.610, 0.739] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.029 | [-0.080, 0.139] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | backloaded | normal | 50 | 0.191 | [-0.007, 0.390] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | backloaded | normal | 50 | 0.032 | [-0.013, 0.078] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | bursty | high_volatility | 50 | -0.155 | [-0.681, 0.371] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | bursty | normal | 50 | -0.067 | [-0.273, 0.139] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | frontloaded | high_volatility | 50 | -0.102 | [-0.785, 0.580] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.012 | [-0.074, 0.097] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | frontloaded | normal | 50 | 0.029 | [-0.186, 0.245] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 0.005 | [-0.006, 0.016] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | randomized | high_volatility | 50 | 0.232 | [-0.765, 1.229] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | -0.021 | [-0.050, 0.009] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | randomized | normal | 50 | 0.076 | [-0.196, 0.348] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | randomized | normal | 50 | 0.004 | [-0.016, 0.023] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | twap | high_volatility | 50 | -0.270 | [-0.788, 0.249] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | twap | normal | 50 | 0.202 | [-0.202, 0.605] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | twap | normal | 50 | 0.046 | [0.008, 0.084] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | backloaded | high_volatility | 50 | 0.069 | [-0.604, 0.742] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.034 | [-0.065, 0.132] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | backloaded | normal | 50 | 0.189 | [-0.009, 0.388] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | backloaded | normal | 50 | 0.030 | [-0.015, 0.075] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | bursty | high_volatility | 50 | -0.155 | [-0.681, 0.371] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | bursty | normal | 50 | -0.067 | [-0.273, 0.139] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | frontloaded | high_volatility | 50 | -0.103 | [-0.786, 0.579] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.011 | [-0.074, 0.096] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | frontloaded | normal | 50 | 0.044 | [-0.175, 0.263] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 0.020 | [-0.025, 0.065] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | randomized | high_volatility | 50 | 0.233 | [-0.764, 1.230] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | -0.020 | [-0.050, 0.010] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | randomized | normal | 50 | 0.103 | [-0.174, 0.379] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | randomized | normal | 50 | 0.031 | [-0.015, 0.076] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | twap | high_volatility | 50 | -0.212 | [-0.743, 0.318] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | twap | high_volatility | 50 | 0.057 | [-0.000, 0.114] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | twap | normal | 50 | 0.156 | [-0.244, 0.555] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | twap | normal | 50 | 0.000 | [0.000, 0.000] |
| selfplay_Q_A_run1 | G0_TWAP | backloaded | high_volatility | 50 | 0.857 | [-0.587, 2.301] |
| selfplay_Q_A_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.821 | [-0.941, 2.584] |
| selfplay_Q_A_run1 | G0_TWAP | backloaded | normal | 50 | 0.826 | [0.026, 1.627] |
| selfplay_Q_A_run1 | G1_dynamic_rule | backloaded | normal | 50 | 0.667 | [-0.128, 1.461] |
| selfplay_Q_A_run1 | G0_TWAP | bursty | high_volatility | 50 | 1.316 | [-0.248, 2.879] |
| selfplay_Q_A_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.471 | [-0.096, 3.037] |
| selfplay_Q_A_run1 | G0_TWAP | bursty | normal | 50 | 1.573 | [0.645, 2.502] |
| selfplay_Q_A_run1 | G1_dynamic_rule | bursty | normal | 50 | 1.641 | [0.728, 2.553] |
| selfplay_Q_A_run1 | G0_TWAP | frontloaded | high_volatility | 50 | 0.250 | [-0.903, 1.403] |
| selfplay_Q_A_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.364 | [-1.160, 1.888] |
| selfplay_Q_A_run1 | G0_TWAP | frontloaded | normal | 50 | 0.937 | [0.185, 1.688] |
| selfplay_Q_A_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 0.912 | [0.120, 1.704] |
| selfplay_Q_A_run1 | G0_TWAP | randomized | high_volatility | 50 | -1.339 | [-2.789, 0.112] |
| selfplay_Q_A_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | -1.592 | [-3.803, 0.620] |
| selfplay_Q_A_run1 | G0_TWAP | randomized | normal | 50 | 0.493 | [-0.167, 1.152] |
| selfplay_Q_A_run1 | G1_dynamic_rule | randomized | normal | 50 | 0.421 | [-0.370, 1.212] |
| selfplay_Q_A_run1 | G0_TWAP | twap | high_volatility | 50 | 1.104 | [-0.047, 2.256] |
| selfplay_Q_A_run1 | G1_dynamic_rule | twap | high_volatility | 50 | 1.374 | [0.056, 2.692] |
| selfplay_Q_A_run1 | G0_TWAP | twap | normal | 50 | 0.696 | [-0.063, 1.455] |
| selfplay_Q_A_run1 | G1_dynamic_rule | twap | normal | 50 | 0.541 | [-0.439, 1.520] |
| selfplay_Q_A_run2 | G0_TWAP | backloaded | high_volatility | 50 | 0.962 | [-0.194, 2.117] |
| selfplay_Q_A_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.926 | [-0.673, 2.526] |
| selfplay_Q_A_run2 | G0_TWAP | backloaded | normal | 50 | 0.398 | [-0.279, 1.076] |
| selfplay_Q_A_run2 | G1_dynamic_rule | backloaded | normal | 50 | 0.239 | [-0.463, 0.941] |
| selfplay_Q_A_run2 | G0_TWAP | bursty | high_volatility | 50 | 0.441 | [-0.626, 1.507] |
| selfplay_Q_A_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.596 | [-0.521, 1.712] |
| selfplay_Q_A_run2 | G0_TWAP | bursty | normal | 50 | 1.089 | [0.205, 1.972] |
| selfplay_Q_A_run2 | G1_dynamic_rule | bursty | normal | 50 | 1.156 | [0.304, 2.008] |
| selfplay_Q_A_run2 | G0_TWAP | frontloaded | high_volatility | 50 | 0.044 | [-0.834, 0.922] |
| selfplay_Q_A_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.158 | [-1.228, 1.544] |
| selfplay_Q_A_run2 | G0_TWAP | frontloaded | normal | 50 | 0.742 | [0.055, 1.429] |
| selfplay_Q_A_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.718 | [0.002, 1.434] |
| selfplay_Q_A_run2 | G0_TWAP | randomized | high_volatility | 50 | -0.521 | [-1.663, 0.622] |
| selfplay_Q_A_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | -0.774 | [-2.592, 1.045] |
| selfplay_Q_A_run2 | G0_TWAP | randomized | normal | 50 | 0.501 | [-0.074, 1.076] |
| selfplay_Q_A_run2 | G1_dynamic_rule | randomized | normal | 50 | 0.428 | [-0.286, 1.143] |
| selfplay_Q_A_run2 | G0_TWAP | twap | high_volatility | 50 | 0.802 | [-0.187, 1.791] |
| selfplay_Q_A_run2 | G1_dynamic_rule | twap | high_volatility | 50 | 1.071 | [-0.239, 2.382] |
| selfplay_Q_A_run2 | G0_TWAP | twap | normal | 50 | 0.263 | [-0.432, 0.957] |
| selfplay_Q_A_run2 | G1_dynamic_rule | twap | normal | 50 | 0.107 | [-0.898, 1.112] |
| selfplay_Q_A_run3 | G0_TWAP | backloaded | high_volatility | 50 | 1.056 | [-0.292, 2.404] |
| selfplay_Q_A_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.021 | [-0.595, 2.637] |
| selfplay_Q_A_run3 | G0_TWAP | backloaded | normal | 50 | 0.902 | [0.024, 1.781] |
| selfplay_Q_A_run3 | G1_dynamic_rule | backloaded | normal | 50 | 0.743 | [-0.120, 1.606] |
| selfplay_Q_A_run3 | G0_TWAP | bursty | high_volatility | 50 | 1.176 | [-0.230, 2.582] |
| selfplay_Q_A_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.331 | [-0.049, 2.711] |
| selfplay_Q_A_run3 | G0_TWAP | bursty | normal | 50 | 1.464 | [0.565, 2.363] |
| selfplay_Q_A_run3 | G1_dynamic_rule | bursty | normal | 50 | 1.531 | [0.648, 2.415] |
| selfplay_Q_A_run3 | G0_TWAP | frontloaded | high_volatility | 50 | 0.373 | [-0.741, 1.487] |
| selfplay_Q_A_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.487 | [-1.057, 2.031] |
| selfplay_Q_A_run3 | G0_TWAP | frontloaded | normal | 50 | 0.889 | [0.172, 1.607] |
| selfplay_Q_A_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 0.865 | [0.122, 1.608] |
| selfplay_Q_A_run3 | G0_TWAP | randomized | high_volatility | 50 | -1.395 | [-2.909, 0.118] |
| selfplay_Q_A_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | -1.648 | [-3.988, 0.692] |
| selfplay_Q_A_run3 | G0_TWAP | randomized | normal | 50 | 0.325 | [-0.295, 0.946] |
| selfplay_Q_A_run3 | G1_dynamic_rule | randomized | normal | 50 | 0.253 | [-0.509, 1.015] |
| selfplay_Q_A_run3 | G0_TWAP | twap | high_volatility | 50 | 1.234 | [0.079, 2.388] |
| selfplay_Q_A_run3 | G1_dynamic_rule | twap | high_volatility | 50 | 1.503 | [0.117, 2.889] |
| selfplay_Q_A_run3 | G0_TWAP | twap | normal | 50 | 0.681 | [-0.043, 1.405] |
| selfplay_Q_A_run3 | G1_dynamic_rule | twap | normal | 50 | 0.525 | [-0.457, 1.507] |
| selfplay_Q_A_run4 | G0_TWAP | backloaded | high_volatility | 50 | 0.761 | [-0.700, 2.221] |
| selfplay_Q_A_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.725 | [-1.077, 2.528] |
| selfplay_Q_A_run4 | G0_TWAP | backloaded | normal | 50 | 1.067 | [0.151, 1.983] |
| selfplay_Q_A_run4 | G1_dynamic_rule | backloaded | normal | 50 | 0.908 | [0.009, 1.807] |
| selfplay_Q_A_run4 | G0_TWAP | bursty | high_volatility | 50 | 1.026 | [-0.167, 2.219] |
| selfplay_Q_A_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.181 | [-0.108, 2.470] |
| selfplay_Q_A_run4 | G0_TWAP | bursty | normal | 50 | 1.276 | [0.492, 2.060] |
| selfplay_Q_A_run4 | G1_dynamic_rule | bursty | normal | 50 | 1.344 | [0.557, 2.131] |
| selfplay_Q_A_run4 | G0_TWAP | frontloaded | high_volatility | 50 | 0.026 | [-1.395, 1.446] |
| selfplay_Q_A_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.140 | [-1.592, 1.871] |
| selfplay_Q_A_run4 | G0_TWAP | frontloaded | normal | 50 | 1.098 | [0.194, 2.003] |
| selfplay_Q_A_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 1.074 | [0.190, 1.959] |
| selfplay_Q_A_run4 | G0_TWAP | randomized | high_volatility | 50 | -1.217 | [-2.709, 0.275] |
| selfplay_Q_A_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | -1.470 | [-3.744, 0.804] |
| selfplay_Q_A_run4 | G0_TWAP | randomized | normal | 50 | 0.497 | [-0.205, 1.198] |
| selfplay_Q_A_run4 | G1_dynamic_rule | randomized | normal | 50 | 0.424 | [-0.405, 1.254] |
| selfplay_Q_A_run4 | G0_TWAP | twap | high_volatility | 50 | 1.431 | [0.130, 2.732] |
| selfplay_Q_A_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 1.701 | [0.214, 3.187] |
| selfplay_Q_A_run4 | G0_TWAP | twap | normal | 50 | 0.854 | [0.010, 1.698] |
| selfplay_Q_A_run4 | G1_dynamic_rule | twap | normal | 50 | 0.698 | [-0.354, 1.751] |
| selfplay_Q_A_run5 | G0_TWAP | backloaded | high_volatility | 50 | 1.003 | [-0.790, 2.795] |
| selfplay_Q_A_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.967 | [-1.157, 3.091] |
| selfplay_Q_A_run5 | G0_TWAP | backloaded | normal | 50 | 1.044 | [0.014, 2.074] |
| selfplay_Q_A_run5 | G1_dynamic_rule | backloaded | normal | 50 | 0.885 | [-0.139, 1.908] |
| selfplay_Q_A_run5 | G0_TWAP | bursty | high_volatility | 50 | 0.827 | [-0.314, 1.967] |
| selfplay_Q_A_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.982 | [-0.189, 2.153] |
| selfplay_Q_A_run5 | G0_TWAP | bursty | normal | 50 | 1.269 | [0.461, 2.077] |
| selfplay_Q_A_run5 | G1_dynamic_rule | bursty | normal | 50 | 1.337 | [0.546, 2.128] |
| selfplay_Q_A_run5 | G0_TWAP | frontloaded | high_volatility | 50 | -0.327 | [-1.911, 1.257] |
| selfplay_Q_A_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | -0.213 | [-2.032, 1.607] |
| selfplay_Q_A_run5 | G0_TWAP | frontloaded | normal | 50 | 1.253 | [0.254, 2.252] |
| selfplay_Q_A_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 1.229 | [0.279, 2.179] |
| selfplay_Q_A_run5 | G0_TWAP | randomized | high_volatility | 50 | -1.304 | [-3.087, 0.478] |
| selfplay_Q_A_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | -1.557 | [-4.095, 0.980] |
| selfplay_Q_A_run5 | G0_TWAP | randomized | normal | 50 | 0.530 | [-0.257, 1.317] |
| selfplay_Q_A_run5 | G1_dynamic_rule | randomized | normal | 50 | 0.458 | [-0.439, 1.355] |
| selfplay_Q_A_run5 | G0_TWAP | twap | high_volatility | 50 | 1.808 | [0.306, 3.310] |
| selfplay_Q_A_run5 | G1_dynamic_rule | twap | high_volatility | 50 | 2.077 | [0.379, 3.775] |
| selfplay_Q_A_run5 | G0_TWAP | twap | normal | 50 | 0.806 | [-0.082, 1.695] |
| selfplay_Q_A_run5 | G1_dynamic_rule | twap | normal | 50 | 0.651 | [-0.449, 1.751] |

## 汇总配对差

下表将五类固定 B 对手和 50 个评估种子作为 250 个配对测试格；学习策略的 5 个训练种子先在格内取均值。成本差为学习策略减规则策略。

| 学习策略 | 规则基线 | 场景 | 配对格数 | 平均成本差 (bp) | 近似 95% 区间 |
|---|---|---|---:|---:|---:|
| G2_Q_learning_existing | G0_TWAP | normal | 250 | 1.351 | [0.852, 1.849] |
| G2_Q_learning_existing | G0_TWAP | high_volatility | 250 | 0.677 | [-0.251, 1.605] |
| G2_Q_learning_existing | G1_dynamic_rule | normal | 250 | 1.282 | [0.766, 1.798] |
| G2_Q_learning_existing | G1_dynamic_rule | high_volatility | 250 | 0.727 | [-0.351, 1.805] |
| G3_opponent_aware_Q_existing | G0_TWAP | normal | 250 | 1.136 | [0.688, 1.584] |
| G3_opponent_aware_Q_existing | G0_TWAP | high_volatility | 250 | 0.428 | [-0.386, 1.241] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | normal | 250 | 1.067 | [0.602, 1.532] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | high_volatility | 250 | 0.478 | [-0.493, 1.448] |
| cost_aligned_schedule_Q | G0_TWAP | normal | 250 | 0.676 | [0.427, 0.925] |
| cost_aligned_schedule_Q | G0_TWAP | high_volatility | 250 | 0.158 | [-0.238, 0.554] |
| cost_aligned_schedule_Q | G1_dynamic_rule | normal | 250 | 0.607 | [0.319, 0.895] |
| cost_aligned_schedule_Q | G1_dynamic_rule | high_volatility | 250 | 0.208 | [-0.370, 0.785] |
| rule_guided_double_Q_m5 | G0_TWAP | normal | 250 | 0.084 | [-0.036, 0.204] |
| rule_guided_double_Q_m5 | G0_TWAP | high_volatility | 250 | -0.045 | [-0.357, 0.266] |
| rule_guided_double_Q_m5 | G1_dynamic_rule | normal | 250 | 0.015 | [0.002, 0.027] |
| rule_guided_double_Q_m5 | G1_dynamic_rule | high_volatility | 250 | 0.005 | [-0.019, 0.029] |
| selfplay_Q_A | G0_TWAP | normal | 250 | 0.859 | [0.515, 1.203] |
| selfplay_Q_A | G0_TWAP | high_volatility | 250 | 0.416 | [-0.155, 0.986] |
| selfplay_Q_A | G1_dynamic_rule | normal | 250 | 0.790 | [0.413, 1.167] |
| selfplay_Q_A | G1_dynamic_rule | high_volatility | 250 | 0.466 | [-0.276, 1.207] |

## 解释限制

本比较检验的是：A 的不同执行策略面对相同固定 B 规则时的表现。双边自博弈 Q 表是在另一个学习型 B 的训练分布中得到，再冻结到相同固定对手环境测试；此项衡量迁移表现。改进候选在固定规则对手混合分布中训练。规则策略若成本更低，应如实保留为结果，不因改进候选的训练设置而宣称 Q-learning 必然更优。
当前环境仍假设每个提交的子单全额成交，并以共同可行性下界保证母单在截止前可完成；因此 100% 完成率不是不同策略的区分性证据。
成本降低是该模拟设定下的结果，不意味着真实市场中同样有效。
