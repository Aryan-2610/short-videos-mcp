# A small Python image. "slim" = Debian without extras.
FROM python:3.11-slim

# FFmpeg is a SYSTEM program (not a Python package). yt-dlp, Whisper and our
# frame extraction all need it. This is the reason we use Docker.
RUN apt-get update \
    && apt-get install -y ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the CPU-only PyTorch first (about 200 MB instead of 2+ GB for GPU builds).
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install the rest of the Python packages.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the AI models NOW (while building) so the first real request
# does not have to wait for them. If you change WHISPER_MODEL or OCR_LANGS
# later, change the names here too.
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')" \
    && python -c "import easyocr; easyocr.Reader(['en'], gpu=False)"

# Copy our code last, so editing server.py does not redo all the steps above.
COPY server.py .

# Render sets PORT itself; 10000 is just the default for local runs.
ENV PORT=10000
EXPOSE 10000

CMD ["python", "server.py"]
