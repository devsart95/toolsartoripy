"""Helpers compartidos entre todas las vistas."""
import re
import subprocess
from typing import Optional, NamedTuple

from rich.text import Text
from textual.widget import Widget
from textual.widgets import ContentSwitcher


# ── conexiones de red sin sudo ────────────────────────────────────────────────

class _Addr(NamedTuple):
    ip:   str
    port: int


class _Conn:
    __slots__ = ("laddr", "raddr", "status", "pid", "name")

    def __init__(self, laddr: Optional[_Addr], raddr: Optional[_Addr],
                 status: str, pid: Optional[int], name: str = ""):
        self.laddr  = laddr
        self.raddr  = raddr
        self.status = status
        self.pid    = pid
        self.name   = name   # comando (COMMAND column de lsof)


def _parse_addr(s: str) -> Optional[_Addr]:
    s = s.strip()
    if not s or s == "*":
        return None
    if s.startswith("["):                    # IPv6 [::1]:port
        m = re.match(r'\[(.+)\]:(\d+)', s)
        if m:
            return _Addr(ip=m.group(1), port=int(m.group(2)))
        return None
    if ":" in s:                             # IPv4 host:port o *:port
        host, _, port_str = s.rpartition(":")
        if port_str.isdigit():
            return _Addr(ip=host if host and host != "*" else "0.0.0.0",
                         port=int(port_str))
    return None


def net_connections() -> list[_Conn]:
    """Conexiones inet via `lsof -i -n -P` — no requiere sudo.

    Devuelve objetos compatibles con la interfaz de psutil connections:
    .laddr, .raddr, .status, .pid, .name
    """
    try:
        r = subprocess.run(
            ["lsof", "-i", "-n", "-P"],
            capture_output=True, text=True, timeout=10,
        )
        conns: list[_Conn] = []
        for line in r.stdout.splitlines()[1:]:   # skip header
            parts = line.split()
            if len(parts) < 9:
                continue
            cmd = parts[0]
            try:
                pid: Optional[int] = int(parts[1])
            except ValueError:
                pid = None

            name_full = " ".join(parts[8:])      # NAME puede tener espacios

            state_m = re.search(r'\((\w+)\)\s*$', name_full)
            state   = state_m.group(1) if state_m else ""
            addr_s  = name_full[:state_m.start()].strip() if state_m else name_full.strip()

            laddr = raddr = None
            if "->" in addr_s:
                local, _, remote = addr_s.partition("->")
                laddr = _parse_addr(local)
                raddr = _parse_addr(remote)
            else:
                laddr = _parse_addr(addr_s)

            if laddr is not None:
                conns.append(_Conn(laddr=laddr, raddr=raddr,
                                   status=state, pid=pid, name=cmd))
        return conns
    except Exception:
        return []


def pct_bar(val: float, w: int = 26) -> Text:
    val    = max(0.0, min(100.0, float(val or 0)))
    filled = round(val / 100 * w)
    color  = "bold red" if val >= 80 else ("yellow" if val >= 55 else "bold green")
    t = Text()
    t.append("█" * filled,       style=color)
    t.append("░" * (w - filled), style="dim white")
    t.append(f" {val:5.1f}%",    style=color)
    return t


def human(n: float) -> str:
    n = float(n or 0)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024.0:
            return f"{n:6.1f} {u}"
        n /= 1024.0
    return f"{n:.1f} PB"


def ago(seconds: float) -> str:
    """Convierte segundos a string legible: '3m', '2h', '5d'."""
    s = int(max(0, seconds))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m"
    if s < 86400:
        return f"{s // 3600}h"
    return f"{s // 86400}d"


def is_view_active(widget: Widget, view_id: str) -> bool:
    """True si el ContentSwitcher esta mostrando esta vista."""
    try:
        sw = widget.app.query_one("#switcher", ContentSwitcher)
        return sw.current == view_id
    except Exception:
        # Antes de mount o si no esta en un switcher: tratar como activo
        return True
