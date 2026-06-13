import platform
import shutil
import time
from pathlib import Path

try:
    import psutil  # type: ignore
except Exception:  # noqa: BLE001
    psutil = None


def _human_bytes(num: float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


def get_system_snapshot(cpu_interval: float = 0.0) -> dict:
    info = {
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "uptime": "N/A",
        "cpu": "N/A",
        "ram": "N/A",
        "disk": "N/A",
        "battery": "N/A",
        "processes": "N/A",
    }

    if psutil is not None:
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = int(time.time() - boot_time)
            hours = uptime_seconds // 3600
            minutes = (uptime_seconds % 3600) // 60
            info["uptime"] = f"{hours}h {minutes}m"
        except Exception:  # noqa: BLE001
            pass

        try:
            info["cpu"] = f"{psutil.cpu_percent(interval=cpu_interval):.1f}%"
        except Exception:  # noqa: BLE001
            pass

        try:
            mem = psutil.virtual_memory()
            info["ram"] = f"{mem.percent:.1f}% ({_human_bytes(mem.used)} / {_human_bytes(mem.total)})"
        except Exception:  # noqa: BLE001
            pass

        try:
            disk = psutil.disk_usage(str(Path.home()))
            info["disk"] = f"{disk.percent:.1f}% ({_human_bytes(disk.used)} / {_human_bytes(disk.total)})"
        except Exception:  # noqa: BLE001
            pass

        try:
            bat = psutil.sensors_battery()
            if bat is not None:
                charging = " (charging)" if bat.power_plugged else ""
                info["battery"] = f"{bat.percent:.1f}%{charging}"
        except Exception:  # noqa: BLE001
            pass

        try:
            info["processes"] = str(len(psutil.pids()))
        except Exception:  # noqa: BLE001
            pass
    else:
        total, used, _free = shutil.disk_usage(Path.home())
        info["disk"] = f"{_human_bytes(used)} / {_human_bytes(total)}"

    return info
