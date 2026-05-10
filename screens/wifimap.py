"""WifiMap — Redes WiFi cercanas (macOS).

En macOS 14.4+ el binario `airport` fue removido, asi que dependemos de
`system_profiler SPAirPortDataType -json`. Devuelve la red actual + las redes
locales cacheadas. Para escaneo activo se requiere `wdutil` con sudo.
"""
import json
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

AIRPORT = Path("/System/Library/PrivateFrameworks/Apple80211.framework"
               "/Versions/Current/Resources/airport")


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
    if not AIRPORT.exists():
        return []
    try:
        r = subprocess.run([str(AIRPORT), "-s"], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return []
        networks = []
        for line in r.stdout.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) < 3:
                continue
            try:
                rssi = int(parts[2])
                networks.append({
                    "ssid":     parts[0],
                    "bssid":    parts[1],
                    "rssi":     rssi,
                    "channel":  parts[3] if len(parts) > 3 else "?",
                    "security": " ".join(parts[6:]) if len(parts) > 6 else "?",
                })
            except (ValueError, IndexError):
                continue
        return sorted(networks, key=lambda x: x["rssi"], reverse=True)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def _scan_system_profiler() -> tuple[list[dict], dict]:
    """Fallback moderno: system_profiler SPAirPortDataType -json.

    Returns (networks, current_info).
    """
    try:
        r = subprocess.run(
            ["system_profiler", "-json", "SPAirPortDataType"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return [], {}
        data = json.loads(r.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
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
    networks = _scan_airport()
    current: dict = {}

    if not networks:
        networks, current = _scan_system_profiler()

    if not networks:
        msg = Text()
        msg.append("  No se pudo escanear redes WiFi.\n", "yellow")
        msg.append("  En macOS modernos puede requerir permiso de Localizacion.\n\n", "dim white")
        try:
            r = subprocess.run(
                ["networksetup", "-getinfo", "Wi-Fi"],
                capture_output=True, text=True, timeout=5,
            )
            if r.stdout:
                msg.append(r.stdout, "dim white")
        except Exception:
            msg.append("  No se pudo obtener info de red.", "dim red")
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
            pass
