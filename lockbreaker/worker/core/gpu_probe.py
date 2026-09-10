from __future__ import annotations
import subprocess
from typing import Dict, Any


def probe_gpu() -> Dict[str, Any]:
    """
    Detects available GPU hardware at worker startup.
    Results are logged into the job manifest for reproducibility.
    """
    result: Dict[str, Any] = {"available": False, "devices": [], "backend_hint": "cpu"}

    # NVIDIA
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and r.stdout.strip():
            devices = [ln.strip() for ln in r.stdout.strip().splitlines() if ln.strip()]
            result["available"] = True
            result["devices"] = [{"type": "nvidia", "info": d} for d in devices]
            result["backend_hint"] = "hashcat_cuda"
            return result
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # AMD ROCm
    try:
        r = subprocess.run(
            ["rocm-smi", "--showproductname"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and r.stdout.strip():
            result["available"] = True
            result["devices"] = [{"type": "amd_rocm", "info": r.stdout.strip()}]
            result["backend_hint"] = "hashcat_opencl"
            return result
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # OpenCL fallback check
    try:
        r = subprocess.run(
            ["clinfo", "--list"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and r.stdout.strip():
            result["available"] = True
            result["devices"] = [{"type": "opencl", "info": r.stdout.strip()[:200]}]
            result["backend_hint"] = "hashcat_opencl"
            return result
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return result
