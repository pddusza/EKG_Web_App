# ecg/ml.py
import json
import numpy as np
import neurokit2 as nk

def run_ecg_analysis(file_path, sampling_rate=500):
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
        signal = np.asarray(signal, dtype=float)

        # 2) Basic stats
        stats = {
            'count': len(signal),
            'min':   float(np.min(signal)),
            'max':   float(np.max(signal)),
            'mean':  float(np.mean(signal)),
        }
        result = {'stats': stats}

        # 3) Clean ECG: try BioSPPy → NeuroKit fallback :contentReference[oaicite:6]{index=6}
        try:
            cleaned = nk.ecg_clean(signal, sampling_rate=sampling_rate, method='biosppy')
        except Exception:
            cleaned = nk.ecg_clean(signal, sampling_rate=sampling_rate, method='neurokit')

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
