import glob, os, subprocess, tempfile, asyncio
import easyocr, yt_dlp, uvicorn
from faster_whisper import WhisperModel
from mcp.server.fastmcp import FastMCP
from fastapi import FastAPI
from contextlib import asynccontextmanager
from thefuzz import fuzz

whisper = WhisperModel("base", device="cpu", compute_type="int8")
ocr = easyocr.Reader(["en"], gpu=False)

def run(cmd):
    subprocess.run(cmd, capture_output=True, check=True)

def process(url):
    with tempfile.TemporaryDirectory() as folder:
        vid_path = f"{folder}/vid.mp4"
        yt_dlp.YoutubeDL({"outtmpl": vid_path, "format": "best[height<=720]", "quiet": True}).extract_info(url)

        audio_path = f"{folder}/audio.wav"
        run(["ffmpeg", "-y", "-i", vid_path, "-vn", "-ac", "1", "-ar", "16000", audio_path])
        segments, _ = whisper.transcribe(audio_path, vad_filter=True)
        speech = [f"- [{int(s.start)}s] {s.text.strip()}" for s in segments if s.text.strip()]

        os.makedirs(f"{folder}/frames")
        run(["ffmpeg", "-y", "-i", vid_path, "-vf", "fps=1", f"{folder}/frames/f_%04d.jpg"])

        screen, prev_text = [], ""
        for i, frame in enumerate(sorted(glob.glob(f"{folder}/frames/*.jpg"))):
            text = " ".join(ocr.readtext(frame, detail=0)).strip()
            if text and fuzz.ratio(text.lower(), prev_text.lower()) <= 85:
                screen.append(f"- [{i}s] {text}")
                prev_text = text

        return "# Video Data\n## Audio\n" + "\n".join(speech) + "\n## Screen\n" + "\n".join(screen)

mcp = FastMCP("video-to-markdown", host="0.0.0.0", stateless_http=True, json_response=True)

@mcp.tool()
async def process_video(url: str) -> str:
    return await asyncio.to_thread(process, url)

@asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run(): yield

app = FastAPI(lifespan=lifespan)
app.mount("/", mcp.streamable_http_app())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))