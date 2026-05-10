# ⚡ toolsartoripy

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python)
![macOS](https://img.shields.io/badge/macOS-000000?logo=apple)
![Textual](https://img.shields.io/badge/Textual-8.0%2B-FF6B6B)
![License](https://img.shields.io/badge/License-MIT-22c55e)

> **10 herramientas TUI para macOS** — monitor de sistema, puertos, Git, Docker, disco, red, batería, WiFi, clipboard y logs. Todo en una terminal.

```bash
git clone https://github.com/devsart95/toolsartoripy
cd toolsartoripy && pip install -r requirements.txt && python app.py
```

## 🧰 Herramientas

| # | Tool | Qué hace |
|---|------|----------|
| ⚡ | SysGlitch | CPU, RAM, disco, red, procesos |
| 🔌 | PortScan | Puertos activos sin sudo |
| 🎯 | GitRadar | Estado de repos en ~/Devsar |
| 🐳 | DockerGlitch | Contenedores en tiempo real |
| 💾 | DiskHeat | Directorios pesados + caches |
| 🌐 | NetWatch | Conexiones red con DNS |
| 🔋 | BatteryLog | Salud de batería macOS |
| 📡 | WifiMap | Redes WiFi cercanas |
| 📋 | ClipHistory | Historial clipboard (opt-in) |
| 📄 | LogTail | Logs del sistema |

## ⌨️ Controles

| Tecla | Acción |
|-------|--------|
| `↑↓` | Navegar sidebar |
| `1`–`0` | Ir a herramienta |
| `r` | Refrescar |
| `q` | Salir |

## 🏗 Stack

[Textual](https://github.com/Textualize/textual) + [Rich](https://github.com/Textualize/rich) + [psutil](https://github.com/giampaolo/psutil) + comandos macOS (`lsof`, `ioreg`, `docker`, `git`...)

## ⚠️ Notas

- `PortScan` / `NetWatch`: usan `lsof` (no requiere sudo)
- `WifiMap`: fallback automático en macOS 14.4+ (airport removido)
- `ClipHistory`: **desactivado por defecto** — activalo con el botón en la UI. Redacta automáticamente API keys, tokens y passwords
- Algunas herramientas necesitan Full Disk Access o permisos de Localización

## 📄 License

MIT
