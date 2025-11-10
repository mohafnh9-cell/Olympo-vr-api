import os, subprocess, time, librosa, soundfile as sf
import numpy as np
from scipy.signal import butter, lfilter
from app.store import update_job
from app.models import JobStatus

# --- FILTROS Y EFECTOS ---
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

# --- PROCESO PRINCIPAL ---
def process_job(job_id: str, file_path: str):
    try:
        update_job(job_id, status=JobStatus.running, progress=10)
        print(f"🚀 Procesando job {job_id} → {file_path}")

        # Salida
        out_root = f"outputs/{os.path.basename(file_path).split('.')[0]}"
        os.makedirs(out_root, exist_ok=True)

        # 1️⃣ Separación con Demucs (2 stems: vocal + instrumental)
        subprocess.run(["demucs", "--two-stems", "vocals", file_path, "-o", out_root], check=True)
        update_job(job_id, progress=60)

        # 2️⃣ Localizar los WAV resultantes
        model_dir = os.path.join(out_root, "htdemucs")
        subfolders = [f.path for f in os.scandir(model_dir) if f.is_dir()]
        if not subfolders:
            raise RuntimeError("❌ No se encontraron salidas de Demucs.")
        song_dir = subfolders[-1]

        vocals_path = os.path.join(song_dir, "vocals.wav")
        instrumental_path = os.path.join(song_dir, "no_vocals.wav")

        # 3️⃣ Masterización simple
        for src_path, tag in [(vocals_path, "vocals_master"), (instrumental_path, "instrumental_master")]:
            y, sr = librosa.load(src_path, sr=None, mono=False)
            if y.ndim == 1:
                y = np.stack([y, y], axis=1)
            y = butter_filter(y, sr, "highpass", 40)
            y = butter_filter(y, sr, "lowpass", 18000)
            y = simple_compressor(y)
            y = normalize_to_rms(y, -14.0)
            sf.write(os.path.join(song_dir, f"{tag}.wav"), y, sr)
            print(f"✅ {tag}.wav generado")

        # 4️⃣ Actualización final del job
        update_job(
            job_id,
            status=JobStatus.done,
            progress=100,
            vocals_master_url=f"/{song_dir}/vocals_master.wav",
            instrumental_master_url=f"/{song_dir}/instrumental_master.wav",
        )
        print(f"🎯 Job {job_id} completado correctamente.")

    except Exception as e:
        update_job(job_id, status=JobStatus.failed, error=str(e))
        print(f"❌ Error en job {job_id}: {e}")