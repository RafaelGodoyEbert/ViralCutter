import customtkinter as ctk
from tkinter import filedialog, colorchooser, messagebox
import json
import os
import sys
import re
import uuid
import subprocess
import cv2
from PIL import Image
import concurrent.futures
import multiprocessing
import base64
import struct

# --- ADAPTED FROM convert_transcripts.py ---
def detect_format(data):
    if "segments" not in data: return "unknown"
    segments = data["segments"]
    if not segments: return "empty"
    first_segment = segments[0]
    if "words" in first_segment and len(first_segment["words"]) > 0:
        first_word = first_segment["words"][0]
        if "confidence" in first_word and "eos" in first_word: return "premiere"
    if "words" in first_segment and len(first_segment["words"]) > 0:
        first_word = first_segment["words"][0]
        if "score" in first_word or "word" in first_word: return "whisperx"
    if "text" in first_segment and "start" in first_segment and "end" in first_segment: return "whisperx"
    return "unknown"

def normalize_to_whisperx(data):
    """Normalize input JSON to a standard list of words with timing."""
    detected = detect_format(data)
    words = []
    
    if detected == "premiere":
        for segment in data.get("segments", []):
            for word in segment.get("words", []):
                words.append({
                    "word": word["text"],
                    "start": word["start"],
                    "end": float(word["start"]) + float(word["duration"]),
                    "text": word["text"]
                })
    elif detected == "whisperx" or detected == "unknown":
        for segment in data.get("segments", []):
            if "words" in segment:
                for word in segment["words"]:
                    w_end = word.get("end", word["start"] + 0.1)
                    words.append({
                        "word": word.get("word", "").strip(),
                        "start": word["start"],
                        "end": w_end,
                        "text": word.get("word", "").strip()
                    })
            else:
                # Basic segment fallback (split by space, approx timing?? No, skip for now or treat whole segment as word)
                pass
    return words

# --- ADAPTED FROM adjust_subtitles.py ---
def format_time_ass(time_seconds):
    hours = int(time_seconds // 3600)
    minutes = int((time_seconds % 3600) // 60)
    seconds = int(time_seconds % 60)
    centiseconds = int((time_seconds % 1) * 100)
    return f"{hours:01}:{minutes:02}:{seconds:02}.{centiseconds:02}"

def hex_to_ass(hex_color):
    """Convert #RRGGBB to &H00BBGGRR&"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
        return f"&H00{b}{g}{r}&".upper()
    return "&H00FFFFFF&"

def hex_to_decimal_color(hex_color):
    """Convert #RRGGBB to decimal RGB for Premiere (e.g. #FFFFFF -> 16777215)"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        return int(hex_color, 16)
    return 16777215  # white

def estimate_text_width_arial(text, font_size):
    """Estimate text width in pixels for Arial font (Variable Width)"""
    width = 0
    # Average widths relative to font size (Tuned for Arial - Slightly Tighter)
    # Plus Kerning Compensation: Subtract small amount per curve pair
    width_sum = 0
    for c in text:
        if c in 'iltI1j .:,;\'"|()': width_sum += 0.24 * font_size
        elif c in 'mwMW@%': width_sum += 0.82 * font_size
        elif c in 'ABCDEFGHCKLNOPQRSTUVWXYZ': width_sum += 0.62 * font_size
        elif c.isnumeric(): width_sum += 0.53 * font_size
        else: width_sum += 0.44 * font_size # a-z and others
    
    # Kerning approximation: Reduce total width by ~1.5% of font size per character pair
    if len(text) > 1:
        width_sum -= (len(text) - 1) * 0.015 * font_size
        
    return max(0, width_sum)

def create_premiere_graphics_payload(text, font_name="Arial", font_size=84, fill_color_hex="#FFFFFF", 
                                    stroke_visible=False, stroke_color_hex="#000000", stroke_width=2,
                                    shadow_visible=False, shadow_color_hex="#000000", shadow_offset=5, shadow_opacity=100,
                                    alignment=1, highlights=None,
                                    back_visible=False, back_color_hex="#000000", back_opacity=75, back_size=0, back_radius=10,
                                    fill_over_stroke=True,
                                    faux_bold=False, faux_italic=False, all_caps=False, underline=False,
                                    underline_on_highlight=False, ghost_mode=False):
    """
    Create Premiere Pro Graphics Source Text payload (Base64 UTF-16LE)
    highlights: List of dicts: {'start': int, 'end': int, 'color': int, 'size': int}
    """
    # Sanitize font name to prevent "[Arial]" issue if user/preset includes brackets
    raw_font = str(font_name)
    font_name = raw_font.strip().replace('[', '').replace(']', '')
    
    # Map common font names to their PostScript names that Premiere expects
    # This prevents Premiere from showing "[FontName]" when it can't find the font
    font_name_map = {
        "Arial": "ArialMT",
        "Arial Bold": "Arial-BoldMT",
        "Arial Italic": "Arial-ItalicMT",
        "Arial Bold Italic": "Arial-BoldItalicMT",
        "Times New Roman": "TimesNewRomanPSMT",
        "Times New Roman Bold": "TimesNewRomanPS-BoldMT",
        "Times New Roman Italic": "TimesNewRomanPS-ItalicMT",
        "Courier New": "CourierNewPSMT",
        "Helvetica": "Helvetica",
        "Verdana": "Verdana",
        "Georgia": "Georgia",
        "Comic Sans MS": "ComicSansMS",
        "Trebuchet MS": "TrebuchetMS",
        "Impact": "Impact",
        "Calibri": "Calibri",
        "Consolas": "Consolas",
        "Cambria": "Cambria",
        "Montserrat": "Montserrat-Regular",
        "Montserrat Regular": "Montserrat-Regular",
        "Montserrat Bold": "Montserrat-Bold",
        "Montserrat ExtraBold": "Montserrat-ExtraBold",
        "Montserrat Black": "Montserrat-Black",
        "Montserrat Medium": "Montserrat-Medium",
        "Montserrat SemiBold": "Montserrat-SemiBold",
        "Open Sans": "OpenSans-Regular",
        "Open Sans Bold": "OpenSans-Bold",
        "Roboto": "Roboto-Regular",
        "Roboto Bold": "Roboto-Bold",
    }
    
    # Apply font mapping (case-insensitive)
    for display_name, ps_name in font_name_map.items():
        if font_name.lower() == display_name.lower():
            font_name = ps_name
            break
    
    # Debug para o usuario ver
    print(f"DEBUG XML: Fonte enviada='{font_name}' (Original='{raw_font}')")
    
    fill_color_dec = hex_to_decimal_color(fill_color_hex)
    stroke_color_dec = hex_to_decimal_color(stroke_color_hex)
    shadow_color_dec = hex_to_decimal_color(shadow_color_hex)
    back_color_dec = hex_to_decimal_color(back_color_hex)
    
    # --- Build Fill Color & Font Size Param Values ---
    # Default: [[0, base]]
    # --- Build Param Values ---
    # Default Params
    fill_param_values = [[0, fill_color_dec]]
    size_param_values = [[0, font_size]]
    
    # Underline Base
    base_under = underline
    if underline_on_highlight: base_under = False
    under_param_values = [[0, base_under]]
    
    # Visibility (Ghost Mode)
    # If ghost_mode=True, base text is hidden (False), highlights are shown (True).
    base_visible = True
    if ghost_mode: base_visible = False
    visible_param_values = [[0, base_visible]]
    
    if highlights:
        fill_param_values = []
        size_param_values = []
        under_param_values = []
        visible_param_values = []
        
        # Sanitize: Trim whitespace from highlight ranges to prevent background on spaces
        clean_highlights = []
        for h in highlights:
            s, e = h['start'], h['end']
            # Safety check indices
            s = max(0, min(len(text), s))
            e = max(0, min(len(text), e))
            if s >= e: continue
            
            sub = text[s:e]
            # Calculate trim offsets
            l_trim = len(sub) - len(sub.lstrip())
            r_trim = len(sub) - len(sub.rstrip())
            
            new_s = s + l_trim
            new_e = e - r_trim
            
            if new_e > new_s:
                nh = h.copy()
                nh['start'] = new_s
                nh['end'] = new_e
                clean_highlights.append(nh)
        
        # Sort highlights by start position
        sorted_highlights = sorted(clean_highlights, key=lambda x: x['start'])
        
        current_idx = 0
        
        for h in sorted_highlights:
            start = h['start']
            end = h['end']
            color = h.get('color', fill_color_dec)
            size = h.get('size', font_size)
            
            # Fill gap with base style if needed
            if start > current_idx:
                fill_param_values.append([current_idx, fill_color_dec])
                size_param_values.append([current_idx, font_size])
                under_param_values.append([current_idx, base_under])
                visible_param_values.append([current_idx, base_visible])
            
            # Add highlight style
            fill_param_values.append([start, color])
            size_param_values.append([start, size])
            
            # Underline High
            hl_under = True if underline_on_highlight else underline
            under_param_values.append([start, hl_under])
            
            # Visible High
            hl_visible = True
            visible_param_values.append([start, hl_visible])
            
            # Reset
            current_idx = end
            
        # Final segment
        if current_idx < len(text):
            fill_param_values.append([current_idx, fill_color_dec])
            size_param_values.append([current_idx, font_size])
            under_param_values.append([current_idx, base_under])
            visible_param_values.append([current_idx, base_visible])
        
        # Ensure starts at 0
        if not fill_param_values or fill_param_values[0][0] != 0:
            fill_param_values.insert(0, [0, fill_color_dec])
            # Assuming logic holds for others if lengths match
            if size_param_values and size_param_values[0][0] != 0: size_param_values.insert(0, [0, font_size])
            if under_param_values and under_param_values[0][0] != 0: under_param_values.insert(0, [0, base_under])
            if visible_param_values and visible_param_values[0][0] != 0: visible_param_values.insert(0, [0, base_visible])
            
    # Fallback
    if not fill_param_values: 
        fill_param_values = [[0, fill_color_dec]]
        size_param_values = [[0, font_size]]
        under_param_values = [[0, base_under]]
        visible_param_values = [[0, base_visible]]

    data = {
        "mTextParam": {
            "mAlignment": alignment, # 0=Left, 1=Center, 2=Right
            "mBackFillColor": back_color_dec,
            "mBackFillOpacity": float(back_opacity),
            "mBackFillSize": float(back_size),
            "mBackFillVisible": back_visible,
            "mBackFillCornerRadius": float(back_radius),
            "mDefaultRun": [],
            "mHeight": 0,
            "mHindiDigits": False,
            "mIndic": False,
            "mIsVerticalText": False,
            "mLeading": 0,
            "mLigatures": False,
            "mRTL": False,
            "mShadowAngle": 135,
            "mShadowBlur": 0,
            "mShadowColor": shadow_color_dec,
            "mShadowOffset": int(shadow_offset),
            "mShadowOpacity": int(shadow_opacity),
            "mShadowVisible": shadow_visible,
            "mStyleSheet": {
                "mBaselineShift": {"mParamValues": [[0, 0]]},
                "mCapsOption": {"mParamValues": [[0, 1 if all_caps else 0]]},
                "mFauxBold": {"mParamValues": [[0, faux_bold]]},
                "mFauxItalic": {"mParamValues": [[0, faux_italic]]},
                "mUnderline": {"mParamValues": under_param_values},
                "mFillColor": {"mParamValues": fill_param_values},
                "mFillOverStroke": {"mParamValues": [[0, fill_over_stroke]]},
                "mFillVisible": {"mParamValues": visible_param_values},
                "mFontName": {"mParamValues": [[0, font_name]]},
                "mFontSize": {"mParamValues": size_param_values},
                "mKerning": {"mParamValues": [[0, 0]]},
                "mStrokeColor": {"mParamValues": [[0, stroke_color_dec]]},
                "mStrokeVisible": {"mParamValues": visible_param_values if stroke_visible else [[0, False]]},
                "mStrokeWidth": {"mParamValues": [[0, stroke_width]]},
                "mText": text,
                "mTracking": {"mParamValues": [[0, 0]]},
                "mTsumi": {"mParamValues": [[0, 0]]}
            },
            "mTabWidth": 400,
            "mWidth": 0
        },
        "mUseLegacyTextBox": False,
        "mUseLegacyTextBox": False,
        "mVersion": 1,
        "mCreator": "Subtitle Studio by Rafael Godoy - https://github.com/RafaelGodoyEbert"
    }
    
    # Serialize to JSON (compact)
    json_str = json.dumps(data, separators=(',', ':'))
    
    # Encode as UTF-16LE
    utf16_bytes = json_str.encode('utf-16le')
    
    # 8-byte header: payload size in little-endian
    size = len(utf16_bytes)
    header = struct.pack('<Q', size)
    
    # Full payload
    return base64.b64encode(header + utf16_bytes).decode('ascii')


class SubtitleStudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Subtitle Studio - Criador de Legendas ASS")
        self.geometry("1100x800")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.loaded_json = None
        self.output_path = None
        self.output_path = None
        self.playing_video = False
        self.ffmpeg_process = None # Processo de streaming
        self.current_filename = "Subtitle_Export"

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)  # Sidebar scroll area
        self.grid_rowconfigure(1, weight=0)  # Credits footer fixed

        # --- LEFT SIDEBAR (Controls - Scrollable) ---
        self.sidebar_frame = ctk.CTkScrollableFrame(self, width=300, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_columnconfigure(0, weight=1)

        self._create_sidebar()
        
        # --- CREDITS FOOTER (Fixed at bottom) ---
        self.credits_footer = ctk.CTkFrame(self, width=300, corner_radius=0, fg_color="#1a1a1a", height=50)
        self.credits_footer.grid(row=1, column=0, sticky="ew")
        self.credits_footer.grid_propagate(False)
        
        ctk.CTkFrame(self.credits_footer, height=1, fg_color="#333").pack(fill="x", side="top")
        
        ctk.CTkLabel(self.credits_footer, text="Desenvolvido por Rafael Godoy", 
                    font=("Roboto", 9), text_color="#666").pack(pady=(8, 2))
        ctk.CTkLabel(self.credits_footer, text="Subtitle Studio v1.0", 
                    font=("Roboto", 8), text_color="#444").pack()

        # --- RIGHT MAIN AREA (Preview & Actions) ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(2, weight=1) # Text area expands
        self.main_frame.grid_columnconfigure(0, weight=1)

        self._create_main_area()
        
        # Load presets
        self._update_presets_combo()

    def _create_sidebar(self):
        # 1. File Selection
        ctk.CTkLabel(self.sidebar_frame, text="Arquivo de Entrada", font=("Roboto", 16, "bold")).pack(pady=(20, 10))
        self.btn_load_file = ctk.CTkButton(self.sidebar_frame, text="Carregar JSON", command=self.load_file)
        self.btn_load_file.pack(pady=5, padx=10, fill="x")
        self.lbl_file_status = ctk.CTkLabel(self.sidebar_frame, text="Nenhum arquivo carregado", text_color="gray")
        self.lbl_file_status.pack(pady=5)

        # Separator
        ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="grey").pack(fill="x", pady=15, padx=10)

        # --- PRESETS SECTION ---
        self.frame_presets = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.frame_presets.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(self.frame_presets, text="Meus Presets:", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=2)
        
        self.combo_presets = ctk.CTkComboBox(self.frame_presets, values=[], command=self.load_selected_preset)
        self.combo_presets.pack(fill="x", padx=5, pady=2)
        
        self.frame_preset_btns = ctk.CTkFrame(self.frame_presets, fg_color="transparent")
        self.frame_preset_btns.pack(fill="x", padx=5, pady=2)
        
        self.btn_save_preset = ctk.CTkButton(self.frame_preset_btns, text="Salvar", width=80, command=self.save_current_preset, fg_color="#2ecc71", hover_color="#27ae60")
        self.btn_save_preset.pack(side="left", padx=2, expand=True)
        
        self.btn_del_preset = ctk.CTkButton(self.frame_preset_btns, text="Excluir", width=80, command=self.delete_current_preset, fg_color="#e74c3c", hover_color="#c0392b")
        self.btn_del_preset.pack(side="right", padx=2, expand=True)

        ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="grey").pack(fill="x", pady=15, padx=10)

        # 2. General Settings (Resolution, Font)
        ctk.CTkLabel(self.sidebar_frame, text="Configurações Gerais", font=("Roboto", 16, "bold")).pack(pady=(0, 10))
        
        self._add_entry("Nome da Fonte", "font_name", "ArialMT")
        self._add_entry("Tamanho da Fonte (Base)", "font_size", "84")
        self._add_entry("Tamanho da Fonte (Destaque)", "highlight_size", "102")
        
        # --- Resolution Presets ---
        ctk.CTkLabel(self.sidebar_frame, text="Preset de Resolução", anchor="w").pack(padx=10, pady=(10, 0), anchor="w")
        
        self.res_presets = {
            "Mobile 9:16 - HD (720p)": (720, 1280),
            "Mobile 9:16 - Full HD (1080p)": (1080, 1920),
            "Mobile 9:16 - 2K (1440p)": (1440, 2560),
            "Mobile 9:16 - 4K (2160p)": (2160, 3840),
            "Landscape 16:9 - HD (720p)": (1280, 720),
            "Landscape 16:9 - Full HD (1080p)": (1920, 1080),
            "Landscape 16:9 - 4K (2160p)": (3840, 2160),
            "Landscape 16:9 - 8K (4320p)": (7680, 4320),
            "Square 1:1 (1080p)": (1080, 1080),
        }
        
        def apply_preset(choice):
            val = self.res_presets.get(choice)
            if val:
                w, h = val
                self.entry_resx.delete(0, "end")
                self.entry_resx.insert(0, str(w))
                self.entry_resy.delete(0, "end")
                self.entry_resy.insert(0, str(h))
                
                # Dynamic Font Scale (Target ~4.5% of height for base, ~5.5% for highlight)
                # Reference: 28px on 640h
                ratio_base = 28 / 640
                ratio_high = 34 / 640
                
                new_base = int(h * ratio_base)
                new_high = int(h * ratio_high)
                
                self.entry_font_size.delete(0, "end")
                self.entry_font_size.insert(0, str(new_base))
                
                self.entry_highlight_size.delete(0, "end")
                self.entry_highlight_size.insert(0, str(new_high))
                
                # Update Outline/Shadow too? (Usually 2px on 640h -> 0.3%)
                new_outline = max(2, int(h * (2/640)))
                self.entry_outline_thick.delete(0, "end")
                self.entry_outline_thick.insert(0, str(new_outline))
                
                new_shadow = max(2, int(h * (2/640)))
                self.entry_shadow_size.delete(0, "end")
                self.entry_shadow_size.insert(0, str(new_shadow))
            
            # Force update visual placeholder immediately
            self.after(50, self._update_placeholder) # Small delay to ensure entry update propagates if needed

        self.combo_res = ctk.CTkOptionMenu(self.sidebar_frame, values=list(self.res_presets.keys()), command=apply_preset)
        self.combo_res.pack(padx=10, pady=2, fill="x")
        self.combo_res.set("Mobile 9:16 - Full HD (1080p)")
        
        frame_res = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        frame_res.pack(fill="x", padx=10, pady=5)
        
        self.entry_resx = ctk.CTkEntry(frame_res, placeholder_text="W", width=70)
        self.entry_resx.pack(side="left", padx=(0,5))
        self.entry_resx.insert(0, "1080")
        
        ctk.CTkLabel(frame_res, text="x").pack(side="left", padx=2)
        
        self.entry_resy = ctk.CTkEntry(frame_res, placeholder_text="H", width=70)
        self.entry_resy.pack(side="left", padx=(5,5))
        self.entry_resy.insert(0, "1920")
        
        def swap_res():
            w = self.entry_resx.get()
            h = self.entry_resy.get()
            self.entry_resx.delete(0, "end")
            self.entry_resy.delete(0, "end")
            self.entry_resx.insert(0, h)
            self.entry_resy.insert(0, w)
            # Force update visual
            self._update_placeholder()
            
        btn_swap = ctk.CTkButton(frame_res, text="⇄", width=30, command=swap_res, fg_color="#444")
        btn_swap.pack(side="left")

        # FPS Input
        frame_fps = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        frame_fps.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame_fps, text="FPS:", width=50, anchor="w").pack(side="left")
        self.entry_fps = ctk.CTkEntry(frame_fps, width=80)
        self.entry_fps.pack(side="left")
        self.entry_fps.insert(0, "30")

        # 3. Colors
        ctk.CTkLabel(self.sidebar_frame, text="Cores (Hex)", font=("Roboto", 16, "bold")).pack(pady=(15, 10))
        self._add_color_picker("Cor Primária", "base_color", "#FFFFFF")
        self._add_color_picker("Cor Destaque", "highlight_color", "#FF0000")
        self._add_color_picker("Borda (Outline)", "outline_color", "#000000")
        self._add_color_picker("Sombra", "shadow_color", "#000000")
        self._add_color_picker("Fundo (Background)", "background_color", "#000000")

        # 4. Styling (Bold, Outline size, etc)
        ctk.CTkLabel(self.sidebar_frame, text="Estilo & Bordas", font=("Roboto", 16, "bold")).pack(pady=(15, 10))
        
        self.check_bold = ctk.CTkCheckBox(self.sidebar_frame, text="Negrito")
        self.check_bold.pack(anchor="w", padx=20, pady=2)
        self.check_bold.select()
        
        self.check_italic = ctk.CTkCheckBox(self.sidebar_frame, text="Itálico")
        self.check_italic.pack(anchor="w", padx=20, pady=2)
        
        self.check_uppercase = ctk.CTkCheckBox(self.sidebar_frame, text="MAIÚSCULAS")
        self.check_uppercase.pack(anchor="w", padx=20, pady=2)
        
        self.check_underline = ctk.CTkCheckBox(self.sidebar_frame, text="Sublinhado")
        self.check_underline.pack(anchor="w", padx=20, pady=(2, 0))
        
        self.check_under_only = ctk.CTkCheckBox(self.sidebar_frame, text="↳ Apenas Destaque", font=("Roboto", 11))
        self.check_under_only.pack(anchor="w", padx=40, pady=(0, 5))
        
        self.check_strikeout = ctk.CTkCheckBox(self.sidebar_frame, text="Tachado (Preview)")
        self.check_strikeout.pack(anchor="w", padx=20, pady=2)
        
        self._add_entry("Espessura da Borda", "outline_thick", "2")
        self._add_dropdown("Posição Borda", "outline_pos", ["Externo", "Sobreposto"], "Externo")
        self._add_entry("Tamanho da Sombra", "shadow_size", "2")
        # Background Settings (Controlled by Border Style)
        ctk.CTkLabel(self.sidebar_frame, text="Configs Fundo (Modo Caixa)", text_color="gray").pack(anchor="w", padx=20, pady=(10, 0))
        
        # Opacity Slider
        self.lbl_bg_op = ctk.CTkLabel(self.sidebar_frame, text="Opacidade Fundo (75%)")
        self.lbl_bg_op.pack(anchor="w", padx=20, pady=(5,0))
        def update_bg_op(val): self.lbl_bg_op.configure(text=f"Opacidade Fundo ({int(val)}%)")
        self.slider_bg_op = ctk.CTkSlider(self.sidebar_frame, from_=0, to=100, number_of_steps=100, command=update_bg_op)
        self.slider_bg_op.pack(padx=20, pady=(0,5), fill="x")
        self.slider_bg_op.set(75)

        # Size Slider
        self.lbl_bg_sz = ctk.CTkLabel(self.sidebar_frame, text="Tamanho Fundo (0)")
        self.lbl_bg_sz.pack(anchor="w", padx=20, pady=(5,0))
        def update_bg_sz(val): self.lbl_bg_sz.configure(text=f"Tamanho Fundo ({int(val)})")
        self.slider_bg_sz = ctk.CTkSlider(self.sidebar_frame, from_=0, to=100, number_of_steps=100, command=update_bg_sz)
        self.slider_bg_sz.pack(padx=20, pady=(0,5), fill="x")
        self.slider_bg_sz.set(0)
        
        # Slider Radius
        self.lbl_radius_title = ctk.CTkLabel(self.sidebar_frame, text="Raio do Canto (0)")
        self.lbl_radius_title.pack(anchor="w", padx=20, pady=(5,0))
        
        def update_radius_lbl(val):
            self.lbl_radius_title.configure(text=f"Raio do Canto ({int(val)})")
            
        self.slider_bg_radius = ctk.CTkSlider(self.sidebar_frame, from_=0, to=100, number_of_steps=100, command=update_radius_lbl)
        self.slider_bg_radius.pack(padx=20, pady=(0,5), fill="x")
        self.slider_bg_radius.set(0)
        
        self.check_bg_only = ctk.CTkCheckBox(self.sidebar_frame, text="Fundo Apenas Destaque (Alpha)")
        self.check_bg_only.pack(anchor="w", padx=20, pady=(5, 5))

        # X Offset for Manual Adjustment
        self.frame_offset = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.frame_offset.pack(fill="x", padx=20, pady=2)
        lbl_off = ctk.CTkLabel(self.frame_offset, text="Ajuste X (px):", width=80, anchor="w")
        lbl_off.pack(side="left")
        self.entry_x_offset = ctk.CTkEntry(self.frame_offset, width=40)
        self.entry_x_offset.pack(side="left", padx=5)
        self.entry_x_offset.insert(0, "0")
        
        lbl_scale = ctk.CTkLabel(self.frame_offset, text="Escala:", width=50, anchor="w")
        lbl_scale.pack(side="left", padx=(10,0))
        self.slider_width_scale = ctk.CTkSlider(self.frame_offset, from_=0.8, to=1.2, number_of_steps=40, width=100)
        self.slider_width_scale.set(1.0)
        self.slider_width_scale.pack(side="left", padx=5)
        
        self._add_dropdown("Estilo da Borda", "border_style", ["1 - Contorno", "3 - Caixa Opaca"], "1 - Contorno")

        # 5. Layout & Logic
        ctk.CTkLabel(self.sidebar_frame, text="Layout & Lógica", font=("Roboto", 16, "bold")).pack(pady=(15, 10))
        
        self._add_dropdown("Modo", "mode", ["highlight", "no_highlight", "word_by_word"], "highlight")
        self._add_entry("Palavras por Bloco", "words_block", "3")
        self._add_entry("Limit Lacuna (s)", "gap_limit", "0.2") # New Gap Limit
        self._add_entry("Quebra Bloco (s)", "block_gap", "2.0") # Breaks block if gap is larger
        
        self._add_entry("Posição Horizontal (X)", "horiz_pos", "540")
        self._add_entry("Posição Vertical (Y)", "vert_pos", "200")
        self._add_dropdown("Alinhamento Texto", "align", ["Esquerda", "Centro", "Direita"], "Centro")
        
        self.check_punctuation = ctk.CTkCheckBox(self.sidebar_frame, text="Remover Pontuação")
        self.check_punctuation.pack(anchor="w", padx=20, pady=10)
        # self.check_punctuation.select() # Default OFF
        
        self.check_split_punct = ctk.CTkCheckBox(self.sidebar_frame, text="Quebrar em Pontuação (. ! ?)")
        self.check_split_punct.pack(anchor="w", padx=20, pady=(0, 10))
        self.check_split_punct.select()

    def _create_main_area(self):
        # 1. Action Buttons (Global)
        frame_actions = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        frame_actions.pack(fill="x", pady=(0, 10))
        
        self.btn_generate = ctk.CTkButton(frame_actions, text="Atualizar Texto ASS", command=self.generate_preview, fg_color="#2b2b2b", border_width=1, border_color="gray")
        self.btn_generate.pack(side="left", padx=5)

        self.btn_preview_video = ctk.CTkButton(frame_actions, text="▶ Live Preview (Instantâneo)", command=self.start_live_preview, fg_color="green")
        self.btn_preview_video.pack(side="left", padx=5)
        
        self.btn_export_graphics = ctk.CTkButton(frame_actions, text="Premiere Graphics XML", command=self.export_premiere_graphics_xml, fg_color="#8b3bb8")
        self.btn_export_graphics.pack(side="left", padx=5)
        
        self.btn_save = ctk.CTkButton(frame_actions, text="Salvar .ASS", command=self.save_file)
        self.btn_save.pack(side="right", padx=5)

        # 2. Tabs
        self.tab_view = ctk.CTkTabview(self.main_frame)
        self.tab_view.pack(fill="both", expand=True)
        
        # Tab 1: Video
        self.tab_video = self.tab_view.add("Visualização")
        # Use place to center the video with correct aspect ratio
        self.video_display = ctk.CTkLabel(self.tab_video, text="", fg_color="black", corner_radius=0)
        self.video_display.place(relx=0.5, rely=0.5, anchor="center")
        
        # Initial Placeholder Update (Scheduled to wait for layout)
        self.after(100, self._update_placeholder)

        # Tab 2: Code
        self.tab_editor = self.tab_view.add("Código .ASS")
        self.preview_text = ctk.CTkTextbox(self.tab_editor, font=("Consolas", 12))
        self.preview_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    def _update_placeholder(self):
        """Draws a black box representing the target resolution."""
        if self.playing_video: return
        
        try:
            target_w = int(self.entry_resx.get())
            target_h = int(self.entry_resy.get())
        except:
            target_w, target_h = 360, 640
            
        avail_w = self.tab_video.winfo_width()
        avail_h = self.tab_video.winfo_height()
        
        if avail_w < 50 or avail_h < 50:
            self.after(500, self._update_placeholder)
            return

        scale = min(avail_w/target_w, avail_h/target_h) * 0.9 # 90% fit
        new_w = int(target_w * scale)
        new_h = int(target_h * scale)
        
        self.video_display.configure(width=new_w, height=new_h, text="Preview Area\n(Gere o vídeo para ver)")
    
    def start_live_preview(self, from_loop=False):
        """Inicia o streaming do FFmpeg direto para a UI via Pipe."""
        if not self.loaded_json:
             messagebox.showwarning("Aviso", "Nenhum JSON carregado.")
             return
             
        # Toggle Logic: Se já estiver tocando e o usuário clicou (não é loop), ENTÃO PARA.
        if self.playing_video and not from_loop:
            self._reset_player_state()
            return

        self.tab_view.set("Visualização")
        
        # 1. Kill processo anterior
        if self.ffmpeg_process:
            try: self.ffmpeg_process.kill()
            except: pass
            self.ffmpeg_process = None
            
        self.playing_video = False # Stop UI loop temporariamente para reinicio

        # 2. Gera ASS

        # 2. Gera ASS
        ass_content = self._generate_ass_content()
        temp_ass = "temp_preview.ass"
        with open(temp_ass, "w", encoding="utf-8") as f:
            f.write(ass_content)
            
        # 3. Calcular Resolução Otimizada (Max 1080p agora)
        try:
            target_w = int(self.entry_resx.get())
            target_h = int(self.entry_resy.get())
        except: target_w, target_h = 360, 640
        
        MAX_PREVIEW = 1080 
        scale = 1.0
        if max(target_w, target_h) > MAX_PREVIEW:
            scale = MAX_PREVIEW / max(target_w, target_h)
        
        w = int(target_w * scale)
        h = int(target_h * scale)
        if w % 2 != 0: w+=1
        if h % 2 != 0: h+=1
        
        # 4. Iniciar FFmpeg Popen
        # Output format: rawvideo, pixel format: bgr24 (nativo do opencv/pil)
        abs_ass = os.path.abspath(temp_ass).replace('\\', '/').replace(':', '\\:')
        
        try: fps = self.entry_fps.get()
        except: fps = "30"

        # Duration longa (ex: 60s) ou baseada no json
        duration = 10.0
        if self.loaded_json:
             try: duration = self.loaded_json[-1]['end'] + 2.0
             except: pass
        
        # -re flag forces input to be read at native frame rate (simulates real time)
        cmd = [
            "ffmpeg", "-re", "-y",
            "-f", "lavfi", "-i", f"color=c=0x1a1a1a:s={w}x{h}:r={fps}:d={duration}",
            "-vf", f"ass='{abs_ass}'",
            "-f", "image2pipe",  
            "-pix_fmt", "bgr24", 
            "-vcodec", "rawvideo", 
            "-"
        ]
        
        try:
            # Creation flags para não abrir janela cmd pop-up
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            self.ffmpeg_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**8, creationflags=creation_flags
            )
            
            self.playing_video = True
            self.btn_preview_video.configure(state="normal", text="⏹ Parar Preview", fg_color="red")
            # Iniciar leitura
            self.after(50, lambda: self._stream_from_pipe(w, h))
            
        except Exception as e:
            messagebox.showerror("Erro Streaming", f"Falha ao iniciar FFmpeg:\n{e}")
            self._reset_player_state()

    def _stream_from_pipe(self, w, h):
        if not self.playing_video or not self.ffmpeg_process:
            self._reset_player_state()
            return
            
        # Calcular tamanho do frame em bytes: W * H * 3 (BGR)
        frame_size = w * h * 3
        
        try:
            # Ler frame do stdout
            raw_frame = self.ffmpeg_process.stdout.read(frame_size)
            
            if len(raw_frame) != frame_size:
                # Fim do stream -> Reiniciar para Loop
                if self.playing_video:
                    # Pequeno delay antes do re-start para não floodar se der erro imediato
                     self.after(10, lambda: self.start_live_preview(from_loop=True))
                else: 
                     self._reset_player_state()
                return
                
            # Converter bytes para imagem
            image = Image.frombytes("RGB", (w, h), raw_frame, "raw", "BGR", 0, 1)
            
            # Ajustar para UI Label
            disp_w = self.video_display.winfo_width()
            disp_h = self.video_display.winfo_height()
            
            if disp_w > 10 and disp_h > 10:
                img_ratio = w / h
                disp_ratio = disp_w / disp_h
                
                if disp_ratio > img_ratio:
                    final_h = disp_h
                    final_w = int(final_h * img_ratio)
                else:
                    final_w = disp_w
                    final_h = int(final_w / img_ratio)
                
                # Resize rapido para display (Bilinear)
                image = image.resize((final_w, final_h), Image.Resampling.BILINEAR)
            
            ctk_img = ctk.CTkImage(light_image=image, dark_image=image, size=(image.width, image.height))
            self.video_display.configure(image=ctk_img, text="")
            
            # Requisitar proximo frame imediatamente (ffmpeg -re controla o tempo)
            # Aumentado para 15ms para não travar a GUI (Scroll/Move)
            self.video_display.after(100, lambda: self._stream_from_pipe(w, h))

        except Exception as e:
            print(f"Stream error: {e}")
            self._reset_player_state()

    def _reset_player_state(self):
        self.playing_video = False
        if self.ffmpeg_process:
            try: self.ffmpeg_process.kill()
            except: pass
        self.ffmpeg_process = None
        self.btn_preview_video.configure(state="normal", text="▶ Live Preview", fg_color="green")

    def _add_entry(self, label, attr_name, default):
        frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=120, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(frame)
        entry.pack(side="right", expand=True, fill="x")
        entry.insert(0, default)
        setattr(self, f"entry_{attr_name}", entry)

    def _add_dropdown(self, label, attr_name, values, default):
        frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=120, anchor="w").pack(side="left")
        dropdown = ctk.CTkOptionMenu(frame, values=values)
        dropdown.pack(side="right", expand=True, fill="x")
        dropdown.set(default)
        setattr(self, f"dropdown_{attr_name}", dropdown)

    def _add_color_picker(self, label, attr_name, default_color):
        frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        
        lbl = ctk.CTkLabel(frame, text=label, width=120, anchor="w")
        lbl.pack(side="left")
        
        # Color Preview/Button
        btn_color = ctk.CTkButton(frame, text=default_color, width=80, fg_color=default_color,
                                  command=lambda: self.pick_color(attr_name, btn_color))
        btn_color.pack(side="right", expand=True, fill="x")
        
        setattr(self, f"val_{attr_name}", default_color)
        setattr(self, f"btn_{attr_name}", btn_color)

    def pick_color(self, attr_name, btn_widget):
        curr = getattr(self, f"val_{attr_name}")
        color = colorchooser.askcolor(initialcolor=curr)
        if color[1]:
            hex_c = color[1]
            setattr(self, f"val_{attr_name}", hex_c)
            btn_widget.configure(text=hex_c, fg_color=hex_c)

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.loaded_json = normalize_to_whisperx(data)
                self.lbl_file_status.configure(text=os.path.basename(path), text_color="white")
                self.current_filename = os.path.splitext(os.path.basename(path))[0]
                self.generate_preview()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao ler arquivo:\n{e}")

    def generate_preview(self):
        content = self._generate_ass_content()
        self.preview_text.delete("0.0", "end")
        self.preview_text.insert("0.0", content)

    def save_file(self):
        if not self.loaded_json:
            messagebox.showwarning("Aviso", "Nenhum JSON carregado.")
            return
            
        path = filedialog.asksaveasfilename(defaultextension=".ass", filetypes=[("Subtitle", "*.ass")])
        if path:
            content = self._generate_ass_content()
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Sucesso", "Arquivo .ASS salvo com sucesso!")

    def _generate_ass_content(self):
        if not self.loaded_json:
            return "[Script Info]\nNo Data Loaded"

        # Get values
        font_name = self.entry_font_name.get()
        font_size = self.entry_font_size.get()
        highlight_size = self.entry_highlight_size.get()
        res_x = self.entry_resx.get()
        res_y = self.entry_resy.get()
        
        base_color = hex_to_ass(self.val_base_color)
        highlight_color = hex_to_ass(self.val_highlight_color)
        # Logic update for ASS Preview alignment with Premiere "Box" Mode
        border_style_str = self.dropdown_border_style.get()
        border_style = "3" if "3" in border_style_str else "1"
        
        if border_style == "3":
            # If Box Mode, ASS Outline represents the Background Box. Use Background Color.
            outline_color = hex_to_ass(self.val_background_color)
        else:
            # If Outline Mode, use Outline Color.
            outline_color = hex_to_ass(self.val_outline_color)
            
        shadow_color = hex_to_ass(self.val_shadow_color)
        
        is_bold = "-1" if self.check_bold.get() else "0"
        is_italic = "-1" if self.check_italic.get() else "0"
        is_upper = self.check_uppercase.get()
        is_under = "-1" if self.check_underline.get() else "0"
        is_strike = "-1" if self.check_strikeout.get() else "0"
        
        outline_thick = self.entry_outline_thick.get()
        shadow_size = self.entry_shadow_size.get()
        
        mode = self.dropdown_mode.get()
        align_str = self.dropdown_align.get()
        # Convert UI String to ASS Numpad Code (1=Left, 2=Center, 3=Right for Bottom Alignment)
        align_ass_map = {"Esquerda": "1", "Centro": "2", "Direita": "3"}
        align = align_ass_map.get(align_str, "2")
        
        vert_pos = self.entry_vert_pos.get()
        
        try:
            words_per_block = int(self.entry_words_block.get())
        except: words_per_block = 3
        
        try:
            gap_limit = float(self.entry_gap_limit.get())
        except: gap_limit = 0.2
        
        try:
            block_gap = float(self.entry_block_gap.get())
        except: block_gap = 2.0
        
        remove_punc = self.check_punctuation.get()
        split_punct = self.check_split_punct.get()

        header = f"""[Script Info]
Title: Subtitle Studio Export
ScriptType: v4.00+
PlayDepth: 0
PlayResX: {res_x}
PlayResY: {res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{base_color},&H00000000,{outline_color},&HFF000000,{is_bold},{is_italic},{is_under},{is_strike},100,100,0,0,{border_style},{outline_thick},{shadow_size},{align},10,10,{vert_pos},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events_str = ""
        
        # Logic to parse words into blocks
        # Pre-process to fix gaps (Anti-Flicker)
        # Creates a local copy so we don't mutate the global loaded_json
        words = [w.copy() for w in self.loaded_json]
        
        count = len(words)
        for k in range(count - 1):
            cur = words[k]
            nxt = words[k+1]
            gap = nxt['start'] - cur['end']
            
            # Se o gap for menor que o limite (ex: 200ms), estica a palavra anterior
            if 0 < gap < gap_limit:
                cur['end'] = nxt['start']

        i = 0
        total_words = len(words)
        
        last_end_time = 0.0
        
        while i < total_words:
            block = []
            while len(block) < words_per_block and i < total_words:
                current_word = words[i]
                
                # Check for max gap split
                if len(block) > 0:
                    last_end = block[-1]['end']
                    curr_start = current_word['start']
                    if (curr_start - last_end) > block_gap:
                        break
                        
                    # Check punctuation split
                    if split_punct:
                        # Check if the PREVIOUS word in the block (the last one added) ended with punctuation
                        # We must use 'raw_word' because 'word' might have stripped punctuation if remove_punc is True
                        last_item = block[-1]
                        last_word_raw = last_item.get('raw_word', last_item['word'])
                        
                        if re.search(r'[.!?]+\s*$', last_word_raw):
                            break
                
                # --- WIDTH SAFETY CHECK ---
                # Estimate current block width + next word
                # We need the TEXT that will be displayed (cleaned/upper/etc)
                temp_word_text = current_word['word']
                if remove_punc: temp_word_text = re.sub(r'[.,!?;]', '', temp_word_text)
                if is_upper: temp_word_text = temp_word_text.upper()
                
                # Current block text
                current_block_text = ""
                for b in block:
                    current_block_text += b['word'] + " " # space
                
                test_text = current_block_text + temp_word_text
                
                # Use font_size (base) or highlight_size? Highlight is larger, safer to use highlight_size for worst case
                # Parse sizes safely
                try: f_sz = float(highlight_size)
                except: f_sz = 80
                try: r_x = float(res_x)
                except: r_x = 1080
                
                est_width = estimate_text_width_arial(test_text, f_sz)
                
                # If exceeds 90% of screen width, break BEFORE adding this word
                # BUT if block is empty, we MUST accept it (single word too long? handle gracefully or just accept)
                if len(block) > 0 and est_width > (r_x * 0.9):
                    break
                # ---------------------------

                word_text = current_word['word']
                
                # Cleaning
                if remove_punc:
                    word_text = re.sub(r'[.,!?;]', '', word_text)
                
                # Uppercase
                if is_upper:
                    word_text = word_text.upper()
                
                # Append to block
                current_word_copy = current_word.copy()
                current_word_copy['raw_word'] = current_word['word'] # Store original for logic checks
                current_word_copy['word'] = word_text
                block.append(current_word_copy)
                i += 1
            
            if not block: continue
            
            # Determine Timings
            start_sec = block[0]['start']
            end_sec = block[-1]['end']
            
            # Gap Check (Dynamic)
            if start_sec - last_end_time < gap_limit:
                start_sec = last_end_time
            if end_sec < start_sec:
                end_sec = start_sec + 0.1 # Minimal duration
                
            start_ass = format_time_ass(start_sec)
            end_ass = format_time_ass(end_sec)
            last_end_time = end_sec
            
            # Generate Dialogue Line
            line_text = ""
            if mode == "highlight":
                # Create duplicate lines for karaoke effect?
                # Actually adjust_subtitles logic creates ONE line per block, 
                # but splits it into different colors within the same line?
                # No, adjust_subtitles logic generates N lines for a block of N words if highlighted sequentially?
                # Wait, looking back at adjust_subtitles:
                # for j in range(len(block)): ... f.write(...)
                # Yes, it loops through the block and writes a new event for EACH word highlight step.
                
                start_times = [w['start'] for w in block]
                end_times = [w['end'] for w in block]
                
                for j in range(len(block)):
                    # Recalculate timing for this specific frame of the block highlighting
                    # In true karaoke, it's one line with \k tags.
                    # But the "Highlighter" style usually means redrawing the line with different colors.
                    
                    # Using the adjust_subtitles logic:
                    s_t = start_times[j]
                    e_t = end_times[j]
                    if s_t - last_end_time < gap_limit: s_t = last_end_time # This is tricky inside loop
                    
                    # Simplified logic for Studio: 
                    # Each "Highlight Frame" lasts for the duration of the specific word, 
                    # but displays the WHOLE block.
                    
                    # Time for this specific state:
                    state_start = format_time_ass(block[j]['start'])
                    state_end = format_time_ass(block[j]['end'])
                    
                    # Highlight Logic
                    seg_text = ""
                    for k, w_data in enumerate(block):
                        w = w_data['word']
                        if k == j:
                            # Highlighted
                            seg_text += f"{{\\c{highlight_color}\\fs{highlight_size}}}{w} "
                        else:
                            # Base
                            seg_text += f"{{\\c{base_color}\\fs{font_size}}}{w} "
                    
                    events_str += f"Dialogue: 0,{state_start},{state_end},Default,,0,0,0,,{seg_text.strip()}\n"
            
            elif mode == "word_by_word":
                # Display only one word at a time
                for w_data in block:
                    s = format_time_ass(w_data['start'])
                    e = format_time_ass(w_data['end'])
                    text = f"{{\\c{highlight_color}\\fs{highlight_size}}}{w_data['word']}"
                    events_str += f"Dialogue: 0,{s},{e},Default,,0,0,0,,{text}\n"
            
            else: # No Highlight (Standard subtitle)
                line_text = " ".join([w['word'] for w in block])
                events_str += f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{line_text}\n"

        return header + events_str

    def render_alpha_video(self):
        if not self.loaded_json:
             messagebox.showwarning("Aviso", "Nenhum JSON carregado.")
             return
        
        output_path = filedialog.asksaveasfilename(defaultextension=".mov", filetypes=[("ProRes Alpha Video", "*.mov")])
        if not output_path: return
        
        # 1. Salvar ASS Temporário
        ass_content = self._generate_ass_content()
        temp_ass = "temp_alpha.ass"
        
        with open(temp_ass, "w", encoding="utf-8") as f:
            f.write(ass_content)
        
        # 2. Get Duration
        max_duration = 300.0 # Limit 5 min to avoid freeze if error
        real_duration = 10.0
        if self.loaded_json:
            try: real_duration = self.loaded_json[-1]['end'] + 1.0
            except: pass
        duration = min(real_duration, max_duration)
        
        res_x = self.entry_resx.get()
        res_y = self.entry_resy.get()
        try: fps = self.entry_fps.get()
        except: fps = "30"
        
        abs_ass_path = os.path.abspath(temp_ass)
        ass_path_unix = abs_ass_path.replace('\\', '/').replace(':', '\\:')
        
        # Use UT Video codec with RGBA - lossless, perfect alpha support
        # Generate transparent base with nullsrc, apply ASS as overlay
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"nullsrc=s={res_x}x{res_y}:d={duration}:r={fps}",
            "-i", abs_ass_path,
            "-filter_complex", f"[0:v]format=rgba[base];[base]subtitles={abs_ass_path}[out]",
            "-map", "[out]",
            "-c:v", "utvideo",
            "-pix_fmt", "rgba",
            output_path.replace('.mov', '.avi')  # UT Video works best in AVI
        ]
        
        # Update output path for AVI
        final_output = output_path.replace('.mov', '.avi')
        
        old_text = self.btn_export_alpha.cget("text")
        self.btn_export_alpha.configure(state="disabled", text="Renderizando...", fg_color="gray")
        self.update()
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            
            # Clean up temp files
            try: os.remove(temp_ass)
            except: pass
            try: os.remove(temp_base_video)
            except: pass
            
            messagebox.showinfo("Sucesso", f"Vídeo Alpha exportado:\\n{output_path}")
            try: os.startfile(os.path.dirname(output_path))
            except: pass
            # Opcional: abrir pasta
            # subprocess.run(f'explorer /select,"{output_path.replace("/","\\")}"')
        except Exception as e:
            messagebox.showerror("Erro Export Alpha", f"Falha no render:\n{e}")
        finally:
             self.btn_export_alpha.configure(state="normal", text=old_text, fg_color="#b83b3b")

    def render_png_sequence(self):
        if not self.loaded_json:
             messagebox.showwarning("Aviso", "Nenhum JSON carregado.")
             return
             
        output_dir = filedialog.askdirectory(title="Selecione pasta para salvar PNGs")
        if not output_dir: return
        
        # Create 'captions' subfolder
        captions_dir = os.path.join(output_dir, "captions")
        os.makedirs(captions_dir, exist_ok=True)
        
        # Create 'temp' subfolder
        temp_dir = os.path.join(output_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # 1. Full ASS
        full_ass = self._generate_ass_content()
        
        # Split Header and Events
        header_lines = []
        event_lines = []
        in_events = False
        
        for line in full_ass.splitlines():
            if line.strip() == "[Events]":
                in_events = True
                header_lines.append(line)
                continue
            
            if in_events:
                if line.startswith("Dialogue:"):
                    event_lines.append(line)
                else:
                    header_lines.append(line)
            else:
                header_lines.append(line)
                
        if not event_lines:
             messagebox.showwarning("Aviso", "Nenhum evento encontrado.")
             return

        old_text = self.btn_export_png.cget("text")
        self.btn_export_png.configure(state="disabled", text="Iniciando...", fg_color="gray")
        self.update()
        
        res_x = self.entry_resx.get()
        res_y = self.entry_resy.get()
        
        # Determine workers - use CPU count but leave one for system/GUI if possible
        max_workers = max(1, (os.cpu_count() or 4) - 1)
        # However, FFmpeg is also multi-threaded usually. 
        # But for single frame lavfi generation, overhead is process creation.
        # Let's use 4-8 parallel workers to saturate IO/Process creation.
        max_workers = min(max_workers, 8) 
        
        try:
            total = len(event_lines)
            xml_clips = [None] * total # Pre-allocate to keep order or use dict? 
            # Threads finish out of order. We need to collect results and sort later or assign by index.
            
            # Helper for thread
            def task_wrapper(args):
                return self._render_frame_task(*args)
            
            # Prepare args
            tasks = []
            base_name = self.current_filename
            for i, raw_line in enumerate(event_lines):
                # Pass captions_dir instead of output_dir AND pass temp_dir AND base_name
                tasks.append((i, raw_line, header_lines, captions_dir, res_x, res_y, temp_dir, base_name))
            
            completed_count = 0
            results = []
            
            # Run in ThreadPool
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all
                future_to_idx = {executor.submit(task_wrapper, task): task[0] for task in tasks}
                
                for future in concurrent.futures.as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        res = future.result()
                        results.append(res)
                    except Exception as exc:
                        print(f"Frame {idx} generated an exception: {exc}")
                    
                    completed_count += 1
                    if completed_count % 5 == 0 or completed_count == total:
                        # Update UI (running in main thread here loop, so it blocks but updates)
                        self.btn_export_png.configure(text=f"PNG {completed_count}/{total}")
                        self.update()
            
            # Sort results by index to ensure XML order
            results.sort(key=lambda x: x['index'])
            xml_clips = [r for r in results]

            # Generate XML for Premiere
            try:
                fps_val = float(self.entry_fps.get()) if self.entry_fps.get() else 30.0
                xml_name = f"{self.current_filename}.xml"
                self._create_premiere_xml(output_dir, xml_clips, fps_val, res_x, res_y, xml_name)
                msg_extra = f"\n+ XML '{xml_name}' gerado!"
            except Exception as e:
                print(e)
                msg_extra = "\n(Erro ao gerar XML)"
            
            # Clean up temp dir if empty? Or just leave it?
            # User asked to PUT them in temp, usually implies keeping organization or easy delete.
            # Convert paths in xml_clips are to PNGs in captions folder, temps are deleted by worker.
            # We can try to remove the temp folder if empty.
            try: os.rmdir(temp_dir)
            except: pass

            messagebox.showinfo("Sucesso", f"{total} PNGs gerados!{msg_extra}")
            try: os.startfile(output_dir)
            except: pass
            
        except Exception as e:
            messagebox.showerror("Erro PNG", f"Falha: {e}")
        finally:
            self.btn_export_png.configure(state="normal", text=old_text, fg_color="#3b8bb8")
    
    def export_premiere_graphics_xml(self):
        """Export Premiere Pro Graphics XML with native editable text"""
        if not self.loaded_json:
            messagebox.showwarning("Aviso", "Nenhum JSON carregado.")
            return
        
        output_dir = filedialog.askdirectory(title="Escolher Pasta para Salvar XML")
        if not output_dir:
            return
        
        old_text = self.btn_export_graphics.cget("text")
        self.btn_export_graphics.configure(state="disabled", text="Gerando XML...", fg_color="gray")
        self.update()
        
        try:
            # Generate ASS content to extract subtitle data
            ass_content = self._generate_ass_content()
            
            # Parse dialogues lines
            dialogues = []
            for line in ass_content.split('\n'):
                if line.startswith('Dialogue:'):
                    dialogues.append(line)
            
            if not dialogues:
                messagebox.showerror("Erro", "Nenhum diálogo encontrado!")
                return
            
            # Get settings from UI
            font_name = self.entry_font_name.get() or "ArialMT"
            is_bold = bool(self.check_bold.get())
            is_italic = bool(self.check_italic.get())
            is_upper = bool(self.check_uppercase.get())
            is_under = bool(self.check_underline.get())
            font_size_base = int(self.entry_font_size.get() or "84")
            font_size_highlight_ui = int(self.entry_highlight_size.get() or "102")
            
            fill_color_hex = self.val_base_color
            highlight_color_hex = self.val_highlight_color
            stroke_color_hex = self.val_outline_color
            shadow_color_hex = self.val_shadow_color
            
            stroke_width = int(self.entry_outline_thick.get() or "2")
            border_style = self.dropdown_border_style.get()
            # Logic: Border Style determines visibility
            # "3 - Caixa Opaca" -> Background ON, Stroke OFF
            # "1 - Contorno" -> Background OFF, Stroke ON
            is_box = ("Caixa" in border_style)
            stroke_visible = not is_box
            bg_vis = is_box
            
            shadow_size = int(self.entry_shadow_size.get() or "2")
            shadow_visible = (shadow_size > 0)
            
            # Background Settings
            bg_hex = self.val_background_color
            bg_op = self.slider_bg_op.get()
            bg_sz = self.slider_bg_sz.get()
            bg_rad = self.slider_bg_radius.get()
            
            # Outline Pos
            outline_pos = self.dropdown_outline_pos.get()
            is_fill_over_stroke = (outline_pos == "Externo")
            
            # Parse Align
            # Based on user testing: 2 results in Center alignment in Premiere.
            align_map = {"Esquerda":0, "Centro":2, "Direita":1} 
            align_ui_val = self.dropdown_align.get() 
            premiere_align = align_map.get(align_ui_val, 2)
            
            highlight_color_dec = hex_to_decimal_color(highlight_color_hex)
            
            # Parse each dialogue
            # Get Only-Highlight Options
            bg_only_highlight = bool(self.check_bg_only.get())
            under_only_highlight = bool(self.check_under_only.get())
            
            # Get resolution and FPS needed for layout calculation
            res_x_str = self.entry_resx.get() or "1920"
            res_x = int(res_x_str)
            res_y = int(self.entry_resy.get() or "1080")
            horiz_pos_str = self.entry_horiz_pos.get() or str(res_x//2)
            horiz_pos_px = int(horiz_pos_str)
            
            clips_v2 = []
            clips_v3 = []
            for idx, dialogue_line in enumerate(dialogues):
                parts = dialogue_line.split(",", 9)
                if len(parts) < 10:
                    continue
                
                start_str = parts[1]
                end_str = parts[2]
                text_with_tags = parts[9]
                
                # --- PARSE HIGHLIGHTS ---
                clean_text = ""
                highlights = []
                
                # Split by tags: {tag} or text
                tokens = re.split(r'(\{.*?\})', text_with_tags)
                
                current_idx = 0
                is_highlight = False
                highlight_start = -1
                current_highlight_size = font_size_highlight_ui
                active_highlight_size = font_size_highlight_ui
                
                for token in tokens:
                    if not token: continue
                    
                    if token.startswith('{'): # Tag
                         # Color: \c&HBBGGRR&
                        color_match = re.search(r'\\c&H([0-9A-Fa-f]+)&', token)
                        
                        # Font Size: \fs100
                        size_match = re.search(r'\\fs(\d+)', token)
                        
                        # Determine if this tag starts a highlight
                        # Trigger is Color == Highlight Color
                        is_target_color = False
                        
                        if color_match:
                            ass_hex = color_match.group(1) # BBGGRR
                            # Convert self.val_highlight_color to ASS Hex like (BBGGRR)
                            hc_r = highlight_color_hex[1:3]
                            hc_g = highlight_color_hex[3:5]
                            hc_b = highlight_color_hex[5:7]
                            target_ass = f"{hc_b}{hc_g}{hc_r}".upper()
                            
                            # Clean ASS Hex (Extract last 6 chars: 00BBGGRR -> BBGGRR)
                            clean_ass_hex = ass_hex[-6:].upper()
                            
                            # If matches highlight color
                            if clean_ass_hex == target_ass:
                                is_target_color = True
                        
                        # Size update (store for next highlight run)
                        if size_match:
                            current_highlight_size = int(size_match.group(1))
                        
                        if is_target_color:
                            if not is_highlight:
                                is_highlight = True
                                highlight_start = current_idx
                                # Capture size at START of highlight
                                active_size = current_highlight_size
                                # Fix: If tag has no size OR size equals base size (reset), force highlight size
                                if not size_match or active_size == font_size_base:
                                    active_size = font_size_highlight_ui
                                active_highlight_size = active_size

                        elif color_match: # Color changed but not target -> End Highlight
                            if is_highlight:
                                highlights.append({
                                    'start': highlight_start,
                                    'end': current_idx,
                                    'color': highlight_color_dec,
                                    'size': active_highlight_size
                                })
                                is_highlight = False
                    else:
                        clean_text += token
                        current_idx += len(token)
                
                if is_highlight:
                    highlights.append({
                        'start': highlight_start,
                        'end': current_idx,
                        'color': highlight_color_dec,
                        'size': active_highlight_size
                    })
                
                text_plain = clean_text.strip()
                
                def ass_time_to_seconds(t):
                    h, m, s = t.split(':')
                    s, cs = s.split('.')
                    return int(h)*3600 + int(m)*60 + int(s) + int(cs)/100
                
                start_sec = ass_time_to_seconds(start_str)
                end_sec = ass_time_to_seconds(end_str)
                
                # V2 Payload (Base)
                payload_v2 = create_premiere_graphics_payload(
                    text=text_plain,
                    font_name=font_name,
                    font_size=font_size_base,
                    fill_color_hex=fill_color_hex,
                    stroke_visible=stroke_visible,
                    stroke_color_hex=stroke_color_hex,
                    stroke_width=stroke_width,
                    shadow_visible=shadow_visible,
                    shadow_color_hex=shadow_color_hex,
                    shadow_offset=shadow_size*2,
                    shadow_opacity=100,
                    alignment=premiere_align,
                    highlights=highlights,
                    
                    back_visible=(bg_vis and not bg_only_highlight),
                    back_color_hex=bg_hex,
                    back_opacity=bg_op,
                    back_size=bg_sz,
                    back_radius=bg_rad,
                    fill_over_stroke=is_fill_over_stroke,
                    faux_bold=is_bold,
                    faux_italic=is_italic,
                    all_caps=is_upper,
                    underline=is_under,
                    underline_on_highlight=under_only_highlight
                )
                
                clips_v2.append({
                    'index': idx,
                    'start': start_sec,
                    'end': end_sec,
                    'text': text_plain,
                    'payload': payload_v2
                })
                
                # V3 Payload (Overlay for BG Only High)
                if bg_only_highlight and highlights:
                     # Check if we can use Trimmed Position Estimation
                     h_start = min(h['start'] for h in highlights)
                     h_end = max(h['end'] for h in highlights)
                     
                     # Get Highlight Properties (First highlight dominant)
                     h_props = highlights[0]
                     h_size = h_props.get('size', font_size_base)
                     h_color_int = h_props.get('color', hex_to_decimal_color(fill_color_hex))
                     h_color_hex = f"#{h_color_int:06X}"
                     
                     # Extract Text
                     h_text = text_plain[h_start:h_end]
                     h_prev = text_plain[:h_start]
                     h_post = text_plain[h_end:]
                     
                     # Trim spaces from the highlight text itself
                     orig_len = len(h_text)
                     h_text_clean = h_text.strip()
                     l_diff = h_text.find(h_text_clean) if h_text_clean else 0
                     
                     if h_text_clean:
                         h_prev += h_text[:l_diff]
                         h_text = h_text_clean
                         
                         # Position Calculation
                         # Note: Prev text might have mixture of sizes if other highlights exist earlier, 
                         # but we assume base size for simplicity or it's too complex.
                         
                         est_scale = self.slider_width_scale.get()
                         
                         w_prev = estimate_text_width_arial(h_prev, font_size_base) * est_scale
                         w_high = estimate_text_width_arial(h_text, h_size) * est_scale
                         w_post = estimate_text_width_arial(h_post, font_size_base) * est_scale
                         w_total = w_prev + w_high + w_post
                         
                         # Row Start X depends on Base Alignment
                         # premiere_align comes from UI map: {"Esquerda":0, "Centro":2, "Direita":1}
                         if premiere_align == 0: # Left
                             row_start_x = horiz_pos_px
                         elif premiere_align == 1: # Right (Mapped to 1)
                             row_start_x = horiz_pos_px - w_total
                         else: # Center (Mapped to 2, or default)
                             row_start_x = horiz_pos_px - (w_total / 2)
                         
                         # Highlight Start X
                         high_start_x = row_start_x + w_prev
                         
                         # We use Left Alignment for V3 to avoid center-point ambiguity
                         # So the Anchor Point (Position) will be at high_start_x
                         
                         # Apply Manual Offset from UI
                         try:
                            manual_offset = int(self.entry_x_offset.get())
                         except:
                            manual_offset = 0
                         
                         high_final_x = high_start_x + manual_offset
                         
                         print(f"DEBUG V3: Text='{h_text}' Align={premiere_align} BaseX={horiz_pos_px} EstTotalW={w_total:.1f} StartX={high_start_x:.1f} Offset={manual_offset} -> Final={high_final_x:.1f}")
                         
                         payload_v3 = create_premiere_graphics_payload(
                            text=h_text, # Trimmed text
                            font_name=font_name,
                            font_size=h_size, # Correct Highlight Size
                            fill_color_hex=h_color_hex, # Correct Highlight Color
                            stroke_visible=False, 
                            shadow_visible=False,
                            alignment=0, # Force Left alignment
                            
                            back_visible=True, # Force BG
                            back_color_hex=bg_hex,
                            back_opacity=bg_op,
                            back_size=bg_sz,
                            back_radius=bg_rad,
                            fill_over_stroke=is_fill_over_stroke,
                            faux_bold=is_bold,
                            faux_italic=is_italic,
                            all_caps=is_upper,
                            
                            ghost_mode=False # NO GHOST. Clean text.
                         )
                         
                         clips_v3.append({
                            'index': idx,
                            'start': start_sec,
                            'end': end_sec,
                            'text': h_text,
                            'payload': payload_v3,
                            'custom_pos_x': high_final_x # Store custom position
                         })
                     else:
                         # Fallback if empty
                         pass

            # Resolution/FPS were read above
            fps_str = self.entry_fps.get() or "30"
            fps = int(fps_str)
            vert_pos_px = int(self.entry_vert_pos.get() or "200")
            
            # Generate XML Filename (Based on JSON name)
            base_name = self.current_filename if self.current_filename else "Subtitle_Export"
            # Ensure valid char
            safe_name = "".join([c for c in base_name if c.isalnum() or c in (' ', '_', '-')]).strip()
            seq_name = f"{safe_name}_text"
            xml_filename = f"{seq_name}.xml"
            
            xml_path = os.path.join(output_dir, xml_filename)
            
            self._create_premiere_graphics_xml(output_dir, clips_v2, clips_v3, fps, res_x, res_y, vert_pos_px, horiz_pos_px, seq_name=seq_name, xml_filename=xml_filename)
            
            messagebox.showinfo("Sucesso", f"XML Premiere Graphics gerado!\\n{xml_path}\\n\\nImporte no Premiere Pro como Sequência.")
            try:
                os.startfile(os.path.dirname(xml_path))
            except:
                pass
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erro", f"Falha ao gerar XML: {e}")
        finally:
            self.btn_export_graphics.configure(state="normal", text=old_text, fg_color="#8b3bb8")

    def _render_frame_task(self, i, raw_line, header_lines, output_dir, res_x, res_y, temp_dir, base_name):
        """Worker function to render a single frame."""
        # raw_line format: Dialogue: 0,Start,End,...
        parts = raw_line.split(",", 9)
        if len(parts) < 10: return {'index': i, 'valid': False}
        
        # Parse Start/End for XML
        def parse_ass(t):
            h_s, m_s, s_s = t.split(':')
            return float(h_s)*3600 + float(m_s)*60 + float(s_s)
        
        try:
            real_start = parse_ass(parts[1])
            real_end = parse_ass(parts[2])
        except:
            real_start, real_end = 0.0, 1.0

        # Original Start for filename
        orig_start = parts[1].replace(":", "-").replace(".", "_")
        
        # Construct new line forced to time 0
        new_line = f"{parts[0]},0:00:00.00,0:00:05.00,{','.join(parts[3:])}"
        
        # Create Mini ASS inside TEMP DIR
        mini_ass_content = "\n".join(header_lines) + "\n" + new_line
        temp_ass_path = os.path.join(temp_dir, f"temp_png_{i}.ass")
        
        # Parse text from ASS with color/size tags
        import re
        text_content = new_line.split(",", 9)[-1] if "," in new_line else ""
        
        filename = os.path.join(output_dir, f"{base_name}_{i:04d}.png")
        
        # Render using Pillow
        from PIL import ImageDraw, ImageFont
        
        # Create transparent image
        img = Image.new('RGBA', (int(res_x), int(res_y)), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Parse segments: {\c&H...&\fs...}word
        segments = []
        pattern = r'(\{[^}]+\})([^{]*)'
        matches = re.findall(pattern, text_content)
        
        for tags, text in matches:
            if not text.strip():
                continue
            # Extract color (BGR format in ASS: &HAABBGGRR& or &HBBGGRR&)
            color_match = re.search(r'\\c&H([0-9A-Fa-f]{6,8})&', tags)
            if color_match:
                hex_str = color_match.group(1)
                # If 8 chars, first 2 are alpha (usually 00), skip them
                if len(hex_str) == 8:
                    hex_str = hex_str[2:]  # Skip AA, keep BBGGRR
                # Now we have BBGGRR (6 chars)
                bb = int(hex_str[0:2], 16)
                gg = int(hex_str[2:4], 16)
                rr = int(hex_str[4:6], 16)
                color = (rr, gg, bb, 255)
            else:
                color = (255, 255, 255, 255)
            
            # Extract size
            size_match = re.search(r'\\fs(\d+)', tags)
            font_size = int(size_match.group(1)) if size_match else 84
            
            # Extract styles
            is_bold = re.search(r'\\b1', tags) is not None
            is_italic = re.search(r'\\i1', tags) is not None
            is_underline = re.search(r'\\u1', tags) is not None
            is_strikeout = re.search(r'\\s1', tags) is not None
            
            segments.append({
                'text': text, 
                'color': color, 
                'size': font_size,
                'bold': is_bold,
                'italic': is_italic,
                'underline': is_underline,
                'strikeout': is_strikeout
            })
        
        # Calculate widths
        total_width = 0
        segment_widths = []
        for seg in segments:
            # Choose font file based on style
            font_file = "arial.ttf"
            if seg['bold'] and seg['italic']:
                font_file = "arialbi.ttf"
            elif seg['bold']:
                font_file = "arialbd.ttf"
            elif seg['italic']:
                font_file = "ariali.ttf"
            
            try:
                font = ImageFont.truetype(font_file, seg['size'])
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", seg['size'])
                except:
                    font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), seg['text'], font=font)
            w = bbox[2] - bbox[0]
            segment_widths.append(w)
            total_width += w
        
        # Start centered
        x_pos = (int(res_x) - total_width) // 2
        
        # Find max height for baseline alignment
        max_height = 0
        for seg in segments:
            font_file = "arial.ttf"
            if seg['bold'] and seg['italic']:
                font_file = "arialbi.ttf"
            elif seg['bold']:
                font_file = "arialbd.ttf"
            elif seg['italic']:
                font_file = "ariali.ttf"
            
            try:
                font = ImageFont.truetype(font_file, seg['size'])
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", seg['size'])
                except:
                    font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), seg['text'], font=font)
            h = bbox[3] - bbox[1]
            if h > max_height:
                max_height = h
        
        # Common baseline
        y_baseline = int(res_y) - 200
        
        # Draw segments
        for idx, seg in enumerate(segments):
            font_file = "arial.ttf"
            if seg['bold'] and seg['italic']:
                font_file = "arialbi.ttf"
            elif seg['bold']:
                font_file = "arialbd.ttf"
            elif seg['italic']:
                font_file = "ariali.ttf"
            
            try:
                font = ImageFont.truetype(font_file, seg['size'])
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", seg['size'])
                except:
                    font = ImageFont.load_default()
            
            # Use baseline alignment (bottom of text aligned)
            bbox = draw.textbbox((0, 0), seg['text'], font=font)
            h = bbox[3] - bbox[1]
            y_pos = y_baseline - h
            
            # Outline
            for adj in [(-2,-2),(-2,0),(-2,2),(0,-2),(0,2),(2,-2),(2,0),(2,2)]:
                draw.text((x_pos+adj[0], y_pos+adj[1]), seg['text'], font=font, fill=(0,0,0,255))
            
            # Main text
            draw.text((x_pos, y_pos), seg['text'], font=font, fill=seg['color'])
            
            # Decorations (underline, strikeout)
            text_width = segment_widths[idx]
            if seg['underline']:
                line_y = y_pos + h + 2
                draw.line([(x_pos, line_y), (x_pos + text_width, line_y)], fill=seg['color'], width=2)
            if seg['strikeout']:
                line_y = y_pos + h // 2
                draw.line([(x_pos, line_y), (x_pos + text_width, line_y)], fill=seg['color'], width=2)
            
            x_pos += text_width
        
        # Save
        img.save(filename, 'PNG')
        
        return {
            'index': i,
            'name': os.path.basename(filename),
            'path': filename,
            'start': real_start,
            'end': real_end,
            'valid': True
        }

    def _create_premiere_xml(self, output_dir, clips, fps, width, height, xml_filename="import_xml.xml"):
        """Gera um XML (FCP 7 XML) compatível com Premiere Pro para importar a sequência."""
        import math
        
        # Determine Timebase & NTSC
        base_rate = int(round(fps))
        is_ntsc = "TRUE" if abs(fps - base_rate) > 0.01 else "FALSE"
        
        # width/height passed as args
        
        lines = []
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        lines.append('<!DOCTYPE xmeml>')
        lines.append('<xmeml version="4">')
        lines.append('<bin>')
        lines.append(f'\t<name>{self.current_filename}</name>') # Bin Name matches file
        lines.append('\t<children>')
        lines.append(f'\t<sequence id="{uuid.uuid4()}">')
        lines.append(f'\t\t<name>{self.current_filename}</name>') # Sequence Name matches file
        lines.append(f'\t\t<rate><timebase>{base_rate}</timebase><ntsc>{is_ntsc}</ntsc></rate>')
        lines.append('\t\t<media>')
        lines.append('\t\t<video>')
        lines.append(f'\t\t\t<format><samplecharacteristics><rate><timebase>{base_rate}</timebase><ntsc>{is_ntsc}</ntsc></rate><width>{width}</width><height>{height}</height><pixelaspectratio>square</pixelaspectratio></samplecharacteristics></format>')
        
        # Track 1 (Empty - Reserved for Footage)
        lines.append('\t\t\t<track>')
        lines.append('\t\t\t</track>')
        
        # Track 2 (Subtitles)
        lines.append('\t\t\t<track>')

        for clip in clips:
            # Convert Seconds to Frames
            start_frame = int(clip['start'] * fps)
            end_frame = int(clip['end'] * fps)
            duration = end_frame - start_frame
            if duration < 1: duration = 1
            
            name = clip['name']
            # Absolute path with forward slashes usually works best for XML
            path = clip['path'].replace("\\", "/") 
            # Fix Drive colon for URI if needed, but Premiere often accepts standard paths in XML block <pathurl>file://localhost/C:/Path...</pathurl>
            # Let's try simple file://localhost/{path} assuming path starts with C:/
            if not path.startswith("/"):
                 path = "/" + path
            
            lines.append(f'\t\t\t\t<clipitem id="{name}">')
            lines.append(f'\t\t\t\t\t<name>{name}</name>')
            lines.append(f'\t\t\t\t\t<duration>{duration}</duration>')
            lines.append(f'\t\t\t\t\t<rate><timebase>{base_rate}</timebase><ntsc>{is_ntsc}</ntsc></rate>')
            lines.append(f'\t\t\t\t\t<start>{start_frame}</start>')
            lines.append(f'\t\t\t\t\t<end>{end_frame}</end>')
            lines.append(f'\t\t\t\t\t<in>0</in>')
            lines.append(f'\t\t\t\t\t<out>{duration}</out>')
            lines.append(f'\t\t\t\t\t<file id="file_{name}">')
            lines.append(f'\t\t\t\t\t\t<name>{name}</name>')
            lines.append(f'\t\t\t\t\t\t<pathurl>file://localhost{path}</pathurl>')
            lines.append(f'\t\t\t\t\t\t<rate><timebase>{base_rate}</timebase><ntsc>{is_ntsc}</ntsc></rate>')
            lines.append(f'\t\t\t\t\t\t<media><video><samplecharacteristics><width>{width}</width><height>{height}</height></samplecharacteristics></video></media>')
            lines.append(f'\t\t\t\t\t</file>')
            lines.append(f'\t\t\t\t</clipitem>')

        lines.append('\t\t\t</track>')
        lines.append('\t\t</video>')
        lines.append('\t\t</media>')
        lines.append('\t</sequence>')
        lines.append('\t</children>')
        lines.append('</bin>')
        lines.append('</xmeml>')
        
        with open(os.path.join(output_dir, xml_filename), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    
    def _create_premiere_graphics_xml(self, output_dir, clips_v2, clips_v3, fps, width, height, vert_pos_px, horiz_pos_px, seq_name="Sequence 01", xml_filename="premiere_graphics.xml"):
        """Generate Premiere Pro Graphics XML with native editable text - Strict Structure"""
        import math
        
        # Calculate Normalized Position for Premiere (0.0 - 1.0)
        # X is (Horiz Pos / Width)
        pos_x_norm = horiz_pos_px / width
            
        # Y is (Height - BottomMargin) / Height
        # Note: Premiere coordinates can be inverted depending on version, but usually 0=top, 1=bottom.
        # User said "1000 em posição Y e foi" (1000px from top in 1080p is bottom).
        # My formula: (height - vert_pos_px)/height. If vert_pos_px=200, (1080-200)/1080 = 0.81 (Bottom).
        # This seems correct.
        
        pos_y_norm = (height - vert_pos_px) / height
        
        # Ensure it's not out of bounds
        pos_x_norm = max(0.0, min(1.0, pos_x_norm))
        pos_y_norm = max(0.0, min(1.0, pos_y_norm))
        
        position_value = f"-91445760000000000,{pos_x_norm:.6f}:{pos_y_norm:.6f},0,0,0,0,0,0,5,4,0,0,0,0"

        # Determine Timebase & NTSC
        base_rate = int(round(fps))
        is_ntsc = "TRUE" if abs(fps - base_rate) > 0.01 else "FALSE"
        
        lines = []
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        lines.append('<!-- Generated by Subtitle Studio - Developed by Rafael Godoy -->')
        lines.append('<!DOCTYPE xmeml>')
        lines.append('<xmeml version="5">')
        lines.append('\t<project>')
        lines.append('\t\t<name>Graphics Sequence</name>')
        lines.append('\t\t<children>')
        lines.append('\t\t\t<sequence id="sequence-1">')
        lines.append(f'\t\t\t\t<name>{seq_name}</name>')
        lines.append(f'\t\t\t\t<duration>{int(clips_v2[-1]["end"] * base_rate) + 100 if clips_v2 else base_rate}</duration>')
        lines.append(f'\t\t\t\t<rate><timebase>{base_rate}</timebase><ntsc>{is_ntsc}</ntsc></rate>')
        lines.append(f'\t\t\t\t<media>')
        lines.append(f'\t\t\t\t\t<video>')
        lines.append(f'\t\t\t\t\t\t<format>')
        lines.append(f'\t\t\t\t\t\t\t<samplecharacteristics>')
        lines.append(f'\t\t\t\t\t\t\t\t<rate><timebase>{base_rate}</timebase><ntsc>{is_ntsc}</ntsc></rate>')
        lines.append(f'\t\t\t\t\t\t\t\t<width>{width}</width>')
        lines.append(f'\t\t\t\t\t\t\t\t<height>{height}</height>')
        lines.append(f'\t\t\t\t\t\t\t\t<anamorphic>FALSE</anamorphic>')
        lines.append(f'\t\t\t\t\t\t\t\t<pixelaspectratio>square</pixelaspectratio>')
        lines.append(f'\t\t\t\t\t\t\t</samplecharacteristics>')
        lines.append(f'\t\t\t\t\t\t</format>')
        
        # Track 1 (Empty - V1)
        lines.append(f'\t\t\t\t\t\t<track>')
        lines.append(f'\t\t\t\t\t\t</track>')
        
        # Track 3 (Graphics - V3 - Highlights Overlay)
        lines.append(f'\t\t\t\t\t\t<track>')
        if clips_v3:
            for i, clip in enumerate(clips_v3):
                idx = clip['index']
                text = clip['text']
                # Escape XML entities for name
                safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")[:50]
                payload = clip['payload']
                
                start_frame = int(round(clip['start'] * base_rate))
                end_frame = int(round(clip['end'] * base_rate))
                duration_frames = end_frame - start_frame
                if duration_frames < 1: duration_frames = 1
                
                # Use offset IDs (e.g. +20000) to avoid conflict
                cid = idx + 20000
                clip_id = f"clipitem-{cid}"
                file_id = f"file-{cid}"
                
                lines.append(f'\t\t\t\t\t\t\t<clipitem id="{clip_id}">')
                lines.append(f'\t\t\t\t\t\t\t\t<masterclipid>masterclip-{cid}</masterclipid>')
                lines.append(f'\t\t\t\t\t\t\t\t<name>{safe_text} (HL)</name>')
                lines.append(f'\t\t\t\t\t\t\t\t<enabled>TRUE</enabled>')
                lines.append(f'\t\t\t\t\t\t\t\t<duration>{duration_frames}</duration>')
                lines.append(f'\t\t\t\t\t\t\t\t<rate><timebase>{base_rate}</timebase><ntsc>{is_ntsc}</ntsc></rate>')
                lines.append(f'\t\t\t\t\t\t\t\t<start>{start_frame}</start>')
                lines.append(f'\t\t\t\t\t\t\t\t<end>{end_frame}</end>')
                lines.append(f'\t\t\t\t\t\t\t\t<in>0</in>')
                lines.append(f'\t\t\t\t\t\t\t\t<out>{duration_frames}</out>')
                lines.append(f'\t\t\t\t\t\t\t\t<alphatype>straight</alphatype>')
                
                # File Reference (Dummy Graphic File)
                lines.append(f'\t\t\t\t\t\t\t\t<file id="{file_id}">')
                lines.append(f'\t\t\t\t\t\t\t\t\t<name>GraphicHL</name>')
                lines.append(f'\t\t\t\t\t\t\t\t\t<mediaSource>GraphicAndType</mediaSource>')
                lines.append(f'\t\t\t\t\t\t\t\t\t<rate><timebase>{base_rate}</timebase><ntsc>{is_ntsc}</ntsc></rate>')
                lines.append(f'\t\t\t\t\t\t\t\t\t<timecode><rate><timebase>{base_rate}</timebase><ntsc>{is_ntsc}</ntsc></rate><string>00;00;00;00</string><frame>0</frame><displayformat>DF</displayformat></timecode>')
                lines.append(f'\t\t\t\t\t\t\t\t\t<media><video><samplecharacteristics><rate><timebase>{base_rate}</timebase><ntsc>{is_ntsc}</ntsc></rate><width>{width}</width><height>{height}</height><pixelaspectratio>square</pixelaspectratio></samplecharacteristics></video></media>')
                lines.append(f'\t\t\t\t\t\t\t\t</file>')
                
                # Filter 1: Basic Motion
                lines.append(f'\t\t\t\t\t\t\t\t<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype><mediatype>video</mediatype><pproBypass>false</pproBypass>')
                lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>scale</parameterid><name>Scale</name><valuemin>0</valuemin><valuemax>1000</valuemax><value>100</value></parameter>')
                lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>rotation</parameterid><name>Rotation</name><valuemin>-8640</valuemin><valuemax>8640</valuemax><value>0</value></parameter>')
                lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>center</parameterid><name>Center</name><value><horiz>0</horiz><vert>0</vert></value></parameter>')
                lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>centerOffset</parameterid><name>Anchor Point</name><value><horiz>0</horiz><vert>0</vert></value></parameter>')
                lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>antiflicker</parameterid><name>Anti-flicker Filter</name><valuemin>0.0</valuemin><valuemax>1.0</valuemax><value>0</value></parameter>')
                lines.append(f'\t\t\t\t\t\t\t\t</effect></filter>')
                
                # Filter 2: GraphicAndType
                lines.append(f'\t\t\t\t\t\t\t\t<filter><effect><name>{safe_text} (HL)</name><effectid>GraphicAndType</effectid><effectcategory>graphic</effectcategory><effecttype>filter</effecttype><mediatype>video</mediatype><pproBypass>false</pproBypass>')
                
                # Source Text
                lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>1</parameterid><name>Source Text</name><value>{payload}</value></parameter>')
                
                # V3 Positioning (Custom or Default)
                # Check if 'custom_pos_x' exists in clip
                hl_pos_val = position_value # Default
                
                if 'custom_pos_x' in clip:
                    cx = clip['custom_pos_x']
                    cx_norm = cx / width
                    cx_norm = max(0.0, min(1.0, cx_norm))
                    hl_pos_val = f"-91445760000000000,{cx_norm:.6f}:{pos_y_norm:.6f},0,0,0,0,0,0,5,4,0,0,0,0"

                # Default Params Overlay
                lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>2</parameterid><name>Transform</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>11</ParameterControlType><value>-91445760000000000,false,0,0,0,0,0,0</value></parameter>')
                lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>3</parameterid><name>Position</name><IsTimeVarying>false</IsTimeVarying><value>{hl_pos_val}</value></parameter>')
                lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>4</parameterid><name>Scale</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>2</ParameterControlType><value>-91445760000000000,100.,0,0,0,0,0,0</value></parameter>')
                lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>5</parameterid><name>Horizontal Scale</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>2</ParameterControlType><value>-91445760000000000,100.,0,0,0,0,0,0</value></parameter>')
                lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>6</parameterid><name> </name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>4</ParameterControlType><value>-91445760000000000,true,0,0,0,0,0,0</value></parameter>')
                lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>7</parameterid><name>Rotation</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>3</ParameterControlType><value>-91445760000000000,0.,0,0,0,0,0,0</value></parameter>')
                lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>8</parameterid><name>Opacity</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>2</ParameterControlType><value>-91445760000000000,100.,0,0,0,0,0,0</value></parameter>')
                lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>9</parameterid><name>Anchor Point</name><IsTimeVarying>false</IsTimeVarying><value>-91445760000000000,0:0,0,0,0,0,0,0,5,4,0,0,0,0</value></parameter>')
                
                lines.append(f'\t\t\t\t\t\t\t\t</effect></filter>')
                lines.append(f'\t\t\t\t\t\t\t</clipitem>')
        
        lines.append(f'\t\t\t\t\t\t</track>')
        
        # Track 2 (Graphics - V2)
        lines.append(f'\t\t\t\t\t\t<track>')
        
        # Add clips
        for i, clip in enumerate(clips_v2):
            idx = clip['index']
            text = clip['text']
            # Escape XML entities in text for name
            safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")[:50]
            payload = clip['payload']
            
            start_frame = int(round(clip['start'] * base_rate))
            end_frame = int(round(clip['end'] * base_rate))
            duration_frames = end_frame - start_frame
            if duration_frames < 1: duration_frames = 1
            
            clip_id = f"clipitem-{idx+100}"
            file_id = f"file-{idx+100}"
            
            lines.append(f'\t\t\t\t\t\t\t<clipitem id="{clip_id}">')
            lines.append(f'\t\t\t\t\t\t\t\t<masterclipid>masterclip-{idx+100}</masterclipid>')
            lines.append(f'\t\t\t\t\t\t\t\t<name>{safe_text}</name>')
            lines.append(f'\t\t\t\t\t\t\t\t<enabled>TRUE</enabled>')
            lines.append(f'\t\t\t\t\t\t\t\t<duration>{duration_frames}</duration>')
            lines.append(f'\t\t\t\t\t\t\t\t<rate><timebase>{base_rate}</timebase><ntsc>{is_ntsc}</ntsc></rate>')
            lines.append(f'\t\t\t\t\t\t\t\t<start>{start_frame}</start>')
            lines.append(f'\t\t\t\t\t\t\t\t<end>{end_frame}</end>')
            lines.append(f'\t\t\t\t\t\t\t\t<in>0</in>')
            lines.append(f'\t\t\t\t\t\t\t\t<out>{duration_frames}</out>')
            lines.append(f'\t\t\t\t\t\t\t\t<alphatype>straight</alphatype>')
            
            # File Reference (Dummy Graphic File)
            lines.append(f'\t\t\t\t\t\t\t\t<file id="{file_id}">')
            lines.append(f'\t\t\t\t\t\t\t\t\t<name>Graphic</name>')
            lines.append(f'\t\t\t\t\t\t\t\t\t<mediaSource>GraphicAndType</mediaSource>')
            lines.append(f'\t\t\t\t\t\t\t\t\t<rate><timebase>{base_rate}</timebase><ntsc>{is_ntsc}</ntsc></rate>')
            lines.append(f'\t\t\t\t\t\t\t\t\t<timecode><rate><timebase>{base_rate}</timebase><ntsc>{is_ntsc}</ntsc></rate><string>00;00;00;00</string><frame>0</frame><displayformat>DF</displayformat></timecode>')
            lines.append(f'\t\t\t\t\t\t\t\t\t<media><video><samplecharacteristics><rate><timebase>{base_rate}</timebase><ntsc>{is_ntsc}</ntsc></rate><width>{width}</width><height>{height}</height><pixelaspectratio>square</pixelaspectratio></samplecharacteristics></video></media>')
            lines.append(f'\t\t\t\t\t\t\t\t</file>')
            
            # Filter 1: Basic Motion (Standard)
            lines.append(f'\t\t\t\t\t\t\t\t<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype><mediatype>video</mediatype><pproBypass>false</pproBypass>')
            lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>scale</parameterid><name>Scale</name><valuemin>0</valuemin><valuemax>1000</valuemax><value>100</value></parameter>')
            lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>rotation</parameterid><name>Rotation</name><valuemin>-8640</valuemin><valuemax>8640</valuemax><value>0</value></parameter>')
            lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>center</parameterid><name>Center</name><value><horiz>0</horiz><vert>0</vert></value></parameter>')
            lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>centerOffset</parameterid><name>Anchor Point</name><value><horiz>0</horiz><vert>0</vert></value></parameter>')
            lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>antiflicker</parameterid><name>Anti-flicker Filter</name><valuemin>0.0</valuemin><valuemax>1.0</valuemax><value>0</value></parameter>')
            lines.append(f'\t\t\t\t\t\t\t\t</effect></filter>')
            
            # Filter 2: GraphicAndType (The ACTUAL text)
            lines.append(f'\t\t\t\t\t\t\t\t<filter><effect><name>{safe_text}</name><effectid>GraphicAndType</effectid><effectcategory>graphic</effectcategory><effecttype>filter</effecttype><mediatype>video</mediatype><pproBypass>false</pproBypass>')
            
            # Parameter 1: Source Text (OUR PAYLOAD)
            lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>1</parameterid><name>Source Text</name><value>{payload}</value></parameter>')
            
            # Default Parameters (2-12) to match standard graphic
            lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>2</parameterid><name>Transform</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>11</ParameterControlType><value>-91445760000000000,false,0,0,0,0,0,0</value></parameter>')
            lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>3</parameterid><name>Position</name><IsTimeVarying>false</IsTimeVarying><value>{position_value}</value></parameter>') # Using Calculated Position
            lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>4</parameterid><name>Scale</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>2</ParameterControlType><value>-91445760000000000,100.,0,0,0,0,0,0</value></parameter>')
            lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>5</parameterid><name>Horizontal Scale</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>2</ParameterControlType><value>-91445760000000000,100.,0,0,0,0,0,0</value></parameter>')
            lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>6</parameterid><name> </name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>4</ParameterControlType><value>-91445760000000000,true,0,0,0,0,0,0</value></parameter>')
            lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>7</parameterid><name>Rotation</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>3</ParameterControlType><value>-91445760000000000,0.,0,0,0,0,0,0</value></parameter>')
            lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>8</parameterid><name>Opacity</name><IsTimeVarying>false</IsTimeVarying><ParameterControlType>2</ParameterControlType><value>-91445760000000000,100.,0,0,0,0,0,0</value></parameter>')
            lines.append(f'\t\t\t\t\t\t\t\t\t<parameter authoringApp="PremierePro"><parameterid>9</parameterid><name>Anchor Point</name><IsTimeVarying>false</IsTimeVarying><value>-91445760000000000,0:0,0,0,0,0,0,0,5,4,0,0,0,0</value></parameter>')
            # Parameters 10, 11, 12 skip if possible or add generic
            
            lines.append(f'\t\t\t\t\t\t\t\t</effect></filter>')
            lines.append(f'\t\t\t\t\t\t\t</clipitem>')
            
        lines.append('\t\t\t\t\t\t</track>')
        lines.append('\t\t\t\t\t</video>')
        lines.append('\t\t\t\t</media>')
        lines.append('\t\t\t</sequence>')
        lines.append('\t\t</children>')
        lines.append('\t</project>')
        lines.append('</xmeml>')
        
        with open(os.path.join(output_dir, xml_filename), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))



    def _update_presets_combo(self):
        """Updates the presets dropdown from file, merging defaults."""
        try:
            # Fallback presets (used only if subtitle_presets.json is missing or incomplete)
            # JSON file presets will OVERRIDE these defaults after merge
            defaults = {
                "01. Padrão (Clean)": {
                    "font_name": "Arial", "font_size": 84, "bold": 0, "italic": 0, "upper": 0, "underline": 0,
                    "color_base": "#FFFFFF", "color_high": "#FFD700", "color_outline": "#000000", "color_shadow": "#000000", "color_bg": "#000000",
                    "outline_thick": 2, "shadow_size": 2,
                    "border_style": "1 - Contorno", "alignment": "Centro", 
                    "bg_only": 0, "bg_opacity": 75, "bg_radius": 0, "x_offset": 0, "width_scale": 1.0,
                    "mode": "highlight", "words_block": 3, "remove_punctuation": 1, "horiz_pos": 540, "vert_pos": 200
                },
                "02. MrBeast (Impacto)": {
                    "font_name": "Arial", "font_size": 104, "bold": 1, "italic": 0, "upper": 1, "underline": 0,
                    "color_base": "#FFFFFF", "color_high": "#00FF00", "color_outline": "#000000", "color_shadow": "#000000", "color_bg": "#000000",
                    "outline_thick": 8, "shadow_size": 0, 
                    "border_style": "1 - Contorno", "alignment": "Centro", 
                    "bg_only": 0, "x_offset": 0, "width_scale": 1.0,
                    "mode": "highlight", "words_block": 1, "remove_punctuation": 1, "horiz_pos": 540, "vert_pos": 500
                },
                "03. TikTok (Caixa Preta)": {
                    "font_name": "Arial", "font_size": 72, "bold": 1, "italic": 0, "upper": 0, "underline": 0,
                    "color_base": "#FFFFFF", "color_high": "#FF0055", "color_outline": "#000000", "color_shadow": "#000000", "color_bg": "#000000",
                    "outline_thick": 0, "shadow_size": 0,
                    "border_style": "3 - Caixa Opaca", "alignment": "Centro", 
                    "bg_opacity": 85, "bg_radius": 15, "bg_only": 0,
                    "mode": "highlight", "words_block": 2, "remove_punctuation": 1, "horiz_pos": 540, "vert_pos": 200
                },
                "04. Hormozi (Amarelo/Bold)": {
                    "font_name": "Arial", "font_size": 90, "bold": 1, "italic": 0, "upper": 1, "underline": 0,
                    "color_base": "#FFD700", "color_high": "#FFFFFF", "color_outline": "#000000", "color_shadow": "#000000", "color_bg": "#000000",
                    "outline_thick": 4, "shadow_size": 2,
                    "border_style": "1 - Contorno", "alignment": "Centro", "bg_only": 0,
                    "mode": "highlight", "words_block": 2, "remove_punctuation": 1
                },
                "05. Highlight Box (Alpha)": {
                    "font_name": "Arial", "font_size": 84, "bold": 1, "italic": 0, "upper": 0, "underline": 0,
                    "color_base": "#FFFFFF", "color_high": "#FFFFFF", "color_outline": "#000000", "color_shadow": "#000000", "color_bg": "#FF0055",
                    "outline_thick": 2, "shadow_size": 0,
                    "border_style": "3 - Caixa Opaca", "alignment": "Centro", 
                    "bg_only": 1, "bg_opacity": 40, "bg_radius": 10, "x_offset": 0, "width_scale": 1.0,
                    "mode": "highlight", "words_block": 3, "remove_punctuation": 1
                },
                "06. Hacker (Terminal)": {
                    "font_name": "Consolas", "font_size": 76, "bold": 1, "italic": 0, "upper": 0, "underline": 0,
                    "color_base": "#00FF00", "color_high": "#FFFFFF", "color_outline": "#003300", "color_shadow": "#000000", "color_bg": "#000000",
                    "outline_thick": 1, "shadow_size": 0,
                    "border_style": "3 - Caixa Opaca", "bg_opacity": 90, "alignment": "Esquerda", 
                    "x_offset": -200, "bg_only": 0,
                    "mode": "word_by_word", "words_block": 1, "remove_punctuation": 0
                },
                "07. Netflix (Elegante)": {
                    "font_name": "Arial", "font_size": 78, "bold": 0, "italic": 0, "upper": 0, "underline": 0,
                    "color_base": "#FFFFFF", "color_high": "#FFEE00", "color_outline": "#000000", "color_shadow": "#000000", "color_bg": "#000000",
                    "outline_thick": 0, "shadow_size": 3,
                    "border_style": "1 - Contorno", "alignment": "Centro", "bg_only": 0,
                    "mode": "no_highlight", "words_block": 7, "remove_punctuation": 0, "vert_pos": 100
                },
                "08. Cyberpunk (Neon)": {
                    "font_name": "Arial", "font_size": 90, "bold": 1, "italic": 1, "upper": 1, "underline": 0,
                    "color_base": "#00FFFF", "color_high": "#FF00FF", "color_outline": "#000000", "color_shadow": "#FF00FF", "color_bg": "#000000",
                    "outline_thick": 3, "shadow_size": 5,
                    "border_style": "1 - Contorno", "alignment": "Centro", "bg_only": 0,
                    "mode": "highlight", "words_block": 2, "remove_punctuation": 1
                },
                "09. Big Red (Alerta)": {
                    "font_name": "Arial", "font_size": 110, "bold": 1, "italic": 0, "upper": 1, "underline": 0,
                    "color_base": "#FF0000", "color_high": "#FFFFFF", "color_outline": "#FFFFFF", "color_shadow": "#000000", "color_bg": "#000000",
                    "outline_thick": 4, "shadow_size": 2,
                    "border_style": "1 - Contorno", "alignment": "Centro", "bg_only": 0,
                    "mode": "highlight", "words_block": 1, "remove_punctuation": 1
                },
                "10. Blue Tech (Corp)": {
                    "font_name": "Arial", "font_size": 80, "bold": 1, "italic": 0, "upper": 0, "underline": 0,
                    "color_base": "#FFFFFF", "color_high": "#00AAFF", "color_outline": "#000000", "color_shadow": "#000000", "color_bg": "#003366",
                    "outline_thick": 0, "shadow_size": 0,
                    "border_style": "3 - Caixa Opaca", "alignment": "Centro", 
                    "bg_only": 1, "bg_opacity": 85, "bg_radius": 5,
                    "mode": "highlight", "words_block": 3, "remove_punctuation": 0
                }
            }

            presets_loaded = {}
            if os.path.exists("subtitle_presets.json"):
                try:
                    with open("subtitle_presets.json", "r", encoding='utf-8') as f:
                        presets_loaded = json.load(f)
                except:
                    presets_loaded = {}
            
            # Merge: Start with defaults, then override with user's JSON presets
            # This way, JSON presets take priority and defaults only fill missing presets
            merged_presets = defaults.copy()
            merged_presets.update(presets_loaded)
            
            # Save back combined (so new defaults appear in JSON for user to edit)
            with open("subtitle_presets.json", "w", encoding='utf-8') as f:
                json.dump(merged_presets, f, indent=4, ensure_ascii=False)
            
            self.presets_data = merged_presets
            
            vals = sorted(list(self.presets_data.keys()))
            self.combo_presets.configure(values=vals)
            if vals: self.combo_presets.set(vals[0])
            
        except Exception as e:
            print(f"Erro presets: {e}")
            self.presets_data = {}

    def get_ui_state(self):
        """Serializes current UI state to dict."""
        return {
            "font_name": self.entry_font_name.get(),
            "font_size": self.entry_font_size.get(),
            "highlight_size": self.entry_highlight_size.get(),
            "bold": self.check_bold.get(),
            "italic": self.check_italic.get(),
            "upper": self.check_uppercase.get(),
            "underline": self.check_underline.get(),
            "color_base": self.val_base_color,
            "color_high": self.val_highlight_color,
            "color_outline": self.val_outline_color,
            "color_shadow": self.val_shadow_color,
            "color_bg": self.val_background_color,
            "outline_thick": self.entry_outline_thick.get(),
            "shadow_size": self.entry_shadow_size.get(),
            "bg_opacity": self.slider_bg_op.get(),
            "bg_size": self.slider_bg_sz.get(),
            "bg_radius": self.slider_bg_radius.get(),
            "border_style": self.dropdown_border_style.get(),
            "outline_pos": self.dropdown_outline_pos.get(),
            "alignment": self.dropdown_align.get(),
            "bg_only": self.check_bg_only.get(),
            # "ghost_mode": self.check_ghost_mode.get(), # Removed
            "under_only": self.check_under_only.get(),
            "x_offset": self.entry_x_offset.get(),
            "width_scale": self.slider_width_scale.get(),
            # Logic
            "mode": self.dropdown_mode.get(),
            "words_block": self.entry_words_block.get(),
            "remove_punctuation": self.check_punctuation.get(),
            "gap_limit": self.entry_gap_limit.get(),
            "horiz_pos": self.entry_horiz_pos.get(),
            "vert_pos": self.entry_vert_pos.get()
        }

    def apply_ui_state(self, data):
        """Applies dict to UI."""
        if not data: return
        try:
            if "font_name" in data: 
                self.entry_font_name.delete(0, "end")
                self.entry_font_name.insert(0, data["font_name"])
            if "font_size" in data:
                self.entry_font_size.delete(0, "end")
                self.entry_font_size.insert(0, str(data["font_size"]))
            if "highlight_size" in data:
                self.entry_highlight_size.delete(0, "end")
                self.entry_highlight_size.insert(0, str(data["highlight_size"]))
            
            self.check_bold.select() if data.get("bold") else self.check_bold.deselect()
            self.check_italic.select() if data.get("italic") else self.check_italic.deselect()
            self.check_uppercase.select() if data.get("upper") else self.check_uppercase.deselect()
            self.check_underline.select() if data.get("underline") else self.check_underline.deselect()
            
            # Colors - Check if key exists AND is valid hex
            if "color_base" in data: self._set_color_btn(self.btn_base_color, data["color_base"], "val_base_color")
            if "color_high" in data: self._set_color_btn(self.btn_highlight_color, data["color_high"], "val_highlight_color")
            if "color_outline" in data: self._set_color_btn(self.btn_outline_color, data["color_outline"], "val_outline_color")
            if "color_shadow" in data: self._set_color_btn(self.btn_shadow_color, data["color_shadow"], "val_shadow_color")
            if "color_bg" in data: self._set_color_btn(self.btn_background_color, data["color_bg"], "val_background_color")
            
            if "outline_thick" in data:
                self.entry_outline_thick.delete(0, "end")
                self.entry_outline_thick.insert(0, str(data["outline_thick"]))
            if "shadow_size" in data:
                self.entry_shadow_size.delete(0, "end")
                self.entry_shadow_size.insert(0, str(data["shadow_size"]))
                
            if "bg_opacity" in data: self.slider_bg_op.set(float(data["bg_opacity"]))
            if "bg_size" in data: self.slider_bg_sz.set(float(data["bg_size"]))
            if "bg_radius" in data: self.slider_bg_radius.set(float(data["bg_radius"]))
            
            if "border_style" in data: self.dropdown_border_style.set(data["border_style"])
            if "outline_pos" in data: self.dropdown_outline_pos.set(data["outline_pos"])
            if "alignment" in data: self.dropdown_align.set(data["alignment"])
            
            self.check_bg_only.select() if data.get("bg_only") else self.check_bg_only.deselect()
            # self.check_ghost_mode.select() if data.get("ghost_mode") else self.check_ghost_mode.deselect() # Removed
            self.check_under_only.select() if data.get("under_only") else self.check_under_only.deselect()
            
            if "x_offset" in data:
                self.entry_x_offset.delete(0, "end")
                self.entry_x_offset.insert(0, str(data["x_offset"]))
            if "width_scale" in data:
                self.slider_width_scale.set(float(data["width_scale"]))
            
            # Logic & Layout
            if "mode" in data: self.dropdown_mode.set(data["mode"])
            if "words_block" in data:
                self.entry_words_block.delete(0, "end")
                self.entry_words_block.insert(0, str(data["words_block"]))
            if "remove_punctuation" in data:
                self.check_punctuation.select() if data.get("remove_punctuation") else self.check_punctuation.deselect()
            if "gap_limit" in data:
                self.entry_gap_limit.delete(0, "end")
                self.entry_gap_limit.insert(0, str(data["gap_limit"]))
            
            # Position
            if "horiz_pos" in data:
                self.entry_horiz_pos.delete(0, "end")
                self.entry_horiz_pos.insert(0, str(data["horiz_pos"]))
            if "vert_pos" in data:
                self.entry_vert_pos.delete(0, "end")
                self.entry_vert_pos.insert(0, str(data["vert_pos"]))
             
        except Exception as e:
            print(f"Error applying preset: {e}")

    def _set_color_btn(self, btn, color, attr_name):
        setattr(self, attr_name, color)
        btn.configure(fg_color=color, text=color)  # Update both color AND text

    def load_selected_preset(self, choice):
        if choice in self.presets_data:
            self.apply_ui_state(self.presets_data[choice])

    def save_current_preset(self):
        name = ctk.CTkInputDialog(text="Nome do Preset:", title="Salvar Preset").get_input()
        if name:
            data = self.get_ui_state()
            self.presets_data[name] = data
            with open("subtitle_presets.json", "w", encoding='utf-8') as f:
                json.dump(self.presets_data, f, indent=4)
            self._update_presets_combo()
            self.combo_presets.set(name)
            
    def delete_current_preset(self):
        name = self.combo_presets.get()
        if name and name in self.presets_data:
            del self.presets_data[name]
            with open("subtitle_presets.json", "w", encoding='utf-8') as f:
                json.dump(self.presets_data, f, indent=4)
            self._update_presets_combo()

if __name__ == "__main__":
    app = SubtitleStudioApp()
    app.mainloop()
