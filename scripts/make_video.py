"""Turn script JSON files into vertical (1080x1920) videos with AI voice + captions.

Usage:
    python src/make_video.py                 # builds every file in scripts/
    python src/make_video.py scripts/video1.json
"""
import asyncio
import json
import sys
import textwrap
from pathlib import Path

import edge_tts
import numpy as np
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BG = (15, 23, 42)
FG = (255, 255, 255)
ACCENT = (250, 204, 21)
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def load_font(size):
    for p in FONT_PATHS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def make_card(text, accent=False):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    size = 84
    font = load_font(size)
    lines = textwrap.wrap(text, width=18)
    line_h = int(size * 1.3)
    y = (H - line_h * len(lines)) / 2
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((W - w) / 2, y), line, font=font, fill=ACCENT if accent else FG)
        y += line_h
    return np.array(img)


async def tts(text, path, voice):
    await edge_tts.Communicate(text, voice).save(str(path))


def build(script_path, out_dir):
    script_path = Path(script_path)
    name = script_path.stem
    data = json.loads(script_path.read_text(encoding="utf-8"))
    scenes = [data["hook"]] + data["lines"] + [data["cta"]]

    audio_path = out_dir / f"{name}.mp3"
    asyncio.run(tts(" ".join(scenes), audio_path, data.get("voice", "en-US-GuyNeural")))
    audio = AudioFileClip(str(audio_path))

    total_words = sum(len(s.split()) for s in scenes)
    clips = []
    for i, text in enumerate(scenes):
        dur = audio.duration * len(text.split()) / total_words
        clips.append(ImageClip(make_card(text, accent=(i == 0))).set_duration(dur))

    video = concatenate_videoclips(clips).set_audio(audio)
    out_path = out_dir / f"{name}.mp4"
    video.write_videofile(str(out_path), fps=24, codec="libx264", audio_codec="aac")
    print(f"Done: {out_path}")


def main():
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)
    files = sys.argv[1:] or sorted(str(p) for p in Path("scripts").glob("*.json"))
    for f in files:
        build(f, out_dir)


if __name__ == "__main__":
    main()
