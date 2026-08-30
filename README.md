<p align="center">
  <img src="https://raw.githubusercontent.com/devsart95/toolsartoripy/main/banner.svg" alt="toolsartoripy" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white&style=for-the-badge"/>
  <img src="https://img.shields.io/badge/macOS-14%2B-000000?logo=apple&logoColor=white&style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Textual-TUI-FF6B6B?logo=gnometerminal&logoColor=white&style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Rich-terminal-7C3AED?logo=python&logoColor=white&style=for-the-badge"/>
  <img src="https://img.shields.io/badge/psutil-system-06B6D4?logoColor=white&style=for-the-badge"/>
  <img src="https://img.shields.io/badge/sin%20sudo-00CC44?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/license-MIT-22C55E?style=for-the-badge"/>
</p>

<p align="center">
  <b>11 herramientas de terminal para macOS, en una sola app navegable.</b><br>
  <sub>Todo local. Sin red saliente, sin telemetría, sin <code>sudo</code>.</sub>
</p>

---

## De dónde salió esto

Empezó como scripts sueltos tirados en una carpeta. Uno para mirar el CPU,
otro para ver qué proceso se comió el `:3000`, otro para saber por qué el
disco estaba lleno otra vez. Pruebas: cada uno escrito en una sentada para
responder **una** pregunta y después olvidado hasta la próxima vez que hiciera
falta.

El problema de los scripts sueltos es que nunca te acordás de cuál tenías, ni
cómo se llamaba, ni dónde lo dejaste. Así que se juntaron todos acá adentro:
un sidebar, una tecla por herramienta, y el mismo lenguaje visual para las 11.
Sigue siendo un laboratorio — el valor está en lo que se aprende construyéndolo,
no en competir con `htop`.

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

Python 3.11+ y tres dependencias (`textual`, `rich`, `psutil`). Todo lo demás
son binarios que ya trae macOS: `lsof`, `ioreg`, `system_profiler`, `networksetup`,
`pbpaste`, `log`, `syslog`, `ps`, `tail`.

Dos herramientas piden algo más, y sólo ellas: GitRadar necesita `git`,
DockerGlitch necesita `docker`. Sin ellos el resto anda igual.

---

## Las herramientas

|   | Tool | Qué responde | Tecla |
|---|------|--------------|-------|
| ⚡ | **SysGlitch** | ¿Qué está quemando la máquina? CPU por core, RAM, disco y red — con sparklines de los últimos 60 s | `1` |
| 🔌 | **PortScan** | ¿Quién tiene tomado el `:3000`? Puertos en escucha con su proceso dueño | `2` |
| 🎯 | **GitRadar** | ¿En qué repo me quedé sucio? Rama, ahead/behind, archivos sin commitear, último commit | `3` |
| 🐳 | **DockerGlitch** | ¿Qué contenedor está vivo y cuánto consume? | `4` |
| 🔥 | **DiskHeat** | ¿Por qué se llenó el disco? Directorios pesados y cachés recuperables | `5` |
| 🌐 | **NetWatch** | ¿Con quién está hablando mi máquina? Conexiones activas + DNS inverso | `6` |
| 🔋 | **BatteryLog** | ¿Cuánto le queda de vida a la batería? Ciclos, capacidad, temperatura | `7` |
| 📡 | **WifiMap** | ¿Qué hay en el aire? Redes cercanas con señal y canal | `8` |
| 📋 | **ClipHistory** | ¿Qué copié hace tres minutos? Historial de clipboard — **opt-in** | `9` |
| 📄 | **LogTail** | ¿Qué se rompió? Logs del sistema y crash reports | `0` |
| 🌧 | **MatrixRain** | Nada. Es lluvia digital y se ve bien | `m` |

Además: `↑` `↓` navegan el sidebar, `r` refresca la vista actual, `q` sale.

---

## Configuración

GitRadar y DiskHeat necesitan saber dónde guardás tu código. Lo autodetectan
buscando los nombres habituales en `$HOME` (`Projects`, `Code`, `dev`, `src`…),
y si no acierta, se lo decís vos:

```bash
export TOOLSARTORIPY_CODE_DIR=~/work
export TOOLSARTORIPY_SCAN_ROOTS=~/work:~/Downloads   # separado por ':'
```

Ninguna ruta personal está hardcodeada en el código: viven en `config.py`.

---

## Privacidad

Es una app que mira tu máquina, así que las reglas están escritas:

🔹 **Nada sale de tu equipo.** No hay llamadas de red salientes en el código —
   el único acceso remoto es el DNS inverso de NetWatch, contra tu propio resolver.
🔹 **Nada se guarda en disco.** Ni historial, ni caché, ni logs propios. Todo
   vive en memoria y muere con el proceso.
🔹 **ClipHistory arranca desactivado.** Hay que activarlo a mano en la UI. Con
   la captura activa, redacta API keys, tokens y passwords **antes** de guardar
   la entrada, y el historial se borra al cerrar.
🔹 **Sin `sudo`.** Nunca. Donde `psutil` pediría root (conexiones de red), se usa
   `lsof` en su lugar.

---

## Cómo está armado

```
app.py            entry point: sidebar, ContentSwitcher, bindings
config.py         rutas por env var — lo único específico de tu máquina
screens/          una herramienta por archivo, ~200 líneas cada una
widgets/shared.py pct_bar(), sparkline(), human(), lsof sin sudo
```

Agregar una herramienta son cuatro pasos:

1. `screens/mitool.py` con una vista que exponga `refresh_view()`.
2. Guarda de actividad: `if not is_view_active(self, "mitool"): return` — sin
   eso, la vista sigue consumiendo CPU escondida detrás de otra.
3. Lo lento (git, docker, DNS, caminar el filesystem) va en `run_worker`. La UI
   nunca se congela: es la regla que gobierna todo el repo.
4. Registrarla en `TOOLS`, `BINDINGS` y el `ContentSwitcher` de `app.py`.

Lint: `ruff check .` — configurado en `.ruff.toml`, sale limpio.

---

## Las trampas de macOS que ya están resueltas

Media hora de dolor por cada una de estas, guardada acá para que no la pagues de nuevo:

🔹 `psutil.net_connections()` pide root en macOS. Se reemplaza parseando
   `lsof -i -n -P`, que no lo pide.
🔹 El binario `airport` fue removido en macOS 14.4. WifiMap cae solo a
   `system_profiler SPAirPortDataType`.
🔹 La API de batería cambió en macOS 13. BatteryLog lee `ioreg` y contempla
   ambos formatos.
🔹 Algunas vistas (LogTail, ClipHistory) necesitan **Full Disk Access** o
   permisos de **Localización** — macOS te los va a pedir, no la app.

---

<p align="center">
  <sub>MIT © 2026 · hecho con ☕ por <a href="https://github.com/devsart95">@devsart95</a></sub>
</p>
