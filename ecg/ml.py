# ecg/ml.py
import json
import numpy as np
import neurokit2 as nk
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers
from tensorflow.keras.models import load_model
from scipy.signal import butter, filtfilt, resample
from tensorflow.keras.utils import register_keras_serializable
from django.conf import settings
from pathlib import Path

def run_ecg_analysis(file_path: str, sampling_rate: int = 100):
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
        # 1) Load data robustly (comma or newline)
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

        # 3) Clean ECG: try BioSPPy → NeuroKit fallback
        try:
            cleaned = nk.ecg_clean(signal_1lead, sampling_rate=sampling_rate, method='biosppy')
        except Exception:
            cleaned = nk.ecg_clean(signal_1lead, sampling_rate=sampling_rate, method='neurokit')

        # 4) R-peak detection (Pan–Tompkins default)
        peaks_signals, peaks_info = nk.ecg_peaks(cleaned, sampling_rate=sampling_rate)
        rpeaks = peaks_info.get('ECG_R_Peaks', []).tolist()
        result['rpeaks'] = rpeaks

        # 5) Instantaneous heart rate
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

        # 7) HRV time-domain
        hrv_time_df = nk.hrv_time(rpeaks, sampling_rate=sampling_rate, show=False)
        result['hrv_time'] = hrv_time_df.to_dict(orient='records')[0]

        # 8) HRV frequency-domain
        try:
            hrv_freq_df = nk.hrv_frequency(rpeaks, sampling_rate=sampling_rate, show=False)
            result['hrv_frequency'] = hrv_freq_df.to_dict(orient='records')[0]
        except ModuleNotFoundError:
            result['hrv_frequency'] = {'error': 'PyWavelets not installed'}

        # 9) HRV non-linear
        try:
            hrv_nonlin_df = nk.hrv_nonlinear(rpeaks, sampling_rate=sampling_rate, show=False)
            result['hrv_nonlinear'] = hrv_nonlin_df.to_dict(orient='records')[0]
        except ModuleNotFoundError:
            result['hrv_nonlinear'] = {'error': 'PyWavelets not installed'}

        # 10) Morphological delineation: PR, QRS, QT
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

# map sampling rates to model files
MODEL_MAP = {
    # if sr ≥ 500 Hz, use the high-res model
    'high': 'best_ecg_resnet_500_weights.h5',
    # otherwise fallback to default 100 Hz model
    'default': 'best_ecg_resnet.h5',
}

# --- 1. Define the Cast layer so that HDF5 restore can find it ---
@register_keras_serializable()
class Cast(layers.Layer):
    def __init__(self, dtype, **kwargs):
        super().__init__(**kwargs)
        self._target_dtype = tf.dtypes.as_dtype(dtype).name

    def call(self, inputs):
        return tf.cast(inputs, self._target_dtype)

    def get_config(self):
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


# --- 3. Single-sample prediction from CSV, dynamic model loading ---
def predict_from_csv(csv_path, sampling_rate=100.0, threshold=0.5):
    """
    Reads a 12-lead ECG from a CSV file,
    applies bandpass + normalization (using sampling_rate), then:
      • loads the appropriate model weights based on sampling_rate
      • returns probabilities, predictions, and raw binary mask
    """
    # (a) Load CSV (no header)
    df = pd.read_csv(csv_path, header=None)
    ecg = df.values
    n_samples, n_leads = ecg.shape

    # (b) Validate leads and resample length
    if n_leads != 12:
        raise ValueError(f"Expected 12 leads (columns), got {n_leads}")
    expected_len = int(sampling_rate * 10)  # e.g. 100 Hz→1000 samples; 500 Hz→5000 samples
    if n_samples != expected_len:
        ecg = resample(ecg, expected_len, axis=0)

    # (c) Preprocess: bandpass → normalize → float32
    filtered = bandpass_filter(ecg, fs=sampling_rate)
    normed   = normalize_signal(filtered).astype(np.float32)

    # (d) Choose model file by sampling_rate
    if sampling_rate >= 500:
        weights_file = MODEL_MAP['high']
    else:
        weights_file = MODEL_MAP['default']

    # (e) Load model with custom Cast layer
    model_path = settings.BASE_DIR / 'ecg' / 'analysis_helper_files' / weights_file
    model = load_model(
        model_path,
        custom_objects={'Cast': Cast},
        compile=False
    )

    # (f) Prepare batch and predict
    batch = np.expand_dims(normed, axis=0)    # shape: (1, expected_len, 12)
    probs = model.predict(batch)[0]           # shape: (5,)
    preds = (probs >= threshold).astype(int)  # binary mask

    # (g) Map indices → class names
    classes = ['NORM', 'MI', 'STTC', 'CD', 'HYP']
    predicted = [cls for cls, p in zip(classes, preds) if p]

    return {
        'model_used':     weights_file,
        'sampling_rate':  sampling_rate,
        'probabilities': dict(zip(classes, probs.tolist())),
        'predictions':    predicted,
        'raw_binary':     preds.tolist()
    }

# ================================
# === End ECG classification code
# ================================