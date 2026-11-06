# marl-trade-execution

A、B 两家机构在收盘前进行双边同步 Independent Q-learning 的多智能体交易执行仿真。当前主模型使用事件驱动限价单撮合和方案 C 完单机制：前期自主报价，落后进度时逐级提高限价的可成交范围，最后一步对剩余母单按公开的合成冲击价格强制完成。C 模式在模拟环境内保证按时完成全部订单，并单独报告强制成交量与成本；这项保证来自环境兜底，不代表真实市场必然有流动性。

## 快速运行

需要 Python 3.10 或更新版本；主模型仅使用 Python 标准库。

```powershell
cd multi_agent_execution
python .\run_experiment.py
```

默认配置为 30 分钟窗口、每 30 秒一步、A/B 各 100,000 股、单边手续费 30bp；训练使用 5 个独立种子、每个 500 回合，评估冻结检查点并交叉组合。默认启用 C 模式，输出目录为 `multi_agent_execution/outputs/advanced_self_play_completion_c/`。使用 `--completion-mode none` 可运行无兜底对照，但该模式不保证完成订单。

小规模运行：

```powershell
python .\run_experiment.py --episodes 40 --training-runs 2 --eval-seeds 3 --checkpoint-interval 20 --output-dir .\outputs\advanced_self_play_limit_orders_pilot
```

## 模型说明

- [限价单多智能体模型机制说明](multi_agent_execution/限价单多智能体模型机制说明.md)：状态、动作、队列撮合、方案 C 截止加急与收盘兜底、奖励、成本和研究边界。
- [多智能体交易模型逐步运行机制详解（方案 C）](multi_agent_execution/多智能体交易模型逐步运行机制详解_方案C.md)：按程序执行顺序解释初始化、状态和动作、每个 30 秒步的撮合流程、Q-learning 更新、训练评估与指标口径。
- [项目运行指南](multi_agent_execution/README.md)：参数、运行入口和输出文件。
- `multi_agent_execution/模型主要运行机制.md`：限价单版本之前的历史机制说明，不能代替新文档。

## 重要口径

订单流、队列深度、可见卖盘和收盘兜底价格是合成设定，没有用真实逐笔行情校准。方案 C 的小规模试跑已在模拟中完成全部订单，但仍有较多股数依赖收盘兜底；结果只用于核对机制及成本记录，不能据此宣称 Q-learning 优于规则策略。报告成本必须同时列出完成率、主动成交量和强制成交量。C 模式试跑记录见 `multi_agent_execution/outputs/deadline_completion_c_validation/`；无兜底对照见 `multi_agent_execution/outputs/deadline_no_completion_validation/`。

旧版 `outputs/advanced_self_play/` 和 `run_matched_rule_q_comparison.py` 基于提交即成交环境，不能与限价单版本直接拼表。规则策略要与新 Q 策略比较，必须在同一限价单撮合环境中重新运行。

本项目是教学仿真，不连接实时行情、账户或真实下单接口，也不构成交易建议。
