# 完单惩罚改进：配对验证记录

## 改动机制

在每个普通撮合步结束后，根据撮合后的剩余母单和剩余时间计算进度缺口：

```text
deficit = max(0, remaining_after_fill - base_slice * steps_after)
step_penalty = 10 bp * deficit / order_size
```

若 Agent 落后于均匀进度，Q-learning 会在该步收到相应惩罚；越接近截止时间，剩余计划容量越小，同样的库存会表现为更大的进度缺口。第 60 步另对普通撮合后的残余量施加 `1,000 bp * residual / order_size` 的终局惩罚。自主完单模式中的 residual 是交给收盘兜底的数量。

惩罚只用于学习，不记入经济交易成本。60 个盘中动作仍完全由 Agent 自主选择；环境只在最后一步普通撮合后执行原有收盘兜底，所以最终模拟完成率仍由环境兜底保证。

## 配对试验设置

两组使用相同模型、手续费、训练预算、训练种子和配对评估种子。基准组关闭进度及终局残余惩罚（0/0 bp）；改进组使用默认系数（10/1,000 bp）。每组训练 5 个独立运行，每个 500 回合；比较最终 A/B 检查点，在正常波动和两倍波动场景各使用 30 个配对评估种子。每个场景每方共 150 个配对评估回合。单边手续费为 30 bp。

复现时分别执行：

```powershell
python .\run_advanced_self_play.py --episodes 500 --training-runs 5 --eval-seeds 30 --checkpoint-interval 100 --seed 20261107 --schedule-deficit-penalty-bps 0 --terminal-unfilled-penalty-bps 0 --output-dir .\outputs\penalty_comparison_unshaped_500x5x30
python .\run_advanced_self_play.py --episodes 500 --training-runs 5 --eval-seeds 30 --checkpoint-interval 100 --seed 20261107 --schedule-deficit-penalty-bps 10 --terminal-unfilled-penalty-bps 1000 --output-dir .\outputs\penalty_comparison_shaped_500x5x30
```

指标是最终检查点自我对局中的均值。强制成交量是第 60 步普通限价撮合后交给收盘兜底的股数；经济成本包含实际成交、手续费和市场冲击，不包含学习惩罚。

## 结果

| 场景 | Agent | 无惩罚：兜底股数 | 新惩罚：兜底股数 | 变化 | 无惩罚：成本 (bp) | 新惩罚：成本 (bp) | 成本变化 (bp) |
|---|---|---:|---:|---:|---:|---:|---:|
| 正常波动 | A | 83,566 | 64,470 | -19,096 (-22.9%) | 59.005 | 51.178 | -7.827 |
| 正常波动 | B | 82,783 | 62,937 | -19,845 (-24.0%) | 58.764 | 50.841 | -7.923 |
| 两倍波动 | A | 82,561 | 63,933 | -18,629 (-22.6%) | 56.442 | 49.296 | -7.146 |
| 两倍波动 | B | 82,788 | 60,640 | -22,148 (-26.8%) | 56.559 | 48.391 | -8.168 |

两组完成率均为 100%，因为 autonomous 模式保留终端兜底。引入惩罚后，四种“机构 × 场景”组合的平均兜底量都下降，配对经济成本均值也下降；按训练种子分别汇总时，五个训练运行的改善方向也一致。尽管如此，改进组平均仍有约 60,000–64,000 股由收盘兜底完成；这说明 Q-learning 减少了兜底依赖，但尚未做到完全自主成交。

## 结果边界

- 这是合成限价订单簿中的模拟结果，不是对真实市场成交概率的估计。
- 每种设置使用 5 个训练种子和 30 个配对评估种子，适合作为课程项目的改进验证，不足以支持普遍性或实盘效果结论。
- 完成率 100% 仍是环境兜底的结果；评价 Agent 本身应同时看自主成交量、兜底成交量和经济成本。
- 完整逐回合结果及配置保存在 `outputs/penalty_comparison_unshaped_500x5x30/` 和 `outputs/penalty_comparison_shaped_500x5x30/`，其中 `run_manifest.json` 记录各组参数。
