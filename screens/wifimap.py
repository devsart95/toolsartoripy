"""WifiMap — Redes WiFi cercanas (macOS).

En macOS 14.4+ el binario `airport` fue removido, asi que dependemos de
`system_profiler SPAirPortDataType -json`. Devuelve la red actual + las redes
locales cacheadas. Para escaneo activo se requiere `wdutil` con sudo.
"""
import json
import logging
import re
import subprocess
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
AIRPORT = Path("/System/Library/PrivateFrameworks/Apple80211.framework"
               "/Versions/Current/Resources/airport")
_last_scan_error = ""


def _signal_bar(rssi: int, w: int = 16) -> Text:
    pct = max(0, min(100, (rssi + 90) * 100 // 60))
    filled = round(pct / 100 * w)
    color  = "bold green" if pct > 66 else ("yellow" if pct > 33 else "bold red")
    t = Text()
    t.append("█" * filled,       style=color)
    t.append("░" * (w - filled), style="dim white")
    t.append(f" {rssi} dBm", style=color)
    return t


def _parse_signal_noise(s: str) -> int:
    """Extrae RSSI de '-41 dBm / -97 dBm' → -41."""
    m = re.search(r"(-?\d+)\s*dBm", s or "")
    return int(m.group(1)) if m else -100


def _parse_channel(s: str) -> str:
    """De '1 (2GHz, 20MHz)' → '1'."""
    if not s:
        return "?"
    m = re.match(r"\s*(\d+)", s)
    return m.group(1) if m else "?"


def _security_label(raw: str) -> str:
    """De 'spairport_security_mode_wpa2_personal' → 'WPA2'."""
    if not raw:
        return "?"
    raw = raw.replace("spairport_security_mode_", "")
    mapping = {
        "none": "Open",
        "wpa_personal": "WPA",
        "wpa2_personal": "WPA2",
        "wpa3_personal": "WPA3",
        "wpa3_transition": "WPA2/3",
        "wpa2_personal_mixed": "WPA/2",
    }
    return mapping.get(raw, raw[:14])


def _scan_airport() -> list[dict]:
    """Legacy airport binary — solo macOS < 14.4."""
    global _last_scan_error
    if not AIRPORT.exists():
        return []
    try:
        r = subprocess.run([str(AIRPORT), "-s"], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            _last_scan_error = (r.stderr or "").strip() or f"airport fallo con codigo {r.returncode}"
            logger.warning("airport scan failed: %s", _last_scan_error)
            return []
        networks = []
        lines = r.stdout.splitlines()
        if not lines:
            return []
        header = lines[0]
        bssid_at = header.find("BSSID")
        rssi_at = header.find("RSSI")
        channel_at = header.find("CHANNEL")
        ht_at = header.find("HT")
        cc_at = header.find("CC")
        security_at = header.find("SECURITY")
        if min(bssid_at, rssi_at, channel_at, security_at) < 0:
            _last_scan_error = "formato inesperado de airport -s"
            logger.warning(_last_scan_error)
            return []
        for line in lines[1:]:
            try:
                ssid = line[:bssid_at].strip()
                bssid = line[bssid_at:rssi_at].strip()
                rssi = int(line[rssi_at:channel_at].strip())
                channel = line[channel_at:ht_at].strip() if ht_at > channel_at else "?"
                security = line[security_at:].strip() if security_at >= 0 else "?"
                networks.append({
                    "ssid":     ssid,
                    "bssid":    bssid,
                    "rssi":     rssi,
                    "channel":  channel or "?",
                    "security": security or "?",
                })
            except (ValueError, IndexError):
                logger.warning("No se pudo parsear red WiFi: %s", line)
                continue
        return sorted(networks, key=lambda x: x["rssi"], reverse=True)
    except FileNotFoundError:
        _last_scan_error = "comando no disponible: airport"
        logger.warning(_last_scan_error)
        return []
    except subprocess.TimeoutExpired:
        _last_scan_error = "timeout escaneando WiFi con airport"
        logger.warning(_last_scan_error)
        return []
    except PermissionError:
        _last_scan_error = "sin permisos para escanear WiFi con airport"
        logger.warning(_last_scan_error)
        return []


def _scan_system_profiler() -> tuple[list[dict], dict]:
    """Fallback moderno: system_profiler SPAirPortDataType -json.

    Returns (networks, current_info).
    """
    global _last_scan_error
    try:
        r = subprocess.run(
            ["system_profiler", "-json", "SPAirPortDataType"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            _last_scan_error = (r.stderr or "").strip() or f"system_profiler fallo con codigo {r.returncode}"
            logger.warning("system_profiler WiFi scan failed: %s", _last_scan_error)
            return [], {}
        data = json.loads(r.stdout)
    except FileNotFoundError:
        _last_scan_error = "comando no disponible: system_profiler"
        logger.warning(_last_scan_error)
        return [], {}
    except subprocess.TimeoutExpired:
        _last_scan_error = "timeout escaneando WiFi con system_profiler"
        logger.warning(_last_scan_error)
        return [], {}
    except json.JSONDecodeError:
        _last_scan_error = "salida invalida de system_profiler"
        logger.warning(_last_scan_error)
        return [], {}
    except PermissionError:
        _last_scan_error = "sin permisos para escanear WiFi"
        logger.warning(_last_scan_error)
        return [], {}

    interfaces = []
    for entry in data.get("SPAirPortDataType", []):
        interfaces.extend(entry.get("spairport_airport_interfaces", []))

    networks: list[dict] = []
    current: dict = {}

    for iface in interfaces:
        cur = iface.get("spairport_current_network_information") or {}
        if cur:
            current = {
                "ssid":     cur.get("_name", ""),
                "rssi":     _parse_signal_noise(cur.get("spairport_signal_noise", "")),
                "channel":  _parse_channel(cur.get("spairport_network_channel", "")),
                "security": _security_label(cur.get("spairport_security_mode", "")),
                "phy":      cur.get("spairport_network_phymode", ""),
            }
            networks.append({
                "ssid":     current["ssid"],
                "bssid":    "—",
                "rssi":     current["rssi"],
                "channel":  current["channel"],
                "security": current["security"],
            })

        for net in iface.get("spairport_airport_other_local_wireless_networks", []) or []:
            networks.append({
                "ssid":     net.get("_name", "?"),
                "bssid":    "—",
                "rssi":     _parse_signal_noise(net.get("spairport_signal_noise", "")),
                "channel":  _parse_channel(net.get("spairport_network_channel", "")),
                "security": _security_label(net.get("spairport_security_mode", "")),
            })

    # Deduplicar por SSID, quedarse con el mejor RSSI
    by_ssid: dict[str, dict] = {}
    for n in networks:
        ssid = n["ssid"]
        if not ssid:
            continue
        if ssid not in by_ssid or n["rssi"] > by_ssid[ssid]["rssi"]:
            by_ssid[ssid] = n

    sorted_nets = sorted(by_ssid.values(), key=lambda x: x["rssi"], reverse=True)
    return sorted_nets, current


def build_renderable():
    global _last_scan_error
    _last_scan_error = ""
    networks = _scan_airport()
    current: dict = {}

    if not networks:
        networks, current = _scan_system_profiler()

    if not networks:
        msg = Text()
        msg.append("  No se pudo escanear redes WiFi.\n", "yellow")
        if _last_scan_error:
            msg.append(f"  {_last_scan_error}\n", "bold red")
        msg.append("  En macOS modernos puede requerir permiso de Localizacion.\n\n", "dim white")
        try:
            r = subprocess.run(
                ["networksetup", "-getinfo", "Wi-Fi"],
                capture_output=True, text=True, timeout=5,
            )
            if r.stdout:
                msg.append(r.stdout, "dim white")
        except FileNotFoundError:
            msg.append("  comando no disponible: networksetup", "dim red")
            logger.warning("networksetup no disponible")
        except subprocess.TimeoutExpired:
            msg.append("  timeout consultando networksetup", "dim red")
            logger.warning("timeout consultando networksetup")
        except PermissionError:
            msg.append("  sin permisos para consultar networksetup", "dim red")
            logger.warning("sin permisos para consultar networksetup")
        except Exception:
            msg.append("  No se pudo obtener info de red.", "dim red")
            logger.exception("No se pudo obtener info de red")
        return Panel(msg, title="[bold cyan] 📡  WifiMap [/]", border_style="cyan")

    cur_ssid = current.get("ssid", "") if current else ""

    tbl = Table(box=box.SIMPLE, header_style="bold cyan", show_edge=False, padding=(0, 1))
    tbl.add_column("SSID",      width=30)
    tbl.add_column("Senal",     width=24)
    tbl.add_column("Canal",     width=8,  justify="center", style="dim cyan")
    tbl.add_column("Seguridad", width=12, style="dim white")

    for net in networks[:25]:
        ssid     = (net.get("ssid") or "?")[:30]
        is_cur   = bool(cur_ssid) and ssid == cur_ssid
        name_txt = Text()
        if is_cur:
            name_txt.append("▶ ", "bold green")
            name_txt.append(ssid, "bold green")
        else:
            name_txt.append("  " + ssid, "white")

        tbl.add_row(
            name_txt,
            _signal_bar(net.get("rssi", -100)),
            str(net.get("channel", "?")),
            str(net.get("security", "?")),
        )

    summary = Text()
    summary.append(f"  {len(networks)} redes detectadas", "dim white")
    if cur_ssid:
        summary.append("   ·   Conectado a: ", "dim white")
        summary.append(cur_ssid, "bold green")
        if current.get("rssi"):
            summary.append(f"  ({current['rssi']} dBm)", "dim cyan")
        if current.get("phy"):
            summary.append(f"  · {current['phy']}", "dim cyan")

    return Group(
        Panel(summary, border_style="cyan", padding=(0, 1)),
        Panel(tbl, title="[bold cyan] 📡  WifiMap [/]", border_style="cyan"),
    )


class WifiMapView(VerticalScroll):
    DEFAULT_CSS = """
    WifiMapView {
        width: 100%;
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Escaneando WiFi…", id="wm_view")

    def on_mount(self) -> None:
        self.set_interval(15, self.refresh_view)
        self.call_after_refresh(self.refresh_view)

    def refresh_view(self) -> None:
        if not is_view_active(self, "wifimap"):
            return
        # system_profiler tarda varios segundos: a worker
        self.run_worker(self._build_async, exclusive=True, thread=True)

    def _build_async(self) -> None:
        rendered = build_renderable()
        self.app.call_from_thread(self._apply, rendered)

    def _apply(self, rendered) -> None:
        try:
            self.query_one("#wm_view", Static).update(rendered)
        except Exception:
            logger.exception("No se pudo actualizar WifiMap")
