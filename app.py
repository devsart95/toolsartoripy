"""toolsartoripy — TUI DevTools para macOS."""
import logging
import sys
from pathlib import Path

# Asegurar que el directorio del proyecto este en el path
sys.path.insert(0, str(Path(__file__).parent))

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import (
    ContentSwitcher, Footer, Label, ListItem, ListView,
)
from textual.containers import Horizontal, Vertical

from screens.sysglitch    import SysGlitchView
from screens.portscanner  import PortScanView
from screens.gitradar     import GitRadarView
from screens.dockerglitch import DockerGlitchView
from screens.diskheat     import DiskHeatView
from screens.netwatch     import NetWatchView
from screens.batterylog   import BatteryLogView
from screens.wifimap      import WifiMapView
from screens.cliphistory  import ClipHistoryView
from screens.logtail      import LogTailView

logger = logging.getLogger(__name__)

TOOLS = [
    ("sysglitch",    "⚡", "SysGlitch",   "Monitor sistema"),
    ("portscanner",  "🔌", "PortScan",    "Puertos activos"),
    ("gitradar",     "🎯", "GitRadar",    "Repos Devsar"),
    ("dockerglitch", "🐳", "Docker",      "Contenedores"),
    ("diskheat",     "🔥", "DiskHeat",    "Uso de disco"),
    ("netwatch",     "🌐", "NetWatch",    "Conexiones red"),
    ("batterylog",   "🔋", "Battery",     "Salud bateria"),
    ("wifimap",      "📡", "WifiMap",     "Redes WiFi"),
    ("cliphistory",  "📋", "ClipHistory", "Historial clipboard"),
    ("logtail",      "📄", "LogTail",     "Logs del sistema"),
]

CSS = """
Screen {
    background: #0a0a0a;
}

#layout {
    height: 100%;
}

#sidebar {
    width: 22;
    background: #0d1a0d;
    border-right: solid #1e5e1e;
    padding: 1 0;
}

#logo {
    color: #00cc44;
    text-style: bold;
    padding: 0 2 1 2;
    border-bottom: solid #1e5e1e;
    margin-bottom: 1;
}

ListView {
    background: transparent;
    border: none;
    padding: 0;
}

ListItem {
    background: transparent;
    padding: 0 1;
    height: 3;
}

ListItem:hover {
    background: #1a3a1a;
}

ListItem.--highlight {
    background: #1e5e1e;
}

.tool-icon {
    width: 3;
    color: #44cc44;
}

.tool-name {
    color: #c0c0c0;
    text-style: bold;
}

.tool-desc {
    color: #666666;
}

#content {
    width: 1fr;
    background: #0a0a0a;
}

ContentSwitcher {
    width: 100%;
    height: 100%;
    background: #0a0a0a;
}

Footer {
    background: #0d1a0d;
    color: #44cc44;
}
"""


class ToolItem(ListItem):
    def __init__(self, tool_id: str, icon: str, name: str, desc: str) -> None:
        super().__init__(id=f"item_{tool_id}")
        self.tool_id = tool_id
        self._icon = icon
        self._name = name
        self._desc = desc

    def compose(self) -> ComposeResult:
        yield Label(f"{self._icon} {self._name}", classes="tool-name")
        yield Label(f"   {self._desc}", classes="tool-desc")


class DevToolsApp(App):
    CSS = CSS
    TITLE = "toolsartoripy"

    BINDINGS = [
        Binding("q",      "quit",          "Salir"),
        Binding("r",      "refresh",       "Refrescar"),
        Binding("1",      "goto('sysglitch')",    "SysGlitch",   show=False),
        Binding("2",      "goto('portscanner')",  "PortScan",    show=False),
        Binding("3",      "goto('gitradar')",     "GitRadar",    show=False),
        Binding("4",      "goto('dockerglitch')", "Docker",      show=False),
        Binding("5",      "goto('diskheat')",     "DiskHeat",    show=False),
        Binding("6",      "goto('netwatch')",     "NetWatch",    show=False),
        Binding("7",      "goto('batterylog')",   "Battery",     show=False),
        Binding("8",      "goto('wifimap')",      "WifiMap",     show=False),
        Binding("9",      "goto('cliphistory')",  "Clips",       show=False),
        Binding("0",      "goto('logtail')",      "Logs",        show=False),
    ]

    def compose(self) -> ComposeResult:
        with Horizontal(id="layout"):
            with Vertical(id="sidebar"):
                yield Label("⚡ DevTools", id="logo")
                yield ListView(
                    *[ToolItem(tid, icon, name, desc) for tid, icon, name, desc in TOOLS],
                    id="tool_list",
                )
            with Vertical(id="content"):
                with ContentSwitcher(initial="sysglitch", id="switcher"):
                    yield SysGlitchView(id="sysglitch")
                    yield PortScanView(id="portscanner")
                    yield GitRadarView(id="gitradar")
                    yield DockerGlitchView(id="dockerglitch")
                    yield DiskHeatView(id="diskheat")
                    yield NetWatchView(id="netwatch")
                    yield BatteryLogView(id="batterylog")
                    yield WifiMapView(id="wifimap")
                    yield ClipHistoryView(id="cliphistory")
                    yield LogTailView(id="logtail")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#tool_list", ListView).index = 0
        # Trigger inicial de la primera vista
        self.call_after_refresh(self._init_first)

    def _init_first(self) -> None:
        try:
            view = self.query_one("#sysglitch", SysGlitchView)
            view.refresh_view()
        except Exception:
            logger.exception("No se pudo inicializar SysGlitch")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, ToolItem):
            self._switch_to(item.tool_id)

    def action_goto(self, tool_id: str) -> None:
        self._switch_to(tool_id)
        # Seleccionar en sidebar tambien
        for i, (tid, *_) in enumerate(TOOLS):
            if tid == tool_id:
                self.query_one("#tool_list", ListView).index = i
                break

    def _switch_to(self, tool_id: str) -> None:
        sw = self.query_one("#switcher", ContentSwitcher)
        sw.current = tool_id
        # Refrescar la vista al cambiar
        try:
            view = self.query_one(f"#{tool_id}")
            if hasattr(view, "refresh_view"):
                view.refresh_view()
        except Exception:
            logger.exception("No se pudo refrescar la vista %s", tool_id)

    def action_refresh(self) -> None:
        current = self.query_one("#switcher", ContentSwitcher).current
        if not current:
            return
        try:
            widget = self.query_one(f"#{current}")
            if hasattr(widget, "refresh_view"):
                widget.refresh_view()
        except Exception:
            logger.exception("No se pudo refrescar la vista actual %s", current)


def main() -> None:
    app = DevToolsApp()
    app.run()


if __name__ == "__main__":
    main()
