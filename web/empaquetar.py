"""Empaqueta el motor de simulación para la versión web.

Crea `web/siembra.zip` con el código Python que corre en el navegador (Pyodide): `src/dominio`, `src/aplicacion`,
la parte de `src/infraestructura` que no depende de PostgreSQL y `web/motor.py`. Ejecútalo cada vez que cambies ese código:

    python web/empaquetar.py

La prueba `tests/test_web.py` falla si el zip quedó desactualizado.
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path
from typing import Dict, List

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "web" / "siembra.zip"
# Lo que la web usa de cada capa (sin PostgreSQL, configuración, logs ni la interfaz de escritorio).
INFRAESTRUCTURA = ["__init__.py", "repositorio_memoria.py", "adaptador_json.py", "lector_historico.py", "graficas.py",
                   "exportador.py"]


def archivos() -> Dict[str, Path]:
    """Nombre dentro del zip → archivo en el repositorio."""
    mapa: Dict[str, Path] = {"src/__init__.py": RAIZ / "src" / "__init__.py"}
    for f in sorted((RAIZ / "src" / "dominio").glob("*.py")):
        mapa[f"src/dominio/{f.name}"] = f
    for f in sorted((RAIZ / "src" / "aplicacion").glob("*.py")):
        mapa[f"src/aplicacion/{f.name}"] = f
    for nombre in INFRAESTRUCTURA:
        mapa[f"src/infraestructura/{nombre}"] = RAIZ / "src" / "infraestructura" / nombre
    mapa["motor.py"] = RAIZ / "web" / "motor.py"
    mapa["docs/integration_guide.md"] = RAIZ / "docs" / "integration_guide.md"  # se muestra en Ayuda
    return mapa


def construir() -> bytes:
    """Zip reproducible (mismas fechas y orden siempre), para que no cambie si el código no cambió."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, ruta in archivos().items():
            info = zipfile.ZipInfo(nombre, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, ruta.read_bytes())
    return buf.getvalue()


def diferencias() -> List[str]:
    """Archivos cuyo contenido en el zip actual no coincide con el repositorio."""
    if not DESTINO.exists():
        return ["(falta web/siembra.zip)"]
    with zipfile.ZipFile(DESTINO) as z:
        en_zip = {n: z.read(n) for n in z.namelist()}
    esperados = {n: p.read_bytes() for n, p in archivos().items()}
    return sorted(n for n in set(en_zip) | set(esperados) if en_zip.get(n) != esperados.get(n))


if __name__ == "__main__":
    DESTINO.write_bytes(construir())
    print(f"Listo: {DESTINO.relative_to(RAIZ)} ({len(archivos())} archivos, {DESTINO.stat().st_size // 1024} KB)")
    sys.exit(0)
