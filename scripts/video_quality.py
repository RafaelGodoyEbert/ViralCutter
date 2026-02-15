# Video Quality Enhancement Module
"""
Provides quality enhancement functions for ViralCutter.
Uses Lanczos interpolation, Denoise, Color Grading and Unsharp Mask for better upscaling quality.
"""

import cv2
import numpy as np

# Quality presets for video enhancement
QUALITY_PRESETS = {
    "standard": {
        "interpolation": cv2.INTER_LANCZOS4,
        "denoise_strength": 0.0,  # No denoise
        "auto_illumination": False,  # No auto-light
        "unsharp_kernel": (0, 0),  # Auto kernel
        "unsharp_sigma": 3.0,
        "unsharp_strength": 0.8,
        "contrast": 1.0,
        "saturation": 1.0,
        "crf": 23,
        "max_bitrate": "5M",
    },
    "high": {
        "interpolation": cv2.INTER_LANCZOS4,
        "denoise_strength": 1.5,  # Light denoise
        "auto_illumination": True,  # Opus-style auto brightness/contrast
        "auto_illumination_clip_limit": 2.0,  # CLAHE clip limit (subtle)
        "unsharp_kernel": (5, 5),  # Fixed kernel — Visual Opus (FFmpeg unsharp=5:5:1.0)
        "unsharp_sigma": 1.0,
        "unsharp_strength": 1.0,  # Stronger sharpening for upscale recovery
        "contrast": 1.05,
        "saturation": 1.1,
        "crf": 18,
        "max_bitrate": "25M",
    },
    "max": {
        "interpolation": cv2.INTER_LANCZOS4,
        "denoise_strength": 2.0,  # Stronger denoise
        "auto_illumination": True,  # Opus-style auto brightness/contrast
        "auto_illumination_clip_limit": 3.0,  # Higher clip = more correction
        "unsharp_kernel": (5, 5),  # Fixed kernel — Visual Opus
        "unsharp_sigma": 1.0,
        "unsharp_strength": 1.2,  # Aggressive sharpening
        "contrast": 1.08,
        "saturation": 1.15,
        "crf": 15,
        "max_bitrate": "35M",
    }
}

# Default preset
DEFAULT_PRESET = "high"


def get_quality_preset(name=None):
    """Get quality preset by name. Returns 'high' preset by default."""
    if name is None:
        name = DEFAULT_PRESET
    return QUALITY_PRESETS.get(name, QUALITY_PRESETS[DEFAULT_PRESET])


def apply_denoise(frame, strength=1.5):
    """
    Apply fast denoise filter to remove compression artifacts BEFORE upscaling.
    Uses bilateral filter which preserves edges while smoothing.
    
    Args:
        frame: Input BGR frame (numpy array)
        strength: Denoise strength (0.0-3.0, default 1.5)
                  0.0 = off, 1.5 = light, 2.0+ = aggressive
    
    Returns:
        Denoised frame
    """
    if strength <= 0:
        return frame
    
    # Bilateral filter: preserves edges while removing noise
    # d=5: diameter of pixel neighborhood
    # sigmaColor: higher = more colors are mixed
    # sigmaSpace: higher = pixels farther away influence each other
    d = 5
    sigma_color = int(strength * 50)  # 75 for strength 1.5
    sigma_space = int(strength * 50)
    
    denoised = cv2.bilateralFilter(frame, d, sigma_color, sigma_space)
    return denoised


def apply_auto_illumination(frame, clip_limit=2.0):
    """
    Opus-style automatic illumination adjustment.
    Uses CLAHE (Contrast Limited Adaptive Histogram Equalization) on the
    luminance channel to normalize brightness and contrast automatically.
    Preserves colors while fixing dark/overexposed areas.
    
    Args:
        frame: Input BGR frame (numpy array)
        clip_limit: CLAHE clip limit (1.0-4.0, default 2.0)
                    2.0 = subtle/natural, 3.0 = stronger correction
    
    Returns:
        Illumination-corrected frame
    """
    # Convert to LAB color space (L = luminance, A/B = color)
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    # Apply CLAHE only to luminance — preserves original colors
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    l_corrected = clahe.apply(l_channel)
    
    # Merge back and convert to BGR
    lab_corrected = cv2.merge([l_corrected, a_channel, b_channel])
    result = cv2.cvtColor(lab_corrected, cv2.COLOR_LAB2BGR)
    
    return result


def apply_color_grading(frame, contrast=1.05, saturation=1.1):
    """
    Apply color grading to make video look more "expensive".
    Higher contrast = perceived sharpness. Higher saturation = more vibrant.
    
    Args:
        frame: Input BGR frame (numpy array)
        contrast: Contrast multiplier (1.0 = no change, 1.05 = 5% increase)
        saturation: Saturation multiplier (1.0 = no change, 1.1 = 10% increase)
    
    Returns:
        Color graded frame
    """
    if contrast == 1.0 and saturation == 1.0:
        return frame
    
    # Apply contrast (centered around 127)
    if contrast != 1.0:
        frame = cv2.convertScaleAbs(frame, alpha=contrast, beta=127 * (1 - contrast))
    
    # Apply saturation in HSV space
    if saturation != 1.0:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)
        frame = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    
    return frame


def apply_unsharp_mask(frame, strength=1.0, kernel=(5, 5), sigma=1.0):
    """
    Apply unsharp mask to recover sharpness lost during upscaling.
    Calibrated to match FFmpeg unsharp=5:5:1.0 (Visual Opus quality).
    
    Args:
        frame: Input BGR frame (numpy array)
        strength: Sharpening strength (0.0-2.0, default 1.0)
                  0.8 = subtle, 1.0 = Visual Opus, 1.2 = aggressive
        kernel: Gaussian kernel size, e.g. (5,5). Use (0,0) for auto.
        sigma: Gaussian sigma (1.0 = Visual Opus standard)
    
    Returns:
        Sharpened frame
    """
    if strength <= 0:
        return frame
    
    # Create Gaussian blur with configurable kernel and sigma
    gaussian = cv2.GaussianBlur(frame, kernel, sigma)
    
    # Apply unsharp mask: original + strength * (original - blurred)
    sharpened = cv2.addWeighted(frame, 1.0 + strength, gaussian, -strength, 0)
    
    return sharpened


def enhance_frame(frame, preset_name=None):
    """
    Apply full Opus-style enhancement pipeline to a frame.
    Order: Denoise → Auto Illumination → Color Grading → Unsharp (sharpness last!)
    
    Pipeline matches Opus Clip quality filters:
    1. Denoising — removes grain and compression artifacts
    2. Auto Illumination — normalizes brightness/contrast automatically (CLAHE)
    3. Color Grading — contrast + saturation boost for "polished" look
    4. Sharpening — reinforces edges and fine details (unsharp mask)
    
    Args:
        frame: Input BGR frame (already resized to target size)
        preset_name: Quality preset name ('standard', 'high', 'max')
    
    Returns:
        Enhanced frame
    """
    preset = get_quality_preset(preset_name)
    
    # 1. Denoise (clean compression artifacts and grain)
    frame = apply_denoise(frame, preset["denoise_strength"])
    
    # 2. Auto Illumination (normalize brightness/contrast — Opus-style)
    if preset.get("auto_illumination", False):
        clip_limit = preset.get("auto_illumination_clip_limit", 2.0)
        frame = apply_auto_illumination(frame, clip_limit=clip_limit)
    
    # 3. Color grading (contrast + saturation for polished look)
    frame = apply_color_grading(frame, preset["contrast"], preset["saturation"])
    
    # 4. Unsharp mask (sharpness - reinforces edges, ALWAYS LAST)
    frame = apply_unsharp_mask(
        frame, 
        strength=preset["unsharp_strength"],
        kernel=preset.get("unsharp_kernel", (5, 5)),
        sigma=preset.get("unsharp_sigma", 1.0)
    )
    
    return frame


def resize_with_quality(frame, target_size, apply_enhancement=True, preset_name=None):
    """
    Resize frame with high quality (Lanczos) and full enhancement pipeline.
    
    Args:
        frame: Input BGR frame
        target_size: Tuple (width, height)
        apply_enhancement: Whether to apply full enhancement pipeline
        preset_name: Quality preset name ('standard', 'high', 'max')
    
    Returns:
        Resized and optionally enhanced frame
    """
    preset = get_quality_preset(preset_name)
    
    # Use Lanczos interpolation for best upscaling quality
    resized = cv2.resize(frame, target_size, interpolation=preset["interpolation"])
    
    # Apply full enhancement pipeline
    if apply_enhancement:
        resized = enhance_frame(resized, preset_name)
    
    return resized


def get_ffmpeg_quality_args(preset_name=None, encoder_name="libx264"):
    """
    Get FFmpeg arguments for quality encoding.
    
    Args:
        preset_name: Quality preset name
        encoder_name: Video encoder name
    
    Returns:
        List of FFmpeg arguments
    """
    preset = get_quality_preset(preset_name)
    
    args = []
    
    # CRF for quality (only for libx264 and similar)
    if "264" in encoder_name or encoder_name == "libx264":
        args.extend(["-crf", str(preset["crf"])])
    
    # Max bitrate
    args.extend(["-b:v", preset["max_bitrate"]])
    
    # Pixel format for compatibility with YouTube/TikTok
    args.extend(["-pix_fmt", "yuv420p"])
    
    return args
