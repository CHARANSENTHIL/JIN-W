"""
JARVIS System Monitor — CPU, RAM, GPU, disk, and process monitoring.
"""
import os
import subprocess
import psutil
from dotenv import load_dotenv

load_dotenv()

GPU_BACKEND = os.getenv("GPU_BACKEND", "nvidia").lower()


class SystemMonitor:
    def cpu_usage(self) -> dict:
        """Return CPU usage percentage and per-core breakdown."""
        overall = psutil.cpu_percent(interval=1)
        per_core = psutil.cpu_percent(interval=0, percpu=True)
        freq = psutil.cpu_freq()
        return {
            "overall_percent": overall,
            "per_core": per_core,
            "frequency_mhz": round(freq.current, 1) if freq else None,
            "core_count": psutil.cpu_count(logical=True),
            "formatted": f"CPU Usage: {overall}% ({psutil.cpu_count(logical=True)} cores @ {round(freq.current)}MHz)"
        }

    def ram_usage(self) -> dict:
        """Return RAM usage details."""
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / 1e9, 2),
            "used_gb": round(mem.used / 1e9, 2),
            "available_gb": round(mem.available / 1e9, 2),
            "percent": mem.percent,
            "formatted": f"RAM: {round(mem.used/1e9,1)}GB used / {round(mem.total/1e9,1)}GB total ({mem.percent}%)"
        }

    def disk_usage(self, path: str = "C:\\") -> dict:
        """Return disk usage for a given path."""
        usage = psutil.disk_usage(path)
        return {
            "path": path,
            "total_gb": round(usage.total / 1e9, 2),
            "used_gb": round(usage.used / 1e9, 2),
            "free_gb": round(usage.free / 1e9, 2),
            "percent": usage.percent,
            "formatted": f"Disk ({path}): {round(usage.used/1e9,1)}GB used / {round(usage.total/1e9,1)}GB total ({usage.percent}%)"
        }

    def gpu_temp(self) -> dict:
        """Return GPU temperature using nvidia-smi (NVIDIA) or WMI fallback."""
        if GPU_BACKEND == "nvidia":
            return self._gpu_nvidia()
        elif GPU_BACKEND == "wmi":
            return self._gpu_wmi()
        else:
            return {"error": "GPU monitoring disabled (GPU_BACKEND=none)"}

    def _gpu_nvidia(self) -> dict:
        """Get GPU stats via nvidia-smi."""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits"
                ],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return self._gpu_wmi()

            lines = result.stdout.strip().splitlines()
            gpus = []
            for line in lines:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 5:
                    gpus.append({
                        "name": parts[0],
                        "temperature_c": int(parts[1]),
                        "utilization_percent": int(parts[2]),
                        "memory_used_mb": int(parts[3]),
                        "memory_total_mb": int(parts[4]),
                        "formatted": f"GPU: {parts[0]} | Temp: {parts[1]}°C | Load: {parts[2]}% | VRAM: {parts[3]}MB/{parts[4]}MB"
                    })
            return {"gpus": gpus, "formatted": " | ".join(g["formatted"] for g in gpus)}
        except FileNotFoundError:
            return self._gpu_wmi()
        except Exception as e:
            return {"error": f"nvidia-smi failed: {e}"}

    def _gpu_wmi(self) -> dict:
        """Fallback GPU info via WMI (no temp, but works without NVIDIA GPU)."""
        try:
            result = subprocess.run(
                ["wmic", "path", "win32_videocontroller", "get", "name,adapterram"],
                capture_output=True, text=True, timeout=5
            )
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip() and "Name" not in l]
            gpus = []
            for line in lines:
                parts = line.rsplit(None, 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    try:
                        vram_mb = int(parts[1]) // (1024 * 1024)
                    except ValueError:
                        vram_mb = 0
                    gpus.append({
                        "name": name,
                        "vram_mb": vram_mb,
                        "temperature_c": "N/A (install nvidia-smi for NVIDIA GPUs)",
                        "formatted": f"GPU: {name} | VRAM: {vram_mb}MB | Temp: N/A"
                    })
            return {"gpus": gpus, "formatted": " | ".join(g["formatted"] for g in gpus) or "No GPU found"}
        except Exception as e:
            return {"error": f"WMI GPU query failed: {e}"}

    def all_stats(self) -> dict:
        """Return all system stats in one call."""
        stats = {
            "cpu": self.cpu_usage(),
            "ram": self.ram_usage(),
            "disk": self.disk_usage(),
            "gpu": self.gpu_temp(),
        }
        summary = " | ".join([
            stats["cpu"]["formatted"],
            stats["ram"]["formatted"],
            stats["disk"]["formatted"],
            stats["gpu"].get("formatted", "GPU: N/A")
        ])
        stats["summary"] = summary
        return stats

    def list_processes(self, top_n: int = 15, sort_by: str = "cpu") -> list[dict]:
        """Return top N processes sorted by CPU or memory."""
        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append({
                    "pid": proc.info["pid"],
                    "name": proc.info["name"],
                    "cpu_percent": proc.info["cpu_percent"] or 0,
                    "memory_percent": round(proc.info["memory_percent"] or 0, 2),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        key = "cpu_percent" if sort_by == "cpu" else "memory_percent"
        return sorted(procs, key=lambda x: x[key], reverse=True)[:top_n]
