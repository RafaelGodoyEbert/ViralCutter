# Video Quality Enhancement Module
"""
Provides quality enhancement functions for ViralCutter.
Uses Lanczos interpolation and Unsharp Mask for better upscaling quality.
"""

import cv2
import numpy as np

# Quality presets for video enhancement
QUALITY_PRESETS = {
    "standard": {
        "interpolation": cv2.INTER_LANCZOS4,
        "unsharp_strength": 0.8,
        "crf": 23,
        "max_bitrate": "5M",
    },
    "high": {
        "interpolation": cv2.INTER_LANCZOS4,
        "unsharp_strength": 1.0,
        "crf": 18,
        "max_bitrate": "8M",
    },
    "max": {
        "interpolation": cv2.INTER_LANCZOS4,
        "unsharp_strength": 1.2,
        "crf": 15,
        "max_bitrate": "12M",
    }
}

# Default preset
DEFAULT_PRESET = "high"


def get_quality_preset(name=None):
    """Get quality preset by name. Returns 'high' preset by default."""
    if name is None:
        name = DEFAULT_PRESET
    return QUALITY_PRESETS.get(name, QUALITY_PRESETS[DEFAULT_PRESET])


def apply_unsharp_mask(frame, strength=1.0):
    """
    Apply unsharp mask to recover sharpness lost during upscaling.
    
    Args:
        frame: Input BGR frame (numpy array)
        strength: Sharpening strength (0.0-2.0, default 1.0)
                  0.8 = subtle, 1.0 = normal, 1.2 = aggressive
    
    Returns:
        Sharpened frame
    """
    if strength <= 0:
        return frame
    
    # Create Gaussian blur
    gaussian = cv2.GaussianBlur(frame, (0, 0), 3.0)
    
    # Apply unsharp mask: original + strength * (original - blurred)
    # cv2.addWeighted(src1, alpha, src2, beta, gamma)
    # result = src1 * alpha + src2 * beta + gamma
    # For unsharp: result = original * (1 + strength) - blurred * strength
    sharpened = cv2.addWeighted(frame, 1.0 + strength, gaussian, -strength, 0)
    
    return sharpened


def resize_with_quality(frame, target_size, apply_sharpening=True, preset_name=None):
    """
    Resize frame with high quality (Lanczos) and optional sharpening.
    
    Args:
        frame: Input BGR frame
        target_size: Tuple (width, height)
        apply_sharpening: Whether to apply unsharp mask after resize
        preset_name: Quality preset name ('standard', 'high', 'max')
    
    Returns:
        Resized and optionally sharpened frame
    """
    preset = get_quality_preset(preset_name)
    
    # Use Lanczos interpolation for best upscaling quality
    resized = cv2.resize(frame, target_size, interpolation=preset["interpolation"])
    
    # Apply sharpening to recover detail lost in upscaling
    if apply_sharpening:
        resized = apply_unsharp_mask(resized, preset["unsharp_strength"])
    
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
