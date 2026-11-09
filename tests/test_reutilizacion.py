"""Reutilizar la configuración de una simulación guardada (memoria y esquema PostgreSQL simulado)."""
from src.aplicacion.orquestador import OrquestadorSimulacion
from src.aplicacion.reutilizacion import configuracion_de_simulacion
from src.dominio.entidades import datos_por_defecto
from src.infraestructura import repositorio_memoria as mem


def test_reutiliza_configuracion_completa():
    cult, cfg, hist = mem.RepositorioCultivosMemoria(), mem.RepositorioConfiguracionesMemoria(), mem.RepositorioHistorialMemoria()
    d = datos_por_defecto()
    d.iteraciones, d.semilla, d.nombre = 300, 5, "prueba"
    d.plan["temporadas"] = 3
    r = OrquestadorSimulacion(cult, cfg, hist).ejecutar_simulacion(d)
    rec = configuracion_de_simulacion(hist, cfg, r.id_historial)
    assert rec is not None and rec.plan["temporadas"] == 3 and rec.iteraciones == 300


def test_sin_configuracion_devuelve_none():
    hist, cfg = mem.RepositorioHistorialMemoria(), mem.RepositorioConfiguracionesMemoria()
    assert configuracion_de_simulacion(hist, cfg, 99) is None


class _Cfg:
    def obtener(self, i):
        return {"datos_deterministas": {"_completo": datos_por_defecto().a_dict()}}


class _Hist:
    def obtener(self, i):
        return {"configuracion_id": 1}


def test_esquema_postgres_usa_copia_completa():
    assert configuracion_de_simulacion(_Hist(), _Cfg(), 1).cultivo.nombre == "Maíz"
