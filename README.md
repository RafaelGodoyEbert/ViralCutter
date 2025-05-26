# ViralCutter: Viral Video Generator
[ ![](https://dcbadge.vercel.app/api/server/aihubbrasil) ](https://discord.gg/aihubbrasil) <br>
[English](https://github.com/RafaelGodoyEbert/ViralCutter/blob/main/README.md) | [Português](https://github.com/RafaelGodoyEbert/ViralCutter/blob/main/README_pt_BR.md)

## **Description**
ViralCutter is an innovative tool for generating viral videos from existing content. Using advanced video and audio processing techniques, ViralCutter cuts and edits video segments that are perfect for sharing on social media. Utilizing the WhisperX model for transcription and automatic subtitle generation, it adapts videos to the 9:16 (vertical) format, ideal for platforms like TikTok, Instagram Reels, and YouTube Shorts.

## **Features**

- **Video Download**: Downloads YouTube videos via a provided URL.
- **Audio Transcription**: Converts audio to text using the WhisperX model.
- **Viral Segment Identification**: Uses AI to detect video parts with high viral potential, with automatic recommendations for maximum segments based on video duration.
- **Cutting and Format Adjustment**: Cuts selected segments and adjusts aspect ratio to 9:16.
- **Audio and Video Merging**: Combines transcribed audio with processed video clips.
- **Batch Export**: Generates a ZIP file with all created viral videos, facilitating download and sharing.
- **Custom Subtitles**: Create custom subtitles with colors, highlights, non-highlights, or word-by-word, offering extensive editing possibilities.

## **How to Use**
<!-- 
Enter the link and follow the steps in order:<br> [![Open In Colab](https://img.shields.io/badge/Colab-F9AB00?style=for-the-badge&logo=googlecolab&color=525252)](https://colab.research.google.com/drive/1gcxImzBt0ObWLfW3ThEcwqKhasB4WpgX?usp=sharing)
HF [![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)]()
-->
- Enter the link and follow the steps in order: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1UZKzeqjIeEyvq9nPx7s_4mU6xlkZQn_R?usp=sharing#scrollTo=pa36OeArowme) <br>
- Simplified version without text editing options [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1aDNLtoJZa9Z0lKcYTR6CGNMgZ_iTpwJD?usp=sharing) <br>
- I created this website to help split transcriptions, as ChatGPT has limits: [Split text for ChatGPT](https://rafaelgodoyebert.github.io/ViralCutter/)

## **Limitations**

- Processing time can be high for long videos.
- The quality of generated videos may vary based on the original video quality.

## Inspiration:
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
- [ ] Satisfactory video on the side
- [ ] Background music
- [ ] watermark at user's choice
- [ ] Upload directly to YouTube channel

## Examples
### Viral video example ``with active highlight`` [compressed to fit GitHub]
https://github.com/user-attachments/assets/dd9a7039-e0f3-427a-a6e1-f50ab5029082

### Opus Clip vs ViralCutter Example [compressed to fit GitHub]
https://github.com/user-attachments/assets/12916792-dc0e-4f63-a76b-5698946f50f4

### Two faces example [compressed to fit GitHub]
https://github.com/user-attachments/assets/ca7ebb9c-52ba-4171-a513-625bef690a2b

## **Contributions**
Want to help make ViralCutter even better? If you have suggestions or want to contribute to the code, feel free to open an issue or submit a pull request on our GitHub repository.

## **Version**
`0.6v Alpha`  
A free alternative to `opus.pro` and `vidyo.ai`.

---