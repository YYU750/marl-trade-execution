import { useRef } from 'react'
import {
  actionLabels, bp, duration, fillQuantity, num, replayActions, scenarioLabel, shares, signed,
  type Agent, type AgentStep, type Replay,
} from './replay'
import styles from './Dashboard.module.css'

export function decisionReason(entry: AgentStep, limit: boolean) {
  const decision = entry.decision
  if (decision.mode === 'twap_fallback_no_tried_feasible_action') {
    return limit ? '当前状态没有已尝试的动作，使用买一限价作为默认动作。'
      : '当前没有已尝试的可行动作，回退到可行的基准 TWAP 或最低可行动作。'
  }
  const rule = limit ? '在已尝试的动作中，选取 Q 值最高的动作。'
    : '在已尝试且满足期限约束的动作中，选取 Q 值最高的动作。'
  return decision.greedy_tie_count > 1 ? rule + ' 本步存在并列最高值。' : rule
}

export function OrderEvents({ entry }: { entry: AgentStep }) {
  const order = entry.execution.limit_order
  if (!order) return null
  const fill = fillQuantity(entry)
  const offered = entry.decision.selected_quantity_shares || order.open_before
  const events: string[] = []
  if (fill > 0) events.push(fill + 1e-6 < offered ? '部分成交' : '全部成交')
  if (order.open_after > 0) events.push(`剩余挂单 ${shares(order.open_after)} 股`)
  if (order.replaced > 0) events.push(`换单撤销 ${shares(order.replaced)} 股`)
  if (order.expired > 0) events.push(`挂单到期 ${shares(order.expired)} 股`)
  if (order.ioc_cancelled > 0) events.push(`IOC 撤销 ${shares(order.ioc_cancelled)} 股`)
  if (order.deadline_cancelled > 0) events.push(`期末撤销 ${shares(order.deadline_cancelled)} 股`)
  return <div className={styles.orderEvents}>{(events.length ? events : ['无成交或订单变动']).map(event =>
    <span key={event} className={styles.chip}>{event}</span>
  )}</div>
}

function explainExecution(entry: AgentStep) {
  const order = entry.execution.limit_order
  const submitted = entry.decision.selected_quantity_shares
  if (!order) {
    return '这局使用简化的提交即成交模型，按当前步的成交量扣减母单。'
  }
  if (order.type === 'marketable_limit_ioc') {
    return '这一步用带价格上限的 IOC 争取立即成交。成交量受限价内可见卖盘约束，IOC 未成交余量立即撤销。'
  }
  if (submitted > 0) {
    return '这一步提交被动限价单，等待卖方订单流消耗队列后成交。提交量和实际成交量分别记录，只有成交部分会减少母单。'
  }
  if (order.open_before > 0) {
    return '本步没有提交新单。已有挂单仍可参与撮合，所以等待期间也可能成交。'
  }
  if (entry.observation.own_remaining_shares === 0) return '母单已没有剩余股数，本步无需提交新订单。'
  return '本步没有新提交，也没有可继续撮合的挂单，母单剩余量保持不变。'
}

export function StepExplanation({ replay, current, agent, onOpen }: {
  replay: Replay; current: number; agent: Agent; onOpen: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const row = replay.steps[current]
  const market = row.market_transition
  const entry = row.agents[agent]
  const { observation, decision, execution } = entry
  const limit = replay.schema_version === '2.0'
  const opponent = agent === 'A' ? 'B' : 'A'
  const history = replay.steps.slice(Math.max(0, current - 2), current)
  const filled = fillQuantity(entry)
  const remaining = Math.max(0, observation.own_remaining_shares - filled)
  const choices = replayActions(limit)
  const tried = decision.feasible_actions
    .filter(({ index }) => decision.all_action_visit_counts[index] > 0)
    .sort((a, b) => decision.all_action_q_values[b.index] - decision.all_action_q_values[a.index])
  return <>
    <button className={`${styles.button} ${styles.explainButton}`}
      onClick={() => { onOpen(); dialog.current?.showModal() }}>本步解读</button>
    <dialog ref={dialog} aria-labelledby="step-explanation-title"
      className={`${styles.glass} ${styles.configDialog} ${styles.explanationDialog}`}>
      <div className={styles.panelHead}>
        <div>
          <h2 id="step-explanation-title" className={styles.panelTitle}>本步解读 · 基金 {agent}</h2>
          <p className={styles.hint}>{scenarioLabel(replay.scenario)} · 第 {row.step} / {replay.steps.length} 步 · 冻结检查点 {replay.checkpoint_episode}</p>
        </div>
        <button className={styles.button} onClick={() => dialog.current?.close()}>关闭解读</button>
      </div>
      <dl className={styles.explanationRows}>
        <div>
          <dt>输入状态</dt>
          <dd>已过 <b>{duration(row.elapsed_seconds)}</b>，剩余时间 <b>{duration(observation.seconds_remaining)}</b>，母单待买 <b>{shares(observation.own_remaining_shares)} 股</b>。
            中间价 {num(market.mid_before, 4)}，报价价差 {bp(market.half_spread_bps * 2, 2)}，单边手续费 {bp(market.one_way_fee_bps, 2)}（{num(market.one_way_fee_bps / 100, 2)}%）。</dd>
        </div>
        <div>
          <dt>对手线索</dt>
          <dd>
            <p>{current === 0 ? '首步尚无对手成交历史。'
              : `Q 状态使用基金 ${opponent} 上一步的实际成交量 ${shares(observation.opponent_previous_quantity)} 股。`}</p>
            {history.length > 0 && <p className={styles.hint}>历史回看 · {history.map(step => {
              const previous = step.agents[opponent]
              return `第 ${step.step} 步 ${actionLabels[previous.decision.selected_action]}，成交 ${shares(fillQuantity(previous))} 股`
            }).join('；')}</p>}
          </dd>
        </div>
        <div>
          <dt>智能体动作</dt>
          <dd><b>{actionLabels[decision.selected_action]}</b>，本步提交 <b>{shares(decision.selected_quantity_shares)} 股</b>。
            {execution.limit_order?.limit_price != null && `新单限价 ${num(execution.limit_order.limit_price, 4)}。`}</dd>
        </div>
        <div>
          <dt>模型依据</dt>
          <dd><p>{decisionReason(entry, limit)}</p>
            {tried.length > 0 && <ul className={styles.explanationValues} aria-label="可比较的 Q 值">
              {tried.map(({ index }) => <li key={index} data-picked={choices[index] === decision.selected_action}>
                {actionLabels[choices[index]]} <b>{num(decision.all_action_q_values[index], 4)}</b>
              </li>)}
            </ul>}
          </dd>
        </div>
        <div>
          <dt>环境反馈</dt>
          <dd>
            <p>实际成交 <b>{shares(filled)} 股</b>，本步后母单剩余 <b>{shares(remaining)} 股</b>。
              中间价 {num(market.mid_before, 4)} → {num(market.mid_after, 4)}（{signed((market.mid_after / market.mid_before - 1) * 10_000)} bp）。</p>
            <OrderEvents entry={entry} />
          </dd>
        </div>
        <div>
          <dt>业务解释</dt>
          <dd>{explainExecution(entry)}</dd>
        </div>
      </dl>
    </dialog>
  </>
}
