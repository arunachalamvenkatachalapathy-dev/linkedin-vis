from PIL import Image, ImageDraw, ImageFont
import textwrap
import os

def create_card(title, hook, output_path="card.png"):
    width = 1200
    height = 630
    img = Image.new('RGB', (width, height), color='#1E1E1E')
    draw = ImageDraw.Draw(img)
    
    # Try to load a font, otherwise use default
    try:
        title_font = ImageFont.truetype("arial.ttf", 60)
        hook_font = ImageFont.truetype("arial.ttf", 40)
        small_font = ImageFont.truetype("arial.ttf", 30)
    except IOError:
        # Fallback to default if no font found (can't specify size for load_default in older PIL, but just in case)
        try:
            title_font = ImageFont.load_default(size=60)
            hook_font = ImageFont.load_default(size=40)
            small_font = ImageFont.load_default(size=30)
        except Exception:
            title_font = ImageFont.load_default()
            hook_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
    margin = 80
    
    # Draw title
    wrapped_title = textwrap.fill(title, width=35)
    draw.text((margin, margin), wrapped_title, font=title_font, fill="#FFFFFF")
    
    # Draw hook at the bottom
    wrapped_hook = textwrap.fill(hook, width=50)
    draw.text((margin, height - 250), wrapped_hook, font=hook_font, fill="#4CAF50")
    
    # Draw tagline
    draw.text((margin, height - margin - 20), "EcoPulse Telemetry & ESG", font=small_font, fill="#888888")
    
    img.save(output_path)
    return output_path
