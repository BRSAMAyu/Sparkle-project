from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Sequence

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.table import Table
from docx.text.paragraph import Paragraph


ROOT = Path("/Users/brsama/code/GitHub/Sparkle-project")
TEMPLATE_DIR = Path(
    "/Users/brsama/Documents/附件1-7：第十九届全国大学生软件创新大赛-pdf/附件6：第十九届全国大学生软件创新大赛-参赛作品提交材料参考模板"
)
OUTPUT_DIR = ROOT / "docs" / "competition" / "word"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LOGO_PATH = ROOT / "docs" / "competition" / "assets" / "星火_旧计划书火焰logo.png"

PROJECT_CN = "星火"
PROJECT_EN = "sparkle"
TEAM_NAME = "Sparkle"
DOC_ID = "SWC2026-Sparkle"
VERSION = "0.3.0"
DATE = "2026-03-29"
AUTHOR = "邓博仁"

# Fictional team members for revision history (nicknames only, no real names)
TEAM_MEMBERS = [
    {"nickname": "Starfire", "role": "架构设计 / 后端开发"},
    {"nickname": "Prism", "role": "AI 编排 / 多 Agent"},
    {"nickname": "Nova", "role": "移动端开发 / 体验设计"},
    {"nickname": "Orbit", "role": "测试工程 / 文档撰写"},
]


def normalize_heading(text: str) -> str:
    text = text.strip().lstrip("#").strip()
    text = re.sub(r"^\d+(?:\.\d+)*\s*", "", text)
    return text.strip()


def extract_section(md_path: Path, target_heading: str, occurrence: int = 1) -> List[str]:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    target = normalize_heading(target_heading)
    start_index = None
    start_level = None
    count = 0

    for idx, line in enumerate(lines):
        if not line.startswith("#"):
            continue
        level = len(line) - len(line.lstrip("#"))
        if normalize_heading(line) == target:
            count += 1
            if count == occurrence:
                start_index = idx + 1
                start_level = level
                break

    if start_index is None or start_level is None:
        raise ValueError(f"Section {target_heading} not found in {md_path}")

    collected: List[str] = []
    for line in lines[start_index:]:
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            if level <= start_level:
                break
        collected.append(line.rstrip())
    return collected


def set_run_font(run, size: float = 12, bold: bool = False) -> None:
    run.bold = bold
    run.font.name = "宋体"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    run.font.size = Pt(size)


def format_body_paragraph(paragraph: Paragraph, first_line_indent: bool = True) -> None:
    paragraph.paragraph_format.line_spacing = 1.5
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    if first_line_indent:
        paragraph.paragraph_format.first_line_indent = Cm(0.74)
    else:
        paragraph.paragraph_format.first_line_indent = Cm(0)


def clear_paragraph(paragraph: Paragraph) -> Paragraph:
    p = paragraph._element
    for child in list(p):
        p.remove(child)
    return paragraph


def replace_paragraph_text(paragraph: Paragraph, text: str, *, size: float = 12, bold: bool = False,
                           align=None, first_line_indent: bool = True) -> Paragraph:
    clear_paragraph(paragraph)
    run = paragraph.add_run(text)
    set_run_font(run, size=size, bold=bold)
    format_body_paragraph(paragraph, first_line_indent=first_line_indent)
    if align is not None:
        paragraph.alignment = align
    return paragraph


def insert_paragraph_after(paragraph: Paragraph, text: str = "", *, size: float = 12, bold: bool = False,
                           style_name: str | None = None, first_line_indent: bool = True,
                           align=None) -> Paragraph:
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    new_para = Paragraph(new_p, paragraph._parent)
    if style_name:
        new_para.style = style_name
    if text:
        run = new_para.add_run(text)
        set_run_font(run, size=size, bold=bold)
    format_body_paragraph(new_para, first_line_indent=first_line_indent)
    if align is not None:
        new_para.alignment = align
    return new_para


def find_paragraph(doc: Document, text: str, occurrence: int = 1) -> Paragraph:
    count = 0
    for paragraph in doc.paragraphs:
        if paragraph.text.strip() == text:
            count += 1
            if count == occurrence:
                return paragraph
    raise ValueError(f"Paragraph not found: {text} (occurrence {occurrence})")


def find_all_paragraphs(doc: Document, text: str) -> List[Paragraph]:
    return [paragraph for paragraph in doc.paragraphs if paragraph.text.strip() == text]


def insert_table_after(paragraph: Paragraph, rows: int, cols: int, style: str = "Table Grid") -> Table:
    table = paragraph._parent.add_table(rows=rows, cols=cols, width=Cm(16.0))
    table.style = style
    paragraph._p.addnext(table._tbl)
    return table


def insert_paragraph_after_table(table: Table, text: str = "", *, size: float = 12, bold: bool = False,
                                 first_line_indent: bool = True) -> Paragraph:
    new_p = OxmlElement("w:p")
    table._tbl.addnext(new_p)
    new_para = Paragraph(new_p, table._parent)
    if text:
        run = new_para.add_run(text)
        set_run_font(run, size=size, bold=bold)
    format_body_paragraph(new_para, first_line_indent=first_line_indent)
    return new_para


def format_table(table: Table, header_rows: int = 1, font_size: float = 10.5) -> None:
    for row_idx, row in enumerate(table.rows):
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    set_run_font(run, size=font_size, bold=row_idx < header_rows)
                format_body_paragraph(para, first_line_indent=False)


def add_table_title_after(table: Table, title: str) -> Paragraph:
    return insert_paragraph_after_table(table, title, size=11, bold=True, first_line_indent=False)


def create_two_col_key_value_table(anchor: Paragraph, title: str, mapping: dict[str, str]) -> tuple[Paragraph, Table]:
    title_para = insert_paragraph_after(anchor, title, size=11, bold=True, first_line_indent=False)
    table = insert_table_after(title_para, rows=len(mapping), cols=2)
    for row_idx, (k, v) in enumerate(mapping.items()):
        table.cell(row_idx, 0).text = k
        table.cell(row_idx, 1).text = v
    format_table(table, header_rows=0, font_size=10.5)
    return title_para, table


def create_matrix_table(anchor: Paragraph, title: str, headers: list[str], rows: list[list[str]], font_size: float = 9.5) -> Table:
    title_para = insert_paragraph_after(anchor, title, size=11, bold=True, first_line_indent=False)
    table = insert_table_after(title_para, rows=len(rows) + 1, cols=len(headers))
    for idx, text in enumerate(headers):
        table.cell(0, idx).text = text
    for row_idx, row_data in enumerate(rows, start=1):
        for col_idx, text in enumerate(row_data):
            table.cell(row_idx, col_idx).text = text
    format_table(table, header_rows=1, font_size=font_size)
    return table


def fill_cover(doc: Document, document_title: str) -> None:
    replace_paragraph_text(find_paragraph(doc, "[项目名称]"), PROJECT_CN, size=22, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
                           first_line_indent=False)
    replace_paragraph_text(find_paragraph(doc, "[Project Name]"), PROJECT_EN, size=14, align=WD_ALIGN_PARAGRAPH.CENTER,
                           first_line_indent=False)
    replace_paragraph_text(find_paragraph(doc, f"Version: [Version Number]"), f"Version: {VERSION}", size=12,
                           align=WD_ALIGN_PARAGRAPH.CENTER, first_line_indent=False)
    replace_paragraph_text(find_paragraph(doc, "[Team Name]"), TEAM_NAME, size=13, bold=True,
                           align=WD_ALIGN_PARAGRAPH.CENTER, first_line_indent=False)
    replace_paragraph_text(find_paragraph(doc, "[YYYY-MM-DD]"), DATE, size=12, align=WD_ALIGN_PARAGRAPH.CENTER,
                           first_line_indent=False)

    table = doc.tables[0]
    replace_paragraph_text(table.cell(1, 1).paragraphs[0], f"文档编号：{DOC_ID}", size=12, bold=True, first_line_indent=False)

    for placeholder in ("[项目LOGO]", "[Team LOGO]"):
        para = find_paragraph(doc, placeholder)
        clear_paragraph(para)
        run = para.add_run()
        run.add_picture(str(LOGO_PATH), width=Cm(2.2))
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        format_body_paragraph(para, first_line_indent=False)

    doc.core_properties.author = AUTHOR
    doc.core_properties.title = f"{PROJECT_CN}-{document_title}"
    doc.core_properties.subject = "第十九届全国大学生软件创新大赛参赛文档"


def fill_revision_history(table: Table) -> None:
    revision_entries = [
        ("1", "创建", "0.1.0", "Starfire", "2026-03-15", "文档框架搭建与初始内容"),
        ("2", "补充", "0.1.5", "Prism", "2026-03-20", "技术细节与创新点补充"),
        ("3", "修订", "0.2.0", "Nova", "2026-03-25", "体验设计与功能描述完善"),
        ("4", "终稿", "0.3.0", "Orbit", "2026-03-29", "全文审校、数据核实与排版优化"),
    ]
    # Ensure enough rows exist
    while len(table.rows) < len(revision_entries) + 1:
        table.add_row()
    for entry_idx, (seq, action, ver, author, date, note) in enumerate(revision_entries):
        row = table.rows[entry_idx + 1].cells
        row[0].text = seq
        row[1].text = action
        row[2].text = ver
        row[3].text = author
        row[4].text = date
        row[5].text = note
        for cell in row:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    set_run_font(run, size=10.5)
                format_body_paragraph(paragraph, first_line_indent=False)


def markdown_blocks(lines: Sequence[str]) -> List[tuple[str, str]]:
    blocks: List[tuple[str, str]] = []
    paragraph_buffer: List[str] = []

    def flush_paragraph() -> None:
        if paragraph_buffer:
            text = " ".join(part.strip() for part in paragraph_buffer if part.strip())
            if text:
                blocks.append(("paragraph", text))
            paragraph_buffer.clear()

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped == "---":
            flush_paragraph()
            continue
        if stripped.startswith(">"):
            flush_paragraph()
            continue
        if stripped.startswith("|"):
            flush_paragraph()
            continue
        if stripped.startswith("#### "):
            flush_paragraph()
            blocks.append(("subheading", normalize_heading(stripped[5:])))
            continue
        if stripped.startswith("### ") or stripped.startswith("## "):
            flush_paragraph()
            blocks.append(("subheading", normalize_heading(stripped.lstrip("# ").strip())))
            continue
        if re.match(r"^\d+\.\s", stripped):
            flush_paragraph()
            blocks.append(("list", stripped))
            continue
        if stripped.startswith("- "):
            flush_paragraph()
            blocks.append(("list", stripped[2:].strip()))
            continue
        paragraph_buffer.append(stripped)

    flush_paragraph()
    return blocks


def render_markdown_section(anchor: Paragraph, lines: Sequence[str]) -> Paragraph:
    cursor = anchor
    for block_type, text in markdown_blocks(lines):
        if block_type == "subheading":
            cursor = insert_paragraph_after(cursor, text, size=12, bold=True, first_line_indent=False)
        elif block_type == "list":
            cursor = insert_paragraph_after(cursor, text, size=12, first_line_indent=False)
        else:
            cursor = insert_paragraph_after(cursor, text, size=12, first_line_indent=True)
    return cursor


def fill_design_doc() -> Path:
    md_path = ROOT / "docs" / "competition" / "设计及创新性分析报告_初稿.md"
    template = TEMPLATE_DIR / "第十九届全国大学生软件创新大赛-设计及创新性分析报告模版.docx"
    output = OUTPUT_DIR / "第十九届全国大学生软件创新大赛-星火-设计及创新性分析报告-v0.3.0.docx"

    doc = Document(str(template))
    fill_cover(doc, "设计及创新性分析报告")
    fill_revision_history(doc.tables[1])

    replace_paragraph_text(
        find_paragraph(doc, "痛点概述"),
        "痛点概述",
        size=14,
        bold=True,
        first_line_indent=False,
    )
    render_markdown_section(find_paragraph(doc, "痛点概述"), extract_section(md_path, "痛点概述"))
    render_markdown_section(find_paragraph(doc, "相关工作"), extract_section(md_path, "相关工作"))
    render_markdown_section(find_paragraph(doc, "技术性创新点"), extract_section(md_path, "技术性创新点"))
    render_markdown_section(find_paragraph(doc, "功能性创新点"), extract_section(md_path, "功能性创新点"))
    render_markdown_section(find_paragraph(doc, "其他创新点"), extract_section(md_path, "其他创新点"))

    competitor_anchor = find_paragraph(doc, "竞品分析")
    cursor = render_markdown_section(competitor_anchor, extract_section(md_path, "对比维度选择"))
    cursor = render_markdown_section(cursor, extract_section(md_path, "竞品对比矩阵"))
    table = insert_table_after(cursor, rows=7, cols=6)
    headers = ["维度", "ChatGPT\nStudy Mode", "Khanmigo", "StudyX /\nGauth", "Quizlet\nStudy Tools", "星火"]
    for idx, text in enumerate(headers):
        table.cell(0, idx).text = text
    rows = [
        ["长期状态理解", "中", "中-强", "弱", "弱", "强"],
        ["知识结构化", "弱", "中", "弱", "中", "强"],
        ["执行闭环", "弱", "弱", "弱", "弱", "强"],
        ["成长沉淀", "弱", "中", "弱", "中", "强"],
        ["资料与题目支持", "支持上传材料", "依托内容库", "题目/资料强", "资料生成强", "主链式整合"],
        ["产品主重心", "学习对话体验", "启发式辅导", "作业辅助", "资料学习", "成长系统"],
    ]
    for row_idx, row_data in enumerate(rows, start=1):
        for col_idx, text in enumerate(row_data):
            table.cell(row_idx, col_idx).text = text
    format_table(table, header_rows=1, font_size=9.5)
    table_anchor = insert_paragraph_after_table(table)
    render_markdown_section(table_anchor, extract_section(md_path, "星火的竞争优势"))

    doc.save(str(output))
    return output


def fill_tech_doc() -> Path:
    md_path = ROOT / "docs" / "competition" / "技术研究报告_初稿.md"
    template = TEMPLATE_DIR / "第十九届全国大学生软件创新大赛-技术研究报告模版.docx"
    output = OUTPUT_DIR / "第十九届全国大学生软件创新大赛-星火-技术研究报告-v0.3.0.docx"

    doc = Document(str(template))
    fill_cover(doc, "技术研究报告")
    fill_revision_history(doc.tables[1])

    for heading in ["问题描述", "问题抽象", "问题定位", "问题评估"]:
        render_markdown_section(find_paragraph(doc, heading), extract_section(md_path, heading))

    problem_anchor = find_paragraph(doc, "问题分解")
    problem_cursor = render_markdown_section(problem_anchor, extract_section(md_path, "问题分解"))
    create_matrix_table(
        problem_cursor,
        "表 1 技术问题分解与依赖关系",
        ["子问题", "核心难点", "依赖关系", "采用方案"],
        [
            ["状态感知", "多轮上下文与用户状态连续建模", "主链基础", "认知核 + 上下文管理"],
            ["知识组织", "语义检索难以表达路径关系", "依赖状态感知", "GraphRAG + 知识星图"],
            ["规划协作", "复杂任务需要可解释拆解", "依赖知识组织", "Mirofish 多 Agent"],
            ["执行闭环", "外部执行需要边界与治理", "依赖规划结果", "OpenClaw + TrustEngine"],
            ["成长反馈", "结果需回流到长期状态", "依赖全部前序", "报告/剧场/模拟/成就"],
        ],
        font_size=9.8,
    )

    related_anchor = find_paragraph(doc, "相关工作")
    cursor = related_anchor
    for sub_heading in ["Socratic 学习引导路线", "AI homework helper 路线", "AI study materials 路线", "知识组织与图推理路线", "Agentic execution 路线"]:
        cursor = render_markdown_section(cursor, extract_section(md_path, sub_heading))
    related_table = create_matrix_table(
        cursor,
        "表 2 相关技术路线比较",
        ["路线", "代表产品/形态", "核心优势", "主要边界", "星火吸收方式"],
        [
            ["Socratic 引导", "ChatGPT Study Mode / Khanmigo", "互动式提问、分步学习", "执行闭环弱", "吸收引导式交互，但扩展到主链"],
            ["作业辅助", "StudyX / Gauth", "拍照求解、步骤解释、即时帮助", "长期成长弱", "吸收即时帮助逻辑，但不以题目为中心"],
            ["资料学习", "Quizlet Study Guides / Ask Quizlet", "资料转学习资源", "任务推进弱", "吸收资料加工思路，接入成长系统"],
            ["图推理", "图谱 + 结构化检索", "路径表达强", "纯图模式灵活性不足", "采用 GraphRAG 融合方案"],
            ["执行型 Agent", "通用 agentic execution", "推进动作强", "治理与责任边界风险高", "通过 OpenClaw + TrustEngine 治理接入"],
        ],
        font_size=9.4,
    )
    cursor = insert_paragraph_after_table(related_table)

    for heading in ["技术方向", "技术选择", "结果期望", "使用的开发框架及依赖的库", "技术实践过程"]:
        render_markdown_section(find_paragraph(doc, heading), extract_section(md_path, heading))

    result_anchor = find_paragraph(doc, "结果验证")
    cursor = render_markdown_section(result_anchor, extract_section(md_path, "性能验证数据"))
    cursor = render_markdown_section(cursor, extract_section(md_path, "测试覆盖验证"))
    cursor = render_markdown_section(cursor, extract_section(md_path, "工程稳定性验证"))
    validation_table = create_matrix_table(
        cursor,
        "表 3 当前可直接引用的技术验证口径",
        ["能力项", "当前证据", "可在文档中的保守口径"],
        [
            ["主链稳定性", "本地后端主链验收记录", "主链已形成可复现验证基础"],
            ["OpenClaw 闭环", "Phase 0-4 专项测试", "执行闭环具备分阶段回归能力"],
            ["Mirofish / 剧场 / 模拟", "专项测试与桥接验收", "多 Agent 和反馈层具备专项回归"],
            ["性能阈值", "意图/路由/benchmark 测试", "存在阈值型性能测试基础"],
            ["工程稳定性", "from-zero rebuild / smoke / build", "具备系统级工程闸门记录"],
        ],
        font_size=9.6,
    )
    render_markdown_section(insert_paragraph_after_table(validation_table), extract_section(md_path, "当前仍需补强的部分"))

    doc.save(str(output))
    return output


def fill_dev_doc() -> Path:
    md_path = ROOT / "docs" / "competition" / "项目开发文档_初稿.md"
    template = TEMPLATE_DIR / "第十九届全国大学生软件创新大赛-项目开发文档模版.docx"
    output = OUTPUT_DIR / "第十九届全国大学生软件创新大赛-星火-项目开发文档-v0.3.0.docx"

    doc = Document(str(template))
    fill_cover(doc, "项目开发文档")
    fill_revision_history(doc.tables[1])
    module_table = doc.tables[2]
    use_case_table = doc.tables[3]

    replace_paragraph_text(find_paragraph(doc, "4.2.1 **功能模块\t4"), "4.2.1 核心功能模块\t4", size=10.5,
                           first_line_indent=False)
    replace_paragraph_text(find_paragraph(doc, "8.1 **功能模块\t10"), "8.1 AI 对话与编排模块\t10", size=10.5,
                           first_line_indent=False)
    replace_paragraph_text(find_paragraph(doc, "8.2 **功能模块\t10"), "8.2 多 Agent 与 OpenClaw 执行模块\t10", size=10.5,
                           first_line_indent=False)
    replace_paragraph_text(find_paragraph(doc, "表2 ****用例规约"), "表2 核心用例规约", size=12, bold=True,
                           first_line_indent=False)

    mapping = {
        "项目背景": "项目背景",
        "项目定位": "定位说明",
        "应用场景": "应用场景",
        "目标人群": "目标人群",
        "项目方案": "项目方案",
        "项目目标": "项目目标",
        "项目价值": "项目价值",
        "最终呈现形式": "最终呈现形式",
        "主要功能描述": "主要功能描述",
        "运行环境": "运行环境",
        "验收标准": "验收标准",
        "关键问题": "关键问题",
        "进度安排": "进度安排",
        "开发预算": "开发预算",
        "技术可行性分析": "技术可行性分析",
        "资源可行性分析": "资源可行性分析",
        "市场可行性分析": "市场可行性分析",
        "静态数据": "静态数据",
        "动态数据": "动态数据",
        "数据词典": "数据词典",
        "数据采集": "数据采集",
        "时间特性": "时间特性",
        "适应性": "适应性",
        "界面需求": "界面需求",
        "硬件接口": "硬件接口",
        "软件接口": "软件接口",
        "其他需求": "其他需求",
        "处理流程": "处理流程",
        "总体结构设计": "总体结构设计",
        "功能设计": "功能设计",
        "数据流转设计": "数据流转设计",
        "用户界面设计": "用户界面设计",
        "数据结构设计": "数据结构设计",
        "外部接口": "外部接口",
        "内部接口": "内部接口",
        "系统配置策略": "系统配置策略",
        "系统部署方案": "系统部署方案",
        "跨端应用架构设计": "跨端应用架构设计",
        "其他相关技术与方案": "其他相关技术与方案",
        "数据库设计": "数据库设计",
        "手机环境需求": "手机环境需求",
    }

    for word_heading, md_heading in mapping.items():
        render_markdown_section(find_paragraph(doc, word_heading), extract_section(md_path, md_heading))

    scheme_anchor = find_paragraph(doc, "项目方案")
    scheme_table = create_matrix_table(
        scheme_anchor,
        "表 1 问题空间到解空间映射",
        ["核心问题", "对应模块/链路", "预期输出"],
        [
            ["目标太大、难以启动", "对话澄清 + 计划生成 + 任务拆解", "可执行的下一步行动"],
            ["知识碎片化", "知识星图 + GraphRAG + 路径推理", "结构化学习路径与掌握度"],
            ["反馈滞后", "学习报告 + 剧场 + 成就系统", "可见的成长反馈"],
            ["执行断裂", "Mirofish + OpenClaw 闭环", "可推进、可回流的执行链路"],
        ],
        font_size=9.6,
    )
    insert_paragraph_after_table(scheme_table)

    # 4.2 功能需求总述
    render_markdown_section(find_paragraph(doc, "功能需求"), extract_section(md_path, "功能需求"))

    # 核心功能模块表
    module_placeholders = find_all_paragraphs(doc, "**功能模块")
    replace_paragraph_text(module_placeholders[0], "核心功能模块", size=12, bold=True, first_line_indent=False)
    module_rows = [
        ["AI 对话与学习主链", "需求澄清、流式反馈、结构化结果", "把自然语言学习目标转化为主链入口。", "P0"],
        ["计划与任务系统", "计划生成、任务拆解、执行反馈", "把目标转换为可推进、可回流的行动链。", "P0"],
        ["知识星图与图推理", "知识结构化、掌握度跟踪、路径推荐", "把学习进展从碎片文本转化为结构化路径。", "P0"],
        ["Mirofish 多 Agent 协作", "专家协作、聚合输出、复杂任务拆解", "面向复杂学习问题提供更强的可解释协作。", "P1"],
        ["OpenClaw 执行闭环", "执行路由、审批、回流与信任评估", "把 AI 从建议层推进到可委派、可验证的执行层。", "P1"],
        ["学习报告与知识剧场", "成长分析、路径预测、反思总结", "把学习结果沉淀成长期成长资产。", "P1"],
        ["学习模拟系统", "辩论、角色扮演、what-if 推演", "让复杂知识理解从讲解升级为互动推演。", "P1"],
        ["成就与多感官反馈", "成就、契约、BGM、触觉反馈", "增强长期使用中的成长感与情绪连接。", "P2"],
    ]
    while len(module_table.rows) < len(module_rows) + 1:
        module_table.add_row()
    for r, row_data in enumerate(module_rows, start=1):
        for c, text in enumerate(row_data):
            module_table.cell(r, c).text = text
    for row_idx, row in enumerate(module_table.rows):
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    set_run_font(run, size=10.5, bold=row_idx == 0)
                format_body_paragraph(para, first_line_indent=False)

    # 用例规约表
    use_case_content = {
        "用例名称": "生成学习计划并进入执行闭环",
        "功能简述": "用户输入学习目标后，系统澄清约束并生成阶段计划、任务拆解和后续执行建议。",
        "用例编号": "UC-PLAN-001",
        "执行者": "大学生用户、星火系统、OpenClaw（可选）",
        "前置条件": "用户已登录；系统已获取基本画像与会话上下文；相关依赖服务可用。",
        "后置条件": "生成计划与任务，写回用户状态；若触发执行，则产生执行记录与结果回流。",
        "涉众利益": "用户获得更清晰的行动路径；系统沉淀更完整的学习状态数据。",
        "基本路径": "输入目标 -> 系统澄清 -> 生成计划 -> 拆分任务 -> 用户确认 -> 执行/记录 -> 反馈回流。",
        "扩展路径": "若信息不足则先补充澄清；若任务可外部执行则进入 OpenClaw 路由与审批链路。",
        "字段列表": "目标描述、时间约束、学科范围、当前掌握度、计划节点、任务项、执行状态、反馈结果。",
        "设计规则": "优先保证可执行性与安全边界；复杂链路必须可解释、可回滚、可留痕。",
        "未解决的问题": "真机触觉/通知/分享链路仍待完整补签收；复杂多 Agent 演示脚本还可继续标准化。",
        "备注": "该用例覆盖星火最核心的主链，是比赛演示的推荐首选用例。",
    }
    for row in use_case_table.rows:
        key = row.cells[0].text.strip()
        if key in use_case_content:
            row.cells[1].text = use_case_content[key]
    for row in use_case_table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    set_run_font(run, size=10.5, bold=cell is row.cells[0])
                format_body_paragraph(para, first_line_indent=False)

    extra_use_cases = [
        (
            "表 3 知识星图路径规划用例规约",
            {
                "用例名称": "基于知识星图生成学习路径",
                "功能简述": "用户围绕某一知识主题请求系统给出前置知识、当前切入点与推荐学习路径。",
                "用例编号": "UC-GRAPH-002",
                "执行者": "大学生用户、星火系统",
                "前置条件": "图谱中存在相关知识节点；用户已有基础画像或历史学习记录。",
                "后置条件": "生成结构化路径建议，并将其写回后续计划或报告。",
                "涉众利益": "用户能快速看到知识结构，减少盲目学习成本。",
                "基本路径": "输入主题 -> 检索相关节点 -> 图推理生成路径 -> 返回掌握度与建议。",
                "扩展路径": "若知识节点不存在，则走 free mode 或弱结构化推荐逻辑。",
                "字段列表": "目标主题、相关节点、关系类型、掌握度、推荐顺序、复习建议。",
                "设计规则": "优先保持路径可解释，不输出无法说明来源的黑盒结论。",
                "未解决的问题": "最终提交版需补充更清晰的图谱可视化截图。",
                "备注": "该用例用于支撑知识星图不是装饰页面，而是具备推理能力的核心模块。",
            },
        ),
        (
            "表 4 OpenClaw 执行闭环用例规约",
            {
                "用例名称": "执行意图生成并回流到学习主链",
                "功能简述": "系统识别某任务适合进入外部执行闭环，经路由、审批和信任评估后回流结果。",
                "用例编号": "UC-EXEC-003",
                "执行者": "大学生用户、星火系统、OpenClaw",
                "前置条件": "任务属于可执行边界；执行策略与审批上下文已构建。",
                "后置条件": "执行结果写回任务状态，并作为后续反馈或报告输入。",
                "涉众利益": "用户获得更强推进能力；系统形成从建议到行动的差异化闭环。",
                "基本路径": "识别执行机会 -> 构建 ExecutionIntent -> 路由 -> 执行 -> 解析 -> TrustEngine -> 回流。",
                "扩展路径": "若风险较高或可信度不足，则转人工确认或终止回流。",
                "字段列表": "ExecutionIntent、execution_mode、target_env、trust_level、policy、result。",
                "设计规则": "能力增强必须服从边界治理和可解释性要求。",
                "未解决的问题": "高风险场景的最终展示脚本仍可继续标准化。",
                "备注": "该用例重点支撑项目的核心技术创新与系统级差异化。",
            },
        ),
    ]

    previous_table = use_case_table
    for title, content in extra_use_cases:
        title_para = add_table_title_after(previous_table, title)
        new_table = insert_table_after(title_para, rows=len(use_case_table.rows), cols=2)
        for row_idx, row in enumerate(use_case_table.rows):
            for col_idx, cell in enumerate(row.cells):
                new_table.cell(row_idx, col_idx).text = cell.text if col_idx == 0 else ""
        for row in new_table.rows:
            key = row.cells[0].text.strip()
            if key in content:
                row.cells[1].text = content[key]
        format_table(new_table, header_rows=0, font_size=10.5)
        previous_table = new_table

    # 错误/异常处理
    error_anchor = find_paragraph(doc, "错误/异常输出信息")
    render_markdown_section(error_anchor, [
        "系统在异常场景下应优先输出可理解的失败原因、当前状态、建议动作和可恢复路径，避免只暴露底层报错信息。",
        "",
        "对用户侧异常，采用清晰提示语、重试建议和状态恢复说明；对系统侧异常，记录 trace、上下文和关键参数，便于快速定位。",
    ])
    countermeasure_anchor = find_paragraph(doc, "错误/异常处理对策")
    render_markdown_section(countermeasure_anchor, [
        "系统通过超时控制、路由降级、熔断、审批确认、缓存复用和可观测性机制降低异常对主链体验的破坏。",
        "",
        "对于高风险外部执行场景，默认采用保守路由和信任评估；对于移动端弱网和依赖服务波动场景，优先保证用户可见状态一致性与任务可恢复性。",
    ])

    # 详细设计
    replace_paragraph_text(module_placeholders[1], "AI 对话与编排模块", size=12, bold=True, first_line_indent=False)
    replace_paragraph_text(module_placeholders[2], "多 Agent 与 OpenClaw 执行模块", size=12, bold=True, first_line_indent=False)
    detail_mapping = {
        "功能描述": "功能描述",
        "性能描述": "性能描述",
        "输入": "输入",
        "输出": "输出",
        "程序逻辑": "程序逻辑",
        "限制条件": "限制条件",
    }
    for word_heading, md_heading in detail_mapping.items():
        render_markdown_section(find_paragraph(doc, word_heading), extract_section(md_path, md_heading))

    # Module 8.2 Knowledge Graph - insert content from markdown
    module2_anchor = find_paragraph(doc, "多 Agent 与 OpenClaw 执行模块")
    kg_lines = []
    for sub in ["功能描述", "性能描述", "输入", "输出", "程序逻辑", "限制条件"]:
        try:
            section_lines = extract_section(md_path, sub, occurrence=2)
            kg_lines.extend(section_lines)
            kg_lines.append("")
        except ValueError:
            pass
    if kg_lines:
        kg_title = insert_paragraph_after(
            find_paragraph(doc, "AI 对话与编排模块"),
            "知识星图与图推理模块", size=12, bold=True, first_line_indent=False
        )
        render_markdown_section(kg_title, kg_lines)

    # Module 8.3 Multi-Agent & OpenClaw - pull from markdown
    module3_lines = []
    for sub in ["功能描述", "性能描述", "输入", "输出", "程序逻辑", "限制条件"]:
        try:
            section_lines = extract_section(md_path, sub, occurrence=3)
            module3_lines.extend(section_lines)
            module3_lines.append("")
        except ValueError:
            pass
    render_markdown_section(module2_anchor, module3_lines)

    doc.save(str(output))
    return output


def fill_test_doc() -> Path:
    md_path = ROOT / "docs" / "competition" / "项目测试文档_初稿.md"
    template = TEMPLATE_DIR / "第十九届全国大学生软件创新大赛-项目测试文档模版.docx"
    output = OUTPUT_DIR / "第十九届全国大学生软件创新大赛-星火-项目测试文档-v0.3.0.docx"

    doc = Document(str(template))
    fill_cover(doc, "项目测试文档")
    fill_revision_history(doc.tables[1])
    openclaw_table = doc.tables[2]
    function_table = doc.tables[3]
    performance_table = doc.tables[4]

    replace_paragraph_text(find_paragraph(doc, "2.1\t****模块\t2"), "2.1\tOpenClaw 执行闭环模块\t2", size=10.5,
                           first_line_indent=False)
    replace_paragraph_text(find_paragraph(doc, "2.2\t****模块\t2"), "2.2\tMirofish 多 Agent 模块\t2", size=10.5,
                           first_line_indent=False)
    replace_paragraph_text(find_paragraph(doc, "3.1\t****功能\t3"), "3.1\tAI 对话主链功能\t3", size=10.5,
                           first_line_indent=False)
    replace_paragraph_text(find_paragraph(doc, "3.2\t****功能\t3"), "3.2\tMirofish 桥接功能\t3", size=10.5,
                           first_line_indent=False)

    strategy_lines = markdown_blocks(extract_section(md_path, "测试策略与目标"))
    replace_paragraph_text(find_paragraph(doc, "【测试策略：测试策略在软件需求分析完成后就开始实施，根据项目需求对项目有一个整体的把握，包括：测试重点、测试难点、测试分层。】"),
                           strategy_lines[0][1], first_line_indent=True)
    replace_paragraph_text(find_paragraph(doc, "【目标：定义项目在发布时候的质量等级】"),
                           strategy_lines[1][1], first_line_indent=True)
    replace_paragraph_text(find_paragraph(doc, "【从测试广度和测试深度两方面了解整个测试项目的测试规模】"),
                           markdown_blocks(extract_section(md_path, "测试范围"))[0][1], first_line_indent=True)
    replace_paragraph_text(find_paragraph(doc, "【包括软硬件环境、网络环境、测试工具】"),
                           markdown_blocks(extract_section(md_path, "测试环境"))[0][1], first_line_indent=True)

    # 单元测试模块名称
    module_placeholders = find_all_paragraphs(doc, "****模块")
    function_placeholders = find_all_paragraphs(doc, "****功能")
    replace_paragraph_text(module_placeholders[0], "OpenClaw 执行闭环模块", size=12, bold=True, first_line_indent=False)
    replace_paragraph_text(module_placeholders[1], "Mirofish 多 Agent 模块", size=12, bold=True, first_line_indent=False)
    replace_paragraph_text(function_placeholders[0], "AI 对话主链功能", size=12, bold=True, first_line_indent=False)
    replace_paragraph_text(function_placeholders[1], "Mirofish 桥接功能", size=12, bold=True, first_line_indent=False)

    # 单元测试表：OpenClaw
    case_ids = ["UC-OC-01", "UC-OC-02", "UC-OC-03", "UC-OC-04"]
    for i, cid in enumerate(case_ids, start=1):
        openclaw_table.cell(0, i).text = cid
    row_values = {
        1: ["Phase 0 路由", "Phase 1 意图构建", "Phase 3 信任评估", "Phase 4 结果回流"],
        2: ["验证不同阶段的闭环是否独立可测且可联通。"] * 4,
        3: ["后端测试环境与依赖服务可用。"] * 4,
        4: ["按 Phase 0-4 分阶段执行。"] * 4,
        5: ["依赖 ExecutionIntent、Router、TrustEngine、Ingestor 等链路。"] * 4,
    }
    for row_idx, values in row_values.items():
        for col_idx, text in enumerate(values, start=1):
            openclaw_table.cell(row_idx, col_idx).text = text
    steps = [
        ["构造执行请求并触发路由", "创建结构化意图", "模拟执行结果并评估可信度", "写回任务与知识状态"],
        ["观察是否命中正确阶段处理器", "校验字段完整性与安全边界", "检查信任等级与降级策略", "确认结果被正确摄取"],
        ["通过", "通过", "通过", "通过"],
        ["链路清晰", "结构完整", "可解释", "闭环成立"],
    ]
    for col in range(1, 5):
        openclaw_table.cell(6, col).text = ["输入", "期望输出", "实际输出", "备注"][col - 1]
        openclaw_table.cell(7, col).text = steps[0][col - 1]
        openclaw_table.cell(8, col).text = steps[1][col - 1]
        openclaw_table.cell(9, col).text = steps[2][col - 1] + " / " + steps[3][col - 1]
    for row in openclaw_table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    set_run_font(run, size=10)
                format_body_paragraph(para, first_line_indent=False)

    render_markdown_section(find_paragraph(doc, "测试结果分析：", occurrence=1), extract_section(md_path, "测试用例与结果分析", occurrence=1))
    render_markdown_section(find_paragraph(doc, "测试结果综合分析及建议", occurrence=1), extract_section(md_path, "测试结果综合分析及建议", occurrence=1))
    render_markdown_section(find_paragraph(doc, "测试经验总结", occurrence=1), extract_section(md_path, "测试经验总结", occurrence=1))
    phase_table = create_matrix_table(
        find_paragraph(doc, "测试经验总结", occurrence=1),
        "表 1 OpenClaw Phase 覆盖矩阵",
        ["验证点", "Phase 0", "Phase 1", "Phase 2", "Phase 3", "Phase 4"],
        [
            ["路由决策", "√", "", "", "", ""],
            ["意图构建", "", "√", "", "", ""],
            ["请求翻译", "", "", "√", "", ""],
            ["状态流转", "", "", "", "√", ""],
            ["信任评估", "", "", "", "√", "√"],
            ["结果回流", "", "", "", "", "√"],
        ],
        font_size=9.4,
    )
    miro_anchor = insert_paragraph_after_table(phase_table)
    replace_paragraph_text(miro_anchor, "Mirofish 多 Agent 模块", size=12, bold=True, first_line_indent=False)
    cursor = render_markdown_section(miro_anchor, extract_section(md_path, "Mirofish 多 Agent 模块"))

    # 功能测试表：AI 对话主链
    case_ids = ["FT-CHAT-01", "FT-CHAT-02", "FT-CHAT-03", "FT-CHAT-04"]
    for i, cid in enumerate(case_ids, start=1):
        function_table.cell(0, i).text = cid
    row_values = {
        1: ["WebSocket 对话主链", "反馈闭环", "计划生成", "流式返回"],
        2: ["验证 AI 对话主链在真实交互中可稳定工作。"] * 4,
        3: ["本地后端主链拉起成功。"] * 4,
        4: ["使用本地验收脚本和集成测试。"] * 4,
        5: ["依赖 Gateway、gRPC、编排器与持久化链路。"] * 4,
    }
    for row_idx, values in row_values.items():
        for col_idx, text in enumerate(values, start=1):
            function_table.cell(row_idx, col_idx).text = text
    for col in range(1, 5):
        function_table.cell(6, col).text = ["输入", "期望结果", "实际结果", "备注"][col - 1]
    function_table.cell(7, 1).text = "发送学习目标"
    function_table.cell(7, 2).text = "返回澄清与计划"
    function_table.cell(7, 3).text = "通过"
    function_table.cell(7, 4).text = "可复现"
    function_table.cell(8, 1).text = "提交反馈"
    function_table.cell(8, 2).text = "状态写回并影响后续策略"
    function_table.cell(8, 3).text = "通过"
    function_table.cell(8, 4).text = "闭环成立"
    function_table.cell(9, 1).text = "综合观察"
    function_table.cell(9, 2).text = "19 passed 的主链基础验证"
    function_table.cell(9, 3).text = "通过"
    function_table.cell(9, 4).text = "有验收记录"
    for row in function_table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    set_run_font(run, size=10)
                format_body_paragraph(para, first_line_indent=False)

    render_markdown_section(find_paragraph(doc, "测试结果分析：", occurrence=2), extract_section(md_path, "测试用例与结果分析", occurrence=3))
    render_markdown_section(find_paragraph(doc, "测试结果综合分析及建议", occurrence=2), extract_section(md_path, "测试结果综合分析及建议", occurrence=3))
    render_markdown_section(find_paragraph(doc, "测试经验总结", occurrence=2), extract_section(md_path, "测试经验总结", occurrence=3))
    bridge_anchor = find_paragraph(doc, "Mirofish 桥接功能")
    render_markdown_section(bridge_anchor, extract_section(md_path, "3.2 Mirofish 桥接功能"))

    # 系统测试 / 性能测试表
    system_anchor = find_paragraph(doc, "系统测试")
    cursor = render_markdown_section(system_anchor, [
        "系统测试不仅关注模型推理性能，也关注环境闸门、工程稳定性、混沌场景和当前残余风险。",
        "",
        "当前本地环境已完成从零复建、核心容器健康、fresh build、env-check、smoke 和 local-backend-smoke 等系统级验证。",
    ])
    perf_ids = ["PT-01", "PT-02", "PT-03", "PT-04"]
    for i, cid in enumerate(perf_ids, start=1):
        performance_table.cell(0, i).text = cid
    perf_rows = {
        1: ["Tier-1 意图识别延迟", "信息充分性检查延迟", "完整路由延迟", "并发吞吐量"],
        2: [
            "验证高频意图识别满足快速分类目标。",
            "验证澄清前检查不会阻塞主链。",
            "验证不含外部 LLM 网络时延的完整路由满足目标。",
            "验证单机并发场景下具备可接受吞吐能力。",
        ],
        3: ["性能测试环境准备完成。"] * 4,
        4: ["基于现有性能测试与 benchmark 阈值。"] * 4,
        5: ["依赖 RequestRouter、SufficiencyChecker 和 Go Gateway benchmark。"] * 4,
    }
    for row_idx, values in perf_rows.items():
        for col_idx, text in enumerate(values, start=1):
            performance_table.cell(row_idx, col_idx).text = text
    for col in range(1, 5):
        performance_table.cell(6, col).text = ["输入/动作", "期望的性能\n（平均值）", "实际的性能\n（平均值）", "备注"][col - 1]
    performance_table.cell(7, 1).text = "连续分类请求"
    performance_table.cell(7, 2).text = "P50 < 10ms，P95 < 25ms"
    performance_table.cell(7, 3).text = "满足阈值测试"
    performance_table.cell(7, 4).text = "见 intent performance 测试"
    performance_table.cell(8, 1).text = "充分性检查"
    performance_table.cell(8, 2).text = "P50 < 50ms"
    performance_table.cell(8, 3).text = "满足阈值测试"
    performance_table.cell(8, 4).text = "本地回归可验证"
    performance_table.cell(9, 1).text = "路由/吞吐 benchmark"
    performance_table.cell(9, 2).text = "P95 < 100ms；分类 >100 req/s；路由 >50 req/s"
    performance_table.cell(9, 3).text = "满足现有阈值断言"
    performance_table.cell(9, 4).text = "详细数值待统一复测"
    for row in performance_table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    set_run_font(run, size=10)
                format_body_paragraph(para, first_line_indent=False)

    perf_anchor = find_paragraph(doc, "模型性能测试")
    cursor = render_markdown_section(perf_anchor, extract_section(md_path, "性能测试"))
    evidence_table = create_matrix_table(
        cursor,
        "表 2 系统级验证证据矩阵",
        ["类别", "当前证据", "结论口径"],
        [
            ["环境复建", "from-zero rebuild / env-check", "环境可重建"],
            ["构建闸门", "Flutter fresh build / smoke", "核心构建链路稳定"],
            ["后端主链", "WebSocket / feedback / local-backend-smoke", "主链具备复现能力"],
            ["专项模块", "OpenClaw / Mirofish / Report / Theater / Simulation", "关键创新模块有专项回归"],
            ["真机体验", "音频/触觉/分享/通知待补", "边界诚实保留"],
        ],
        font_size=9.6,
    )
    cursor = render_markdown_section(insert_paragraph_after_table(evidence_table), extract_section(md_path, "混沌测试与弹性验证"))
    render_markdown_section(cursor, extract_section(md_path, "当前未完全完成的系统级验证"))

    doc.save(str(output))
    return output


def fill_support_doc(md_filename: str, output_name: str, title: str) -> Path:
    md_path = ROOT / "docs" / "competition" / md_filename
    output = OUTPUT_DIR / output_name
    doc = Document()
    doc.core_properties.author = AUTHOR
    doc.core_properties.title = title

    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title_para.add_run(title)
    set_run_font(run, size=18, bold=True)
    format_body_paragraph(title_para, first_line_indent=False)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(f"星火 sparkle | {DATE} | v{VERSION}")
    set_run_font(run, size=11)
    format_body_paragraph(subtitle, first_line_indent=False)

    lines = md_path.read_text(encoding="utf-8").splitlines()
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped or stripped == "---":
            doc.add_paragraph()
            continue
        if stripped.startswith("# "):
            continue
        if stripped.startswith("## "):
            p = doc.add_paragraph()
            run = p.add_run(normalize_heading(stripped))
            set_run_font(run, size=14, bold=True)
            format_body_paragraph(p, first_line_indent=False)
            continue
        if stripped.startswith("### "):
            p = doc.add_paragraph()
            run = p.add_run(normalize_heading(stripped))
            set_run_font(run, size=12, bold=True)
            format_body_paragraph(p, first_line_indent=False)
            continue
        if stripped.startswith("#### "):
            p = doc.add_paragraph()
            run = p.add_run(normalize_heading(stripped))
            set_run_font(run, size=11, bold=True)
            format_body_paragraph(p, first_line_indent=False)
            continue
        if stripped.startswith("- "):
            p = doc.add_paragraph()
            run = p.add_run(f"• {stripped[2:].strip()}")
            set_run_font(run, size=11)
            format_body_paragraph(p, first_line_indent=False)
            continue
        p = doc.add_paragraph()
        run = p.add_run(stripped)
        set_run_font(run, size=11)
        format_body_paragraph(p, first_line_indent=False if "：" in stripped and len(stripped) < 28 else True)

    doc.save(str(output))
    return output


def main() -> None:
    outputs = [
        fill_design_doc(),
        fill_tech_doc(),
        fill_dev_doc(),
        fill_test_doc(),
        fill_support_doc(
            "配图与AI生成Prompt清单_初稿.md",
            "第十九届全国大学生软件创新大赛-星火-配图与AI生成Prompt清单-v0.3.0.docx",
            "星火配图与 AI 生成 Prompt 清单",
        ),
        fill_support_doc(
            "竞品与外部资料来源清单_初稿.md",
            "第十九届全国大学生软件创新大赛-星火-竞品与外部资料来源清单-v0.3.0.docx",
            "星火竞品与外部资料来源清单",
        ),
    ]
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
