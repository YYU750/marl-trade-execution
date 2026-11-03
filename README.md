# 双机构交易执行模拟：Q-learning 第五轮复核

这是一个课程用的单资产、双机构执行模拟。第五轮重点复核表格型 Q-learning 的动作行为、强制完单约束和冻结策略在压力场景中的表现。当前结果显示：Bellman 更新等局部实现通过测试，但 Q-learning 的测试成本高于 TWAP；100% 完成率由环境约束保证，不能解释为策略主动执行成功。

## 环境与成本

每个 episode 有 30 个一分钟时段，A、B 各需买入 100,000 股。双方在同一只读市场快照下独立决定，随后环境统一处理行动。成交价包含半价差和即时冲击；联合成交量的永久冲击与外生随机扰动共同影响下一期中间价。环境不模拟订单簿、限价单或部分成交；冲击参数是教学假设，并非真实市场估计。

总目标成本分列已成交实施缺口、未完成机会成本、手续费和终端惩罚。完成约束开启时，行动量不足以保证期限内完单则由环境补足最低成交量。项目同时记录策略请求和实际成交，避免把约束补足归为学习策略的主动决策。

## 第五轮内容

- `src_round5/`：隔离的第五轮实现。Q-learning 更新与动作选择保持第四轮规则；增加状态—动作访问计数和行为诊断字段。
- `tests_round5/`：19 项迁移测试、12 项独立数学/环境测试和 4 项行为诊断测试。
- `results_round5_standard/`：300/60/100 个互不重叠 train/validation/test seed 的标准实验及冻结 Q 表。
- `results_round5_pressure_02/`：100 个新 seed 上 5 个冻结策略压力场景的逐 seed 结果和逐步行为轨迹。
- `results_round4_standard_02/`：只保留标准结果身份比对所需的第四轮测试动作轨迹与指标。
- `audit_round5/`：实测日志、真实训练更新重放和审计说明。
- `deliverables/round5_course_report.md`、`.docx`、`round5_course_slides.pptx`：课程报告及可编辑汇报稿。
- `deliverables/qlearning_audit_bundle_round5_final.zip`：独立复核用的精简源码、关键结果和哈希清单。

## 复现

需要 Python 3.10 或更新版本；运行代码和测试只依赖 Python 标准库。PowerShell 示例：

```powershell
python -m unittest discover -s tests_round5 -p 'test_*.py' -v
python run_qlearning_round5.py --train-seeds 300 --validation-seeds 60 --test-seeds 100 --seed-start 20261103 --output results_round5_standard_rerun
python run_round5_pressure.py --model results_round5_standard_rerun/q_table_selected.json --output results_round5_pressure_rerun --seed-start 20261600 --seeds 100
python tools_round5/replay_selected_training_update.py --output audit_round5/selected_training_update_rerun.json
python tools_round5/replay_selected_training_episode.py --output audit_round5/selected_training_episode_trace_rerun.csv
python tools_round5/summarize_round5.py --output audit_round5/round5_key_findings_rerun.json
python tools_round5/package_audit_bundle.py --output deliverables/qlearning_audit_bundle_round5_rebuild.zip
```

运行入口拒绝覆盖已经存在的输出目录。用新目录复跑。已保存的基准结果和审计回执见 `results_round5_standard/`、`results_round5_pressure_02/` 与 `audit_round5/`。

## 结果摘要

标准测试成本（按初始订单名义金额计，bp）：Q-learning 8.8491，TWAP 7.5044，价差紧迫度规则 7.7252。按相同 seed 配对，Q-learning 比 TWAP 高 1.3447 bp，95% 描述性 t 区间为 `[0.5334, 2.1560]`。测试的 3,000 个决策中，Q-learning 请求零倍配速 2,833 次；环境强制补足成交量为总成交量的 90.15%。

冻结策略的低流动性与宽价差压力场景中，测试状态均未出现在训练 Q 表，动作价值为零并导致每步请求零股。压力实验因此没有显示策略可以把训练经验外推到这两种参数。所有策略仍然显示 100% 完成，这是硬约束造成的。

## 证据边界

配对区间描述所用模拟 seed 的成本差，不是现实交易市场置信区间。状态的部分市场变量经过分箱，严格 Markov 充分性未验证。当前只有 A 学习、B 采用固定规则；没有实现双边学习或纳什均衡，也没有证明真实市场有效性。事后零请求策略只作行为诊断，不是确认性基准。完整结论与逐项状态见 `audit_round5/AUDIT_REPORT.md`。
