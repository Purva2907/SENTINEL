import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors

def generate_pdf(case: dict, user: dict) -> str:
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    file_path = os.path.join(reports_dir, f"{case['case_id']}.pdf")
    doc = SimpleDocTemplate(file_path, pagesize=letter)
    styles = getSampleStyleSheet()
    
    title_style = styles['Heading1']
    title_style.textColor = colors.HexColor("#FF9D50")
    
    heading2_style = styles['Heading2']
    heading2_style.textColor = colors.HexColor("#1DCED8")
    
    normal_style = styles['Normal']
    
    story = []
    
    # Page 1 - Header
    story.append(Paragraph("SENTINEL", title_style))
    story.append(Paragraph("AI-Powered Document Forensics", normal_style))
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("FORENSIC SCREENING REPORT", heading2_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(f"<b>Case ID:</b> {case['case_id']}", normal_style))
    story.append(Paragraph(f"<b>Document Type:</b> {case.get('document_type', 'Unknown')}", normal_style))
    story.append(Paragraph(f"<b>Investigator:</b> {user['name']}", normal_style))
    story.append(Paragraph(f"<b>Date:</b> {case.get('created_at', '')}", normal_style))
    story.append(Spacer(1, 20))
    
    story.append(Paragraph(f"<b>Risk Score:</b> {case.get('risk_score', 0)} / 100", normal_style))
    classification_color = "#55E07E"
    if case.get('classification') == 'High Suspicion': classification_color = "#ff4d4d"
    elif case.get('classification') == 'Review Required': classification_color = "#ffcc00"
    
    classification_style = ParagraphStyle(
        'Classification',
        parent=styles['Normal'],
        textColor=colors.HexColor(classification_color),
        fontSize=14,
        spaceAfter=20
    )
    story.append(Paragraph(f"<b>Classification:</b> {case.get('classification', 'Unknown').upper()}", classification_style))
    
    # Page 2 - Evidence Table
    story.append(PageBreak())
    story.append(Paragraph("FORENSIC EVIDENCE", heading2_style))
    
    analysis = case.get('analysis', {})
    evidence_list = analysis.get('evidence', [])
    
    if evidence_list:
        table_data = [["ID", "Category", "Finding", "Severity"]]
        for ev in evidence_list:
            table_data.append([
                ev.get('id', 'N/A'),
                ev.get('category', 'N/A'),
                ev.get('finding', 'N/A'),
                ev.get('severity', 'N/A')
            ])
            
        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#FF9D50")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#FFF9D8")),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No specific evidence recorded.", normal_style))
        
    # Final Page - Disclaimer
    story.append(PageBreak())
    story.append(Paragraph("DISCLAIMER", heading2_style))
    disclaimer_text = "SENTINEL is a forensic screening prototype intended to assist investigation and document review. Results are based on available visual, OCR, QR and image-forensic indicators and should not be treated as official government authentication or a definitive determination of document authenticity."
    story.append(Paragraph(disclaimer_text, normal_style))
    
    doc.build(story)
    
    return file_path
