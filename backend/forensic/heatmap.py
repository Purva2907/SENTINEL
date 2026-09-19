import cv2
import numpy as np
import base64

def generate_heatmap(image_path: str, evidence: list) -> str:
    """
    Generates a heatmap overlay based on evidence regions.
    Returns a base64 encoded string of the image.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return ""
            
        overlay = img.copy()
        output = img.copy()
        
        # Draw regions from evidence if available
        # In a real implementation, regions would come from models
        # For the demo fallback, we generate a synthetic heatmap
        
        height, width, _ = img.shape
        heatmap = np.zeros((height, width), dtype=np.uint8)
        
        has_high_risk = any(e.get("severity") == "High" for e in evidence)
        
        if has_high_risk:
            # Draw a synthetic hotspot for demonstration
            center = (width // 2, height // 3)
            cv2.circle(heatmap, center, min(width, height) // 4, 255, -1)
            heatmap = cv2.GaussianBlur(heatmap, (99, 99), 0)
            
            # Apply colormap
            colored_heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
            
            # Blend
            alpha = 0.4
            cv2.addWeighted(colored_heatmap, alpha, output, 1 - alpha, 0, output)
            
        # Encode to base64
        _, buffer = cv2.imencode('.jpg', output)
        base64_str = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_str}"
        
    except Exception as e:
        print(f"Heatmap error: {e}")
        return ""
