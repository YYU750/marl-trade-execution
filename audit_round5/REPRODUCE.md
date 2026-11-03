# 第五轮复现说明

## 环境

- Python 3.12.14；依赖 Python 标准库。
- Windows PowerShell 或兼容的 Python 3.10+ 环境。
- 项目不读取外部训练数据。

## 从项目目录运行

```powershell
python -m unittest discover -s tests_round5 -p 'test_*.py' -v
python run_qlearning_round5.py --train-seeds 300 --validation-seeds 60 --test-seeds 100 --seed-start 20261103 --output results_round5_standard
python run_round5_pressure.py --model results_round5_standard/q_table_selected.json --output results_round5_pressure_02 --seed-start 20261600 --seeds 100
python tools_round5/replay_selected_training_update.py
python tools_round5/replay_selected_training_episode.py --output audit_round5/selected_training_episode_trace.csv
python tools_round5/summarize_round5.py --output audit_round5/round5_key_findings_verified.json
python tools_round5/package_audit_bundle.py --output deliverables/qlearning_audit_bundle_round5_rebuild.zip
```

训练/验证/标准测试 seed 分别为 `20261103–20261402`、`20261403–20261462`、`20261463–20261562`。压力种子为 `20261600–20261699`。

训练比较四组 `(alpha, epsilon_decay)`：`(0.15,0.99)`、`(0.15,0.995)`、`(0.30,0.99)`、`(0.30,0.995)`。按验证集平均总目标成本选择候选；被选配置为 `(0.30,0.99)`。测试和压力阶段均从保存的 Q 表加载，`epsilon=0`，不更新。

输出中每个 CSV 都包含逐 seed 或逐步记录。`pressure_q_action_trace.csv` 另保留决策前 Q 值和访问次数、请求量、强制补足量及最终成交量。

结果目录必须为空或不存在；运行入口会拒绝覆盖非空目录。重跑时请换用新的输出目录。汇总脚本也拒绝覆盖已存在的回执。

测试、更新重放和汇总核验的实际命令输出分别保存在 `audit_round5/test_run_verified.log`、`audit_round5/replay_run.log`、`audit_round5/episode_replay_run.log` 和 `audit_round5/summary_run.log`。标准与压力实验结果保存在各自结果目录；这两项没有另存控制台日志。
