def generate_fallback_response(query: str, analysis_context: dict) -> str:
    """
    Local rule-based fallback if LLM is unavailable.
    """
    query_lower = query.lower()
    
    if "why" in query_lower and "flag" in query_lower:
        evidence = analysis_context.get("evidence", [])
        if evidence:
            highest = max(evidence, key=lambda x: x.get("score", 0))
            return f"The strongest indicator is: {highest.get('title')}. {highest.get('explanation')}"
        return "The document was analyzed based on quality, layout, and visual consistency."
        
    if "qr" in query_lower:
        qr = analysis_context.get("qr", {})
        if qr.get("detected"):
            return f"A QR code was detected and its consistency is marked as {qr.get('consistency')}."
        return "No valid QR code was detected on this document."
        
    if "quality" in query_lower:
        qual = analysis_context.get("quality", {})
        return f"The image quality score is {qual.get('score', 0)}/100. Findings: {', '.join(qual.get('findings', []))}"
        
    if "risk" in query_lower or "score" in query_lower:
        return f"The risk score is {analysis_context.get('risk_score')}/100, which classifies it as {analysis_context.get('classification')}."
        
    if "check" in query_lower or "review" in query_lower:
        return "An investigator should manually review the high-severity evidence items and verify the physical document if possible."
        
    return "I am the SENTINEL AI Fallback. I can explain the risk score, QR analysis, image quality, and specific evidence found in this case."
