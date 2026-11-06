import { useEffect, useMemo, useRef } from 'react'
import { init, use, type EChartsCoreOption, type EChartsType } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, MarkPointComponent, TooltipComponent } from 'echarts/components'
import { SVGRenderer } from 'echarts/renderers'
import { actionLabels, actions, agents, num, type Replay } from './replay'
import styles from './Dashboard.module.css'

use([BarChart, LineChart, GridComponent, LegendComponent, MarkPointComponent, TooltipComponent, SVGRenderer])

const palette = ['#6df3f2', '#b0b7ff']
const textColor = '#a9c8e7'
const gridColor = 'rgba(181, 222, 255, 0.13)'
const tooltip = {
  trigger: 'axis', confine: true, renderMode: 'richText',
  backgroundColor: '#102b4b', borderColor: '#477fa3',
  textStyle: { color: '#eefaff' },
}
const axis = { axisLabel: { color: textColor }, axisLine: { lineStyle: { color: gridColor } }, axisTick: { show: false } }
const valueAxis = { type: 'value', ...axis, splitLine: { lineStyle: { color: gridColor } } }

function Chart({ option, label, onStep }: {
  option: EChartsCoreOption
  label: string
  onStep?: (index: number) => void
}) {
  const container = useRef<HTMLDivElement>(null)
  const chart = useRef<EChartsType | null>(null)
  useEffect(() => {
    const node = container.current!
    const instance = init(node, undefined, { renderer: 'svg' })
    chart.current = instance
    const resize = new ResizeObserver(() => {
      if (!instance.isDisposed()) instance.resize()
    })
    resize.observe(node)
    return () => {
      resize.disconnect()
      instance.dispose()
      chart.current = null
    }
  }, [])
  useEffect(() => {
    chart.current?.setOption(option, { notMerge: true })
  }, [option])
  useEffect(() => {
    const instance = chart.current
    if (!instance || !onStep) return
    const click = ({ dataIndex, componentType }: { dataIndex: number; componentType: string }) => {
      if (componentType === 'series' && Number.isInteger(dataIndex)) onStep(dataIndex)
    }
    instance.on('click', click)
    return () => {
      if (!instance.isDisposed()) instance.off('click', click)
    }
  }, [onStep])
  return <div ref={container} className={styles.chart} role="img" aria-label={label} />
}

export function PriceChart({ steps, current, onStep }: {
  steps: Replay['steps']; current: number; onStep: (index: number) => void
}) {
  const option = useMemo(() => {
    const prices = steps.map(step => step.market_transition.mid_before)
    return {
      animation: false, tooltip: { ...tooltip, valueFormatter: (value: number) => num(value, 4) },
      grid: { left: 60, right: 16, top: 17, bottom: 25 },
      xAxis: { ...axis, type: 'category', boundaryGap: false, data: steps.map(step => step.step) },
      yAxis: { ...valueAxis, scale: true, splitNumber: 4, axisLabel: { color: textColor, formatter: (value: number) => num(value, 3) } },
      series: [{
        name: '交易前中间价', type: 'line', data: prices, showSymbol: false,
        lineStyle: { width: 1.5, color: '#6096b8', type: 'dashed' },
        itemStyle: { color: '#6096b8' },
      }, {
        name: '已回放', type: 'line', data: prices.map((price, i) => i <= current ? price : null),
        tooltip: { show: false }, showSymbol: false,
        lineStyle: { width: 2.5, color: palette[0] }, itemStyle: { color: palette[0] },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
          { offset: 0, color: '#61e5f344' }, { offset: 1, color: '#61e5f300' },
        ] } },
        markPoint: { symbol: 'circle', symbolSize: 12, label: { show: false }, itemStyle: {
          color: '#d6ffff', borderWidth: 3, borderColor: '#41d1e7', shadowBlur: 10, shadowColor: '#64eafa',
        }, data: [{ coord: [current, prices[current]] }] },
      }],
    }
  }, [steps, current])
  return <Chart option={option} label={`中间价轨迹，当前第 ${current + 1} 步`} onStep={onStep} />
}

export function ImpactChart({ steps, current }: { steps: Replay['steps']; current: number }) {
  const option = useMemo(() => ({
    animation: false, color: palette, tooltip,
    legend: { textStyle: { color: textColor }, top: 1 },
    grid: { left: 50, right: 15, top: 35, bottom: 25 },
    xAxis: { ...axis, type: 'category', data: steps.map(step => step.step) },
    yAxis: { ...valueAxis, name: 'bp', nameTextStyle: { color: textColor } },
    series: [
      { name: '临时冲击', type: 'bar', data: steps.map((step, index) => ({
        value: step.market_transition.temporary_impact_bps,
        itemStyle: { color: index === current ? '#bcffff' : index < current ? palette[0] : '#426785' },
      })) },
      { name: '永久冲击', type: 'line', showSymbol: false, data: steps.map(step => step.market_transition.permanent_impact_bps) },
    ],
  }), [steps, current])
  return <Chart option={option} label="各步临时冲击与永久冲击" />
}

export function CumulativeCostChart({ steps, current }: { steps: Replay['steps']; current: number }) {
  const option = useMemo(() => ({
    animation: false, color: palette,
    tooltip: { ...tooltip, valueFormatter: (value: number) => `${num(value, 4)} bp` },
    legend: { textStyle: { color: textColor }, top: 1 },
    grid: { left: 51, right: 15, top: 35, bottom: 25 },
    xAxis: { ...axis, type: 'category', boundaryGap: false, data: steps.map(step => step.step) },
    yAxis: { ...valueAxis, name: 'bp', nameTextStyle: { color: textColor } },
    series: agents.map(id => {
      let accumulated = 0
      const costs = steps.map(step => accumulated += step.agents[id].execution.weighted_step_shortfall_bps)
      return {
        name: `基金 ${id}`, type: 'line', showSymbol: false,
        data: costs, lineStyle: { width: 2 },
        markPoint: { symbol: 'circle', symbolSize: 10, label: { show: false },
          data: [{ coord: [current, costs[current]] }] },
      }
    }),
  }), [steps, current])
  return <Chart option={option} label={`A/B 累计成交成本，当前第 ${current + 1} 步`} />
}

export function ActionChart({ summary }: { summary: Replay['summary'] }) {
  const option = useMemo(() => ({
    animation: false, color: palette, tooltip: { ...tooltip, axisPointer: { type: 'shadow' } },
    legend: { top: 0, textStyle: { color: textColor } },
    grid: { left: 100, right: 28, top: 34, bottom: 28 },
    xAxis: { ...valueAxis, minInterval: 1 },
    yAxis: { ...axis, type: 'category', inverse: true, data: actions.map(action => actionLabels[action]) },
    series: agents.map(id => ({
      name: `基金 ${id}`, type: 'bar', barMaxWidth: 13,
      label: { show: true, position: 'right', color: '#edfaff' },
      itemStyle: { borderRadius: [0, 4, 4, 0] },
      data: actions.map(action => summary[`${id}_action_counts`][action] ?? 0),
    })),
  }), [summary])
  return <Chart option={option} label="A/B 各动作档位的选择次数" />
}
