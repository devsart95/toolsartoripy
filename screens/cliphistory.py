"""ClipHistory — Historial del clipboard en sesion (macOS)."""
import logging
import re
import subprocess
import threading
import time

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.widgets import Button, Static
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll

from widgets.shared import is_view_active

logger = logging.getLogger(__name__)
_history: list[tuple[str, float]] = []   # (contenido, timestamp)
_last_clip: str = ""
_history_lock = threading.Lock()
MAX_HISTORY = 50
MAX_PREVIEW = 80
_capture_enabled = False
_last_error = ""

_SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password|passwd|pwd)\b\s*[:=]\s*['\"]?([^\s'\";,]+)"),
    re.compile(r"\b(sk-[A-Za-z0-9_-]{20,})\b"),
    re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\b(xox[baprs]-[A-Za-z0-9-]{20,})\b"),
    re.compile(r"\b([A-Za-z0-9_=-]{32,})\b"),
]


def _redact(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        if pattern.groups >= 2:
            redacted = pattern.sub(lambda m: f"{m.group(1)}=[REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _pbpaste() -> str:
    global _last_error
    _last_error = ""
    try:
        r = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=2)
        if r.returncode != 0:
            _last_error = (r.stderr or "").strip() or f"pbpaste fallo con codigo {r.returncode}"
            logger.warning("pbpaste failed: %s", _last_error)
            return ""
        return r.stdout
    except FileNotFoundError:
        _last_error = "comando no disponible: pbpaste"
        logger.warning(_last_error)
        return ""
    except subprocess.TimeoutExpired:
        _last_error = "timeout leyendo clipboard"
        logger.warning(_last_error)
        return ""
    except PermissionError:
        _last_error = "sin permisos para leer clipboard"
        logger.warning(_last_error)
        return ""
    except Exception:
        _last_error = "error inesperado leyendo clipboard"
        logger.exception(_last_error)
        return ""


def _poll_clipboard() -> None:
    """Lee pbpaste y agrega al historial si cambio. Llamar en worker thread."""
    global _last_clip
    if not _capture_enabled:
        return
    current = _pbpaste()
    if not current:
        return
    with _history_lock:
        if current != _last_clip:
            _last_clip = current
            _history.insert(0, (_redact(current), time.time()))
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
    capture_enabled = _capture_enabled
    last_error = _last_error

    status = Text()
    status.append("  Captura: ", "dim white")
    status.append("activa" if capture_enabled else "desactivada", "bold green" if capture_enabled else "bold yellow")
    status.append("  ·  Secretos: redaccion automatica  ·  Max: 50 entradas", "dim cyan")
    if last_error:
        status.append(f"\n  {last_error}", "bold red")

    if not snapshot:
        msg = Text()
        msg.append("\n  Historial vacio.\n\n", "dim white")
        if capture_enabled:
            msg.append("  Copia algo para agregarlo al historial de esta sesion.", "dim cyan")
        else:
            msg.append("  Activa captura para empezar. El clipboard no se lee mientras esta desactivado.", "dim cyan")
        return Group(
            Panel(status, border_style="white", padding=(0, 1)),
            Panel(msg, title="[bold white] 📋  ClipHistory [/]", border_style="white"),
        )

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
    summary.append("captura opt-in, no persistente", "dim white")

    return Group(
        Panel(status, border_style="white", padding=(0, 1)),
        Panel(summary, border_style="white", padding=(0, 1)),
        Panel(tbl, title="[bold white] 📋  ClipHistory [/]", border_style="white"),
    )


class ClipHistoryView(VerticalScroll):
    DEFAULT_CSS = """
    ClipHistoryView {
        width: 100%;
        height: 100%;
    }
    #ch_controls {
        height: auto;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="ch_controls"):
            yield Button("Activar captura", id="ch_toggle", variant="success")
            yield Button("Clear", id="ch_clear", variant="warning")
        yield Static(id="ch_view")

    def on_mount(self) -> None:
        # Poll del clipboard en worker controlado, refresh UI en main
        self.set_interval(1, self._poll_worker)
        self.set_interval(1, self.refresh_view)
        self.refresh_view()

    def _poll_worker(self) -> None:
        if not is_view_active(self, "cliphistory") or not _capture_enabled:
            return
        self.run_worker(_poll_clipboard, exclusive=True, thread=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        global _capture_enabled, _last_clip
        if event.button.id == "ch_toggle":
            _capture_enabled = not _capture_enabled
            if not _capture_enabled:
                _last_clip = ""
            self._sync_buttons()
            self.refresh_view()
        elif event.button.id == "ch_clear":
            with _history_lock:
                _history.clear()
            _last_clip = ""
            self.refresh_view()

    def _sync_buttons(self) -> None:
        try:
            btn = self.query_one("#ch_toggle", Button)
            btn.label = "Desactivar captura" if _capture_enabled else "Activar captura"
            btn.variant = "error" if _capture_enabled else "success"
        except Exception:
            logger.exception("No se pudo actualizar controles de ClipHistory")

    def refresh_view(self) -> None:
        if not is_view_active(self, "cliphistory"):
            return
        try:
            self._sync_buttons()
            self.query_one("#ch_view", Static).update(build_renderable())
        except Exception:
            logger.exception("No se pudo actualizar ClipHistory")
