import os
import json
import csv
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import cv2
import numpy as np
import qrcode

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
    
    {"id": "SYN-TEST-0006", "name": "TEST USER 06", "label": "REVIEW_REQUIRED", "condition": "blur", "desc": "Moderate optical blur"},
    {"id": "SYN-TEST-0007", "name": "TEST USER 07", "label": "REVIEW_REQUIRED", "condition": "spacing", "desc": "Layout spacing and vertical margin irregularities"},
    {"id": "SYN-TEST-0008", "name": "TEST USER 08", "label": "REVIEW_REQUIRED", "condition": "brightness", "desc": "Overexposed illumination variation"},
    
    {"id": "SYN-TEST-0009", "name": "TEST USER 09", "label": "HIGH_SUSPICION", "condition": "manipulated", "desc": "Pasted ID, font/color mismatch, and splice boundaries"},
    {"id": "SYN-TEST-0010", "name": "TEST USER 10", "label": "HIGH_SUSPICION", "condition": "heavy_artifacts", "desc": "Inconsistent typography, splice artifacts, and heavy compression"},
]

def generate_base_id_card():
    # Create a generic white card background
    img = Image.new('RGB', (800, 500), color=(242, 245, 249))
    draw = ImageDraw.Draw(img)
    
    # Add a blue header banner
    draw.rectangle([0, 0, 800, 80], fill=(41, 128, 185))
    
    # Fonts
    try:
        font_large = ImageFont.truetype("arial.ttf", 32)
        font_huge = ImageFont.truetype("arial.ttf", 42)
        font_med = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 15)
    except IOError:
        font_large = ImageFont.load_default()
        font_huge = ImageFont.load_default()
        font_med = ImageFont.load_default()
        font_small = ImageFont.load_default()
        
    draw.text((25, 22), "SYNTHETIC TEST DOCUMENT", fill=(255, 255, 255), font=font_large)
    
    return img, draw, font_large, font_huge, font_med, font_small

def add_profile_placeholder(draw):
    draw.rectangle([50, 120, 250, 370], fill=(210, 215, 220), outline=(160, 165, 170), width=2)
    draw.ellipse([110, 150, 190, 230], fill=(150, 155, 160))
    draw.ellipse([80, 240, 220, 370], fill=(150, 155, 160))

def generate_sample(item):
    img, draw, font_large, font_huge, font_med, font_small = generate_base_id_card()
    add_profile_placeholder(draw)
    
    # Base Layout positions
    name_x = 300
    name_y = 145
    id_x = 300
    id_y = 225
    status_y = 305
    
    # Condition: spacing variation
    if item['condition'] in ("spacing", "manipulated"):
        name_y += 28
        id_y -= 25
        id_x += 48 # intentional margin drift
        
    # Name Field
    draw.text((name_x, name_y - 22), "Full Name:", fill=(110, 110, 110), font=font_small)
    draw.text((name_x, name_y), item['name'], fill=(15, 15, 15), font=font_med)
    
    # Document ID Field
    draw.text((id_x, id_y - 22), "Document ID:", fill=(110, 110, 110), font=font_small)
    if item['condition'] in ("manipulated", "heavy_artifacts"):
        # Altered typography: distinct large font, blue ink, splice background patch
        draw.rectangle([id_x - 8, id_y - 6, id_x + 360, id_y + 44], fill=(255, 255, 225), outline=(210, 60, 60), width=2)
        draw.text((id_x, id_y), item['id'], fill=(0, 20, 190), font=font_huge)
    else:
        draw.text((id_x, id_y), item['id'], fill=(15, 15, 15), font=font_med)
        
    # Status Field
    draw.text((name_x, status_y - 22), "Screening Status:", fill=(110, 110, 110), font=font_small)
    draw.text((name_x, status_y), "ACTIVE VERIFIED", fill=(30, 130, 60), font=font_med)
    
    # Robust QR Generation
    # box_size=4, border=4 creates sharp modules with compliant 4-module quiet zone
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=4,
    )
    qr.add_data(f"SENTINEL-DEMO-{item['id']}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    
    # Paste QR code directly without destructive anti-aliasing
    img.paste(qr_img, (650, 350))

    # Condition-Specific Observable Image Modifications
    if item['condition'] == "blur":
        # Realistic optical blur that lowers Laplacian variance without wiping text
        img = img.filter(ImageFilter.GaussianBlur(radius=2.2))
        
    elif item['condition'] == "brightness":
        # Overexposed illumination
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.85)
        
    elif item['condition'] == "manipulated":
        # Draw subtle digital splice boundary rectangle around the ID field
        draw_manip = ImageDraw.Draw(img)
        draw_manip.rectangle([id_x - 12, id_y - 10, id_x + 370, id_y + 48], outline=(230, 40, 40), width=2)
        
    elif item['condition'] == "heavy_artifacts":
        # Draw finder pattern tamper mark on QR code corner so it damages decode
        draw_tamper = ImageDraw.Draw(img)
        draw_tamper.rectangle([650, 350, 695, 395], fill=(242, 245, 249))
        
        # Re-save with low JPEG quality to create genuine compression blocks, then reload
        temp_path = os.path.join(OUTPUT_DIR, "temp.jpg")
        img.save(temp_path, "JPEG", quality=15)
        img = Image.open(temp_path).copy()
        try:
            os.remove(temp_path)
        except OSError:
            pass

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
            print(f"Generating {item['id']} ({item['condition']})...")
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
        
    print(f"Dataset generation complete. 10 files created in {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
