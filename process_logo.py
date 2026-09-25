import os
from PIL import Image
import numpy as np

src_path = r'C:\Users\RAM\.gemini\antigravity-ide\brain\6be9cbc7-18e3-47b4-9cad-f15be2c87903\.user_uploaded\media_1790357461701.png'
assets_dir = r'd:\WORK & CODING\WORKSTATION\HACKATHON WORKSPACE\SENTINEL-MUSA\frontend\assets'
os.makedirs(assets_dir, exist_ok=True)

im_raw = Image.open(src_path).convert('RGBA')
arr = np.array(im_raw, dtype=np.float32)

# Unmult transparency processing
rgb = arr[:, :, :3]
max_c = np.max(rgb, axis=2)

# Clean alpha curve
alpha = np.clip(max_c / 255.0, 0, 1.0)
# Smooth threshold out low background noise
alpha = np.where(max_c < 6, 0.0, alpha)

safe_alpha = np.where(alpha > 0.01, alpha, 1.0)[:, :, np.newaxis]
rgb_unmult = np.clip(rgb / safe_alpha, 0, 255)

out_dark = np.zeros_like(arr)
out_dark[:, :, :3] = rgb_unmult
out_dark[:, :, 3] = alpha * 255.0
im_dark_full = Image.fromarray(out_dark.astype(np.uint8))

# 1. Full Logo (Dark Mode)
# Content bounds: X: 206 to 840, Y: 267 to 698
pad = 20
box_full = (206 - pad, 267 - pad, 840 + pad, 698 + pad)
im_logo_dark = im_dark_full.crop(box_full)
im_logo_dark.save(os.path.join(assets_dir, 'sentinel-logo.png'), 'PNG')
print("Saved sentinel-logo.png", im_logo_dark.size)

# 2. Compact S Mark (Dark Mode)
# Emblem bounds: X: 389 to 635, Y: 267 to 576 (width 246, height 309)
# Center into a square with proportional padding
cx = (389 + 635) // 2
cy = (267 + 576) // 2
half_size = int(max(635 - 389, 576 - 267) * 0.58)
box_mark = (cx - half_size, cy - half_size, cx + half_size, cy + half_size)
im_mark_dark = im_dark_full.crop(box_mark)
im_mark_dark.save(os.path.join(assets_dir, 'sentinel-mark.png'), 'PNG')
print("Saved sentinel-mark.png", im_mark_dark.size)

# 3. Horizontal Lockup (Dark Mode)
# [S Mark] [SENTINEL wordmark] on a single row
# Extract S emblem tightly
im_emblem_tight = im_dark_full.crop((385, 263, 639, 580))
# Extract Text tightly
im_text_tight = im_dark_full.crop((200, 645, 846, 702))

# Scale emblem to height ~ 80px, text to proportional height ~ 40px
target_h = 100
emblem_scale = target_h / im_emblem_tight.height
emblem_w = int(im_emblem_tight.width * emblem_scale)
emblem_resized = im_emblem_tight.resize((emblem_w, target_h), Image.Resampling.LANCZOS)

# Text scaling
text_scale = (target_h * 0.44) / im_text_tight.height
text_w = int(im_text_tight.width * text_scale)
text_h = int(im_text_tight.height * text_scale)
text_resized = im_text_tight.resize((text_w, text_h), Image.Resampling.LANCZOS)

spacing = 24
horiz_w = emblem_w + spacing + text_w + 20
horiz_h = target_h + 10
im_horiz_dark = Image.new('RGBA', (horiz_w, horiz_h), (0, 0, 0, 0))
im_horiz_dark.paste(emblem_resized, (10, 5), emblem_resized)
text_y = (horiz_h - text_h) // 2
im_horiz_dark.paste(text_resized, (10 + emblem_w + spacing, text_y), text_resized)
im_horiz_dark.save(os.path.join(assets_dir, 'sentinel-logo-horizontal.png'), 'PNG')
print("Saved sentinel-logo-horizontal.png", im_horiz_dark.size)

# 4. Light Mode Variants (Dark Navy / Blue gradient)
# Transform RGB to deep navy/cyan tones for light mode readability
def make_light_variant(img):
    arr_in = np.array(img, dtype=np.float32)
    alpha_ch = arr_in[:, :, 3]
    rgb_ch = arr_in[:, :, :3]
    
    # Calculate luminance
    lum = (0.299 * rgb_ch[:, :, 0] + 0.587 * rgb_ch[:, :, 1] + 0.114 * rgb_ch[:, :, 2]) / 255.0
    
    # Map high luminance (whites/light icy blues) to deep navy/dark slate,
    # and cyan highlights to rich blue (#0284c7 / #0369a1)
    # Target palette: Dark navy #0a1128 (10, 17, 40) to steel blue #0284c7 (2, 132, 199)
    # Invert luminance relationship for dark-on-light contrast
    inverted_lum = 1.0 - lum * 0.85
    
    r_light = np.clip(10 + (1 - inverted_lum) * 20 + rgb_ch[:, :, 0] * 0.05, 0, 255)
    g_light = np.clip(25 + (1 - inverted_lum) * 90 + rgb_ch[:, :, 1] * 0.35, 0, 255)
    b_light = np.clip(60 + (1 - inverted_lum) * 140 + rgb_ch[:, :, 2] * 0.45, 0, 255)
    
    # For text areas where it was white: make it deep crisp navy (#0f172a)
    out_arr = np.zeros_like(arr_in)
    out_arr[:, :, 0] = r_light
    out_arr[:, :, 1] = g_light
    out_arr[:, :, 2] = b_light
    out_arr[:, :, 3] = alpha_ch
    return Image.fromarray(out_arr.astype(np.uint8))

im_logo_light = make_light_variant(im_logo_dark)
im_logo_light.save(os.path.join(assets_dir, 'sentinel-logo-light.png'), 'PNG')
print("Saved sentinel-logo-light.png")

im_mark_light = make_light_variant(im_mark_dark)
im_mark_light.save(os.path.join(assets_dir, 'sentinel-mark-light.png'), 'PNG')
print("Saved sentinel-mark-light.png")

im_horiz_light = make_light_variant(im_horiz_dark)
im_horiz_light.save(os.path.join(assets_dir, 'sentinel-logo-horizontal-light.png'), 'PNG')
print("Saved sentinel-logo-horizontal-light.png")

# 5. Favicons
im_mark_dark.resize((64, 64), Image.Resampling.LANCZOS).save(os.path.join(assets_dir, 'favicon.ico'), format='ICO')
im_mark_dark.resize((64, 64), Image.Resampling.LANCZOS).save(os.path.join(r'd:\WORK & CODING\WORKSTATION\HACKATHON WORKSPACE\SENTINEL-MUSA\frontend', 'favicon.ico'), format='ICO')
im_mark_dark.resize((64, 64), Image.Resampling.LANCZOS).save(os.path.join(r'd:\WORK & CODING\WORKSTATION\HACKATHON WORKSPACE\SENTINEL-MUSA', 'favicon.ico'), format='ICO')

im_mark_dark.resize((32, 32), Image.Resampling.LANCZOS).save(os.path.join(assets_dir, 'favicon-32x32.png'), 'PNG')
im_mark_dark.resize((16, 16), Image.Resampling.LANCZOS).save(os.path.join(assets_dir, 'favicon-16x16.png'), 'PNG')
print("Saved all favicons successfully!")
