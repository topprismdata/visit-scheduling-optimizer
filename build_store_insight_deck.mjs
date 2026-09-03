import pptxgen from "/Users/ghb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pptxgenjs/dist/pptxgen.es.js";

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "TopPrism";
pptx.subject = "SH Store Insight 产品介绍";
pptx.title = "SH Store Insight｜看懂售点数据，提炼可信洞察";
pptx.company = "棱镜极";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "Heiti SC",
  bodyFontFace: "Heiti SC",
  lang: "zh-CN"
};

const OUT = "/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer/SH_Store_Insight_产品介绍_v1.0.pptx";
const BG = "/Users/ghb/Documents/Codex/2026-07-27/users-ghb-workbuddy-2026-07-22/work/mousheng/double-prism/double-prism-background-v2.png";
const LOGO = "/Users/ghb/Documents/Codex/2026-07-27/users-ghb-workbuddy-2026-07-22/work/mousheng/topprism-logo.png";

const C = {
  navy: "07162D", navy2: "0B1C39", card: "102544", blue: "55C2FF",
  blue2: "73A7FF", violet: "9B7CFF", pink: "E879F9", amber: "FFB45E",
  white: "F5FAFF", text: "D8E7F7", muted: "91A7BF", line: "274766",
  light: "F5F8FC", ink: "132238", gray: "5E7185", pale: "E8F2FA"
};

const addText = (s, text, x, y, w, h, opt={}) => s.addText(text, {
  x,y,w,h, margin:0, fontFace: opt.fontFace || "Heiti SC",
  fontSize: opt.fontSize || 18, color: opt.color || C.text,
  bold: opt.bold || false, breakLine: false, valign: opt.valign || "mid",
  align: opt.align || "left", fit: "shrink", ...opt
});

function darkBase(title, kicker, page) {
  const s = pptx.addSlide();
  s.background = { color: C.navy };
  s.addShape(pptx.ShapeType.rect,{x:0,y:0,w:13.333,h:0.06,fill:{color:C.blue},line:{color:C.blue}});
  addText(s,kicker.toUpperCase(),0.62,0.32,4.5,0.25,{fontSize:8.5,color:C.blue,bold:true,charSpacing:1.8});
  addText(s,title,0.62,0.62,11.9,0.52,{fontSize:25,color:C.white,bold:true});
  addText(s,String(page).padStart(2,"0"),12.2,7.06,0.5,0.18,{fontSize:7.5,color:C.muted,align:"right"});
  return s;
}

function lightBase(title, kicker, page) {
  const s = pptx.addSlide();
  s.background = { color: C.light };
  s.addShape(pptx.ShapeType.rect,{x:0,y:0,w:13.333,h:0.06,fill:{color:C.blue},line:{color:C.blue}});
  addText(s,kicker.toUpperCase(),0.62,0.32,4.5,0.25,{fontSize:8.5,color:"2683B8",bold:true,charSpacing:1.8});
  addText(s,title,0.62,0.62,11.9,0.52,{fontSize:25,color:C.ink,bold:true});
  addText(s,String(page).padStart(2,"0"),12.2,7.06,0.5,0.18,{fontSize:7.5,color:C.gray,align:"right"});
  return s;
}

function card(s,x,y,w,h,title,body,color=C.blue,dark=true) {
  s.addShape(pptx.ShapeType.roundRect,{x,y,w,h,rectRadius:0.08,
    fill:{color:dark?C.card:"FFFFFF",transparency:dark?4:0},
    line:{color:dark?C.line:"D9E5EF",width:1}});
  s.addShape(pptx.ShapeType.rect,{x:x+0.18,y:y+0.2,w:0.07,h:0.38,fill:{color},line:{color}});
  addText(s,title,x+0.38,y+0.18,w-0.55,0.38,{fontSize:14,bold:true,color:dark?C.white:C.ink});
  addText(s,body,x+0.25,y+0.72,w-0.5,h-0.9,{fontSize:10.5,color:dark?C.text:C.gray,valign:"top",breakLine:true});
}

function pill(s,text,x,y,w,color=C.blue,dark=true) {
  s.addShape(pptx.ShapeType.roundRect,{x,y,w,h:0.34,rectRadius:0.16,fill:{color,transparency:dark?78:86},line:{color,width:0.8}});
  addText(s,text,x,y+0.01,w,0.3,{fontSize:8.5,color:dark?C.white:C.ink,align:"center",bold:true});
}

// 1. Cover
{
  const s = pptx.addSlide();
  s.addImage({path:BG,x:0,y:0,w:13.333,h:7.5});
  s.addShape(pptx.ShapeType.rect,{x:0,y:0,w:13.333,h:7.5,fill:{color:C.navy,transparency:26},line:{color:C.navy,transparency:100}});
  s.addImage({path:LOGO,x:0.58,y:0.38,w:1.35,h:0.42,transparency:0});
  addText(s,"SH STORE INSIGHT",0.7,1.35,6.8,0.4,{fontSize:12,color:C.blue,bold:true,charSpacing:3});
  addText(s,"看懂售点数据\n提炼可信洞察",0.7,1.88,7.0,1.65,{fontSize:37,color:C.white,bold:true,breakLine:true,breakLineOnTextOverflow:false});
  addText(s,"一句业务问题，获得一份清晰、可信、可追溯的洞察",0.73,3.72,7.5,0.45,{fontSize:16,color:C.text});
  pill(s,"独立 Insight 组件",0.73,4.45,1.85,C.blue,true);
  pill(s,"业务语义驱动",2.75,4.45,1.8,C.violet,true);
  pill(s,"证据与质量同行",4.72,4.45,2.0,C.pink,true);
  addText(s,"Decision Intelligence. On Demand.",0.73,6.72,4.8,0.24,{fontSize:9,color:C.muted,charSpacing:1.1});
  s.addNotes("开场建议：SH Store Insight 不是通用数据平台，也不负责派单和执行。它只做一件事：把复杂售点数据转化为业务人员能够理解、能够追溯、能够继续使用的洞察。整套产品遵循棱镜极双棱镜哲学——把复杂留给AI，把清晰交给业务。");
}

// 2. Problem
{
  const s = lightBase("售点数据很多，真正的洞察却很少","THE PROBLEM",2);
  const items = [
    ["153+ 字段","物理字段复杂，业务人员不知道该用哪一列",C.blue],
    ["业务语言不一致","高潜力、景区周边、上海市等概念需要解释",C.violet],
    ["结果不等于洞察","返回几千行数据，仍然没有回答什么值得关注",C.pink]
  ];
  items.forEach((it,i)=>card(s,0.75+i*4.15,1.55,3.75,2.25,it[0],it[1],it[2],false));
  s.addShape(pptx.ShapeType.roundRect,{x:0.75,y:4.25,w:12,h:1.55,rectRadius:0.08,fill:{color:"EAF5FC"},line:{color:"B9DDF1",width:1}});
  addText(s,"真正的问题",1.05,4.58,1.5,0.35,{fontSize:12,color:"2683B8",bold:true});
  addText(s,"不是“如何查到数据”，而是“如何把业务问题转化为可信洞察”。",2.45,4.38,9.5,0.75,{fontSize:24,color:C.ink,bold:true,align:"center"});
  addText(s,"SH Store Insight 在业务语言与售点数据之间建立一层可管理、可验证的解释能力。",2.1,5.18,10.1,0.35,{fontSize:12,color:C.gray,align:"center"});
  s.addNotes("这一页强调客户痛点。数据宽表不是能力，能把客户熟悉的业务语言稳定映射到正确数据，并从结果中提炼出值得关注的事实，才是产品价值。重点不要讲技术框架。");
}

// 3. Positioning
{
  const s = darkBase("一个边界清晰的独立 Insight 组件","PRODUCT POSITIONING",3);
  addText(s,"输入",0.8,1.55,1.2,0.35,{fontSize:13,color:C.blue,bold:true,align:"center"});
  addText(s,"SH Store Insight",5.05,1.55,3.2,0.35,{fontSize:13,color:C.violet,bold:true,align:"center"});
  addText(s,"输出",11.2,1.55,1.2,0.35,{fontSize:13,color:C.pink,bold:true,align:"center"});
  card(s,0.65,2.0,2.75,2.8,"业务问题 + 售点数据","自然语言问题\n结构化分析请求\n数据集与语义版本\n可选范围、指标和规则",C.blue,true);
  s.addShape(pptx.ShapeType.chevron,{x:3.55,y:3.0,w:0.8,h:0.65,fill:{color:C.blue,transparency:28},line:{color:C.blue,transparency:100}});
  card(s,4.45,2.0,4.4,2.8,"观察 · 分析 · 解释","理解业务语义\n执行确定性分析\n发现结构与差异\n评估数据质量\n组织证据与限制",C.violet,true);
  s.addShape(pptx.ShapeType.chevron,{x:9.0,y:3.0,w:0.8,h:0.65,fill:{color:C.pink,transparency:28},line:{color:C.pink,transparency:100}});
  card(s,9.9,2.0,2.75,2.8,"Insight Package","核心结论\n数据证据\n置信边界\n限制说明\n下一步分析",C.pink,true);
  addText(s,"只负责“看懂并说清楚”",0.8,5.42,5.5,0.45,{fontSize:19,color:C.white,bold:true});
  addText(s,"不负责派单、排程、路线、CRM 或业务执行",6.1,5.46,6.1,0.38,{fontSize:13,color:C.muted,align:"right"});
  s.addNotes("边界是这页的重点。组件输入业务问题与售点数据，输出结构化洞察。它不做派单、拜访排程或CRM，也不替客户做最终业务决策。这样才能成为可组合、可复用的独立组件。");
}

// 4. Double prism
{
  const s = darkBase("双棱镜：把复杂留给 AI，把清晰交给业务","THE DOUBLE PRISM",4);
  s.addShape(pptx.ShapeType.chevron,{x:0.85,y:2.45,w:1.35,h:1.45,fill:{color:"DCEEFF",transparency:15},line:{color:C.blue,width:1.2}});
  addText(s,"一句业务问题",0.55,4.15,1.9,0.38,{fontSize:12,color:C.white,bold:true,align:"center"});
  s.addShape(pptx.ShapeType.triangle,{x:2.55,y:1.9,w:1.55,h:2.65,rotate:90,fill:{color:C.blue,transparency:40},line:{color:C.blue,width:1.6}});
  addText(s,"第一棱镜",2.45,4.8,1.8,0.35,{fontSize:13,color:C.blue,bold:true,align:"center"});
  addText(s,"展开复杂性",2.4,5.18,1.9,0.32,{fontSize:10.5,color:C.text,align:"center"});
  const beams = [
    ["对象",C.blue,2.15],["范围",C.blue2,2.55],["指标",C.violet,2.95],
    ["规则",C.pink,3.35],["口径",C.amber,3.75]
  ];
  beams.forEach((b)=>{
    s.addShape(pptx.ShapeType.line,{x:4.0,y:b[2],w:4.85,h:(3.0-b[2])*0.18,line:{color:b[1],width:3,transparency:15}});
    addText(s,b[0],5.55,b[2]-0.23,0.75,0.28,{fontSize:8.5,color:b[1],bold:true,align:"center"});
  });
  s.addShape(pptx.ShapeType.triangle,{x:8.85,y:1.9,w:1.55,h:2.65,rotate:270,fill:{color:C.violet,transparency:40},line:{color:C.violet,width:1.6}});
  addText(s,"第二棱镜",8.7,4.8,1.85,0.35,{fontSize:13,color:C.violet,bold:true,align:"center"});
  addText(s,"收束复杂性",8.65,5.18,1.95,0.32,{fontSize:10.5,color:C.text,align:"center"});
  s.addShape(pptx.ShapeType.chevron,{x:11.05,y:2.45,w:1.35,h:1.45,fill:{color:"FFFFFF",transparency:12},line:{color:C.pink,width:1.2}});
  addText(s,"结论 · 证据\n质量 · 限制",10.75,4.08,1.95,0.75,{fontSize:11.5,color:C.white,bold:true,align:"center",breakLine:true});
  addText(s,"理解与计算发生在中间，客户只需要面对清晰的输入与输出。",2.35,6.15,8.7,0.38,{fontSize:13,color:C.muted,align:"center"});
  s.addNotes("第一棱镜把一句业务问题展开成对象、范围、指标、规则与口径。中间光谱代表查询、统计、比较、验证与质量判断。第二棱镜把复杂结果重新收束成结论、证据、质量和限制。下一步只给分析建议，不越界成为业务执行。");
}

// 5. Capabilities
{
  const s = lightBase("六项能力，服务于同一个结果：可信洞察","CORE CAPABILITIES",5);
  const caps = [
    ["01","业务语义理解","把品牌、区域、业态、指标和口语规则映射为受控语义",C.blue],
    ["02","查询与探索","支持明细、分布、比较、排序和连续下钻",C.blue2],
    ["03","规则评估","按用户明确规则计算符合度，不包装成自动决策",C.violet],
    ["04","洞察综合","提炼事实、结构、差异、异常和后续分析方向",C.pink],
    ["05","质量与置信","同步输出样本、缺失、适用性、代理指标和限制",C.amber],
    ["06","多形态交付","以文本、表格、CSV、图表和接口交付同一份洞察",C.blue]
  ];
  caps.forEach((c,i)=>{
    const col=i%3,row=Math.floor(i/3),x=0.7+col*4.18,y=1.45+row*2.38;
    s.addShape(pptx.ShapeType.roundRect,{x,y,w:3.78,h:2.0,rectRadius:0.08,fill:{color:"FFFFFF"},line:{color:"D7E4EE",width:1}});
    addText(s,c[0],x+0.22,y+0.18,0.55,0.38,{fontSize:17,color:c[3],bold:true});
    addText(s,c[1],x+0.86,y+0.2,2.55,0.35,{fontSize:14,color:C.ink,bold:true});
    addText(s,c[2],x+0.25,y+0.78,3.25,0.82,{fontSize:10.3,color:C.gray,valign:"top",breakLine:true});
    s.addShape(pptx.ShapeType.line,{x:x+0.25,y:y+1.72,w:3.1,h:0,line:{color:c[3],width:1.6,transparency:40}});
  });
  s.addNotes("这六项不是六个独立产品。它们共同服务于一个结果：可信洞察。技术引擎、缓存、MCP、图表库都只是内部实现，不作为客户侧产品卖点。");
}

// 6. Output contract
{
  const s = darkBase("每一份洞察，都交付完整的 Insight Package","STANDARD OUTPUT",6);
  const centerX=6.67, centerY=3.52;
  s.addShape(pptx.ShapeType.ellipse,{x:5.25,y:2.18,w:2.84,h:2.84,fill:{color:C.violet,transparency:72},line:{color:C.violet,width:1.6}});
  addText(s,"INSIGHT\nPACKAGE",5.65,2.95,2.05,1.1,{fontSize:20,color:C.white,bold:true,align:"center",breakLine:true});
  const nodes=[
    ["核心结论","一句话回答业务问题",0.8,1.4,C.blue],
    ["分析解释","系统如何理解对象与规则",9.75,1.4,C.blue2],
    ["数据证据","样本、表格与下钻线索",0.8,4.65,C.violet],
    ["质量与置信","缺失、适用性与可信等级",9.75,4.65,C.pink],
    ["限制说明","不能支持什么结论",4.45,5.55,C.amber]
  ];
  nodes.forEach(n=>card(s,n[2],n[3],2.8,1.15,n[0],n[1],n[4],true));
  [[3.6,2.0,1.65,0.9],[8.08,2.0,1.67,0.9],[3.6,5.0,1.65,-0.85],[8.08,5.0,1.67,-0.85],[6.65,5.03,0,0.5]].forEach(l=>s.addShape(pptx.ShapeType.line,{x:l[0],y:l[1],w:l[2],h:l[3],line:{color:C.line,width:1.2,dash:"dash"}}));
  addText(s,"结构化输出是主契约；文本、表格和图表只是不同表现形式。",2.4,6.85,8.55,0.3,{fontSize:11.5,color:C.muted,align:"center"});
  s.addNotes("强调输出必须完整。只有结论没有证据，不是洞察；只有证据没有结论，也不是洞察。质量与限制必须和结果一起生成，而不是在用户追问后才补充。");
}

// 7. Example
{
  const s = lightBase("从一句问题，到一份可以继续使用的洞察","EXAMPLE",7);
  s.addShape(pptx.ShapeType.roundRect,{x:0.72,y:1.4,w:4.1,h:0.75,rectRadius:0.12,fill:{color:"E8F5FC"},line:{color:"B7DFF2"}});
  addText(s,"“海南不同县市的售点结构如何？”",1.02,1.57,3.5,0.35,{fontSize:15,color:C.ink,bold:true,align:"center"});
  addText(s,"第一棱镜识别",0.75,2.45,2.0,0.32,{fontSize:11,color:"2683B8",bold:true});
  [["对象","海南售点"],["粒度","县市"],["指标","数量 / 占比 / 类型"],["输出","洞察 + 地图 + 下钻"]].forEach((r,i)=>{
    addText(s,r[0],0.78,2.9+i*0.62,0.7,0.3,{fontSize:9,color:C.gray,bold:true});
    addText(s,r[1],1.55,2.85+i*0.62,3.0,0.38,{fontSize:11.5,color:C.ink});
  });
  s.addShape(pptx.ShapeType.roundRect,{x:5.15,y:1.35,w:7.45,h:4.95,rectRadius:0.08,fill:{color:"FFFFFF"},line:{color:"D6E3ED"}});
  addText(s,"核心洞察",5.5,1.68,1.5,0.32,{fontSize:11,color:"2683B8",bold:true});
  addText(s,"售点分布集中于北部县市，南部呈现少数高占比节点；部分县市数据完整度不足，不宜直接进行横向比较。",5.5,2.08,6.5,0.82,{fontSize:18,color:C.ink,bold:true,breakLine:true});
  const bars=[0.93,0.78,0.64,0.48,0.35];
  ["海口","澄迈","三亚","儋州","琼海"].forEach((n,i)=>{
    addText(s,n,5.55,3.25+i*0.43,0.7,0.25,{fontSize:8.5,color:C.gray});
    s.addShape(pptx.ShapeType.roundRect,{x:6.35,y:3.28+i*0.43,w:4.65*bars[i],h:0.18,rectRadius:0.08,fill:{color:i<2?C.blue:C.violet,transparency:10},line:{color:i<2?C.blue:C.violet,transparency:100}});
  });
  addText(s,"证据",5.5,5.67,0.7,0.25,{fontSize:9,color:C.gray,bold:true});
  addText(s,"县市分布表 · 有效样本数 · 字段覆盖率 · 门店下钻键",6.15,5.62,5.8,0.35,{fontSize:10.5,color:C.ink});
  s.addShape(pptx.ShapeType.roundRect,{x:0.75,y:5.72,w:4.1,h:0.58,rectRadius:0.08,fill:{color:"FFF3E5"},line:{color:"F4C789"}});
  addText(s,"边界：不输出拜访路线或渠道决策",0.95,5.84,3.7,0.32,{fontSize:10.5,color:"8A541E",bold:true,align:"center"});
  s.addNotes("这是一个示意案例。关键不在于图，而在于输出包含结论、证据和限制。地图只用于表达空间分布洞察，不承担路线和排程功能。");
}

// 8. User experience
{
  const s = darkBase("先广后深：像分析师一样连续探索","EXPERIENCE",8);
  const steps=[
    ["01","提出问题","用业务语言描述想了解什么",C.blue],
    ["02","确认理解","查看对象、范围、指标与规则",C.blue2],
    ["03","获得洞察","先读结论，再看证据和质量",C.violet],
    ["04","继续下钻","从总体进入区域、品牌和门店",C.pink],
    ["05","交付复用","导出或交给下游系统继续使用",C.amber]
  ];
  steps.forEach((st,i)=>{
    const x=0.55+i*2.55;
    s.addShape(pptx.ShapeType.ellipse,{x:x+0.72,y:1.65,w:0.8,h:0.8,fill:{color:st[3],transparency:18},line:{color:st[3],width:1.3}});
    addText(s,st[0],x+0.72,1.86,0.8,0.3,{fontSize:13,color:C.white,bold:true,align:"center"});
    if(i<4)s.addShape(pptx.ShapeType.chevron,{x:x+1.65,y:1.86,w:0.6,h:0.34,fill:{color:C.line},line:{color:C.line}});
    addText(s,st[1],x+0.25,2.72,1.75,0.35,{fontSize:13,color:C.white,bold:true,align:"center"});
    addText(s,st[2],x,3.25,2.25,1.0,{fontSize:10.2,color:C.muted,align:"center",valign:"top",breakLine:true});
  });
  s.addShape(pptx.ShapeType.roundRect,{x:1.0,y:5.15,w:11.3,h:1.0,rectRadius:0.08,fill:{color:C.card},line:{color:C.line}});
  addText(s,"用户始终知道：当前分析范围是什么、使用了哪些口径、结论有多可靠。",1.35,5.42,10.6,0.42,{fontSize:16,color:C.text,bold:true,align:"center"});
  s.addNotes("交互原则是先广后深。连续追问的价值不是聊天本身，而是保持分析上下文，让用户从总体结构逐步进入证据明细，同时始终知道当前范围和口径。");
}

// 9. Component relation
{
  const s = lightBase("独立组件，可被人和系统共同使用","COMPOSABLE BY DESIGN",9);
  card(s,0.7,1.55,3.0,3.6,"上游输入","售点宽表\n数据仓库或数据湖\n业务语义与指标口径\n世界模型中的对象状态",C.blue,false);
  s.addShape(pptx.ShapeType.chevron,{x:3.9,y:2.95,w:0.75,h:0.7,fill:{color:C.blue,transparency:20},line:{color:C.blue,transparency:100}});
  s.addShape(pptx.ShapeType.roundRect,{x:4.85,y:1.7,w:3.6,h:3.3,rectRadius:0.1,fill:{color:C.navy2},line:{color:C.violet,width:1.5}});
  addText(s,"SH STORE\nINSIGHT",5.3,2.32,2.7,0.95,{fontSize:23,color:C.white,bold:true,align:"center",breakLine:true});
  addText(s,"观察 · 分析 · 解释",5.4,3.55,2.5,0.35,{fontSize:11.5,color:C.blue,align:"center",bold:true});
  addText(s,"只输出 Insight",5.4,4.1,2.5,0.3,{fontSize:10,color:C.muted,align:"center"});
  s.addShape(pptx.ShapeType.chevron,{x:8.65,y:2.95,w:0.75,h:0.7,fill:{color:C.pink,transparency:20},line:{color:C.pink,transparency:100}});
  card(s,9.6,1.55,3.0,3.6,"下游使用","业务人员阅读\n策略组件引用\n排程组件使用\n其他智能体调用",C.pink,false);
  addText(s,"与世界模型的关系",0.72,5.75,2.1,0.3,{fontSize:11,color:"2683B8",bold:true});
  addText(s,"世界模型提供对象与状态；Insight 组件负责从中提炼值得关注的结构、差异与异常。",2.65,5.6,9.6,0.55,{fontSize:16,color:C.ink,bold:true,align:"center"});
  s.addNotes("SH Store Insight 可以独立读取售点数据，也可以读取世界模型提供的对象状态。它不管理世界模型，不编排下游动作。它只把观察结果变成标准化洞察包，供人或其他组件使用。");
}

// 10. Roadmap/close
{
  const s = darkBase("从可信查询开始，逐步形成洞察组件","ROADMAP",10);
  const phases=[
    ["01","可信查询","语义解释\n查询可追溯\n质量同步输出",C.blue],
    ["02","洞察综合","事实与结构\n比较与异常\n限制与后续分析",C.violet],
    ["03","交互式洞察","连续探索\n汇总下钻\n图表与区域地图",C.pink],
    ["04","组件化交付","标准 Insight Schema\nAPI / MCP\n版本与权限",C.amber]
  ];
  phases.forEach((p,i)=>{
    const x=0.75+i*3.12;
    s.addShape(pptx.ShapeType.roundRect,{x,y:1.6,w:2.75,h:3.3,rectRadius:0.08,fill:{color:C.card},line:{color:p[3],width:1.2}});
    addText(s,p[0],x+0.22,1.85,0.55,0.38,{fontSize:18,color:p[3],bold:true});
    addText(s,p[1],x+0.85,1.88,1.55,0.35,{fontSize:14,color:C.white,bold:true});
    addText(s,p[2],x+0.32,2.75,2.1,1.35,{fontSize:11,color:C.text,align:"center",valign:"mid",breakLine:true});
  });
  addText(s,"北极星指标",0.78,5.42,1.5,0.32,{fontSize:11,color:C.blue,bold:true});
  addText(s,"被用户确认有用，并能够追溯到数据证据的洞察数量",2.15,5.25,10.1,0.6,{fontSize:21,color:C.white,bold:true,align:"center"});
  addText(s,"一句问题进来，一份可信洞察出去。",2.5,6.42,8.35,0.42,{fontSize:17,color:C.blue,align:"center",bold:true});
  s.addNotes("收尾强调路线图不是堆功能，而是逐步提高洞察可信度和组件可用性。北极星指标不是查询次数，也不是图表数量，而是被用户确认有用且可追溯的洞察数量。结尾回到双棱镜：一句问题进来，一份可信洞察出去。");
}

pptx.writeFile({ fileName: OUT });
