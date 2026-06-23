"""Export service: generate PDF and CSV reports."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from loguru import logger


def generate_pdf_report(analysis_data: dict, resume_data: dict, jd_data: dict) -> bytes:
    """Generate a PDF analysis report using ReportLab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=20, spaceAfter=6, textColor=colors.HexColor("#1e40af"))
        h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=14, spaceBefore=12, spaceAfter=4, textColor=colors.HexColor("#1e3a8a"))
        body_style = styles["BodyText"]
        score_style = ParagraphStyle("Score", parent=styles["Normal"], fontSize=36, textColor=colors.HexColor("#059669"), alignment=TA_CENTER)

        story = []

        story.append(Paragraph("ATS Resume Analysis Report", title_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}", styles["Normal"]))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1e40af")))
        story.append(Spacer(1, 0.5*cm))

        story.append(Paragraph(f"Job: {jd_data.get('title', 'N/A')} @ {jd_data.get('company', 'N/A')}", styles["Heading3"]))
        story.append(Paragraph(f"Resume: {resume_data.get('original_filename', 'N/A')}", styles["Heading3"]))
        story.append(Spacer(1, 0.5*cm))

        story.append(Paragraph("Overall ATS Score", h2_style))
        story.append(Paragraph(f"{analysis_data.get('overall_score', 0):.1f}/100", score_style))
        story.append(Spacer(1, 0.5*cm))

        story.append(Paragraph("Score Breakdown", h2_style))
        breakdown_data = [
            ["Category", "Score", "Weight"],
            ["Keyword Match", f"{analysis_data.get('keyword_score', 0):.1f}%", "35%"],
            ["Skills Match", f"{analysis_data.get('skills_score', 0):.1f}%", "25%"],
            ["Experience Match", f"{analysis_data.get('experience_score', 0):.1f}%", "15%"],
            ["Education Match", f"{analysis_data.get('education_score', 0):.1f}%", "10%"],
            ["Semantic Similarity", f"{analysis_data.get('semantic_score', 0):.1f}%", "15%"],
        ]
        table = Table(breakdown_data, colWidths=[8*cm, 4*cm, 3*cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eff6ff")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#93c5fd")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.5*cm))

        matched_skills = analysis_data.get("matched_skills", [])
        if matched_skills:
            story.append(Paragraph("Matched Skills", h2_style))
            story.append(Paragraph(", ".join(matched_skills[:20]), body_style))
            story.append(Spacer(1, 0.3*cm))

        missing_skills = analysis_data.get("missing_skills", [])
        if missing_skills:
            story.append(Paragraph("Missing Skills", h2_style))
            story.append(Paragraph(", ".join(missing_skills[:20]), body_style))
            story.append(Spacer(1, 0.3*cm))

        suggestions = analysis_data.get("suggestions", [])
        if suggestions:
            story.append(Paragraph("Improvement Suggestions", h2_style))
            for i, suggestion in enumerate(suggestions, 1):
                story.append(Paragraph(f"{i}. {suggestion}", body_style))
            story.append(Spacer(1, 0.3*cm))

        missing_kws = analysis_data.get("missing_keywords", [])
        if missing_kws:
            story.append(Paragraph("Missing Keywords", h2_style))
            story.append(Paragraph(", ".join(missing_kws[:20]), body_style))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise


def generate_csv_ranking(rankings: list[dict], jd_data: dict) -> bytes:
    """Generate a CSV ranking report."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow([
        "Rank", "Candidate", "File", "Overall Score",
        "Keyword Score", "Skills Score", "Experience Score",
        "Education Score", "Semantic Score",
        "Matched Skills", "Missing Skills",
    ])

    for item in rankings:
        analysis = item.get("analysis") or {}
        resume = item.get("resume") or {}
        parsed = resume.get("parsed_data") or {}

        writer.writerow([
            item.get("rank", ""),
            parsed.get("name", "Unknown"),
            resume.get("original_filename", ""),
            f"{item.get('overall_score', 0):.1f}",
            f"{analysis.get('keyword_score', 0):.1f}",
            f"{analysis.get('skills_score', 0):.1f}",
            f"{analysis.get('experience_score', 0):.1f}",
            f"{analysis.get('education_score', 0):.1f}",
            f"{analysis.get('semantic_score', 0):.1f}",
            "; ".join(analysis.get("matched_skills", [])[:10]),
            "; ".join(analysis.get("missing_skills", [])[:10]),
        ])

    return buffer.getvalue().encode("utf-8")
