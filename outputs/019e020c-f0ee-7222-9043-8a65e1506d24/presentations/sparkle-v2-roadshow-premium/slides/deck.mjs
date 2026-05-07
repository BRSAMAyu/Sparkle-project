const C = {
  paper: "#F7F4EC",
  paper2: "#EFE9DD",
  ink: "#1E2429",
  muted: "#68717A",
  hair: "#D8D0C2",
  sage: "#7D8B6F",
  sage2: "#E7EBDD",
  clay: "#C46F4D",
  clay2: "#F2D8C9",
  blue: "#6E8498",
  blue2: "#DDE7EC",
  gold: "#B8955E",
  dark: "#172027",
  dark2: "#25313A",
  white: "#FFFFFF",
  red: "#A94D3F",
  green: "#557A62",
};

const ASSET_UI = "/Users/brsama/code/GitHub/Sparkle-project/outputs/019e020c-f0ee-7222-9043-8a65e1506d24/presentations/sparkle-v2-roadshow-premium/assets/sparkle-ui-concept.png";

function bg(slide, ctx, fill = C.paper) {
  ctx.addShape(slide, { x: 0, y: 0, w: ctx.W, h: ctx.H, fill });
}

function rect(slide, ctx, x, y, w, h, fill, line = "none") {
  return ctx.addShape(slide, {
    x, y, w, h,
    geometry: "roundRect",
    fill,
    line: line === "none" ? ctx.line("#00000000", 0) : ctx.line(line, 1),
  });
}

function rule(slide, ctx, x, y, w, h = 1, fill = C.hair) {
  ctx.addShape(slide, { x, y, w, h, fill, line: ctx.line("#00000000", 0) });
}

function text(slide, ctx, s, x, y, w, h, opts = {}) {
  return ctx.addText(slide, {
    text: s,
    x, y, w, h,
    fontSize: opts.size ?? 24,
    color: opts.color ?? C.ink,
    bold: opts.bold ?? false,
    align: opts.align ?? "left",
    valign: opts.valign ?? "top",
    typeface: opts.face ?? "PingFang SC",
    insets: opts.insets ?? { left: 0, right: 0, top: 0, bottom: 0 },
    fill: opts.fill ?? "#00000000",
    line: ctx.line("#00000000", 0),
  });
}

function title(slide, ctx, kicker, headline, sub) {
  text(slide, ctx, kicker, 64, 46, 420, 24, { size: 15, color: C.clay, bold: true });
  text(slide, ctx, headline, 64, 76, 1060, 104, { size: 37, bold: true });
  if (sub) text(slide, ctx, sub, 66, 188, 1000, 46, { size: 18, color: C.muted });
}

function foot(slide, ctx, n, label = "Sparkle V2 Roadshow") {
  text(slide, ctx, label, 64, 680, 360, 18, { size: 11, color: "#8F8A80" });
  text(slide, ctx, String(n).padStart(2, "0"), 1182, 680, 34, 18, { size: 11, color: "#8F8A80", align: "right" });
}

async function icon(slide, ctx, name, x, y, size = 24, color = C.ink) {
  return ctx.addLucideIcon(slide, { icon: name, x, y, w: size, h: size, color, strokeWidth: 2.1 });
}

async function pill(slide, ctx, label, x, y, w, color = C.sage, iconName) {
  rect(slide, ctx, x, y, w, 34, "#FFFFFFAA", "#E3DED3");
  if (iconName) await icon(slide, ctx, iconName, x + 12, y + 8, 18, color);
  text(slide, ctx, label, x + (iconName ? 38 : 14), y + 8, w - 48, 18, { size: 13, color: C.dark, bold: true });
}

function note(slide, body) {
  slide.speakerNotes.setText(body);
}

function metric(slide, ctx, value, label, x, y, w, color = C.sage) {
  rect(slide, ctx, x, y, w, 92, C.white, "#E0D8CA");
  text(slide, ctx, value, x + 18, y + 18, w - 36, 34, { size: 30, color, bold: true });
  text(slide, ctx, label, x + 18, y + 55, w - 36, 24, { size: 14, color: C.muted });
}

function tinyTag(slide, ctx, s, x, y, color = C.sage) {
  rect(slide, ctx, x, y, 92, 28, color + "22", color);
  text(slide, ctx, s, x + 10, y + 7, 72, 14, { size: 11, color, bold: true, align: "center" });
}

async function phoneFrame(slide, ctx, x, y, w, h, scale = "cover") {
  rect(slide, ctx, x, y, w, h, C.dark, "#0E1418");
  rect(slide, ctx, x + 12, y + 12, w - 24, h - 24, C.white, "#2D3840");
  await ctx.addImage(slide, { path: ASSET_UI, x: x + 18, y: y + 18, w: w - 36, h: h - 36, fit: scale, alt: "Sparkle UI concept" });
}

async function slide01(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx, C.paper);
  rect(slide, ctx, 42, 36, 1196, 648, "#FFFFFF88", "#E2DACD");
  text(slide, ctx, "Sparkle", 82, 68, 200, 36, { size: 25, bold: true, color: C.blue });
  text(slide, ctx, "鸿雁杯校内选拔 · 8 分钟路演", 82, 108, 300, 22, { size: 14, color: C.muted });
  text(slide, ctx, "7", 82, 170, 190, 180, { size: 154, bold: true, color: C.clay });
  text(slide, ctx, "天后考试，基本没学。\nAI 能救吗？", 286, 180, 520, 130, { size: 46, bold: true });
  text(slide, ctx, "我们不把 Sparkle 讲成“又一个会答题的 AI”。\n今天只讲一件事：它怎样把一个普通学生从慌乱带到可执行、可反馈、可通过。", 290, 334, 560, 92, { size: 21, color: C.muted });
  await phoneFrame(slide, ctx, 890, 80, 250, 520, "cover");
  await pill(slide, ctx, "北极星压力测试", 292, 458, 174, C.clay, "Target");
  await pill(slide, ctx, "计网 7 天抢救", 482, 458, 160, C.sage, "BookOpen");
  foot(slide, ctx, 1);
  note(slide, "25s。开场不要解释产品全貌，直接把评委拉进场景：一个学生 7 天后考计算机网络，基本没学。普通 AI 能答题，但这类场景真正难的是目标决策。过渡：为什么 AI 越来越强，学生离目标却没有更近？");
  return slide;
}

async function slide02(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx);
  title(slide, ctx, "Problem", "AI 很强，但普通人离目标没有更近", "问题不是模型不会答，而是用户不知道如何把目标变成路径，并一路做完。");
  const items = [
    ["需求断裂", "我想通过考试，但说不清差距在哪里。"],
    ["路径断裂", "资料很多、时间很短，不知道先救哪一块。"],
    ["执行断裂", "计划看起来完整，落到今天只剩下焦虑。"],
    ["反馈断裂", "失败后没人判断原因，下一步仍然靠猜。"],
  ];
  for (let i = 0; i < items.length; i++) {
    const x = 74 + i * 286;
    rect(slide, ctx, x, 278, 248, 170, i === 1 ? C.sage2 : C.white, "#DDD4C8");
    text(slide, ctx, `0${i + 1}`, x + 22, 300, 46, 26, { size: 18, color: [C.clay, C.sage, C.blue, C.gold][i], bold: true });
    text(slide, ctx, items[i][0], x + 22, 335, 170, 28, { size: 24, bold: true });
    text(slide, ctx, items[i][1], x + 22, 378, 194, 44, { size: 16, color: C.muted });
  }
  rule(slide, ctx, 96, 508, 1088, 1);
  text(slide, ctx, "所有人都在卷模型能力。我们选择卷另一件事：让普通人真的把目标做成。", 132, 546, 930, 34, { size: 27, bold: true, color: C.dark, align: "center" });
  text(slide, ctx, "这也是 Sparkle 的战略选择：系统承担 prompt、拆解、取舍、追踪和纠偏的认知负担。", 218, 590, 844, 25, { size: 16, color: C.muted, align: "center" });
  foot(slide, ctx, 2);
  note(slide, "40s。先承认 AI 很强，避免陷入和大模型比参数。然后说普通用户缺的不是答案，而是四个断裂。结尾用战略选择拔高：我们不是因为 AI 火了才做 AI，而是看到普通人离目标没有更近。");
  return slide;
}

async function slide03(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx, "#F2EEE5");
  title(slide, ctx, "Aurora", "第一次对话就不一样：不是先答，是先决策", "Aurora 不是让 AI 更会聊天，而是每次回答前先做上下文与目标决策。");
  const x1 = 88, x2 = 668, y = 254, w = 500;
  rect(slide, ctx, x1, y, w, 248, C.white, "#DED7CA");
  rect(slide, ctx, x2, y, w, 248, "#F7FBF2", C.sage);
  text(slide, ctx, "裸用通用 AI", x1 + 28, y + 26, 220, 28, { size: 23, bold: true });
  text(slide, ctx, "“7 天后考计网，基本没学。”", x1 + 28, y + 76, 340, 28, { size: 19, color: C.muted });
  text(slide, ctx, "常见结果：给一份完整复习计划\n包含所有章节、资料和解释\n看似全面，但没有取舍", x1 + 28, y + 120, 400, 82, { size: 22, color: C.ink });
  text(slide, ctx, "问题：把判断留给用户", x1 + 28, y + 212, 300, 20, { size: 15, color: C.red, bold: true });
  text(slide, ctx, "Sparkle + Aurora", x2 + 28, y + 26, 250, 28, { size: 23, bold: true, color: C.green });
  text(slide, ctx, "同一句输入，先进入抢救模式", x2 + 28, y + 76, 310, 28, { size: 19, color: C.muted });
  text(slide, ctx, "先做 12 分钟诊断\n根据考试权重和当前基础取舍\n主动放弃低收益章节", x2 + 28, y + 120, 400, 82, { size: 22, color: C.ink });
  text(slide, ctx, "差异：系统先做目标决策", x2 + 28, y + 212, 300, 20, { size: 15, color: C.green, bold: true });
  await icon(slide, ctx, "ArrowRight", 604, y + 112, 42, C.clay);
  rect(slide, ctx, 214, 548, 852, 54, C.dark, "#00000000");
  text(slide, ctx, "这不是“先问几个问题”的聊天技巧，而是把模型能力装进目标状态、用户画像和反馈闭环里。", 242, 564, 796, 24, { size: 18, color: C.white, align: "center" });
  foot(slide, ctx, 3);
  note(slide, "40s。关键是避免讲成“更会聊天”。用决策对比：普通 AI 给完整计划，Sparkle 先诊断、取舍、定最小通过路径。过渡：下面把这个决策入口放进 7 天计网抢救的完整旅程。");
  return slide;
}

async function slide04(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx);
  title(slide, ctx, "North Star / 1", "7 天救急·上：诊断 + 主动放弃", "最难的不是把知识讲全，而是在时间不足时判断什么该做、什么不该做。");
  rect(slide, ctx, 78, 250, 500, 310, C.white, "#DED6C9");
  text(slide, ctx, "12 分钟诊断", 110, 282, 220, 30, { size: 28, bold: true });
  text(slide, ctx, "Sparkle 不让学生先“开始复习”，而是先测三类高收益能力：", 112, 330, 410, 34, { size: 18, color: C.muted });
  const diag = [["TCP 可靠传输", "高频考点"], ["子网划分", "短板暴露"], ["差错检测", "可快速补齐"]];
  for (let i = 0; i < diag.length; i++) {
    const yy = 392 + i * 50;
    rect(slide, ctx, 112, yy, 400, 36, i === 1 ? C.clay2 : C.sage2, "#00000000");
    text(slide, ctx, diag[i][0], 132, yy + 8, 180, 16, { size: 15, bold: true });
    text(slide, ctx, diag[i][1], 340, yy + 8, 140, 16, { size: 14, color: C.muted, align: "right" });
  }
  rect(slide, ctx, 650, 250, 500, 310, "#F9FAF4", C.sage);
  text(slide, ctx, "主动放弃第 8 章", 684, 282, 260, 30, { size: 28, bold: true, color: C.green });
  text(slide, ctx, "不是因为它不重要，而是因为在 7 天约束下投入产出比最低。", 686, 330, 400, 42, { size: 18, color: C.muted });
  const plan = [["Day 1-2", "救 TCP / 子网 / 差错检测"], ["Day 3-5", "真题驱动补理论"], ["Day 6", "错因回收"], ["Day 7", "保底题型演练"]];
  for (let i = 0; i < plan.length; i++) {
    const yy = 400 + i * 42;
    text(slide, ctx, plan[i][0], 688, yy, 82, 18, { size: 14, color: C.clay, bold: true });
    text(slide, ctx, plan[i][1], 782, yy, 260, 18, { size: 17, color: C.ink, bold: i === 0 });
  }
  text(slide, ctx, "一句话：救急不是完整学习，是最小通过路径。", 280, 602, 720, 28, { size: 25, bold: true, align: "center" });
  foot(slide, ctx, 4);
  note(slide, "50s。讲两个关键时刻：诊断不是问卷，是按考试权重和当前基础选择测什么；主动放弃不是偷懒，是最小通过路径。这里要让评委感到 Sparkle 在做取舍。");
  return slide;
}

async function slide05(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx, "#F4EFE6");
  title(slide, ctx, "North Star / 2", "7 天救急·下：任务卡 + 失败重规划", "失败不是计划结束，而是系统更新对用户的判断。");
  rect(slide, ctx, 78, 238, 406, 360, C.white, "#DDD5C8");
  text(slide, ctx, "今日任务卡", 112, 270, 180, 28, { size: 26, bold: true });
  tinyTag(slide, ctx, "高价值", 354, 270, C.clay);
  text(slide, ctx, "理解 TCP 可靠传输", 112, 318, 260, 28, { size: 23, bold: true });
  text(slide, ctx, "预计 45 分钟 · 真题驱动 · 2 道验证题", 112, 356, 300, 20, { size: 15, color: C.muted });
  rule(slide, ctx, 112, 392, 318, 1);
  text(slide, ctx, "为什么做", 112, 410, 110, 20, { size: 16, bold: true, color: C.green });
  text(slide, ctx, "高频题型，能快速提升原理题与应用题准确率。", 112, 438, 300, 38, { size: 15, color: C.muted });
  text(slide, ctx, "卡住怎么办", 112, 494, 120, 20, { size: 16, bold: true, color: C.clay });
  text(slide, ctx, "15 分钟无进展：看示例题 → 10 分钟讲解 → 向 Sparkle 求助。", 112, 522, 300, 38, { size: 15, color: C.muted });
  const steps = [
    ["失败", "任务超时，题没做出"],
    ["归因", "不是没时间，是不会做报文段推理"],
    ["改判", "降低阅读量，增加例题拆解"],
    ["重规划", "下一张任务卡自动变短、先练题"],
  ];
  for (let i = 0; i < steps.length; i++) {
    const x = 550 + i * 156;
    rect(slide, ctx, x, 296, 124, 150, i === 1 ? C.clay2 : C.white, "#DDD5C8");
    text(slide, ctx, String(i + 1), x + 18, 316, 24, 22, { size: 18, color: [C.red, C.clay, C.sage, C.blue][i], bold: true });
    text(slide, ctx, steps[i][0], x + 18, 350, 88, 24, { size: 21, bold: true });
    text(slide, ctx, steps[i][1], x + 18, 386, 88, 42, { size: 12.5, color: C.muted });
    if (i < steps.length - 1) await icon(slide, ctx, "ChevronRight", x + 132, 360, 20, C.hair);
  }
  rect(slide, ctx, 552, 502, 592, 58, C.dark, "#00000000");
  text(slide, ctx, "Aurora 不是只改这一张任务卡，而是更新后续所有相关决策参数。", 580, 520, 536, 24, { size: 18, color: C.white, align: "center" });
  foot(slide, ctx, 5);
  note(slide, "50s。左边讲任务卡必须有为什么、材料、步骤、卡住怎么办、完成标准。右边讲失败闭环：用户纠正一次“我不是没时间，是不会做”，系统后续计划全改。过渡：7 天结束后，这些东西不会消失。");
  return slide;
}

async function slide06(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx);
  title(slide, ctx, "Long Run", "用一年后，留下的不是聊天记录", "留下的是一套关于“这个人怎么更容易做成事”的可迁移方法资产。");
  const centerX = 640, centerY = 395;
  ctx.addShape(slide, { geometry: "ellipse", x: centerX - 84, y: centerY - 84, w: 168, h: 168, fill: C.dark, line: ctx.line("#00000000", 0) });
  text(slide, ctx, "个人\n方法资产", centerX - 58, centerY - 38, 116, 76, { size: 30, color: C.white, bold: true, align: "center" });
  const assets = [
    ["薄弱点", "子网划分反复失分", 245, 260, C.clay],
    ["有效资料", "真题优先于长视频", 493, 218, C.sage],
    ["任务粒度", "45 分钟以上容易拖延", 740, 218, C.blue],
    ["策略迁移", "先练题再补理论", 850, 430, C.gold],
    ["情绪触发", "高压下需要低成本第一步", 492, 530, C.clay],
    ["社群见证", "责任伙伴记录关键突破", 216, 430, C.sage],
  ];
  for (const [head, body, x, y, color] of assets) {
    rule(slide, ctx, Math.min(x + 70, centerX), y + 42, Math.abs(centerX - x - 70), 1, color + "77");
    rect(slide, ctx, x, y, 210, 88, C.white, "#DDD5C8");
    text(slide, ctx, head, x + 18, y + 16, 120, 22, { size: 19, color, bold: true });
    text(slide, ctx, body, x + 18, y + 46, 170, 25, { size: 14, color: C.muted });
  }
  text(slide, ctx, "这不是用户自己总结的，是 Aurora 在每一次决策、反馈和纠正中自动积累的。", 250, 626, 780, 26, { size: 21, bold: true, align: "center" });
  foot(slide, ctx, 6);
  note(slide, "45s。长期价值不要说自我实现，太虚。说可迁移资产：它知道你什么薄弱、什么资料有效、任务多长会拖延、什么策略能迁移到下一门课。社群只作为资产维度出现，不抢主线。");
  return slide;
}

async function slide07(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx, "#F2EEE5");
  title(slide, ctx, "Differentiation", "为什么竞品难做到：不是单点弱，是缺闭环", "Sparkle 的差异不在“回答更聪明”，而在目标决策、执行反馈、长期资产和可信校正同时存在。");
  const x = 82, y = 244, w = 1116, rowH = 78;
  const cols = [250, 288, 288, 290];
  const headers = ["比较维度", "通用大模型", "学习工具 / 校内平台", "Sparkle"];
  let cx = x;
  for (let i = 0; i < headers.length; i++) {
    rect(slide, ctx, cx, y, cols[i], 46, i === 3 ? C.dark : C.white, "#DCD4C7");
    text(slide, ctx, headers[i], cx + 16, y + 14, cols[i] - 32, 16, { size: 14, bold: true, color: i === 3 ? C.white : C.ink, align: i === 0 ? "left" : "center" });
    cx += cols[i];
  }
  const rows = [
    ["目标决策", "能回答，但常给完整计划", "有计划表，少动态取舍", "先诊断，再算最小通过路径"],
    ["执行反馈", "对话结束即断开", "打卡为主，少错因归因", "任务结果反向更新计划"],
    ["长期资产", "聊天记录难迁移", "知识点沉淀，少方法沉淀", "沉淀个人方法资产"],
    ["可信校正", "建议黑盒，难追踪", "流程可见但 AI 决策弱", "关键决策可追溯、可纠正、可回滚"],
  ];
  for (let r = 0; r < rows.length; r++) {
    cx = x;
    const yy = y + 46 + r * rowH;
    for (let c = 0; c < headers.length; c++) {
      rect(slide, ctx, cx, yy, cols[c], rowH, c === 3 ? "#F7FBF2" : C.white, c === 3 ? C.sage : "#E0D8CB");
      text(slide, ctx, rows[r][c], cx + 16, yy + (c === 0 ? 25 : 19), cols[c] - 32, 38, { size: c === 0 ? 18 : 15, bold: c === 0 || c === 3, color: c === 3 ? C.green : c === 0 ? C.ink : C.muted, align: c === 0 ? "left" : "center" });
      cx += cols[c];
    }
  }
  text(slide, ctx, "我们不否认通用模型很强；Sparkle 做的是把强模型变成普通用户可稳定获得结果的系统。", 146, 628, 988, 25, { size: 20, bold: true, align: "center" });
  foot(slide, ctx, 7);
  note(slide, "50s。姿态要稳：不要贬低 ChatGPT、Claude、DeepSeek、豆包或校内平台。它们强在单点能力或入口，但 Sparkle 补的是目标闭环。可信维度要说一句：关键决策可追溯、可纠正、可回滚，这是 AI 教育产品的信任基础。");
  return slide;
}

async function slide08(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx);
  title(slide, ctx, "Proof", "不是概念：已有可运行系统", "产品体验有清晰形态，底层工程也已经通过多轮本地验证。");
  await phoneFrame(slide, ctx, 96, 236, 250, 392, "cover");
  text(slide, ctx, "界面示意，可替换为真实截图", 114, 638, 214, 18, { size: 11, color: "#8C857B", align: "center" });
  metric(slide, ctx, "24 种", "极端目标场景全通过：含零基础、7 天 deadline、多目标冲突", 430, 226, 302, C.sage);
  metric(slide, ctx, "12/12", "ExamSprintBench 本地冲刺场景通过", 766, 226, 302, C.clay);
  metric(slide, ctx, "97.3%", "Aurora closeout 验收项完成率：72/74 verified", 430, 354, 302, C.blue);
  metric(slide, ctx, "90%+", "关键路径真机/本地联调已跑通，移动端黑洞状态降为 0%", 766, 354, 302, C.gold);
  rect(slide, ctx, 430, 508, 638, 72, C.dark, "#00000000");
  text(slide, ctx, "这些数字不是为了炫工程量，而是回答评委心里的问题：这不是 PPT 公司，已经有能跑、能测、能继续迭代的系统底座。", 458, 526, 584, 30, { size: 17, color: C.white, align: "center" });
  foot(slide, ctx, 8);
  note(slide, "40s。先让评委看到产品形态，再给工程证据。数字要翻译成人话：24 种极端场景不是 benchmark 名词，是零基础、7 天 deadline、多目标冲突这些难场景。这里可替换真实截图，正式比赛前最好换。");
  return slide;
}

async function slide09(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx, "#F3EFE7");
  title(slide, ctx, "Team", "为什么我们能做成：导师把关 + 工程型团队", "这不是单点算法项目，而是产品、AI、工程、安全和验证一起推进的系统工程。");
  rect(slide, ctx, 80, 228, 342, 300, C.white, "#DDD5C8");
  text(slide, ctx, "项目导师", 112, 260, 100, 22, { size: 16, color: C.clay, bold: true });
  text(slide, ctx, "黄亚坤", 112, 298, 160, 36, { size: 34, bold: true });
  text(slide, ctx, "副教授 · 博士\n北京邮电大学计算机学院\n国家示范性软件学院", 112, 348, 260, 72, { size: 17, color: C.muted });
  text(slide, ctx, "负责研究方案指导、技术路线把关、实验设计与论文写作指导。", 112, 446, 260, 46, { size: 16, color: C.ink });
  const layers = [
    ["产品与用户洞察", "北极星场景、完整体验、路线规划"],
    ["AI 系统设计", "Aurora、Causal Spine、知识星图"],
    ["后端与可信执行", "Python AI Engine、Go Gateway、OpenClaw"],
    ["移动端体验", "Flutter 产品界面、任务流、社区协同"],
    ["验证与安全", "Benchmark、trace、RBAC、审计"],
  ];
  for (let i = 0; i < layers.length; i++) {
    const yy = 226 + i * 62;
    rect(slide, ctx, 470, yy, 328, 46, i % 2 === 0 ? C.white : C.sage2, "#DDD5C8");
    text(slide, ctx, layers[i][0], 492, yy + 9, 130, 15, { size: 14, color: C.green, bold: true });
    text(slide, ctx, layers[i][1], 492, yy + 27, 268, 12, { size: 11.5, color: C.muted });
  }
  const members = [
    ["邓博仁", "计算机科学与技术", "产品愿景 / 系统架构 / 核心研发"],
    ["张雨凝", "计算机科学与技术", "产品与移动端协作"],
    ["王宇", "电子信息", "工程实现与测试协作"],
    ["王英树", "计算机科学与技术", "后端与验证协作"],
  ];
  for (let i = 0; i < members.length; i++) {
    const yy = 228 + i * 74;
    rect(slide, ctx, 842, yy, 310, 64, C.white, "#DDD5C8");
    text(slide, ctx, members[i][0], 864, yy + 11, 88, 22, { size: 20, bold: true });
    text(slide, ctx, members[i][1], 964, yy + 14, 160, 16, { size: 12.5, color: C.muted });
    text(slide, ctx, members[i][2], 864, yy + 36, 236, 16, { size: 11.5, color: C.blue });
  }
  foot(slide, ctx, 9);
  note(slide, "40s。团队页不要念出生年份。讲导师保证研究方案和实验设计，团队覆盖产品、AI、后端、移动端、验证安全。邓博仁作为汇报人与核心负责人，可以在口播里自然点出。");
  return slide;
}

async function slide10(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx);
  title(slide, ctx, "Growth", "未来：从校园救急到 AI-native Goal OS", "先从最刚需、最可验证的校园考试切入，再扩展到长期学习与个人目标管理。");
  const phases = [
    ["1", "北邮试点", "7 天救急 / 课程场景验证 PMF"],
    ["2", "多高校复制", "期末、竞赛、考研等高压目标"],
    ["3", "机构合作", "课程体系、班级辅导、导师减负"],
    ["4", "Goal OS", "从学习扩展到个人成长目标"],
  ];
  for (let i = 0; i < phases.length; i++) {
    const x = 90 + i * 286;
    ctx.addShape(slide, { geometry: "ellipse", x: x + 70, y: 270, w: 82, h: 82, fill: i === 0 ? C.clay : C.sage2, line: ctx.line("#00000000", 0) });
    text(slide, ctx, phases[i][0], x + 98, 292, 26, 28, { size: 26, color: i === 0 ? C.white : C.green, bold: true, align: "center" });
    text(slide, ctx, phases[i][1], x, 386, 222, 28, { size: 25, bold: true, align: "center" });
    text(slide, ctx, phases[i][2], x + 10, 426, 202, 40, { size: 15, color: C.muted, align: "center" });
    if (i < phases.length - 1) rule(slide, ctx, x + 166, 310, 118, 3, C.hair);
  }
  rect(slide, ctx, 154, 538, 430, 86, C.white, "#DDD5C8");
  text(slide, ctx, "C 端订阅", 184, 562, 130, 24, { size: 23, bold: true, color: C.clay });
  text(slide, ctx, "学生为高频刚需与关键节点付费：考试救急、长期计划、复习资产。", 330, 558, 210, 38, { size: 15, color: C.muted });
  rect(slide, ctx, 694, 538, 430, 86, C.white, "#DDD5C8");
  text(slide, ctx, "D 端合作", 724, 562, 130, 24, { size: 23, bold: true, color: C.green });
  text(slide, ctx, "与高校、课程团队、教育机构合作：个性化辅导、学习数据与导师减负。", 870, 558, 210, 38, { size: 15, color: C.muted });
  foot(slide, ctx, 10);
  note(slide, "35s。商业模式不要空喊市场规模。说清楚为什么从校园开始：高频、刚需、可验证、传播快。C 端订阅先跑 PMF，D 端和课程/机构合作扩大。");
  return slide;
}

async function slide11(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx, C.dark);
  await phoneFrame(slide, ctx, 82, 82, 230, 500, "cover");
  text(slide, ctx, "回到那个学生", 390, 118, 360, 42, { size: 34, color: C.clay2, bold: true });
  text(slide, ctx, "7 天前，他面对计网考试，基本没学。", 390, 206, 690, 44, { size: 33, color: C.white, bold: true });
  text(slide, ctx, "7 天后，他通过了。", 390, 274, 420, 42, { size: 33, color: C.white, bold: true });
  text(slide, ctx, "不是因为 Sparkle 比他聪明，\n而是因为 Sparkle 帮他做了那些他不知道该怎么做的决策。", 390, 354, 700, 78, { size: 27, color: "#D9E2D1" });
  rule(slide, ctx, 390, 480, 620, 1, "#53606A");
  text(slide, ctx, "我们相信：能不能做成事，不应该取决于你多会用 AI、多会做计划、多有钱请私教。", 390, 516, 710, 38, { size: 21, color: "#D8D0C2", bold: true });
  text(slide, ctx, "Sparkle 让普通人第一次就能走进自己的目标路径。", 390, 586, 620, 30, { size: 24, color: C.white, bold: true });
  foot(slide, ctx, 11, "Sparkle · Thank you");
  note(slide, "30s。收束回到第一页。不要再开新概念，用完整故事闭环。最后一句落到信念：能不能做成事，不应该取决于用户会不会 prompt、会不会做计划、有没有钱请私教。");
  return slide;
}

async function appendixBase(presentation, ctx, n, kicker, headline, sub) {
  const slide = presentation.slides.add();
  bg(slide, ctx, n % 2 === 0 ? "#F6F2E9" : "#F1EDE4");
  title(slide, ctx, kicker, headline, sub);
  foot(slide, ctx, n, "Appendix");
  return slide;
}

async function slide12(presentation, ctx) {
  const slide = await appendixBase(presentation, ctx, 12, "Appendix A", "社群不是聊天广场，而是目标推进结构", "责任伙伴、冲刺小组和 check-in 机制补足纯 AI 的执行弱点。");
  const items = [["责任伙伴", "互相见证目标、提醒关键节点、降低中途放弃概率"], ["冲刺小组", "围绕考试/竞赛 deadline 形成短期协同"], ["群聊与打卡", "把执行证据沉淀为可追踪事件"], ["社群引入", "从个人任务扩展到班级、课程、机构协作"]];
  for (let i = 0; i < items.length; i++) {
    const x = 90 + (i % 2) * 560, y = 254 + Math.floor(i / 2) * 150;
    rect(slide, ctx, x, y, 480, 104, C.white, "#DDD5C8");
    await icon(slide, ctx, i === 0 ? "Users" : i === 1 ? "CalendarDays" : i === 2 ? "CheckCircle2" : "School", x + 24, y + 28, 36, [C.sage, C.clay, C.blue, C.gold][i]);
    text(slide, ctx, items[i][0], x + 82, y + 24, 160, 22, { size: 23, bold: true });
    text(slide, ctx, items[i][1], x + 82, y + 58, 340, 30, { size: 16, color: C.muted });
  }
  note(slide, "附录。若评委问“是不是只有 AI 对话”，用这一页说明社群是目标执行系统的一部分，不是泛社交。");
  return slide;
}

async function slide13(presentation, ctx) {
  const slide = await appendixBase(presentation, ctx, 13, "Appendix B", "安全与可追溯：AI 建议必须能被信任", "关键决策要有 trace、receipt、纠正与回滚机制。");
  const chain = [["Decision Trace", "为什么建议先救 TCP"], ["Context Receipt", "用了哪些资料和用户状态"], ["User Correction", "用户可纠正：不是没时间，是不会做"], ["Policy Guard", "RBAC / kill switch / 审计日志"]];
  for (let i = 0; i < chain.length; i++) {
    const x = 96 + i * 282;
    rect(slide, ctx, x, 285, 220, 160, i === 0 ? C.dark : C.white, i === 0 ? "#00000000" : "#DDD5C8");
    text(slide, ctx, chain[i][0], x + 22, 320, 176, 24, { size: 20, bold: true, color: i === 0 ? C.white : C.ink, align: "center" });
    text(slide, ctx, chain[i][1], x + 22, 362, 176, 40, { size: 15, color: i === 0 ? "#D8D0C2" : C.muted, align: "center" });
    if (i < chain.length - 1) await icon(slide, ctx, "ArrowRight", x + 236, 350, 30, C.clay);
  }
  text(slide, ctx, "可信不是“我们保证不出错”，而是出错时能看见、能纠正、能把系统带回正确轨道。", 190, 532, 900, 28, { size: 23, bold: true, align: "center" });
  note(slide, "附录。回答 AI 教育产品的信任问题：决策依据可见，用户纠正会进入系统，权限与审计保证边界。");
  return slide;
}

async function slide14(presentation, ctx) {
  const slide = await appendixBase(presentation, ctx, 14, "Appendix C", "Aurora：自适应认知控制层", "把裸模型调用变成带目标、状态、偏好、资料与反馈的 harness。");
  const rows = [["输入", "目标 / deadline / 用户情绪 / 当前资料"], ["理解", "多层用户模型 + 场景模式识别"], ["决策", "诊断、取舍、任务粒度、模型路由"], ["输出", "任务卡、解释、追问、下一步"], ["反馈", "结果、错因、纠正、trace 回写"]];
  for (let i = 0; i < rows.length; i++) {
    const y = 232 + i * 66;
    rect(slide, ctx, 170, y, 200, 42, C.dark, "#00000000");
    text(slide, ctx, rows[i][0], 190, y + 11, 160, 14, { size: 16, color: C.white, bold: true, align: "center" });
    rect(slide, ctx, 420, y, 650, 42, C.white, "#DDD5C8");
    text(slide, ctx, rows[i][1], 446, y + 11, 600, 14, { size: 16, color: C.ink });
  }
  note(slide, "附录。用技术但不堆名词：Aurora 的价值是让每次模型调用前先组装上下文和决策目标。");
  return slide;
}

async function slide15(presentation, ctx) {
  const slide = await appendixBase(presentation, ctx, 15, "Appendix D", "知识星图：个人知识库不是笔记堆", "它记录掌握度、证据、错因和迁移关系。");
  const nodes = [
    ["TCP", 600, 352, 92, C.dark],
    ["可靠传输", 430, 250, 64, C.blue],
    ["拥塞控制", 760, 250, 64, C.sage],
    ["差错检测", 800, 438, 64, C.clay],
    ["子网划分", 390, 444, 64, C.gold],
    ["应用层", 600, 512, 54, "#B9B2A6"],
  ];
  for (const [name, x, y, r, color] of nodes) {
    rule(slide, ctx, 646, 398, x + r / 2 - 646, y + r / 2 - 398, 2, color + "66");
  }
  for (const [name, x, y, r, color] of nodes) {
    ctx.addShape(slide, { geometry: "ellipse", x, y, w: r, h: r, fill: color, line: ctx.line("#FFFFFF", 2) });
    text(slide, ctx, name, x + 4, y + r / 2 - 10, r - 8, 20, { size: r > 70 ? 18 : 13, color: C.white, bold: true, align: "center" });
  }
  rect(slide, ctx, 92, 278, 230, 188, C.white, "#DDD5C8");
  text(slide, ctx, "每个节点包含", 118, 306, 150, 24, { size: 22, bold: true });
  text(slide, ctx, "掌握证据\n错因记录\n资料来源\n下一步任务\n可迁移策略", 118, 350, 170, 90, { size: 17, color: C.muted });
  note(slide, "附录。知识星图不要讲成漂亮图，而是讲成用户长期资产的数据结构。");
  return slide;
}

async function slide16(presentation, ctx) {
  const slide = await appendixBase(presentation, ctx, 16, "Appendix E", "Skill Extraction：从一次成功中提取可复用方法", "系统不是只记住结果，而是提取策略信念并进入 Learning Base。");
  const flow = [["Episode", "一次任务/考试过程"], ["Evidence", "结果、错因、纠正"], ["Strategy Belief", "形成策略信念"], ["Learning Base", "跨目标复用"], ["Next Goal", "自动推荐"]];
  for (let i = 0; i < flow.length; i++) {
    const x = 92 + i * 230;
    rect(slide, ctx, x, 324, 176, 110, i === 2 ? C.clay2 : C.white, "#DDD5C8");
    text(slide, ctx, flow[i][0], x + 14, 350, 148, 22, { size: 18, bold: true, align: "center", color: i === 2 ? C.clay : C.ink });
    text(slide, ctx, flow[i][1], x + 16, 386, 144, 28, { size: 13, color: C.muted, align: "center" });
    if (i < flow.length - 1) await icon(slide, ctx, "ArrowRight", x + 188, 366, 28, C.sage);
  }
  text(slide, ctx, "例：计网中验证有效的“先练真题再补理论”，下次数据库考试会成为优先策略候选。", 170, 528, 940, 28, { size: 22, bold: true, align: "center" });
  note(slide, "附录。回答系统如何越用越好：不是简单记忆聊天，而是从 episode 中抽取策略。");
  return slide;
}

async function slide17(presentation, ctx) {
  const slide = await appendixBase(presentation, ctx, 17, "Appendix F", "MirrorFish / 多 Agent 推演", "用模拟世界和角色代理提前压力测试策略，而不是只靠真实用户试错。");
  const lanes = [["目标世界", "GoalWorldGraph 定义目标、约束、路径"], ["角色代理", "学生、导师、系统、责任伙伴多角色交互"], ["推演结果", "发现冲突、风险和失败路径"], ["策略修正", "回写计划、提示词、任务模板"]];
  for (let i = 0; i < lanes.length; i++) {
    const y = 236 + i * 86;
    rect(slide, ctx, 150, y, 220, 54, C.dark, "#00000000");
    text(slide, ctx, lanes[i][0], 180, y + 17, 160, 18, { size: 18, color: C.white, bold: true, align: "center" });
    rect(slide, ctx, 420, y, 660, 54, C.white, "#DDD5C8");
    text(slide, ctx, lanes[i][1], 450, y + 17, 600, 18, { size: 17, color: C.ink });
  }
  note(slide, "附录。回答策略怎么验证有效：通过多 agent 推演发现失败路径，再回写策略。");
  return slide;
}

async function slide18(presentation, ctx) {
  const slide = await appendixBase(presentation, ctx, 18, "Appendix G", "技术架构：模型能力之外，是一套目标实现系统", "Python AI Engine、Go Gateway、Flutter、数据库、可信执行和多模型路由协同。");
  const boxes = [
    ["Flutter Mobile", 90, 260, C.blue2],
    ["Go Gateway\nWebSocket / HTTP", 350, 260, C.sage2],
    ["Python AI Engine\nAurora / Causal Spine", 610, 260, C.clay2],
    ["Data Layer\nPostgreSQL / Redis / Trace", 870, 260, C.white],
    ["Model Router\nDeepSeek / OpenAI / others", 610, 455, C.white],
  ];
  for (const [label, x, y, fill] of boxes) {
    rect(slide, ctx, x, y, 230, 94, fill, "#DDD5C8");
    text(slide, ctx, label, x + 18, y + 26, 194, 40, { size: 18, bold: true, align: "center" });
  }
  await icon(slide, ctx, "ArrowRight", 318, 292, 28, C.sage);
  await icon(slide, ctx, "ArrowRight", 578, 292, 28, C.clay);
  await icon(slide, ctx, "ArrowRight", 838, 292, 28, C.blue);
  await icon(slide, ctx, "ArrowDown", 710, 368, 28, C.gold);
  text(slide, ctx, "技术架构图放附录，主线只讲用户能感知到的结果；答辩时再展开每层如何支撑闭环。", 190, 606, 900, 26, { size: 20, bold: true, align: "center" });
  note(slide, "附录。技术答辩页，避免主讲时陷入架构细节。");
  return slide;
}

async function slide19(presentation, ctx) {
  const slide = await appendixBase(presentation, ctx, 19, "Appendix H", "工程验证详情", "把“我们做出来了”从口号变成可检查的进展。");
  const rows = [
    ["SparkleGoalBench", "24/24", "覆盖极端目标场景与闭环路径"],
    ["ExamSprintBench", "12/12", "考试冲刺核心路径通过"],
    ["Aurora Closeout", "72/74", "97.3% 验收项 verified"],
    ["移动端黑洞", "0%", "关键启动/回退状态已收敛"],
    ["安全机制", "RBAC / trace / kill switch", "访问控制、追踪、开关与审计"],
  ];
  for (let i = 0; i < rows.length; i++) {
    const y = 224 + i * 68;
    rect(slide, ctx, 110, y, 1060, 50, i % 2 ? C.white : "#FBFAF5", "#E1D9CC");
    text(slide, ctx, rows[i][0], 140, y + 15, 260, 16, { size: 16, bold: true });
    text(slide, ctx, rows[i][1], 430, y + 13, 190, 20, { size: 19, bold: true, color: i === 1 ? C.clay : C.green, align: "center" });
    text(slide, ctx, rows[i][2], 670, y + 15, 440, 16, { size: 15, color: C.muted });
  }
  note(slide, "附录。答辩时可用于解释具体工程进展。注意这些指标应与最新测试结果保持同步。");
  return slide;
}

export const slides = [
  slide01, slide02, slide03, slide04, slide05, slide06, slide07, slide08, slide09, slide10, slide11,
  slide12, slide13, slide14, slide15, slide16, slide17, slide18, slide19,
];

export async function addByIndex(presentation, ctx, index) {
  return slides[index - 1](presentation, ctx);
}
