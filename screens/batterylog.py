"""BatteryLog — Salud de bateria (macOS via ioreg)."""
import logging
import subprocess
import re

from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static
from textual.app import ComposeResult
from textual.containers import VerticalScroll

from widgets.shared import pct_bar, is_view_active

logger = logging.getLogger(__name__)
_last_battery_error = ""


def _ioreg() -> dict[str, str]:
    global _last_battery_error
    _last_battery_error = ""
    try:
        r = subprocess.run(
            ["ioreg", "-l", "-n", "AppleSmartBattery", "-r"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            _last_battery_error = (r.stderr or "").strip() or f"ioreg fallo con codigo {r.returncode}"
            logger.warning("ioreg failed: %s", _last_battery_error)
            return {}
        # Solo lineas tipo: "Key" = value (single-line value, sin braces)
        result: dict[str, str] = {}
        for line in r.stdout.splitlines():
            m = re.match(r'\s*"(\w+)"\s*=\s*([^\s{(<].*?)$', line)
            if m:
                result[m.group(1)] = m.group(2).strip()
        return result
    except FileNotFoundError:
        _last_battery_error = "comando no disponible: ioreg"
        logger.warning(_last_battery_error)
        return {}
    except subprocess.TimeoutExpired:
        _last_battery_error = "timeout consultando bateria"
        logger.warning(_last_battery_error)
        return {}
    except PermissionError:
        _last_battery_error = "sin permisos para consultar bateria"
        logger.warning(_last_battery_error)
        return {}
    except Exception:
        _last_battery_error = "error inesperado consultando bateria"
        logger.exception(_last_battery_error)
        return {}


def _to_signed64(n: int) -> int:
    """ioreg vuelca int64 negativos como uint64 enormes — convertir."""
    if n >= 2**63:
        return n - 2**64
    return n


def build_renderable():
    d = _ioreg()
    if not d:
        detail = f"\n  {_last_battery_error}" if _last_battery_error else ""
        return Panel(
            Text("  No se pudo leer informacion de bateria.\n  Solo disponible en MacBooks."
                 f"{detail}", "yellow"),
            title="[bold yellow] 🔋  BatteryLog [/]", border_style="yellow",
        )

    def iv(key: str, default: int = 0) -> int:
        try:
            return int(d.get(key, default))
        except (ValueError, TypeError):
            return default

    def bv(key: str) -> bool:
        return d.get(key, "No") == "Yes"

    # Capacidades: AppleRawCurrentCapacity es la actual en mAh.
    # AppleRawMaxCapacity puede no existir en macOS modernos.
    # NominalChargeCapacity es la max real actual en mAh.
    # MaxCapacity al top-level es % de salud.
    capacity_now    = iv("AppleRawCurrentCapacity")
    capacity_max    = iv("AppleRawMaxCapacity") or iv("NominalChargeCapacity")
    capacity_design = iv("DesignCapacity")
    voltage         = iv("Voltage")          # mV
    amperage        = _to_signed64(iv("Amperage"))  # mA, signed
    cycle_count     = iv("CycleCount")
    temperature     = iv("Temperature")      # centesimas de grado

    is_charging   = bv("IsCharging")
    is_charged    = bv("FullyCharged")
    plugged_in    = bv("ExternalConnected")

    # Salud: si tenemos AppleRawMax usamos eso; si no, MaxCapacity (que en macOS modernos ya es %).
    if iv("AppleRawMaxCapacity") and capacity_design:
        health_pct = capacity_max / capacity_design * 100
    else:
        # MaxCapacity en macOS modernos es directamente el % de salud
        mc = iv("MaxCapacity")
        if 0 < mc <= 100:
            health_pct = float(mc)
        elif capacity_max and capacity_design:
            health_pct = capacity_max / capacity_design * 100
        else:
            health_pct = 0.0

    charge_pct = (capacity_now / capacity_max * 100) if capacity_max else 0.0
    charge_pct = max(0.0, min(100.0, charge_pct))
    health_pct = max(0.0, min(100.0, health_pct))

    temp_c = temperature / 100 if temperature else 0.0
    watts  = abs(voltage * amperage) / 1_000_000 if voltage and amperage else 0.0

    t = Text()
    t.append("  Carga actual   ", "bold cyan"); t.append_text(pct_bar(charge_pct, 28))
    if is_charging:
        t.append(f"  ⚡ Cargando  {watts:.1f}W", "bold green")
    elif is_charged:
        t.append("  ✓ Cargado", "bold green")
    elif plugged_in:
        t.append("  ⚡ Enchufado (sin cargar)", "yellow")
    else:
        t.append(f"  🔋 Descargando  {watts:.1f}W", "bold yellow")

    t.append("\n\n  Salud         ", "bold cyan"); t.append_text(pct_bar(health_pct, 28))

    t.append("\n\n")
    cap_value = (
        f"{capacity_max} mAh  /  {capacity_design} mAh diseno"
        if capacity_max and capacity_design
        else (f"{capacity_design} mAh diseno" if capacity_design else "—")
    )
    rows = [
        ("Ciclos",           f"{cycle_count}  (max recomendado ~1000)"),
        ("Capacidad actual", cap_value),
        ("Voltaje",          f"{voltage / 1000:.2f} V" if voltage else "—"),
        ("Temperatura",      f"{temp_c:.1f} °C" if temperature else "—"),
    ]
    for label, value in rows:
        t.append(f"  {label:<20} ", "dim white")
        if "Ciclos" in label and cycle_count > 800:
            t.append(value + "\n", "bold red")
        elif "Temperatura" in label and temp_c > 40:
            t.append(value + "\n", "bold red")
        else:
            t.append(value + "\n", "white")

    t.append("\n  Diagnostico:  ", "dim white")
    if health_pct >= 90:
        t.append("Bateria en excelente estado ✓", "bold green")
    elif health_pct >= 80:
        t.append("Bateria en buen estado", "green")
    elif health_pct >= 70:
        t.append("Bateria con desgaste moderado — considerar reemplazo", "yellow")
    elif health_pct > 0:
        t.append("⚠ Bateria con desgaste significativo — reemplazar pronto", "bold red")
    else:
        t.append("Sin datos de salud disponibles", "dim white")

    return Panel(t, title="[bold yellow] 🔋  BatteryLog [/]", border_style="yellow", padding=(0, 1))


class BatteryLogView(VerticalScroll):
    DEFAULT_CSS = """
    BatteryLogView {
        width: 100%;
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(id="bl_view")

    def on_mount(self) -> None:
        self.set_interval(10, self.refresh_view)
        self.call_after_refresh(self.refresh_view)

    def refresh_view(self) -> None:
        if not is_view_active(self, "batterylog"):
            return
        try:
            self.query_one("#bl_view", Static).update(build_renderable())
        except Exception:
            logger.exception("No se pudo actualizar BatteryLog")
