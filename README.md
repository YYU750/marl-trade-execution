# marl-trade-execution

A、B 两家机构在收盘前进行双边同步 Independent Q-learning 的多智能体交易执行仿真。当前主模型使用简化的事件驱动限价单撮合：挂单进入队列，卖方订单流消耗队列，订单可能部分成交、撤销或到期。提交量不再默认等于成交量，实际完成率作为结果报告。

## 快速运行

需要 Python 3.10 或更新版本；主模型仅使用 Python 标准库。

```powershell
cd multi_agent_execution
python .\run_experiment.py
```

默认配置为 30 分钟窗口、每 30 秒一步、A/B 各 100,000 股、单边手续费 30bp；训练使用 5 个独立种子、每个 500 回合，评估冻结检查点并交叉组合。默认输出目录为 `multi_agent_execution/outputs/advanced_self_play_limit_orders/`。

小规模运行：

```powershell
python .\run_experiment.py --episodes 40 --training-runs 2 --eval-seeds 3 --checkpoint-interval 20 --output-dir .\outputs\advanced_self_play_limit_orders_pilot
```

## 模型说明

- [限价单多智能体模型机制说明](multi_agent_execution/限价单多智能体模型机制说明.md)：状态、动作、队列、成交概率、奖励、成本和研究边界。
- [项目运行指南](multi_agent_execution/README.md)：参数、运行入口和输出文件。
- `multi_agent_execution/模型主要运行机制.md`：限价单版本之前的历史机制说明，不能代替新文档。

## 重要口径

订单流、队列深度和可见卖盘深度是合成参数，目前没有用真实逐笔行情校准。近期 1 个训练种子、500 回合、3 个评估种子的机制试跑中，最终检查点完成率约为 14%–21%；这只是小样本下的机制观察，不能据此宣称策略能够完成母单或优于规则策略。报告成本必须与完成率和未完成股数一起解读。

旧版 `outputs/advanced_self_play/` 和 `run_matched_rule_q_comparison.py` 基于提交即成交环境，不能与限价单版本直接拼表。规则策略要与新 Q 策略比较，必须在同一限价单撮合环境中重新运行。

本项目是教学仿真，不连接实时行情、账户或真实下单接口，也不构成交易建议。
