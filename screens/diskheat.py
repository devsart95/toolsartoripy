"""DiskHeat — Directorios mas pesados y caches recuperables."""
import logging
import os
import time
from pathlib import Path

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.widgets import Static
from textual.app import ComposeResult
from textual.containers import VerticalScroll

from config import code_dir, scan_roots
from widgets.shared import human, is_view_active

logger = logging.getLogger(__name__)
SKIP_DIRS  = {".git", "node_modules", ".next", "__pycache__", ".venv", "venv", ".cache",
              "Library", ".Trash", "vendor", "dist", "build", ".nuxt", ".turbo"}
MAX_RGLOB_DEPTH = 3   # limite para escanear caches sin perderse en el FS


def _dir_size(path: Path, max_depth: int = 2, depth: int = 0) -> int:
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_symlink():
                        continue
                    if entry.is_file(follow_symlinks=False):
                        try:
                            total += entry.stat(follow_symlinks=False).st_size
                        except OSError:
                            logger.debug("No se pudo leer tamano de %s", entry.path, exc_info=True)
                    elif entry.is_dir(follow_symlinks=False) and entry.name not in SKIP_DIRS and depth < max_depth:
                        total += _dir_size(Path(entry.path), max_depth, depth + 1)
                except OSError:
                    continue
    except PermissionError:
        logger.warning("sin permisos para escanear %s", path)
    except OSError:
        logger.debug("No se pudo escanear %s", path, exc_info=True)
    return total


def _top_dirs(root: Path, limit: int = 12) -> list[tuple[Path, int]]:
    results = []
    try:
        with os.scandir(root) as it:
            for entry in it:
                try:
                    if entry.is_dir(follow_symlinks=False) and not entry.name.startswith("."):
                        size = _dir_size(Path(entry.path))
                        if size > 0:
                            results.append((Path(entry.path), size))
                except OSError:
                    continue
    except PermissionError:
        logger.warning("sin permisos para escanear %s", root)
    except OSError:
        logger.debug("No se pudo escanear %s", root, exc_info=True)
    return sorted(results, key=lambda x: x[1], reverse=True)[:limit]


def _find_named_dirs(root: Path, name: str, max_depth: int = MAX_RGLOB_DEPTH) -> list[Path]:
    """Busca directorios por nombre limitando profundidad — evita rglob lento."""
    found: list[Path] = []
    if not root.exists():
        return found

    def walk(p: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            with os.scandir(p) as it:
                for entry in it:
                    try:
                        if not entry.is_dir(follow_symlinks=False):
                            continue
                        if entry.name == name:
                            found.append(Path(entry.path))
                            # No descender dentro del propio match
                            continue
                        if entry.name in SKIP_DIRS:
                            continue
                        walk(Path(entry.path), depth + 1)
                    except OSError:
                        continue
        except (PermissionError, OSError):
            return

    walk(root, 0)
    return found


def _heavy_cache_dirs() -> list[tuple[str, int]]:
    devsar = code_dir()
    found: list[tuple[str, int]] = []

    if devsar.exists():
        nm_dirs = _find_named_dirs(devsar, "node_modules")
        nm_total = sum(_dir_size(p, max_depth=1) for p in nm_dirs[:50])
        if nm_total > 0:
            found.append((f"node_modules ({len(nm_dirs)} dirs)", nm_total))

        next_dirs = _find_named_dirs(devsar, ".next")
        next_total = sum(_dir_size(p, max_depth=1) for p in next_dirs[:50])
        if next_total > 0:
            found.append((f".next builds ({len(next_dirs)} dirs)", next_total))

    return found


def build_renderable():
    panels = []

    for root in scan_roots():
        if not root.exists():
            continue
        dirs = _top_dirs(root)
        if not dirs:
            continue
        tbl = Table(box=box.SIMPLE, header_style="bold yellow", show_edge=False, padding=(0, 1))
        tbl.add_column("Directorio", width=32, style="bold white")
        tbl.add_column("Tamano",     width=12, justify="right")
        tbl.add_column("Bar",        width=28)

        max_size = dirs[0][1] if dirs else 1
        for path, size in dirs:
            pct   = (size / max_size * 100) if max_size else 0
            color = "bold red" if pct > 80 else ("yellow" if pct > 40 else "green")
            bar   = "█" * int(pct / 4)
            tbl.add_row(
                path.name[:32],
                human(size),
                Text(f"{bar:<25} {pct:4.0f}%", style=color),
            )
        panels.append(Panel(tbl, title=f"[bold yellow] 📂  {root} [/]", border_style="yellow"))

    # Caches recuperables
    caches = _heavy_cache_dirs()
    if caches:
        ct = Text()
        for label, size in caches:
            ct.append(f"  {label:<30} ", "dim white")
            ct.append(f"{human(size)}\n", "bold red")
        recoverable = sum(s for _, s in caches)
        ct.append("\n  Espacio recuperable estimado: ", "dim white")
        ct.append(human(recoverable), "bold yellow")
        panels.append(Panel(ct, title="[bold red] 🗑  Caches pesadas [/]", border_style="red", padding=(0, 1)))

    if not panels:
        return Panel(Text("  No se encontraron directorios para analizar.", "yellow"),
                     title="[bold yellow] 💾  DiskHeat [/]", border_style="yellow")

    return Group(*panels)


class DiskHeatView(VerticalScroll):
    DEFAULT_CSS = """
    DiskHeatView {
        width: 100%;
        height: 100%;
    }
    """

    _last_build: float = 0

    def compose(self) -> ComposeResult:
        yield Static("Escaneando disco… (puede tardar varios segundos)", id="dh_view")

    def on_mount(self) -> None:
        self.set_interval(120, self.refresh_view)
        self.call_after_refresh(self.refresh_view)

    def refresh_view(self) -> None:
        if not is_view_active(self, "diskheat"):
            return
        now = time.monotonic()
        if now - self._last_build < 30:
            return
        self._last_build = now
        self.run_worker(self._build_async, exclusive=True, thread=True)

    def _build_async(self) -> None:
        rendered = build_renderable()
        self.app.call_from_thread(self._apply, rendered)

    def _apply(self, rendered) -> None:
        try:
            self.query_one("#dh_view", Static).update(rendered)
        except Exception:
            logger.exception("No se pudo actualizar DiskHeat")
