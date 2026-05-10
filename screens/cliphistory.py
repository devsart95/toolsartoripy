"""ClipHistory — Historial del clipboard en sesion (macOS)."""
import subprocess
import threading
import time

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.widgets import Static
from textual.app import ComposeResult
from textual.containers import VerticalScroll

from widgets.shared import is_view_active

_history: list[tuple[str, float]] = []   # (contenido, timestamp)
_last_clip: str = ""
_history_lock = threading.Lock()
MAX_HISTORY = 50
MAX_PREVIEW = 80


def _pbpaste() -> str:
    try:
        r = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=2)
        return r.stdout
    except Exception:
        return ""


def _poll_clipboard() -> None:
    """Lee pbpaste y agrega al historial si cambio. Llamar en worker thread."""
    global _last_clip
    current = _pbpaste()
    if not current:
        return
    with _history_lock:
        if current != _last_clip:
            _last_clip = current
            _history.insert(0, (current, time.time()))
            if len(_history) > MAX_HISTORY:
                _history.pop()


def _ago(ts: float) -> str:
    s = int(time.time() - ts)
    if s < 60:   return f"{s}s"
    if s < 3600: return f"{s // 60}m"
    return f"{s // 3600}h"


def _preview(text: str) -> str:
    line = text.strip().replace("\n", " ↵ ").replace("\t", " → ")
    return line[:MAX_PREVIEW] + ("…" if len(line) > MAX_PREVIEW else "")


def _type_icon(text: str) -> tuple[str, str]:
    """Detecta tipo de contenido y retorna (icono, color)."""
    s = text.strip()
    if s.startswith(("http://", "https://")):
        return "🔗", "bold cyan"
    if "\n" in s and len(s.splitlines()) > 2:
        return "📄", "dim white"
    if any(kw in s for kw in ("def ", "class ", "function", "import ", "const ", "let ")):
        return "💻", "bold green"
    if s and s.lstrip("-").replace(".", "").isdigit():
        return "🔢", "yellow"
    return "📋", "white"


def build_renderable():
    with _history_lock:
        snapshot = list(_history)

    if not snapshot:
        msg = Text()
        msg.append("\n  Historial vacio — copia algo para empezar.\n\n", "dim white")
        msg.append("  Actualizacion: cada 1s  ·  Max: 50 entradas", "dim cyan")
        return Panel(msg, title="[bold white] 📋  ClipHistory [/]", border_style="white")

    tbl = Table(box=box.SIMPLE, header_style="bold white", show_edge=False, padding=(0, 1))
    tbl.add_column("#",         width=4,  justify="right", style="dim white")
    tbl.add_column("T",         width=3,  justify="center")
    tbl.add_column("Contenido", width=70)
    tbl.add_column("Hace",      width=8,  justify="right", style="dim white")
    tbl.add_column("Bytes",     width=8,  justify="right", style="dim white")

    for i, (content, ts) in enumerate(snapshot[:30]):
        icon, color = _type_icon(content)
        tbl.add_row(
            str(i + 1),
            icon,
            Text(_preview(content), style=color if i == 0 else "white"),
            _ago(ts),
            str(len(content.encode("utf-8", errors="replace"))),
        )

    summary = Text()
    summary.append(f"  {len(snapshot)} entradas en sesion  ·  ", "dim white")
    summary.append("q → sale de la app", "dim white")

    return Group(
        Panel(summary, border_style="white", padding=(0, 1)),
        Panel(tbl, title="[bold white] 📋  ClipHistory [/]", border_style="white"),
    )


class ClipHistoryView(VerticalScroll):
    DEFAULT_CSS = """
    ClipHistoryView {
        width: 100%;
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(id="ch_view")

    def on_mount(self) -> None:
        # Poll del clipboard en thread separado, refresh UI en main
        self.set_interval(1, self._poll_in_thread)
        self.set_interval(1, self.refresh_view)

    def _poll_in_thread(self) -> None:
        threading.Thread(target=_poll_clipboard, daemon=True).start()

    def refresh_view(self) -> None:
        if not is_view_active(self, "cliphistory"):
            return
        try:
            self.query_one("#ch_view", Static).update(build_renderable())
        except Exception:
            pass
