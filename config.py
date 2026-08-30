"""Configuración por entorno.

Ningún path personal vive hardcodeado en el código: GitRadar y DiskHeat
necesitan saber dónde guardás los repos, y eso cambia en cada máquina.

    TOOLSARTORIPY_CODE_DIR    directorio con tus repos     (default: autodetectado)
    TOOLSARTORIPY_SCAN_ROOTS  dirs a escanear, separados por ':'
"""
import os
from pathlib import Path

# Nombres habituales de la carpeta de proyectos, en orden de preferencia.
_CODE_DIR_CANDIDATES = (
    "Devsar", "Projects", "Proyectos", "Code", "code",
    "dev", "Developer", "src", "work", "repos", "git",
)


def code_dir() -> Path:
    """Directorio raíz donde viven los repos.

    Env var si está definida; si no, el primer candidato que exista en
    $HOME; si no hay ninguno, $HOME (GitRadar simplemente no encontrará
    repos y lo dirá en pantalla).
    """
    env = os.environ.get("TOOLSARTORIPY_CODE_DIR", "").strip()
    if env:
        return Path(env).expanduser()
    home = Path.home()
    for name in _CODE_DIR_CANDIDATES:
        candidate = home / name
        if candidate.is_dir():
            return candidate
    return home


def scan_roots() -> list[Path]:
    """Directorios que DiskHeat mide en busca de peso."""
    env = os.environ.get("TOOLSARTORIPY_SCAN_ROOTS", "").strip()
    if env:
        return [Path(p).expanduser() for p in env.split(os.pathsep) if p.strip()]
    home = Path.home()
    roots = [code_dir(), home / "Downloads", home / "Desktop"]
    seen: list[Path] = []
    for r in roots:
        if r not in seen:
            seen.append(r)
    return seen
