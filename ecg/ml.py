import os
import json

def run_ecg_analysis(file_path):
    """
    Reads an ECG file (CSV or JSON lines) at file_path,
    computes basic stats, and returns a JSON-serializable dict.
    """
    # Example: if it’s a plain text of numbers, one per line:
    try:
        with open(file_path, 'r') as f:
            # parse floats from each line
            data = [float(line.strip()) for line in f if line.strip()]
    except ValueError:
        # fallback: if it’s JSON containing a list under “signal”
        obj = json.load(open(file_path))
        data = obj.get('signal', [])
    # compute simple stats
    if not data:
        return {'error': 'no data'}
    stats = {
        'count':    len(data),
        'min':      min(data),
        'max':      max(data),
        'mean':     sum(data) / len(data),
    }
    return stats
