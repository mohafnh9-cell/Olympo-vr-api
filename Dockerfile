FROM python:3.10-slim

# ffmpeg es necesario para demucs / audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# código
COPY app ./app

# evita buffering en logs
ENV PYTHONUNBUFFERED=1

# Puerto dinámico (Railway define $PORT)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]