const DATA_URL = "../outputs/advanced_self_play/demo_frozen/demo_frozen_episode.json";
const ACTION_LABELS = {
  wait: "等待",
  half: "半份 TWAP",
  base: "基准 TWAP",
  one_and_half: "1.5 倍 TWAP",
  double: "2 倍 TWAP",
};
const COST_LABELS = [
  ["price_drift", "drift"],
  ["half_spread", "spread"],
  ["temporary_impact", "impact"],
  ["fee", "fee"],
];

const $ = (id) => document.getElementById(id);
const state = { data: null, step: 0, timer: null };

function fmt(value, digits = 2) {
  return Number(value).toLocaleString("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function signed(value, digits = 3) {
  const number = Number(value);
  return `${number > 0 ? "+" : ""}${fmt(number, digits)}`;
}

function stepAt(index) {
  return state.data.steps[index];
}

function cumulativeCost(agent, upto) {
  const sum = Object.fromEntries(COST_LABELS.map(([key]) => [key, 0]));
  for (let i = 0; i <= upto; i += 1) {
    const parts = stepAt(i).agents[agent].execution.cost_components_bps_of_parent_order;
    for (const [key] of COST_LABELS) sum[key] += Number(parts[key]);
  }
  return sum;
}

function renderActionRows(agent, record) {
  const target = $(`${agent.toLowerCase()}-actions`);
  const actions = record.decision.all_actions;
  const values = actions.map((item) => Number(item.q_value));
  const low = Math.min(...values);
  const high = Math.max(...values);
  target.innerHTML = actions.map((item) => {
    const span = high - low;
    const width = span < 1e-12 ? 55 : 16 + ((Number(item.q_value) - low) / span) * 84;
    const selected = item.index === record.decision.selected_action_index;
    const classes = ["action-row", selected ? "selected" : "", item.feasible ? "" : "infeasible"].filter(Boolean).join(" ");
    const label = ACTION_LABELS[item.name] ?? item.name;
    return `<div class="${classes}" title="${label} · ${item.feasible ? "可行动作" : "当前不可行"}">
      <span class="action-name">${label}${selected ? " · 已选" : ""}${item.feasible ? "" : " · 不可行"}</span>
      <span class="q-track"><span class="q-fill" style="width:${width}%"></span></span>
      <span class="q-number">${fmt(item.q_value, 4)}</span>
      <span class="visit-number">n=${item.visit_count}</span>
    </div>`;
  }).join("");
}

function renderAgent(agent, record) {
  const prefix = agent.toLowerCase();
  const observation = record.observation;
  const decision = record.decision;
  const execution = record.execution;
  $(prefix + "-action-tag").textContent = ACTION_LABELS[decision.selected_action] ?? decision.selected_action;
  $(prefix + "-action").textContent = ACTION_LABELS[decision.selected_action] ?? decision.selected_action;
  $(prefix + "-qty").textContent = `${fmt(execution.submitted_quantity_shares, 2)} 股`;
  $(prefix + "-remaining").textContent = `${fmt(observation.own_remaining_shares, 2)} 股`;
  $(prefix + "-pace").textContent = `${fmt(observation.pace_ratio_vs_remaining_twap, 3)}×`;
  $(prefix + "-state").textContent = `[${observation.state_key.join(", ")}]`;
  $(prefix + "-mode").textContent = decision.mode === "twap_fallback_no_tried_feasible_action" ? "未探索动作回退 TWAP" : "已访问可行动作中 Q 值最高";
  $(prefix + "-opponent-flow").textContent = `${fmt(observation.opponent_previous_quantity, 2)} 股`;
  $(prefix + "-floor").textContent = `${fmt(decision.minimum_feasible_quantity_shares, 2)} 股`;
  renderActionRows(agent, record);
}

function renderCosts(index) {
  const a = cumulativeCost("A", index);
  const b = cumulativeCost("B", index);
  const totalA = COST_LABELS.reduce((sum, [key]) => sum + a[key], 0);
  const totalB = COST_LABELS.reduce((sum, [key]) => sum + b[key], 0);
  for (const [key, suffix] of COST_LABELS) {
    $(`cost-a-${suffix}`).textContent = `${signed(a[key])} bp`;
    $(`cost-b-${suffix}`).textContent = `${signed(b[key])} bp`;
  }
  $("cost-a-total").textContent = `${signed(totalA)} bp`;
  $("cost-b-total").textContent = `${signed(totalB)} bp`;
  $("cost-through-step").textContent = `累计至第 ${index + 1} 步`;
}

function renderStep(index) {
  if (!state.data) return;
  state.step = Math.max(0, Math.min(state.data.steps.length - 1, index));
  const step = stepAt(state.step);
  const tr = step.market_transition;
  const a = step.agents.A;
  const b = step.agents.B;
  const config = state.data.config;
  $("step-slider").value = String(state.step + 1);
  $("progress-label").textContent = `${state.step + 1} / ${state.data.steps.length}`;
  $("metric-step").textContent = `${state.step + 1} / ${state.data.steps.length}`;
  $("metric-mid").textContent = fmt(tr.mid_before, 4);
  $("metric-mid-change").textContent = `相对初始价 ${signed((tr.mid_before / config.initial_mid_price - 1) * 10000, 2)} bp`;
  $("metric-rem-a").textContent = `${fmt(a.observation.own_remaining_shares, 2)} 股`;
  $("metric-rem-b").textContent = `${fmt(b.observation.own_remaining_shares, 2)} 股`;
  $("metric-fill-a").textContent = `已完成 ${fmt(100 * (1 - a.observation.own_remaining_shares / config.order_size_per_agent_shares), 2)}%`;
  $("metric-fill-b").textContent = `已完成 ${fmt(100 * (1 - b.observation.own_remaining_shares / config.order_size_per_agent_shares), 2)}%`;
  $("joint-qty").textContent = `${fmt(tr.joint_submitted_quantity_shares, 2)} 股`;
  $("external-shock").textContent = `${signed(tr.external_shock_bps, 4)} bp`;
  $("temp-impact").textContent = `${fmt(tr.temporary_impact_bps, 4)} bp`;
  $("perm-impact").textContent = `${fmt(tr.permanent_impact_bps, 4)} bp`;
  $("next-mid").textContent = fmt(tr.mid_after, 4);
  $("flow-a-qty").textContent = `${fmt(a.execution.submitted_quantity_shares, 2)} 股`;
  $("flow-b-qty").textContent = `${fmt(b.execution.submitted_quantity_shares, 2)} 股`;
  $("flow-a-action").textContent = ACTION_LABELS[a.decision.selected_action] ?? a.decision.selected_action;
  $("flow-b-action").textContent = ACTION_LABELS[b.decision.selected_action] ?? b.decision.selected_action;
  $("flow-joint").textContent = `${fmt(tr.joint_submitted_quantity_shares, 2)} 股`;
  $("execution-explanation").textContent = `A 与 B 各自按同一交易前中间价 ${fmt(tr.mid_before, 4)} 决策。本步临时冲击 ${fmt(tr.temporary_impact_bps, 4)} bp 由联合成交量产生；外生扰动与永久冲击共同决定下一步中间价。`;
  renderAgent("A", a);
  renderAgent("B", b);
  renderCosts(state.step);
  drawPriceChart();
}

function drawPriceChart() {
  const canvas = $("price-chart");
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.round(rect.width * ratio));
  canvas.height = Math.max(1, Math.round(rect.height * ratio));
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  const width = rect.width;
  const height = rect.height;
  const left = 62, right = 12, top = 14, bottom = 22;
  const points = state.data.steps.map((item) => item.market_transition.mid_before);
  const min = Math.min(...points), max = Math.max(...points);
  const pad = Math.max((max - min) * 0.18, state.data.config.initial_mid_price * 0.00012);
  const lo = min - pad, hi = max + pad;
  const x = (i) => left + (i / (points.length - 1)) * (width - left - right);
  const y = (value) => top + ((hi - value) / (hi - lo)) * (height - top - bottom);
  ctx.clearRect(0, 0, width, height);
  ctx.font = "10px 'DM Mono', monospace";
  ctx.textBaseline = "middle";
  for (let i = 0; i < 5; i += 1) {
    const value = hi - ((hi - lo) * i) / 4;
    const yy = y(value);
    ctx.beginPath(); ctx.moveTo(left, yy); ctx.lineTo(width - right, yy);
    ctx.strokeStyle = "#e8eeeb"; ctx.lineWidth = 1; ctx.stroke();
    ctx.fillStyle = "#82918a"; ctx.textAlign = "right";
    ctx.fillText(value.toFixed(4), left - 7, yy);
  }
  const tickSteps = [0, 14, 29, 44, 59];
  for (const index of tickSteps) {
    const xx = x(index);
    ctx.beginPath(); ctx.moveTo(xx, top); ctx.lineTo(xx, height - bottom);
    ctx.strokeStyle = "#f0f3f1"; ctx.stroke();
    ctx.fillStyle = "#82918a"; ctx.textAlign = "center";
    ctx.fillText(String(index + 1), xx, height - 8);
  }
  const selectedX = x(state.step);
  ctx.beginPath(); ctx.moveTo(selectedX, top); ctx.lineTo(selectedX, height - bottom);
  ctx.strokeStyle = "rgba(207,107,80,.38)"; ctx.setLineDash([3, 4]); ctx.stroke(); ctx.setLineDash([]);
  const currentPoint = state.step;
  ctx.beginPath();
  for (let i = 0; i <= currentPoint; i += 1) {
    if (i === 0) ctx.moveTo(x(i), y(points[i]));
    else ctx.lineTo(x(i), y(points[i]));
  }
  ctx.strokeStyle = "#118e82"; ctx.lineWidth = 2.4; ctx.lineJoin = "round"; ctx.lineCap = "round"; ctx.stroke();
  if (currentPoint < points.length - 1) {
    ctx.beginPath();
    ctx.moveTo(x(currentPoint), y(points[currentPoint]));
    for (let i = currentPoint + 1; i < points.length; i += 1) ctx.lineTo(x(i), y(points[i]));
    ctx.strokeStyle = "#aab7b1"; ctx.lineWidth = 1.7; ctx.setLineDash([4, 5]); ctx.stroke(); ctx.setLineDash([]);
  }
  ctx.beginPath(); ctx.arc(selectedX, y(points[state.step]), 5, 0, Math.PI * 2);
  ctx.fillStyle = "#fff"; ctx.fill(); ctx.lineWidth = 2.5; ctx.strokeStyle = "#cf6b50"; ctx.stroke();
  ctx.beginPath(); ctx.arc(x(0), y(points[0]), 3, 0, Math.PI * 2); ctx.fillStyle = "#118e82"; ctx.fill();
}

function stopPlayback() {
  if (state.timer) window.clearInterval(state.timer);
  state.timer = null;
  $("toggle-play").textContent = "▶";
  $("toggle-play").title = "播放";
  $("toggle-play").setAttribute("aria-label", "播放");
}

function startPlayback() {
  if (state.timer) { stopPlayback(); return; }
  if (state.step >= state.data.steps.length - 1) renderStep(0);
  $("toggle-play").textContent = "Ⅱ";
  $("toggle-play").title = "暂停";
  $("toggle-play").setAttribute("aria-label", "暂停");
  state.timer = window.setInterval(() => {
    if (state.step >= state.data.steps.length - 1) { stopPlayback(); return; }
    renderStep(state.step + 1);
  }, Number($("play-speed").value));
}

function bindControls() {
  $("step-slider").addEventListener("input", (event) => { stopPlayback(); renderStep(Number(event.target.value) - 1); });
  $("first-step").addEventListener("click", () => { stopPlayback(); renderStep(0); });
  $("next-step").addEventListener("click", () => { stopPlayback(); renderStep(state.step + 1); });
  $("toggle-play").addEventListener("click", startPlayback);
  $("play-speed").addEventListener("change", () => { if (state.timer) { stopPlayback(); startPlayback(); } });
  $("price-chart").addEventListener("click", (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = Math.max(0, Math.min(1, (event.clientX - rect.left - 62) / (rect.width - 74)));
    stopPlayback();
    renderStep(Math.round(x * (state.data.steps.length - 1)));
  });
  window.addEventListener("resize", () => { if (state.data) drawPriceChart(); });
  window.addEventListener("keydown", (event) => {
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement) return;
    if (event.key === "ArrowRight") { stopPlayback(); renderStep(state.step + 1); }
    if (event.key === "ArrowLeft") { stopPlayback(); renderStep(state.step - 1); }
    if (event.key === " ") { event.preventDefault(); startPlayback(); }
  });
}

async function loadReplay() {
  try {
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`数据请求失败 (${response.status})`);
    state.data = await response.json();
    if (state.data.steps.length !== 60 || state.data.policy_mode !== "frozen_greedy_no_learning_updates") {
      throw new Error("回放文件结构与冻结策略约定不符");
    }
    $("checkpoint").textContent = String(state.data.checkpoint_episode);
    $("seed").textContent = String(state.data.seed);
    $("data-status").textContent = `已载入 ${state.data.steps.length} 步 · ${state.data.policy_mode}`;
    $("step-slider").max = String(state.data.steps.length);
    bindControls();
    renderStep(0);
  } catch (error) {
    $("data-status").textContent = "回放数据未载入";
    $("load-error").hidden = false;
    $("load-error").textContent = `无法载入回放 JSON：${error.message}。请从 multi_agent_execution 目录启动本地静态服务器。`;
  }
}

loadReplay();
