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
        "unsharp_strength": 0.8,
        "contrast": 1.0,
        "saturation": 1.0,
        "crf": 23,
        "max_bitrate": "5M",
    },
    "high": {
        "interpolation": cv2.INTER_LANCZOS4,
        "denoise_strength": 1.5,  # Light denoise
        "unsharp_strength": 0.8,
        "contrast": 1.05,
        "saturation": 1.1,
        "crf": 18,
        "max_bitrate": "25M",
    },
    "max": {
        "interpolation": cv2.INTER_LANCZOS4,
        "denoise_strength": 2.0,  # Stronger denoise
        "unsharp_strength": 1.0,
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


def apply_unsharp_mask(frame, strength=0.8):
    """
    Apply unsharp mask to recover sharpness lost during upscaling.
    
    Args:
        frame: Input BGR frame (numpy array)
        strength: Sharpening strength (0.0-2.0, default 0.8)
                  0.8 = subtle, 1.0 = normal, 1.2 = aggressive
    
    Returns:
        Sharpened frame
    """
    if strength <= 0:
        return frame
    
    # Create Gaussian blur
    gaussian = cv2.GaussianBlur(frame, (0, 0), 3.0)
    
    # Apply unsharp mask: original + strength * (original - blurred)
    sharpened = cv2.addWeighted(frame, 1.0 + strength, gaussian, -strength, 0)
    
    return sharpened


def enhance_frame(frame, preset_name=None):
    """
    Apply full enhancement pipeline to a frame.
    Order: Denoise -> Color Grading -> Unsharp (sharpness last!)
    
    Args:
        frame: Input BGR frame (already resized to target size)
        preset_name: Quality preset name ('standard', 'high', 'max')
    
    Returns:
        Enhanced frame
    """
    preset = get_quality_preset(preset_name)
    
    # 1. Denoise (clean compression artifacts)
    frame = apply_denoise(frame, preset["denoise_strength"])
    
    # 2. Color grading (contrast + saturation)
    frame = apply_color_grading(frame, preset["contrast"], preset["saturation"])
    
    # 3. Unsharp mask (sharpness - ALWAYS LAST)
    frame = apply_unsharp_mask(frame, preset["unsharp_strength"])
    
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
