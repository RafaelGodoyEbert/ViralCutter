# ViralCutter: Viral Video Generator
[ ![](https://dcbadge.vercel.app/api/server/aihubbrasil) ](https://discord.gg/aihubbrasil) <br>
[English](https://github.com/RafaelGodoyEbert/ViralCutter/blob/main/README_en.md) | [Português](https://github.com/RafaelGodoyEbert/ViralCutter/blob/main/README.md)

## **Description**
ViralCutter is an innovative tool designed to generate viral videos from existing content. With advanced video and audio processing techniques, ViralCutter cuts and edits video segments that are perfect for sharing on social media. Using the WhisperX model for transcription and automatic caption generation, it adapts videos to the 9:16 (vertical) format, ideal for platforms like TikTok, Instagram Reels, and YouTube Shorts.

## **What's New & Updates (Changelog)**

Check out the latest improvements:

-   **Performance Optimization**: Transcription "slicing" implemented. The video is transcribed only once, and cuts reuse the data, eliminating reprocessing.
-   **Flexible AI Support**: Native integration with **Gemini API** and experimental support for **G4F** (GPT-4 Free), plus a Manual mode.
-   **External Configuration**: `api_config.json` and `prompt.txt` files for easy customization without touching the code.
-   **Face Fix**: MediaPipe fix for precise face tracking without relying on "Center Crop".
-   **Subtitle Improvements**: Smart positioning for 2-face videos (split screen) and style corrections.

*(See [changelog.md](changelog.md) for full details)*

## **Features**

- **Video Download**: Downloads YouTube videos via a provided URL.
- **Audio Transcription**: Converts audio to text using the WhisperX model.
- **Viral Segment Identification**: Uses AI to detect parts of the video with high viral potential.
- **Cutting & Formatting**: Cuts selected segments and adjusts the aspect ratio to 9:16.
- **Smart Cropping**: Keeps the speaker in focus (Face Tracking) or uses automatic Split Screen (2-Faces) mode.
- **Audio/Video Merging**: Combines transcribed audio with processed video clips.
- **Batch Export**: Generates a ZIP file with all created viral videos, facilitating download and sharing.
- **Custom Captions**: Create custom captions with colors, highlights, no highlights, or word-by-word styles, offering extensive editing possibilities.


## **How to Use**
<!--
Open the link and follow the steps in order:<br> [![Open In Colab](https://img.shields.io/badge/Colab-F9AB00?style=for-the-badge&logo=googlecolab&color=525252)](https://colab.research.google.com/drive/1gcxImzBt0ObWLfW3ThEcwqKhasB4WpgX?usp=sharing)
HF [![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)]()
-->

- Open the link and follow the steps in order(Only Portuguese, sorry): [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1UZKzeqjIeEyvq9nPx7s_4mU6xlkZQn_R?usp=sharing#scrollTo=pa36OeArowme) <br>


## **Limitations**

- The quality of generated videos may vary based on the quality of the original video.
- Processing time depends heavily on your GPU.
- The **G4F** model may be unstable or have request limits. Use **Gemini** for greater stability (requires an api_key).

## Inspiration
This project was inspired by the following repositories:

*   [Reels Clips Automator](https://github.com/eddieoz/reels-clips-automator)
*   [YoutubeVideoToAIPoweredShorts](https://github.com/Fitsbit/YoutubeVideoToAIPoweredShorts)

## TODO📝
- [x] Release code
- [ ] Huggingface SpaceDemo
- [x] Two face in the cut
- [x] Custom caption and burn
- [x] Make the code faster
- [ ] More types of framing beyond 9:16
- [x] The cut follows the face as it moves
- [ ] Automatic translation
- [ ] Satisfying video on the side
- [ ] Background music
- [ ] Watermark at user's choice
- [ ] Upload directly to YouTube channel

## Examples
### Viral video example `with active highlight` [compressed to fit GitHub]
https://github.com/user-attachments/assets/dd9a7039-e0f3-427a-a6e1-f50ab5029082

### Opus Clip vs ViralCutter example [compressed to fit GitHub]
https://github.com/user-attachments/assets/12916792-dc0e-4f63-a76b-5698946f50f4

### 2-Face example [compressed to fit GitHub]
https://github.com/user-attachments/assets/ca7ebb9c-52ba-4171-a513-625bef690a2b

## **Installation and Local Usage**

### Prerequisites
-   Python 3.10+
-   FFmpeg installed and in the system PATH.
-   NVIDIA GPU recommended (with CUDA installed) for WhisperX.

### Configuration
1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: WhisperX and Torch may require specific installation instructions for your CUDA version)*.

2.  **Configure API (Optional but Recommended)**:
    Edit the `api_config.json` file in the root folder:
    ```json
    {
        "selected_api": "gemini",
        "gemini": {
            "api_key": "YOUR_KEY_HERE"
        }
    }
    ```

### Running

#### Interactive Mode (Simple)
Just run the script and follow the on-screen instructions:
```bash
python main_improved.py
```

#### CLI Mode (Advanced)
You can pass all arguments via command line for automation:

```bash
python main_improved.py --url "https://youtu.be/EXAMPLE" --segments 3 --ai-backend gemini --model large-v3-turbo
```

**Main Arguments:**
-   `--url`: YouTube video URL.
-   `--segments`: Number of cuts to generate.
-   `--ai-backend`: `gemini` (Recommended), `g4f`, or `manual`.
-   `--viral`: Activates automatic viral search mode.
-   `--face-mode`: `auto`, `1` (one face), or `2` (two faces/split).
-   `--workflow`: `1` (Full) or `2` (Cut Only, no captions/crop).

---

## **Contributions**
Want to help make ViralCutter even better? If you have suggestions or want to contribute to the code, feel free to open an issue or submit a pull request on our GitHub repository.

## **Version**
`0.7v Alpha`  
A free alternative to `opus.pro` and `vidyo.ai`.

---