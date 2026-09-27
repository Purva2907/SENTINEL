import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, Image
from reportlab.lib import colors

def generate_pdf(case: dict, user: dict, report_id: str = None) -> str:
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    filename = f"{report_id}.pdf" if report_id else f"{case.get('case_id', 'case')}.pdf"
    file_path = os.path.join(reports_dir, filename)
    
    # 0.5 inch (36 pt) margins = 540 pt printable width, 720 pt printable height
    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=32,
        bottomMargin=32
    )
    
    styles = getSampleStyleSheet()
    
    # Typography Styles
    brand_title_style = ParagraphStyle(
        'BrandTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A")
    )
    
    brand_sub_style = ParagraphStyle(
        'BrandSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0284C7")
    )
    
    meta_head_style = ParagraphStyle(
        'MetaHead',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748B")
    )
    
    meta_val_style = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0F172A")
    )
    
    heading2_style = ParagraphStyle(
        'Heading2Compact',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0F172A")
    )
    
    table_head_style = ParagraphStyle(
        'TableHead',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#1E293B")
    )
    
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0F172A")
    )
    
    disclaimer_style = ParagraphStyle(
        'DisclaimerText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#475569")
    )

    story = []
    
    # ---------------- 1. EXECUTIVE HEADER BAR ----------------
    if isinstance(user, dict):
        investigator_name = user.get('name') or user.get('username') or case.get('investigator_name') or "Investigator"
    elif isinstance(user, str) and user:
        investigator_name = user
    else:
        investigator_name = case.get('investigator_name') or "Investigator"
    date_str = str(case.get('created_at', ''))[:19].replace('T', ' ')
    readable_report_id = report_id or f"RPT-2026-{case.get('case_id', 'DOC')}"
    
    report_type_style = ParagraphStyle(
        'ReportTypeSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#64748B")
    )
    
    logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "assets", "sentinel-mark-light.png")
    if not os.path.exists(logo_path):
        logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "assets", "sentinel-mark.png")
    
    has_logo = os.path.exists(logo_path)
    
    if has_logo:
        logo_img = Image(logo_path, width=32, height=32)
        brand_flow = [
            Paragraph("<b>SENTINEL</b>", brand_title_style),
            Paragraph("AI-POWERED DOCUMENT FORENSICS", brand_sub_style),
            Paragraph("FORENSIC INVESTIGATION REPORT", report_type_style)
        ]
        meta_flow = [
            Paragraph(f"<b>REPORT ID:</b> {readable_report_id}<br/><b>DATE:</b> {date_str} UTC", ParagraphStyle(
                'HeaderRight',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=8,
                leading=11,
                alignment=2,
                textColor=colors.HexColor("#475569")
            )),
            Spacer(1, 4),
            Paragraph("CONFIDENTIAL // FORENSIC AUDIT RECORD", ParagraphStyle(
                'HeaderRightConf',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=7,
                leading=8,
                alignment=2,
                textColor=colors.HexColor("#94A3B8")
            ))
        ]
        header_table = Table([[logo_img, brand_flow, meta_flow]], colWidths=[38, 270, 232])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor("#0284C7")),
        ]))
    else:
        header_data = [
            [
                Paragraph("<b>SENTINEL</b>", brand_title_style),
                Paragraph(f"<b>REPORT ID:</b> {readable_report_id}<br/><b>DATE:</b> {date_str} UTC", ParagraphStyle(
                    'HeaderRight',
                    parent=styles['Normal'],
                    fontName='Helvetica',
                    fontSize=8,
                    leading=11,
                    alignment=2,
                    textColor=colors.HexColor("#475569")
                ))
            ],
            [
                Paragraph("AI-POWERED DOCUMENT FORENSICS<br/><font color='#64748B' size='7'>FORENSIC INVESTIGATION REPORT</font>", brand_sub_style),
                Paragraph("CONFIDENTIAL // FORENSIC AUDIT RECORD", ParagraphStyle(
                    'HeaderRightConf',
                    parent=styles['Normal'],
                    fontName='Helvetica-Bold',
                    fontSize=7,
                    leading=8,
                    alignment=2,
                    textColor=colors.HexColor("#94A3B8")
                ))
            ]
        ]
        header_table = Table(header_data, colWidths=[300, 240])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('LINEBELOW', (0, 1), (-1, 1), 1.5, colors.HexColor("#0284C7")),
        ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    
    # ---------------- 2. CASE OVERVIEW & RISK SUMMARY ----------------
    risk_score = int(case.get('risk_score', 0))
    authenticity_score = int(case.get('authenticity_score', max(0, 100 - risk_score)))
    classification = str(case.get('classification', 'Review Required')).upper()
    
    class_bg = "#DCFCE7"  # Green
    class_text = "#15803D"
    if "HIGH" in classification:
        class_bg = "#FEE2E2"
        class_text = "#B91C1C"
    elif "REVIEW" in classification or "SUSPIC" in classification:
        class_bg = "#FEF3C7"
        class_text = "#B45309"
        
    left_meta = [
        [Paragraph("CASE IDENTIFIER:", meta_head_style), Paragraph(f"<b>{case.get('case_id', 'N/A')}</b>", meta_val_style)],
        [Paragraph("INVESTIGATION TITLE:", meta_head_style), Paragraph(case.get('title', 'Forensic Intake Screening'), meta_val_style)],
        [Paragraph("DOCUMENT TYPE:", meta_head_style), Paragraph(case.get('document_type', 'Unknown'), meta_val_style)],
        [Paragraph("INVESTIGATOR:", meta_head_style), Paragraph(investigator_name, meta_val_style)],
    ]
    left_meta_table = Table(left_meta, colWidths=[110, 210])
    left_meta_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    score_display = [
        [Paragraph("AUTHENTICITY ASSESSMENT", ParagraphStyle('ScoreHead', fontName='Helvetica-Bold', fontSize=7, textColor=colors.HexColor("#64748B"), alignment=1))],
        [Paragraph(f"<b>{authenticity_score}</b> <font size=9 color='#64748B'>/ 100</font>", ParagraphStyle('ScoreVal', fontName='Helvetica-Bold', fontSize=20, leading=22, textColor=colors.HexColor(class_text), alignment=1))],
        [Paragraph(f"<b>{classification}</b>", ParagraphStyle('ClassVal', fontName='Helvetica-Bold', fontSize=8, leading=9.5, textColor=colors.HexColor(class_text), alignment=1))],
        [Paragraph(f"<font size=6.5 color='#64748B'>Risk Index: <b>{risk_score}/100</b></font>", ParagraphStyle('SubRiskVal', fontName='Helvetica', fontSize=7, leading=8.5, textColor=colors.HexColor("#475569"), alignment=1))]
    ]
    score_table = Table(score_display, colWidths=[180])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(class_bg)),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor(class_text)),
    ]))
    
    summary_card_data = [[left_meta_table, score_table]]
    summary_card = Table(summary_card_data, colWidths=[340, 200])
    summary_card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor("#E2E8F0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(summary_card)
    story.append(Spacer(1, 8))
    
    # ---------------- 2b. MACHINE-READABLE QR ANALYSIS ----------------
    analysis = case.get('analysis', {})
    if isinstance(analysis, dict) and 'analysis_json' in analysis and isinstance(analysis['analysis_json'], dict):
        for k, v in analysis['analysis_json'].items():
            if k not in analysis:
                analysis[k] = v

    qr_data = analysis.get('qr', {}) if isinstance(analysis, dict) else {}
    if qr_data:
        story.append(Paragraph("MACHINE-READABLE CREDENTIAL & QR ANALYSIS", heading2_style))
        story.append(Spacer(1, 3))
        
        qr_status = str(qr_data.get('status', 'NOT_DETECTED'))
        qr_type = str(qr_data.get('payload_type', 'UNKNOWN'))
        qr_verif = qr_data.get('verification', {})
        verif_status = qr_verif.get('status', 'NOT_PERFORMED')
        
        if verif_status == 'NOT_PERFORMED':
            verif_display = "Cryptographic UIDAI verification not performed" if qr_type == "AADHAAR_SECURE_QR" else "Not performed"
        elif verif_status == 'SIGNATURE_VERIFIED':
            verif_display = f"Signature Verified ({qr_verif.get('authority', 'UIDAI')})"
        elif verif_status == 'SIGNATURE_INVALID':
            verif_display = "Signature Validation Failed"
        else:
            verif_display = str(verif_status)

        qr_rows = [
            [
                Paragraph("<b>QR STATUS:</b>", meta_head_style),
                Paragraph(f"<b>{qr_status}</b>", meta_val_style),
                Paragraph("<b>PAYLOAD TYPE:</b>", meta_head_style),
                Paragraph(f"<b>{qr_type}</b>", meta_val_style)
            ],
            [
                Paragraph("<b>VERIFICATION:</b>", meta_head_style),
                Paragraph(verif_display, meta_val_style),
                Paragraph("<b>OCR CROSS-CHECK:</b>", meta_head_style),
                Paragraph(str(qr_data.get('ocr_cross_check', {}).get('status', 'NOT_AVAILABLE')), meta_val_style)
            ]
        ]
        
        if qr_data.get('url'):
            url_str = str(qr_data.get('url'))
            url_short = url_str if len(url_str) <= 65 else url_str[:62] + "..."
            qr_rows.append([
                Paragraph("<b>QR LINK:</b>", meta_head_style),
                Paragraph(f"<font color='#0284C7'><u>{url_short}</u></font>", meta_val_style),
                Paragraph("<b>SAFE SCHEME:</b>", meta_head_style),
                Paragraph("Verified HTTP(S)" if qr_data.get('safe_url') else "Unsafe Protocol", meta_val_style)
            ])
        elif qr_data.get('data_preview') and qr_data.get('data_preview') != 'None':
            preview_str = str(qr_data.get('data_preview'))
            if len(preview_str) > 65:
                preview_str = preview_str[:62] + "..."
            qr_rows.append([
                Paragraph("<b>DATA PREVIEW:</b>", meta_head_style),
                Paragraph(preview_str, meta_val_style),
                Paragraph("<b>DETECTION COUNT:</b>", meta_head_style),
                Paragraph(str(qr_data.get('detected_count', 1)), meta_val_style)
            ])

        qr_table = Table(qr_rows, colWidths=[110, 190, 110, 130])
        qr_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor("#E2E8F0")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor("#F1F5F9")),
        ]))
        story.append(qr_table)
        story.append(Spacer(1, 8))

    # ---------------- 2c. DYNAMIC FORENSIC EVIDENCE TABLE (Section 22) ----------------
    aadhaar_profile = analysis.get('aadhaar_profile', {})
    ev_table_data = aadhaar_profile.get('evidence_table') or analysis.get('evidence_table') or []
    
    if ev_table_data:
        story.append(Paragraph("AADHAAR MULTI-EVIDENCE FORENSIC ASSESSMENT TABLE", heading2_style))
        story.append(Spacer(1, 3))
        
        dyn_rows = [[
            Paragraph("Evidence Element", table_head_style),
            Paragraph("Forensic Status", table_head_style),
            Paragraph("Impact Category", table_head_style)
        ]]
        
        for item in ev_table_data:
            ev_name = item.get("evidence", "Evidence")
            ev_stat = item.get("status", "Evaluated")
            ev_imp = item.get("impact", "Supporting")
            
            imp_color = "#15803D"
            if "Suspicious" in ev_imp:
                imp_color = "#B91C1C"
            elif "Neutral" in ev_imp or "Informational" in ev_imp:
                imp_color = "#64748B"
                
            dyn_rows.append([
                Paragraph(f"<b>{ev_name}</b>", table_cell_bold),
                Paragraph(ev_stat, table_cell_style),
                Paragraph(f"<font color='{imp_color}'><b>{ev_imp}</b></font>", table_cell_style)
            ])
            
        fet_table = Table(dyn_rows, colWidths=[130, 270, 140])
        fet_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ]))
        story.append(fet_table)
        story.append(Spacer(1, 8))

    # ---------------- 3. EVIDENCE LOG TABLE ----------------
    story.append(Paragraph("FORENSIC EVIDENCE & SIGNAL BREAKDOWN", heading2_style))
    story.append(Spacer(1, 4))
    
    evidence_list = analysis.get('evidence', []) if isinstance(analysis, dict) else []
    
    if evidence_list:
        table_data = [[
            Paragraph("ID", table_head_style),
            Paragraph("Category", table_head_style),
            Paragraph("Finding & Technical Observation", table_head_style),
            Paragraph("Severity", table_head_style),
            Paragraph("Risk Impact", table_head_style)
        ]]
        
        for ev in evidence_list:
            contrib = ev.get('risk_contribution', ev.get('score', 0))
            contrib_str = f"+{contrib}" if contrib > 0 else "0"
            severity = str(ev.get('severity', 'Info')).capitalize()
            
            # Severity color
            sev_color = "#0F172A"
            if severity.lower() == "high":
                sev_color = "#B91C1C"
            elif severity.lower() == "warning":
                sev_color = "#B45309"
            elif severity.lower() == "info":
                sev_color = "#0369A1"
                
            finding_text = ev.get('finding') or ev.get('title') or 'Signal evaluated.'
            
            table_data.append([
                Paragraph(str(ev.get('id', 'N/A')), table_cell_bold),
                Paragraph(str(ev.get('category', 'General')), table_cell_style),
                Paragraph(finding_text, table_cell_style),
                Paragraph(f"<font color='{sev_color}'><b>{severity}</b></font>", table_cell_style),
                Paragraph(f"<b>{contrib_str}</b>", table_cell_style)
            ])
            
        # Total colWidths sum = 50 + 75 + 280 + 70 + 65 = 540 pt (matches exact printable width)
        evidence_table = Table(table_data, colWidths=[45, 75, 290, 65, 65])
        evidence_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ]))
        story.append(evidence_table)
    else:
        story.append(Paragraph("No anomalous forensic evidence items detected.", meta_val_style))
        
    story.append(Spacer(1, 10))
    
    # ---------------- 4. COMPACT LEGAL DISCLAIMER ----------------
    disclaimer_text = (
        "<b>OFFICIAL DISCLAIMER:</b> SENTINEL is an automated computer-vision and signal-forensic decision-support system. "
        "SENTINEL performs forensic screening and does not replace official UIDAI authentication or authorized identity verification. "
        "Findings are calculated based on observable visual quality, OCR character confidence, machine-readable QR payloads, "
        "compression anomalies, and layout heuristics. This screening report does not constitute official legal authentication "
        "or replace designated statutory forensic verification procedures."
    )
    disclaimer_box = Table([[Paragraph(disclaimer_text, disclaimer_style)]], colWidths=[540])
    disclaimer_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(disclaimer_box)

    
    doc.build(story)
    
    return file_path
