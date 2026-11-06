import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent, type CSSProperties, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { ActionChart, CumulativeCostChart, ImpactChart, PriceChart } from './Charts'
import { decisionReason, OrderEvents, StepExplanation } from './StepExplanation'
import {
  actionLabels, agents, aggregateCosts, bp, componentLabels, costComponents, fillQuantity,
  duration, num, parseReplay, percent, replayActions, scenarioLabel, shares, signed,
  type Agent, type Costs, type Replay,
} from './replay'
import styles from './Dashboard.module.css'

const pages = [
  { id: 'overview', label: '总览回放', title: '双智能体同步回放', icon: 'play' },
  { id: 'decision', label: '智能体决策', title: '智能体决策', icon: 'decision' },
  { id: 'market', label: '市场与成本', title: '市场反馈与执行成本', icon: 'chart' },
  { id: 'summary', label: '回合总结', title: '回合总结', icon: 'layers' },
] as const
type Page = typeof pages[number]['id']
type IconName = typeof pages[number]['icon'] | 'snowflake' | 'upload' | 'pause' | 'previous' | 'next' | 'lock' | 'check' | 'arrow' | 'bank' | 'settings'
const paths: Record<IconName, ReactNode> = {
  snowflake: <path d="M12 2v20M3.34 7l17.32 10M3.34 17l17.32-10M9 4l3 3 3-3m-6 16 3-3 3 3M4 10l4-1-1-4m10 14-1-4 4-1M4 14l4 1-1 4M17 5l-1 4 4 1"/>,
  play: <path d="m8 5 12 7-12 7Z"/>,
  decision: <><rect x="4" y="4" width="16" height="16" rx="4"/><path d="M9 8v8m6-8v8M7 11h4m2 2h4"/></>,
  chart: <><path d="M3 18h18M4 14l5-5 4 3 6-7"/><path d="M15 5h4v4"/></>,
  layers: <><path d="m12 3 9 5-9 5-9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/></>,
  upload: <><path d="M12 16V4m-4 4 4-4 4 4M4 15v5h16v-5"/></>,
  pause: <><path d="M9 5v14m6-14v14"/></>,
  previous: <path d="M6 5v14m12-14-10 7 10 7Z"/>,
  next: <path d="M18 5v14M6 5l10 7-10 7Z"/>,
  lock: <><rect x="5" y="10" width="14" height="11" rx="3"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/></>,
  check: <path d="m5 12 4 4L19 6"/>,
  arrow: <path d="M4 12h15m-6-6 6 6-6 6"/>,
  bank: <><path d="m3 8 9-5 9 5ZM4 20h16M7 11v6m5-6v6m5-6v6"/></>,
  settings: <><path d="M3 7h7m4 0h7M3 17h3m4 0h11"/><circle cx="12" cy="7" r="2"/><circle cx="8" cy="17" r="2"/></>,
}
function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}

function Heading({ children, icon }: { children: ReactNode; icon: IconName }) {
  return <h2 className={styles.panelTitle}><Icon name={icon} />{children}</h2>
}

function Metrics({ values }: { values: [string, ReactNode][] }) {
  return <dl className={styles.metrics}>{values.map(([label, value]) =>
    <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
  )}</dl>
}

function CostTable({ a, b, totals, limit, opportunity }: {
  a: Costs; b: Costs; totals: [number, number]; limit: boolean; opportunity?: [number, number]
}) {
  return <div className={styles.tableWrap}><table className={styles.table}>
    <thead><tr><th scope="col">成本项</th><th scope="col">基金 A · bp</th><th scope="col">基金 B · bp</th></tr></thead>
    <tbody>
      {costComponents(limit).map(component => <tr key={component}>
        <th scope="row">{componentLabels[component]}</th>
        <td>{signed(a[component] ?? 0, 4)}</td><td>{signed(b[component] ?? 0, 4)}</td>
      </tr>)}
      {opportunity && <tr><th scope="row">未成交机会成本</th>
        <td>{signed(opportunity[0], 4)}</td><td>{signed(opportunity[1], 4)}</td></tr>}
      <tr className={styles.total}><th scope="row">实施缺口</th><td>{num(totals[0], 4)}</td><td>{num(totals[1], 4)}</td></tr>
    </tbody>
  </table></div>
}

const scenarios = ['normal', 'high_volatility'] as const
type Scenario = typeof scenarios[number]
const presetUrl = (scenario: Scenario) => `${import.meta.env.BASE_URL}limit_replay_${scenario}.json`

function ReplayConfig({ replay, onScenario, preset }: {
  replay: Replay; onScenario: (scenario: Scenario) => Promise<void>; preset: Scenario | null
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [pending, setPending] = useState<Scenario | null>(null)
  const [error, setError] = useState('')
  const config = replay.config
  async function changeScenario(scenario: Scenario) {
    setPending(scenario)
    setError('')
    try {
      await onScenario(scenario)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '读取回放失败')
      setPending(null)
    }
  }
  return <>
    <button className={styles.button} onClick={() => { setError(''); dialog.current?.showModal() }}>
      <Icon name="settings" size={16} />回放配置
    </button>
    <dialog ref={dialog} aria-labelledby="replay-config-title" className={`${styles.glass} ${styles.configDialog}`}
      onCancel={event => { if (pending) event.preventDefault() }}>
      <div className={styles.panelHead}>
        <h2 id="replay-config-title" className={styles.panelTitle}><Icon name="settings" />回放配置</h2>
        <button className={styles.button} disabled={pending !== null} onClick={() => dialog.current?.close()}>关闭配置</button>
      </div>
      <dl className={styles.configFacts}>
        <div><dt>模拟标的</dt><dd>{config.asset_symbol ?? '单一模拟资产'}</dd></div>
        <div><dt>执行方向</dt><dd>买入 BUY</dd></div>
        <div><dt>执行窗口</dt><dd>{config.window_minutes} 分钟</dd></div>
        <div><dt>单边手续费</dt><dd>{bp(config.one_way_fee_bps, 2)}</dd></div>
        <div><dt>基金 A 母单</dt><dd>{shares(config.order_size_per_agent_shares)} 股</dd></div>
        <div><dt>基金 B 母单</dt><dd>{shares(config.order_size_per_agent_shares)} 股</dd></div>
        <div><dt>当前情景</dt><dd>{scenarioLabel(replay.scenario)}</dd></div>
        <div><dt>完单机制</dt><dd>{replay.completion_mode === 'autonomous' ? '期末兜底成交' : '无期末兜底'}</dd></div>
        <div><dt>检查点 / 种子</dt><dd>{replay.checkpoint_episode} / {replay.seed}</dd></div>
      </dl>
      <h3>内置市场情景</h3>
      <div className={styles.segmented} aria-label="选择内置回放情景">{scenarios.map(scenario =>
        <button key={scenario} aria-pressed={preset === scenario}
          disabled={pending !== null || preset === scenario} onClick={() => void changeScenario(scenario)}>
          {scenarioLabel(scenario)}{pending === scenario && ' · 载入中'}
        </button>
      )}</div>
      <p className={styles.hint}>切换情景会加载预生成的整局冻结回放。</p>
      {error && <p role="alert" className={styles.configError}>{error}</p>}
    </dialog>
  </>
}

function Timeline({ current, total, stepSeconds, playing, speed, onStep, onPlay, onSpeed }: {
  current: number; total: number; stepSeconds: number; playing: boolean; speed: number
  onStep: (index: number) => void; onPlay: () => void; onSpeed: (speed: number) => void
}) {
  const ticks = [...new Set([1, Math.ceil(total / 4), Math.ceil(total / 2), Math.ceil(total * .75), total])]
  return <section className={`${styles.glass} ${styles.timeline}`} aria-label="回放时间轴">
    <div className={styles.transport}>
      <button aria-label="上一步" title="上一步" disabled={current === 0} onClick={() => onStep(current - 1)}><Icon name="previous" size={18} /></button>
      <button className={styles.play} aria-label={playing ? '暂停回放' : '播放回放'} title={playing ? '暂停回放' : '播放回放'} onClick={onPlay} disabled={total < 2}><Icon name={playing ? 'pause' : 'play'} size={19} /></button>
      <button aria-label="下一步" title="下一步" disabled={current === total - 1} onClick={() => onStep(current + 1)}><Icon name="next" size={18} /></button>
    </div>
    <div className={styles.scrubber}>
      <label htmlFor="replay-step">回放进度 <strong>{current + 1} / {total}</strong></label>
      <input id="replay-step" type="range" min={1} max={total} value={current + 1}
        aria-valuetext={`第 ${current + 1} 步，共 ${total} 步`}
        style={{ '--progress': `${100 * current / Math.max(total - 1, 1)}%` } as CSSProperties}
        onChange={event => onStep(Number(event.currentTarget.value) - 1)} />
      <div className={styles.ticks}>{ticks.map(tick =>
        <button key={tick} style={{ left: `${100 * (tick - 1) / Math.max(total - 1, 1)}%` }}
          onClick={() => onStep(tick - 1)} aria-label={`跳至第 ${tick} 步`}>{tick}</button>
      )}</div>
    </div>
    <div className={styles.speed}>
      <select aria-label="播放速度" value={speed} onChange={event => onSpeed(Number(event.currentTarget.value))}>
        <option value={0.5}>0.5×</option><option value={1}>1×</option><option value={2}>2×</option><option value={4}>4×</option>
      </select>
      <span>每步 {stepSeconds} 秒</span>
    </div>
  </section>
}

function Dashboard({ replay, filename, onImport, onRestore, onScenario, preset }: {
  replay: Replay; filename: string; onImport: () => void; onRestore: () => void
  onScenario: (scenario: Scenario) => Promise<void>; preset: Scenario | null
}) {
  const [page, setPage] = useState<Page>('overview')
  const [agent, setAgent] = useState<Agent>('A')
  const [marketChart, setMarketChart] = useState<'impact' | 'cost'>('impact')
  const [costRange, setCostRange] = useState<'step' | 'cumulative'>('step')
  const [current, setCurrent] = useState(() => {
    if (replay.schema_version === '1.0') return Math.min(17, replay.steps.length - 1)
    const partial = replay.steps.findIndex(step => agents.some(id => {
      const entry = step.agents[id]
      return fillQuantity(entry) > 0 && fillQuantity(entry) + 1e-6 < entry.decision.selected_quantity_shares
    }))
    return Math.max(0, partial)
  })
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const length = replay.steps.length
  const row = replay.steps[current]
  const { market_transition: market } = row
  const active = row.agents[agent]
  const selected = active.decision
  const limit = replay.schema_version === '2.0'
  const finalStep = current === length - 1
  const overviewRemaining = (id: Agent) => finalStep ? replay.summary[`${id}_unfilled_shares`]
    : row.agents[id].observation.own_remaining_shares
  const orderSize = replay.config.order_size_per_agent_shares
  const totalCosts = useMemo(() => agents.map(id => aggregateCosts(replay, id)), [replay])
  const cumulative = costRange === 'cumulative'
  const displayedCosts = agents.map(id => cumulative ? aggregateCosts(replay, id, current + 1)
    : row.agents[id].execution.cost_components_bps_of_parent_order)
  const displayedTotals = displayedCosts.map((costs, index) => cumulative
    ? Object.values(costs).reduce((total, part) => total + part, 0)
    : row.agents[agents[index]].execution.weighted_step_shortfall_bps) as [number, number]
  const [aCosts, bCosts] = totalCosts
  const totals: [number, number] = [replay.summary.A_cost_bps, replay.summary.B_cost_bps]
  const reconciles = agents.every((id, index) => {
    const sum = Object.values(totalCosts[index]).reduce((total, value) => total + value, 0)
    const residual = replay.summary.cost_reconciliation[id].residual_opportunity_cost_bps
    return Math.abs(sum + residual - totals[index]) < 1e-6
  })
  const selectStep = useCallback((index: number) => {
    setPlaying(false)
    setCurrent(Math.min(length - 1, Math.max(0, index)))
  }, [length])
  const changePage = (target: Page) => {
    setPage(target)
    window.scrollTo(0, 0)
  }
  const togglePlay = useCallback(() => {
    if (playing) { setPlaying(false); return }
    if (current === length - 1) setCurrent(0)
    setPlaying(true)
  }, [current, length, playing])
  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.isComposing || event.altKey || event.ctrlKey || event.metaKey ||
        document.querySelector('dialog[open]')) return
      const target = event.target
      if (target instanceof Element && (target.closest('input, select, textarea, [contenteditable="true"]') ||
        (event.key === ' ' && target.closest('button, a[href]')))) return
      if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
        event.preventDefault()
        selectStep(current + (event.key === 'ArrowRight' ? 1 : -1))
      } else if (event.key === ' ') {
        event.preventDefault()
        if (!event.repeat && length > 1) togglePlay()
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [current, length, selectStep, togglePlay])
  useEffect(() => {
    if (!playing) return
    if (current === length - 1) { setPlaying(false); return }
    const timer = window.setTimeout(() => setCurrent(current + 1), 800 / speed)
    return () => window.clearTimeout(timer)
  }, [current, length, playing, speed])

  return <div className={styles.shell}>
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <div><strong>MARL</strong><span>交易执行实验室</span></div>
      </div>
      <nav className={styles.nav} aria-label="页面导航">
        {pages.map(item => <button key={item.id} onClick={() => changePage(item.id)}
          aria-current={page === item.id ? 'page' : undefined}>
          <Icon name={item.icon} size={18} /><span>{item.label}</span>
        </button>)}
      </nav>
      <div className={styles.sideFoot}><i />模拟环境<span>INDEPENDENT Q-LEARNING</span></div>
    </aside>

    <main className={styles.main}>
      <header className={styles.header}>
        <div>
          <div className={styles.titleRow}>
            <h1>{pages.find(item => item.id === page)?.title}</h1>
            <span className={styles.badge}><Icon name="snowflake" size={16} />冻结策略</span>
          </div>
          <div className={styles.metadata}>{scenarioLabel(replay.scenario)}<i />检查点 {replay.checkpoint_episode}<i />种子 {replay.seed}</div>
        </div>
        <div className={styles.headerActions}>
          <ReplayConfig replay={replay} onScenario={onScenario} preset={preset} />
          <button className={styles.button} onClick={onImport} title={filename}><Icon name="upload" size={16} />导入回放</button>
          {filename !== '内置回放' && <button className={styles.textButton} onClick={onRestore}>恢复样例</button>}
        </div>
      </header>

      {page === 'overview' && <>
        <section className={`${styles.glass} ${styles.metricBand}`} aria-label="交易前状态">
          <Metrics values={[
            ['当前中间价', num(market.mid_before, 4)], ['当前步数', `${row.step} / ${length}`],
            [finalStep ? 'A 期末剩余' : 'A 步前剩余', <>{shares(overviewRemaining('A'))} <small>股</small></>],
            [finalStep ? 'B 期末剩余' : 'B 步前剩余', <>{shares(overviewRemaining('B'))} <small>股</small></>],
          ]} />
        </section>
        <div className={styles.pair}>
          {agents.map(id => {
            const record = row.agents[id]
            const completed = finalStep ? replay.summary[`${id}_completion_rate`] : 1 - overviewRemaining(id) / orderSize
            const forced = record.execution.forced_completion_quantity_shares ?? 0
            return <section className={`${styles.glass} ${styles.agentCard}`} data-agent={id} key={id}>
              <div className={styles.panelHead}>
                <Heading icon="bank">基金 {id}</Heading>
                <button className={styles.textButton} onClick={() => { setAgent(id); changePage('decision') }}>决策详情<Icon name="arrow" size={16} /></button>
              </div>
              <div className={styles.agentAction}>
                <div><span>本步决策</span><strong className={styles.actionPill}>{actionLabels[record.decision.selected_action]}</strong></div>
                <div><span>{limit ? '本步提交' : '本步下单'}</span><strong>{shares(record.decision.selected_quantity_shares)} <small>股</small></strong></div>
              </div>
              <div className={styles.agentFacts}>
                <span>Q 值 <b>{record.decision.selected_q_value === null ? '—' : num(record.decision.selected_q_value, 4)}</b></span>
                <span>已完成 <b>{percent(completed)}</b></span>
                {limit ? <span>普通成交 <b>{shares(fillQuantity(record) - forced)} 股</b>{forced > 0 &&
                  <> · 兜底 <b>{shares(forced)} 股</b></>}</span>
                  : <span>上期对手成交 <b>{shares(record.observation.opponent_previous_quantity)} 股</b></span>}
              </div>
            </section>
          })}
        </div>
        <div className={`${styles.marketGrid} ${styles.overviewMarket}`}>
          <section className={styles.glass}>
            <div className={styles.panelHead}><Heading icon="chart">中间价轨迹</Heading><span className={styles.hint}>交易前 · 第 {row.step} 步</span></div>
            <PriceChart steps={replay.steps} current={current} onStep={selectStep} />
          </section>
          <section className={styles.glass}>
            <Heading icon="layers">共同市场反馈</Heading>
            <dl className={styles.rows}>
              <div><dt>{limit ? '联合提交' : '联合下单'}</dt><dd>{shares(market.joint_submitted_quantity_shares)} 股</dd></div>
              {limit && <div><dt>联合实际成交{finalStep && replay.completion_mode === 'autonomous' ? '（含兜底）' : ''}</dt><dd>{shares(market.joint_actual_filled_quantity_shares ?? 0)} 股</dd></div>}
              <div><dt>临时冲击</dt><dd>{bp(market.temporary_impact_bps)}</dd></div>
              <div><dt>下一中间价</dt><dd>{num(market.mid_after, 4)}</dd></div>
            </dl>
          </section>
        </div>
      </>}

      {page === 'decision' && <>
        <div className={styles.viewBar}>
          <div className={styles.segmented} aria-label="选择智能体">{agents.map(id =>
            <button key={id} aria-pressed={agent === id} onClick={() => setAgent(id)}>基金 {id}</button>
          )}</div>
          <div className={styles.stepTools}>
            <span className={styles.hint}>交易前状态 · 第 {row.step} / {length} 步</span>
            <StepExplanation replay={replay} current={current} agent={agent} onOpen={() => setPlaying(false)} />
          </div>
        </div>
        <section className={styles.glass}>
          <Metrics values={[
            ['当前中间价', num(market.mid_before, 4)],
            ['剩余订单', <>{shares(active.observation.own_remaining_shares)} <small>股</small></>],
            ['剩余时间', duration(active.observation.seconds_remaining)],
            ['对手上期成交', <>{shares(active.observation.opponent_previous_quantity)} <small>股</small></>],
          ]} />
          <p className={styles.stateLine}>状态编码 <code>[{active.observation.state_key.join(', ')}]</code>
            <span>执行进度比 {num(active.observation.pace_ratio_vs_remaining_twap, 2)}</span>
            <span>价格偏离 {bp(active.observation.price_deviation_bps)}</span></p>
        </section>
        <div className={styles.marketGrid}>
          <section className={styles.glass}>
            <Heading icon="decision">动作档位与 Q 值</Heading>
            <div className={styles.tableWrap}><table className={styles.table}>
              <thead><tr><th scope="col">动作</th><th scope="col">下单股数</th><th scope="col">Q 值</th><th scope="col">访问次数</th><th scope="col">状态</th></tr></thead>
              <tbody>{replayActions(limit).map((action, index) => {
                const feasible = selected.feasible_actions.find(candidate => candidate.index === index)
                const visits = selected.all_action_visit_counts[index]
                const picked = action === selected.selected_action
                return <tr key={action} className={picked ? styles.chosen : !feasible ? styles.disabledRow : undefined}>
                  <th scope="row">{actionLabels[action]}</th><td>{feasible ? shares(feasible.quantity_shares) : '—'}</td>
                  <td>{visits ? num(selected.all_action_q_values[index], 4) : '—'}</td><td>{visits}</td>
                  <td>{picked ? <span className={styles.chip}>已选择</span> : !feasible ? '期限受限' : visits ? '可比较' : '未尝试'}</td>
                </tr>
              })}</tbody>
            </table></div>
          </section>
          <section className={`${styles.glass} ${styles.choice}`} data-agent={agent}>
            <Heading icon="bank">基金 {agent} 的选择</Heading>
            <div className={styles.choiceResult}>
              <span className={styles.actionPill}>{actionLabels[selected.selected_action]}</span>
              <div className={styles.big}>{shares(selected.selected_quantity_shares)} <small>股</small></div>
            </div>
            <p>{decisionReason(active, limit)}</p>
            {active.execution.limit_order ? <>
              <dl className={styles.rows}>
                <div><dt>实际成交</dt><dd>{shares(fillQuantity(active))} 股</dd></div>
                <div><dt>新单限价</dt><dd>{active.execution.limit_order.limit_price === null
                  ? '—' : num(active.execution.limit_order.limit_price, 4)}</dd></div>
              </dl>
              <OrderEvents entry={active} />
            </> : <dl className={styles.rows}>
              <div><dt>最低可行量</dt><dd>{shares(selected.minimum_feasible_quantity_shares ?? 0)} 股</dd></div>
              <div><dt>探索率</dt><dd>ε = 0</dd></div>
            </dl>}
          </section>
        </div>
        <section className={`${styles.glass} ${styles.decisionFeedback}`}>
          <div className={styles.panelHead}><Heading icon="layers">同步执行后的市场反馈</Heading>
            <button className={styles.textButton} onClick={() => changePage('market')}>查看成本<Icon name="arrow" size={16} /></button>
          </div>
          <Metrics values={[
            [limit ? 'A 实际成交' : 'A 下单', `${shares(fillQuantity(row.agents.A))} 股`],
            [limit ? 'B 实际成交' : 'B 下单', `${shares(fillQuantity(row.agents.B))} 股`],
            [limit ? '联合提交' : '联合下单', `${shares(market.joint_submitted_quantity_shares)} 股`],
            ['下一中间价', num(market.mid_after, 4)],
          ]} />
        </section>
      </>}

      {page === 'market' && <>
        <section className={styles.glass}>
          <Heading icon="layers">第 {row.step} 步市场转移</Heading>
          <Metrics values={[
            ['交易前中间价', num(market.mid_before, 4)], ['下一中间价', num(market.mid_after, 4)],
            ['外生扰动', `${signed(market.external_shock_bps)} bp`], ['永久冲击', bp(market.permanent_impact_bps)],
          ]} />
        </section>
        <div className={styles.pair}>
          <section className={styles.glass}>
            <div className={styles.panelHead}>
              <Heading icon="chart">市场轨迹</Heading>
              <div className={styles.segmented} aria-label="选择市场图表">
                <button aria-pressed={marketChart === 'impact'} onClick={() => setMarketChart('impact')}>冲击</button>
                <button aria-pressed={marketChart === 'cost'} onClick={() => setMarketChart('cost')}>累计成本</button>
              </div>
            </div>
            {marketChart === 'impact' ? <>
              <ImpactChart steps={replay.steps} current={current} />
              <p className={styles.hint}>临时冲击进入当步成交价，永久冲击传导至下一步中间价。</p>
            </> : <>
              <CumulativeCostChart steps={replay.steps} current={current} />
              <p className={styles.hint}>逐步累计已成交部分的含费实施缺口，机会成本残差见回合总结。</p>
            </>}
          </section>
          <section className={styles.glass}>
            <div className={styles.panelHead}>
              <Heading icon="layers">执行成本拆分</Heading>
              <div className={styles.segmented} aria-label="成本统计范围">
                <button aria-pressed={!cumulative} onClick={() => setCostRange('step')}>当步</button>
                <button aria-pressed={cumulative} onClick={() => setCostRange('cumulative')}>累计至当前步</button>
              </div>
            </div>
            <CostTable limit={limit} a={displayedCosts[0]} b={displayedCosts[1]} totals={displayedTotals} />
            <p className={styles.hint}>{cumulative ? `第 1–${row.step} 步已成交成本。期末机会成本见回合总结。`
              : `以母单名义金额归一化。单边手续费 ${bp(market.one_way_fee_bps, 2)}。`}</p>
          </section>
        </div>
        <section className={styles.glass}>
          <Heading icon="bank">当步成交</Heading>
          {limit ? <div className={styles.executionPair}>{agents.map(id => {
            const entry = row.agents[id]
            const price = entry.execution.fill_price_including_fee
            const order = entry.execution.limit_order!
            return <div key={id}>
              <strong>基金 {id}</strong>
              <p>提交 {shares(entry.decision.selected_quantity_shares)} 股 · 实际成交 {shares(fillQuantity(entry))} 股
                {price !== null && ` · 含费价 ${num(price, 4)}`}</p>
              <p className={styles.hint}>被动成交 {shares(order.maker_filled)} 股 · 主动成交 {shares(order.taker_filled)} 股
                {(entry.execution.forced_completion_quantity_shares ?? 0) > 0 && ` · 兜底成交 ${shares(entry.execution.forced_completion_quantity_shares!)} 股`}
                {order.open_after > 0 && ` · 队列前方 ${shares(order.queue_ahead_after)} 股`}</p>
              <OrderEvents entry={entry} />
            </div>
          })}</div> : <Metrics values={agents.map(id => {
            const entry = row.agents[id]
            const amount = entry.decision.selected_quantity_shares
            return [`基金 ${id}`, amount > 0 && entry.execution.fill_price_including_fee !== null
              ? <>{shares(amount)} <small>股 · 含费价 {num(entry.execution.fill_price_including_fee, 4)}</small></>
              : '无成交']
          })} />}
        </section>
      </>}

      {page === 'summary' && <>
        <div className={styles.viewBar}><span className={styles.hint}>完整回合 · {length} 步 · 每方母单 {shares(orderSize)} 股</span>
          <button className={styles.button} onClick={() => { changePage('overview'); setCurrent(0); setPlaying(true) }}><Icon name="play" size={16} />从头回放</button>
        </div>
        <div className={styles.pair}>{agents.map((id, index) =>
          <section className={styles.glass} data-agent={id} key={id}>
            <Heading icon="bank">基金 {id}</Heading>
            <span className={styles.hint}>总实施缺口</span>
            <div className={styles.big}>{num(totals[index], 4)} <small>bp</small></div>
            <div className={styles.agentFacts}><span>完成率 <b>{percent(replay.summary[`${id}_completion_rate`])}</b></span>
              <span>未完成 <b>{shares(replay.summary[`${id}_unfilled_shares`])} 股</b></span>
              {replay.completion_mode === 'autonomous' && <span>期末兜底 <b>{shares(replay.summary[`${id}_forced_completion_shares`] ?? 0)} 股</b>
                {' · '}{bp(replay.summary[`${id}_forced_completion_cost_bps`] ?? 0, 2)}（已计入总成本）</span>}</div>
          </section>
        )}</div>
        <div className={styles.pair}>
          <section className={styles.glass}>
            <Heading icon="layers">回合成本构成</Heading>
            <CostTable limit={limit} a={aCosts} b={bCosts} totals={totals}
              opportunity={limit ? agents.map(id => replay.summary.cost_reconciliation[id].residual_opportunity_cost_bps) as [number, number] : undefined} />
            {!limit && <p className={styles.hint}>机会成本残差 · A {bp(replay.summary.cost_reconciliation.A.residual_opportunity_cost_bps, 4)} / B {bp(replay.summary.cost_reconciliation.B.residual_opportunity_cost_bps, 4)}</p>}
          </section>
          <section className={styles.glass}><Heading icon="chart">动作分布</Heading>
            <ActionChart summary={replay.summary} limit={limit} /><p className={styles.hint}>按动作选择次数统计，包含等待。</p>
          </section>
        </div>
        <div className={`${styles.glass} ${styles.verification}`}>
          <span><Icon name={reconciles ? 'check' : 'layers'} size={17} />{reconciles ? '成本复算一致' : '成本复算有差异'}</span>
          <span><Icon name="lock" size={17} />策略表哈希一致</span>
          <span className={styles.hint}>{limit ? '完成率按实际成交量计算，期末未成交股数计入机会成本。'
            : '完成率由期限约束与模拟成交假设共同决定。'}</span>
        </div>
      </>}

      <Timeline current={current} total={length} stepSeconds={replay.config.step_seconds} playing={playing}
        speed={speed} onStep={selectStep} onPlay={togglePlay} onSpeed={setSpeed} />
      <footer className={styles.footer}><span>冻结回放 · ε = 0 · Q 表未更新</span><span>单局模拟示例</span></footer>
    </main>
  </div>
}

const configuredUrl = import.meta.env.VITE_REPLAY_URL
const defaultUrl = configuredUrl || presetUrl('normal')
async function fetchReplay(url: string, signal?: AbortSignal) {
  const response = await fetch(url, { signal })
  if (!response.ok) throw new Error(`读取回放失败（HTTP ${response.status}）`)
  return parseReplay(await response.json())
}
function App() {
  const [replay, setReplay] = useState<Replay | null>(null)
  const [defaultReplay, setDefaultReplay] = useState<Replay | null>(null)
  const [filename, setFilename] = useState('内置回放')
  const [error, setError] = useState('')
  const [version, setVersion] = useState(0)
  const [preset, setPreset] = useState<Scenario | null>(configuredUrl ? null : 'normal')
  const fileInput = useRef<HTMLInputElement>(null)
  useEffect(() => {
    const controller = new AbortController()
    fetchReplay(defaultUrl, controller.signal).then(data => {
      setDefaultReplay(data)
      setReplay(previous => previous ?? data)
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '读取回放失败')
    })
    return () => controller.abort()
  }, [])
  async function selectScenario(scenario: Scenario) {
    const data = await fetchReplay(presetUrl(scenario))
    if (data.schema_version !== '2.0' || data.scenario !== scenario) {
      throw new Error('内置回放的版本或情景与选项不符。')
    }
    setReplay(data)
    setPreset(scenario)
    setFilename('内置回放')
    setVersion(previous => previous + 1)
    setError('')
  }
  async function importFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0]
    event.currentTarget.value = ''
    if (!file) return
    try {
      const data = parseReplay(JSON.parse(await file.text()))
      setReplay(data)
      setFilename(file.name)
      setPreset(null)
      setVersion(previous => previous + 1)
      setError('')
    } catch (reason) {
      setError(reason instanceof SyntaxError ? '文件不是有效的 JSON。' : reason instanceof Error ? reason.message : '导入失败')
    }
  }
  const openFile = () => fileInput.current?.click()
  return <>
    <input ref={fileInput} type="file" accept="application/json,.json" hidden onChange={importFile} />
    {replay ? <Dashboard key={version} replay={replay} filename={filename} onImport={openFile}
      onScenario={selectScenario} preset={preset}
      onRestore={() => {
        if (!defaultReplay) { setError('内置样例尚未加载。'); return }
        setPreset(configuredUrl ? null : 'normal')
        setReplay(defaultReplay); setFilename('内置回放'); setVersion(previous => previous + 1); setError('')
      }} /> : <main className={styles.loading}><section className={styles.glass}>
      <h1>交易执行实验室</h1><p role="status">{error ? '请选择冻结回放文件' : '正在加载冻结回放…'}</p>
      <button className={styles.button} onClick={openFile}><Icon name="upload" size={16} />导入回放</button>
    </section></main>}
    {error && <div role="alert" className={styles.error}>{error}<button className={styles.textButton} onClick={() => setError('')}>关闭</button></div>}
  </>
}

createRoot(document.getElementById('root')!).render(<App />)
