import json

def generate_fallback_response(query: str, ctx: dict) -> str:
    """
    Local rule-based fallback if LLM is unavailable.
    Genuinely context-aware based on the SENTINEL context dict.
    """
    query_lower = query.lower()
    
    if not ctx:
        return "I don't have an active forensic result to analyze yet. Upload a document or open a case first."
        
    if "why" in query_lower or "flag" in query_lower or "strongest" in query_lower or "evidence" in query_lower:
        evidence = ctx.get("evidence", [])
        if evidence:
            # Find the evidence with the highest risk contribution
            highest = max(evidence, key=lambda x: x.get("risk_contribution", 0))
            return f"Based on the analysis, the strongest indicator is '{highest.get('title')}'. {highest.get('finding')}"
        return "The document was analyzed based on quality, layout, and visual consistency, but no specific high-risk evidence flags were triggered."
        
    if "qr" in query_lower:
        qr = ctx.get("qr", {})
        if qr.get("detected"):
            return f"A QR code was detected. Its consistency check resulted in: {qr.get('consistency')}. Note that QR decoding alone does not establish official authenticity."
        return "No valid QR code was detected on this document."
        
    if "quality" in query_lower or "blur" in query_lower or "resolution" in query_lower:
        qual = ctx.get("quality", {})
        findings = qual.get('findings', [])
        score = qual.get('score', 'N/A')
        if findings:
            return f"The image quality score is {score}/100. Findings: {', '.join(findings)}."
        return f"The image quality score is {score}/100 with no major negative findings."
        
    if "risk" in query_lower or "score" in query_lower:
        risk = ctx.get('risk_score', 'N/A')
        cls = ctx.get('classification', 'N/A')
        return f"The risk score is {risk}/100, which classifies this document as '{cls}' based on our forensic screening."
        
    if "ocr" in query_lower or "text" in query_lower:
        ocr = ctx.get("ocr", {})
        if ocr.get("success"):
            conf = ocr.get("average_confidence", 0) * 100
            return f"OCR successfully extracted text with an average confidence of {conf:.1f}%. The layout and typography signals contribute to the overall score."
        return "OCR failed to extract meaningful text from this document."

    if "check" in query_lower or "review" in query_lower or "manual" in query_lower:
        rec = ctx.get("recommendation", "")
        if rec:
            return f"Recommendation: {rec}. You should manually verify any highlighted suspicious signals against the physical document."
        return "An investigator should manually review the high-severity evidence items and verify the physical document if possible."
        
    if "summarize" in query_lower or "case" in query_lower:
        cls = ctx.get('classification', 'Unknown')
        risk = ctx.get('risk_score', 'Unknown')
        title = ctx.get('case_title', 'this document')
        return f"This is a summary for {title}. The forensic screening resulted in a '{cls}' classification with a risk score of {risk}/100. Please review the specific evidence flags for details."
        
    return "I am the SENTINEL AI Fallback. I can explain the risk score, QR analysis, image quality, OCR findings, and specific evidence found in this case. Please ask a specific question about the analysis."
