from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import subprocess, os, re, sys, librosa, numpy as np, soundfile as sf
from scipy.signal import butter, lfilter

app = FastAPI(title="Olympo Vocal Remover", version="1.0")

# ============================================================
# 🟡 CORS (permite conexión desde tu frontend)
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # puedes limitarlo luego a tu dominio en producción (ej: https://olympo.app)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 🎚️ Utilidades de mastering
# ============================================================
def butter_filter(x, sr, kind="highpass", fc=60, order=2):
    nyq = 0.5 * sr
    Wn = fc / nyq
    b, a = butter(order, Wn, btype="high" if kind == "highpass" else "low")
    return lfilter(b, a, x, axis=0)

def simple_compressor(x, thresh_db=-18, ratio=3.0, makeup_db=3.0):
    eps = 1e-9
    rms = np.sqrt(np.mean(x**2, axis=0) + eps)
    level_db = 20 * np.log10(rms + eps)
    over = np.maximum(level_db - thresh_db, 0.0)
    gain_db = -(1.0 - 1.0 / ratio) * over
    linear = 10 ** ((gain_db + makeup_db) / 20.0)
    return x * linear

def normalize_to_rms(x, target_dbfs=-14.0):
    eps = 1e-9
    cur = 20 * np.log10(np.sqrt(np.mean(x**2)) + eps)
    gain = 10 ** ((target_dbfs - cur) / 20.0)
    y = x * gain
    peak = np.max(np.abs(y)) + eps
    if peak > 0.999:
        y = y / peak * 0.999
    return y.astype(np.float32)

# ============================================================
# 🔊 Endpoint principal /separate
# ============================================================
@app.post("/separate")
async def separate(file: UploadFile = File(...)):
    """
    Separa voces e instrumental + aplica mastering automático
    """
    try:
        # --- Limpieza del nombre ---
        base_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', file.filename.split('.')[0])
        input_dir = "input"
        output_dir = "output"
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        input_path = os.path.join(input_dir, f"{base_name}.mp3")
        with open(input_path, "wb") as f:
            f.write(await file.read())

        # --- Ejecutar Demucs ---
        print(f"🎧 Ejecutando Demucs para {input_path}...")
        subprocess.run(
            [sys.executable, "-m", "demucs", "--two-stems", "vocals", "--device", "cpu", input_path, "-o", output_dir],
            check=True
        )

        # --- Buscar carpeta de salida ---
        demucs_subdirs = [d for d in os.listdir(output_dir) if d.startswith("htdemucs")]
        if not demucs_subdirs:
            raise RuntimeError("❌ No se encontró la carpeta de salida generada por Demucs.")
        model_root = os.path.join(output_dir, demucs_subdirs[0])

        vocals, instrumental = None, None
        for root, _, files in os.walk(model_root):
            for name in files:
                if name.endswith("vocals.wav"):
                    vocals = os.path.join(root, name)
                elif name.endswith("no_vocals.wav"):
                    instrumental = os.path.join(root, name)

        if not vocals or not instrumental:
            raise RuntimeError("❌ No se encontraron los archivos separados por Demucs.")

        # --- Mastering automático ---
        def master_track(path_in, tag):
            y, sr = librosa.load(path_in, sr=None, mono=False)
            if y.ndim == 1:
                y = np.stack([y, y], axis=1)
            y = butter_filter(y, sr, "highpass", 40)
            y = butter_filter(y, sr, "lowpass", 18000)
            y = simple_compressor(y)
            y = normalize_to_rms(y, -14.0)
            master_path = path_in.replace(".wav", f"_{tag}_master.wav")
            sf.write(master_path, y, sr, format="WAV", subtype="PCM_16")
            return master_path

        vocals_master = master_track(vocals, "vocals")
        instrumental_master = master_track(instrumental, "instrumental")

        print("✅ Separación y mastering completados con éxito.")
        return {
            "message": "✅ Separación y mastering completados con éxito",
            "vocals_master": vocals_master,
            "instrumental_master": instrumental_master
        }

    except subprocess.CalledProcessError as e:
        return {"error": f"❌ Error ejecutando Demucs: {e}"}
    except Exception as e:
        return {"error": f"⚠️ Error: {str(e)}"}

# ============================================================
# 🧠 Endpoint de prueba (Render health check)
# ============================================================
@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "🏆 Olympo Vocal Remover API funcionando correctamente"}

# ============================================================
# 🚀 Servidor local
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)