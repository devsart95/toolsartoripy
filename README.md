<p align="center">
  <img src="https://raw.githubusercontent.com/devsart95/toolsartoripy/main/banner.svg" alt="toolsartoripy" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white&style=for-the-badge"/>
  <img src="https://img.shields.io/badge/macOS-14%2B-000000?logo=apple&logoColor=white&style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Textual-TUI-FF6B6B?logo=gnometerminal&logoColor=white&style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Rich-terminal-7C3AED?logo=python&logoColor=white&style=for-the-badge"/>
  <img src="https://img.shields.io/badge/psutil-system-06B6D4?logoColor=white&style=for-the-badge"/>
  <img src="https://img.shields.io/badge/license-MIT-22C55E?style=for-the-badge"/>
</p>

---

## Vista previa

<p align="center">
  <img src="https://raw.githubusercontent.com/devsart95/toolsartoripy/main/demo.svg" alt="toolsartoripy demo" width="100%">
</p>

---

## Instalación

```bash
git clone https://github.com/devsart95/toolsartoripy
cd toolsartoripy
pip install -r requirements.txt
python app.py
```

> Python 3.11+ requerido. Sin dependencias del sistema fuera de macOS nativo (`lsof`, `ioreg`, `system_profiler`).

---

## Herramientas

|   | Tool | Descripción |
|---|------|-------------|
| ⚡ | **SysGlitch** | CPU por core, RAM + procesos, disco, red en vivo |
| 🔌 | **PortScan** | Puertos activos y conexiones sin `sudo` |
| 🎯 | **GitRadar** | Dashboard de todos los repos en `~/Devsar` |
| 🐳 | **DockerGlitch** | Contenedores Docker en tiempo real |
| 💾 | **DiskHeat** | Directorios pesados y cachés recuperables |
| 🌐 | **NetWatch** | Conexiones de red + resolución DNS |
| 🔋 | **BatteryLog** | Salud de batería (ciclos, capacidad, temperatura) |
| 📡 | **WifiMap** | Redes WiFi cercanas con señal y canal |
| 📋 | **ClipHistory** | Historial de clipboard — opt-in, redacción automática |
| 📄 | **LogTail** | Logs del sistema y crash reports |

---

## Controles

| Tecla | Acción |
|-------|--------|
| `↑` `↓` | Navegar sidebar |
| `1` – `0` | Salto directo a herramienta |
| `r` | Refrescar vista actual |
| `q` | Salir |

---

## Stack

<p align="center">
  <img src="https://img.shields.io/badge/Textual-framework%20TUI-FF6B6B?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Rich-render%20terminal-7C3AED?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/psutil-métricas%20sistema-06B6D4?style=flat-square"/>
  <img src="https://img.shields.io/badge/lsof-red%20sin%20sudo-00CC44?style=flat-square"/>
  <img src="https://img.shields.io/badge/ioreg-batería%20macOS-FFAA00?style=flat-square"/>
  <img src="https://img.shields.io/badge/system__profiler-WiFi-CC44CC?style=flat-square"/>
</p>

> Las tareas lentas (git, docker, disk walk, DNS) corren en `run_worker` — la UI nunca se congela.

---

## Notas

🔹 **PortScan / NetWatch** — usan `lsof` en lugar de `psutil.net_connections()` (requeriría `sudo` en macOS)  
🔹 **WifiMap** — en macOS 14.4+ cae automáticamente a `system_profiler` (el binario `airport` fue removido)  
🔹 **ClipHistory** — 🛡️ **desactivado por defecto**. Activación manual + redacción automática de API keys, tokens y passwords  
🔹 **BatteryLog** — compatible con el cambio de API en macOS 13+  
🔹 Algunas herramientas requieren **Full Disk Access** o permisos de **Localización**

---

<p align="center">
  <sub>MIT © 2026 · hecho con ☕ por <a href="https://github.com/devsart95">@devsart95</a></sub>
</p>
