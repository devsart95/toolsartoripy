"""Helpers compartidos entre todas las vistas."""
import logging
import re
import subprocess
from typing import NamedTuple

from rich.text import Text
from textual.widget import Widget
from textual.widgets import ContentSwitcher

logger = logging.getLogger(__name__)
_net_connections_error = ""


# ── conexiones de red sin sudo ────────────────────────────────────────────────

class _Addr(NamedTuple):
    ip:   str
    port: int


class _Conn:
    __slots__ = ("laddr", "name", "pid", "raddr", "status")

    def __init__(self, laddr: _Addr | None, raddr: _Addr | None,
                 status: str, pid: int | None, name: str = ""):
        self.laddr  = laddr
        self.raddr  = raddr
        self.status = status
        self.pid    = pid
        self.name   = name   # comando (COMMAND column de lsof)


def _parse_addr(s: str) -> _Addr | None:
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
    global _net_connections_error
    _net_connections_error = ""
    try:
        r = subprocess.run(
            ["lsof", "-i", "-n", "-P"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            stderr = (r.stderr or "").strip()
            _net_connections_error = stderr or f"lsof fallo con codigo {r.returncode}"
            logger.warning("lsof failed: %s", _net_connections_error)
            return []
        conns: list[_Conn] = []
        for line in r.stdout.splitlines()[1:]:   # skip header
            parts = line.split()
            if len(parts) < 9:
                continue
            cmd = parts[0]
            try:
                pid: int | None = int(parts[1])
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
    except FileNotFoundError:
        _net_connections_error = "comando no disponible: lsof"
        logger.warning(_net_connections_error)
        return []
    except subprocess.TimeoutExpired:
        _net_connections_error = "timeout ejecutando lsof"
        logger.warning(_net_connections_error)
        return []
    except PermissionError:
        _net_connections_error = "sin permisos para ejecutar lsof"
        logger.warning(_net_connections_error)
        return []
    except Exception:
        _net_connections_error = "error inesperado ejecutando lsof"
        logger.exception(_net_connections_error)
        return []


def net_connections_error() -> str:
    return _net_connections_error


_SPARK_BLOCKS = "▁▂▃▄▅▆▇█"


def pct_style(val: float) -> str:
    """Estilo Rich segun carga porcentual — criterio unico de toda la app."""
    val = float(val or 0)
    return "bold red" if val >= 80 else ("yellow" if val >= 55 else "bold green")


def pct_bar(val: float, w: int = 26) -> Text:
    val    = max(0.0, min(100.0, float(val or 0)))
    filled = round(val / 100 * w)
    color  = pct_style(val)
    t = Text()
    t.append("█" * filled,       style=color)
    t.append("░" * (w - filled), style="dim white")
    t.append(f" {val:5.1f}%",    style=color)
    return t


def sparkline(data, w: int = 24, lo: float | None = None,
              hi: float | None = None) -> str:
    """Historial como bloques Unicode.

    lo/hi fijan la escala (0-100 para porcentajes). Sin ellos la escala es
    dinamica al min/max de la ventana — util para tasas, enganoso para
    porcentajes casi planos, que se veria como una montana de ruido.
    """
    pts = list(data)[-w:]
    if not pts:
        return " " * w
    bottom = min(pts) if lo is None else lo
    top    = max(pts) if hi is None else hi
    rng    = (top - bottom) or 1.0
    out = []
    for v in pts:
        norm = (float(v) - bottom) / rng
        idx  = int(max(0.0, min(1.0, norm)) * (len(_SPARK_BLOCKS) - 1))
        out.append(_SPARK_BLOCKS[idx])
    return "".join(out).rjust(w)


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
        logger.debug("No se pudo detectar vista activa; se asume activa", exc_info=True)
        # Antes de mount o si no esta en un switcher: tratar como activo
        return True
