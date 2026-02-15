# ViralCutter
[![Discord](https://dcbadge.limes.pink/api/server/tAdPHFAbud)](https://discord.gg/tAdPHFAbud)<br>

**100% Free, Local, and Unlimited Open-Source Alternative to Opus Clip**  
Turn long YouTube videos into viral shorts optimized for TikTok, Instagram Reels, and YouTube Shorts – with state-of-the-art AI, dynamic captions, precise *face tracking*, and automatic translation. All running on your machine.

[![Stars](https://img.shields.io/github/stars/RafaelGodoyEbert/ViralCutter?style=social)](https://github.com/RafaelGodoyEbert/ViralCutter/stargazers)
[![Forks](https://img.shields.io/github/forks/RafaelGodoyEbert/ViralCutter?style=social)](https://github.com/RafaelGodoyEbert/ViralCutter/network/members)
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1UZKzeqjIeEyvq9nPx7s_4mU6xlkZQn_R?usp=sharing)

[English](README_en.md) • [Português](README.md)

## Why is ViralCutter a "Game Changer"?

Forget expensive subscriptions and minute limits. ViralCutter offers unlimited power on your own hardware.

| Feature | ViralCutter (Open-Source) | Opus Clip / Klap / Munch (SaaS) |
| :--- | :--- | :--- |
| **Price** | **Free & Unlimited** | $20–$100/mo + minute limits |
| **Privacy** | **100% Local** (Your data never leaves your PC) | Upload to third-party cloud |
| **AI & LLM** | **Flexible**: Gemini (Free), GPT-4, **Local GGUF (Offline)** | Only what they offer |
| **Face Tracking** | **Split Screen (2 faces)**, Active Speaker (Exp.), Auto | Basic or extra cost |
| **Translation** | **Yes** (Translate captions to 10+ languages) | Limited features |
| **Editing** | **Export XML to Premiere Pro** (Beta) | Limited web editor |
| **Watermark** | **ZERO** | Yes (on free plans) |

**Professional results, total privacy, and zero cost.**

## Key Features 🚀

-   🤖 **AI Viral Cut**: Automatically identifies hooks and engaging moments using **Gemini**, **GPT-4**, or **Local LLMs (Llama 3, DeepSeek, etc)**.
-   🗣️ **Ultra-Precise Transcription**: Powered by **WhisperX** with GPU acceleration for perfect subtitles.
-   🎨 **Dynamic Captions**: "Hormozi" style with word-by-word highlights, vibrant colors, emojis, and full customization.
-   🎥 **Auto Camera Direction**:
    -   **Auto-Crop 9:16**: Transforms horizontal to vertical while keeping the focus.
    -   **Smart Split Screen**: Detects 2 people talking and automatically splits the screen.
    -   **Active Speaker (Experimental)**: The camera cuts to whoever is speaking.
-   🌍 **Video Translation**: Automatically generate translated subtitles (e.g., English Video -> Portuguese Subtitles).
-   💾 **Quality & Control**: Choose resolution (up to 4K/Best), format output, and save processing configurations.
-   ⚡ **Performance**: Transcription with "slicing" (process 1x, cut N times) and ultra-fast installation via `uv`.
-   🖥️ **Modern Interface**: Gradio WebUI, Dark Mode, Project Gallery, and integrated Subtitle Editor.

## Web Interface (Inspired by Opus Clip)
![WebUI Home](https://github.com/user-attachments/assets/ba147149-fc5f-48fc-a03c-fc86b5dc0568)
*Intuitive control panel with fine-tuning for AI and rendering.*

![WebUi Library](https://github.com/user-attachments/assets/b0204e4b-0e5d-4ee4-b7b4-cac044b76c24)
*Library: OpusClip-style gallery and intuitive controls*

## Local Installation (Super Fast ⚡)

### Prerequisites
- Python 3.10+
- FFmpeg installed on the system
- **NVIDIA GPU** (Highly recommended for speed and local AI features)

### Step-by-Step

1.  **Install Dependencies**
    Run the `install_dependencies.bat` script. It uses `uv` manager to set everything up in seconds.

2.  **Configure AI (Optional)**
    -   **Gemini (Recommended/Free)**: Add your key in `api_config.json`.
    -   **Local (GGUF)**: Download your favorite `.gguf` models and place them in the `models/` folder. ViralCutter will detect them automatically.

3.  **Run**
    -   Double-click `run_webui.bat` to open the interface in your browser.
    -   Or use `python main_improved.py` for the CLI version.

## Output Examples

**Viral Clip with Highlight Captions**  
<video src="https://github.com/user-attachments/assets/7a32edce-fa29-4693-985f-2b12313362f3" controls></video>

**Direct Comparison: Opus Clip vs ViralCutter** (same input video)  
<video src="https://github.com/user-attachments/assets/12916792-dc0e-4f63-a76b-5698946f50f4" controls></video>

**2-Face Split Screen Mode**  
<video src="https://github.com/user-attachments/assets/f5ce5168-04a2-4c9b-9408-949a5400d020" controls></video>

## Roadmap (TODO)

- [x] Release code
- [ ] Permanent Demo on Hugging Face Spaces
- [x] Two face in the cut (Split Screen)
- [x] Custom caption and burn
- [x] Make the code faster
- [x] 100% Local AI Models (Ollama/Llama/GGUF)
- [x] Automatic caption translation
- [x] The cut follows the face as it moves
- [x] XML Export to Premiere Pro (Beta)
- [ ] Automatic background music (Auto-Duck)
- [ ] Direct upload to TikTok/YouTube/Instagram
- [ ] More framing formats (beyond 9:16)
- [ ] Optional Watermark

---

## Contribute!

ViralCutter is community-maintained. Join us to democratize AI content creation!
-   **Discord**: [AI Hub Brasil](https://discord.gg/aihubbrasil)
-   **Github**: Give us a ⭐ star if this project helped you!

## 📄 License

This project is licensed under the **GNU General Public License v3**. [Read the full license here](LICENSE).

**Current Version**: 0.8v Alpha
*ViralCutter: Because viral clips shouldn't cost a fortune.* 🚀
