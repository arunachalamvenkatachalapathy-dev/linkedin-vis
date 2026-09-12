import os
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

PAGE_WIDTH = 540
PAGE_HEIGHT = 675  # 4:5 portrait aspect ratio, optimal for LinkedIn mobile feed

BG_COLOR = HexColor("#0b1320")        # Deep midnight navy
CARD_BG = HexColor("#132238")         # Elevated card slate
ACCENT_COLOR = HexColor("#10b981")    # Emerald green
TEXT_MAIN = HexColor("#f8fafc")       # Bright off-white
TEXT_MUTED = HexColor("#94a3b8")      # Cool slate gray
LINE_COLOR = HexColor("#1e3a5f")      # Subtle divider

def wrap_text(text, max_chars=40):
    words = text.split()
    lines = []
    curr = []
    curr_len = 0
    for w in words:
        if curr_len + len(w) + 1 <= max_chars:
            curr.append(w)
            curr_len += len(w) + 1
        else:
            if curr:
                lines.append(" ".join(curr))
            curr = [w]
            curr_len = len(w)
    if curr:
        lines.append(" ".join(curr))
    return lines


def draw_slide_template(c, slide_num, total_slides, tag="ESG & SUSTAINABILITY INSIGHT"):
    # Background
    c.setFillColor(BG_COLOR)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    
    # Top pill tag
    c.setFillColor(CARD_BG)
    c.roundRect(36, PAGE_HEIGHT - 54, 210, 24, 6, fill=1, stroke=0)
    c.setFillColor(ACCENT_COLOR)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(46, PAGE_HEIGHT - 44, tag.upper())
    
    # Slide tracker on top right
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(PAGE_WIDTH - 36, PAGE_HEIGHT - 44, f"{slide_num} / {total_slides}")
    
    # Bottom footer brand
    c.setStrokeColor(LINE_COLOR)
    c.setLineWidth(1)
    c.line(36, 50, PAGE_WIDTH - 36, 50)
    
    c.setFillColor(TEXT_MAIN)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(36, 32, "Arunachalam Venkatachalapathy")
    
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", 8)
    c.drawString(36, 20, "ESG & Sustainability • BRSR Core • Climate Tech")
    
    # Swipe cue
    if slide_num < total_slides:
        c.setFillColor(ACCENT_COLOR)
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(PAGE_WIDTH - 36, 26, "SWIPE ➔")
    else:
        c.setFillColor(ACCENT_COLOR)
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(PAGE_WIDTH - 36, 26, "SHARE / SAVE 📌")


def generate_carousel_pdf(output_path, title, hook, slides_content):
    """
    slides_content: list of dicts:
    [
      {"heading": "1. THE REGULATORY MANDATE", "highlight": "...", "body": "..."},
      {"heading": "2. GROUND REALITY", "highlight": "...", "body": "..."},
      {"heading": "3. TACTICAL PLAYBOOK", "highlight": "...", "body": "..."},
      {"heading": "KEY TAKEAWAY", "highlight": "...", "body": "..."}
    ]
    """
    c = canvas.Canvas(output_path, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    total_slides = len(slides_content) + 1
    
    # --- SLIDE 1: COVER SLIDE ---
    draw_slide_template(c, 1, total_slides, "EXECUTIVE BRIEFING")
    
    # Large Title
    c.setFillColor(TEXT_MAIN)
    c.setFont("Helvetica-Bold", 24)
    title_lines = wrap_text(title, max_chars=30)
    y = PAGE_HEIGHT - 170
    for line in title_lines[:4]:
        c.drawString(36, y, line)
        y -= 32
    
    # Green accent line
    c.setFillColor(ACCENT_COLOR)
    c.rect(36, y - 10, 60, 4, fill=1, stroke=0)
    
    # Hook / Subtitle in elevated card
    y -= 45
    c.setFillColor(CARD_BG)
    c.roundRect(36, y - 110, PAGE_WIDTH - 72, 120, 10, fill=1, stroke=0)
    
    c.setFillColor(TEXT_MAIN)
    c.setFont("Helvetica", 12)
    hook_lines = wrap_text(hook, max_chars=44)
    text_y = y - 24
    for line in hook_lines[:4]:
        c.drawString(52, text_y, line)
        text_y -= 18
        
    c.setFillColor(ACCENT_COLOR)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(52, y - 96, "5-Minute Tactical Breakdown ➔")
    
    c.showPage()
    
    # --- CONTENT SLIDES ---
    for i, slide in enumerate(slides_content, start=2):
        draw_slide_template(c, i, total_slides, "TACTICAL DEEP DIVE")
        
        # Section Heading
        c.setFillColor(ACCENT_COLOR)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(36, PAGE_HEIGHT - 110, slide.get("heading", "").upper())
        
        # Main Box
        c.setFillColor(CARD_BG)
        c.roundRect(36, 90, PAGE_WIDTH - 72, PAGE_HEIGHT - 225, 12, fill=1, stroke=0)
        
        # Sub-heading or Key highlight
        highlight = slide.get("highlight", "")
        curr_y = PAGE_HEIGHT - 160
        if highlight:
            c.setFillColor(TEXT_MAIN)
            c.setFont("Helvetica-Bold", 15)
            h_lines = wrap_text(highlight, max_chars=34)
            for h in h_lines:
                c.drawString(56, curr_y, h)
                curr_y -= 22
            curr_y -= 14
        
        # Body text
        c.setFillColor(TEXT_MUTED)
        c.setFont("Helvetica", 11)
        body_lines = wrap_text(slide.get("body", ""), max_chars=42)
        for b in body_lines:
            if curr_y < 120:
                break
            c.drawString(56, curr_y, b)
            curr_y -= 18
            
        c.showPage()
        
    c.save()
    return output_path
