# ecg/ml.py
import json
import numpy as np
import neurokit2 as nk
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers
from tensorflow.keras.models import load_model
from scipy.signal import butter, filtfilt
from tensorflow.keras.utils import register_keras_serializable
from django.conf import settings
from pathlib import Path

def run_ecg_analysis(file_path, sampling_rate=100):
    """
    Reads an ECG file (CSV/plain-text/JSON), robustly parses it,
    and runs a two-stage cleaning + analysis pipeline:
      • stats (count, min, max, mean)
      • R-peaks + HR series
      • HRV (time, freq, nonlinear)
      • Morphology (PR, QRS, QT intervals)
    Falls back gracefully on short signals or missing deps.
    """
    try:
        # 1) Load data robustly (comma or newline) :contentReference[oaicite:5]{index=5}
        try:
            signal = np.loadtxt(file_path, delimiter=',')
        except Exception:
            try:
                signal = np.loadtxt(file_path)
            except Exception:
                return {'error': 'no data found'}
        signal_1lead = np.asarray(signal[:,1], dtype=float)

        # 2) Basic stats
        stats = {
            'count': len(signal_1lead),
            'min':   float(np.min(signal_1lead)),
            'max':   float(np.max(signal_1lead)),
            'mean':  float(np.mean(signal_1lead)),
        }
        result = {'stats': stats}

        # 3) Clean ECG: try BioSPPy → NeuroKit fallback :contentReference[oaicite:6]{index=6}
        try:
            cleaned = nk.ecg_clean(signal_1lead, sampling_rate=sampling_rate, method='biosppy')
        except Exception:
            cleaned = nk.ecg_clean(signal_1lead, sampling_rate=sampling_rate, method='neurokit')

        # 4) R-peak detection (Pan–Tompkins default) :contentReference[oaicite:7]{index=7}
        peaks_signals, peaks_info = nk.ecg_peaks(cleaned, sampling_rate=sampling_rate)
        rpeaks = peaks_info.get('ECG_R_Peaks', []).tolist()
        result['rpeaks'] = rpeaks

        # 5) Instantaneous heart rate :contentReference[oaicite:8]{index=8}
        hr = nk.ecg_rate(rpeaks, sampling_rate=sampling_rate)
        result['heart_rate'] = hr.tolist() if hr.size else []

        # 6) Guard downstream analytics on too few peaks
        if len(rpeaks) < 2:
            result.update({
                'hrv_time':      {'error': 'too few peaks'},
                'hrv_frequency': {'error': 'too few peaks'},
                'hrv_nonlinear': {'error': 'too few peaks'},
                'morphology':    {'error': 'too few peaks'},
            })
            return result

        # 7) HRV time-domain :contentReference[oaicite:9]{index=9}
        hrv_time_df = nk.hrv_time(rpeaks, sampling_rate=sampling_rate, show=False)
        result['hrv_time'] = hrv_time_df.to_dict(orient='records')[0]

        # 8) HRV frequency-domain :contentReference[oaicite:10]{index=10}
        try:
            hrv_freq_df = nk.hrv_frequency(rpeaks, sampling_rate=sampling_rate, show=False)
            result['hrv_frequency'] = hrv_freq_df.to_dict(orient='records')[0]
        except ModuleNotFoundError:
            result['hrv_frequency'] = {'error': 'PyWavelets not installed'}

        # 9) HRV non-linear :contentReference[oaicite:11]{index=11}
        try:
            hrv_nonlin_df = nk.hrv_nonlinear(rpeaks, sampling_rate=sampling_rate, show=False)
            result['hrv_nonlinear'] = hrv_nonlin_df.to_dict(orient='records')[0]
        except ModuleNotFoundError:
            result['hrv_nonlinear'] = {'error': 'PyWavelets not installed'}

        # 10) Morphological delineation: PR, QRS, QT :contentReference[oaicite:12]{index=12}
        try:
            _, delineate_info = nk.ecg_delineate(cleaned, rpeaks, sampling_rate=sampling_rate)
            P_on  = np.array(delineate_info.get('ECG_P_Onsets', []))
            Q_on  = np.array(delineate_info.get('ECG_Q_Peaks', []))
            S_off = np.array(delineate_info.get('ECG_S_Peaks', []))
            T_off = np.array(delineate_info.get('ECG_T_Offsets', []))
            pr  = (Q_on  - P_on ) / sampling_rate * 1000
            qrs = (S_off - Q_on ) / sampling_rate * 1000
            qt  = (T_off - Q_on ) / sampling_rate * 1000
            result['morphology'] = {
                'pr_mean_ms':  float(np.nanmean(pr)),
                'qrs_mean_ms': float(np.nanmean(qrs)),
                'qt_mean_ms':  float(np.nanmean(qt)),
            }
        except Exception:
            result['morphology'] = {'error': 'delineation failed'}

        return result

    except Exception as e:
        return {'error': f'processing error: {str(e)}'}


# ================================
# === Begin ECG classification code
# ================================

# --- 1. Define the Cast layer so that HDF5 restore can find it ---
@register_keras_serializable()
class Cast(layers.Layer):
    def __init__(self, dtype, **kwargs):
        super().__init__(**kwargs)
        # Store the target dtype as a string (e.g., "float32")
        self._target_dtype = tf.dtypes.as_dtype(dtype).name

    def call(self, inputs):
        # Cast inputs to the stored dtype
        return tf.cast(inputs, self._target_dtype)

    def get_config(self):
        # Include 'dtype' in the layer's config so that loading works
        cfg = super().get_config()
        cfg.update({'dtype': self._target_dtype})
        return cfg


# --- 2. Preprocessing utilities (bandpass + normalization) ---
def bandpass_filter(sig, lowcut=0.5, highcut=40.0, fs=100.0, order=4):
    """
    Apply a Butterworth bandpass filter to a 12-lead ECG (sig).
    Assumes `sig` is a NumPy array of shape (n_samples, 12).
    """
    nyq = 0.5 * fs
    b, a = butter(order, [lowcut / nyq, highcut / nyq], btype='band')
    return filtfilt(b, a, sig, axis=0)

def normalize_signal(sig):
    """
    Normalize each column (lead) to zero mean, unit variance.
    """
    mean = np.mean(sig, axis=0)
    std  = np.std(sig, axis=0) + 1e-6
    return (sig - mean) / std


# --- 3. Load the model once, with custom_objects for Cast ---
#    Place your HDF5 (best_ecg_resnet.h5) in the same folder as this file,
#    or update the path below if you store it elsewhere.
BASE_DIR = Path(__file__).resolve().parent.parent
_MODEL_PATH = settings.BASE_DIR / 'ecg' / 'analysis_helper_files' / 'best_ecg_resnet.h5'
_model = load_model(
    _MODEL_PATH,
    custom_objects={'Cast': Cast},
    compile=False
)


# --- 4. Single-sample prediction from CSV ---
def predict_from_csv(csv_path, threshold=0.5):
    """
    Reads a 12-lead ECG from a CSV file (expected shape: 1000×12),
    applies bandpass + normalization, and returns:
      • probabilities: dict mapping class → prob
      • predictions:   list of class names whose prob ≥ threshold
      • raw_binary:    list of 0/1 flags in the same order as classes
    """
    # (a) Load CSV (no header)
    df = pd.read_csv(csv_path, header=None)
    ecg = df.values
    # Validate shape
    if ecg.shape != (1000, 12):
        raise ValueError(f"Expected CSV of shape (1000,12), got {ecg.shape}")

    # (b) Preprocess: bandpass → normalize → float32
    filtered = bandpass_filter(ecg)
    normed   = normalize_signal(filtered).astype(np.float32)

    # (c) Add batch dimension: (1, 1000, 12)
    batch = np.expand_dims(normed, axis=0)

    # (d) Predict: model returns a 5-element vector of probabilities
    probs = _model.predict(batch)[0]           # shape: (5,)
    preds = (probs >= threshold).astype(int)   # length 5 binary mask

    # (e) Map indices → class names
    classes = ['NORM', 'MI', 'STTC', 'CD', 'HYP']
    predicted = [cls for cls, p in zip(classes, preds) if p]

    return {
        'probabilities': dict(zip(classes, probs.tolist())),
        'predictions':    predicted,
        'raw_binary':     preds.tolist()
    }

# ================================
# === End ECG classification code
# ================================
