"""DockerGlitch — Contenedores Docker en tiempo real."""
import json
import subprocess

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.widgets import Static
from textual.app import ComposeResult
from textual.containers import VerticalScroll

from widgets.shared import is_view_active


def _docker_ps() -> list[dict]:
    try:
        r = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            return []
        out = []
        for line in r.stdout.strip().splitlines():
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def _docker_stats() -> dict[str, dict]:
    try:
        r = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return {}
        stats = {}
        for line in r.stdout.strip().splitlines():
            try:
                d = json.loads(line)
                cid = d.get("ID", "") or ""
                stats[cid[:12]] = d
            except json.JSONDecodeError:
                continue
        return stats
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}


def build_renderable():
    containers = _docker_ps()

    if not containers:
        msg = Text()
        msg.append("\n  Docker no disponible o sin contenedores.\n", "yellow")
        msg.append("  Asegurate de que Docker Desktop este corriendo.", "dim white")
        return Panel(msg, title="[bold cyan] 🐳  DockerGlitch [/]", border_style="cyan")

    # Solo pedir stats si hay contenedores running (docker stats hangs si no hay)
    has_running = any(c.get("State") == "running" for c in containers)
    stats = _docker_stats() if has_running else {}

    tbl = Table(box=box.SIMPLE, header_style="bold cyan", show_edge=False, padding=(0, 1))
    tbl.add_column("Nombre",   width=24, style="bold white")
    tbl.add_column("Imagen",   width=22, style="dim white")
    tbl.add_column("Estado",   width=12)
    tbl.add_column("CPU %",    width=8,  justify="right")
    tbl.add_column("RAM",      width=14, justify="right")
    tbl.add_column("Puertos",  width=20, style="dim cyan")

    running = sum(1 for c in containers if c.get("State") == "running")

    for c in containers:
        cid     = (c.get("ID") or "")[:12]
        name    = (c.get("Names") or c.get("Name") or "?")[:24]
        image   = (c.get("Image") or "?")[:22]
        state   = c.get("State") or c.get("Status") or "?"
        ports   = (c.get("Ports") or "—")[:20]

        st_color = "bold green" if state == "running" else ("yellow" if state == "paused" else "dim red")

        cstats = stats.get(cid, {})
        cpu_str = (cstats.get("CPUPerc") or "").replace("%", "").strip()
        mem_raw = cstats.get("MemUsage") or ""
        mem_str = mem_raw.split("/")[0].strip() if mem_raw else "—"

        try:
            cpu_val = float(cpu_str) if cpu_str else 0.0
            cpu_color = "bold red" if cpu_val > 80 else ("yellow" if cpu_val > 40 else "green")
            cpu_display = f"[{cpu_color}]{cpu_val:.1f}%[/]"
        except (ValueError, TypeError):
            cpu_display = "—"

        tbl.add_row(name, image, f"[{st_color}]{state}[/]", cpu_display, mem_str, ports)

    summary = Text()
    summary.append(f"  {len(containers)} contenedores  ·  ", "dim white")
    summary.append(f"{running} running", "bold green")
    stopped = len(containers) - running
    summary.append(f"  ·  {stopped} detenidos", "dim red" if stopped else "dim white")

    return Group(
        Panel(summary, border_style="cyan", padding=(0, 1)),
        Panel(tbl, title="[bold cyan] 🐳  DockerGlitch [/]", border_style="cyan"),
    )


class DockerGlitchView(VerticalScroll):
    DEFAULT_CSS = """
    DockerGlitchView {
        width: 100%;
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Consultando Docker…", id="dg_view")

    def on_mount(self) -> None:
        self.set_interval(5, self.refresh_view)
        self.call_after_refresh(self.refresh_view)

    def refresh_view(self) -> None:
        if not is_view_active(self, "dockerglitch"):
            return
        # docker stats puede tardar varios segundos: a worker thread
        self.run_worker(self._build_async, exclusive=True, thread=True)

    def _build_async(self) -> None:
        rendered = build_renderable()
        self.app.call_from_thread(self._apply, rendered)

    def _apply(self, rendered) -> None:
        try:
            self.query_one("#dg_view", Static).update(rendered)
        except Exception:
            pass
