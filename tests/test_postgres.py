"""Integración con PostgreSQL real (se omite si no hay base de datos: docker compose -f docker/docker-compose.yml up -d)."""
import pytest

from src.aplicacion.orquestador import OrquestadorSimulacion
from src.aplicacion.reutilizacion import configuracion_de_simulacion
from src.dominio.entidades import datos_por_defecto

pg = pytest.importorskip("src.infraestructura.repositorio_postgres")


@pytest.fixture(scope="module")
def con():
    try:
        from src.infraestructura.config import cargar_config
        c = pg.ConexionPostgres(cargar_config())
        if not c.probar():
            raise RuntimeError
        return c
    except Exception:
        pytest.skip("PostgreSQL no disponible")


def test_guardar_y_reutilizar_configuracion(con):
    cult, cfg, hist = pg.RepositorioCultivosPG(con), pg.RepositorioConfiguracionesPG(con), pg.RepositorioHistorialPG(con)
    d = datos_por_defecto()
    d.iteraciones, d.nombre = 200, "pg-test"
    d.plan["temporadas"] = 3
    r = OrquestadorSimulacion(cult, cfg, hist).ejecutar_simulacion(d)
    rec = configuracion_de_simulacion(hist, cfg, r.id_historial)
    assert rec is not None and rec.plan["temporadas"] == 3
    hist.eliminar(r.id_historial)


def test_matrices(con):
    m = pg.RepositorioMatricesPG(con)
    i = m.guardar("t", "salud", ["A", "B"], [[0.5, 0.5], [0, 1]])
    assert m.obtener(i)["estados"] == ["A", "B"]
    assert m.eliminar(i)
