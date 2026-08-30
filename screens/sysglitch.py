"""SysGlitch — Monitor de sistema en tiempo real."""
import logging
import time
import platform
from collections import deque
from datetime import timedelta, datetime

import psutil
from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.table import Table
from textual.widgets import Static
from textual.app import ComposeResult
from textual.containers import VerticalScroll

from widgets.shared import pct_bar, pct_style, sparkline, human, is_view_active

logger = logging.getLogger(__name__)
_net0 = None
_net_t0 = None
HISTORY_LEN = 60
_cpu_hist = deque(maxlen=HISTORY_LEN)
_mem_hist = deque(maxlen=HISTORY_LEN)
_tx_hist  = deque(maxlen=HISTORY_LEN)
_rx_hist  = deque(maxlen=HISTORY_LEN)
_APFS_NOISE = {
    "/System/Volumes/Data", "/System/Volumes/Preboot",
    "/System/Volumes/Recovery", "/System/Volumes/VM",
    "/System/Volumes/Update", "/System/Volumes/xarts",
    "/System/Volumes/iSCPreboot", "/System/Volumes/Hardware",
}


def _cpu() -> Panel:
    total = psutil.cpu_percent()
    cores = psutil.cpu_percent(percpu=True)
    t = Text()
    _cpu_hist.append(total)
    t.append("  TOTAL   ", "bold cyan"); t.append_text(pct_bar(total, 26)); t.append("\n")
    t.append("           ", "dim white")
    t.append(sparkline(_cpu_hist, 26, lo=0.0, hi=100.0), pct_style(total))
    t.append("\n\n")
    if cores:
        mid = (len(cores) + 1) // 2
        left = cores[:mid]
        right = cores[mid:]
        for i, lc in enumerate(left):
            t.append(f"  Core {i:<2} ", "dim cyan");        t.append_text(pct_bar(lc, 13))
            if i < len(right):
                t.append(f"   Core {i + mid:<2} ", "dim cyan"); t.append_text(pct_bar(right[i], 13))
            t.append("\n")
    physical = psutil.cpu_count(logical=False) or 0
    logical  = psutil.cpu_count() or 0
    t.append(f"\n  {physical} fisicos · {logical} logicos", "dim white")
    t.append(f"   {platform.machine()}", "dim yellow")
    return Panel(t, title="[bold green] ⚡  CPU [/]", border_style="green", padding=(0, 1))


def _mem() -> Panel:
    m, s = psutil.virtual_memory(), psutil.swap_memory()
    t = Text()
    _mem_hist.append(m.percent)
    t.append("  RAM    ", "bold cyan"); t.append_text(pct_bar(m.percent, 28))
    t.append("\n         ", "dim white")
    t.append(sparkline(_mem_hist, 28, lo=0.0, hi=100.0), pct_style(m.percent))
    t.append(f"\n  {human(m.used)} / {human(m.total)}", "dim white")
    t.append("   libre: ", "dim white"); t.append(human(m.available), "bold green")
    t.append("\n\n  SWAP   ", "bold cyan"); t.append_text(pct_bar(s.percent, 28))
    t.append(f"\n  {human(s.used)} / {human(s.total)}", "dim white")
    t.append("\n\n  TOP RAM\n", "bold cyan")
    procs = []
    for p in psutil.process_iter(["name", "memory_percent", "memory_info"]):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            logger.debug("No se pudo leer proceso para memoria", exc_info=True)
    procs.sort(key=lambda x: x.get("memory_percent") or 0, reverse=True)
    for p in procs[:7]:
        pct  = p.get("memory_percent") or 0.0
        info = p.get("memory_info")
        rss  = info.rss if info else 0
        color = "bold red" if pct > 20 else ("yellow" if pct > 10 else "dim white")
        t.append(f"  {(p.get('name') or '?')[:22]:<22} ", "white")
        t.append(f"{pct:5.1f}%  {human(rss)}\n", color)
    return Panel(t, title="[bold blue] 🧠  Memoria [/]", border_style="blue", padding=(0, 1))


def _disk() -> Panel:
    t = Text()
    shown = 0
    for part in psutil.disk_partitions(all=False):
        if part.mountpoint in _APFS_NOISE or shown >= 4:
            continue
        try:
            u = psutil.disk_usage(part.mountpoint)
            t.append(f"  {part.mountpoint[:12]:<12} ", "bold cyan"); t.append_text(pct_bar(u.percent, 22))
            t.append(f"\n  {human(u.used)} / {human(u.total)}\n", "dim white")
            shown += 1
        except (PermissionError, OSError):
            logger.debug("No se pudo leer uso de disco en %s", part.mountpoint, exc_info=True)
            continue
    try:
        io = psutil.disk_io_counters()
        if io:
            t.append(f"\n  Read  total: {human(io.read_bytes)}", "dim yellow")
            t.append(f"\n  Write total: {human(io.write_bytes)}", "dim yellow")
    except Exception:
        logger.exception("No se pudieron leer contadores de disco")
    return Panel(t, title="[bold yellow] 💾  Disco [/]", border_style="yellow", padding=(0, 1))


def _net() -> Panel:
    global _net0, _net_t0
    n, ts = psutil.net_io_counters(), time.monotonic()
    prev_n, prev_t = _net0, _net_t0
    has_delta = prev_n is not None and prev_t is not None
    tx_spd = rx_spd = 0.0
    if has_delta:
        dt = (ts - prev_t) or 0.001
        tx_spd = max(0.0, (n.bytes_sent - prev_n.bytes_sent) / dt)
        rx_spd = max(0.0, (n.bytes_recv - prev_n.bytes_recv) / dt)
    _net0, _net_t0 = n, ts
    if has_delta:
        _tx_hist.append(tx_spd)
        _rx_hist.append(rx_spd)
    def spd(v: float) -> str:
        return f"{human(v)}/s" if has_delta else "    --"

    t = Text()
    t.append("  ↑ Enviado     ", "bold green"); t.append(f"{human(n.bytes_sent)}\n", "white")
    t.append("  ↓ Recibido    ", "bold cyan");  t.append(f"{human(n.bytes_recv)}\n", "white")
    t.append("\n  ↑ Velocidad   ", "green");     t.append(f"{spd(tx_spd)}\n", "bold yellow")
    t.append("                ", "dim white");   t.append(f"{sparkline(_tx_hist, 24)}\n", "green")
    t.append("  ↓ Velocidad   ", "cyan");        t.append(f"{spd(rx_spd)}\n", "bold yellow")
    t.append("                ", "dim white");   t.append(f"{sparkline(_rx_hist, 24)}\n", "cyan")
    err = sum(getattr(n, a, 0) for a in ("errin", "errout", "dropin", "dropout"))
    t.append("\n  Errores/drops ", "dim white"); t.append(str(err), "bold red" if err else "bold green")
    return Panel(t, title="[bold magenta] 🌐  Red [/]", border_style="magenta", padding=(0, 1))


def _procs() -> Panel:
    ICONS = {"running": "[green]●[/]", "sleeping": "[blue]●[/]", "idle": "[dim]●[/]", "zombie": "[red]☠[/]"}
    tbl = Table(box=box.SIMPLE, header_style="bold green", show_edge=False, padding=(0, 1))
    tbl.add_column("PID",     style="dim cyan",  width=7,  justify="right")
    tbl.add_column("Proceso", style="bold white", width=24)
    tbl.add_column("CPU %",   width=7,  justify="right")
    tbl.add_column("RAM %",   width=7,  justify="right")
    tbl.add_column("Estado",  width=14)
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            logger.debug("No se pudo leer proceso para CPU", exc_info=True)
    procs.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
    for p in procs[:12]:
        cpu = p.get("cpu_percent") or 0.0
        mem = p.get("memory_percent") or 0.0
        cs  = "bold red" if cpu > 30 else ("yellow" if cpu > 5 else "dim white")
        ms  = "bold red" if mem > 20 else ("yellow" if mem > 10 else "dim white")
        st  = p.get("status") or "?"
        tbl.add_row(str(p.get("pid", "?")), (p.get("name") or "?")[:24],
                    f"[{cs}]{cpu:.1f}[/]", f"[{ms}]{mem:.1f}[/]",
                    f"{ICONS.get(st, '⚪')} {st}")
    return Panel(tbl, title="[bold red] ⚙  Top Procesos — CPU [/]", border_style="red")


def build_renderable():
    try:
        up_secs = int(time.time() - psutil.boot_time())
        up = str(timedelta(seconds=up_secs))
    except Exception:
        logger.exception("No se pudo calcular uptime")
        up = "—"
    now = datetime.now().strftime("%H:%M:%S")
    header = Text()
    header.append(f"  {platform.node()}  ", "bold white")
    header.append(f"{platform.system()} {platform.release()}  ", "dim white")
    header.append(f"up {up}  ", "bold yellow")
    header.append(now, "bold green")
    return Group(
        Panel(header, border_style="green", padding=(0, 1)),
        Columns([_cpu(), _mem()], equal=True, expand=True),
        Columns([_disk(), _net()], equal=True, expand=True),
        _procs(),
    )


class SysGlitchView(VerticalScroll):
    DEFAULT_CSS = """
    SysGlitchView {
        width: 100%;
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(id="sg_view")

    def on_mount(self) -> None:
        # Primer sample para que cpu_percent tenga delta valido
        psutil.cpu_percent(percpu=True)
        self.set_interval(1.0, self.refresh_view)

    def refresh_view(self) -> None:
        if not is_view_active(self, "sysglitch"):
            return
        try:
            self.query_one("#sg_view", Static).update(build_renderable())
        except Exception:
            logger.exception("No se pudo actualizar SysGlitch")
