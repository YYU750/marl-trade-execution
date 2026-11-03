# marl-trade-execution

双边同步学习的多智能体交易执行模拟研究。当前主模型让基金 A、基金 B 两个表格型 Q-learning Agent 在收盘前 30 分钟共同训练；每 30 秒同步决策，成交流共同影响市场冲击与下一时点价格。训练后通过冻结检查点交叉对局分析策略互动、训练稳定性和有限候选集最佳反应。

## 快速运行

需要 Python 3.10 或更新版本；主模型仅使用 Python 标准库。

```powershell
cd multi_agent_execution
python .\run_experiment.py
```

默认配置为 5 个独立训练种子、每个 500 回合、每 100 回合保存检查点、每个对局组合使用 30 个评估种子。完整评估覆盖正常波动和两倍波动场景。

小规模流程核对：

```powershell
python .\run_experiment.py --episodes 40 --training-runs 2 --eval-seeds 3 --checkpoint-interval 20 --output-dir .\outputs\advanced_self_play_pilot
```

详细的状态、动作、奖励、训练流程、研究结果和限制见 [主模型说明](multi_agent_execution/模型主要运行机制.md) 与 [运行指南](multi_agent_execution/README.md)。默认运行产物位于 `multi_agent_execution/outputs/advanced_self_play/`。

旧版单学习者/固定规则对手实验留在 `multi_agent_execution/run_standard_benchmark.py` 作为历史对照代码；默认入口 `run_experiment.py` 运行双边同步学习主模型。

若需比较动态规则与 Q-learning，可运行 `multi_agent_execution/run_matched_rule_q_comparison.py`；配对结果和改进候选记录在 `multi_agent_execution/outputs/matched_rule_q_comparison/`。

本项目是简化市场仿真，不连接实时行情、账户或真实下单接口。模拟结果不构成真实市场效果或交易建议。
