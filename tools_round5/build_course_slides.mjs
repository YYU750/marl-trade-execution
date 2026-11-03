import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SKILL_DIR = "C:/Users/谢东杰/.codex/plugins/cache/openai-primary-runtime/presentations/26.1026.10807/skills/Presentations";
const BUILD_DIR = path.join(ROOT, ".pptx_build_round5");
const OUTPUT_DIR = path.join(ROOT, "deliverables");
const CANDIDATE = path.join(BUILD_DIR, "candidate.pptx");
const FINAL = path.join(OUTPUT_DIR, "round5_course_slides.pptx");
const RENDER_DIR = path.join(ROOT, ".pptx_render_round5");
const FONT = "Microsoft YaHei";
const C = {
  ink: "#152A33", muted: "#526A73", teal: "#007C83", green: "#3E7C59",
  red: "#B5423C", amber: "#B9791F", blue: "#255B73", pale: "#E9F1F4",
  paleGreen: "#EAF2ED", paleRed: "#F7ECEB", white: "#FFFFFF", grid: "#D6E0E3",
  dark: "#102830", light: "#F6F8F8",
};

await fs.mkdir(BUILD_DIR, { recursive: true });
await fs.mkdir(OUTPUT_DIR, { recursive: true });
await fs.mkdir(RENDER_DIR, { recursive: true });
if (await fs.stat(FINAL).catch(() => null)) throw new Error(`Refusing to overwrite ${FINAL}`);

const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const slides = [];

function shape(slide, x, y, w, h, fill = "none", line = "none", geometry = "rect") {
  return slide.shapes.add({
    geometry,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: line, width: line === "none" ? 0 : 1 },
  });
}

function text(slide, value, x, y, w, h, opts = {}) {
  const box = shape(slide, x, y, w, h);
  box.text = value;
  box.text.style = {
    typeface: FONT,
    fontSize: opts.size ?? 24,
    bold: opts.bold ?? false,
    color: opts.color ?? C.ink,
    alignment: opts.align ?? "left",
    verticalAlignment: opts.valign ?? "middle",
    wrap: "square",
    autoFit: "shrinkText",
    insets: opts.insets ?? { left: 2, right: 2, top: 2, bottom: 2 },
  };
  return box;
}

function baseSlide(title, kicker, n, dark = false) {
  const slide = presentation.slides.add();
  slides.push(slide);
  slide.background.fill = dark ? C.dark : C.white;
  if (kicker) text(slide, kicker.toUpperCase(), 64, 33, 950, 22, { size: 14, bold: true, color: dark ? "#80C9C5" : C.teal });
  if (title) text(slide, title, 64, 68, 1150, 58, { size: 34, bold: true, color: dark ? C.white : C.ink });
  if (n > 1) text(slide, `${String(n).padStart(2, "0")} / 10`, 1100, 666, 116, 24, { size: 12, color: dark ? "#B9C8CC" : C.muted, align: "right" });
  return slide;
}

function line(slide, x1, y1, x2, y2, color = C.grid, width = 2) {
  shape(slide, x1, y1, x2 - x1, y2 - y1, "none", color, "line").line.width = width;
}

function notes(slide, body) { slide.speakerNotes.text = body; }

// 1. Conclusion first.
{
  const s = baseSlide("双机构交易执行：Q-learning 学会了什么？", "金融人工智能课程项目 · 第五轮复核", 1, true);
  text(s, "算法更新通过独立数值审计，\n但当前策略没有胜过 TWAP。", 72, 190, 840, 150, { size: 44, bold: true, color: C.white });
  text(s, "94.4%", 78, 418, 245, 76, { size: 54, bold: true, color: "#80C9C5" });
  text(s, "测试决策请求零倍配速", 80, 492, 330, 34, { size: 20, color: "#E1ECEE" });
  text(s, "90.15%", 430, 418, 245, 76, { size: 54, bold: true, color: "#F0BE69" });
  text(s, "成交量来自完单约束补足", 432, 492, 370, 34, { size: 20, color: "#E1ECEE" });
  text(s, "Q 8.85 bp   |   TWAP 7.50 bp", 80, 570, 640, 34, { size: 22, bold: true, color: C.white });
  text(s, "结论来自可复跑的 300 / 60 / 100 seed 协议与 5 组冻结策略压力场景。", 72, 632, 890, 28, { size: 15, color: "#B9C8CC" });
  notes(s, "主结论先说清楚：Bellman 更新和终止处理经过独立测试，但成本比较中 Q-learning 高于 TWAP。测试期的 100% 完成由环境硬约束保证，不能说成是学习策略主动完成。数值来源：results_round5_standard/test_summary.json 与 round5_key_findings.json；压力来源：results_round5_pressure_02/pressure_summary.csv。日期和材料对应本轮第五轮复核。 ");
}

// 2. The market the agents face.
{
  const s = baseSlide("双方买单共同改变价格路径", "01 · 仿真环境", 2);
  text(s, "A\n100,000 股买单", 85, 193, 250, 92, { size: 25, bold: true, align: "center", color: C.blue });
  text(s, "B\n100,000 股买单", 945, 193, 250, 92, { size: 25, bold: true, align: "center", color: C.green });
  line(s, 333, 238, 500, 238, C.blue, 3);
  line(s, 780, 238, 945, 238, C.green, 3);
  shape(s, 500, 164, 280, 150, C.pale, C.grid, "rect");
  text(s, "同一市场快照\n价差 · 中间价 · 流动性", 510, 185, 260, 98, { size: 22, bold: true, align: "center" });
  text(s, "同刻观察 → 独立决策 → 联合成交", 310, 347, 660, 40, { size: 22, bold: true, align: "center", color: C.teal });
  shape(s, 92, 437, 500, 126, C.light, C.grid, "rect");
  text(s, "成交价", 116, 454, 134, 30, { size: 19, bold: true, color: C.blue });
  text(s, "中间价 × [1 + (半价差 + 即时冲击) / 10,000]", 116, 494, 440, 42, { size: 20 });
  shape(s, 686, 437, 500, 126, C.light, C.grid, "rect");
  text(s, "下一期中间价", 710, 454, 240, 30, { size: 19, bold: true, color: C.green });
  text(s, "当前中间价 × exp[(外生冲击 + 永久冲击) / 10,000]", 710, 494, 440, 52, { size: 19 });
  text(s, "30 个一分钟时段；不含订单簿、限价单或部分成交。冲击参数是教学假设，未用真实市场校准。", 90, 600, 1090, 40, { size: 16, color: C.muted });
  notes(s, "两家机构都是买方，联合成交量影响即时成交价，也通过永久冲击改变下一期中间价。双方先在同一市场快照下决定，再由环境一起处理，避免一个 agent 看见另一个本期的行动。源码：src_round5/execution_sim/environment.py，观测与 step 的同步约束；README.md 给出公式及单位。 ");
}

// 3. Separate policy decisions from environment constraints.
{
  const s = baseSlide("策略请求量与实际成交量是两件事", "02 · 执行机制", 3);
  const labels = [
    ["策略请求", "动作 × 平均配速", C.blue],
    ["上限裁切", "不超过剩余量与单步上限", C.teal],
    ["完单补足", "避免剩余订单无法按期完成", C.amber],
    ["实际成交", "裁切请求 + 约束补足", C.green],
  ];
  const xs = [78, 378, 678, 978];
  for (let i = 0; i < labels.length; i++) {
    shape(s, xs[i], 212, 224, 132, i === 2 ? "#FBF3E4" : C.light, C.grid, "rect");
    text(s, labels[i][0], xs[i] + 15, 229, 194, 34, { size: 21, bold: true, align: "center", color: labels[i][2] });
    text(s, labels[i][1], xs[i] + 14, 273, 196, 52, { size: 16, align: "center" });
    if (i < labels.length - 1) text(s, "→", xs[i] + 236, 250, 56, 42, { size: 34, bold: true, color: C.muted, align: "center" });
  }
  text(s, "测试期核账", 84, 405, 185, 32, { size: 18, bold: true, color: C.muted });
  text(s, "3,000 / 3,000 步成交量恒等式通过", 84, 445, 595, 46, { size: 30, bold: true, color: C.ink });
  text(s, "强制补足", 758, 410, 180, 30, { size: 18, bold: true, color: C.amber });
  text(s, "9,015,269 / 10,000,000 股\n占总成交量 90.15%", 758, 448, 405, 78, { size: 27, bold: true, color: C.amber });
  text(s, "所以 100% 完成率是硬约束的结果，不能作为学习策略有效的证据。", 84, 576, 1085, 40, { size: 21, bold: true, color: C.red });
  notes(s, "训练动作和环境最终成交必须分开。源码按请求量 floor，再按剩余股数和单步上限裁切，之后执行 enforce_completion 的最低完单量。测试轨迹逐行满足 filled_shares = request_after_clip_shares + forced_fill_shares；共 3,000 行，失败 0。90.15% 是最终成交股数占比，不是发生强制补足的步数占比。来源：results_round5_standard/test_action_trace.csv 和 round5_key_findings.json。 ");
}

// 4. State, action and protocol.
{
  const s = baseSlide("Q 表只学习了一个有限状态与动作空间", "03 · Q-learning", 4);
  text(s, "状态", 88, 185, 140, 36, { size: 22, bold: true, color: C.teal });
  text(s, "剩余步数\n自身剩余股数\n可观察价差、中间价偏离\n流动性比例、单步上限", 92, 235, 470, 206, { size: 24 });
  line(s, 618, 182, 618, 538, C.grid, 2);
  text(s, "动作", 688, 185, 140, 36, { size: 22, bold: true, color: C.blue });
  text(s, "当前平均配速 ×\n0 / 0.5 / 1 / 1.5 / 2", 692, 237, 480, 92, { size: 28, bold: true });
  text(s, "训练 300 seeds\n验证 60 seeds 选参\n测试 100 个新 seeds\n测试冻结 Q 表，epsilon=0", 692, 358, 450, 160, { size: 22 });
  shape(s, 90, 553, 1085, 67, C.pale, "none", "rect");
  text(s, "有限期限采用 γ=1；机构 B 固定 TWAP。规则 TWAP 用连续股数计划，Q-learning 用离散动作。", 112, 566, 1040, 40, { size: 18, bold: true, align: "center" });
  notes(s, "Q 表状态包括精确剩余步数与股数，其余市场变量分箱，因此它是近似状态表示，并未严格证明 Markov 充分性。动作是平均配速倍数。参数通过 60 个验证 seed 选择，选中 alpha=0.30、epsilon_decay=0.99；测试阶段重新加载保存的 Q 表，epsilon=0，不更新。训练/验证/测试 seed 区间见 results_round5_standard/qlearning_config.json。 ");
}

// 5. Standard comparison chart built from report values.
{
  const s = baseSlide("标准测试中，Q-learning 成本更高", "04 · 100 个配对测试 seed", 5);
  const vals = [8.8491, 7.5044, 7.7252];
  const names = ["Q-learning", "TWAP", "价差紧迫度"];
  const colors = [C.red, C.green, C.blue];
  const max = 10;
  const chartX = 320, chartY = 198, chartW = 720;
  for (let i = 0; i < vals.length; i++) {
    const y = chartY + i * 112;
    text(s, names[i], 85, y + 9, 210, 32, { size: 21, bold: i === 0 });
    shape(s, chartX, y, chartW * vals[i] / max, 52, colors[i], "none", "rect");
    text(s, vals[i].toFixed(4), chartX + chartW * vals[i] / max + 16, y + 6, 150, 38, { size: 23, bold: true, color: colors[i] });
  }
  text(s, "总目标成本（bp）  ·  越低越好", 320, 550, 700, 28, { size: 16, color: C.muted });
  shape(s, 82, 596, 1080, 46, C.paleRed, "none", "rect");
  text(s, "Q − TWAP = +1.3447 bp；95% 配对区间 [+0.5334, +2.1560]", 104, 602, 1038, 34, { size: 22, bold: true, color: C.red, align: "center" });
  notes(s, "标准测试固定 B=TWAP，A 三种策略在相同 100 个测试 seed 上比较。均值成本的单位是初始订单名义金额的 bp。Q−TWAP 是逐 seed 配对差；95% t 区间全为正，故在该仿真假设下 Q 成本高于 TWAP。Q mean 8.8491187372；TWAP 7.5044235678；spread urgency 7.7251586843。来源：results_round5_standard/test_summary.json、test_paired_comparison.csv。 ");
}

// 6. Where Q behavior came from.
{
  const s = baseSlide("94.4% 的零倍动作，大多没有让订单停下来", "05 · 行为归因", 6);
  const x0 = 108, y0 = 204, barW = 948, barH = 64;
  shape(s, x0, y0, barW, barH, C.pale, "none", "rect");
  shape(s, x0, y0, barW * 0.9015269, barH, C.amber, "none", "rect");
  text(s, "环境强制补足 90.15%", x0 + 18, y0 + 11, 420, 42, { size: 26, bold: true, color: C.white });
  text(s, "策略主动请求成交 9.85%", x0 + barW * 0.9015269 + 10, y0 + 14, 260, 38, { size: 18, bold: true, color: C.ink });
  text(s, "2,833 / 3,000", 115, 338, 420, 56, { size: 36, bold: true, color: C.blue });
  text(s, "测试决策请求 0 倍配速", 117, 396, 430, 35, { size: 19, color: C.muted });
  text(s, "937 / 3,000", 658, 338, 420, 56, { size: 36, bold: true, color: C.amber });
  text(s, "决策步实际发生强制补足", 660, 396, 430, 35, { size: 19, color: C.muted });
  line(s, 150, 492, 1120, 492, C.grid, 2);
  text(s, "472 次未见状态", 145, 524, 270, 42, { size: 22, bold: true });
  text(s, "782 次全零 Q 向量", 505, 524, 300, 42, { size: 22, bold: true });
  text(s, "平局选择首个有效动作", 865, 524, 330, 42, { size: 22, bold: true, color: C.teal });
  text(s, "与零倍动作集中相符；这是机制解释，不是唯一原因证明。", 146, 602, 1010, 30, { size: 17, color: C.muted, align: "center" });
  notes(s, "测试期 3,000 个决策中 2,833 次选零倍。总共成交 1,000 万股，其中环境最低完单约束补了 9,015,269 股。发生强制补足的决策步为 937。另有 472 次状态未在 Q 表中、782 次整个 Q 向量为零。冻结模型遇到全零向量时按首个有效动作打平，动作顺序首项是零倍配速。观察结果支持这种解释，但不能单独证明唯一因果来源。 ");
}

// 7. One actual terminal update.
{
  const s = baseSlide("一条真实更新：零请求，环境补了 10,000 股", "06 · 训练轨迹复核", 7);
  const rows = [
    ["训练候选", "alpha=0.30；第 1 episode；第 30 步"],
    ["状态", "剩 1 步；自身剩余 10,000 股"],
    ["动作与成交", "0 倍配速请求 0；最低完单量 10,000"],
    ["成本与奖励", "目标成本 2,359.9411；奖励 −2,359.9411"],
    ["Bellman 目标", "终止步不 bootstrap；target = reward"],
    ["Q 值", "0 + 0.30 × (−2,359.9411 − 0) = −707.9823"],
  ];
  const widths = [250, 720];
  const y = 181;
  for (let i = 0; i < rows.length; i++) {
    const yy = y + i * 66;
    shape(s, 110, yy, widths[0], 52, i === 5 ? C.paleGreen : C.light, C.grid, "rect");
    shape(s, 360, yy, widths[1], 52, C.white, C.grid, "rect");
    text(s, rows[i][0], 124, yy + 7, 220, 38, { size: 18, bold: true, color: C.blue });
    text(s, rows[i][1], 378, yy + 7, 680, 38, { size: i === 5 ? 21 : 18, bold: i === 5 });
  }
  text(s, "原训练回执与独立重放一致。", 110, 594, 1060, 32, { size: 20, bold: true, color: C.green, align: "center" });
  notes(s, "该更新取自选中候选 2 的训练流，episode seed 20261103，agent seed 20271105。最后一步的状态只允许动作索引 0，动作请求零股；完成约束实际成交 10,000 股。IS 2,329.8712，fee 30.0699，机会成本与终端惩罚为 0，总目标 2,359.9411。done=True 后 next_state=null、next_max_q=0，所以 target 等于 reward。alpha=0.30，新Q=-707.9823。回执 selected_training_update_full.json 与重放一致。 ");
}

// 8. Pressure test table.
{
  const s = baseSlide("压力变化下，冻结策略没有稳住相对成本", "07 · 新的 100 个压力 seed", 8);
  const rows = [
    ["场景", "Q 成本", "Q − TWAP", "配对区间"],
    ["基准参数", "8.15", "+1.36", "+0.54 至 +2.18"],
    ["波动率 8 bp", "7.55", "+0.94", "−2.42 至 +4.31"],
    ["流动性 10,000 股", "13.40", "+3.03", "+2.15 至 +3.91"],
    ["全价差 12 bp", "11.26", "+1.46", "+0.58 至 +2.34"],
    ["B 改为前置买入", "8.42", "+0.88", "+0.05 至 +1.71"],
  ];
  const table = s.tables.add({
    rows: rows.length, columns: 4, left: 82, top: 182, width: 1088, height: 372,
    columnWidths: [360, 165, 165, 398], values: rows,
  });
  table.styleOptions = { headerRow: false, bandedRows: false };
  table.borders.assign({ style: "solid", fill: C.grid, width: 1 });
  for (let r = 0; r < rows.length; r++) {
    for (let c = 0; c < rows[r].length; c++) {
      const cell = table.getCell(r, c);
      cell.fill = r === 0 ? C.blue : r % 2 ? C.light : C.white;
      cell.text.style = {
        typeface: FONT,
        fontSize: r === 0 ? 17 : 18,
        bold: r === 0 || (c === 2 && r !== 0),
        color: r === 0 ? C.white : c === 2 ? C.red : C.ink,
        verticalAlignment: "middle",
        alignment: c === 0 ? "left" : "center",
        wrap: "square",
        autoFit: "shrinkText",
      };
    }
  }
  text(s, "低流动性和宽价差下，测试状态 3,000/3,000 未见，Q 表全零，每步请求 0 股。", 88, 574, 1090, 42, { size: 18, bold: true, color: C.red, align: "center" });
  text(s, "所有场景仍是 100% 完成：因为完单硬约束仍开启。", 88, 622, 1090, 26, { size: 15, color: C.muted, align: "center" });
  notes(s, "压力 seed 20261600–20261699，与训练、验证、标准测试不重叠。Q 表冻结，epsilon=0，无更新。表中的成本和 Q−TWAP 差单位为 bp；区间是同 seed 配对差的 95% 描述性 t 区间。波动率场景区间包含 0；其余列示场景 Q 成本更高。低流动性、宽价差两场景 3,000 条测试状态都未在训练表中，所有 Q 值为 0，因此每步请求零股并由约束完成。来源：results_round5_pressure_02/pressure_summary.csv、pressure_q_action_trace.csv。 ");
}

// 9. Correct interpretation.
{
  const s = baseSlide("算法正确性与策略有效性要分开判断", "08 · 结果解释", 9);
  const colX = [88, 666];
  const titles = ["已通过的核验", "当前没有得到的结果"];
  const bullets = [
    ["35 项测试全部通过", "Bellman 终止值、合法动作与保存恢复", "独立重放匹配真实训练更新", "请求、强制补足与实际成交逐步对账"],
    ["成本优于 TWAP", "对未见市场状态的可靠外推", "Markov 充分性的严格证明", "真实市场表现或双边学习均衡"],
  ];
  for (let i = 0; i < 2; i++) {
    text(s, titles[i], colX[i], 190, 500, 42, { size: 26, bold: true, color: i === 0 ? C.green : C.red });
    line(s, colX[i], 242, colX[i] + 500, 242, i === 0 ? C.green : C.red, 3);
    for (let j = 0; j < bullets[i].length; j++) {
      const yy = 274 + j * 70;
      text(s, i === 0 ? "✓" : "—", colX[i], yy, 42, 36, { size: 23, bold: true, color: i === 0 ? C.green : C.red });
      text(s, bullets[i][j], colX[i] + 52, yy, 435, 44, { size: 19, bold: j === 0 });
    }
  }
  shape(s, 88, 586, 1090, 52, C.pale, "none", "rect");
  text(s, "更新公式实现无误，不代表学出的执行策略已经有效。", 110, 594, 1045, 34, { size: 22, bold: true, color: C.blue, align: "center" });
  notes(s, "35 项是同一第五轮源码路径上的旧测试迁移 19 项、独立审计 12 项和新增行为测试 4 项。当前实验显示算法局部逻辑可以通过数值核验，但策略仍劣于 TWAP，且状态覆盖在压力场景中明显不足。状态变量中有离散分箱，并未严格验证 Markov 充分性。A 学习、B 固定，不能声称双边博弈均衡。 ");
}

// 10. What a defensible next round would do.
{
  const s = baseSlide("下一轮应先解决状态覆盖和约束依赖", "09 · 后续研究", 10, true);
  const items = [
    ["1", "重做状态聚合", "用剩余比例等尺度稳健的表示，先测训练覆盖。"],
    ["2", "分解请求与补足", "将主动成交节奏作为核心行为指标，避免完成约束遮蔽策略。"],
    ["3", "保留独立测试", "只用新的验证 seed 比较改进，冻结后再评估新测试集。"],
  ];
  for (let i = 0; i < items.length; i++) {
    const yy = 177 + i * 132;
    text(s, items[i][0], 92, yy + 6, 64, 52, { size: 39, bold: true, color: i === 0 ? "#80C9C5" : "#F0BE69" });
    text(s, items[i][1], 177, yy, 370, 46, { size: 26, bold: true, color: C.white });
    text(s, items[i][2], 558, yy + 3, 600, 54, { size: 20, color: "#D8E4E6" });
    if (i < 2) line(s, 177, yy + 83, 1164, yy + 83, "#35515A", 1);
  }
  text(s, "不改旧测试集，不把事后诊断包装成确认性结果。", 92, 591, 1060, 40, { size: 20, bold: true, color: "#80C9C5" });
  notes(s, "当前是分析建议，不是已执行的改进实验。训练/验证/测试 seed 必须继续隔离；任何重新设计应在新的验证集合选择，保留新的测试集合，且报告负结果。零请求策略的事后对照只作诊断，不应成为方法有效的正式证据。 ");
}

for (let i = 0; i < slides.length; i++) {
  const blob = await presentation.export({ slide: slides[i], format: "png", scale: 1 });
  await fs.writeFile(path.join(RENDER_DIR, `slide-${String(i + 1).padStart(2, "0")}.png`), new Uint8Array(await blob.arrayBuffer()));
}

const finalizer = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href);
await (await PresentationFile.exportPptx(presentation)).save(CANDIDATE);
const result = await finalizer.finalizePresentation({
  explicitTotalSlideCount: 10,
  workspaceDir: ROOT,
  candidatePath: CANDIDATE,
  finalPath: FINAL,
  pythonExecutable: "C:/Users/谢东杰/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe",
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-bullet-geometry", "--validate-heading-fit", "--require-native-table-slide", "8"],
  requiredNativeTableOwnerSlides: [8],
  fontPolicy: { basis: "design", families: ["Microsoft YaHei"] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(BUILD_DIR, "round5_course_slides.validation.json"),
});
console.log(JSON.stringify({ final: FINAL, renderDir: RENDER_DIR, slides: slides.length, validation: result }, null, 2));
