"""GitRadar — Estado de todos los repos en ~/Devsar/."""
import subprocess
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

from widgets.shared import is_view_active

DEVSAR = Path.home() / "Devsar"


def _git(cmd: list[str], cwd: Path) -> str:
    try:
        r = subprocess.run(
            ["git"] + cmd, cwd=str(cwd),
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip()
    except Exception:
        return ""


def _repos() -> list[Path]:
    if not DEVSAR.exists():
        return []
    repos = []
    try:
        for d in sorted(DEVSAR.iterdir()):
            if d.is_dir() and (d / ".git").exists():
                repos.append(d)
    except (OSError, PermissionError):
        pass
    return repos


def build_renderable():
    repos = _repos()

    if not repos:
        return Panel(
            Text(f"  No se encontraron repos git en {DEVSAR}", "yellow"),
            title="[bold green] 🎯  GitRadar [/]", border_style="green",
        )

    tbl = Table(box=box.SIMPLE, header_style="bold green", show_edge=False, padding=(0, 1))
    tbl.add_column("Repo",          width=22, style="bold white")
    tbl.add_column("Rama",          width=18, style="bold cyan")
    tbl.add_column("Estado",        width=10, justify="center")
    tbl.add_column("↑↓ origin",     width=10, justify="center")
    tbl.add_column("Ultimo commit", width=38, style="dim white")

    clean_count = 0

    for repo in repos:
        branch  = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo) or "?"
        dirty   = _git(["status", "--porcelain"], repo)
        n_dirty = len([l for l in dirty.splitlines() if l.strip()])
        if n_dirty == 0:
            clean_count += 1

        # ahead / behind
        ahead = behind = 0
        has_upstream = False
        ab = _git(["rev-list", "--left-right", "--count", "HEAD...@{u}"], repo)
        if ab and "\t" in ab:
            try:
                a_str, b_str = ab.split("\t", 1)
                ahead, behind = int(a_str), int(b_str)
                has_upstream = True
            except (ValueError, IndexError):
                has_upstream = False

        # ultimo commit
        last = _git(["log", "-1", "--pretty=format:%s · %cr", "--no-merges"], repo)
        last = last[:38] if last else "—"

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
        if n_dirty > 0:
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
            last,
        )

    summary = Text()
    summary.append(f"  {len(repos)} repos en ", "dim white")
    summary.append(str(DEVSAR), "dim cyan")
    summary.append(f"   ·   {clean_count} limpios", "bold green")
    dirty_total = len(repos) - clean_count
    summary.append(f"   ·   {dirty_total} con cambios",
                   "bold yellow" if dirty_total else "dim white")

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
            pass
