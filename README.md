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
All active ports and connections without `sudo`. Uses `lsof -i -n -P` directly — shows listening ports, established connections, other connection states, process names, and states with color coding. Permission, missing-command, and timeout errors are shown in the view.

### 🎯 GitRadar
Dashboard of all git repos under `~/Devsar/`. Shows current branch, dirty file count, ahead/behind origin, and last commit message + relative time. Git ops run in a background worker so the UI never blocks. If `git status` fails or times out, the repo is marked as an error instead of clean.

### 🐳 DockerGlitch
Live Docker container monitor via `docker ps` + `docker stats`. Shows CPU%, RAM usage, state, image, and ports per container. Skips stats polling if no containers are running and reports Docker command, permission, and timeout errors in the view.

### 🔥 DiskHeat
Largest directories under `~/Devsar`, `~/Downloads`, and `~/Desktop` with proportional bar charts. Detects heavy development caches (`node_modules`, `.next`) and shows estimated recoverable space.

### 🌐 NetWatch
Active network connections split into Internet (public IPs) and Local. DNS resolution runs through a bounded background worker — shows `pendiente…` or `resolviendo…` while looking up, then replaces with hostname when done. Permission, missing-command, and timeout errors from `lsof` are shown in the view.

### 🔋 BatteryLog
macOS battery health via `ioreg`. Reads cycle count, max/design capacity, voltage, temperature, and charging state. Handles macOS 13+ API changes (capacity reported as percentage). Includes degradation diagnosis.

### 📡 WifiMap
Nearby WiFi networks. Uses the legacy `airport` binary if present; falls back to `system_profiler SPAirPortDataType -json` on macOS 14.4+ (where `airport` was removed). Parses legacy `airport` output without breaking SSIDs that contain spaces. Shows signal strength bars, channel, and security.

### 📋 ClipHistory
Opt-in in-session clipboard history (up to 50 entries). Clipboard capture starts disabled, can be toggled off again, and can be cleared from the UI. Reads `pbpaste` through a controlled worker, detects content type (URL, code, number, text), shows byte size and elapsed time, and automatically redacts common API key, token, secret, and password patterns before storing entries. Does not persist between sessions.

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
├── netwatch.py         ← bounded background worker for DNS resolution
├── batterylog.py
├── wifimap.py          ← background worker for system_profiler
├── cliphistory.py      ← opt-in clipboard polling worker + redaction
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
