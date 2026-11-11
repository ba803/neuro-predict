"""
report_generator.py
Generates a professional 4-page A4 PDF clinical assessment report for NeuroPredict.
Follows strict publishing standards: consistent headers/footers, high-resolution vector-quality charts,
no clipping or distortion, and completely non-technical wording.
"""

import io
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
    HRFlowable,
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and draw exact total page numbers
    and professional running headers and footers on every page.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running header (Pages 2, 3, 4)
        if self._pageNumber > 1:
            self.drawString(45, 805, "NeuroPredict | Detailed Assessment Report")
            self.drawRightString(550, 805, "Confidential Healthcare Assessment")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.75)
            self.line(45, 798, 550, 798)

        # Running footer (All pages)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.75)
        self.line(45, 45, 550, 45)

        self.drawString(45, 32, "Educational & Research Tool — Not a Medical Diagnosis")
        self.drawRightString(550, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


# -------------------------------------------------------------------
# Chart Generation (300 DPI, Dedicated A4 Dimensions)
# -------------------------------------------------------------------
def generate_pdf_likelihood_chart(prob_ad: float, prob_other: float, risk_level: str) -> io.BytesIO:
    """
    Generate clean, large high-resolution donut chart for likelihood.
    """
    fig, ax = plt.subplots(figsize=(6.8, 3.4), dpi=300)
    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#ffffff')

    is_high = "higher" in risk_level.lower()
    slice_colors = ['#ef4444', '#10b981'] if is_high else ['#10b981', '#3b82f6']

    wedges, _ = ax.pie(
        [prob_ad, prob_other],
        colors=['#ef4444', '#10b981'],
        startangle=90,
        counterclock=False,
        wedgeprops=dict(width=0.35, edgecolor='#ffffff', linewidth=2.5)
    )

    # Center label
    center_text = f"{prob_ad:.1f}%"
    sub_text = "Higher Risk" if is_high else "Lower Risk"
    color_text = '#dc2626' if is_high else '#059669'

    ax.text(0, 0.1, center_text, ha='center', va='center', fontsize=22, fontweight='bold', color=color_text)
    ax.text(0, -0.15, sub_text, ha='center', va='center', fontsize=10, fontweight='bold', color='#475569')

    # Legend below
    ax.legend(
        wedges,
        [f"Higher Risk Likelihood: {prob_ad:.1f}%", f"Lower Risk Likelihood: {prob_other:.1f}%"],
        loc="center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=2,
        frameon=False,
        fontsize=9.5
    )

    ax.set_title("Assessment Likelihood Distribution", fontsize=12, fontweight='bold', color='#0f172a', pad=15)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_pdf_key_factors_chart(key_factors: List[Dict[str, Any]]) -> io.BytesIO:
    """
    Generate horizontal bar chart for Key Factors considered in the assessment.
    """
    # Sort ascending for horizontal bar chart (highest at top)
    sorted_factors = sorted(key_factors, key=lambda x: x["weight"])
    names = [f["factor"] for f in sorted_factors]
    weights = [f["weight"] for f in sorted_factors]

    fig, ax = plt.subplots(figsize=(6.8, 3.2), dpi=300)
    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#f8fafc')

    bars = ax.barh(names, weights, color='#0284c7', height=0.52, edgecolor='#0369a1', linewidth=1)

    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.8, bar.get_y() + bar.get_height() / 2, f"{w:.1f}%",
                va='center', ha='left', fontsize=8.5, fontweight='bold', color='#1e293b')

    ax.set_xlim(0, max(weights) + 8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#cbd5e1')
    ax.spines['bottom'].set_color('#cbd5e1')
    ax.tick_params(axis='y', labelsize=9, colors='#1e293b')
    ax.tick_params(axis='x', labelsize=8.5, colors='#64748b')
    ax.set_xlabel("Relevance in Assessment (%)", fontsize=9, color='#475569', labelpad=6)
    ax.set_title("Key Factors Considered in Assessment", fontsize=12, fontweight='bold', color='#0f172a', pad=12)
    ax.grid(axis='x', linestyle='--', alpha=0.5, color='#e2e8f0')

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_pdf_scores_chart(patient_scores: Dict[str, Any]) -> io.BytesIO:
    """
    Generate clean score progress meters for the numeric scores.
    """
    labels = ["Functional Assessment", "MMSE Score", "ADL Score"]
    values = [
        patient_scores["functional"]["value"],
        patient_scores["mmse"]["value"],
        patient_scores["adl"]["value"]
    ]
    max_values = [10.0, 30.0, 10.0]
    display_texts = [
        patient_scores["functional"]["display"],
        patient_scores["mmse"]["display"],
        patient_scores["adl"]["display"]
    ]

    # Convert to 0-100% progress for visual bars
    percents = [(v / m) * 100 for v, m in zip(values, max_values)]

    # Reverse so top is first
    labels.reverse()
    percents.reverse()
    display_texts.reverse()

    fig, ax = plt.subplots(figsize=(6.8, 2.5), dpi=300)
    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#f8fafc')

    # Background gray tracks
    ax.barh(labels, [100, 100, 100], color='#e2e8f0', height=0.5, edgecolor='none')
    # Foreground active bars
    bars = ax.barh(labels, percents, color='#0284c7', height=0.5, edgecolor='#0369a1', linewidth=0.8)

    for i, bar in enumerate(bars):
        ax.text(103, bar.get_y() + bar.get_height() / 2, display_texts[i],
                va='center', ha='left', fontsize=9, fontweight='bold', color='#0f172a')

    ax.set_xlim(0, 125)
    ax.set_xticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#cbd5e1')
    ax.spines['bottom'].set_visible(False)
    ax.tick_params(axis='y', labelsize=9.5, colors='#1e293b')
    ax.set_title("Your Assessment Scores (Numeric Indicators)", fontsize=11.5, fontweight='bold', color='#0f172a', pad=10)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


# -------------------------------------------------------------------
# Primary PDF Builder Function (Strict 4-Page A4 Layout)
# -------------------------------------------------------------------
def create_pdf_report(report_data: dict, output_filepath: str = None) -> bytes:
    """
    Builds an executive clinical PDF report with exactly 4 distinct pages on A4.
    """
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        leftMargin=45,
        rightMargin=45,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    # Custom styles
    app_title_style = ParagraphStyle(
        'AppTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#0f172a')
    )

    doc_subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#475569')
    )

    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#64748b'),
        alignment=2 # Right aligned
    )

    page_heading_style = ParagraphStyle(
        'PageHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=0,
        spaceAfter=4
    )

    page_subheading_style = ParagraphStyle(
        'PageSubheading',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=12
    )

    section_heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=8,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'ReportBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=14,
        textColor=colors.HexColor('#334155')
    )

    body_bold = ParagraphStyle(
        'ReportBodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=14,
        textColor=colors.HexColor('#0f172a')
    )

    disclaimer_style = ParagraphStyle(
        'DisclaimerText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=13,
        textColor=colors.HexColor('#78350f')
    )

    story = []

    # Common values
    is_high_risk = "higher" in report_data.get("risk_level", "").lower()
    risk_title = "Higher Risk" if is_high_risk else "Lower Risk"
    prob_ad = float(report_data.get("alzheimers_likelihood", report_data.get("probability_alzheimers", 0.0)))
    prob_other = float(report_data.get("other_likelihood", report_data.get("probability_no_alzheimers", 100.0 - prob_ad)))
    assessment_id = report_data.get("assessment_id", f"NP-{datetime.now().strftime('%Y%m%d')}-001")
    date_str = report_data.get("timestamp_formatted", datetime.now().strftime("%B %d, %Y at %I:%M %p"))
    patient_scores = report_data.get("patient_scores", {})
    key_factors = report_data.get("key_factors", [])

    # ===================================================================
    # PAGE 1: NeuroPredict | Assessment Summary & Your Assessment
    # ===================================================================
    header_table_data = [
        [
            Paragraph("<b>NeuroPredict</b><br/><font color='#475569' size='11'>Alzheimer's Risk Assessment</font>", app_title_style),
            Paragraph(f"<b>Assessment Date:</b> {date_str}<br/><b>Reference:</b> {assessment_id}", meta_style)
        ]
    ]
    head_table = Table(header_table_data, colWidths=[315, 190])
    head_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(head_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284c7'), spaceAfter=14))

    # Page 1 Section: Assessment Summary
    story.append(Paragraph("Assessment Summary", page_heading_style))
    story.append(Paragraph("Initial assessment evaluation based on provided responses.", page_subheading_style))

    badge_bg = colors.HexColor('#fef2f2') if is_high_risk else colors.HexColor('#ecfdf5')
    badge_border = colors.HexColor('#ef4444') if is_high_risk else colors.HexColor('#10b981')
    badge_color = '#dc2626' if is_high_risk else '#047857'

    result_box_content = [
        [
            Paragraph(f"<font color='{badge_color}' size='16'><b>{risk_title}</b></font>", styles['Normal']),
            Paragraph(f"<b>Alzheimer's Likelihood:</b> <font size='12'><b>{prob_ad:.1f}%</b></font>&nbsp;&nbsp;|&nbsp;&nbsp;<b>Other Likelihood:</b> {prob_other:.1f}%", body_style)
        ],
        [
            Paragraph(report_data.get("explanation", "This result is based on the information entered in the assessment. It is intended for educational and research purposes and should not be treated as a medical diagnosis."), body_style),
            ""
        ]
    ]
    result_table = Table(result_box_content, colWidths=[170, 335])
    result_table.setStyle(TableStyle([
        ('SPAN', (0, 1), (1, 1)),
        ('BACKGROUND', (0, 0), (-1, -1), badge_bg),
        ('BOX', (0, 0), (-1, -1), 1.5, badge_border),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(result_table)
    story.append(Spacer(1, 12))

    summary_text = report_data.get("summary", f"Based on the information provided, the assessment indicates a {risk_title.lower()} level of risk. The estimated likelihood was {prob_ad:.1f}%.")
    story.append(Paragraph(f"<b>Summary:</b> {summary_text}", body_style))
    story.append(Spacer(1, 16))

    # Page 1 Section: Your Assessment (Five Values)
    story.append(Paragraph("Your Assessment Values", page_heading_style))
    story.append(Paragraph("The five values provided for this evaluation.", page_subheading_style))

    p_raw = report_data.get("patient_data", {})
    fas_val = p_raw.get("Functional_Assessment_Score", patient_scores.get("functional", {}).get("value", "N/A"))
    mmse_val = int(p_raw.get("MMSE_Score", patient_scores.get("mmse", {}).get("value", 0)))
    adl_val = p_raw.get("ADL_Score", patient_scores.get("adl", {}).get("value", "N/A"))
    mem_val = "Yes" if p_raw.get("Memory_Complaints", patient_scores.get("memory", {}).get("value", 0)) == 1 else "No"
    beh_val = "Yes" if p_raw.get("Behavioral_Problems", patient_scores.get("behavior", {}).get("value", 0)) == 1 else "No"

    table_data_p1 = [
        [Paragraph("<b>Factor</b>", body_bold), Paragraph("<b>Your Value</b>", body_bold), Paragraph("<b>Description</b>", body_bold)],
        [Paragraph("Functional Assessment Score", body_style), Paragraph(f"<b>{fas_val} / 10</b>", body_style), Paragraph("Measures how independently a person manages everyday activities.", body_style)],
        [Paragraph("MMSE Score", body_style), Paragraph(f"<b>{mmse_val} / 30</b>", body_style), Paragraph("A short assessment of memory, attention and thinking.", body_style)],
        [Paragraph("ADL Score", body_style), Paragraph(f"<b>{adl_val} / 10</b>", body_style), Paragraph("Measures how independently a person manages daily living activities.", body_style)],
        [Paragraph("Memory Complaints", body_style), Paragraph(f"<b>{mem_val}</b>", body_style), Paragraph("Are there noticeable or persistent memory difficulties?", body_style)],
        [Paragraph("Behavioral Problems", body_style), Paragraph(f"<b>{beh_val}</b>", body_style), Paragraph("Have there been noticeable changes in behavior or mood?", body_style)],
    ]
    t_p1 = Table(table_data_p1, colWidths=[155, 90, 260])
    t_p1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    story.append(t_p1)

    story.append(PageBreak())

    # ===================================================================
    # PAGE 2: Visual Analysis (Large Likelihood Chart + Key Factors Chart)
    # ===================================================================
    story.append(Paragraph("Visual Analysis", page_heading_style))
    story.append(Paragraph("Detailed visual breakdown of likelihood distribution and primary factors.", page_subheading_style))

    # 1. Large Likelihood Chart
    buf_likelihood = generate_pdf_likelihood_chart(prob_ad, prob_other, risk_title)
    story.append(Image(buf_likelihood, width=505, height=240))
    story.append(Spacer(1, 14))

    # 2. Large Key Factors Chart
    buf_factors = generate_pdf_key_factors_chart(key_factors)
    story.append(Image(buf_factors, width=505, height=230))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "<i>Note: Key factors indicate the relative weighting of each factor considered during the assessment evaluation.</i>",
        ParagraphStyle('NoteStyle', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=8, textColor=colors.HexColor('#64748b'))
    ))

    story.append(PageBreak())

    # ===================================================================
    # PAGE 3: Your Scores (Visual Scores Meter + Key Factors Table)
    # ===================================================================
    story.append(Paragraph("Your Assessment Scores", page_heading_style))
    story.append(Paragraph("Visual comparison of your scores and summary of their plain-language meanings.", page_subheading_style))

    # 1. Scores Chart
    if patient_scores:
        buf_scores = generate_pdf_scores_chart(patient_scores)
        story.append(Image(buf_scores, width=505, height=185))
        story.append(Spacer(1, 10))

    # Status Cards for Binary Fields (Memory & Behavior)
    status_box_data = [
        [
            Paragraph("<b>Memory Complaints:</b>", body_bold),
            Paragraph(f"<font color='{'#dc2626' if mem_val == 'Yes' else '#059669'}'><b>{mem_val}</b> ({'Reported' if mem_val == 'Yes' else 'None reported'})</font>", body_style),
            Paragraph("<b>Behavioral Problems:</b>", body_bold),
            Paragraph(f"<font color='{'#dc2626' if beh_val == 'Yes' else '#059669'}'><b>{beh_val}</b> ({'Observed' if beh_val == 'Yes' else 'None observed'})</font>", body_style),
        ]
    ]
    status_table = Table(status_box_data, colWidths=[120, 132, 120, 133])
    status_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(status_table)
    story.append(Spacer(1, 14))

    # 2. Key Factors Table (Factor, Your Value, Meaning)
    story.append(Paragraph("Key Factors Summary", section_heading_style))
    factors_rows = [
        [Paragraph("<b>Factor</b>", body_bold), Paragraph("<b>Your Value</b>", body_bold), Paragraph("<b>Meaning</b>", body_bold)],
    ]
    for row in report_data.get("factors_table", []):
        factors_rows.append([
            Paragraph(row.get("factor", ""), body_style),
            Paragraph(f"<b>{row.get('value', '')}</b>", body_style),
            Paragraph(row.get("meaning", ""), body_style),
        ])

    table_factors_summary = Table(factors_rows, colWidths=[175, 110, 220])
    table_factors_summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    story.append(table_factors_summary)

    story.append(PageBreak())

    # ===================================================================
    # PAGE 4: Helpful Guidance & Important Notice
    # ===================================================================
    story.append(Paragraph("Helpful Guidance & Next Steps", page_heading_style))
    story.append(Paragraph("Supportive recommendations based on your entered assessment values.", page_subheading_style))

    # 1. Personalized Suggestions
    story.append(Paragraph("Personalized Observations", section_heading_style))
    guidance_list = report_data.get("helpful_guidance", [])
    if guidance_list:
        guidance_rows = []
        for g in guidance_list:
            guidance_rows.append([Paragraph(f"&bull;&nbsp;&nbsp;{g}", body_style)])
        t_guidance = Table(guidance_rows, colWidths=[505])
        t_guidance.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_guidance)
    story.append(Spacer(1, 10))

    # 2. General Wellness Guidance
    story.append(Paragraph("General Healthy-Living Guidance", section_heading_style))
    wellness_list = report_data.get("general_wellness", [
        "Maintain regular physical activity and gentle aerobic exercise.",
        "Maintain a consistent and restful sleep routine.",
        "Stay socially engaged with family, friends, and community.",
        "Follow a balanced, nutritious diet and stay well hydrated.",
        "Keep regular periodic health checkups with your doctor.",
        "Keep track of noticeable changes in memory, mood, or daily routines over time."
    ])
    wellness_rows = []
    for w in wellness_list:
        wellness_rows.append([Paragraph(f"&bull;&nbsp;&nbsp;{w}", body_style)])
    t_wellness = Table(wellness_rows, colWidths=[505])
    t_wellness.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_wellness)
    story.append(Spacer(1, 16))

    # 3. Important Notice (Medical Disclaimer Box)
    notice_text = (
        "<b>IMPORTANT NOTICE:</b> "
        "This application provides an assessment based on the information entered and is intended for "
        "educational and research purposes. It is not a medical diagnosis and should not replace evaluation "
        "by a qualified healthcare professional.<br/><br/>"
        "<i>These suggestions provide supportive practical tips for lifestyle and clinician communication. "
        "Lifestyle habits do not prevent or cure Alzheimer's disease. No medications or treatments are prescribed.</i>"
    )
    notice_box = Table(
        [[Paragraph(notice_text, disclaimer_style)]],
        colWidths=[505]
    )
    notice_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fef3c7')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#f59e0b')),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(notice_box)

    # Build document with NumberedCanvas for exact page counting
    doc.build(story, canvasmaker=NumberedCanvas)
    pdf_bytes = pdf_buffer.getvalue()

    if output_filepath:
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
        with open(output_filepath, "wb") as f:
            f.write(pdf_bytes)

    return pdf_bytes
