<p align="center">
  <img src="https://img.shields.io/badge/macOS-000?logo=apple&logoColor=white&style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Python_3.11+-3776AB?logo=python&logoColor=white&style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Textual-FF6B6B?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge"/>
</p>

<h1 align="center">⚡ toolsartoripy</h1>
<p align="center"><b>10 herramientas TUI para macOS</b> — <i>todo en tu terminal, sin sudo</i></p>

<p align="center">
  <code>git clone https://github.com/devsart95/toolsartoripy</code><br>
  <code>cd toolsartoripy && pip install -r requirements.txt && python app.py</code>
</p>

---

## 🧰 Herramientas

|   | Tool | Descripción |
|---|------|-------------|
| ⚡ | **SysGlitch** | CPU, RAM, disco, red y procesos en vivo |
| 🔌 | **PortScan** | Puertos activos y conexiones sin sudo |
| 🎯 | **GitRadar** | Dashboard de repos en ~/Devsar |
| 🐳 | **DockerGlitch** | Contenedores Docker en tiempo real |
| 💾 | **DiskHeat** | Directorios pesados y caches recuperables |
| 🌐 | **NetWatch** | Conexiones de red + resolución DNS |
| 🔋 | **BatteryLog** | Salud de batería (ciclos, capacidad, °C) |
| 📡 | **WifiMap** | Redes WiFi cercanas y señal |
| 📋 | **ClipHistory** | Historial de clipboard (opt-in, seguro) |
| 📄 | **LogTail** | Logs del sistema y crash reports |

## ⌨️ Controles

| Tecla | Acción |
|-------|--------|
| `↑` `↓` | Navegar sidebar |
| `1` – `0` | Salto directo a tool |
| `r` | Refrescar vista actual |
| `q` | Salir |

## 📦 Stack

`Textual` · `Rich` · `psutil` · `lsof` · `ioreg` · `system_profiler`

> Tareas lentas (git, docker, disk walk) corren en `run_worker` — la UI nunca se congela.

---

## ⚠️ Notas

🔹 **PortScan / NetWatch** — usan `lsof` en vez de `psutil.net_connections()` (requeriría sudo en macOS)  
🔹 **WifiMap** — en macOS 14.4+ cae automáticamente a `system_profiler` (airport fue removido)  
🔹 **ClipHistory** — 🛡️ **desactivado por defecto**. Activación manual + redacción automática de API keys, tokens y passwords  
🔹 **BatteryLog** — maneja el cambio de API en macOS 13+  
🔹 Algunas herramientas requieren **Full Disk Access** o permisos de **Localización**

---

<p align="center">
  <sub>MIT © 2026 · hecho con ☕ por <a href="https://github.com/devsart95">@devsart95</a></sub>
</p>
