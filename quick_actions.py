import os
import subprocess
import webbrowser
from pathlib import Path


class ActionError(Exception):
    pass


def open_path(path: str) -> None:
    target = Path(path).expanduser()
    if not target.exists():
        raise ActionError(f"Path does not exist: {target}")

    try:
        if os.name == "nt":
            os.startfile(target)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(target)])
    except Exception as exc:  # noqa: BLE001
        raise ActionError(str(exc)) from exc


def open_web(url: str) -> None:
    ok = webbrowser.open(url)
    if not ok:
        raise ActionError(f"Failed to open URL: {url}")


def run_command(command: str) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            timeout=20,
        )
    except Exception as exc:  # noqa: BLE001
        raise ActionError(str(exc)) from exc

    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode, output.strip()
