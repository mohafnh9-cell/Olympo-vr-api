# ===============================
# 🧠 DOCKERFILE - OLYMPO VOCAL REMOVER (PRODUCTION)
# ===============================

# 1️⃣ Imagen base ligera con Python 3.10
FROM python:3.10-slim

# 2️⃣ Instalar dependencias del sistema (ffmpeg es vital para Demucs)
RUN apt-get update && \
    apt-get install -y ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

# 3️⃣ Definir directorio de trabajo
WORKDIR /app

# 4️⃣ Copiar dependencias
COPY requirements.txt .

# 5️⃣ Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# 6️⃣ Copiar el resto del proyecto
COPY . .

# 7️⃣ Exponer el puerto 7860 (requerido por Hugging Face Spaces)
EXPOSE 7860

# 8️⃣ Comando para iniciar el servidor FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]