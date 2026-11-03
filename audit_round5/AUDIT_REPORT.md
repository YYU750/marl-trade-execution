# Q-learning 第五轮复核

## 结论

第五轮在独立副本中完成了旧测试迁移、强制成交行为诊断、冻结策略压力测试及课程交付材料。源第四轮目录、原始 19 项测试和历史结果均保留。Q-learning 策略参数与第四轮相同；第五轮只为训练状态—动作对增加访问计数，并扩展逐步日志。

| 类别 | 结论 | 依据 |
|---|---|---|
| 旧 19 项测试迁移到第五轮 API | PASS | `tests_round5/` 对应 19 项通过；原 `tests/` 未修改 |
| 12 项独立算法/环境测试 | PASS | Bellman、终止步、动作屏蔽、同步观察、成本恒等式、保存恢复等 |
| 4 项行为诊断测试 | PASS | 零倍请求与强制成交拆分、成交量复算、未见状态平局、访问计数保存恢复 |
| 第四轮标准结果复现 | PASS | 100 个 Q 测试 episode 的成本及 3,000 个动作选择与原回执逐项一致 |
| 标准测试请求/成交对账 | PASS | 3,000/3,000 行满足 `filled = clipped_request + forced_fill` |
| 真实训练更新重放 | PASS | 选中候选第 1 episode 的终止更新与原回执相同；零请求、强制成交 10,000 股 |
| 压力测试冻结与 seed 隔离 | PASS | Q 表冻结、epsilon=0、无更新；100 个压力 seed 与训练/验证/标准测试区间无重叠 |
| Q-learning 成本优于 TWAP | FAIL（真实结果） | 标准配对差 `+1.3447 bp`，95% 区间 `[+0.5334,+2.1560]` |
| 状态表示严格满足 Markov 性 | NOT VERIFIED | 中间价、价差和流动性仍按箱离散；箱内状态被合并 |
| 真实市场有效性或双边学习均衡 | NOT VERIFIED | 环境是单学习者、简化冲击假设的教学仿真 |

## 结果要点

- 标准测试：Q-learning 8.8491 bp、TWAP 7.5044 bp、价差紧迫度 7.7252 bp；三者完成率均为 100%，由 `enforce_completion=True` 保证。
- Q-learning 在 3,000 个测试决策中选择零倍配速 2,833 次；937 步被环境强制补足。强制成交量占 9,015,269/10,000,000 股，即 90.15%。
- 测试中有 472 个未被训练访问的状态决策和 782 次全零 Q 向量决策。
- 在 `20261600–20261699` 的冻结策略压力测试中，低流动性与宽价差场景各有 3,000/3,000 个状态未见；Q 每步请求 0 股，成交全部由完单约束补足。
- 标准测试 seed 上的零请求策略是事后诊断：8.9591 bp；Q-learning 低 0.1099 bp，配对区间 `[-0.1873,-0.0325]`。此比较不是事前登记结果，不能取代 TWAP 主基准。

## 统计与解释边界

成本差按共同随机 seed 配对。95% 区间描述当前仿真 seed 的差异分布；它们不代表真实市场置信区间。流动性、价差和冲击系数是模拟参数，未通过真实交易数据校准。压力下未见状态趋向全零 Q 值并选择首个合法动作，说明当前状态表的外推有限；它不是唯一可能机制的证明。

## 实际检查命令

```powershell
python -m unittest discover -s tests_round5 -p 'test_*.py' -v
python run_qlearning_round5.py --train-seeds 300 --validation-seeds 60 --test-seeds 100 --seed-start 20261103 --output results_round5_standard
python run_round5_pressure.py --model results_round5_standard/q_table_selected.json --output results_round5_pressure_02 --seed-start 20261600 --seeds 100
python tools_round5/replay_selected_training_update.py
python tools_round5/summarize_round5.py --output audit_round5/round5_key_findings_verified.json
```

实际运行环境为捆绑 Python 3.12.14；代码仅依赖标准库。测试、训练更新重放和汇总核验的命令输出分别保存在 `audit_round5/test_run.log`、`audit_round5/replay_run.log` 和 `audit_round5/summary_run.log`。标准与压力实验的完整结果保存在各自结果目录中；没有另存标准/压力命令的控制台日志。
