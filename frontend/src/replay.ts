export type Agent = 'A' | 'B'
export const agents = ['A', 'B'] as const
export const actions = ['wait', 'half', 'base', 'one_and_half', 'double'] as const
export type Action = typeof actions[number]
export const actionLabels: Record<Action, string> = {
  wait: '等待', half: '半份 TWAP', base: '基准 TWAP',
  one_and_half: '1.5 倍 TWAP', double: '2 倍 TWAP',
}
export const components = ['price_drift', 'half_spread', 'temporary_impact', 'fee'] as const
export const componentLabels = {
  price_drift: '价格漂移', half_spread: '半价差', temporary_impact: '临时冲击', fee: '手续费',
}
export type Costs = Record<typeof components[number], number>

export interface AgentStep {
  observation: {
    own_remaining_shares: number
    seconds_remaining: number
    price_deviation_bps: number
    pace_ratio_vs_remaining_twap: number
    opponent_previous_quantity: number
    state_key: number[]
  }
  decision: {
    mode: 'greedy_q_over_tried_feasible_actions' | 'twap_fallback_no_tried_feasible_action'
    selected_action: Action
    selected_quantity_shares: number
    selected_q_value: number | null
    greedy_tie_count: number
    minimum_feasible_quantity_shares: number
    minimum_feasible_action_index: number
    all_action_q_values: number[]
    all_action_visit_counts: number[]
    feasible_actions: { index: number; quantity_shares: number; twap_multiple: number }[]
  }
  execution: {
    fill_price_including_fee: number
    weighted_step_shortfall_bps: number
    cost_components_bps_of_parent_order: Costs
  }
}

export interface Replay {
  source_ref: string
  checkpoint_episode: number
  seed: number
  scenario: string
  config: {
    window_minutes: number
    step_seconds: number
    horizon_steps: number
    order_size_per_agent_shares: number
    initial_mid_price: number
    one_way_fee_bps: number
  }
  steps: {
    step: number
    elapsed_seconds: number
    agents: Record<Agent, AgentStep>
    market_transition: {
      mid_before: number
      mid_after: number
      external_shock_bps: number
      permanent_impact_bps: number
      temporary_impact_bps: number
      joint_submitted_quantity_shares: number
      half_spread_bps: number
      one_way_fee_bps: number
    }
  }[]
  summary: Record<`${Agent}_${'cost_bps' | 'completion_rate' | 'unfilled_shares'}`, number>
    & Record<`${Agent}_action_counts`, Partial<Record<Action, number>>>
    & { cost_reconciliation: Record<Agent, {
      sum_of_step_shortfalls_bps: number
      reported_total_cost_bps: number
      residual_opportunity_cost_bps: number
    }> }
  policy_table_sha256_before: Record<Agent, string>
  policy_table_sha256_after: Record<Agent, string>
}

type Fields = Record<string, unknown>
function check(ok: unknown, field: string): asserts ok {
  if (!ok) throw new Error(`回放文件字段无效：${field}`)
}
function record(value: unknown, field: string): Fields {
  check(value && typeof value === 'object' && !Array.isArray(value), field)
  return value as Fields
}
function numbers(value: unknown, keys: readonly string[], field: string) {
  const obj = record(value, field)
  for (const key of keys) {
    check(typeof obj[key] === 'number' && Number.isFinite(obj[key]), `${field}.${key}`)
  }
  return obj
}
const validActionIndex = (value: unknown): value is number =>
  typeof value === 'number' && Number.isInteger(value) && value >= 0 && value < actions.length

// All dependencies on the Python export shape are collected here.
export function parseReplay(value: unknown): Replay {
  const data = numbers(value, ['checkpoint_episode', 'seed'], '回放')
  check(data.schema_version === '1.0', 'schema_version（当前支持 1.0）')
  check(data.training_updates_applied === false && data.epsilon === 0, '冻结策略标记')
  check(typeof data.scenario === 'string' && typeof data.source_ref === 'string', '来源与情景')
  const config = numbers(data.config, [
    'window_minutes', 'step_seconds', 'horizon_steps', 'order_size_per_agent_shares',
    'initial_mid_price', 'one_way_fee_bps',
  ], 'config')
  check(Number(config.order_size_per_agent_shares) > 0 && Number(config.step_seconds) > 0, '订单量与步长')
  check(Array.isArray(data.steps) && data.steps.length > 0 && data.steps.length === config.horizon_steps, 'steps')
  const hashesBefore = record(data.policy_table_sha256_before, '回放前哈希')
  const hashesAfter = record(data.policy_table_sha256_after, '回放后哈希')
  const summary = record(data.summary, 'summary')
  const reconciliation = record(summary.cost_reconciliation, 'cost_reconciliation')
  for (const id of agents) {
    check(typeof hashesBefore[id] === 'string' && hashesBefore[id] === hashesAfter[id], `基金 ${id} 的策略哈希`)
    numbers(summary, [`${id}_cost_bps`, `${id}_completion_rate`, `${id}_unfilled_shares`], 'summary')
    const counts = record(summary[`${id}_action_counts`], `基金 ${id} 动作次数`)
    for (const count of Object.values(counts)) check(Number.isInteger(count) && Number(count) >= 0, '动作次数')
    numbers(reconciliation[id], [
      'sum_of_step_shortfalls_bps', 'reported_total_cost_bps', 'residual_opportunity_cost_bps',
    ], `cost_reconciliation.${id}`)
  }
  for (const [index, value] of data.steps.entries()) {
    const step = numbers(value, ['step', 'elapsed_seconds'], '时间步')
    check(step.step === index + 1, '时间步顺序')
    numbers(step.market_transition, [
      'mid_before', 'mid_after', 'external_shock_bps', 'permanent_impact_bps',
      'temporary_impact_bps', 'joint_submitted_quantity_shares', 'half_spread_bps', 'one_way_fee_bps',
    ], 'market_transition')
    const pair = record(step.agents, 'agents')
    for (const id of agents) {
      const entry = record(pair[id], `agents.${id}`)
      const observation = numbers(entry.observation, [
        'own_remaining_shares', 'seconds_remaining', 'price_deviation_bps',
        'pace_ratio_vs_remaining_twap', 'opponent_previous_quantity',
      ], 'observation')
      check(Array.isArray(observation.state_key) && observation.state_key.every(Number.isInteger), 'state_key')
      const decision = numbers(entry.decision, [
        'selected_quantity_shares', 'greedy_tie_count',
        'minimum_feasible_quantity_shares', 'minimum_feasible_action_index',
      ], 'decision')
      check(decision.mode === 'greedy_q_over_tried_feasible_actions' ||
        decision.mode === 'twap_fallback_no_tried_feasible_action', 'decision.mode')
      check(decision.selected_q_value === null || Number.isFinite(decision.selected_q_value), 'selected_q_value')
      const selected = actions.findIndex(action => action === decision.selected_action)
      check(selected >= 0, 'selected_action')
      for (const key of ['all_action_q_values', 'all_action_visit_counts'] as const) {
        const array = decision[key]
        check(Array.isArray(array) && array.length === actions.length && array.every(Number.isFinite), key)
      }
      check(Array.isArray(decision.feasible_actions), 'feasible_actions')
      const feasible = decision.feasible_actions.map(value => {
        const action = numbers(value, ['index', 'quantity_shares', 'twap_multiple'], 'feasible_actions')
        check(validActionIndex(action.index), '动作档位')
        return action.index
      })
      check(feasible.includes(selected), '实际动作的期限可行性')
      const execution = numbers(entry.execution, ['fill_price_including_fee', 'weighted_step_shortfall_bps'], 'execution')
      numbers(execution.cost_components_bps_of_parent_order, components, '成本分项')
    }
  }
  return data as unknown as Replay
}

const formats = new Map<number, Intl.NumberFormat>()
export function num(value: number, digits = 2) {
  if (!formats.has(digits)) {
    formats.set(digits, new Intl.NumberFormat('zh-CN', { maximumFractionDigits: digits, minimumFractionDigits: digits }))
  }
  return formats.get(digits)!.format(Math.abs(value) < 0.5 * 10 ** -digits ? 0 : value)
}
export const shares = (value: number) => num(value, Number.isInteger(value) ? 0 : 2)
export const bp = (value: number, digits = 3) => `${num(value, digits)} bp`
export const signed = (value: number, digits = 3) => `${value > 0 ? '+' : ''}${num(value, digits)}`
export const percent = (value: number) => `${num(value * 100, 2)}%`
export const duration = (value: number) =>
  `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`
export const scenarioLabel = (scenario: string) =>
  ({ normal: '正常波动', high_volatility: '两倍波动' }[scenario] ?? scenario)

export function aggregateCosts(steps: Replay['steps'], id: Agent): Costs {
  const totals: Costs = { price_drift: 0, half_spread: 0, temporary_impact: 0, fee: 0 }
  for (const step of steps) {
    const costs = step.agents[id].execution.cost_components_bps_of_parent_order
    for (const component of components) totals[component] += costs[component]
  }
  return totals
}
