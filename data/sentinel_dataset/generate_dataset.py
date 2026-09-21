import os
import json
import csv
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import cv2
import numpy as np

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")
METADATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metadata.json")
LABELS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "labels.csv")

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Dataset configuration: 5 Authentic, 3 Review, 2 High Suspicion
DATASET_CONFIG = [
    {"id": "SYN-TEST-0001", "name": "TEST USER 01", "label": "LIKELY_AUTHENTIC", "condition": "clean", "desc": "Clean synthetic document"},
    {"id": "SYN-TEST-0002", "name": "TEST USER 02", "label": "LIKELY_AUTHENTIC", "condition": "clean", "desc": "Clean synthetic document"},
    {"id": "SYN-TEST-0003", "name": "TEST USER 03", "label": "LIKELY_AUTHENTIC", "condition": "clean", "desc": "Clean synthetic document"},
    {"id": "SYN-TEST-0004", "name": "TEST USER 04", "label": "LIKELY_AUTHENTIC", "condition": "clean", "desc": "Clean synthetic document"},
    {"id": "SYN-TEST-0005", "name": "TEST USER 05", "label": "LIKELY_AUTHENTIC", "condition": "clean", "desc": "Clean synthetic document"},
    
    {"id": "SYN-TEST-0006", "name": "TEST USER 06", "label": "REVIEW_REQUIRED", "condition": "blur", "desc": "Moderate blur and jpeg compression"},
    {"id": "SYN-TEST-0007", "name": "TEST USER 07", "label": "REVIEW_REQUIRED", "condition": "spacing", "desc": "Small spacing inconsistencies"},
    {"id": "SYN-TEST-0008", "name": "TEST USER 08", "label": "REVIEW_REQUIRED", "condition": "brightness", "desc": "Overexposed brightness variation"},
    
    {"id": "SYN-TEST-0009", "name": "TEST USER 09", "label": "HIGH_SUSPICION", "condition": "manipulated", "desc": "Obvious spacing and visual region manipulation"},
    {"id": "SYN-TEST-0010", "name": "TEST USER 10", "label": "HIGH_SUSPICION", "condition": "heavy_artifacts", "desc": "Inconsistent typography and strong compression"},
]

def generate_base_id_card():
    # Create a generic white card background
    img = Image.new('RGB', (800, 500), color=(240, 245, 250))
    draw = ImageDraw.Draw(img)
    
    # Add a blue header banner
    draw.rectangle([0, 0, 800, 80], fill=(41, 128, 185))
    
    # Header Text
    try:
        font_large = ImageFont.truetype("arial.ttf", 36)
        font_med = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except IOError:
        font_large = ImageFont.load_default()
        font_med = ImageFont.load_default()
        font_small = ImageFont.load_default()
        
    draw.text((20, 20), "SYNTHETIC TEST DOCUMENT", fill=(255, 255, 255), font=font_large)
    
    return img, draw, font_large, font_med, font_small

def add_profile_placeholder(draw):
    draw.rectangle([50, 120, 250, 370], fill=(200, 200, 200), outline=(150,150,150), width=2)
    # Draw simple person icon
    draw.ellipse([110, 150, 190, 230], fill=(150, 150, 150))
    draw.ellipse([80, 240, 220, 370], fill=(150, 150, 150))

def generate_sample(item):
    img, draw, font_large, font_med, font_small = generate_base_id_card()
    add_profile_placeholder(draw)
    
    # Base Layout
    name_x = 300
    name_y = 150
    id_y = 220
    status_y = 290
    qr_y = 360
    
    if item['condition'] == "spacing" or item['condition'] == "manipulated":
        name_y += 15 # inconsistent layout
        id_y -= 10
        
    # Name
    draw.text((name_x, name_y - 25), "Name:", fill=(100, 100, 100), font=font_small)
    draw.text((name_x, name_y), item['name'], fill=(0, 0, 0), font=font_med)
    
    # ID
    draw.text((name_x, id_y - 25), "Document ID:", fill=(100, 100, 100), font=font_small)
    # If manipulated, make typography inconsistent (simulate pasted ID)
    if item['condition'] == "manipulated" or item['condition'] == "heavy_artifacts":
        draw.text((name_x, id_y), item['id'], fill=(0, 0, 150), font=font_large) # different color and font
        # Add visual splice line
        draw.line((name_x-10, id_y-5, name_x+300, id_y-5), fill=(200,200,200), width=2)
    else:
        draw.text((name_x, id_y), item['id'], fill=(0, 0, 0), font=font_med)
        
    # Status
    draw.text((name_x, status_y - 25), "Status:", fill=(100, 100, 100), font=font_small)
    draw.text((name_x, status_y), "DEMO DATA", fill=(200, 50, 50), font=font_med)
    
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=3,
            border=1,
        )
        qr.add_data(f"SENTINEL-DEMO-{item['id']}")
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").resize((100, 100))
        img.paste(qr_img, (650, 350))
    except ImportError:
        draw.rectangle([650, 350, 750, 450], fill=(0,0,0))
        draw.rectangle([660, 360, 740, 440], fill=(255,255,255))
        draw.rectangle([670, 370, 730, 430], fill=(0,0,0))
        draw.text((name_x, qr_y), f"QR_PAYLOAD: SENTINEL-DEMO-{item['id'][-4:]}", fill=(0, 0, 0), font=font_small)

    # Post processing for variations
    if item['condition'] == "blur":
        img = img.filter(ImageFilter.GaussianBlur(radius=2))
        
    if item['condition'] == "brightness":
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.6)
        
    if item['condition'] == "heavy_artifacts":
        # Save low quality jpeg then reload
        temp_path = os.path.join(OUTPUT_DIR, "temp.jpg")
        img.save(temp_path, "JPEG", quality=10)
        img = Image.open(temp_path)
        
    if item['condition'] == "manipulated":
        # Add random noise block
        draw = ImageDraw.Draw(img)
        draw.rectangle([300, 200, 600, 250], outline=(255,0,0), width=1) # ELA will pick up sharp edges here

    filename = f"{item['id']}.jpg"
    filepath = os.path.join(OUTPUT_DIR, filename)
    img.save(filepath, "JPEG", quality=95)
    return filename

def main():
    metadata = []
    
    with open(LABELS_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['filename', 'synthetic_id', 'label'])
        
        for item in DATASET_CONFIG:
            print(f"Generating {item['id']}...")
            filename = generate_sample(item)
            
            writer.writerow([filename, item['id'], item['label']])
            
            metadata.append({
                "filename": filename,
                "synthetic_id": item['id'],
                "label": item['label'],
                "generation_parameters": {
                    "condition": item['condition']
                },
                "description": item['desc']
            })
            
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=4)
        
    # Clean up temp file if exists
    if os.path.exists(os.path.join(OUTPUT_DIR, "temp.jpg")):
        os.remove(os.path.join(OUTPUT_DIR, "temp.jpg"))
        
    print("Dataset generation complete. 10 files created in documents/")

if __name__ == "__main__":
    main()
