# marl-trade-execution

多智能体交易执行模拟研究项目。当前可运行实现位于 [multi_agent_execution/](multi_agent_execution/)，围绕收盘前 30 分钟的双机构母单执行，使用 30 秒决策步长（共 60 步），比较固定 TWAP、动态规则、Q-learning 和对手感知 Q-learning。

## 快速开始

需要 Python 3.10 或更新版本；项目仅使用 Python 标准库，无需安装第三方依赖。

    cd multi_agent_execution
    python .\run_experiment.py

快速检查可运行较小规模：

    python .\run_experiment.py --episodes 100 --seeds 5

运行说明、模型假设、实验场景和输出字段见 [multi_agent_execution/README.md](multi_agent_execution/README.md)。模型的状态、动作、奖励和逐步运行流程见 [multi_agent_execution/模型主要运行机制.md](multi_agent_execution/模型主要运行机制.md)。实验结果和训练后的 Q 表保存在 multi_agent_execution/outputs/。

进阶版双 Q-learning 自博弈也已实现为独立实验，训练 A、B 两个学习型策略并评估冻结检查点的交叉对局、训练稳定性和候选集最佳反应；它不改变标准版固定规则对手基准。运行命令：

    cd multi_agent_execution
    python .\run_advanced_self_play.py

进阶版输出单独保存在 `multi_agent_execution/outputs/advanced_self_play/`。完整运行方式与研究边界见项目说明。

本项目是可复现的模拟研究，不连接实时行情、账户或真实下单接口。研究假设需要通过运行结果检验，不应将模拟结论解读为真实交易建议。
