# ViralCutter: Viral Video Generator
[ ![](https://dcbadge.vercel.app/api/server/aihubbrasil) ](https://discord.gg/aihubbrasil) <br>
[English](https://github.com/RafaelGodoyEbert/ViralCutter/blob/main/README_en.md) | [Português](https://github.com/RafaelGodoyEbert/ViralCutter/blob/main/README.md)

## **Description**
ViralCutter is an innovative tool for generating viral videos from existing content. With advanced video and audio processing techniques, ViralCutter cuts and edits video segments that are perfect for sharing on social media. Using the WhisperX model for transcription and automatic subtitle generation, it adapts videos to a 9:16 (vertical) format, ideal for platforms like TikTok and Instagram Reels, as well as YouTube Shorts.

## **Features**

- **Video Download**: Downloads videos from YouTube using a provided URL.
- **Audio Transcription**: Converts audio to text using the WhisperX model.
- **Viral Segment Identification**: Uses AI to detect parts of the video with high viral potential.
- **Cutting and Format Adjustment**: Cuts selected segments and adjusts the aspect ratio to 9:16.
- **Audio and Video Merging**: Combines transcribed audio with processed video clips.
- **Batch Export**: Generates a ZIP file with all created viral videos, making it easy to download and share.
- **Custom Subtitles**: Create personalized subtitles with options for color, highlighting, or word-by-word display, allowing for extensive editing possibilities.

## **How to Use**
- Go to the link and follow the steps in order: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1UZKzeqjIeEyvq9nPx7s_4mU6xlkZQn_R?usp=sharing#scrollTo=pa36OeArowme) (only Portuguese) <br>
- Simplified version without text change options [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1aDNLtoJZa9Z0lKcYTR6CGNMgZ_iTpwJD?usp=sharing) (only Portuguese) <br>
- I created this site to help split the transcription, since ChatGPT has limits: [Split text for ChatGPT](https://rafaelgodoyebert.github.io/ViralCutter/)

## **Limitations**

- Processing time may be high for long videos.
- The quality of generated videos may vary based on the quality of the original video.

## Inspiration:
This project was inspired by the following repositories:

*   [Reels Clips Automator](https://github.com/eddieoz/reels-clips-automator)
*   [YoutubeVideoToAIPoweredShorts](https://github.com/Fitsbit/YoutubeVideoToAIPoweredShorts)

## TODO📝
- [x] Release code
- [ ] Hugging Face Space Demo
- [x] Two faces in the cut
- [x] Custom caption and burn
- [x] Make the code faster
- [ ] More types of framing beyond 9:16
- [x] The cut follows the face as it moves
- [ ] Automatic translation
- [ ] Satisfactory video on the side
- [ ] Background music
- [ ] Watermark at user's choice
- [ ] Upload directly to YouTube channel

## Example of viral video ``with highlight active``
https://github.com/user-attachments/assets/dd9a7039-e0f3-427a-a6e1-f50ab5029082

## **Contributions**
Want to help make ViralCutter even better? If you have suggestions or want to contribute code, feel free to open an issue or send a pull request in our GitHub repository.

## **Version**
`0.6v Alpha`  
A free alternative to `opus.pro` and `vidyo.ai`.

---