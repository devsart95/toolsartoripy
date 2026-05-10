"""LogTail — Tail de logs del sistema macOS."""
import datetime
import subprocess
from pathlib import Path

from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static
from textual.app import ComposeResult
from textual.containers import VerticalScroll

from widgets.shared import is_view_active

COMMON_LOGS = [
    Path("/var/log/system.log"),
    Path("/var/log/install.log"),
]

_LEVEL_COLORS = {
    "error":   "bold red",
    "fault":   "bold red",
    "warning": "yellow",
    "warn":    "yellow",
    "info":    "dim white",
    "debug":   "dim cyan",
    "notice":  "white",
}


def _colorize_line(line: str) -> Text:
    t = Text()
    lower = line.lower()
    for keyword, color in _LEVEL_COLORS.items():
        if keyword in lower:
            t.append(line[:160] + "\n", style=color)
            return t
    t.append(line[:160] + "\n", style="dim white")
    return t


def _tail_file(path: Path, lines: int = 30) -> list[str]:
    try:
        r = subprocess.run(
            ["tail", "-n", str(lines), str(path)],
            capture_output=True, text=True, timeout=3,
        )
        return r.stdout.splitlines()
    except Exception:
        return []


def _unified_log(predicate: str, last: str = "5m") -> list[str]:
    try:
        r = subprocess.run(
            ["log", "show", "--predicate", predicate, "--last", last, "--style", "syslog"],
            capture_output=True, text=True, timeout=15,
        )
        return r.stdout.splitlines()[-30:]
    except Exception:
        return []


def build_renderable():
    panels = []

    # Logs de archivos disponibles
    for log_path in COMMON_LOGS:
        if not log_path.is_file():
            continue
        lines = _tail_file(log_path, 20)
        if not lines:
            continue
        t = Text()
        for line in lines:
            t.append_text(_colorize_line(line))
        panels.append(Panel(
            t,
            title=f"[bold yellow] 📄  {log_path.name} [/]",
            border_style="yellow",
            padding=(0, 1),
        ))

    # Unified log del sistema (errores recientes)
    error_lines = _unified_log('eventMessage contains[c] "error" OR eventMessage contains[c] "fail"')
    if error_lines:
        t = Text()
        for line in error_lines[-20:]:
            t.append_text(_colorize_line(line))
        panels.append(Panel(
            t,
            title="[bold red] 🔴  Errores recientes (ultimos 5m) [/]",
            border_style="red",
            padding=(0, 1),
        ))

    # Diagnosticos recientes
    diag_dir = Path.home() / "Library/Logs/DiagnosticReports"
    if diag_dir.exists():
        try:
            reports = sorted(
                diag_dir.glob("*.ips"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )[:5]
        except (OSError, PermissionError):
            reports = []
        if reports:
            t = Text()
            for rpt in reports:
                try:
                    mtime = datetime.datetime.fromtimestamp(rpt.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                except OSError:
                    mtime = "?"
                t.append(f"  {mtime}  ", "dim white")
                t.append(rpt.stem[:60] + "\n", "white")
            panels.append(Panel(t, title="[bold magenta] 💥  Crash Reports [/]",
                                border_style="magenta", padding=(0, 1)))

    if not panels:
        return Panel(
            Text("  Sin logs disponibles o sin permisos para leerlos.\n"
                 "  Algunos logs requieren Full Disk Access en Preferencias del Sistema.", "yellow"),
            title="[bold yellow] 📋  LogTail [/]", border_style="yellow",
        )

    return Group(*panels)


class LogTailView(VerticalScroll):
    DEFAULT_CSS = """
    LogTailView {
        width: 100%;
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Cargando logs… (puede tardar varios segundos)", id="lt_view")

    def on_mount(self) -> None:
        self.set_interval(15, self.refresh_view)
        self.call_after_refresh(self.refresh_view)

    def refresh_view(self) -> None:
        if not is_view_active(self, "logtail"):
            return
        # `log show` es lento: a worker thread
        self.run_worker(self._build_async, exclusive=True, thread=True)

    def _build_async(self) -> None:
        rendered = build_renderable()
        self.app.call_from_thread(self._apply, rendered)

    def _apply(self, rendered) -> None:
        try:
            self.query_one("#lt_view", Static).update(rendered)
        except Exception:
            pass
