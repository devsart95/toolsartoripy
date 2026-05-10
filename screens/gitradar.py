"""GitRadar — Estado de todos los repos en ~/Devsar/."""
import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.widgets import Static
from textual.app import ComposeResult
from textual.containers import VerticalScroll

from widgets.shared import is_view_active

logger = logging.getLogger(__name__)
DEVSAR = Path.home() / "Devsar"
_last_repo_error = ""


@dataclass
class GitResult:
    ok: bool
    stdout: str = ""
    error: str = ""


def _git(cmd: list[str], cwd: Path) -> GitResult:
    try:
        r = subprocess.run(
            ["git"] + cmd, cwd=str(cwd),
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            err = (r.stderr or "").strip() or f"git {' '.join(cmd)} fallo con codigo {r.returncode}"
            logger.warning("git command failed in %s: %s", cwd, err)
            return GitResult(False, r.stdout.strip(), err)
        return GitResult(True, r.stdout.strip(), "")
    except FileNotFoundError:
        err = "comando no disponible: git"
        logger.warning(err)
        return GitResult(False, "", err)
    except subprocess.TimeoutExpired:
        err = "timeout ejecutando git"
        logger.warning("%s en %s: git %s", err, cwd, " ".join(cmd))
        return GitResult(False, "", err)
    except PermissionError:
        err = "sin permisos para ejecutar git"
        logger.warning("%s en %s", err, cwd)
        return GitResult(False, "", err)
    except Exception as exc:
        err = f"error inesperado ejecutando git: {exc}"
        logger.exception("git command failed in %s", cwd)
        return GitResult(False, "", err)


def _repos() -> list[Path]:
    global _last_repo_error
    _last_repo_error = ""
    if not DEVSAR.exists():
        _last_repo_error = f"Directorio no encontrado: {DEVSAR}"
        return []
    repos = []
    try:
        for d in sorted(DEVSAR.iterdir()):
            if d.is_dir() and (d / ".git").exists():
                repos.append(d)
    except PermissionError:
        _last_repo_error = f"sin permisos para leer {DEVSAR}"
        logger.exception(_last_repo_error)
    except OSError:
        _last_repo_error = f"error de sistema al leer {DEVSAR}"
        logger.exception(_last_repo_error)
    return repos


def build_renderable():
    repos = _repos()

    if not repos:
        msg = Text(f"  No se encontraron repos git en {DEVSAR}", "yellow")
        if _last_repo_error:
            msg.append(f"\n  {_last_repo_error}", "bold red")
        return Panel(
            msg,
            title="[bold green] 🎯  GitRadar [/]", border_style="green",
        )

    tbl = Table(box=box.SIMPLE, header_style="bold green", show_edge=False, padding=(0, 1))
    tbl.add_column("Repo",          width=22, style="bold white")
    tbl.add_column("Rama",          width=18, style="bold cyan")
    tbl.add_column("Estado",        width=10, justify="center")
    tbl.add_column("↑↓ origin",     width=10, justify="center")
    tbl.add_column("Ultimo commit", width=38, style="dim white")

    clean_count = 0
    error_count = 0

    for repo in repos:
        branch_result = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo)
        status_result = _git(["status", "--porcelain"], repo)
        branch = branch_result.stdout or "?"
        status_ok = status_result.ok
        n_dirty = len([l for l in status_result.stdout.splitlines() if l.strip()]) if status_ok else 0
        if status_ok and n_dirty == 0:
            clean_count += 1
        elif not status_ok:
            error_count += 1

        # ahead / behind
        ahead = behind = 0
        has_upstream = False
        ab = _git(["rev-list", "--left-right", "--count", "HEAD...@{u}"], repo)
        if ab.ok and ab.stdout and "\t" in ab.stdout:
            try:
                a_str, b_str = ab.stdout.split("\t", 1)
                ahead, behind = int(a_str), int(b_str)
                has_upstream = True
            except (ValueError, IndexError):
                has_upstream = False

        # ultimo commit
        last_result = _git(["log", "-1", "--pretty=format:%s · %cr", "--no-merges"], repo)
        last = last_result.stdout[:38] if last_result.ok and last_result.stdout else "—"

        # color rama
        if branch in ("main", "master"):
            branch_style = "bold green"
        elif branch.startswith(("feat", "feature")):
            branch_style = "bold cyan"
        elif branch.startswith("fix"):
            branch_style = "bold yellow"
        else:
            branch_style = "cyan"

        dirty_txt = Text()
        if not status_ok:
            dirty_txt.append("! error", "bold red")
        elif n_dirty > 0:
            dirty_txt.append(f"✎ {n_dirty}", "bold yellow")
        else:
            dirty_txt.append("✓ limpio", "bold green")

        ahead_txt = Text()
        if has_upstream:
            if ahead > 0:
                ahead_txt.append(f"↑{ahead}", "bold green")
            if behind > 0:
                ahead_txt.append(f" ↓{behind}", "bold red")
            if ahead == 0 and behind == 0:
                ahead_txt.append("≡", "dim white")
        else:
            ahead_txt.append("—", "dim white")

        tbl.add_row(
            repo.name[:22],
            Text(branch, style=branch_style),
            dirty_txt,
            ahead_txt,
            status_result.error[:38] if not status_ok else last,
        )

    summary = Text()
    summary.append(f"  {len(repos)} repos en ", "dim white")
    summary.append(str(DEVSAR), "dim cyan")
    summary.append(f"   ·   {clean_count} limpios", "bold green")
    dirty_total = len(repos) - clean_count - error_count
    summary.append(f"   ·   {dirty_total} con cambios",
                   "bold yellow" if dirty_total else "dim white")
    if error_count:
        summary.append(f"   ·   {error_count} con error", "bold red")

    return Group(
        Panel(summary, border_style="green", padding=(0, 1)),
        Panel(tbl, title="[bold green] 🎯  GitRadar [/]", border_style="green"),
    )


class GitRadarView(VerticalScroll):
    DEFAULT_CSS = """
    GitRadarView {
        width: 100%;
        height: 100%;
    }
    """

    _last_build: float = 0

    def compose(self) -> ComposeResult:
        yield Static("Cargando repos…", id="gr_view")

    def on_mount(self) -> None:
        self.set_interval(30, self.refresh_view)
        # Construccion inicial diferida
        self.call_after_refresh(self.refresh_view)

    def refresh_view(self) -> None:
        if not is_view_active(self, "gitradar"):
            return
        now = time.monotonic()
        if now - self._last_build < 5:
            return
        self._last_build = now
        # Correr en worker para no bloquear el loop con git subprocess
        self.run_worker(self._build_async, exclusive=True, thread=True)

    def _build_async(self) -> None:
        rendered = build_renderable()
        self.app.call_from_thread(self._apply, rendered)

    def _apply(self, rendered) -> None:
        try:
            self.query_one("#gr_view", Static).update(rendered)
        except Exception:
            logger.exception("No se pudo actualizar GitRadar")
