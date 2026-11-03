# 第五轮复核文件清单

## 源码

- `src_round4/`：未复制到本分支；原始工作区中的第四轮源码保持原样。本分支只包含标准结果比对所需的 `results_round4_standard_02/test_action_trace.csv` 与 `test_metrics.csv`。
- `src_round5/execution_sim/qlearning.py`：仅增加状态—动作更新次数与保存/加载字段；Q-learning 更新、动作选择规则不变。
- `src_round5/execution_sim/qexperiment.py`：新增决策前 Q 值、访问次数、未见状态、请求裁切量和环境补足量日志。
- `run_qlearning_round5.py`：同配置诊断重跑入口。
- `run_round5_pressure.py`：冻结 Q 表的压力评估入口。
- `tools_round5/replay_selected_training_update.py`：重放一条真实训练终止更新。
- `tools_round5/replay_selected_training_episode.py`：重放选中候选第1训练episode并保存完整30步Q更新轨迹。
- `tools_round5/summarize_round5.py`：标准重跑一致性、动作/成交对账及 seed 隔离检查。
- `tools_round5/package_audit_bundle.py`：生成精简审计复核包并校验 ZIP CRC。

## 测试

- `tests_round5/test_qlearning.py`、`tests_round5/test_simulation.py`：旧 19 项测试的第五轮 API 迁移副本。
- `tests_round5/test_independent_audit.py`：12 项独立数学与环境用例的第五轮导入副本。
- `tests_round5/test_behavior_diagnostics.py`：4 项第五轮新增行为诊断。
- 原研究目录中的第四轮完整源码、`tests/` 与 `audit_round4/` 记录未修改，且不属于本分支；本分支提供迁移后的第五轮测试。

## 结果与课程材料

- `results_round5_standard/`：300/60/100 标准重跑、冻结 Q 表、测试逐步轨迹和关键发现。
- `results_round5_pressure_02/`：100 个压力 seed、五个情景、逐 seed 结果、配对差及 Q 行为轨迹。
- `audit_round5/selected_training_update_full.json`：实际更新重放。
- `audit_round5/selected_training_episode_trace.csv`：完整单episode训练轨迹，包含每步状态、行动、奖励和Q更新。
- `audit_round5/test_run.log`、`audit_round5/test_run_verified.log`、`audit_round5/test_run_clone.log`、`audit_round5/replay_run.log`、`audit_round5/episode_replay_run.log`、`audit_round5/summary_run.log`：35项测试及审计脚本的实际命令输出。
- `deliverables/round5_course_report.md`：课程报告 Markdown 主稿。
- `deliverables/round5_course_report.docx`：可编辑 Word 报告。
- `deliverables/round5_course_slides.pptx`：10 页汇报文件。
- `deliverables/qlearning_audit_bundle_round5_final.zip`：独立二次审计的精简源码、关键结果、完整训练episode和哈希清单。

## 未打包文件

无原始市场数据、虚拟环境、密钥或远端服务器文件。ABIDES 源码没有复制，项目只复用算法思想。
