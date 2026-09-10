"""Build the participant-evaluation and dissertation working documents."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = PROJECT_ROOT / "research_materials"
PARTICIPANT_OUTPUT = OUTPUT_ROOT / "Participant_Evaluation_Pack_DRAFT.docx"
DISSERTATION_OUTPUT = OUTPUT_ROOT / "Dissertation_Working_Draft.docx"
DASHBOARD_IMAGE = PROJECT_ROOT / "evidence" / "formal_results_dashboard.png"

NAVY = "17324D"
BLUE = "285E80"
PALE_BLUE = "DCEAF4"
PALE_GRAY = "F2F4F7"
GOLD = "FFF0CC"
RED = "9B1C1C"
WHITE = "FFFFFF"
INK = "172033"


def set_font(run, name: str = "Calibri", size: float = 11, bold=False, italic=False, color=INK):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)


def shade(cell, fill: str):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_cell_width(cell, width_inches: float):
    width = int(width_inches * 1440)
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(width))
    tc_w.set(qn("w:type"), "dxa")


def style_table(table, widths: list[float], header=True):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table_width = int(sum(widths) * 1440)
    table_properties = table._tbl.tblPr
    table_layout = table_properties.find(qn("w:tblLayout"))
    if table_layout is None:
        table_layout = OxmlElement("w:tblLayout")
        table_properties.append(table_layout)
    table_layout.set(qn("w:type"), "fixed")
    preferred_width = table_properties.find(qn("w:tblW"))
    if preferred_width is None:
        preferred_width = OxmlElement("w:tblW")
        table_properties.append(preferred_width)
    preferred_width.set(qn("w:w"), str(table_width))
    preferred_width.set(qn("w:type"), "dxa")
    grid_columns = table._tbl.tblGrid.gridCol_lst
    for column_index, width_inches in enumerate(widths):
        width_twips = int(width_inches * 1440)
        if column_index < len(grid_columns):
            grid_columns[column_index].set(qn("w:w"), str(width_twips))
        table.columns[column_index].width = Inches(width_inches)
    for row_index, row in enumerate(table.rows):
        for column_index, cell in enumerate(row.cells):
            cell.width = Inches(widths[column_index])
            set_cell_width(cell, widths[column_index])
            cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if header and row_index == 0:
                shade(cell, BLUE)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(2)
                for run in paragraph.runs:
                    set_font(
                        run,
                        size=9.5,
                        bold=header and row_index == 0,
                        color=WHITE if header and row_index == 0 else INK,
                    )
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))


def configure_document(doc: Document, preset: str):
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.8 if preset == "standard_business_brief" else 1.0)
    section.bottom_margin = Inches(0.8 if preset == "standard_business_brief" else 1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string(INK)
    normal.paragraph_format.space_after = Pt(6 if preset == "standard_business_brief" else 8)
    normal.paragraph_format.line_spacing = 1.10 if preset == "standard_business_brief" else 1.333

    settings = [
        ("Heading 1", 16, BLUE, 16 if preset == "standard_business_brief" else 18, 8),
        ("Heading 2", 13, BLUE, 12, 6),
        ("Heading 3", 12, "1F4D78", 8, 4),
    ]
    for style_name, size, color, before, after in settings:
        style = doc.styles[style_name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    for section in doc.sections:
        header = section.header.paragraphs[0]
        header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = header.add_run("Vision-Based Autonomous E-puck Navigation Research")
        set_font(run, size=8.5, color="667085")
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = footer.add_run("Local working document — verify before submission or recruitment")
        set_font(run, size=8, color="667085")


def add_title_block(doc: Document, title: str, subtitle: str, draft=True):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(18)
    paragraph.paragraph_format.space_after = Pt(6)
    run = paragraph.add_run(title)
    set_font(run, size=24, bold=True, color=NAVY)
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(14)
    run = paragraph.add_run(subtitle)
    set_font(run, size=13, italic=True, color=BLUE)
    if draft:
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(18)
        run = paragraph.add_run("DRAFT — NOT APPROVED FOR RECRUITMENT OR SUBMISSION")
        set_font(run, size=11, bold=True, color=RED)


def add_callout(doc: Document, text: str, fill=PALE_BLUE, color=NAVY):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    cell = table.cell(0, 0)
    set_cell_width(cell, 6.5)
    cell_margins(cell, top=140, bottom=140, start=180, end=180)
    shade(cell, fill)
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(text)
    set_font(run, size=10.5, bold=True, color=color)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_bullet(doc: Document, text: str):
    paragraph = doc.add_paragraph(style="List Bullet")
    paragraph.paragraph_format.left_indent = Inches(0.5)
    paragraph.paragraph_format.first_line_indent = Inches(-0.25)
    paragraph.paragraph_format.space_after = Pt(4)
    run = paragraph.add_run(text)
    set_font(run)


def add_numbered(doc: Document, text: str):
    paragraph = doc.add_paragraph(style="List Number")
    paragraph.paragraph_format.left_indent = Inches(0.5)
    paragraph.paragraph_format.first_line_indent = Inches(-0.25)
    paragraph.paragraph_format.space_after = Pt(4)
    run = paragraph.add_run(text)
    set_font(run)


def add_checkbox(doc: Document, text: str):
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.left_indent = Inches(0.25)
    paragraph.paragraph_format.space_after = Pt(5)
    run = paragraph.add_run("☐  " + text)
    set_font(run)


def build_participant_pack():
    doc = Document()
    configure_document(doc, "standard_business_brief")
    add_title_block(
        doc,
        "Participant Evaluation Pack",
        "Vision-Based Lane and Obstacle Detection for Autonomous e-puck Robot Navigation in Webots Simulation",
    )
    metadata = doc.add_table(rows=5, cols=2)
    values = [
        ("Researcher", "Abin Thankachan (student number 34060534)"),
        ("Researcher SHU email", "[REQUIRED BEFORE APPROVAL]"),
        ("Supervisor", "[NAME AND SHU EMAIL REQUIRED BEFORE APPROVAL]"),
        ("Proposed participants", "8–12 adults aged 18+ in Computing; target 10"),
        ("Estimated time", "Approximately 10 minutes"),
    ]
    for row, (label, value) in zip(metadata.rows, values):
        row.cells[0].text = label
        row.cells[1].text = value
        shade(row.cells[0], PALE_GRAY)
    style_table(metadata, [1.875, 4.625], header=False)
    add_callout(
        doc,
        "Do not recruit or collect participant data until the supervisor and independent reviewer/module leader have signed the approved UREC2 materials.",
        fill=GOLD,
        color=RED,
    )

    doc.add_heading("Part A — Participant Information Sheet", level=1)
    doc.add_heading("Purpose of the study", level=2)
    doc.add_paragraph(
        "This study evaluates a simulated e-puck robot that uses camera-based OpenCV perception to follow a lane, detect stationary and moving obstacles, stop or avoid them, rejoin the lane and reach a finish point. Participant feedback will assess whether the demonstration is clear, useful and appropriately communicates safety and limitations."
    )
    doc.add_heading("Why you have been invited", level=2)
    doc.add_paragraph(
        "Adults aged 18 or over with a Computing student or staff background are invited because they can provide informed feedback about the clarity, educational usefulness and limitations of a simulation-based autonomous robotics prototype."
    )
    doc.add_heading("What participation involves", level=2)
    for item in [
        "View the same short live or recorded Webots demonstration used for every participant.",
        "Complete ten rating questions on a five-point scale.",
        "Optionally answer three open-text questions.",
        "Spend approximately ten minutes in total.",
    ]:
        add_bullet(doc, item)
    doc.add_heading("Voluntary participation and withdrawal", level=2)
    doc.add_paragraph(
        "Taking part is voluntary. Choosing not to participate will have no negative consequence. You may stop before submitting the questionnaire. The questionnaire does not request direct identifiers; after an anonymous response is submitted and combined with other responses, it may not be possible to identify and withdraw it."
    )
    doc.add_heading("Risks and benefits", level=2)
    doc.add_paragraph(
        "No physical, medical or sensitive activity is involved. The task is limited to viewing a technical simulation and providing feedback. No direct personal benefit is promised; the feedback may improve the project evaluation and teaching value."
    )
    doc.add_heading("Privacy, lawful basis and confidentiality", level=2)
    doc.add_paragraph(
        "Sheffield Hallam University processes research data under its public task in the public interest. Consent is requested for participation in this specific project. No names, student or staff numbers, email addresses, photographs, audio, video or special-category data will be requested in the questionnaire. Results will be reported in aggregate, and optional quotations will be anonymised or paraphrased."
    )
    paragraph = doc.add_paragraph()
    run = paragraph.add_run("University Privacy Notice for Research Participants: ")
    set_font(run, bold=True)
    run = paragraph.add_run(
        "https://www.shu.ac.uk/about-this-website/privacy-policy/privacy-notices/privacy-notice-for-research"
    )
    set_font(run, color=BLUE)
    doc.add_heading("Storage and retention", level=2)
    doc.add_paragraph(
        "Questionnaire data will be stored in approved university storage. Consent records will be stored separately with access restricted to the researcher and authorized supervisor/reviewer. The proposed retention period is 12 months after final project assessment, after which participant data and consent records will be securely deleted. This period must be confirmed in the approved ethics record before recruitment."
    )
    doc.add_heading("Questions or concerns", level=2)
    doc.add_paragraph(
        "Researcher contact: [SHU EMAIL REQUIRED]. Supervisor contact: [NAME AND SHU EMAIL REQUIRED]. Data protection questions may be directed to DPO@shu.ac.uk. Concerns about research conduct may be directed to ethicssupport@shu.ac.uk."
    )

    doc.add_page_break()
    doc.add_heading("Part B — Participant Consent Form", level=1)
    add_callout(
        doc,
        "Complete this form only after reading Part A. Consent records must be stored separately from questionnaire responses.",
    )
    for statement in [
        "I have read and understood the Participant Information Sheet.",
        "I have had the opportunity to ask questions before deciding.",
        "I understand that participation is voluntary and I may stop before submitting the questionnaire.",
        "I understand that the activity consists of a project demonstration and a short questionnaire.",
        "I understand that the questionnaire does not request direct identifiers or sensitive personal data.",
        "I understand that anonymous responses may be used in aggregated or anonymised form in the final report.",
        "I understand that withdrawal after anonymous submission may not be possible.",
        "I confirm that I am aged 18 or over.",
        "I agree to take part in this low-risk feedback study.",
    ]:
        add_checkbox(doc, statement)
    doc.add_paragraph("\nParticipant name: ______________________________________________")
    doc.add_paragraph("Participant signature: __________________________________________")
    doc.add_paragraph("Date: ____________________")
    doc.add_paragraph("Researcher signature: ___________________________________________")
    doc.add_paragraph("Date: ____________________")

    doc.add_page_break()
    questionnaire_heading = doc.add_heading(
        "Part C — Participant Feedback Questionnaire", level=1
    )
    questionnaire_heading.paragraph_format.left_indent = Inches(0.08)
    doc.add_paragraph(
        "Do not write your name, student number, staff number or email address on this questionnaire."
    )
    role = doc.add_table(rows=2, cols=4)
    role.cell(0, 0).text = "Anonymous participant ID"
    role.cell(0, 1).text = "P____"
    role.cell(0, 2).text = "Role category"
    role.cell(0, 3).text = "☐ Student   ☐ Staff   ☐ Other adult Computing participant"
    role.cell(1, 0).text = "Scale"
    role.cell(1, 1).merge(role.cell(1, 3))
    role.cell(1, 1).text = "1 Strongly disagree | 2 Disagree | 3 Neutral | 4 Agree | 5 Strongly agree"
    style_table(role, [1.45, 1.0, 1.2, 2.85], header=False)
    statements = [
        "The project aim and purpose were clearly explained.",
        "The simulation demonstrated lane following clearly.",
        "The stationary-obstacle detection and avoidance behavior was clear.",
        "The moving-object stop-and-wait behavior appeared logical and safe within the simulation.",
        "The lane-recovery behavior was understandable.",
        "The prototype seemed useful for learning about autonomous robot navigation.",
        "Webots was appropriate for safely testing the project.",
        "Camera-based computer vision was appropriate for the project scope.",
        "The demonstration made the simulation-to-reality limitations understandable.",
        "Overall, the prototype appeared suitable as a Computing or AI research artefact.",
    ]
    table = doc.add_table(rows=1, cols=6)
    headers = ["Statement", "1", "2", "3", "4", "5"]
    for cell, text in zip(table.rows[0].cells, headers):
        cell.text = text
    for index, statement in enumerate(statements, 1):
        cells = table.add_row().cells
        cells[0].text = f"{index}. {statement}"
        for column in range(1, 6):
            cells[column].text = "☐"
            cells[column].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_table(table, [4.65, 0.37, 0.37, 0.37, 0.37, 0.37])
    doc.add_heading("Optional open feedback", level=2)
    for question in [
        "What is the main strength of the prototype?",
        "What is the main limitation or risk that should be improved?",
        "What additional feature, test or evidence would make the project stronger?",
    ]:
        doc.add_paragraph(question)
        doc.add_paragraph("________________________________________________________________")
        doc.add_paragraph("________________________________________________________________")

    doc.add_page_break()
    doc.add_heading("Part D — Debriefing Statement", level=1)
    doc.add_paragraph(
        "Thank you for taking part. The feedback activity supports evaluation of a simulated Webots e-puck navigation prototype using camera-based lane and obstacle detection. Responses will be analysed anonymously and reported in aggregate form. The simulation is a research and teaching prototype and must not be interpreted as evidence that the system is ready for physical deployment or safety-critical use."
    )
    doc.add_paragraph(
        "If you have questions after taking part, contact the researcher at [SHU EMAIL REQUIRED] or the supervisor at [NAME AND SHU EMAIL REQUIRED]."
    )
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    doc.save(PARTICIPANT_OUTPUT)


def add_result_table(doc: Document):
    table = doc.add_table(rows=1, cols=3)
    for cell, text in zip(table.rows[0].cells, ["Measure", "Vision result", "Planned criterion"]):
        cell.text = text
    rows = [
        ("Formal runs", "150", "150"),
        ("Completion", "150/150 (100%)", "≥ 80% overall; ≥ 90% nominal"),
        ("Overall mean lane error", "0.0334 m", "≤ 0.05 m"),
        ("Collisions", "0", "0 accepted-trial collisions"),
        ("Obstacle detections", "90/90 expected; 0 false positives", "≥ 90%"),
        ("Minimum moving-object centre clearance", "0.1277 m", "≥ 0.10 m"),
        ("Multi-obstacle completion", "30/30; 0 collisions", "Stress-case measure"),
        ("Ground-sensor baseline completion", "30/60 (50%)", "Comparison measure"),
    ]
    for values in rows:
        cells = table.add_row().cells
        for cell, value in zip(cells, values):
            cell.text = value
    style_table(table, [2.15, 2.15, 2.2])


def build_dissertation():
    doc = Document()
    configure_document(doc, "narrative_proposal")
    add_title_block(
        doc,
        "Vision-Based Lane and Obstacle Detection for Autonomous e-puck Robot Navigation",
        "Dissertation Working Draft | Webots R2025a and classical OpenCV",
        draft=True,
    )
    metadata = doc.add_table(rows=5, cols=2)
    values = [
        ("Student", "Abin Thankachan"),
        ("Student number", "34060534"),
        ("Technical configuration", "82999888659be0c7"),
        ("Document status", "Technical chapters populated; participant evaluation and verified literature references pending"),
        ("Prepared", date.today().isoformat()),
    ]
    for row, values_row in zip(metadata.rows, values):
        row.cells[0].text, row.cells[1].text = values_row
        shade(row.cells[0], PALE_GRAY)
    style_table(metadata, [1.875, 4.625], header=False)
    add_callout(
        doc,
        "This is a working draft, not a final dissertation. Participant findings, ethics approvals, supervisor feedback and the verified literature review must be completed by the student.",
        fill=GOLD,
        color=RED,
    )

    doc.add_heading("Abstract", level=1)
    doc.add_paragraph(
        "This project designed and evaluated a camera-only autonomous navigation controller for an e-puck robot in Webots R2025a. Classical OpenCV segmentation estimates two white lane boundaries, lane centre, normalized steering error and confidence. Multi-object centroid tracking maintains independent tracks, classifies measured motion and prioritises threats, while a finite-state controller implements lane following, stop-and-wait, avoidance, lane rejoining, finish handling and failsafe behavior. A frozen controller was evaluated in 150 vision trials covering route geometry, lighting, single obstacles and three multi-obstacle layouts; a preserved ground-sensor controller was evaluated in 60 lane-only comparison trials. The vision controller completed all 150 trials with no recorded collisions, 0.0334 m overall mean lateral error and at least 0.1277 m moving-object centre clearance. The baseline completed all straight trials but none of the curve-dominant trials, for 50% overall completion. These findings support the effectiveness of the transparent camera pipeline in this controlled simulation, but do not establish real-world deployment safety."
    )

    doc.add_heading("Document map", level=1)
    for item in [
        "Chapter 1 — Introduction, question, aim and objectives",
        "Chapter 2 — Literature review structure and verification gaps",
        "Chapter 3 — Methodology and research design",
        "Chapter 4 — System design and implementation",
        "Chapter 5 — Experimental design",
        "Chapter 6 — Formal technical results",
        "Chapter 7 — Discussion, limitations and future work",
        "Chapter 8 — Participant evaluation (pending ethics approval)",
        "Chapter 9 — Conclusion",
        "Appendices — Reproducibility, ethics status and AI transparency",
    ]:
        add_bullet(doc, item)

    doc.add_page_break()
    doc.add_heading("1. Introduction", level=1)
    doc.add_paragraph(
        "Autonomous mobile robots require perception that links environmental features to safe movement decisions. Ground-sensor line following is valuable for educational demonstrations but offers limited information about objects and route geometry. This project investigates a transparent, classical computer-vision alternative in which an e-puck uses camera frames for lane following and obstacle behavior inside a repeatable simulation."
    )
    doc.add_heading("1.1 Research question", level=2)
    doc.add_paragraph(
        "How effectively can an OpenCV-based camera-vision controller support lane following, obstacle detection and safe autonomous navigation decisions for an e-puck robot in Webots simulation?"
    )
    doc.add_heading("1.2 Aim", level=2)
    doc.add_paragraph(
        "To design, implement and evaluate a Webots-based vision-control system that enables an autonomous e-puck robot to follow simulated lanes, detect obstacles and execute safe stopping, avoidance and lane-recovery behavior using OpenCV-based computer vision."
    )
    doc.add_heading("1.3 Objectives", level=2)
    for item in [
        "Critically evaluate literature on vision-based lane detection, obstacle detection, mobile robot navigation and simulation-led robotics.",
        "Design a controlled Webots environment with route, lighting and obstacle scenarios.",
        "Develop an OpenCV pipeline that estimates lane position and obstacle cues.",
        "Integrate perception with autonomous following, stopping, avoidance, recovery and failsafe logic.",
        "Evaluate performance using completion, lane error, detections, collisions, clearances, state timing and a ground-sensor baseline.",
        "Subject to ethics approval, collect low-risk participant feedback on clarity, usefulness and perceived safety.",
    ]:
        add_bullet(doc, item)

    doc.add_heading("2. Literature Review", level=1)
    add_callout(
        doc,
        "STUDENT ACTION: complete critical synthesis and verify every citation against the original source. Do not submit the placeholder structure below as a finished literature review.",
        fill=GOLD,
        color=RED,
    )
    for heading, description in [
        ("2.1 Vision-based lane detection", "Compare thresholding, edge/line extraction, perspective effects, robustness to illumination and classical versus learned approaches."),
        ("2.2 Camera-based obstacle detection", "Review colour/contour methods, temporal tracking, ego-motion limitations and distance/clearance estimation."),
        ("2.3 Mobile robot control", "Connect lateral error, PID control, finite-state behavior, recovery logic and conservative stopping."),
        ("2.4 Simulation-led robotics", "Assess repeatability, scenario control and the simulation-to-reality gap."),
        ("2.5 Research gap", "Position the project as a transparent, reproducible e-puck vision controller evaluated across controlled lighting and obstacle cases."),
    ]:
        doc.add_heading(heading, level=2)
        doc.add_paragraph(description)

    doc.add_heading("3. Methodology and Research Design", level=1)
    doc.add_paragraph(
        "The technical study used a deterministic, simulation-based experimental design. Pilot trials were separated from formal trials. The final controller was content-frozen before formal execution using a local SHA-256 manifest, without Git or remote publication. The independent variables were route type, lighting, stationary-obstacle lateral position, moving-object speed and obstacle layout. Each formal scenario was repeated ten times with an explicit scenario ID, repetition and seed."
    )
    doc.add_heading("3.1 Variables and measures", level=2)
    for item in [
        "Independent variables: straight/full route, dim/nominal/bright light, stationary left/centre/right, moving speed 0.10/0.15/0.20 m/s, and sequential-static/sequential-moving/mixed layouts.",
        "Dependent measures: completion, lane error, collision count, object detection, clearance, state observations, stopping distance and duration.",
        "Controls: Webots R2025a, 32 ms step, fixed arena geometry, pinned PROTO URLs, fixed Python/OpenCV/NumPy dependencies.",
        "Comparison: the preserved ground-sensor controller ran the six lane-only cases ten times each.",
    ]:
        add_bullet(doc, item)
    doc.add_heading("3.2 Integrity and separation", level=2)
    doc.add_paragraph(
        "The vision controller reads only its camera and wheel motors. It does not read ground sensors, a Supervisor receiver, robot coordinates or obstacle distances. The Supervisor controls scenarios and writes ground-truth evaluation data but has no Emitter or Receiver connection to the e-puck."
    )

    doc.add_heading("4. System Design and Implementation", level=1)
    doc.add_heading("4.1 World", level=2)
    doc.add_paragraph(
        "The 3.0 m × 2.0 m arena contains a 0.50 m dark-grey road with straight and curved sections, a narrow pair of white vision boundaries, start/finish markers and three checkpoints. Three configurable red 0.08 m stationary obstacles and two configurable blue moving crossing objects provide single- and multi-obstacle layouts. Every obstacle uses collision geometry."
    )
    doc.add_heading("4.2 Perception pipeline", level=2)
    for item in [
        "Convert the Webots BGRA buffer to an OpenCV BGR array.",
        "Apply a camera region of interest and mask the visible robot body.",
        "Use adaptive Otsu value thresholding with low-saturation filtering for white boundaries.",
        "Calculate lane centre, normalized lateral error and confidence.",
        "Segment red and blue obstacle contours in HSV space and merge nearby fragments belonging to one physical object.",
        "Maintain independent track IDs, classify measured motion, rank threats and identify a visually blocked driving corridor.",
        "Detect lane loss and the green finish cue.",
    ]:
        add_numbered(doc, item)
    doc.add_heading("4.3 Control architecture", level=2)
    doc.add_paragraph(
        "The finite-state controller includes FOLLOW_LANE, STOP_WAIT, AVOID, REJOIN, FINISHED and FAILSAFE. PID steering uses the camera-derived lane error. Moving or unknown objects and blocked multi-obstacle corridors cause a stop while classification continues. Confirmed stationary obstacles cause a committed S-curve avoidance manoeuvre bound to the active track and colour, after which the controller reacquires the lane. A newly threatening object can interrupt avoidance, and timeouts force a safe stop."
    )

    doc.add_page_break()
    doc.add_heading("5. Experimental Design", level=1)
    table = doc.add_table(rows=1, cols=4)
    for cell, text in zip(table.rows[0].cells, ["Category", "Scenarios", "Repetitions", "Controller"]):
        cell.text = text
    rows = [
        ("Lane", "Straight/full × nominal/dim/bright", "6 × 10", "Vision"),
        ("Stationary", "Left/centre/right", "3 × 10", "Vision"),
        ("Moving", "0.10/0.15/0.20 m/s", "3 × 10", "Vision"),
        ("Multi-obstacle", "Sequential static/moving; mixed", "3 × 10", "Vision"),
        ("Baseline", "Six lane cases", "6 × 10", "Ground sensor"),
    ]
    for values in rows:
        cells = table.add_row().cells
        for cell, value in zip(cells, values):
            cell.text = value
    style_table(table, [1.25, 3.1, 1.0, 1.15])
    doc.add_paragraph(
        "Formal configuration ID: 82999888659be0c7. All 210 formal summary rows carry this ID. The earlier 180-run single-target result set is preserved separately and excluded from the current reported results."
    )

    doc.add_heading("6. Formal Technical Results", level=1)
    add_result_table(doc)
    doc.add_heading("6.1 Scenario findings", level=2)
    for item in [
        "All 60 vision lane-only runs completed. Scenario mean lane error ranged from 0.0014 m to 0.0365 m.",
        "All 30 stationary-obstacle runs detected the obstacle, entered avoidance, rejoined and finished with no recorded collision.",
        "All 30 moving-object runs detected the object and entered stop-and-wait. Minimum centre clearance across moving-object layouts was 0.1277 m.",
        "All 30 multi-obstacle runs completed with no recorded collision: sequential static, sequential moving and mixed static/moving layouts each completed 10/10.",
        "The multi_static_sequential stress case averaged 0.0585 m lane error, above the 0.05 m target when considered individually; the overall vision mean remained 0.0334 m.",
        "No false-positive obstacle detections were recorded in the 60 lane-only vision runs.",
        "The ground-sensor baseline completed 30/30 straight runs and 0/30 curve-dominant runs, producing 50% completion overall.",
    ]:
        add_bullet(doc, item)
    if DASHBOARD_IMAGE.exists():
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run()
        run.add_picture(str(DASHBOARD_IMAGE), width=Inches(6.3))
        caption = doc.add_paragraph("Figure 1. Formal technical-results dashboard.")
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        caption.paragraph_format.space_after = Pt(8)
        for run in caption.runs:
            set_font(run, size=9, italic=True, color="667085")

    doc.add_heading("7. Discussion", level=1)
    doc.add_paragraph(
        "The formal results indicate that the camera controller was robust within the controlled simulation matrix. Adaptive thresholding supported all three lighting conditions, while the state machine separated moving-object waiting from stationary avoidance and conservatively handled the configured multi-obstacle layouts. The sequential-static stress case increased lateral error, showing that completion and collision outcomes should be interpreted alongside path-quality metrics. The comparison suggests that the preserved ground-sensor baseline was effective on a simple straight route but could not generalise to the curved route geometry used here."
    )
    doc.add_heading("7.1 Limitations", level=2)
    for item in [
        "The results are simulation evidence and do not demonstrate physical-robot or safety-critical deployment readiness.",
        "Colour segmentation assumes deliberately red and blue objects and controlled scene design.",
        "Centroid displacement contains apparent motion caused by robot movement; it is not a full world-motion estimator.",
        "The camera and lane geometry were tuned together, so performance may change under different camera mounts or road markings.",
        "Deterministic repetitions demonstrate repeatability but do not substitute for broader randomised geometry and sensor-noise testing.",
        "The baseline was preserved from the original project and was not redesigned for the new curved track, which limits causal claims about sensing modality alone.",
    ]:
        add_bullet(doc, item)
    doc.add_heading("7.2 Future work", level=2)
    for item in [
        "Randomise lane wear, textures, shadows, object trajectories and camera noise.",
        "Estimate obstacle range and ego-motion explicitly.",
        "Evaluate denser simultaneous objects, occlusion, additional colours/shapes and more route geometries.",
        "Transfer the frozen pipeline to a physical e-puck only after a separate safety assessment.",
        "Complete the approved participant evaluation and integrate anonymous findings.",
    ]:
        add_bullet(doc, item)

    doc.add_heading("8. Participant Evaluation — Pending", level=1)
    add_callout(
        doc,
        "No participant responses exist. This chapter must remain pending until UREC2 approval is signed and the approved recruitment/data-collection procedure is completed.",
        fill=GOLD,
        color=RED,
    )
    doc.add_paragraph(
        "Planned analysis: Likert counts, percentages, means and distributions for ten items, followed by anonymised thematic coding of three optional open-text questions. Consent records will be stored separately from questionnaire data."
    )

    doc.add_heading("9. Ethics, Privacy and Data Management", level=1)
    doc.add_paragraph(
        "The technical simulation did not involve human participants. A low-risk UREC2 participant-feedback route is planned. Recruitment must not begin until supervisor and independent-reviewer approval is recorded. The proposed participant data retention period is 12 months after final project assessment, subject to approval. Sheffield Hallam University's public task is the proposed lawful basis for research processing; informed consent is requested for participation."
    )

    doc.add_heading("10. Conclusion", level=1)
    doc.add_paragraph(
        "Within the controlled Webots R2025a environment, the frozen camera controller met the planned overall technical criteria: 150/150 vision completions, zero recorded collisions, 0.0334 m overall mean lane error, complete expected-object detection and moving-object centre clearance above 0.10 m. All 30 configured multi-obstacle runs completed, although the sequential-static scenario exceeded the 0.05 m lane-error target when considered separately. The results support the research aim at simulation level and demonstrate a transparent alternative to the original ground-sensor baseline. Claims must remain limited to the evaluated simulation until further external and physical validation is completed."
    )

    doc.add_heading("References — Verification Required", level=1)
    add_callout(
        doc,
        "STUDENT ACTION: replace this short implementation-source list with a complete, critically verified academic reference list. Verify authors, titles, years, venues, DOIs and access dates.",
        fill=GOLD,
        color=RED,
    )
    for reference in [
        "Cyberbotics. Webots R2025a release and documentation. https://cyberbotics.com/",
        "OpenCV documentation. https://docs.opencv.org/",
        "Sheffield Hallam University. Privacy Notice for Research Participants. https://www.shu.ac.uk/about-this-website/privacy-policy/privacy-notices/privacy-notice-for-research",
        "Sheffield Hallam University. Research data management guidance. https://www.shu.ac.uk/research/excellence/ethics-and-integrity/data-management",
    ]:
        doc.add_paragraph(reference)

    doc.add_heading("Appendix A — Reproducibility", level=1)
    for item in [
        "Plan and progress: PROJECT_COMPLETION_PLAN.md",
        "Frozen manifest: config/frozen_experiment_configuration.json (configuration 82999888659be0c7)",
        "Scenario matrix: scenarios/scenarios.json",
        "Worlds: worlds/autonomous_epuck_experiment.wbt and worlds/ground_sensor_baseline.wbt",
        "Formal raw evaluator data: results/formal/raw/",
        "Formal camera telemetry: results/formal/telemetry/",
        "Enriched summary: results/formal/enriched_summary.csv",
        "Results workbook: results/Research_Results.xlsx",
    ]:
        add_bullet(doc, item)

    doc.add_heading("Appendix B — AI Transparency Declaration", level=1)
    doc.add_paragraph(
        "Generative AI was used extensively as a development assistant for requirements synthesis, planning, Python controller code, Webots world generation, automated tests, experiment orchestration, spreadsheet construction and document drafting. The student remains responsible for understanding, executing, validating and revising all outputs; verifying academic references; checking compliance with module and university rules; accurately declaring AI use in the required submission format; and making final authorship and submission decisions. AI-generated text and code must not be represented as independently authored without the required disclosure."
    )

    doc.add_heading("Appendix C — Outstanding Completion Checklist", level=1)
    for item in [
        "Complete and verify the literature review and academic references.",
        "Add researcher and supervisor contact details to ethics materials.",
        "Confirm retention and obtain supervisor/independent-reviewer signatures.",
        "Collect no participant data before approval.",
        "After approval, conduct and analyse participant evaluation.",
        "Integrate supervisor feedback and complete final proofreading.",
    ]:
        add_checkbox(doc, item)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    doc.save(DISSERTATION_OUTPUT)


def main():
    build_participant_pack()
    build_dissertation()
    print(PARTICIPANT_OUTPUT)
    print(DISSERTATION_OUTPUT)


if __name__ == "__main__":
    main()
