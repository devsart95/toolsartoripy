# toolsartoripy

> A collection of interactive terminal tools for macOS, built with Python + Textual + Rich.

```
⚡ DevTools
├── ⚡ SysGlitch    Monitor sistema
├── 🔌 PortScan     Puertos activos
├── 🎯 GitRadar     Repos Devsar
├── 🐳 Docker       Contenedores
├── 🔥 DiskHeat     Uso de disco
├── 🌐 NetWatch     Conexiones red
├── 🔋 Battery      Salud batería
├── 📡 WifiMap      Redes WiFi
├── 📋 ClipHistory  Historial clipboard
└── 📄 LogTail      Logs del sistema
```

---

## Requirements

- macOS (Apple Silicon or Intel)
- Python 3.11+

## Install & run

```bash
git clone https://github.com/devsart95/toolsartoripy
cd toolsartoripy
pip install -r requirements.txt
python app.py
```

## Navigation

| Key | Action |
|-----|--------|
| `↑ ↓` or click | Navigate sidebar |
| `1` – `0` | Jump to tool directly |
| `r` | Refresh current view |
| `q` | Quit |

---

## Tools

### ⚡ SysGlitch
Real-time system monitor. CPU per-core (2-column layout), RAM + top memory processes, disk usage (filters macOS APFS internal volumes), network I/O with live speed, top 12 processes by CPU. Updates every second.

### 🔌 PortScan
All active ports and connections without `sudo`. Uses `lsof -i -n -P` directly — shows listening ports, established connections, process names, and states with color coding.

### 🎯 GitRadar
Dashboard of all git repos under `~/Devsar/`. Shows current branch, dirty file count, ahead/behind origin, and last commit message + relative time. Git ops run in a background worker so the UI never blocks.

### 🐳 DockerGlitch
Live Docker container monitor via `docker ps` + `docker stats`. Shows CPU%, RAM usage, state, ports, and uptime per container. Skips stats polling if no containers are running.

### 🔥 DiskHeat
Largest directories under `~/Devsar`, `~/Downloads`, and `~/Desktop` with proportional bar charts. Detects heavy caches (`node_modules`, `.next`, Docker volumes) and shows estimated recoverable space.

### 🌐 NetWatch
Active network connections split into Internet (public IPs) and Local. Background DNS resolution — shows `resolviendo…` while looking up, replaces with hostname when done. No blocking.

### 🔋 BatteryLog
macOS battery health via `ioreg`. Reads cycle count, max/design capacity, voltage, temperature, and charging state. Handles macOS 13+ API changes (capacity reported as percentage). Includes degradation diagnosis.

### 📡 WifiMap
Nearby WiFi networks. Uses the legacy `airport` binary if present; falls back to `system_profiler SPAirPortDataType -json` on macOS 14.4+ (where `airport` was removed). Shows signal strength bars, channel, and security.

### 📋 ClipHistory
In-session clipboard history (up to 50 entries). Polls `pbpaste` every second, detects content type (URL, code, number, text), shows byte size and elapsed time. Does not persist between sessions.

### 📄 LogTail
System log viewer. Tails `/var/log/system.log`, queries the unified log for recent errors via `log show`, and lists crash reports from `~/Library/Logs/DiagnosticReports`. Some logs require Full Disk Access in System Settings.

---

## Stack

| Layer | Library |
|-------|---------|
| TUI framework | [Textual](https://github.com/Textualize/textual) |
| Rich rendering | [Rich](https://github.com/Textualize/rich) |
| System metrics | [psutil](https://github.com/giampaolo/psutil) |
| Network info | `lsof` (built-in macOS) |
| Battery / WiFi | `ioreg`, `system_profiler` (built-in macOS) |

## Architecture

```
app.py                  ← Textual App, sidebar, ContentSwitcher
screens/
├── sysglitch.py        ← VerticalScroll widget + psutil panels
├── portscanner.py
├── gitradar.py         ← background worker for git subprocess calls
├── dockerglitch.py     ← background worker for docker commands
├── diskheat.py         ← background worker for os.walk
├── netwatch.py         ← async DNS resolution via daemon threads
├── batterylog.py
├── wifimap.py          ← background worker for system_profiler
├── cliphistory.py      ← polling + threading.Lock for history
└── logtail.py          ← background worker for `log show`
widgets/
└── shared.py           ← pct_bar(), human(), net_connections(), is_view_active()
```

Each tool is a `VerticalScroll` widget (not a Textual `Screen`), which lets them live inside a `ContentSwitcher`. Slow I/O (git, docker, disk walk, log show) runs in `run_worker(thread=True)` and calls back via `app.call_from_thread()`.

---

## Notes

- `PortScan` and `NetWatch` use `lsof` instead of `psutil.net_connections()` — the latter requires `sudo` on macOS.
- `WifiMap` falls back to `system_profiler` since the `airport` binary was removed in macOS 14.4.
- `BatteryLog` handles the macOS 13+ change where `AppleRawMaxCapacity` was replaced and `Amperage` is returned as unsigned int64.
- `DiskHeat` skips `node_modules`, `.next`, `.venv`, and other known cache dirs during size calculation to avoid runaway scans.

## License

MIT
