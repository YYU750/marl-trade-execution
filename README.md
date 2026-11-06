# marl-trade-execution

A、B 两家机构在收盘前进行双边同步 Independent Q-learning 的多智能体交易执行仿真。默认主模型使用事件驱动限价单撮合：60 个盘中时间步都由 Agent 自主选择动作，只有最后一步普通撮合之后，环境才按公开的合成冲击价格兜底完成剩余母单。该设计保证模拟任务按时结清，但不把环境兜底误称为 Agent 学会了自主完成；兜底数量和成本单独报告。

## 快速运行

需要 Python 3.10 或更新版本；主模型仅使用 Python 标准库。

```powershell
cd multi_agent_execution
python .\run_experiment.py
```

默认配置为 30 分钟窗口、每 30 秒一步、A/B 各 100,000 股、单边手续费 30bp；训练使用 5 个独立种子、每个 500 回合，评估冻结检查点并交叉组合。默认启用 `autonomous` 模式，输出目录为 `multi_agent_execution/outputs/advanced_self_play_autonomous_completion/`。该模式保留 Agent 的盘中自主决策，只在最后一步对剩余母单进行环境兜底。`--completion-mode none` 可关闭兜底作为对照，但不保证完成订单。

学习奖励还会逐步惩罚落后于均匀执行进度的剩余量，并在终局惩罚未成交量或收盘兜底依赖量。默认系数为 10 bp 和 1,000 bp；这是训练信号，不并入报告的经济交易成本。

小规模运行：

```powershell
python .\run_experiment.py --episodes 40 --training-runs 2 --eval-seeds 3 --checkpoint-interval 20 --output-dir .\outputs\advanced_self_play_limit_orders_pilot
```

## 模型说明

- [限价单多智能体模型机制说明](multi_agent_execution/限价单多智能体模型机制说明.md)：状态、动作、队列撮合、Agent 自主决策与终端完单兜底、奖励、成本和研究边界。
- [多智能体交易模型逐步运行机制详解（自主决策版）](multi_agent_execution/多智能体交易模型逐步运行机制详解_自主决策版.md)：按程序执行顺序解释初始化、状态和动作、每个 30 秒步的撮合流程、终端兜底、Q-learning 更新、训练评估与指标口径。
- [完单惩罚配对验证记录](multi_agent_execution/penalty_shaping_validation.md)：对比加入逐步进度惩罚和终局残余惩罚前后的兜底成交量与经济成本。
- [项目运行指南](multi_agent_execution/README.md)：参数、运行入口和输出文件。
- `multi_agent_execution/模型主要运行机制.md`：限价单版本之前的历史机制说明，不能代替新文档。

## 重要口径

订单流、队列深度、可见卖盘和收盘兜底价格是合成设定，没有用真实逐笔行情校准。历史试跑数据仍保存在原输出目录，仅用于回溯，不属于当前模型机制或结果。报告成本必须同时列出完成率、Maker/Taker 成交量、终端强制成交量及其成本贡献；100% 完成由环境兜底保证，不足以证明 Q-learning 优于规则策略。

旧版 `outputs/advanced_self_play/` 和 `run_matched_rule_q_comparison.py` 基于提交即成交环境，不能与限价单版本直接拼表。规则策略要与新 Q 策略比较，必须在同一限价单撮合环境中重新运行。

本项目是教学仿真，不连接实时行情、账户或真实下单接口，也不构成交易建议。
