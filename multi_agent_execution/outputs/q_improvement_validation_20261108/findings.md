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
| G0_TWAP | high_volatility | 39.318 | 1.000 | 250 |
| G0_TWAP | normal | 38.949 | 1.000 | 250 |
| G1_dynamic_rule | high_volatility | 38.945 | 1.000 | 250 |
| G1_dynamic_rule | normal | 38.914 | 1.000 | 250 |
| G2_Q_learning_existing | high_volatility | 41.853 | 1.000 | 250 |
| G2_Q_learning_existing | normal | 40.457 | 1.000 | 250 |
| G3_opponent_aware_Q_existing | high_volatility | 41.665 | 1.000 | 250 |
| G3_opponent_aware_Q_existing | normal | 40.385 | 1.000 | 250 |
| cost_aligned_schedule_Q_run1 | high_volatility | 40.332 | 1.000 | 250 |
| cost_aligned_schedule_Q_run1 | normal | 39.850 | 1.000 | 250 |
| cost_aligned_schedule_Q_run2 | high_volatility | 39.889 | 1.000 | 250 |
| cost_aligned_schedule_Q_run2 | normal | 39.646 | 1.000 | 250 |
| cost_aligned_schedule_Q_run3 | high_volatility | 40.530 | 1.000 | 250 |
| cost_aligned_schedule_Q_run3 | normal | 39.706 | 1.000 | 250 |
| cost_aligned_schedule_Q_run4 | high_volatility | 40.259 | 1.000 | 250 |
| cost_aligned_schedule_Q_run4 | normal | 39.810 | 1.000 | 250 |
| cost_aligned_schedule_Q_run5 | high_volatility | 40.565 | 1.000 | 250 |
| cost_aligned_schedule_Q_run5 | normal | 40.024 | 1.000 | 250 |
| rule_guided_double_Q_m0.1_run1 | high_volatility | 39.626 | 1.000 | 250 |
| rule_guided_double_Q_m0.1_run1 | normal | 39.185 | 1.000 | 250 |
| rule_guided_double_Q_m0.1_run2 | high_volatility | 39.872 | 1.000 | 250 |
| rule_guided_double_Q_m0.1_run2 | normal | 39.194 | 1.000 | 250 |
| rule_guided_double_Q_m0.1_run3 | high_volatility | 39.882 | 1.000 | 250 |
| rule_guided_double_Q_m0.1_run3 | normal | 39.295 | 1.000 | 250 |
| rule_guided_double_Q_m0.1_run4 | high_volatility | 39.814 | 1.000 | 250 |
| rule_guided_double_Q_m0.1_run4 | normal | 39.210 | 1.000 | 250 |
| rule_guided_double_Q_m0.1_run5 | high_volatility | 39.785 | 1.000 | 250 |
| rule_guided_double_Q_m0.1_run5 | normal | 39.284 | 1.000 | 250 |
| rule_guided_double_Q_m0.25_run1 | high_volatility | 39.570 | 1.000 | 250 |
| rule_guided_double_Q_m0.25_run1 | normal | 39.183 | 1.000 | 250 |
| rule_guided_double_Q_m0.25_run2 | high_volatility | 39.698 | 1.000 | 250 |
| rule_guided_double_Q_m0.25_run2 | normal | 39.230 | 1.000 | 250 |
| rule_guided_double_Q_m0.25_run3 | high_volatility | 39.811 | 1.000 | 250 |
| rule_guided_double_Q_m0.25_run3 | normal | 39.297 | 1.000 | 250 |
| rule_guided_double_Q_m0.25_run4 | high_volatility | 39.651 | 1.000 | 250 |
| rule_guided_double_Q_m0.25_run4 | normal | 39.212 | 1.000 | 250 |
| rule_guided_double_Q_m0.25_run5 | high_volatility | 39.769 | 1.000 | 250 |
| rule_guided_double_Q_m0.25_run5 | normal | 39.297 | 1.000 | 250 |
| rule_guided_double_Q_m0.5_run1 | high_volatility | 39.436 | 1.000 | 250 |
| rule_guided_double_Q_m0.5_run1 | normal | 39.165 | 1.000 | 250 |
| rule_guided_double_Q_m0.5_run2 | high_volatility | 39.536 | 1.000 | 250 |
| rule_guided_double_Q_m0.5_run2 | normal | 39.224 | 1.000 | 250 |
| rule_guided_double_Q_m0.5_run3 | high_volatility | 39.736 | 1.000 | 250 |
| rule_guided_double_Q_m0.5_run3 | normal | 39.246 | 1.000 | 250 |
| rule_guided_double_Q_m0.5_run4 | high_volatility | 39.474 | 1.000 | 250 |
| rule_guided_double_Q_m0.5_run4 | normal | 39.205 | 1.000 | 250 |
| rule_guided_double_Q_m0.5_run5 | high_volatility | 39.600 | 1.000 | 250 |
| rule_guided_double_Q_m0.5_run5 | normal | 39.290 | 1.000 | 250 |
| rule_guided_double_Q_m0_run1 | high_volatility | 39.639 | 1.000 | 250 |
| rule_guided_double_Q_m0_run1 | normal | 39.185 | 1.000 | 250 |
| rule_guided_double_Q_m0_run2 | high_volatility | 39.846 | 1.000 | 250 |
| rule_guided_double_Q_m0_run2 | normal | 39.201 | 1.000 | 250 |
| rule_guided_double_Q_m0_run3 | high_volatility | 39.907 | 1.000 | 250 |
| rule_guided_double_Q_m0_run3 | normal | 39.282 | 1.000 | 250 |
| rule_guided_double_Q_m0_run4 | high_volatility | 39.847 | 1.000 | 250 |
| rule_guided_double_Q_m0_run4 | normal | 39.228 | 1.000 | 250 |
| rule_guided_double_Q_m0_run5 | high_volatility | 39.878 | 1.000 | 250 |
| rule_guided_double_Q_m0_run5 | normal | 39.284 | 1.000 | 250 |
| rule_guided_double_Q_m1_run1 | high_volatility | 39.132 | 1.000 | 250 |
| rule_guided_double_Q_m1_run1 | normal | 38.958 | 1.000 | 250 |
| rule_guided_double_Q_m1_run2 | high_volatility | 39.020 | 1.000 | 250 |
| rule_guided_double_Q_m1_run2 | normal | 38.979 | 1.000 | 250 |
| rule_guided_double_Q_m1_run3 | high_volatility | 39.010 | 1.000 | 250 |
| rule_guided_double_Q_m1_run3 | normal | 38.956 | 1.000 | 250 |
| rule_guided_double_Q_m1_run4 | high_volatility | 39.025 | 1.000 | 250 |
| rule_guided_double_Q_m1_run4 | normal | 38.962 | 1.000 | 250 |
| rule_guided_double_Q_m1_run5 | high_volatility | 39.121 | 1.000 | 250 |
| rule_guided_double_Q_m1_run5 | normal | 38.956 | 1.000 | 250 |
| rule_guided_double_Q_m2_run1 | high_volatility | 38.964 | 1.000 | 250 |
| rule_guided_double_Q_m2_run1 | normal | 38.928 | 1.000 | 250 |
| rule_guided_double_Q_m2_run2 | high_volatility | 38.955 | 1.000 | 250 |
| rule_guided_double_Q_m2_run2 | normal | 38.947 | 1.000 | 250 |
| rule_guided_double_Q_m2_run3 | high_volatility | 38.969 | 1.000 | 250 |
| rule_guided_double_Q_m2_run3 | normal | 38.935 | 1.000 | 250 |
| rule_guided_double_Q_m2_run4 | high_volatility | 38.964 | 1.000 | 250 |
| rule_guided_double_Q_m2_run4 | normal | 38.933 | 1.000 | 250 |
| rule_guided_double_Q_m2_run5 | high_volatility | 38.961 | 1.000 | 250 |
| rule_guided_double_Q_m2_run5 | normal | 38.947 | 1.000 | 250 |
| rule_guided_double_Q_m5_run1 | high_volatility | 38.975 | 1.000 | 250 |
| rule_guided_double_Q_m5_run1 | normal | 38.922 | 1.000 | 250 |
| rule_guided_double_Q_m5_run2 | high_volatility | 38.962 | 1.000 | 250 |
| rule_guided_double_Q_m5_run2 | normal | 38.936 | 1.000 | 250 |
| rule_guided_double_Q_m5_run3 | high_volatility | 38.949 | 1.000 | 250 |
| rule_guided_double_Q_m5_run3 | normal | 38.936 | 1.000 | 250 |
| rule_guided_double_Q_m5_run4 | high_volatility | 38.971 | 1.000 | 250 |
| rule_guided_double_Q_m5_run4 | normal | 38.931 | 1.000 | 250 |
| rule_guided_double_Q_m5_run5 | high_volatility | 38.959 | 1.000 | 250 |
| rule_guided_double_Q_m5_run5 | normal | 38.936 | 1.000 | 250 |
| selfplay_Q_A_run1 | high_volatility | 40.766 | 1.000 | 250 |
| selfplay_Q_A_run1 | normal | 39.881 | 1.000 | 250 |
| selfplay_Q_A_run2 | high_volatility | 40.316 | 1.000 | 250 |
| selfplay_Q_A_run2 | normal | 39.711 | 1.000 | 250 |
| selfplay_Q_A_run3 | high_volatility | 40.836 | 1.000 | 250 |
| selfplay_Q_A_run3 | normal | 39.819 | 1.000 | 250 |
| selfplay_Q_A_run4 | high_volatility | 41.046 | 1.000 | 250 |
| selfplay_Q_A_run4 | normal | 40.100 | 1.000 | 250 |
| selfplay_Q_A_run5 | high_volatility | 41.311 | 1.000 | 250 |
| selfplay_Q_A_run5 | normal | 40.229 | 1.000 | 250 |

## 配对成本差

| 学习策略 | 对照规则 | B 对手 | 场景 | 配对种子 | 成本差 (bp) | 近似 95% 区间 |
|---|---|---|---|---:|---:|---:|
| G2_Q_learning_existing | G0_TWAP | backloaded | high_volatility | 50 | 2.991 | [0.610, 5.373] |
| G2_Q_learning_existing | G1_dynamic_rule | backloaded | high_volatility | 50 | 2.780 | [0.255, 5.306] |
| G2_Q_learning_existing | G0_TWAP | backloaded | normal | 50 | 1.692 | [0.716, 2.668] |
| G2_Q_learning_existing | G1_dynamic_rule | backloaded | normal | 50 | 1.694 | [0.725, 2.663] |
| G2_Q_learning_existing | G0_TWAP | bursty | high_volatility | 50 | 1.203 | [-0.943, 3.349] |
| G2_Q_learning_existing | G1_dynamic_rule | bursty | high_volatility | 50 | 1.642 | [-0.637, 3.921] |
| G2_Q_learning_existing | G0_TWAP | bursty | normal | 50 | 0.638 | [-0.325, 1.600] |
| G2_Q_learning_existing | G1_dynamic_rule | bursty | normal | 50 | 0.613 | [-0.365, 1.592] |
| G2_Q_learning_existing | G0_TWAP | frontloaded | high_volatility | 50 | 2.692 | [0.642, 4.743] |
| G2_Q_learning_existing | G1_dynamic_rule | frontloaded | high_volatility | 50 | 2.996 | [0.754, 5.237] |
| G2_Q_learning_existing | G0_TWAP | frontloaded | normal | 50 | 2.316 | [1.381, 3.251] |
| G2_Q_learning_existing | G1_dynamic_rule | frontloaded | normal | 50 | 2.278 | [1.345, 3.210] |
| G2_Q_learning_existing | G0_TWAP | randomized | high_volatility | 50 | 3.059 | [1.148, 4.970] |
| G2_Q_learning_existing | G1_dynamic_rule | randomized | high_volatility | 50 | 3.839 | [1.482, 6.196] |
| G2_Q_learning_existing | G0_TWAP | randomized | normal | 50 | 0.756 | [-0.178, 1.689] |
| G2_Q_learning_existing | G1_dynamic_rule | randomized | normal | 50 | 0.891 | [-0.038, 1.819] |
| G2_Q_learning_existing | G0_TWAP | twap | high_volatility | 50 | 2.733 | [1.024, 4.443] |
| G2_Q_learning_existing | G1_dynamic_rule | twap | high_volatility | 50 | 3.285 | [1.515, 5.056] |
| G2_Q_learning_existing | G0_TWAP | twap | normal | 50 | 2.139 | [1.264, 3.014] |
| G2_Q_learning_existing | G1_dynamic_rule | twap | normal | 50 | 2.238 | [1.423, 3.053] |
| G3_opponent_aware_Q_existing | G0_TWAP | backloaded | high_volatility | 50 | 3.112 | [0.729, 5.494] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | backloaded | high_volatility | 50 | 2.901 | [0.378, 5.424] |
| G3_opponent_aware_Q_existing | G0_TWAP | backloaded | normal | 50 | 1.660 | [0.648, 2.672] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | backloaded | normal | 50 | 1.662 | [0.664, 2.661] |
| G3_opponent_aware_Q_existing | G0_TWAP | bursty | high_volatility | 50 | 0.362 | [-0.601, 1.326] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | bursty | high_volatility | 50 | 0.801 | [-0.369, 1.972] |
| G3_opponent_aware_Q_existing | G0_TWAP | bursty | normal | 50 | 0.307 | [-0.131, 0.745] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | bursty | normal | 50 | 0.283 | [-0.178, 0.743] |
| G3_opponent_aware_Q_existing | G0_TWAP | frontloaded | high_volatility | 50 | 2.754 | [0.759, 4.750] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | frontloaded | high_volatility | 50 | 3.057 | [0.883, 5.232] |
| G3_opponent_aware_Q_existing | G0_TWAP | frontloaded | normal | 50 | 2.276 | [1.336, 3.217] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | frontloaded | normal | 50 | 2.238 | [1.305, 3.171] |
| G3_opponent_aware_Q_existing | G0_TWAP | randomized | high_volatility | 50 | 2.744 | [1.005, 4.483] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | randomized | high_volatility | 50 | 3.525 | [1.346, 5.704] |
| G3_opponent_aware_Q_existing | G0_TWAP | randomized | normal | 50 | 0.783 | [-0.056, 1.621] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | randomized | normal | 50 | 0.918 | [0.083, 1.753] |
| G3_opponent_aware_Q_existing | G0_TWAP | twap | high_volatility | 50 | 2.762 | [1.013, 4.511] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | twap | high_volatility | 50 | 3.314 | [1.515, 5.113] |
| G3_opponent_aware_Q_existing | G0_TWAP | twap | normal | 50 | 2.158 | [1.236, 3.081] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | twap | normal | 50 | 2.257 | [1.401, 3.114] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | backloaded | high_volatility | 50 | 0.705 | [-0.296, 1.706] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.494 | [-0.640, 1.629] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | backloaded | normal | 50 | 0.826 | [0.124, 1.528] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | backloaded | normal | 50 | 0.828 | [0.120, 1.536] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | bursty | high_volatility | 50 | 0.677 | [-0.728, 2.082] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.116 | [-0.490, 2.722] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | bursty | normal | 50 | 0.559 | [-0.044, 1.161] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | bursty | normal | 50 | 0.534 | [-0.084, 1.153] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | frontloaded | high_volatility | 50 | 1.508 | [-0.000, 3.017] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.812 | [0.365, 3.258] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | frontloaded | normal | 50 | 1.432 | [0.627, 2.237] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 1.394 | [0.656, 2.132] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | randomized | high_volatility | 50 | 1.431 | [0.374, 2.487] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 2.211 | [1.000, 3.422] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | randomized | normal | 50 | 0.572 | [-0.038, 1.182] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | randomized | normal | 50 | 0.707 | [0.086, 1.328] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | twap | high_volatility | 50 | 0.752 | [-0.133, 1.637] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | twap | high_volatility | 50 | 1.304 | [0.450, 2.159] |
| cost_aligned_schedule_Q_run1 | G0_TWAP | twap | normal | 50 | 1.119 | [0.457, 1.781] |
| cost_aligned_schedule_Q_run1 | G1_dynamic_rule | twap | normal | 50 | 1.218 | [0.644, 1.792] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | backloaded | high_volatility | 50 | 0.675 | [-0.340, 1.691] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.465 | [-0.612, 1.541] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | backloaded | normal | 50 | 0.821 | [0.230, 1.412] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | backloaded | normal | 50 | 0.823 | [0.203, 1.443] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | bursty | high_volatility | 50 | 1.311 | [0.438, 2.183] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.750 | [0.507, 2.992] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | bursty | normal | 50 | 0.338 | [-0.092, 0.769] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.314 | [-0.242, 0.870] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | frontloaded | high_volatility | 50 | 0.533 | [-0.193, 1.259] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.836 | [-0.455, 2.127] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | frontloaded | normal | 50 | 1.067 | [0.588, 1.547] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 1.029 | [0.455, 1.603] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | randomized | high_volatility | 50 | 0.614 | [0.088, 1.139] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.394 | [0.394, 2.395] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | randomized | normal | 50 | 0.482 | [-0.034, 0.997] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | randomized | normal | 50 | 0.617 | [0.064, 1.170] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | twap | high_volatility | 50 | -0.277 | [-0.967, 0.412] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | twap | high_volatility | 50 | 0.274 | [-0.429, 0.978] |
| cost_aligned_schedule_Q_run2 | G0_TWAP | twap | normal | 50 | 0.781 | [0.219, 1.343] |
| cost_aligned_schedule_Q_run2 | G1_dynamic_rule | twap | normal | 50 | 0.880 | [0.369, 1.391] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | backloaded | high_volatility | 50 | -0.551 | [-1.553, 0.452] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | -0.761 | [-2.264, 0.741] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | backloaded | normal | 50 | 0.711 | [0.031, 1.391] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | backloaded | normal | 50 | 0.713 | [-0.016, 1.441] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | bursty | high_volatility | 50 | 1.078 | [-0.385, 2.540] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.517 | [-0.108, 3.142] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | bursty | normal | 50 | 0.252 | [-0.353, 0.857] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.228 | [-0.420, 0.875] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | frontloaded | high_volatility | 50 | 2.084 | [0.441, 3.727] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 2.387 | [0.454, 4.319] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | frontloaded | normal | 50 | 1.701 | [0.959, 2.442] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 1.662 | [0.889, 2.436] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | randomized | high_volatility | 50 | 2.686 | [1.390, 3.981] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 3.466 | [1.732, 5.201] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | randomized | normal | 50 | 0.460 | [-0.208, 1.128] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | randomized | normal | 50 | 0.595 | [-0.097, 1.288] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | twap | high_volatility | 50 | 0.765 | [-0.260, 1.791] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | twap | high_volatility | 50 | 1.317 | [0.040, 2.594] |
| cost_aligned_schedule_Q_run3 | G0_TWAP | twap | normal | 50 | 0.665 | [0.115, 1.216] |
| cost_aligned_schedule_Q_run3 | G1_dynamic_rule | twap | normal | 50 | 0.764 | [0.142, 1.386] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | backloaded | high_volatility | 50 | 0.873 | [-0.687, 2.432] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.662 | [-1.253, 2.576] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | backloaded | normal | 50 | 1.178 | [0.426, 1.931] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | backloaded | normal | 50 | 1.180 | [0.400, 1.960] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | bursty | high_volatility | 50 | 0.166 | [-0.473, 0.804] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.605 | [-0.531, 1.741] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | bursty | normal | 50 | 0.231 | [-0.005, 0.467] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.207 | [-0.109, 0.523] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | frontloaded | high_volatility | 50 | 0.719 | [-0.339, 1.778] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.022 | [-0.088, 2.133] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | frontloaded | normal | 50 | 1.060 | [0.518, 1.601] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 1.022 | [0.525, 1.518] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | randomized | high_volatility | 50 | 1.494 | [0.497, 2.491] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 2.275 | [1.015, 3.534] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | randomized | normal | 50 | 0.142 | [-0.376, 0.660] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | randomized | normal | 50 | 0.277 | [-0.219, 0.774] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | twap | high_volatility | 50 | 1.453 | [0.475, 2.430] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 2.004 | [0.915, 3.094] |
| cost_aligned_schedule_Q_run4 | G0_TWAP | twap | normal | 50 | 1.698 | [0.997, 2.399] |
| cost_aligned_schedule_Q_run4 | G1_dynamic_rule | twap | normal | 50 | 1.796 | [1.106, 2.487] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | backloaded | high_volatility | 50 | 0.127 | [-1.417, 1.670] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | -0.084 | [-2.014, 1.845] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | backloaded | normal | 50 | 0.898 | [0.189, 1.608] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | backloaded | normal | 50 | 0.900 | [0.137, 1.664] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | bursty | high_volatility | 50 | 0.965 | [-0.124, 2.053] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.404 | [0.186, 2.621] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | bursty | normal | 50 | 0.404 | [-0.098, 0.905] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.379 | [-0.164, 0.923] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | frontloaded | high_volatility | 50 | 2.092 | [0.476, 3.709] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 2.395 | [0.545, 4.246] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | frontloaded | normal | 50 | 2.020 | [1.313, 2.727] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 1.982 | [1.270, 2.693] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | randomized | high_volatility | 50 | 1.570 | [0.389, 2.751] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | 2.351 | [0.729, 3.972] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | randomized | normal | 50 | 0.516 | [-0.124, 1.157] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | randomized | normal | 50 | 0.651 | [-0.026, 1.328] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | twap | high_volatility | 50 | 1.481 | [0.457, 2.506] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | twap | high_volatility | 50 | 2.033 | [0.713, 3.353] |
| cost_aligned_schedule_Q_run5 | G0_TWAP | twap | normal | 50 | 1.539 | [0.906, 2.172] |
| cost_aligned_schedule_Q_run5 | G1_dynamic_rule | twap | normal | 50 | 1.638 | [0.986, 2.290] |
| rule_guided_double_Q_m0.1_run1 | G0_TWAP | backloaded | high_volatility | 50 | 0.937 | [0.220, 1.653] |
| rule_guided_double_Q_m0.1_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.726 | [-0.033, 1.485] |
| rule_guided_double_Q_m0.1_run1 | G0_TWAP | backloaded | normal | 50 | 0.420 | [0.059, 0.782] |
| rule_guided_double_Q_m0.1_run1 | G1_dynamic_rule | backloaded | normal | 50 | 0.422 | [0.172, 0.672] |
| rule_guided_double_Q_m0.1_run1 | G0_TWAP | bursty | high_volatility | 50 | -0.223 | [-0.929, 0.483] |
| rule_guided_double_Q_m0.1_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.216 | [-0.005, 0.437] |
| rule_guided_double_Q_m0.1_run1 | G0_TWAP | bursty | normal | 50 | 0.093 | [-0.190, 0.376] |
| rule_guided_double_Q_m0.1_run1 | G1_dynamic_rule | bursty | normal | 50 | 0.068 | [-0.050, 0.187] |
| rule_guided_double_Q_m0.1_run1 | G0_TWAP | frontloaded | high_volatility | 50 | 0.529 | [-0.156, 1.215] |
| rule_guided_double_Q_m0.1_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.832 | [0.138, 1.526] |
| rule_guided_double_Q_m0.1_run1 | G0_TWAP | frontloaded | normal | 50 | 0.500 | [0.049, 0.952] |
| rule_guided_double_Q_m0.1_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 0.462 | [0.190, 0.735] |
| rule_guided_double_Q_m0.1_run1 | G0_TWAP | randomized | high_volatility | 50 | 0.408 | [-0.289, 1.105] |
| rule_guided_double_Q_m0.1_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.188 | [0.399, 1.977] |
| rule_guided_double_Q_m0.1_run1 | G0_TWAP | randomized | normal | 50 | -0.041 | [-0.390, 0.307] |
| rule_guided_double_Q_m0.1_run1 | G1_dynamic_rule | randomized | normal | 50 | 0.094 | [-0.116, 0.303] |
| rule_guided_double_Q_m0.1_run1 | G0_TWAP | twap | high_volatility | 50 | -0.109 | [-0.791, 0.573] |
| rule_guided_double_Q_m0.1_run1 | G1_dynamic_rule | twap | high_volatility | 50 | 0.442 | [0.143, 0.742] |
| rule_guided_double_Q_m0.1_run1 | G0_TWAP | twap | normal | 50 | 0.211 | [-0.162, 0.583] |
| rule_guided_double_Q_m0.1_run1 | G1_dynamic_rule | twap | normal | 50 | 0.310 | [0.130, 0.489] |
| rule_guided_double_Q_m0.1_run2 | G0_TWAP | backloaded | high_volatility | 50 | 1.514 | [0.513, 2.514] |
| rule_guided_double_Q_m0.1_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.303 | [0.372, 2.234] |
| rule_guided_double_Q_m0.1_run2 | G0_TWAP | backloaded | normal | 50 | 0.343 | [-0.057, 0.743] |
| rule_guided_double_Q_m0.1_run2 | G1_dynamic_rule | backloaded | normal | 50 | 0.345 | [0.057, 0.634] |
| rule_guided_double_Q_m0.1_run2 | G0_TWAP | bursty | high_volatility | 50 | -0.184 | [-0.869, 0.501] |
| rule_guided_double_Q_m0.1_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.255 | [0.091, 0.419] |
| rule_guided_double_Q_m0.1_run2 | G0_TWAP | bursty | normal | 50 | 0.084 | [-0.201, 0.369] |
| rule_guided_double_Q_m0.1_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.059 | [-0.059, 0.178] |
| rule_guided_double_Q_m0.1_run2 | G0_TWAP | frontloaded | high_volatility | 50 | 0.951 | [-0.170, 2.072] |
| rule_guided_double_Q_m0.1_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.254 | [0.253, 2.255] |
| rule_guided_double_Q_m0.1_run2 | G0_TWAP | frontloaded | normal | 50 | 0.518 | [-0.037, 1.074] |
| rule_guided_double_Q_m0.1_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.480 | [0.095, 0.865] |
| rule_guided_double_Q_m0.1_run2 | G0_TWAP | randomized | high_volatility | 50 | 0.479 | [-0.352, 1.310] |
| rule_guided_double_Q_m0.1_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.260 | [0.415, 2.105] |
| rule_guided_double_Q_m0.1_run2 | G0_TWAP | randomized | normal | 50 | 0.001 | [-0.370, 0.371] |
| rule_guided_double_Q_m0.1_run2 | G1_dynamic_rule | randomized | normal | 50 | 0.136 | [-0.098, 0.369] |
| rule_guided_double_Q_m0.1_run2 | G0_TWAP | twap | high_volatility | 50 | 0.012 | [-0.710, 0.733] |
| rule_guided_double_Q_m0.1_run2 | G1_dynamic_rule | twap | high_volatility | 50 | 0.563 | [0.218, 0.908] |
| rule_guided_double_Q_m0.1_run2 | G0_TWAP | twap | normal | 50 | 0.283 | [-0.141, 0.707] |
| rule_guided_double_Q_m0.1_run2 | G1_dynamic_rule | twap | normal | 50 | 0.382 | [0.143, 0.620] |
| rule_guided_double_Q_m0.1_run3 | G0_TWAP | backloaded | high_volatility | 50 | 1.561 | [0.476, 2.646] |
| rule_guided_double_Q_m0.1_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.350 | [0.323, 2.378] |
| rule_guided_double_Q_m0.1_run3 | G0_TWAP | backloaded | normal | 50 | 0.607 | [0.102, 1.112] |
| rule_guided_double_Q_m0.1_run3 | G1_dynamic_rule | backloaded | normal | 50 | 0.608 | [0.220, 0.997] |
| rule_guided_double_Q_m0.1_run3 | G0_TWAP | bursty | high_volatility | 50 | -0.283 | [-1.042, 0.475] |
| rule_guided_double_Q_m0.1_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.156 | [-0.186, 0.498] |
| rule_guided_double_Q_m0.1_run3 | G0_TWAP | bursty | normal | 50 | 0.086 | [-0.197, 0.370] |
| rule_guided_double_Q_m0.1_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.062 | [-0.056, 0.180] |
| rule_guided_double_Q_m0.1_run3 | G0_TWAP | frontloaded | high_volatility | 50 | 1.076 | [-0.086, 2.238] |
| rule_guided_double_Q_m0.1_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.379 | [0.340, 2.418] |
| rule_guided_double_Q_m0.1_run3 | G0_TWAP | frontloaded | normal | 50 | 0.721 | [0.123, 1.319] |
| rule_guided_double_Q_m0.1_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 0.683 | [0.257, 1.109] |
| rule_guided_double_Q_m0.1_run3 | G0_TWAP | randomized | high_volatility | 50 | 0.410 | [-0.407, 1.227] |
| rule_guided_double_Q_m0.1_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.190 | [0.349, 2.032] |
| rule_guided_double_Q_m0.1_run3 | G0_TWAP | randomized | normal | 50 | 0.038 | [-0.364, 0.439] |
| rule_guided_double_Q_m0.1_run3 | G1_dynamic_rule | randomized | normal | 50 | 0.173 | [-0.093, 0.438] |
| rule_guided_double_Q_m0.1_run3 | G0_TWAP | twap | high_volatility | 50 | 0.056 | [-0.550, 0.662] |
| rule_guided_double_Q_m0.1_run3 | G1_dynamic_rule | twap | high_volatility | 50 | 0.607 | [0.274, 0.941] |
| rule_guided_double_Q_m0.1_run3 | G0_TWAP | twap | normal | 50 | 0.281 | [-0.145, 0.708] |
| rule_guided_double_Q_m0.1_run3 | G1_dynamic_rule | twap | normal | 50 | 0.380 | [0.137, 0.623] |
| rule_guided_double_Q_m0.1_run4 | G0_TWAP | backloaded | high_volatility | 50 | 1.445 | [0.364, 2.525] |
| rule_guided_double_Q_m0.1_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.234 | [0.232, 2.236] |
| rule_guided_double_Q_m0.1_run4 | G0_TWAP | backloaded | normal | 50 | 0.385 | [0.005, 0.765] |
| rule_guided_double_Q_m0.1_run4 | G1_dynamic_rule | backloaded | normal | 50 | 0.387 | [0.141, 0.633] |
| rule_guided_double_Q_m0.1_run4 | G0_TWAP | bursty | high_volatility | 50 | -0.220 | [-0.930, 0.489] |
| rule_guided_double_Q_m0.1_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.219 | [-0.003, 0.440] |
| rule_guided_double_Q_m0.1_run4 | G0_TWAP | bursty | normal | 50 | 0.106 | [-0.181, 0.393] |
| rule_guided_double_Q_m0.1_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.082 | [-0.041, 0.204] |
| rule_guided_double_Q_m0.1_run4 | G0_TWAP | frontloaded | high_volatility | 50 | 0.981 | [-0.151, 2.114] |
| rule_guided_double_Q_m0.1_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.284 | [0.275, 2.294] |
| rule_guided_double_Q_m0.1_run4 | G0_TWAP | frontloaded | normal | 50 | 0.562 | [0.087, 1.037] |
| rule_guided_double_Q_m0.1_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 0.524 | [0.231, 0.816] |
| rule_guided_double_Q_m0.1_run4 | G0_TWAP | randomized | high_volatility | 50 | 0.259 | [-0.562, 1.081] |
| rule_guided_double_Q_m0.1_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.040 | [0.259, 1.820] |
| rule_guided_double_Q_m0.1_run4 | G0_TWAP | randomized | normal | 50 | -0.031 | [-0.391, 0.329] |
| rule_guided_double_Q_m0.1_run4 | G1_dynamic_rule | randomized | normal | 50 | 0.104 | [-0.112, 0.320] |
| rule_guided_double_Q_m0.1_run4 | G0_TWAP | twap | high_volatility | 50 | 0.017 | [-0.586, 0.619] |
| rule_guided_double_Q_m0.1_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 0.568 | [0.216, 0.920] |
| rule_guided_double_Q_m0.1_run4 | G0_TWAP | twap | normal | 50 | 0.284 | [-0.104, 0.672] |
| rule_guided_double_Q_m0.1_run4 | G1_dynamic_rule | twap | normal | 50 | 0.383 | [0.189, 0.576] |
| rule_guided_double_Q_m0.1_run5 | G0_TWAP | backloaded | high_volatility | 50 | 1.530 | [0.466, 2.594] |
| rule_guided_double_Q_m0.1_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.319 | [0.314, 2.324] |
| rule_guided_double_Q_m0.1_run5 | G0_TWAP | backloaded | normal | 50 | 0.501 | [-0.013, 1.016] |
| rule_guided_double_Q_m0.1_run5 | G1_dynamic_rule | backloaded | normal | 50 | 0.503 | [0.121, 0.886] |
| rule_guided_double_Q_m0.1_run5 | G0_TWAP | bursty | high_volatility | 50 | -0.307 | [-1.067, 0.452] |
| rule_guided_double_Q_m0.1_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.132 | [-0.211, 0.475] |
| rule_guided_double_Q_m0.1_run5 | G0_TWAP | bursty | normal | 50 | 0.088 | [-0.196, 0.373] |
| rule_guided_double_Q_m0.1_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.064 | [-0.056, 0.183] |
| rule_guided_double_Q_m0.1_run5 | G0_TWAP | frontloaded | high_volatility | 50 | 0.921 | [-0.298, 2.140] |
| rule_guided_double_Q_m0.1_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.224 | [0.153, 2.295] |
| rule_guided_double_Q_m0.1_run5 | G0_TWAP | frontloaded | normal | 50 | 0.717 | [0.139, 1.294] |
| rule_guided_double_Q_m0.1_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 0.678 | [0.270, 1.087] |
| rule_guided_double_Q_m0.1_run5 | G0_TWAP | randomized | high_volatility | 50 | 0.336 | [-0.470, 1.141] |
| rule_guided_double_Q_m0.1_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.116 | [0.274, 1.958] |
| rule_guided_double_Q_m0.1_run5 | G0_TWAP | randomized | normal | 50 | 0.096 | [-0.288, 0.479] |
| rule_guided_double_Q_m0.1_run5 | G1_dynamic_rule | randomized | normal | 50 | 0.231 | [-0.007, 0.469] |
| rule_guided_double_Q_m0.1_run5 | G0_TWAP | twap | high_volatility | 50 | -0.141 | [-0.834, 0.551] |
| rule_guided_double_Q_m0.1_run5 | G1_dynamic_rule | twap | high_volatility | 50 | 0.410 | [0.097, 0.723] |
| rule_guided_double_Q_m0.1_run5 | G0_TWAP | twap | normal | 50 | 0.275 | [-0.117, 0.667] |
| rule_guided_double_Q_m0.1_run5 | G1_dynamic_rule | twap | normal | 50 | 0.374 | [0.175, 0.572] |
| rule_guided_double_Q_m0.25_run1 | G0_TWAP | backloaded | high_volatility | 50 | 0.915 | [0.199, 1.631] |
| rule_guided_double_Q_m0.25_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.704 | [-0.045, 1.453] |
| rule_guided_double_Q_m0.25_run1 | G0_TWAP | backloaded | normal | 50 | 0.407 | [0.050, 0.764] |
| rule_guided_double_Q_m0.25_run1 | G1_dynamic_rule | backloaded | normal | 50 | 0.409 | [0.160, 0.659] |
| rule_guided_double_Q_m0.25_run1 | G0_TWAP | bursty | high_volatility | 50 | -0.223 | [-0.929, 0.483] |
| rule_guided_double_Q_m0.25_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.216 | [-0.005, 0.437] |
| rule_guided_double_Q_m0.25_run1 | G0_TWAP | bursty | normal | 50 | 0.093 | [-0.190, 0.376] |
| rule_guided_double_Q_m0.25_run1 | G1_dynamic_rule | bursty | normal | 50 | 0.068 | [-0.050, 0.187] |
| rule_guided_double_Q_m0.25_run1 | G0_TWAP | frontloaded | high_volatility | 50 | 0.411 | [-0.307, 1.129] |
| rule_guided_double_Q_m0.25_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.714 | [0.052, 1.377] |
| rule_guided_double_Q_m0.25_run1 | G0_TWAP | frontloaded | normal | 50 | 0.495 | [0.056, 0.933] |
| rule_guided_double_Q_m0.25_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 0.456 | [0.198, 0.715] |
| rule_guided_double_Q_m0.25_run1 | G0_TWAP | randomized | high_volatility | 50 | 0.353 | [-0.347, 1.054] |
| rule_guided_double_Q_m0.25_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.134 | [0.352, 1.916] |
| rule_guided_double_Q_m0.25_run1 | G0_TWAP | randomized | normal | 50 | -0.028 | [-0.371, 0.314] |
| rule_guided_double_Q_m0.25_run1 | G1_dynamic_rule | randomized | normal | 50 | 0.107 | [-0.097, 0.311] |
| rule_guided_double_Q_m0.25_run1 | G0_TWAP | twap | high_volatility | 50 | -0.193 | [-0.884, 0.498] |
| rule_guided_double_Q_m0.25_run1 | G1_dynamic_rule | twap | high_volatility | 50 | 0.359 | [0.055, 0.662] |
| rule_guided_double_Q_m0.25_run1 | G0_TWAP | twap | normal | 50 | 0.208 | [-0.161, 0.577] |
| rule_guided_double_Q_m0.25_run1 | G1_dynamic_rule | twap | normal | 50 | 0.307 | [0.132, 0.482] |
| rule_guided_double_Q_m0.25_run2 | G0_TWAP | backloaded | high_volatility | 50 | 1.092 | [0.208, 1.977] |
| rule_guided_double_Q_m0.25_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.882 | [0.061, 1.702] |
| rule_guided_double_Q_m0.25_run2 | G0_TWAP | backloaded | normal | 50 | 0.485 | [0.026, 0.944] |
| rule_guided_double_Q_m0.25_run2 | G1_dynamic_rule | backloaded | normal | 50 | 0.487 | [0.146, 0.828] |
| rule_guided_double_Q_m0.25_run2 | G0_TWAP | bursty | high_volatility | 50 | -0.184 | [-0.869, 0.501] |
| rule_guided_double_Q_m0.25_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.255 | [0.091, 0.419] |
| rule_guided_double_Q_m0.25_run2 | G0_TWAP | bursty | normal | 50 | 0.084 | [-0.201, 0.369] |
| rule_guided_double_Q_m0.25_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.059 | [-0.059, 0.178] |
| rule_guided_double_Q_m0.25_run2 | G0_TWAP | frontloaded | high_volatility | 50 | 0.626 | [-0.320, 1.572] |
| rule_guided_double_Q_m0.25_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.929 | [0.070, 1.788] |
| rule_guided_double_Q_m0.25_run2 | G0_TWAP | frontloaded | normal | 50 | 0.576 | [0.004, 1.148] |
| rule_guided_double_Q_m0.25_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.538 | [0.138, 0.937] |
| rule_guided_double_Q_m0.25_run2 | G0_TWAP | randomized | high_volatility | 50 | 0.411 | [-0.352, 1.173] |
| rule_guided_double_Q_m0.25_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.191 | [0.413, 1.970] |
| rule_guided_double_Q_m0.25_run2 | G0_TWAP | randomized | normal | 50 | -0.019 | [-0.391, 0.353] |
| rule_guided_double_Q_m0.25_run2 | G1_dynamic_rule | randomized | normal | 50 | 0.116 | [-0.121, 0.353] |
| rule_guided_double_Q_m0.25_run2 | G0_TWAP | twap | high_volatility | 50 | -0.045 | [-0.771, 0.682] |
| rule_guided_double_Q_m0.25_run2 | G1_dynamic_rule | twap | high_volatility | 50 | 0.507 | [0.155, 0.860] |
| rule_guided_double_Q_m0.25_run2 | G0_TWAP | twap | normal | 50 | 0.283 | [-0.141, 0.707] |
| rule_guided_double_Q_m0.25_run2 | G1_dynamic_rule | twap | normal | 50 | 0.382 | [0.143, 0.620] |
| rule_guided_double_Q_m0.25_run3 | G0_TWAP | backloaded | high_volatility | 50 | 1.353 | [0.347, 2.359] |
| rule_guided_double_Q_m0.25_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.142 | [0.175, 2.110] |
| rule_guided_double_Q_m0.25_run3 | G0_TWAP | backloaded | normal | 50 | 0.610 | [0.101, 1.119] |
| rule_guided_double_Q_m0.25_run3 | G1_dynamic_rule | backloaded | normal | 50 | 0.611 | [0.219, 1.004] |
| rule_guided_double_Q_m0.25_run3 | G0_TWAP | bursty | high_volatility | 50 | -0.283 | [-1.042, 0.475] |
| rule_guided_double_Q_m0.25_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.156 | [-0.186, 0.498] |
| rule_guided_double_Q_m0.25_run3 | G0_TWAP | bursty | normal | 50 | 0.086 | [-0.197, 0.370] |
| rule_guided_double_Q_m0.25_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.062 | [-0.056, 0.180] |
| rule_guided_double_Q_m0.25_run3 | G0_TWAP | frontloaded | high_volatility | 50 | 0.974 | [-0.139, 2.087] |
| rule_guided_double_Q_m0.25_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.277 | [0.294, 2.260] |
| rule_guided_double_Q_m0.25_run3 | G0_TWAP | frontloaded | normal | 50 | 0.750 | [0.166, 1.333] |
| rule_guided_double_Q_m0.25_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 0.711 | [0.305, 1.118] |
| rule_guided_double_Q_m0.25_run3 | G0_TWAP | randomized | high_volatility | 50 | 0.358 | [-0.464, 1.181] |
| rule_guided_double_Q_m0.25_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.139 | [0.302, 1.977] |
| rule_guided_double_Q_m0.25_run3 | G0_TWAP | randomized | normal | 50 | 0.031 | [-0.362, 0.424] |
| rule_guided_double_Q_m0.25_run3 | G1_dynamic_rule | randomized | normal | 50 | 0.166 | [-0.091, 0.423] |
| rule_guided_double_Q_m0.25_run3 | G0_TWAP | twap | high_volatility | 50 | 0.062 | [-0.543, 0.667] |
| rule_guided_double_Q_m0.25_run3 | G1_dynamic_rule | twap | high_volatility | 50 | 0.613 | [0.280, 0.947] |
| rule_guided_double_Q_m0.25_run3 | G0_TWAP | twap | normal | 50 | 0.268 | [-0.152, 0.689] |
| rule_guided_double_Q_m0.25_run3 | G1_dynamic_rule | twap | normal | 50 | 0.367 | [0.133, 0.601] |
| rule_guided_double_Q_m0.25_run4 | G0_TWAP | backloaded | high_volatility | 50 | 1.142 | [0.255, 2.028] |
| rule_guided_double_Q_m0.25_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.931 | [0.108, 1.754] |
| rule_guided_double_Q_m0.25_run4 | G0_TWAP | backloaded | normal | 50 | 0.384 | [0.005, 0.763] |
| rule_guided_double_Q_m0.25_run4 | G1_dynamic_rule | backloaded | normal | 50 | 0.386 | [0.141, 0.631] |
| rule_guided_double_Q_m0.25_run4 | G0_TWAP | bursty | high_volatility | 50 | -0.279 | [-0.989, 0.430] |
| rule_guided_double_Q_m0.25_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.160 | [-0.057, 0.376] |
| rule_guided_double_Q_m0.25_run4 | G0_TWAP | bursty | normal | 50 | 0.106 | [-0.181, 0.393] |
| rule_guided_double_Q_m0.25_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.082 | [-0.041, 0.204] |
| rule_guided_double_Q_m0.25_run4 | G0_TWAP | frontloaded | high_volatility | 50 | 0.719 | [-0.231, 1.670] |
| rule_guided_double_Q_m0.25_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.023 | [0.158, 1.887] |
| rule_guided_double_Q_m0.25_run4 | G0_TWAP | frontloaded | normal | 50 | 0.562 | [0.087, 1.037] |
| rule_guided_double_Q_m0.25_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 0.524 | [0.231, 0.816] |
| rule_guided_double_Q_m0.25_run4 | G0_TWAP | randomized | high_volatility | 50 | 0.263 | [-0.505, 1.030] |
| rule_guided_double_Q_m0.25_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.043 | [0.397, 1.690] |
| rule_guided_double_Q_m0.25_run4 | G0_TWAP | randomized | normal | 50 | -0.033 | [-0.393, 0.326] |
| rule_guided_double_Q_m0.25_run4 | G1_dynamic_rule | randomized | normal | 50 | 0.102 | [-0.114, 0.317] |
| rule_guided_double_Q_m0.25_run4 | G0_TWAP | twap | high_volatility | 50 | -0.179 | [-0.792, 0.434] |
| rule_guided_double_Q_m0.25_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 0.373 | [0.034, 0.712] |
| rule_guided_double_Q_m0.25_run4 | G0_TWAP | twap | normal | 50 | 0.297 | [-0.113, 0.707] |
| rule_guided_double_Q_m0.25_run4 | G1_dynamic_rule | twap | normal | 50 | 0.396 | [0.176, 0.616] |
| rule_guided_double_Q_m0.25_run5 | G0_TWAP | backloaded | high_volatility | 50 | 1.520 | [0.454, 2.587] |
| rule_guided_double_Q_m0.25_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.310 | [0.323, 2.296] |
| rule_guided_double_Q_m0.25_run5 | G0_TWAP | backloaded | normal | 50 | 0.566 | [0.084, 1.049] |
| rule_guided_double_Q_m0.25_run5 | G1_dynamic_rule | backloaded | normal | 50 | 0.568 | [0.218, 0.919] |
| rule_guided_double_Q_m0.25_run5 | G0_TWAP | bursty | high_volatility | 50 | -0.307 | [-1.067, 0.452] |
| rule_guided_double_Q_m0.25_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.132 | [-0.211, 0.475] |
| rule_guided_double_Q_m0.25_run5 | G0_TWAP | bursty | normal | 50 | 0.088 | [-0.196, 0.373] |
| rule_guided_double_Q_m0.25_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.064 | [-0.056, 0.183] |
| rule_guided_double_Q_m0.25_run5 | G0_TWAP | frontloaded | high_volatility | 50 | 0.889 | [-0.338, 2.117] |
| rule_guided_double_Q_m0.25_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.192 | [0.124, 2.261] |
| rule_guided_double_Q_m0.25_run5 | G0_TWAP | frontloaded | normal | 50 | 0.761 | [0.199, 1.323] |
| rule_guided_double_Q_m0.25_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 0.723 | [0.332, 1.114] |
| rule_guided_double_Q_m0.25_run5 | G0_TWAP | randomized | high_volatility | 50 | 0.265 | [-0.561, 1.091] |
| rule_guided_double_Q_m0.25_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.045 | [0.250, 1.840] |
| rule_guided_double_Q_m0.25_run5 | G0_TWAP | randomized | normal | 50 | 0.049 | [-0.323, 0.422] |
| rule_guided_double_Q_m0.25_run5 | G1_dynamic_rule | randomized | normal | 50 | 0.185 | [-0.043, 0.412] |
| rule_guided_double_Q_m0.25_run5 | G0_TWAP | twap | high_volatility | 50 | -0.112 | [-0.812, 0.588] |
| rule_guided_double_Q_m0.25_run5 | G1_dynamic_rule | twap | high_volatility | 50 | 0.440 | [0.117, 0.762] |
| rule_guided_double_Q_m0.25_run5 | G0_TWAP | twap | normal | 50 | 0.275 | [-0.117, 0.667] |
| rule_guided_double_Q_m0.25_run5 | G1_dynamic_rule | twap | normal | 50 | 0.374 | [0.175, 0.572] |
| rule_guided_double_Q_m0.5_run1 | G0_TWAP | backloaded | high_volatility | 50 | 0.886 | [0.077, 1.694] |
| rule_guided_double_Q_m0.5_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.675 | [0.092, 1.257] |
| rule_guided_double_Q_m0.5_run1 | G0_TWAP | backloaded | normal | 50 | 0.441 | [0.054, 0.828] |
| rule_guided_double_Q_m0.5_run1 | G1_dynamic_rule | backloaded | normal | 50 | 0.443 | [0.158, 0.728] |
| rule_guided_double_Q_m0.5_run1 | G0_TWAP | bursty | high_volatility | 50 | -0.278 | [-0.985, 0.429] |
| rule_guided_double_Q_m0.5_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.161 | [-0.056, 0.378] |
| rule_guided_double_Q_m0.5_run1 | G0_TWAP | bursty | normal | 50 | 0.014 | [-0.268, 0.295] |
| rule_guided_double_Q_m0.5_run1 | G1_dynamic_rule | bursty | normal | 50 | -0.011 | [-0.126, 0.104] |
| rule_guided_double_Q_m0.5_run1 | G0_TWAP | frontloaded | high_volatility | 50 | 0.268 | [-0.622, 1.157] |
| rule_guided_double_Q_m0.5_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.571 | [0.042, 1.099] |
| rule_guided_double_Q_m0.5_run1 | G0_TWAP | frontloaded | normal | 50 | 0.487 | [0.025, 0.949] |
| rule_guided_double_Q_m0.5_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 0.449 | [0.165, 0.733] |
| rule_guided_double_Q_m0.5_run1 | G0_TWAP | randomized | high_volatility | 50 | -0.023 | [-0.844, 0.799] |
| rule_guided_double_Q_m0.5_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.758 | [0.170, 1.346] |
| rule_guided_double_Q_m0.5_run1 | G0_TWAP | randomized | normal | 50 | -0.037 | [-0.367, 0.293] |
| rule_guided_double_Q_m0.5_run1 | G1_dynamic_rule | randomized | normal | 50 | 0.098 | [-0.088, 0.284] |
| rule_guided_double_Q_m0.5_run1 | G0_TWAP | twap | high_volatility | 50 | -0.260 | [-0.944, 0.423] |
| rule_guided_double_Q_m0.5_run1 | G1_dynamic_rule | twap | high_volatility | 50 | 0.291 | [0.015, 0.568] |
| rule_guided_double_Q_m0.5_run1 | G0_TWAP | twap | normal | 50 | 0.176 | [-0.186, 0.538] |
| rule_guided_double_Q_m0.5_run1 | G1_dynamic_rule | twap | normal | 50 | 0.275 | [0.103, 0.446] |
| rule_guided_double_Q_m0.5_run2 | G0_TWAP | backloaded | high_volatility | 50 | 1.069 | [0.103, 2.035] |
| rule_guided_double_Q_m0.5_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.858 | [0.199, 1.517] |
| rule_guided_double_Q_m0.5_run2 | G0_TWAP | backloaded | normal | 50 | 0.424 | [-0.019, 0.868] |
| rule_guided_double_Q_m0.5_run2 | G1_dynamic_rule | backloaded | normal | 50 | 0.426 | [0.116, 0.736] |
| rule_guided_double_Q_m0.5_run2 | G0_TWAP | bursty | high_volatility | 50 | -0.184 | [-0.869, 0.501] |
| rule_guided_double_Q_m0.5_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.255 | [0.091, 0.419] |
| rule_guided_double_Q_m0.5_run2 | G0_TWAP | bursty | normal | 50 | 0.084 | [-0.201, 0.369] |
| rule_guided_double_Q_m0.5_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.059 | [-0.059, 0.178] |
| rule_guided_double_Q_m0.5_run2 | G0_TWAP | frontloaded | high_volatility | 50 | 0.387 | [-0.669, 1.444] |
| rule_guided_double_Q_m0.5_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.690 | [-0.049, 1.430] |
| rule_guided_double_Q_m0.5_run2 | G0_TWAP | frontloaded | normal | 50 | 0.557 | [0.008, 1.106] |
| rule_guided_double_Q_m0.5_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.518 | [0.146, 0.891] |
| rule_guided_double_Q_m0.5_run2 | G0_TWAP | randomized | high_volatility | 50 | -0.017 | [-0.940, 0.906] |
| rule_guided_double_Q_m0.5_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.764 | [0.172, 1.356] |
| rule_guided_double_Q_m0.5_run2 | G0_TWAP | randomized | normal | 50 | 0.029 | [-0.335, 0.394] |
| rule_guided_double_Q_m0.5_run2 | G1_dynamic_rule | randomized | normal | 50 | 0.164 | [-0.054, 0.383] |
| rule_guided_double_Q_m0.5_run2 | G0_TWAP | twap | high_volatility | 50 | -0.166 | [-0.888, 0.556] |
| rule_guided_double_Q_m0.5_run2 | G1_dynamic_rule | twap | high_volatility | 50 | 0.385 | [0.054, 0.716] |
| rule_guided_double_Q_m0.5_run2 | G0_TWAP | twap | normal | 50 | 0.283 | [-0.141, 0.707] |
| rule_guided_double_Q_m0.5_run2 | G1_dynamic_rule | twap | normal | 50 | 0.382 | [0.143, 0.620] |
| rule_guided_double_Q_m0.5_run3 | G0_TWAP | backloaded | high_volatility | 50 | 1.316 | [0.321, 2.311] |
| rule_guided_double_Q_m0.5_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.105 | [0.171, 2.040] |
| rule_guided_double_Q_m0.5_run3 | G0_TWAP | backloaded | normal | 50 | 0.485 | [0.051, 0.919] |
| rule_guided_double_Q_m0.5_run3 | G1_dynamic_rule | backloaded | normal | 50 | 0.487 | [0.171, 0.802] |
| rule_guided_double_Q_m0.5_run3 | G0_TWAP | bursty | high_volatility | 50 | -0.283 | [-1.042, 0.475] |
| rule_guided_double_Q_m0.5_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.156 | [-0.186, 0.498] |
| rule_guided_double_Q_m0.5_run3 | G0_TWAP | bursty | normal | 50 | 0.086 | [-0.197, 0.370] |
| rule_guided_double_Q_m0.5_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.062 | [-0.056, 0.180] |
| rule_guided_double_Q_m0.5_run3 | G0_TWAP | frontloaded | high_volatility | 50 | 1.006 | [-0.090, 2.103] |
| rule_guided_double_Q_m0.5_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.309 | [0.370, 2.249] |
| rule_guided_double_Q_m0.5_run3 | G0_TWAP | frontloaded | normal | 50 | 0.635 | [0.109, 1.161] |
| rule_guided_double_Q_m0.5_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 0.597 | [0.247, 0.946] |
| rule_guided_double_Q_m0.5_run3 | G0_TWAP | randomized | high_volatility | 50 | 0.212 | [-0.585, 1.009] |
| rule_guided_double_Q_m0.5_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.993 | [0.157, 1.828] |
| rule_guided_double_Q_m0.5_run3 | G0_TWAP | randomized | normal | 50 | 0.012 | [-0.343, 0.367] |
| rule_guided_double_Q_m0.5_run3 | G1_dynamic_rule | randomized | normal | 50 | 0.148 | [-0.067, 0.362] |
| rule_guided_double_Q_m0.5_run3 | G0_TWAP | twap | high_volatility | 50 | -0.161 | [-0.849, 0.526] |
| rule_guided_double_Q_m0.5_run3 | G1_dynamic_rule | twap | high_volatility | 50 | 0.390 | [0.105, 0.675] |
| rule_guided_double_Q_m0.5_run3 | G0_TWAP | twap | normal | 50 | 0.268 | [-0.153, 0.688] |
| rule_guided_double_Q_m0.5_run3 | G1_dynamic_rule | twap | normal | 50 | 0.366 | [0.132, 0.601] |
| rule_guided_double_Q_m0.5_run4 | G0_TWAP | backloaded | high_volatility | 50 | 0.975 | [0.098, 1.852] |
| rule_guided_double_Q_m0.5_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.765 | [0.155, 1.374] |
| rule_guided_double_Q_m0.5_run4 | G0_TWAP | backloaded | normal | 50 | 0.401 | [0.012, 0.789] |
| rule_guided_double_Q_m0.5_run4 | G1_dynamic_rule | backloaded | normal | 50 | 0.402 | [0.151, 0.654] |
| rule_guided_double_Q_m0.5_run4 | G0_TWAP | bursty | high_volatility | 50 | -0.279 | [-0.989, 0.430] |
| rule_guided_double_Q_m0.5_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.160 | [-0.057, 0.376] |
| rule_guided_double_Q_m0.5_run4 | G0_TWAP | bursty | normal | 50 | 0.106 | [-0.181, 0.393] |
| rule_guided_double_Q_m0.5_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.082 | [-0.041, 0.204] |
| rule_guided_double_Q_m0.5_run4 | G0_TWAP | frontloaded | high_volatility | 50 | 0.366 | [-0.628, 1.359] |
| rule_guided_double_Q_m0.5_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.669 | [0.015, 1.322] |
| rule_guided_double_Q_m0.5_run4 | G0_TWAP | frontloaded | normal | 50 | 0.522 | [0.025, 1.018] |
| rule_guided_double_Q_m0.5_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 0.483 | [0.175, 0.792] |
| rule_guided_double_Q_m0.5_run4 | G0_TWAP | randomized | high_volatility | 50 | -0.099 | [-1.068, 0.869] |
| rule_guided_double_Q_m0.5_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.681 | [0.213, 1.150] |
| rule_guided_double_Q_m0.5_run4 | G0_TWAP | randomized | normal | 50 | -0.042 | [-0.385, 0.301] |
| rule_guided_double_Q_m0.5_run4 | G1_dynamic_rule | randomized | normal | 50 | 0.093 | [-0.099, 0.285] |
| rule_guided_double_Q_m0.5_run4 | G0_TWAP | twap | high_volatility | 50 | -0.179 | [-0.792, 0.434] |
| rule_guided_double_Q_m0.5_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 0.373 | [0.034, 0.712] |
| rule_guided_double_Q_m0.5_run4 | G0_TWAP | twap | normal | 50 | 0.297 | [-0.113, 0.707] |
| rule_guided_double_Q_m0.5_run4 | G1_dynamic_rule | twap | normal | 50 | 0.396 | [0.176, 0.616] |
| rule_guided_double_Q_m0.5_run5 | G0_TWAP | backloaded | high_volatility | 50 | 1.388 | [0.297, 2.480] |
| rule_guided_double_Q_m0.5_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.178 | [0.380, 1.976] |
| rule_guided_double_Q_m0.5_run5 | G0_TWAP | backloaded | normal | 50 | 0.537 | [0.072, 1.002] |
| rule_guided_double_Q_m0.5_run5 | G1_dynamic_rule | backloaded | normal | 50 | 0.539 | [0.206, 0.872] |
| rule_guided_double_Q_m0.5_run5 | G0_TWAP | bursty | high_volatility | 50 | -0.307 | [-1.067, 0.452] |
| rule_guided_double_Q_m0.5_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.132 | [-0.211, 0.475] |
| rule_guided_double_Q_m0.5_run5 | G0_TWAP | bursty | normal | 50 | 0.088 | [-0.196, 0.373] |
| rule_guided_double_Q_m0.5_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.064 | [-0.056, 0.183] |
| rule_guided_double_Q_m0.5_run5 | G0_TWAP | frontloaded | high_volatility | 50 | 0.718 | [-0.571, 2.007] |
| rule_guided_double_Q_m0.5_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.021 | [0.103, 1.938] |
| rule_guided_double_Q_m0.5_run5 | G0_TWAP | frontloaded | normal | 50 | 0.740 | [0.192, 1.288] |
| rule_guided_double_Q_m0.5_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 0.702 | [0.325, 1.078] |
| rule_guided_double_Q_m0.5_run5 | G0_TWAP | randomized | high_volatility | 50 | -0.173 | [-1.111, 0.766] |
| rule_guided_double_Q_m0.5_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.608 | [0.031, 1.185] |
| rule_guided_double_Q_m0.5_run5 | G0_TWAP | randomized | normal | 50 | 0.058 | [-0.307, 0.422] |
| rule_guided_double_Q_m0.5_run5 | G1_dynamic_rule | randomized | normal | 50 | 0.193 | [-0.025, 0.411] |
| rule_guided_double_Q_m0.5_run5 | G0_TWAP | twap | high_volatility | 50 | -0.212 | [-0.913, 0.488] |
| rule_guided_double_Q_m0.5_run5 | G1_dynamic_rule | twap | high_volatility | 50 | 0.339 | [0.032, 0.646] |
| rule_guided_double_Q_m0.5_run5 | G0_TWAP | twap | normal | 50 | 0.284 | [-0.106, 0.674] |
| rule_guided_double_Q_m0.5_run5 | G1_dynamic_rule | twap | normal | 50 | 0.382 | [0.187, 0.578] |
| rule_guided_double_Q_m0_run1 | G0_TWAP | backloaded | high_volatility | 50 | 0.834 | [0.154, 1.513] |
| rule_guided_double_Q_m0_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.623 | [-0.113, 1.359] |
| rule_guided_double_Q_m0_run1 | G0_TWAP | backloaded | normal | 50 | 0.373 | [0.015, 0.731] |
| rule_guided_double_Q_m0_run1 | G1_dynamic_rule | backloaded | normal | 50 | 0.375 | [0.123, 0.627] |
| rule_guided_double_Q_m0_run1 | G0_TWAP | bursty | high_volatility | 50 | -0.223 | [-0.929, 0.483] |
| rule_guided_double_Q_m0_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.216 | [-0.005, 0.437] |
| rule_guided_double_Q_m0_run1 | G0_TWAP | bursty | normal | 50 | 0.093 | [-0.190, 0.376] |
| rule_guided_double_Q_m0_run1 | G1_dynamic_rule | bursty | normal | 50 | 0.068 | [-0.050, 0.187] |
| rule_guided_double_Q_m0_run1 | G0_TWAP | frontloaded | high_volatility | 50 | 0.533 | [-0.132, 1.198] |
| rule_guided_double_Q_m0_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.836 | [0.152, 1.520] |
| rule_guided_double_Q_m0_run1 | G0_TWAP | frontloaded | normal | 50 | 0.529 | [0.091, 0.966] |
| rule_guided_double_Q_m0_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 0.491 | [0.220, 0.761] |
| rule_guided_double_Q_m0_run1 | G0_TWAP | randomized | high_volatility | 50 | 0.526 | [-0.191, 1.243] |
| rule_guided_double_Q_m0_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.307 | [0.516, 2.097] |
| rule_guided_double_Q_m0_run1 | G0_TWAP | randomized | normal | 50 | -0.024 | [-0.359, 0.311] |
| rule_guided_double_Q_m0_run1 | G1_dynamic_rule | randomized | normal | 50 | 0.111 | [-0.092, 0.314] |
| rule_guided_double_Q_m0_run1 | G0_TWAP | twap | high_volatility | 50 | -0.063 | [-0.749, 0.623] |
| rule_guided_double_Q_m0_run1 | G1_dynamic_rule | twap | high_volatility | 50 | 0.489 | [0.178, 0.799] |
| rule_guided_double_Q_m0_run1 | G0_TWAP | twap | normal | 50 | 0.211 | [-0.162, 0.583] |
| rule_guided_double_Q_m0_run1 | G1_dynamic_rule | twap | normal | 50 | 0.310 | [0.130, 0.489] |
| rule_guided_double_Q_m0_run2 | G0_TWAP | backloaded | high_volatility | 50 | 1.461 | [0.473, 2.448] |
| rule_guided_double_Q_m0_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.250 | [0.330, 2.169] |
| rule_guided_double_Q_m0_run2 | G0_TWAP | backloaded | normal | 50 | 0.362 | [-0.041, 0.764] |
| rule_guided_double_Q_m0_run2 | G1_dynamic_rule | backloaded | normal | 50 | 0.363 | [0.066, 0.661] |
| rule_guided_double_Q_m0_run2 | G0_TWAP | bursty | high_volatility | 50 | -0.194 | [-0.880, 0.491] |
| rule_guided_double_Q_m0_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.245 | [0.079, 0.410] |
| rule_guided_double_Q_m0_run2 | G0_TWAP | bursty | normal | 50 | 0.084 | [-0.201, 0.369] |
| rule_guided_double_Q_m0_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.059 | [-0.059, 0.178] |
| rule_guided_double_Q_m0_run2 | G0_TWAP | frontloaded | high_volatility | 50 | 0.904 | [-0.220, 2.029] |
| rule_guided_double_Q_m0_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.207 | [0.208, 2.207] |
| rule_guided_double_Q_m0_run2 | G0_TWAP | frontloaded | normal | 50 | 0.519 | [-0.036, 1.075] |
| rule_guided_double_Q_m0_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.481 | [0.093, 0.869] |
| rule_guided_double_Q_m0_run2 | G0_TWAP | randomized | high_volatility | 50 | 0.443 | [-0.386, 1.271] |
| rule_guided_double_Q_m0_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.223 | [0.380, 2.066] |
| rule_guided_double_Q_m0_run2 | G0_TWAP | randomized | normal | 50 | 0.018 | [-0.363, 0.398] |
| rule_guided_double_Q_m0_run2 | G1_dynamic_rule | randomized | normal | 50 | 0.153 | [-0.090, 0.395] |
| rule_guided_double_Q_m0_run2 | G0_TWAP | twap | high_volatility | 50 | 0.028 | [-0.698, 0.754] |
| rule_guided_double_Q_m0_run2 | G1_dynamic_rule | twap | high_volatility | 50 | 0.580 | [0.230, 0.929] |
| rule_guided_double_Q_m0_run2 | G0_TWAP | twap | normal | 50 | 0.283 | [-0.141, 0.707] |
| rule_guided_double_Q_m0_run2 | G1_dynamic_rule | twap | normal | 50 | 0.382 | [0.143, 0.620] |
| rule_guided_double_Q_m0_run3 | G0_TWAP | backloaded | high_volatility | 50 | 1.666 | [0.573, 2.759] |
| rule_guided_double_Q_m0_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.455 | [0.420, 2.491] |
| rule_guided_double_Q_m0_run3 | G0_TWAP | backloaded | normal | 50 | 0.541 | [0.016, 1.066] |
| rule_guided_double_Q_m0_run3 | G1_dynamic_rule | backloaded | normal | 50 | 0.543 | [0.133, 0.952] |
| rule_guided_double_Q_m0_run3 | G0_TWAP | bursty | high_volatility | 50 | -0.283 | [-1.042, 0.475] |
| rule_guided_double_Q_m0_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.156 | [-0.186, 0.498] |
| rule_guided_double_Q_m0_run3 | G0_TWAP | bursty | normal | 50 | 0.086 | [-0.197, 0.370] |
| rule_guided_double_Q_m0_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.062 | [-0.056, 0.180] |
| rule_guided_double_Q_m0_run3 | G0_TWAP | frontloaded | high_volatility | 50 | 1.072 | [-0.090, 2.234] |
| rule_guided_double_Q_m0_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.375 | [0.338, 2.412] |
| rule_guided_double_Q_m0_run3 | G0_TWAP | frontloaded | normal | 50 | 0.708 | [0.115, 1.300] |
| rule_guided_double_Q_m0_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 0.670 | [0.250, 1.090] |
| rule_guided_double_Q_m0_run3 | G0_TWAP | randomized | high_volatility | 50 | 0.433 | [-0.384, 1.251] |
| rule_guided_double_Q_m0_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.214 | [0.368, 2.060] |
| rule_guided_double_Q_m0_run3 | G0_TWAP | randomized | normal | 50 | 0.019 | [-0.366, 0.403] |
| rule_guided_double_Q_m0_run3 | G1_dynamic_rule | randomized | normal | 50 | 0.154 | [-0.098, 0.406] |
| rule_guided_double_Q_m0_run3 | G0_TWAP | twap | high_volatility | 50 | 0.056 | [-0.550, 0.662] |
| rule_guided_double_Q_m0_run3 | G1_dynamic_rule | twap | high_volatility | 50 | 0.607 | [0.274, 0.941] |
| rule_guided_double_Q_m0_run3 | G0_TWAP | twap | normal | 50 | 0.315 | [-0.134, 0.764] |
| rule_guided_double_Q_m0_run3 | G1_dynamic_rule | twap | normal | 50 | 0.414 | [0.146, 0.682] |
| rule_guided_double_Q_m0_run4 | G0_TWAP | backloaded | high_volatility | 50 | 1.464 | [0.370, 2.559] |
| rule_guided_double_Q_m0_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.253 | [0.242, 2.264] |
| rule_guided_double_Q_m0_run4 | G0_TWAP | backloaded | normal | 50 | 0.391 | [-0.057, 0.839] |
| rule_guided_double_Q_m0_run4 | G1_dynamic_rule | backloaded | normal | 50 | 0.393 | [0.075, 0.711] |
| rule_guided_double_Q_m0_run4 | G0_TWAP | bursty | high_volatility | 50 | -0.220 | [-0.930, 0.489] |
| rule_guided_double_Q_m0_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.219 | [-0.003, 0.440] |
| rule_guided_double_Q_m0_run4 | G0_TWAP | bursty | normal | 50 | 0.106 | [-0.181, 0.393] |
| rule_guided_double_Q_m0_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.082 | [-0.041, 0.204] |
| rule_guided_double_Q_m0_run4 | G0_TWAP | frontloaded | high_volatility | 50 | 0.988 | [-0.163, 2.139] |
| rule_guided_double_Q_m0_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.291 | [0.271, 2.311] |
| rule_guided_double_Q_m0_run4 | G0_TWAP | frontloaded | normal | 50 | 0.674 | [0.114, 1.233] |
| rule_guided_double_Q_m0_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 0.635 | [0.252, 1.019] |
| rule_guided_double_Q_m0_run4 | G0_TWAP | randomized | high_volatility | 50 | 0.398 | [-0.470, 1.266] |
| rule_guided_double_Q_m0_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.178 | [0.371, 1.986] |
| rule_guided_double_Q_m0_run4 | G0_TWAP | randomized | normal | 50 | -0.033 | [-0.395, 0.329] |
| rule_guided_double_Q_m0_run4 | G1_dynamic_rule | randomized | normal | 50 | 0.102 | [-0.119, 0.323] |
| rule_guided_double_Q_m0_run4 | G0_TWAP | twap | high_volatility | 50 | 0.015 | [-0.589, 0.619] |
| rule_guided_double_Q_m0_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 0.567 | [0.215, 0.918] |
| rule_guided_double_Q_m0_run4 | G0_TWAP | twap | normal | 50 | 0.259 | [-0.119, 0.637] |
| rule_guided_double_Q_m0_run4 | G1_dynamic_rule | twap | normal | 50 | 0.358 | [0.173, 0.543] |
| rule_guided_double_Q_m0_run5 | G0_TWAP | backloaded | high_volatility | 50 | 1.780 | [0.624, 2.937] |
| rule_guided_double_Q_m0_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.570 | [0.478, 2.661] |
| rule_guided_double_Q_m0_run5 | G0_TWAP | backloaded | normal | 50 | 0.504 | [0.041, 0.966] |
| rule_guided_double_Q_m0_run5 | G1_dynamic_rule | backloaded | normal | 50 | 0.505 | [0.174, 0.836] |
| rule_guided_double_Q_m0_run5 | G0_TWAP | bursty | high_volatility | 50 | -0.307 | [-1.067, 0.452] |
| rule_guided_double_Q_m0_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.132 | [-0.211, 0.475] |
| rule_guided_double_Q_m0_run5 | G0_TWAP | bursty | normal | 50 | 0.088 | [-0.196, 0.373] |
| rule_guided_double_Q_m0_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.064 | [-0.056, 0.183] |
| rule_guided_double_Q_m0_run5 | G0_TWAP | frontloaded | high_volatility | 50 | 1.078 | [-0.128, 2.285] |
| rule_guided_double_Q_m0_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.381 | [0.313, 2.450] |
| rule_guided_double_Q_m0_run5 | G0_TWAP | frontloaded | normal | 50 | 0.672 | [0.097, 1.248] |
| rule_guided_double_Q_m0_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 0.634 | [0.227, 1.041] |
| rule_guided_double_Q_m0_run5 | G0_TWAP | randomized | high_volatility | 50 | 0.397 | [-0.431, 1.225] |
| rule_guided_double_Q_m0_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | 1.178 | [0.327, 2.028] |
| rule_guided_double_Q_m0_run5 | G0_TWAP | randomized | normal | 50 | 0.082 | [-0.300, 0.464] |
| rule_guided_double_Q_m0_run5 | G1_dynamic_rule | randomized | normal | 50 | 0.218 | [-0.018, 0.453] |
| rule_guided_double_Q_m0_run5 | G0_TWAP | twap | high_volatility | 50 | -0.147 | [-0.848, 0.554] |
| rule_guided_double_Q_m0_run5 | G1_dynamic_rule | twap | high_volatility | 50 | 0.405 | [0.088, 0.721] |
| rule_guided_double_Q_m0_run5 | G0_TWAP | twap | normal | 50 | 0.333 | [-0.084, 0.749] |
| rule_guided_double_Q_m0_run5 | G1_dynamic_rule | twap | normal | 50 | 0.431 | [0.206, 0.657] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | backloaded | high_volatility | 50 | 0.617 | [-0.189, 1.423] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.406 | [0.097, 0.715] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | backloaded | normal | 50 | 0.004 | [-0.219, 0.226] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | backloaded | normal | 50 | 0.006 | [-0.044, 0.055] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | bursty | high_volatility | 50 | -0.308 | [-0.998, 0.382] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.131 | [-0.031, 0.293] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | bursty | normal | 50 | 0.029 | [-0.199, 0.258] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | bursty | normal | 50 | 0.005 | [-0.035, 0.045] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | frontloaded | high_volatility | 50 | -0.284 | [-1.012, 0.445] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.020 | [-0.077, 0.116] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | frontloaded | normal | 50 | 0.123 | [-0.138, 0.383] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 0.084 | [0.026, 0.143] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | randomized | high_volatility | 50 | -0.678 | [-1.515, 0.160] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.103 | [-0.074, 0.280] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | randomized | normal | 50 | -0.091 | [-0.323, 0.141] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | randomized | normal | 50 | 0.044 | [-0.011, 0.099] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | twap | high_volatility | 50 | -0.276 | [-0.951, 0.398] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | twap | high_volatility | 50 | 0.275 | [0.004, 0.547] |
| rule_guided_double_Q_m1_run1 | G0_TWAP | twap | normal | 50 | -0.016 | [-0.309, 0.277] |
| rule_guided_double_Q_m1_run1 | G1_dynamic_rule | twap | normal | 50 | 0.083 | [-0.021, 0.186] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | backloaded | high_volatility | 50 | 0.268 | [-0.403, 0.939] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.057 | [-0.032, 0.146] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | backloaded | normal | 50 | 0.067 | [-0.156, 0.290] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | backloaded | normal | 50 | 0.069 | [-0.004, 0.141] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | bursty | high_volatility | 50 | -0.296 | [-0.973, 0.381] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.143 | [0.006, 0.280] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | bursty | normal | 50 | 0.024 | [-0.191, 0.240] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | frontloaded | high_volatility | 50 | -0.265 | [-0.990, 0.460] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.038 | [-0.027, 0.103] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | frontloaded | normal | 50 | 0.079 | [-0.203, 0.361] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.040 | [-0.026, 0.107] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | randomized | high_volatility | 50 | -0.787 | [-1.576, 0.002] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | -0.006 | [-0.071, 0.059] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | randomized | normal | 50 | -0.054 | [-0.296, 0.188] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | randomized | normal | 50 | 0.081 | [0.035, 0.128] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | twap | high_volatility | 50 | -0.409 | [-1.043, 0.224] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | twap | high_volatility | 50 | 0.142 | [-0.074, 0.359] |
| rule_guided_double_Q_m1_run2 | G0_TWAP | twap | normal | 50 | 0.034 | [-0.226, 0.294] |
| rule_guided_double_Q_m1_run2 | G1_dynamic_rule | twap | normal | 50 | 0.133 | [0.077, 0.188] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | backloaded | high_volatility | 50 | 0.286 | [-0.388, 0.960] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.075 | [-0.026, 0.177] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | backloaded | normal | 50 | 0.004 | [-0.219, 0.226] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | backloaded | normal | 50 | 0.005 | [-0.044, 0.055] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | bursty | high_volatility | 50 | -0.466 | [-1.211, 0.278] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | -0.027 | [-0.345, 0.290] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | bursty | normal | 50 | 0.024 | [-0.191, 0.240] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | frontloaded | high_volatility | 50 | -0.174 | [-0.807, 0.459] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.129 | [-0.111, 0.370] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | frontloaded | normal | 50 | 0.079 | [-0.203, 0.361] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 0.040 | [-0.026, 0.107] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | randomized | high_volatility | 50 | -0.613 | [-1.378, 0.152] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.168 | [-0.006, 0.341] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | randomized | normal | 50 | -0.072 | [-0.314, 0.169] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | randomized | normal | 50 | 0.063 | [0.016, 0.110] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | twap | high_volatility | 50 | -0.573 | [-1.096, -0.050] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | twap | high_volatility | 50 | -0.021 | [-0.057, 0.015] |
| rule_guided_double_Q_m1_run3 | G0_TWAP | twap | normal | 50 | 0.001 | [-0.303, 0.305] |
| rule_guided_double_Q_m1_run3 | G1_dynamic_rule | twap | normal | 50 | 0.100 | [-0.012, 0.212] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | backloaded | high_volatility | 50 | 0.263 | [-0.408, 0.934] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.052 | [-0.036, 0.140] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | backloaded | normal | 50 | 0.016 | [-0.228, 0.260] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | backloaded | normal | 50 | 0.018 | [-0.065, 0.101] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | bursty | high_volatility | 50 | -0.341 | [-1.045, 0.363] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.098 | [-0.110, 0.306] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | bursty | normal | 50 | 0.045 | [-0.180, 0.269] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.020 | [-0.009, 0.049] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | frontloaded | high_volatility | 50 | -0.275 | [-1.003, 0.454] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.028 | [-0.070, 0.127] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | frontloaded | normal | 50 | 0.073 | [-0.196, 0.342] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 0.035 | [0.007, 0.062] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | randomized | high_volatility | 50 | -0.723 | [-1.529, 0.083] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.057 | [-0.043, 0.158] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | randomized | normal | 50 | -0.121 | [-0.363, 0.122] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | randomized | normal | 50 | 0.015 | [-0.043, 0.072] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | twap | high_volatility | 50 | -0.390 | [-1.031, 0.251] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 0.162 | [-0.065, 0.388] |
| rule_guided_double_Q_m1_run4 | G0_TWAP | twap | normal | 50 | 0.056 | [-0.214, 0.327] |
| rule_guided_double_Q_m1_run4 | G1_dynamic_rule | twap | normal | 50 | 0.155 | [0.087, 0.223] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | backloaded | high_volatility | 50 | 0.470 | [-0.264, 1.203] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.259 | [0.080, 0.438] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | backloaded | normal | 50 | 0.008 | [-0.213, 0.230] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | backloaded | normal | 50 | 0.010 | [-0.040, 0.060] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | bursty | high_volatility | 50 | -0.353 | [-1.072, 0.367] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.086 | [-0.135, 0.308] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | bursty | normal | 50 | 0.024 | [-0.191, 0.240] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | frontloaded | high_volatility | 50 | -0.012 | [-0.881, 0.856] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.291 | [-0.025, 0.607] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | frontloaded | normal | 50 | 0.127 | [-0.150, 0.404] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 0.089 | [0.010, 0.167] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | randomized | high_volatility | 50 | -0.700 | [-1.544, 0.145] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.081 | [-0.112, 0.274] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | randomized | normal | 50 | -0.064 | [-0.304, 0.176] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | randomized | normal | 50 | 0.071 | [0.009, 0.133] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | twap | high_volatility | 50 | -0.390 | [-1.029, 0.249] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | twap | high_volatility | 50 | 0.162 | [-0.052, 0.376] |
| rule_guided_double_Q_m1_run5 | G0_TWAP | twap | normal | 50 | -0.056 | [-0.302, 0.189] |
| rule_guided_double_Q_m1_run5 | G1_dynamic_rule | twap | normal | 50 | 0.042 | [0.005, 0.080] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | backloaded | high_volatility | 50 | 0.286 | [-0.388, 0.960] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.075 | [-0.026, 0.177] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | backloaded | normal | 50 | 0.004 | [-0.219, 0.226] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | backloaded | normal | 50 | 0.006 | [-0.044, 0.055] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | bursty | high_volatility | 50 | -0.439 | [-1.067, 0.188] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | bursty | normal | 50 | 0.024 | [-0.191, 0.240] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | frontloaded | high_volatility | 50 | -0.284 | [-1.012, 0.445] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.020 | [-0.077, 0.116] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | frontloaded | normal | 50 | 0.041 | [-0.224, 0.306] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 0.003 | [-0.008, 0.014] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | randomized | high_volatility | 50 | -0.721 | [-1.528, 0.087] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.060 | [-0.047, 0.167] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | randomized | normal | 50 | -0.098 | [-0.335, 0.138] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | randomized | normal | 50 | 0.037 | [0.002, 0.071] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | twap | high_volatility | 50 | -0.611 | [-1.139, -0.083] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | twap | high_volatility | 50 | -0.059 | [-0.145, 0.026] |
| rule_guided_double_Q_m2_run1 | G0_TWAP | twap | normal | 50 | -0.074 | [-0.315, 0.167] |
| rule_guided_double_Q_m2_run1 | G1_dynamic_rule | twap | normal | 50 | 0.025 | [0.002, 0.048] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | backloaded | high_volatility | 50 | 0.268 | [-0.403, 0.939] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.057 | [-0.032, 0.146] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | backloaded | normal | 50 | 0.007 | [-0.214, 0.229] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | backloaded | normal | 50 | 0.009 | [-0.040, 0.058] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | bursty | high_volatility | 50 | -0.439 | [-1.067, 0.188] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | bursty | normal | 50 | 0.024 | [-0.191, 0.240] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | frontloaded | high_volatility | 50 | -0.265 | [-0.990, 0.460] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.038 | [-0.027, 0.103] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | frontloaded | normal | 50 | 0.079 | [-0.203, 0.361] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.040 | [-0.026, 0.107] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | randomized | high_volatility | 50 | -0.787 | [-1.576, 0.002] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | -0.006 | [-0.071, 0.059] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | randomized | normal | 50 | -0.072 | [-0.314, 0.169] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | randomized | normal | 50 | 0.063 | [0.016, 0.109] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | twap | high_volatility | 50 | -0.588 | [-1.119, -0.058] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | twap | high_volatility | 50 | -0.037 | [-0.103, 0.029] |
| rule_guided_double_Q_m2_run2 | G0_TWAP | twap | normal | 50 | -0.047 | [-0.295, 0.200] |
| rule_guided_double_Q_m2_run2 | G1_dynamic_rule | twap | normal | 50 | 0.051 | [0.014, 0.088] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | backloaded | high_volatility | 50 | 0.280 | [-0.394, 0.954] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.069 | [-0.032, 0.170] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | backloaded | normal | 50 | 0.004 | [-0.219, 0.226] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | backloaded | normal | 50 | 0.005 | [-0.044, 0.055] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | bursty | high_volatility | 50 | -0.439 | [-1.067, 0.188] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | bursty | normal | 50 | 0.024 | [-0.191, 0.240] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | frontloaded | high_volatility | 50 | -0.305 | [-1.031, 0.422] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | -0.002 | [-0.078, 0.075] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | frontloaded | normal | 50 | 0.079 | [-0.203, 0.361] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 0.040 | [-0.026, 0.107] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | randomized | high_volatility | 50 | -0.730 | [-1.532, 0.073] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.051 | [-0.041, 0.143] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | randomized | normal | 50 | -0.072 | [-0.314, 0.169] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | randomized | normal | 50 | 0.063 | [0.016, 0.110] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | twap | high_volatility | 50 | -0.552 | [-1.075, -0.029] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | twap | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m2_run3 | G0_TWAP | twap | normal | 50 | -0.101 | [-0.337, 0.134] |
| rule_guided_double_Q_m2_run3 | G1_dynamic_rule | twap | normal | 50 | -0.003 | [-0.014, 0.009] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | backloaded | high_volatility | 50 | 0.263 | [-0.408, 0.934] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.052 | [-0.036, 0.140] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | backloaded | normal | 50 | 0.003 | [-0.219, 0.226] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | backloaded | normal | 50 | 0.005 | [-0.044, 0.054] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | bursty | high_volatility | 50 | -0.439 | [-1.067, 0.188] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | bursty | normal | 50 | 0.024 | [-0.191, 0.240] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | frontloaded | high_volatility | 50 | -0.275 | [-1.003, 0.454] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.028 | [-0.070, 0.127] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | frontloaded | normal | 50 | 0.041 | [-0.224, 0.306] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 0.003 | [-0.008, 0.014] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | randomized | high_volatility | 50 | -0.723 | [-1.529, 0.083] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.057 | [-0.043, 0.158] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | randomized | normal | 50 | -0.105 | [-0.341, 0.130] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | randomized | normal | 50 | 0.030 | [-0.004, 0.063] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | twap | high_volatility | 50 | -0.597 | [-1.126, -0.068] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | twap | high_volatility | 50 | -0.045 | [-0.114, 0.023] |
| rule_guided_double_Q_m2_run4 | G0_TWAP | twap | normal | 50 | -0.039 | [-0.292, 0.214] |
| rule_guided_double_Q_m2_run4 | G1_dynamic_rule | twap | normal | 50 | 0.059 | [0.018, 0.101] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | backloaded | high_volatility | 50 | 0.263 | [-0.407, 0.933] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.052 | [-0.030, 0.135] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | backloaded | normal | 50 | 0.008 | [-0.213, 0.230] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | backloaded | normal | 50 | 0.010 | [-0.040, 0.060] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | bursty | high_volatility | 50 | -0.439 | [-1.067, 0.188] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | bursty | normal | 50 | 0.024 | [-0.191, 0.240] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | frontloaded | high_volatility | 50 | -0.278 | [-1.006, 0.451] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.025 | [-0.072, 0.123] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | frontloaded | normal | 50 | 0.077 | [-0.205, 0.359] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 0.038 | [-0.028, 0.105] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | randomized | high_volatility | 50 | -0.720 | [-1.526, 0.085] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.060 | [-0.038, 0.158] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | randomized | normal | 50 | -0.073 | [-0.315, 0.168] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | randomized | normal | 50 | 0.062 | [0.015, 0.109] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | twap | high_volatility | 50 | -0.607 | [-1.136, -0.078] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | twap | high_volatility | 50 | -0.055 | [-0.145, 0.034] |
| rule_guided_double_Q_m2_run5 | G0_TWAP | twap | normal | 50 | -0.046 | [-0.294, 0.202] |
| rule_guided_double_Q_m2_run5 | G1_dynamic_rule | twap | normal | 50 | 0.053 | [0.014, 0.091] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | backloaded | high_volatility | 50 | 0.280 | [-0.394, 0.954] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.069 | [-0.032, 0.170] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | backloaded | normal | 50 | 0.006 | [-0.216, 0.228] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | backloaded | normal | 50 | 0.008 | [-0.040, 0.056] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | bursty | high_volatility | 50 | -0.439 | [-1.067, 0.188] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | bursty | normal | 50 | 0.024 | [-0.191, 0.240] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | frontloaded | high_volatility | 50 | -0.284 | [-1.012, 0.445] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.020 | [-0.077, 0.116] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | frontloaded | normal | 50 | 0.041 | [-0.224, 0.306] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 0.003 | [-0.008, 0.014] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | randomized | high_volatility | 50 | -0.720 | [-1.528, 0.087] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.060 | [-0.047, 0.167] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | randomized | normal | 50 | -0.105 | [-0.340, 0.130] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | randomized | normal | 50 | 0.030 | [-0.003, 0.063] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | twap | high_volatility | 50 | -0.552 | [-1.075, -0.029] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | twap | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run1 | G0_TWAP | twap | normal | 50 | -0.099 | [-0.332, 0.134] |
| rule_guided_double_Q_m5_run1 | G1_dynamic_rule | twap | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | backloaded | high_volatility | 50 | 0.264 | [-0.406, 0.935] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.053 | [-0.034, 0.141] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | backloaded | normal | 50 | 0.003 | [-0.218, 0.223] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | backloaded | normal | 50 | 0.004 | [-0.041, 0.050] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | bursty | high_volatility | 50 | -0.439 | [-1.067, 0.188] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | bursty | normal | 50 | 0.024 | [-0.191, 0.240] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | frontloaded | high_volatility | 50 | -0.265 | [-0.990, 0.460] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.038 | [-0.027, 0.103] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | frontloaded | normal | 50 | 0.082 | [-0.200, 0.364] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 0.043 | [-0.021, 0.108] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | randomized | high_volatility | 50 | -0.786 | [-1.575, 0.003] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | -0.006 | [-0.071, 0.059] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | randomized | normal | 50 | -0.075 | [-0.315, 0.166] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | randomized | normal | 50 | 0.060 | [0.017, 0.104] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | twap | high_volatility | 50 | -0.552 | [-1.075, -0.029] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | twap | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run2 | G0_TWAP | twap | normal | 50 | -0.099 | [-0.332, 0.134] |
| rule_guided_double_Q_m5_run2 | G1_dynamic_rule | twap | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | backloaded | high_volatility | 50 | 0.211 | [-0.447, 0.868] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | -0.000 | [-0.011, 0.011] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | backloaded | normal | 50 | 0.003 | [-0.219, 0.224] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | backloaded | normal | 50 | 0.004 | [-0.042, 0.051] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | bursty | high_volatility | 50 | -0.439 | [-1.067, 0.188] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | bursty | normal | 50 | 0.024 | [-0.191, 0.240] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | frontloaded | high_volatility | 50 | -0.298 | [-1.026, 0.429] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.005 | [-0.065, 0.074] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | frontloaded | normal | 50 | 0.079 | [-0.203, 0.361] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 0.041 | [-0.025, 0.106] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | randomized | high_volatility | 50 | -0.766 | [-1.556, 0.024] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.014 | [-0.033, 0.062] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | randomized | normal | 50 | -0.071 | [-0.312, 0.170] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | randomized | normal | 50 | 0.064 | [0.018, 0.110] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | twap | high_volatility | 50 | -0.552 | [-1.075, -0.029] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | twap | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run3 | G0_TWAP | twap | normal | 50 | -0.099 | [-0.332, 0.134] |
| rule_guided_double_Q_m5_run3 | G1_dynamic_rule | twap | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | backloaded | high_volatility | 50 | 0.263 | [-0.408, 0.934] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.052 | [-0.036, 0.140] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | backloaded | normal | 50 | 0.003 | [-0.218, 0.223] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | backloaded | normal | 50 | 0.004 | [-0.041, 0.050] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | bursty | high_volatility | 50 | -0.439 | [-1.067, 0.188] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | bursty | normal | 50 | 0.024 | [-0.191, 0.240] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | frontloaded | high_volatility | 50 | -0.286 | [-1.014, 0.442] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.017 | [-0.078, 0.112] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | frontloaded | normal | 50 | 0.041 | [-0.224, 0.306] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 0.003 | [-0.008, 0.014] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | randomized | high_volatility | 50 | -0.722 | [-1.528, 0.085] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.059 | [-0.042, 0.160] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | randomized | normal | 50 | -0.105 | [-0.340, 0.130] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | randomized | normal | 50 | 0.030 | [-0.003, 0.063] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | twap | high_volatility | 50 | -0.552 | [-1.075, -0.029] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run4 | G0_TWAP | twap | normal | 50 | -0.049 | [-0.297, 0.198] |
| rule_guided_double_Q_m5_run4 | G1_dynamic_rule | twap | normal | 50 | 0.050 | [0.018, 0.082] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | backloaded | high_volatility | 50 | 0.260 | [-0.410, 0.931] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.050 | [-0.033, 0.132] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | backloaded | normal | 50 | 0.007 | [-0.213, 0.228] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | backloaded | normal | 50 | 0.009 | [-0.038, 0.056] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | bursty | high_volatility | 50 | -0.439 | [-1.067, 0.188] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | bursty | normal | 50 | 0.024 | [-0.191, 0.240] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.000 | [0.000, 0.000] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | frontloaded | high_volatility | 50 | -0.285 | [-1.014, 0.443] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.018 | [-0.077, 0.113] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | frontloaded | normal | 50 | 0.081 | [-0.201, 0.364] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 0.043 | [-0.023, 0.109] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | randomized | high_volatility | 50 | -0.721 | [-1.525, 0.084] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | 0.060 | [-0.037, 0.156] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | randomized | normal | 50 | -0.075 | [-0.316, 0.166] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | randomized | normal | 50 | 0.061 | [0.015, 0.106] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | twap | high_volatility | 50 | -0.609 | [-1.137, -0.081] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | twap | high_volatility | 50 | -0.057 | [-0.143, 0.029] |
| rule_guided_double_Q_m5_run5 | G0_TWAP | twap | normal | 50 | -0.099 | [-0.332, 0.134] |
| rule_guided_double_Q_m5_run5 | G1_dynamic_rule | twap | normal | 50 | 0.000 | [0.000, 0.000] |
| selfplay_Q_A_run1 | G0_TWAP | backloaded | high_volatility | 50 | 1.552 | [0.120, 2.983] |
| selfplay_Q_A_run1 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.341 | [-0.283, 2.964] |
| selfplay_Q_A_run1 | G0_TWAP | backloaded | normal | 50 | 1.067 | [0.375, 1.759] |
| selfplay_Q_A_run1 | G1_dynamic_rule | backloaded | normal | 50 | 1.069 | [0.347, 1.791] |
| selfplay_Q_A_run1 | G0_TWAP | bursty | high_volatility | 50 | 1.074 | [-0.631, 2.780] |
| selfplay_Q_A_run1 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.513 | [-0.372, 3.399] |
| selfplay_Q_A_run1 | G0_TWAP | bursty | normal | 50 | 0.655 | [-0.079, 1.389] |
| selfplay_Q_A_run1 | G1_dynamic_rule | bursty | normal | 50 | 0.631 | [-0.144, 1.405] |
| selfplay_Q_A_run1 | G0_TWAP | frontloaded | high_volatility | 50 | 1.013 | [-0.090, 2.116] |
| selfplay_Q_A_run1 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.316 | [-0.090, 2.723] |
| selfplay_Q_A_run1 | G0_TWAP | frontloaded | normal | 50 | 1.319 | [0.690, 1.947] |
| selfplay_Q_A_run1 | G1_dynamic_rule | frontloaded | normal | 50 | 1.280 | [0.605, 1.956] |
| selfplay_Q_A_run1 | G0_TWAP | randomized | high_volatility | 50 | 1.963 | [0.694, 3.233] |
| selfplay_Q_A_run1 | G1_dynamic_rule | randomized | high_volatility | 50 | 2.744 | [1.095, 4.392] |
| selfplay_Q_A_run1 | G0_TWAP | randomized | normal | 50 | 0.470 | [-0.073, 1.014] |
| selfplay_Q_A_run1 | G1_dynamic_rule | randomized | normal | 50 | 0.606 | [0.020, 1.191] |
| selfplay_Q_A_run1 | G0_TWAP | twap | high_volatility | 50 | 1.642 | [0.734, 2.550] |
| selfplay_Q_A_run1 | G1_dynamic_rule | twap | high_volatility | 50 | 2.193 | [1.163, 3.223] |
| selfplay_Q_A_run1 | G0_TWAP | twap | normal | 50 | 1.153 | [0.606, 1.699] |
| selfplay_Q_A_run1 | G1_dynamic_rule | twap | normal | 50 | 1.251 | [0.741, 1.762] |
| selfplay_Q_A_run2 | G0_TWAP | backloaded | high_volatility | 50 | 1.146 | [-0.060, 2.352] |
| selfplay_Q_A_run2 | G1_dynamic_rule | backloaded | high_volatility | 50 | 0.936 | [-0.593, 2.464] |
| selfplay_Q_A_run2 | G0_TWAP | backloaded | normal | 50 | 0.769 | [0.175, 1.362] |
| selfplay_Q_A_run2 | G1_dynamic_rule | backloaded | normal | 50 | 0.771 | [0.095, 1.446] |
| selfplay_Q_A_run2 | G0_TWAP | bursty | high_volatility | 50 | 0.629 | [-0.607, 1.864] |
| selfplay_Q_A_run2 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.068 | [-0.309, 2.444] |
| selfplay_Q_A_run2 | G0_TWAP | bursty | normal | 50 | 0.536 | [-0.040, 1.113] |
| selfplay_Q_A_run2 | G1_dynamic_rule | bursty | normal | 50 | 0.512 | [-0.135, 1.159] |
| selfplay_Q_A_run2 | G0_TWAP | frontloaded | high_volatility | 50 | 0.574 | [-0.140, 1.288] |
| selfplay_Q_A_run2 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 0.877 | [-0.400, 2.154] |
| selfplay_Q_A_run2 | G0_TWAP | frontloaded | normal | 50 | 1.194 | [0.672, 1.716] |
| selfplay_Q_A_run2 | G1_dynamic_rule | frontloaded | normal | 50 | 1.156 | [0.551, 1.760] |
| selfplay_Q_A_run2 | G0_TWAP | randomized | high_volatility | 50 | 1.531 | [0.454, 2.609] |
| selfplay_Q_A_run2 | G1_dynamic_rule | randomized | high_volatility | 50 | 2.312 | [0.826, 3.798] |
| selfplay_Q_A_run2 | G0_TWAP | randomized | normal | 50 | 0.254 | [-0.209, 0.718] |
| selfplay_Q_A_run2 | G1_dynamic_rule | randomized | normal | 50 | 0.389 | [-0.137, 0.916] |
| selfplay_Q_A_run2 | G0_TWAP | twap | high_volatility | 50 | 1.110 | [0.382, 1.837] |
| selfplay_Q_A_run2 | G1_dynamic_rule | twap | high_volatility | 50 | 1.661 | [0.591, 2.731] |
| selfplay_Q_A_run2 | G0_TWAP | twap | normal | 50 | 1.061 | [0.470, 1.652] |
| selfplay_Q_A_run2 | G1_dynamic_rule | twap | normal | 50 | 1.160 | [0.543, 1.777] |
| selfplay_Q_A_run3 | G0_TWAP | backloaded | high_volatility | 50 | 1.666 | [0.196, 3.135] |
| selfplay_Q_A_run3 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.455 | [-0.265, 3.175] |
| selfplay_Q_A_run3 | G0_TWAP | backloaded | normal | 50 | 0.752 | [0.140, 1.364] |
| selfplay_Q_A_run3 | G1_dynamic_rule | backloaded | normal | 50 | 0.754 | [0.092, 1.416] |
| selfplay_Q_A_run3 | G0_TWAP | bursty | high_volatility | 50 | 1.178 | [-0.445, 2.802] |
| selfplay_Q_A_run3 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.617 | [-0.211, 3.446] |
| selfplay_Q_A_run3 | G0_TWAP | bursty | normal | 50 | 0.600 | [-0.119, 1.319] |
| selfplay_Q_A_run3 | G1_dynamic_rule | bursty | normal | 50 | 0.576 | [-0.186, 1.337] |
| selfplay_Q_A_run3 | G0_TWAP | frontloaded | high_volatility | 50 | 1.120 | [0.086, 2.153] |
| selfplay_Q_A_run3 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.423 | [-0.062, 2.907] |
| selfplay_Q_A_run3 | G0_TWAP | frontloaded | normal | 50 | 1.352 | [0.741, 1.963] |
| selfplay_Q_A_run3 | G1_dynamic_rule | frontloaded | normal | 50 | 1.314 | [0.632, 1.996] |
| selfplay_Q_A_run3 | G0_TWAP | randomized | high_volatility | 50 | 2.257 | [0.954, 3.561] |
| selfplay_Q_A_run3 | G1_dynamic_rule | randomized | high_volatility | 50 | 3.038 | [1.238, 4.837] |
| selfplay_Q_A_run3 | G0_TWAP | randomized | normal | 50 | 0.465 | [-0.143, 1.073] |
| selfplay_Q_A_run3 | G1_dynamic_rule | randomized | normal | 50 | 0.600 | [-0.039, 1.240] |
| selfplay_Q_A_run3 | G0_TWAP | twap | high_volatility | 50 | 1.372 | [0.315, 2.429] |
| selfplay_Q_A_run3 | G1_dynamic_rule | twap | high_volatility | 50 | 1.924 | [0.685, 3.163] |
| selfplay_Q_A_run3 | G0_TWAP | twap | normal | 50 | 1.180 | [0.643, 1.718] |
| selfplay_Q_A_run3 | G1_dynamic_rule | twap | normal | 50 | 1.279 | [0.730, 1.829] |
| selfplay_Q_A_run4 | G0_TWAP | backloaded | high_volatility | 50 | 1.807 | [0.374, 3.240] |
| selfplay_Q_A_run4 | G1_dynamic_rule | backloaded | high_volatility | 50 | 1.596 | [-0.110, 3.302] |
| selfplay_Q_A_run4 | G0_TWAP | backloaded | normal | 50 | 1.164 | [0.421, 1.907] |
| selfplay_Q_A_run4 | G1_dynamic_rule | backloaded | normal | 50 | 1.166 | [0.427, 1.905] |
| selfplay_Q_A_run4 | G0_TWAP | bursty | high_volatility | 50 | 0.890 | [-0.516, 2.295] |
| selfplay_Q_A_run4 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.329 | [-0.348, 3.006] |
| selfplay_Q_A_run4 | G0_TWAP | bursty | normal | 50 | 0.738 | [0.084, 1.392] |
| selfplay_Q_A_run4 | G1_dynamic_rule | bursty | normal | 50 | 0.713 | [-0.010, 1.436] |
| selfplay_Q_A_run4 | G0_TWAP | frontloaded | high_volatility | 50 | 1.690 | [0.222, 3.157] |
| selfplay_Q_A_run4 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 1.993 | [0.291, 3.695] |
| selfplay_Q_A_run4 | G0_TWAP | frontloaded | normal | 50 | 1.771 | [1.038, 2.504] |
| selfplay_Q_A_run4 | G1_dynamic_rule | frontloaded | normal | 50 | 1.733 | [0.989, 2.477] |
| selfplay_Q_A_run4 | G0_TWAP | randomized | high_volatility | 50 | 2.294 | [1.004, 3.585] |
| selfplay_Q_A_run4 | G1_dynamic_rule | randomized | high_volatility | 50 | 3.075 | [1.379, 4.771] |
| selfplay_Q_A_run4 | G0_TWAP | randomized | normal | 50 | 0.578 | [-0.073, 1.229] |
| selfplay_Q_A_run4 | G1_dynamic_rule | randomized | normal | 50 | 0.713 | [0.042, 1.385] |
| selfplay_Q_A_run4 | G0_TWAP | twap | high_volatility | 50 | 1.962 | [0.695, 3.228] |
| selfplay_Q_A_run4 | G1_dynamic_rule | twap | high_volatility | 50 | 2.514 | [1.141, 3.886] |
| selfplay_Q_A_run4 | G0_TWAP | twap | normal | 50 | 1.507 | [0.758, 2.255] |
| selfplay_Q_A_run4 | G1_dynamic_rule | twap | normal | 50 | 1.605 | [0.897, 2.313] |
| selfplay_Q_A_run5 | G0_TWAP | backloaded | high_volatility | 50 | 2.589 | [0.601, 4.578] |
| selfplay_Q_A_run5 | G1_dynamic_rule | backloaded | high_volatility | 50 | 2.378 | [0.184, 4.573] |
| selfplay_Q_A_run5 | G0_TWAP | backloaded | normal | 50 | 1.514 | [0.705, 2.324] |
| selfplay_Q_A_run5 | G1_dynamic_rule | backloaded | normal | 50 | 1.516 | [0.699, 2.334] |
| selfplay_Q_A_run5 | G0_TWAP | bursty | high_volatility | 50 | 0.862 | [-0.437, 2.162] |
| selfplay_Q_A_run5 | G1_dynamic_rule | bursty | high_volatility | 50 | 1.301 | [-0.234, 2.836] |
| selfplay_Q_A_run5 | G0_TWAP | bursty | normal | 50 | 0.666 | [0.019, 1.312] |
| selfplay_Q_A_run5 | G1_dynamic_rule | bursty | normal | 50 | 0.641 | [-0.043, 1.326] |
| selfplay_Q_A_run5 | G0_TWAP | frontloaded | high_volatility | 50 | 1.725 | [0.089, 3.362] |
| selfplay_Q_A_run5 | G1_dynamic_rule | frontloaded | high_volatility | 50 | 2.028 | [0.229, 3.828] |
| selfplay_Q_A_run5 | G0_TWAP | frontloaded | normal | 50 | 2.013 | [1.191, 2.835] |
| selfplay_Q_A_run5 | G1_dynamic_rule | frontloaded | normal | 50 | 1.975 | [1.151, 2.798] |
| selfplay_Q_A_run5 | G0_TWAP | randomized | high_volatility | 50 | 2.321 | [0.764, 3.878] |
| selfplay_Q_A_run5 | G1_dynamic_rule | randomized | high_volatility | 50 | 3.102 | [1.096, 5.108] |
| selfplay_Q_A_run5 | G0_TWAP | randomized | normal | 50 | 0.634 | [-0.104, 1.371] |
| selfplay_Q_A_run5 | G1_dynamic_rule | randomized | normal | 50 | 0.769 | [0.039, 1.499] |
| selfplay_Q_A_run5 | G0_TWAP | twap | high_volatility | 50 | 2.471 | [1.012, 3.930] |
| selfplay_Q_A_run5 | G1_dynamic_rule | twap | high_volatility | 50 | 3.022 | [1.454, 4.591] |
| selfplay_Q_A_run5 | G0_TWAP | twap | normal | 50 | 1.575 | [0.791, 2.359] |
| selfplay_Q_A_run5 | G1_dynamic_rule | twap | normal | 50 | 1.674 | [0.910, 2.438] |

## 汇总配对差

下表将五类固定 B 对手和 50 个评估种子作为 250 个配对测试格；学习策略的 5 个训练种子先在格内取均值。成本差为学习策略减规则策略。

| 学习策略 | 规则基线 | 场景 | 配对格数 | 平均成本差 (bp) | 近似 95% 区间 |
|---|---|---|---:|---:|---:|
| G2_Q_learning_existing | G0_TWAP | normal | 250 | 1.508 | [1.084, 1.933] |
| G2_Q_learning_existing | G0_TWAP | high_volatility | 250 | 2.536 | [1.621, 3.450] |
| G2_Q_learning_existing | G1_dynamic_rule | normal | 250 | 1.543 | [1.123, 1.962] |
| G2_Q_learning_existing | G1_dynamic_rule | high_volatility | 250 | 2.908 | [1.907, 3.910] |
| G3_opponent_aware_Q_existing | G0_TWAP | normal | 250 | 1.437 | [1.046, 1.828] |
| G3_opponent_aware_Q_existing | G0_TWAP | high_volatility | 250 | 2.347 | [1.527, 3.166] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | normal | 250 | 1.472 | [1.088, 1.855] |
| G3_opponent_aware_Q_existing | G1_dynamic_rule | high_volatility | 250 | 2.720 | [1.814, 3.625] |
| cost_aligned_schedule_Q | G0_TWAP | normal | 250 | 0.859 | [0.619, 1.099] |
| cost_aligned_schedule_Q | G0_TWAP | high_volatility | 250 | 0.997 | [0.592, 1.402] |
| cost_aligned_schedule_Q | G1_dynamic_rule | normal | 250 | 0.894 | [0.645, 1.142] |
| cost_aligned_schedule_Q | G1_dynamic_rule | high_volatility | 250 | 1.370 | [0.828, 1.912] |
| rule_guided_double_Q_m0 | G0_TWAP | normal | 250 | 0.288 | [0.105, 0.470] |
| rule_guided_double_Q_m0 | G0_TWAP | high_volatility | 250 | 0.506 | [0.120, 0.891] |
| rule_guided_double_Q_m0 | G1_dynamic_rule | normal | 250 | 0.322 | [0.208, 0.436] |
| rule_guided_double_Q_m0 | G1_dynamic_rule | high_volatility | 250 | 0.878 | [0.557, 1.200] |
| rule_guided_double_Q_m0.1 | G0_TWAP | normal | 250 | 0.285 | [0.104, 0.466] |
| rule_guided_double_Q_m0.1 | G0_TWAP | high_volatility | 250 | 0.478 | [0.095, 0.861] |
| rule_guided_double_Q_m0.1 | G1_dynamic_rule | normal | 250 | 0.320 | [0.209, 0.431] |
| rule_guided_double_Q_m0.1 | G1_dynamic_rule | high_volatility | 250 | 0.851 | [0.531, 1.171] |
| rule_guided_double_Q_m0.25 | G0_TWAP | normal | 250 | 0.295 | [0.114, 0.477] |
| rule_guided_double_Q_m0.25 | G0_TWAP | high_volatility | 250 | 0.382 | [0.019, 0.745] |
| rule_guided_double_Q_m0.25 | G1_dynamic_rule | normal | 250 | 0.330 | [0.218, 0.442] |
| rule_guided_double_Q_m0.25 | G1_dynamic_rule | high_volatility | 250 | 0.755 | [0.460, 1.049] |
| rule_guided_double_Q_m0.5 | G0_TWAP | normal | 250 | 0.277 | [0.099, 0.455] |
| rule_guided_double_Q_m0.5 | G0_TWAP | high_volatility | 250 | 0.239 | [-0.145, 0.622] |
| rule_guided_double_Q_m0.5 | G1_dynamic_rule | normal | 250 | 0.312 | [0.204, 0.420] |
| rule_guided_double_Q_m0.5 | G1_dynamic_rule | high_volatility | 250 | 0.611 | [0.369, 0.854] |
| rule_guided_double_Q_m1 | G0_TWAP | normal | 250 | 0.014 | [-0.095, 0.123] |
| rule_guided_double_Q_m1 | G0_TWAP | high_volatility | 250 | -0.256 | [-0.575, 0.062] |
| rule_guided_double_Q_m1 | G1_dynamic_rule | normal | 250 | 0.048 | [0.027, 0.069] |
| rule_guided_double_Q_m1 | G1_dynamic_rule | high_volatility | 250 | 0.116 | [0.051, 0.182] |
| rule_guided_double_Q_m2 | G0_TWAP | normal | 250 | -0.011 | [-0.117, 0.096] |
| rule_guided_double_Q_m2 | G0_TWAP | high_volatility | 250 | -0.355 | [-0.659, -0.052] |
| rule_guided_double_Q_m2 | G1_dynamic_rule | normal | 250 | 0.024 | [0.008, 0.040] |
| rule_guided_double_Q_m2 | G1_dynamic_rule | high_volatility | 250 | 0.018 | [-0.015, 0.051] |
| rule_guided_double_Q_m5 | G0_TWAP | normal | 250 | -0.016 | [-0.122, 0.089] |
| rule_guided_double_Q_m5 | G0_TWAP | high_volatility | 250 | -0.355 | [-0.657, -0.052] |
| rule_guided_double_Q_m5 | G1_dynamic_rule | normal | 250 | 0.018 | [0.004, 0.033] |
| rule_guided_double_Q_m5 | G1_dynamic_rule | high_volatility | 250 | 0.018 | [-0.009, 0.045] |
| selfplay_Q_A | G0_TWAP | normal | 250 | 0.999 | [0.722, 1.277] |
| selfplay_Q_A | G0_TWAP | high_volatility | 250 | 1.538 | [0.978, 2.097] |
| selfplay_Q_A | G1_dynamic_rule | normal | 250 | 1.034 | [0.744, 1.324] |
| selfplay_Q_A | G1_dynamic_rule | high_volatility | 250 | 1.910 | [1.223, 2.597] |

## 解释限制

本比较检验的是：A 的不同执行策略面对相同固定 B 规则时的表现。双边自博弈 Q 表是在另一个学习型 B 的训练分布中得到，再冻结到相同固定对手环境测试；此项衡量迁移表现。改进候选在固定规则对手混合分布中训练。规则策略若成本更低，应如实保留为结果，不因改进候选的训练设置而宣称 Q-learning 必然更优。
当前环境仍假设每个提交的子单全额成交，并以共同可行性下界保证母单在截止前可完成；因此 100% 完成率不是不同策略的区分性证据。
成本降低是该模拟设定下的结果，不意味着真实市场中同样有效。
