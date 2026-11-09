"""Repositorios PostgreSQL (psycopg2, RealDictCursor, transacciones con rollback)."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from decimal import Decimal
from typing import Any, Dict, Iterator, List, Optional

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from src.dominio.interfaces import (RepositorioConfigRelevancia, RepositorioConfiguraciones, RepositorioCultivos,
                                    RepositorioDatosExternos, RepositorioHistorial, RepositorioMatrices,
                                    RepositorioRegistrosCampo)
from src.infraestructura.config import ConfigBD

log = logging.getLogger(__name__)


def _limpiar(fila: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convierte Decimal a float y fechas a texto ISO para que la fila sea serializable."""
    if fila is None:
        return None
    return {k: float(v) if isinstance(v, Decimal) else (v.isoformat() if hasattr(v, "isoformat") else v)
            for k, v in dict(fila).items()}


class ConexionPostgres:
    """Fábrica de cursores transaccionales: commit al salir, rollback ante error."""

    def __init__(self, config: ConfigBD) -> None:
        self.config = config

    def _conectar(self):
        c = self.config
        return psycopg2.connect(host=c.host, port=c.port, dbname=c.dbname, user=c.user,
                                password=c.password, connect_timeout=5)

    @contextmanager
    def cursor(self) -> Iterator[RealDictCursor]:
        """Entrega un cursor de diccionarios dentro de una transacción."""
        conn = self._conectar()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            log.exception("Error en la transacción; se hizo rollback")
            raise
        finally:
            conn.close()

    def probar(self) -> bool:
        """True si la base de datos responde."""
        try:
            with self.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception:
            return False


class RepositorioCultivosPG(RepositorioCultivos):
    """Catálogo de cultivos en PostgreSQL."""

    def __init__(self, conexion: ConexionPostgres) -> None:
        self.conexion = conexion

    def guardar(self, cultivo: Dict[str, Any]) -> int:
        """Inserta un cultivo y devuelve su id."""
        with self.conexion.cursor() as cur:
            cur.execute(
                """INSERT INTO cultivos (nombre, dias_crecimiento, temperatura_min, temperatura_max,
                   requerimiento_agua, resistencia_plagas, rendimiento_base)
                   VALUES (%(nombre)s, %(dias_crecimiento)s, %(temperatura_min)s, %(temperatura_max)s,
                   %(requerimiento_agua)s, %(resistencia_plagas)s, %(rendimiento_base)s) RETURNING id""", cultivo)
            return cur.fetchone()["id"]

    def obtener(self, id_cultivo: int) -> Optional[Dict[str, Any]]:
        """Obtiene un cultivo por id."""
        with self.conexion.cursor() as cur:
            cur.execute("SELECT * FROM cultivos WHERE id = %s", (id_cultivo,))
            return _limpiar(cur.fetchone())

    def listar(self) -> List[Dict[str, Any]]:
        """Lista los cultivos ordenados por nombre."""
        with self.conexion.cursor() as cur:
            cur.execute("SELECT * FROM cultivos ORDER BY nombre")
            return [_limpiar(f) for f in cur.fetchall()]

    def eliminar(self, id_cultivo: int) -> bool:
        """Elimina un cultivo."""
        with self.conexion.cursor() as cur:
            cur.execute("DELETE FROM cultivos WHERE id = %s", (id_cultivo,))
            return cur.rowcount > 0


class RepositorioConfiguracionesPG(RepositorioConfiguraciones):
    """Configuraciones de simulación en PostgreSQL."""

    def __init__(self, conexion: ConexionPostgres) -> None:
        self.conexion = conexion

    def guardar(self, nombre: str, datos: Dict[str, Any]) -> int:
        """Guarda una configuración (DatosEntrada.a_dict()) repartida en sus columnas JSONB."""
        with self.conexion.cursor() as cur:
            cur.execute(
                """INSERT INTO configuraciones (nombre, datos_deterministas, datos_estocasticos, datos_estado,
                   factor_relevancia) VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (nombre, Json({"cultivo": datos["cultivo"], **datos["deterministas"],
                               "iteraciones": datos["iteraciones"], "semilla": datos["semilla"],
                               "ventana_dias": datos["ventana_dias"], "paso_dias": datos["paso_dias"],
                               "esfuerzo": datos["esfuerzo"], "_completo": datos}),
                 Json(datos["estocasticos"]), Json(datos["estado"]), Json(datos["pesos"])))
            return cur.fetchone()["id"]

    def obtener(self, id_config: int) -> Optional[Dict[str, Any]]:
        """Obtiene una configuración."""
        with self.conexion.cursor() as cur:
            cur.execute("SELECT * FROM configuraciones WHERE id = %s", (id_config,))
            return _limpiar(cur.fetchone())

    def listar(self) -> List[Dict[str, Any]]:
        """Lista configuraciones recientes."""
        with self.conexion.cursor() as cur:
            cur.execute("SELECT * FROM configuraciones ORDER BY id DESC")
            return [_limpiar(f) for f in cur.fetchall()]

    def eliminar(self, id_config: int) -> bool:
        """Elimina una configuración."""
        with self.conexion.cursor() as cur:
            cur.execute("DELETE FROM configuraciones WHERE id = %s", (id_config,))
            return cur.rowcount > 0


class RepositorioHistorialPG(RepositorioHistorial):
    """Historial de simulaciones en PostgreSQL."""

    def __init__(self, conexion: ConexionPostgres) -> None:
        self.conexion = conexion

    def guardar(self, resultado: Dict[str, Any], configuracion_id: Optional[int] = None, nombre: str = "") -> int:
        """Guarda un resultado; la probabilidad se almacena como porcentaje (0-100)."""
        fo = resultado["fecha_optima"]
        with self.conexion.cursor() as cur:
            cur.execute(
                """INSERT INTO historial_simulaciones (configuracion_id, nombre, fecha_optima, kpi_esperado,
                   probabilidad_exito, resultado_completo) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (configuracion_id, nombre or resultado.get("nombre", ""), fo["fecha"], fo["kpi"],
                 fo["probabilidad_exito"] * 100, Json(resultado)))
            return cur.fetchone()["id"]

    def obtener(self, id_sim: int) -> Optional[Dict[str, Any]]:
        """Obtiene una simulación completa."""
        with self.conexion.cursor() as cur:
            cur.execute("SELECT * FROM historial_simulaciones WHERE id = %s", (id_sim,))
            return _limpiar(cur.fetchone())

    def listar(self, limite: int = 50) -> List[Dict[str, Any]]:
        """Lista las simulaciones más recientes (sin el resultado completo)."""
        with self.conexion.cursor() as cur:
            cur.execute("""SELECT id, configuracion_id, nombre, fecha_optima, kpi_esperado, probabilidad_exito,
                           fecha_ejecucion FROM historial_simulaciones ORDER BY id DESC LIMIT %s""", (limite,))
            return [_limpiar(f) for f in cur.fetchall()]

    def renombrar(self, id_sim: int, nombre: str) -> bool:
        """Cambia el nombre de una simulación (columna y copia dentro del JSON)."""
        with self.conexion.cursor() as cur:
            cur.execute("""UPDATE historial_simulaciones SET nombre = %s,
                           resultado_completo = jsonb_set(resultado_completo, '{nombre}', to_jsonb(%s::text))
                           WHERE id = %s""", (nombre, nombre, id_sim))
            return cur.rowcount > 0

    def eliminar(self, id_sim: int) -> bool:
        """Elimina una simulación."""
        with self.conexion.cursor() as cur:
            cur.execute("DELETE FROM historial_simulaciones WHERE id = %s", (id_sim,))
            return cur.rowcount > 0


class RepositorioDatosExternosPG(RepositorioDatosExternos):
    """Datos recibidos de simuladores externos."""

    def __init__(self, conexion: ConexionPostgres) -> None:
        self.conexion = conexion

    def guardar(self, origen: str, datos: Dict[str, Any], valido: bool = True) -> int:
        """Registra datos externos."""
        with self.conexion.cursor() as cur:
            cur.execute("INSERT INTO datos_externos (origen, datos, valido) VALUES (%s, %s, %s) RETURNING id",
                        (origen, Json(datos), valido))
            return cur.fetchone()["id"]

    def ultimo(self) -> Optional[Dict[str, Any]]:
        """Devuelve el último registro recibido."""
        with self.conexion.cursor() as cur:
            cur.execute("SELECT * FROM datos_externos ORDER BY id DESC LIMIT 1")
            return _limpiar(cur.fetchone())


class RepositorioConfigRelevanciaPG(RepositorioConfigRelevancia):
    """Perfiles de Factor de Relevancia en PostgreSQL."""

    def __init__(self, conexion: ConexionPostgres) -> None:
        self.conexion = conexion

    def guardar(self, config: Dict[str, Any]) -> int:
        """Guarda un perfil {nombre, pesos, metodo, autor, notas, fecha}."""
        with self.conexion.cursor() as cur:
            cur.execute("""INSERT INTO configuraciones_relevancia (nombre, autor, metodo, notas, pesos)
                           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                        (config["nombre"], config.get("autor", ""), config.get("metodo", "manual"),
                         config.get("notas", ""), Json(config["pesos"])))
            return cur.fetchone()["id"]

    def obtener(self, id_config: int) -> Optional[Dict[str, Any]]:
        """Obtiene un perfil."""
        with self.conexion.cursor() as cur:
            cur.execute("SELECT * FROM configuraciones_relevancia WHERE id = %s", (id_config,))
            return _limpiar(cur.fetchone())

    def listar(self) -> List[Dict[str, Any]]:
        """Lista los perfiles, los más recientes primero."""
        with self.conexion.cursor() as cur:
            cur.execute("SELECT * FROM configuraciones_relevancia ORDER BY id DESC")
            return [_limpiar(f) for f in cur.fetchall()]

    def eliminar(self, id_config: int) -> bool:
        """Elimina un perfil."""
        with self.conexion.cursor() as cur:
            cur.execute("DELETE FROM configuraciones_relevancia WHERE id = %s", (id_config,))
            return cur.rowcount > 0


class RepositorioMatricesPG(RepositorioMatrices):
    """Matrices de transición de Márkov en PostgreSQL (tabla `matrices_markov`)."""

    def __init__(self, conexion: ConexionPostgres) -> None:
        self.conexion = conexion

    def guardar(self, nombre: str, tipo: str, estados: List[str], matriz: List[List[float]]) -> int:
        """Guarda una matriz con sus estados."""
        with self.conexion.cursor() as cur:
            cur.execute("""INSERT INTO matrices_markov (nombre, tipo, estados, matriz_transicion)
                           VALUES (%s, %s, %s, %s) RETURNING id""", (nombre, tipo, Json(estados), Json(matriz)))
            return cur.fetchone()["id"]

    def listar(self, tipo: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista las matrices guardadas (opcionalmente de un tipo)."""
        with self.conexion.cursor() as cur:
            if tipo:
                cur.execute("SELECT * FROM matrices_markov WHERE tipo = %s ORDER BY id DESC", (tipo,))
            else:
                cur.execute("SELECT * FROM matrices_markov ORDER BY id DESC")
            return [_limpiar(f) for f in cur.fetchall()]

    def obtener(self, id_matriz: int) -> Optional[Dict[str, Any]]:
        """Obtiene una matriz."""
        with self.conexion.cursor() as cur:
            cur.execute("SELECT * FROM matrices_markov WHERE id = %s", (id_matriz,))
            return _limpiar(cur.fetchone())

    def eliminar(self, id_matriz: int) -> bool:
        """Elimina una matriz."""
        with self.conexion.cursor() as cur:
            cur.execute("DELETE FROM matrices_markov WHERE id = %s", (id_matriz,))
            return cur.rowcount > 0


class RepositorioRegistrosCampoPG(RepositorioRegistrosCampo):
    """Diario de campo en PostgreSQL."""

    def __init__(self, conexion: ConexionPostgres) -> None:
        self.conexion = conexion

    def guardar(self, registro: Dict[str, Any]) -> int:
        """Guarda {temporada, variable, valor, rendimiento}."""
        with self.conexion.cursor() as cur:
            cur.execute("""INSERT INTO registros_campo (temporada, variable, valor, rendimiento)
                           VALUES (%s, %s, %s, %s) RETURNING id""",
                        (str(registro["temporada"]), registro["variable"], registro["valor"], registro["rendimiento"]))
            return cur.fetchone()["id"]

    def listar(self) -> List[Dict[str, Any]]:
        """Lista los registros por orden de creación."""
        with self.conexion.cursor() as cur:
            cur.execute("SELECT * FROM registros_campo ORDER BY id")
            return [_limpiar(f) for f in cur.fetchall()]

    def eliminar(self, id_registro: int) -> bool:
        """Elimina un registro."""
        with self.conexion.cursor() as cur:
            cur.execute("DELETE FROM registros_campo WHERE id = %s", (id_registro,))
            return cur.rowcount > 0
