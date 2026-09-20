import os
import glob

# The script to inject right after <head>
theme_script = """<script>
        (function(){
            var theme = localStorage.getItem('sentinel_theme') || 'dark';
            document.documentElement.setAttribute('data-theme', theme);
        })();
    </script>"""

# Find all HTML files in frontend
html_files = glob.glob('frontend/*.html')

for file_path in html_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # If it's already there, skip
    if "sentinel_theme" in content and "document.documentElement.setAttribute" in content:
        continue
    
    # Inject after <head>
    if "<head>" in content:
        content = content.replace("<head>", f"<head>\n    {theme_script}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Injected into {file_path}")
    else:
        print(f"No <head> tag found in {file_path}")

print("Done.")
