# MARL 冻结策略回放前端

用 React、TypeScript、Vite、CSS Modules 和 ECharts 实现。界面以蓝色渐变、半透明卡片和联动时间轴为主。需要 Node.js 20.19+ 或 22.12+。

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
- 决策页的「本步解读」暂停播放并展示当前基金的六项运行样例。正常波动下选第 12 步的基金 A，可演示可成交限价 IOC 的部分成交与余量撤销。
- 「导入回放」兼容旧版 `schema_version: "1.0"` 和新版限价单 `"2.0"` 的冻结回放 JSON。「恢复样例」切回默认数据源。

## 数据接入

新版内置样例为 `public/limit_replay_normal.json` 和 `public/limit_replay_high_volatility.json`。两者均使用 `wuxinhan-1@a363536` 的限价单模型，以相同的第 500 回合检查点、回放种子 20261105 和单边 30 bp 手续费生成。旧版 `public/demo_frozen_episode.json` 可单独导入作历史演示。

可用同版模型的检查点重新导出两份回放。在 `multi_agent_execution` 目录执行：

```powershell
python .\export_limit_order_replay.py --output-dir ..\frontend\public
```

默认读取 `outputs/advanced_self_play_limit_orders/checkpoint_qtables_run1.json`，也可以用 `--checkpoint-file`、`--checkpoint` 和 `--source-ref` 指定来源。导出会检查冻结前后的策略哈希及成本复算。

可以在 `.env.local` 设置 `VITE_REPLAY_URL` 指向兼容的默认 JSON 地址。浏览器跨域读取时，数据服务需允许对应来源。接口结构变化集中在 `src/replay.ts` 的类型与校验函数中。

页面只展示冻结回放，Q 值来自检查点。永久冲击通过下一步中间价传导。总实施缺口与完成率对应指定的单局模拟。
