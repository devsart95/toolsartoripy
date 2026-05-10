"""NetWatch — Conexiones de red activas con proceso y resolucion de hostname."""
import logging
import socket
import threading
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.widgets import Static
from textual.app import ComposeResult
from textual.containers import VerticalScroll

from widgets.shared import is_view_active, net_connections, net_connections_error

logger = logging.getLogger(__name__)

_PRIVATE = ("10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.",
            "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.",
            "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
            "192.168.", "127.", "::1", "fe80", "0.0.0.0")

_hostname_cache: dict[str, str] = {}
_resolving: set[str] = set()
_pending_resolve: set[str] = set()
_cache_lock = threading.Lock()
MAX_RESOLVE_BATCH = 12


def _is_public(ip: str) -> bool:
    return not any(ip.startswith(p) for p in _PRIVATE)


def _resolve_async(ip: str) -> None:
    """Resuelve un IP en thread y guarda en cache. No bloqueante."""
    try:
        host = socket.gethostbyaddr(ip)[0]
        parts = host.split(".")
        result = ".".join(parts[-2:]) if len(parts) > 2 else host
    except (socket.herror, socket.gaierror, OSError):
        result = ip
    with _cache_lock:
        _hostname_cache[ip] = result
        _resolving.discard(ip)


def _take_pending_resolves(limit: int = MAX_RESOLVE_BATCH) -> list[str]:
    with _cache_lock:
        ips = sorted(_pending_resolve)[:limit]
        for ip in ips:
            _pending_resolve.discard(ip)
            _resolving.add(ip)
        return ips


def _resolve_pending_batch() -> None:
    for ip in _take_pending_resolves():
        _resolve_async(ip)


def _hostname(ip: str) -> str:
    """Lookup no bloqueante: agenda resolve en worker controlado."""
    with _cache_lock:
        if ip in _hostname_cache:
            return _hostname_cache[ip]
        if ip in _resolving:
            return "resolviendo…"
        _pending_resolve.add(ip)
    return "pendiente…"


def build_renderable():
    conns = net_connections()

    if not conns:
        detail = net_connections_error()
        text = "  Sin conexiones detectadas."
        if detail:
            text = f"  {detail}"
        return Panel(
            Text(text, "yellow"),
            title="[bold magenta] 🌐  NetWatch [/]", border_style="magenta",
        )

    established = [c for c in conns if c.status == "ESTABLISHED" and c.raddr]
    public_conns = [c for c in established if c.raddr and _is_public(c.raddr.ip)]
    local_conns  = [c for c in established if c.raddr and not _is_public(c.raddr.ip)]

    pub_tbl = Table(box=box.SIMPLE, header_style="bold magenta", show_edge=False, padding=(0, 1))
    pub_tbl.add_column("Proceso", width=22)
    pub_tbl.add_column("→ IP",    width=18, style="cyan")
    pub_tbl.add_column("Host",    width=24, style="dim cyan")
    pub_tbl.add_column("Puerto",  width=8,  justify="right")
    pub_tbl.add_column("Local",   width=10, justify="right", style="dim white")

    for c in sorted(public_conns, key=lambda x: x.raddr.ip if x.raddr else "")[:18]:
        ip   = c.raddr.ip if c.raddr else "?"
        host = _hostname(ip)
        pub_tbl.add_row(
            (c.name or "—")[:22],
            ip,
            host if host != ip else "—",
            str(c.raddr.port) if c.raddr else "?",
            str(c.laddr.port) if c.laddr else "?",
        )

    loc_tbl = Table(box=box.SIMPLE, header_style="bold blue", show_edge=False, padding=(0, 1))
    loc_tbl.add_column("Proceso",  width=22)
    loc_tbl.add_column("↔ Local",  width=22, style="blue")
    loc_tbl.add_column("Puerto L", width=9,  justify="right", style="dim white")
    loc_tbl.add_column("Puerto R", width=9,  justify="right", style="dim cyan")

    for c in sorted(local_conns, key=lambda x: x.laddr.port if x.laddr else 0)[:12]:
        loc_tbl.add_row(
            (c.name or "—")[:22],
            c.raddr.ip if c.raddr else "—",
            str(c.laddr.port) if c.laddr else "?",
            str(c.raddr.port) if c.raddr else "?",
        )

    summary = Text()
    summary.append("  Internet: ", "bold magenta");      summary.append(f"{len(public_conns)}  ", "white")
    summary.append("Local: ", "bold blue");              summary.append(f"{len(local_conns)}  ", "white")
    summary.append("Total ESTABLISHED: ", "dim white");  summary.append(str(len(established)), "bold white")

    parts = [Panel(summary, border_style="magenta", padding=(0, 1))]
    if public_conns:
        parts.append(Panel(pub_tbl, title="[bold magenta] 🌍  Conexiones a Internet [/]", border_style="magenta"))
    if local_conns:
        parts.append(Panel(loc_tbl, title="[bold blue] 🏠  Conexiones Locales [/]", border_style="blue"))

    return Group(*parts)


class NetWatchView(VerticalScroll):
    DEFAULT_CSS = """
    NetWatchView {
        width: 100%;
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(id="nw_view")

    def on_mount(self) -> None:
        self.set_interval(3, self.refresh_view)

    def refresh_view(self) -> None:
        if not is_view_active(self, "netwatch"):
            return
        try:
            self.query_one("#nw_view", Static).update(build_renderable())
            self.run_worker(_resolve_pending_batch, exclusive=True, thread=True)
        except Exception:
            logger.exception("No se pudo actualizar NetWatch")
