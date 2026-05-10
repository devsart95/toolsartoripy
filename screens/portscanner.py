"""PortScan — Puertos activos y conexiones del sistema."""
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.widgets import Static
from textual.app import ComposeResult
from textual.containers import VerticalScroll

from widgets.shared import is_view_active, net_connections

_STATE_COLORS = {
    "LISTEN":      "bold green",
    "ESTABLISHED": "cyan",
    "CLOSE_WAIT":  "yellow",
    "TIME_WAIT":   "dim yellow",
    "CLOSING":     "red",
    "FIN_WAIT1":   "dim red",
    "FIN_WAIT2":   "dim red",
    "LAST_ACK":    "red",
    "SYN_SENT":    "bold cyan",
    "SYN_RECV":    "bold cyan",
    "NONE":        "dim white",
}


def build_renderable():
    conns = net_connections()

    if not conns:
        return Panel(
            Text("  lsof no disponible o sin conexiones detectadas.", "yellow"),
            title="[bold red] 🔌  PortScan [/]", border_style="red",
        )

    listen = sorted([c for c in conns if c.status == "LISTEN"],
                    key=lambda c: c.laddr.port if c.laddr else 0)
    active = sorted([c for c in conns if c.status == "ESTABLISHED"],
                    key=lambda c: c.laddr.port if c.laddr else 0)
    other  = [c for c in conns if c.status not in ("LISTEN", "ESTABLISHED")]

    def make_panel(title: str, rows: list, color: str) -> Panel:
        tbl = Table(box=box.SIMPLE, header_style=f"bold {color}", show_edge=False, padding=(0, 1))
        tbl.add_column("Puerto",  width=8,  justify="right")
        tbl.add_column("Proceso", width=24)
        tbl.add_column("PID",     width=7,  justify="right", style="dim cyan")
        tbl.add_column("Remoto",  width=28)
        tbl.add_column("Estado",  width=14)
        for c in rows[:20]:
            port   = str(c.laddr.port) if c.laddr else "?"
            remote = (f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "—")
            state  = c.status or "NONE"
            sc     = _STATE_COLORS.get(state, "white")
            tbl.add_row(
                port,
                (c.name or "—")[:24],
                str(c.pid) if c.pid else "—",
                remote,
                f"[{sc}]{state}[/]",
            )
        return Panel(tbl, title=f"[bold {color}] {title} ({len(rows)}) [/]",
                     border_style=color, padding=(0, 0))

    summary = Text()
    summary.append("  LISTEN: ", "bold green");      summary.append(f"{len(listen)}  ", "white")
    summary.append("ESTABLISHED: ", "bold cyan");    summary.append(f"{len(active)}  ", "white")
    summary.append("Otras: ", "dim white");          summary.append(str(len(other)), "white")
    summary.append("  ·  Total: ", "dim white");     summary.append(str(len(conns)), "bold white")

    return Group(
        Panel(summary, border_style="green", padding=(0, 1)),
        make_panel("En escucha", listen, "green"),
        make_panel("Establecidas", active, "cyan"),
    )


class PortScanView(VerticalScroll):
    DEFAULT_CSS = """
    PortScanView {
        width: 100%;
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(id="ps_view")

    def on_mount(self) -> None:
        self.set_interval(2, self.refresh_view)

    def refresh_view(self) -> None:
        if not is_view_active(self, "portscanner"):
            return
        try:
            self.query_one("#ps_view", Static).update(build_renderable())
        except Exception:
            pass
