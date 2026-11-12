# MARL 冻结策略回放前端

用 React、TypeScript、Vite、CSS Modules 和 ECharts 实现。界面以蓝色渐变、半透明卡片和联动时间轴为主。需要 Node.js 20.19+ 或 22.12+。

逐页操作、指标、动作和理论说明见[使用说明书](使用说明书.md)。

## 本地运行

在本目录执行：

```powershell
npm install
npm run dev
```

打开终端打印的本地地址。生产构建执行 `npm run build`，生成静态目录 `dist/`，可用 `npm run preview` 本地预览。

## 演示

- 新版总览从有新订单部分成交的第一步打开。播放、暂停、切换前后步、拖动时间轴或调整倍速都会联动 A/B 决策与市场反馈。
- 左右键逐步切换，空格播放或暂停。点击中间价图的绘图区可跳到最近的时间步。「市场与成本」可切换当步拆分和累计至当前步的已成交成本。
- 「回放配置」显示执行窗口、母单、手续费和策略来源参数。正常波动与两倍波动会各自加载一份完整的预生成回放。
- 「决策详情」展示状态、各档 Q 值、访问次数、最终选择及其成交结果。市场页区分提交、实际成交、排队、撤单和到期。回合总结按实际成交计算完成率，费用明细包含期末未成交机会成本。
- 决策页的「本步解读」暂停播放并展示当前基金的六项运行样例。当前正常波动样例中，第 19 步的基金 A 展示买一限价部分成交，第 43 步展示 IOC 余量撤销。
- 「导入回放」兼容旧版 `schema_version: "1.0"` 和新版限价单 `"2.0"` 的冻结回放 JSON。「恢复样例」切回默认数据源。

## 数据接入

新版内置样例为 `public/limit_replay_normal.json` 和 `public/limit_replay_high_volatility.json`。两者均使用 `wuxinhan-1@7906ab8` 的期末兜底模式，以相同的第 500 回合检查点、回放种子 20261105 和单边 30 bp 手续费生成。第 60 步总览显示撮合后的期末剩余，决策页仍展示决策前状态。回合总结单列兜底股数及其已计入总成本的贡献。旧版 `public/demo_frozen_episode.json` 可单独导入作历史演示。

### 从干净克隆重新生成内置回放

仓库保留了内置回放实际使用的[检查点](../multi_agent_execution/replay_reference/checkpoint_qtables_run1.json)和[训练清单](../multi_agent_execution/replay_reference/run_manifest.json)。在 `multi_agent_execution` 目录执行以下命令即可用固定输入重建两份样例：

```powershell
python .\export_limit_order_replay.py --checkpoint-file .\replay_reference\checkpoint_qtables_run1.json --source-ref wuxinhan-1@7906ab8 --output-dir ..\frontend\public
```

导出器默认读取检查点旁的 `run_manifest.json`，也可用 `--manifest-file` 指定清单。它会核对清单记录的检查点 SHA-256，在两份 JSON 的 `provenance` 中写入检查点和清单的文件名及各自的 SHA-256，并检查策略表在回放前后是否一致。可用 PowerShell 的 `Get-FileHash -Algorithm SHA256` 对原文件复核。旧的已导出回放仍可导入前端。训练清单没有检查点摘要的旧训练产物，需要重新训练才能用新版导出器生成带出处的回放。

### 从头训练再导出

在 `multi_agent_execution` 目录运行以下命令。训练命令会生成检查点及配套清单，导出到独立目录后可用网页的「导入回放」查看：

```powershell
python .\run_experiment.py --episodes 500 --training-runs 1 --eval-seeds 1 --checkpoint-interval 500 --seed 20261103 --fee-bps 30 --completion-mode autonomous
python .\export_limit_order_replay.py --output-dir .\outputs\advanced_self_play_autonomous_completion\replays
```

### 学习型方案 C 回放

在「回放配置」中选择「方案 C · 正常波动」或「方案 C · 两倍波动」。决策页分别显示普通策略的候选动作与 Q 值、方案 C 的加急报价和追加提交量，以及普通撮合和环境兜底的成交量。回合总结汇总主动追赶次数和追加提交股数。

从 `multi_agent_execution` 目录重新训练和导出时，导出器会从匹配的训练清单识别学习型方案 C，并生成独立的预设文件。

```powershell
$out = '.\outputs\advanced_self_play_autonomous_completion\learned_c_frontend'
python .\run_experiment.py --deadline-c-mode learned --output-dir $out
python .\export_limit_order_replay.py --checkpoint-file (Join-Path $out 'checkpoint_qtables_run1.json') --source-ref frontend_UI@3f70301 --output-dir ..\frontend\public
```

训练和导出都使用相同的完单模式。两条命令加上 `--completion-mode none` 即可生成无兜底对照，导出目录也应改为 `outputs/advanced_self_play_no_completion/replays`。重新训练会产生包含新时间戳的清单，其文件哈希随之变化。需要复核内置回放的原始文件哈希时，使用随仓库提供的固定输入。

可以在 `.env.local` 设置 `VITE_REPLAY_URL` 指向兼容的默认 JSON 地址。浏览器跨域读取时，数据服务需允许对应来源。接口结构变化集中在 `src/replay.ts` 的类型与校验函数中。

页面只展示冻结回放，Q 值来自检查点。永久冲击通过下一步中间价传导。总实施缺口与完成率对应指定的单局模拟。

## 分支审查范围

`frontend_UI` 将限价单撮合、训练与完单机制、冻结回放导出和 React 前端集成在同一分支。相对 `codex/agent-demo-integration`，审查时需要同时复核后端撮合与训练口径、回放数据来源和前端交互。可用 `git log --left-right --oneline origin/frontend_UI...origin/codex/agent-demo-integration` 查看两边各自的提交。
