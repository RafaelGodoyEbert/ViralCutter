
import os
import re
import subprocess
import gradio as gr
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKING_DIR = os.path.dirname(CURRENT_DIR) # ViralCutter root
import sys
sys.path.append(WORKING_DIR)
from i18n.i18n import I18nAuto
i18n = I18nAuto()

# Subtitle Presets
SUBTITLE_PRESETS = {

    "MrBeast Clean Hook": {
        "font_name": "Montserrat-ExtraBold",
        "font_size": 32,
        "base_color": "#FFFFFF",
        "highlight_color": "#FFD700",
        "outline_color": "#000000",
        "outline_thickness": 3,
        "shadow_color": "#000000",
        "shadow_size": 2,
        "bold": True,
        "italic": False,
        "uppercase": True,
        "highlight_size": 38,
        "words_per_block": 1,
        "gap_limit": 0.25,
        "mode": "highlight",
        "underline": False,
        "strikeout": False,
        "border_style": 1,
        "vertical_position": 180,
        "alignment": 2
    },

    "Hormozi (Classic)": {
        "font_name": "Montserrat-ExtraBold",
        "font_size": 30,
        "base_color": "#FFFFFF",
        "highlight_color": "#00FF00",
        "outline_color": "#000000",
        "outline_thickness": 3,
        "shadow_color": "#000000",
        "shadow_size": 0,
        "bold": True,
        "italic": False,
        "uppercase": True,
        "highlight_size": 35,
        "words_per_block": 2,
        "gap_limit": 0.5,
        "mode": "highlight",
        "underline": False,
        "strikeout": False,
        "border_style": 1,
        "vertical_position": 200,
        "alignment": 2
    },

    "Beasty (Loud)": {
        "font_name": "Arial",
        "font_size": 34,
        "base_color": "#FFFFFF",
        "highlight_color": "#FF0000",
        "outline_color": "#000000",
        "outline_thickness": 3,
        "shadow_color": "#000000",
        "shadow_size": 3,
        "bold": True,
        "italic": False,
        "uppercase": True,
        "highlight_size": 40,
        "words_per_block": 1,
        "gap_limit": 0.4,
        "mode": "highlight",
        "underline": False,
        "strikeout": False,
        "border_style": 1,
        "vertical_position": 190,
        "alignment": 2
    },

    "Word Killer (TikTok)": {
        "font_name": "Impact",
        "font_size": 38,
        "base_color": "#FFFFFF",
        "highlight_color": "#FF0000",
        "outline_color": "#000000",
        "outline_thickness": 3,
        "shadow_color": "#000000",
        "shadow_size": 3,
        "bold": True,
        "italic": False,
        "uppercase": True,
        "highlight_size": 45,
        "words_per_block": 1,
        "gap_limit": 0.2,
        "mode": "word_by_word",
        "underline": False,
        "strikeout": False,
        "border_style": 1,
        "vertical_position": 210,
        "alignment": 2
    },

    "Rapid Fire (Sprint)": {
        "font_name": "Impact",
        "font_size": 36,
        "base_color": "#FFFFFF",
        "highlight_color": "#FFFF00",
        "outline_color": "#000000",
        "outline_thickness": 2,
        "shadow_color": "#000000",
        "shadow_size": 2,
        "bold": True,
        "italic": True,
        "uppercase": True,
        "highlight_size": 42,
        "words_per_block": 1,
        "gap_limit": 0.3,
        "mode": "word_by_word",
        "underline": False,
        "strikeout": False,
        "border_style": 1,
        "vertical_position": 210,
        "alignment": 2
    },

    "Educational Fast": {
        "font_name": "Roboto-Bold",
        "font_size": 28,
        "base_color": "#FFFFFF",
        "highlight_color": "#00BFFF",
        "outline_color": "#000000",
        "outline_thickness": 2,
        "shadow_color": "#000000",
        "shadow_size": 1,
        "bold": True,
        "italic": False,
        "uppercase": False,
        "highlight_size": 34,
        "words_per_block": 3,
        "gap_limit": 0.45,
        "mode": "highlight",
        "underline": False,
        "strikeout": False,
        "border_style": 1,
        "vertical_position": 220,
        "alignment": 2
    },

    "Podcast Viral (Centered)": {
        "font_name": "Arial",
        "font_size": 26,
        "base_color": "#FFFFFF",
        "highlight_color": "#00FFAA",
        "outline_color": "#000000",
        "outline_thickness": 2,
        "shadow_color": "#000000",
        "shadow_size": 1,
        "bold": True,
        "italic": False,
        "uppercase": False,
        "highlight_size": 30,
        "words_per_block": 4,
        "gap_limit": 0.55,
        "mode": "highlight",
        "underline": False,
        "strikeout": False,
        "border_style": 1,
        "vertical_position": 240,
        "alignment": 2
    },

    "Drama Emocional": {
        "font_name": "Arial",
        "font_size": 28,
        "base_color": "#EAEAEA",
        "highlight_color": "#FF5555",
        "outline_color": "#000000",
        "outline_thickness": 2,
        "shadow_color": "#000000",
        "shadow_size": 2,
        "bold": True,
        "italic": False,
        "uppercase": False,
        "highlight_size": 34,
        "words_per_block": 2,
        "gap_limit": 0.6,
        "mode": "highlight",
        "underline": False,
        "strikeout": False,
        "border_style": 1,
        "vertical_position": 235,
        "alignment": 2
    },

    "Story Subtitle (Netflix Style)": {
        "font_name": "Arial",
        "font_size": 24,
        "base_color": "#FFFFFF",
        "highlight_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_thickness": 0,
        "shadow_color": "#000000",
        "shadow_size": 0,
        "bold": True,
        "italic": False,
        "uppercase": False,
        "highlight_size": 24,
        "words_per_block": 7,
        "gap_limit": 0.7,
        "mode": "no_highlight",
        "underline": False,
        "strikeout": False,
        "border_style": 3,
        "vertical_position": 250,
        "alignment": 2
    },

    "Neon Cyber": {
        "font_name": "Arial",
        "font_size": 30,
        "base_color": "#FF00FF",
        "highlight_color": "#00FFFF",
        "outline_color": "#FFFFFF",
        "outline_thickness": 1,
        "shadow_color": "#000000",
        "shadow_size": 3,
        "bold": True,
        "italic": False,
        "uppercase": True,
        "highlight_size": 36,
        "words_per_block": 2,
        "gap_limit": 0.5,
        "mode": "highlight",
        "underline": True,
        "strikeout": False,
        "border_style": 1,
        "vertical_position": 205,
        "alignment": 2
    },

    "Retro Pixel": {
        "font_name": "Consolas",
        "font_size": 26,
        "base_color": "#00FF00",
        "highlight_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_thickness": 2,
        "shadow_color": "#000000",
        "shadow_size": 0,
        "bold": False,
        "italic": False,
        "uppercase": True,
        "highlight_size": 26,
        "words_per_block": 3,
        "gap_limit": 0.5,
        "mode": "word_by_word",
        "underline": False,
        "strikeout": False,
        "border_style": 3,
        "vertical_position": 215,
        "alignment": 2
    }
}

def generate_preview_html(font, size, color, highlight, outline, outline_thick, shadow, shadow_sz, bold, italic, upper, 
                          h_size, w_block, gap, mode, under, strike, border_s, vert_pos, align):
    weight = "bold" if bold else "normal"
    style = "italic" if italic else "normal"
    transform = "uppercase" if upper else "none"
    decorations = []
    if under: decorations.append("underline")
    if strike: decorations.append("line-through")
    decoration = " ".join(decorations) if decorations else "none"
    
    # Force larger preview size regardless of input size
    # We maintain ratio between highlight and base
    base_preview_px = 40
    ratio = 1.0
    if size > 0:
        ratio = h_size / size
    highlight_preview_px = base_preview_px * ratio
    
    # Avoid extreme ratios in preview
    if highlight_preview_px > base_preview_px * 2: highlight_preview_px = base_preview_px * 2
    
    # Border Style 3 is Opaque Box usually in ASS, here we can simulate background
    bg_style = "background-color: rgba(0,0,0,0.6); padding: 5px 10px; border-radius: 4px;" if border_s == 3 else ""
    
    # Handle Content based on Mode
    # Handle Content based on Mode
    content_html = ""
    preview_word = i18n("PREVIEW")
    if mode == "word_by_word":
        # Only show the active word
        content_html = f'<span style="font-size: {highlight_preview_px}px; color: {highlight}; -webkit-text-stroke: {outline_thick}px {outline};">{preview_word}</span>'
    elif mode == "no_highlight":
         # No highlight difference
         span_html = f'<span style="font-size: {base_preview_px}px; color: {color}; -webkit-text-stroke: {outline_thick}px {outline};">{preview_word}</span>'
         content_html = i18n("This is a {} of your subtitles").format(span_html)
    else:
        # Default Highlight mode
        span_html = f'<span style="font-size: {highlight_preview_px}px; color: {highlight}; -webkit-text-stroke: {outline_thick}px {outline};">{preview_word}</span>'
        content_html = i18n("This is a {} of your subtitles").format(span_html)

    html = f"""
    <div style="
        background-color: #222; 
        background-image: linear-gradient(45deg, #2a2a2a 25%, transparent 25%, transparent 75%, #2a2a2a 75%, #2a2a2a), 
                          linear-gradient(45deg, #2a2a2a 25%, transparent 25%, transparent 75%, #2a2a2a 75%, #2a2a2a);
        background-size: 20px 20px;
        background-position: 0 0, 10px 10px;
        padding: 40px; 
        border-radius: 8px; 
        text-align: center; 
        font-family: '{font}', sans-serif;
        margin-bottom: 10px;
        border: 1px solid #444;
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 120px;
    ">
        <span style="
            font-size: {base_preview_px}px;
            color: {color};
            font-weight: {weight};
            font-style: {style};
            text-transform: {transform};
            text-decoration: {decoration};
            -webkit-text-stroke: {outline_thick}px {outline};
            text-shadow: {shadow_sz}px {shadow_sz}px 0 {shadow};
            {bg_style}
            line-height: 1.2;
        ">
            {content_html}
        </span>
    </div>
    """
    return html

def apply_preset(preset):
    if preset in SUBTITLE_PRESETS:
        p = SUBTITLE_PRESETS[preset]
        return (
            p["font_name"], p["font_size"], p["base_color"], p["highlight_color"], 
            p["outline_color"], p["outline_thickness"], p["shadow_color"], 
            p["shadow_size"], p["bold"], p["italic"], p["uppercase"],
            p["highlight_size"], p["words_per_block"], p["gap_limit"], p["mode"],
            p["underline"], p["strikeout"], p["border_style"],
            p.get("vertical_position", 210), p.get("alignment", 2)
        )
    return (gr.skip(),) * 20 

def render_preview_video(font, size, color, highlight, outline, outline_thick, shadow, shadow_sz, bold, italic, upper,
                         h_size, w_block, gap, mode, under, strike, border_s, vert_pos, align):
    # Helper to convert HEX to ASS color &HBBGGRR&
    def hex_to_ass(h):
        if not h: return "&H00FFFFFF"
        h = h.lstrip('#')
        if len(h) == 6:
            return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}"
        return "&H00FFFFFF"
    
    base_c = hex_to_ass(color)
    high_c = hex_to_ass(highlight)
    out_c = hex_to_ass(outline)
    shad_c = hex_to_ass(shadow)
    
    # Handle Mode Logic for Video Preview
    if mode == "word_by_word":
        # Make base color fully transparent (Alpha FF)
        # base_c format is &H00BBGGRR, change 00 to FF
        base_c = f"&HFF{base_c[4:]}"
    elif mode == "no_highlight":
        # Highlight color same as base color
        high_c = base_c
    
    template_path = os.path.join(CURRENT_DIR, "This is a PREVIEW of your subtitles.ass")
    if not os.path.exists(template_path):
        return None
        
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Replace colors in the Events (The template uses these hardcoded placeholders)
        # We assume the template uses &H00FFFFFF for base and &H0000FFFF for active
        content = content.replace('&H00FFFFFF', base_c) 
        content = content.replace('&H0000FFFF', high_c)
        
        # Construct Style line
        # Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, ...
        bold_val = "-1" if bold else "0"
        italic_val = "-1" if italic else "0"
        under_val = "-1" if under else "0"
        strike_val = "-1" if strike else "0"
        
        # Note: encoding 1 is Default
        style_line = f"Style: Default,{font},{size},{base_c},&H00000000,{out_c},{shad_c},{bold_val},{italic_val},{under_val},{strike_val},100,100,0,0,{border_s},{outline_thick},{shadow_sz},2,10,10,10,1"
        
        content = re.sub(r"Style: Default,.*", style_line, content)
        
        temp_ass = "temp_preview.ass"
        temp_ass_path = os.path.join(WORKING_DIR, temp_ass)
        with open(temp_ass_path, "w", encoding='utf-8') as f:
            f.write(content)
            
        out_vid = "preview_render.mp4"
        out_vid_path = os.path.join(WORKING_DIR, out_vid)
        
        # Render with ffmpeg
        # Background color #333333 to match UI roughly
        cmd = [
            "ffmpeg", "-y", 
            "-f", "lavfi", "-i", "color=c=0x333333:s=854x480:d=2.4",
            "-vf", f"ass={temp_ass}", 
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-an",
            out_vid
        ]
        
        subprocess.run(cmd, cwd=WORKING_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(out_vid_path):
            return out_vid_path
            
    except Exception as e:
        print(f"Preview Gen Error: {e}")
        
    return None
