"""
Test script for the new Minimalist UI Charcoal & Yellow carousel generator
using League Spartan font ONLY.
"""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR = Path(r"C:\Users\NALINI ARUN\.gemini\antigravity\scratch\linkedin vis")
ASSETS_DIR = BASE_DIR / "assets"
BG_DIR = ASSETS_DIR / "backgrounds"
FONT_DIR = ASSETS_DIR / "fonts"
PROFILE_DIR = ASSETS_DIR / "profile"
OUTPUT_DIR = BASE_DIR / "test_output_carousel"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Canvas settings
CANVAS_SIZE = 1080
CARD_X = 110
CARD_Y = 110
CARD_W = 860
CARD_H = 860
CORNER_RADIUS = 36

# Colors matching the reference PDF exact hex: #FBEC9D
C_YELLOW = (251, 236, 157)       # #FBEC9D - Warm Buttery Yellow
C_YELLOW_DIM = (213, 207, 181)   # #D5CFB5
C_BODY = (251, 236, 157)         # Matching original PDF body text color (#FBEC9D)
C_DARK_CARD = (26, 26, 28, 220)  # Charcoal glass tint
C_CARD_BORDER = (251, 236, 157, 35)
C_DIVIDER = (251, 236, 157, 60)
C_SEARCH_BG = (235, 235, 235)
C_SEARCH_TEXT = (25, 25, 25)
C_SEARCH_BORDER = (200, 200, 200)

def get_font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    weight_map = {
        "thin": "LeagueSpartan-Thin.ttf",
        "light": "LeagueSpartan-Light.ttf",
        "regular": "LeagueSpartan-Regular.ttf",
        "medium": "LeagueSpartan-Medium.ttf",
        "semibold": "LeagueSpartan-SemiBold.ttf",
        "bold": "LeagueSpartan-Bold.ttf",
        "extrabold": "LeagueSpartan-ExtraBold.ttf",
        "black": "LeagueSpartan-Black.ttf",
    }
    font_file = weight_map.get(weight.lower(), "LeagueSpartan-Regular.ttf")
    font_path = FONT_DIR / font_file
    if not font_path.exists():
        font_path = FONT_DIR / "LeagueSpartan-Bold.ttf"
    return ImageFont.truetype(str(font_path), size)

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    lines = []
    paragraphs = text.split("\n")
    for para in paragraphs:
        if not para.strip():
            lines.append("")
            continue
        words = para.split()
        current_line = []
        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
    return lines

def create_frosted_card(bg_image: Image.Image) -> Image.Image:
    crop_box = (CARD_X, CARD_Y, CARD_X + CARD_W, CARD_Y + CARD_H)
    card_crop = bg_image.crop(crop_box)
    blurred = card_crop.filter(ImageFilter.GaussianBlur(radius=16))
    tint = Image.new("RGBA", (CARD_W, CARD_H), C_DARK_CARD)
    card_surface = Image.alpha_composite(blurred.convert("RGBA"), tint)
    
    mask = Image.new("L", (CARD_W, CARD_H), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle([(0, 0), (CARD_W, CARD_H)], radius=CORNER_RADIUS, fill=255)
    
    rounded_card = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    rounded_card.paste(card_surface, (0, 0), mask)
    
    draw_border = ImageDraw.Draw(rounded_card)
    draw_border.rounded_rectangle([(0, 0), (CARD_W - 1, CARD_H - 1)], radius=CORNER_RADIUS, outline=C_CARD_BORDER, width=1)
    return rounded_card

def draw_arrow(draw: ImageDraw.ImageDraw, x: int, y: int, length: int = 55, color = C_YELLOW, width: int = 3):
    draw.line([(x, y), (x + length, y)], fill=color, width=width)
    draw.line([(x + length - 14, y - 10), (x + length, y)], fill=color, width=width)
    draw.line([(x + length - 14, y + 10), (x + length, y)], fill=color, width=width)

def draw_window_dots(draw: ImageDraw.ImageDraw, start_x: int, y: int):
    dot_r = 7
    spacing = 22
    for i in range(3):
        dx = start_x + i * spacing
        draw.ellipse([(dx - dot_r, y - dot_r), (dx + dot_r, y + dot_r)], fill=C_YELLOW)

def render_slide(slide_data: dict, bg_path: Path) -> Image.Image:
    bg = Image.open(bg_path).convert("RGB")
    w, h = bg.size
    scale = max(CANVAS_SIZE / w, CANVAS_SIZE / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    bg_resized = bg.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - CANVAS_SIZE) // 2
    top = (new_h - CANVAS_SIZE) // 2
    bg_cropped = bg_resized.crop((left, top, left + CANVAS_SIZE, top + CANVAS_SIZE))
    
    card = create_frosted_card(bg_cropped)
    canvas = bg_cropped.convert("RGBA")
    canvas.paste(card, (CARD_X, CARD_Y), card)
    
    draw = ImageDraw.Draw(canvas)
    slide_type = slide_data.get("type", "content")
    
    inner_left = CARD_X + 55
    inner_right = CARD_X + CARD_W - 55
    max_content_w = inner_right - inner_left
    footer_y = CARD_Y + CARD_H - 85
    divider_y = footer_y - 25
    
    draw.line([(inner_left, divider_y), (inner_right, divider_y)], fill=C_DIVIDER, width=1)
    
    if slide_type == "cover":
        f_font = get_font(26, weight="bold")
        draw.text((inner_left, footer_y - 8), "Swipe to know more", font=f_font, fill=C_YELLOW)
        draw_arrow(draw, inner_right - 65, footer_y + 8, length=60, color=C_YELLOW, width=3)
    elif slide_type != "outro":
        draw_arrow(draw, inner_right - 65, footer_y + 8, length=60, color=C_YELLOW, width=3)

    if slide_type == "cover":
        # Subtitle badge - bigger
        sub_font = get_font(34, weight="bold")
        draw.text((inner_left, CARD_Y + 110), slide_data.get("badge", "Let's discuss"), font=sub_font, fill=C_YELLOW)
        
        # Main Title - BIGGER League Spartan Bold
        title_font = get_font(78, weight="bold")
        title_text = slide_data.get("title", "")
        title_lines = wrap_text(title_text, title_font, max_content_w, draw)
        
        cur_y = CARD_Y + 185
        for line in title_lines:
            draw.text((inner_left, cur_y), line, font=title_font, fill=C_YELLOW)
            cur_y += 92

    elif slide_type in ("content", "quote"):
        draw_window_dots(draw, inner_left + 8, CARD_Y + 55)
        
        # Section Title - BIGGER League Spartan Bold
        t_font = get_font(68, weight="bold")
        title_text = slide_data.get("title", "")
        title_lines = wrap_text(title_text, t_font, max_content_w, draw)
        
        cur_y = CARD_Y + 115
        for line in title_lines:
            draw.text((inner_left, cur_y), line, font=t_font, fill=C_YELLOW)
            cur_y += 80
            
        cur_y += 20
        
        # Body text - League Spartan Medium
        b_font = get_font(34, weight="medium")
        body_text = slide_data.get("body", "")
        body_lines = wrap_text(body_text, b_font, max_content_w, draw)
        for line in body_lines:
            draw.text((inner_left, cur_y), line, font=b_font, fill=C_BODY)
            cur_y += 50
            
        if slide_type == "quote" and slide_data.get("attribution"):
            cur_y += 20
            attr_font = get_font(28, weight="semibold")
            draw.text((inner_left, cur_y), f"— {slide_data['attribution']}", font=attr_font, fill=C_YELLOW_DIM)

    elif slide_type == "search_ui":
        draw_window_dots(draw, inner_left + 8, CARD_Y + 55)
        
        t_font = get_font(58, weight="bold")
        draw.text((inner_left, CARD_Y + 115), slide_data.get("title", "Key Strategic Actions"), font=t_font, fill=C_YELLOW)
        
        box_y = CARD_Y + 205
        box_w = max_content_w
        box_h = 360
        box_r = 18
        
        draw.rounded_rectangle([(inner_left, box_y), (inner_left + box_w, box_y + box_h)], radius=box_r, fill=C_SEARCH_BG, outline=C_SEARCH_BORDER, width=1)
        
        hdr_h = 70
        draw.line([(inner_left, box_y + hdr_h), (inner_left + box_w, box_y + hdr_h)], fill=(210, 210, 210), width=1)
        
        s_font = get_font(30, weight="bold")
        draw.text((inner_left + 25, box_y + 18), slide_data.get("search_label", "Strategic priorities"), font=s_font, fill=C_SEARCH_TEXT)
        sx = inner_left + box_w - 45
        sy = box_y + 35
        draw.ellipse([(sx - 9, sy - 9), (sx + 9, sy + 9)], outline=C_SEARCH_TEXT, width=3)
        draw.line([(sx + 7, sy + 7), (sx + 16, sy + 16)], fill=C_SEARCH_TEXT, width=3)
        
        items = slide_data.get("items", [])
        item_font = get_font(30, weight="semibold")
        item_y = box_y + hdr_h + 30
        for item in items:
            draw.text((inner_left + 25, item_y), f"•  {item}", font=item_font, fill=C_SEARCH_TEXT)
            item_y += 68

    elif slide_type == "outro":
        draw_window_dots(draw, inner_left + 8, CARD_Y + 55)
        
        prof_img_path = PROFILE_DIR / "profile.jpg"
        sig_img_path = PROFILE_DIR / "signature.png"
        
        cur_y = CARD_Y + 115
        
        if prof_img_path.exists():
            pimg = Image.open(prof_img_path).convert("RGB")
            p_size = 180
            pimg_res = pimg.resize((p_size, p_size), Image.Resampling.LANCZOS)
            
            p_mask = Image.new("L", (p_size, p_size), 0)
            p_draw = ImageDraw.Draw(p_mask)
            p_draw.ellipse([(0, 0), (p_size, p_size)], fill=255)
            
            ring = Image.new("RGBA", (p_size + 8, p_size + 8), (0, 0, 0, 0))
            r_draw = ImageDraw.Draw(ring)
            r_draw.ellipse([(0, 0), (p_size + 7, p_size + 7)], outline=C_YELLOW, width=3)
            
            canvas.paste(ring, (inner_left - 4, cur_y - 4), ring)
            canvas.paste(pimg_res, (inner_left, cur_y), p_mask)
            
            name_x = inner_left + p_size + 30
            n_font = get_font(38, weight="bold")
            d_font = get_font(24, weight="semibold")
            f_font = get_font(22, weight="regular")
            
            draw.text((name_x, cur_y + 20), "Arunachalam V.", font=n_font, fill=C_YELLOW)
            draw.text((name_x, cur_y + 75), "ESG & Sustainability Lead", font=d_font, fill=C_BODY)
            draw.text((name_x, cur_y + 115), "BRSR Core • GHG • Climate Tech", font=f_font, fill=C_YELLOW_DIM)
            
            cur_y += p_size + 35
        else:
            n_font = get_font(42, weight="bold")
            draw.text((inner_left, cur_y), "Arunachalam Venkatachalapathy", font=n_font, fill=C_YELLOW)
            cur_y += 65
            
        if sig_img_path.exists():
            sig = Image.open(sig_img_path).convert("RGBA")
            yellow_sig = Image.new("RGBA", sig.size, C_YELLOW)
            gray = sig.convert("L")
            inv_mask = gray.point(lambda p: 255 - p if p < 240 else 0)
            sig_w = 260
            scale = sig_w / sig.width
            sig_h = int(sig.height * scale)
            yellow_sig_res = yellow_sig.resize((sig_w, sig_h), Image.Resampling.LANCZOS)
            inv_mask_res = inv_mask.resize((sig_w, sig_h), Image.Resampling.LANCZOS)
            canvas.paste(yellow_sig_res, (inner_left, cur_y), inv_mask_res)
            cur_y += sig_h + 20
            
        bio_font = get_font(28, weight="medium")
        bio = (
            "Sharing engineering-first perspectives on industrial decarbonization, "
            "SEBI BRSR Core assurance, and practical Scope 1-3 GHG accounting.\n\n"
            "Follow for grounded analysis that cuts through corporate greenwash."
        )
        bio_lines = wrap_text(bio, bio_font, max_content_w, draw)
        for line in bio_lines:
            draw.text((inner_left, cur_y), line, font=bio_font, fill=C_BODY)
            cur_y += 42

    return canvas.convert("RGB")



def generate_carousel_pdf(*args, **kwargs) -> str:
    """
    Flexible signature supporting both:
      - generate_carousel_pdf(slides, output_path="post_carousel.pdf")
      - generate_carousel_pdf(pdf_name, title, hook, slides)
    """
    output_path = "post_carousel.pdf"
    slides = []

    if args:
        if isinstance(args[0], list):
            slides = args[0]
            if len(args) > 1 and isinstance(args[1], str):
                output_path = args[1]
        elif isinstance(args[0], str):
            output_path = args[0]
            if isinstance(args[-1], list):
                slides = args[-1]
    
    if "output_path" in kwargs:
        output_path = kwargs["output_path"]
    if "slides" in kwargs:
        slides = kwargs["slides"]

    bg_files = sorted(list(BG_DIR.glob("*.*"))) if BG_DIR.exists() else []
    formatted = []
    
    if slides:
        c = slides[0] if isinstance(slides[0], dict) else {"title": str(slides[0])}
        formatted.append({
            "type": "cover",
            "badge": c.get("tag", "Let's discuss"),
            "title": c.get("title", "Climate Tech & Decarbonization")
        })
        
        for s in slides[1:]:
            if not isinstance(s, dict):
                s = {"body": str(s)}
            bullets = s.get("bullets", [])
            if bullets and len(bullets) >= 2:
                formatted.append({
                    "type": "search_ui",
                    "title": s.get("title", "Key Strategic Actions"),
                    "search_label": "Operational priorities",
                    "items": bullets[:3]
                })
            elif s.get("is_quote") or "quote" in s.get("title", "").lower():
                formatted.append({
                    "type": "quote",
                    "title": s.get("title", ""),
                    "attribution": s.get("attribution", "Industry Analysis"),
                    "body": s.get("body", "")
                })
            else:
                body = s.get("body", "")
                if bullets:
                    body = "\n\n".join(bullets)
                formatted.append({
                    "type": "content",
                    "title": s.get("title", "Operational Context"),
                    "body": body
                })
                
    formatted.append({"type": "outro"})
    
    images = []
    for i, slide in enumerate(formatted):
        bg = bg_files[i % len(bg_files)] if bg_files else None
        img = render_slide(slide, bg)
        images.append(img)
        
    if images:
        images[0].save(output_path, save_all=True, append_images=images[1:], resolution=150)
        return output_path
    return ""
