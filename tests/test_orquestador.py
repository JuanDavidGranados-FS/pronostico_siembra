import copy
import json

import pytest

from src.aplicacion.gestor_historial import GestorHistorial
from src.aplicacion.orquestador import OrquestadorSimulacion
from src.aplicacion.validador import ErrorValidacion
from src.dominio.entidades import DatosEntrada, datos_por_defecto
from src.infraestructura.adaptador_json import AdaptadorJSON
from src.infraestructura.repositorio_memoria import (RepositorioConfiguracionesMemoria, RepositorioCultivosMemoria,
                                                     RepositorioDatosExternosMemoria, RepositorioHistorialMemoria)


def base(**kw) -> DatosEntrada:
    d = datos_por_defecto()
    d.deterministas["fecha"] = "2026-01-01"
    d.iteraciones, d.semilla = 600, 42
    for k, v in kw.items():
        setattr(d, k, v)
    return d


def pesos(**p):
    return {k: p.get(k, 0) for k in ("agua", "ph", "temperatura", "humedad", "nutrientes")}


def test_cv01_pesos_opuestos_cambian_fecha_optima():
    """CV-01: Agua=100/pH=0 vs. Agua=0/pH=100 producen fechas óptimas distintas."""
    o = OrquestadorSimulacion()
    r_agua = o.ejecutar_simulacion(base(pesos=pesos(agua=100)))
    r_ph = o.ejecutar_simulacion(base(pesos=pesos(ph=100)))
    assert r_agua.fecha_optima.fecha != r_ph.fecha_optima.fecha


def test_cv02_sano_muerto_da_rendimiento_cero():
    """CV-02: Sano→Muerto = 100 % implica rendimiento (y KPI) 0."""
    d = base()
    d.estado["salud"]["matriz"][0] = [0.0, 0.0, 0.0, 1.0]
    r = OrquestadorSimulacion().ejecutar_simulacion(d)
    assert r.kpi.valor == 0 and r.kpi.rendimiento_esperado == 0
    assert r.estadisticas_rendimiento["media"] == 0 and not r.fecha_optima.viable


def test_cv03_reproducibilidad():
    """CV-03: misma semilla, mismo resultado."""
    o = OrquestadorSimulacion()
    a, b = o.ejecutar_simulacion(base()), o.ejecutar_simulacion(base())
    da, db = a.a_dict(), b.a_dict()
    for d in (da, db):  # metadatos que dependen del reloj, no del cálculo
        d.pop("duracion_segundos"), d.pop("nombre")
    assert da == db
    c = o.ejecutar_simulacion(base(semilla=43))
    assert c.kpi.valor != a.kpi.valor


def test_cv04_clima_artico_no_viable():
    """CV-04: clima ártico → no viable (o fecha más tardía que la del clima templado)."""
    normal = OrquestadorSimulacion().ejecutar_simulacion(base())
    d = base()
    d.estocasticos["temperatura"].update(parametros={"media": -5.0, "std": 3.0}, amplitud_estacional=10.0)
    art = OrquestadorSimulacion().ejecutar_simulacion(d)
    assert (not art.fecha_optima.viable) or art.fecha_optima.fecha > normal.fecha_optima.fecha
    assert art.kpi.valor < normal.kpi.valor


def test_estacionalidad_clima_templado_es_viable():
    r = OrquestadorSimulacion().ejecutar_simulacion(base())
    assert r.fecha_optima.viable and r.kpi.valor > 0
    assert 0 <= r.fecha_optima.probabilidad_exito <= 1


def test_esfuerzo_reduce_kpi():
    o = OrquestadorSimulacion()
    assert o.ejecutar_simulacion(base(esfuerzo=1.0)).kpi.valor == pytest.approx(
        o.ejecutar_simulacion(base()).kpi.valor / 2)


def test_datos_invalidos_lanzan_error_de_validacion():
    d = base(); d.deterministas["ph"] = 99
    with pytest.raises(ErrorValidacion) as exc:
        OrquestadorSimulacion().ejecutar_simulacion(d)
    assert exc.value.errores


def test_persistencia_progreso_e_historial():
    hist, cfg = RepositorioHistorialMemoria(), RepositorioConfiguracionesMemoria()
    o = OrquestadorSimulacion(RepositorioCultivosMemoria(), cfg, hist)
    avances = []
    r1 = o.ejecutar_simulacion(base(), progreso=lambda i, n: avances.append((i, n)))
    r2 = o.ejecutar_simulacion(base(esfuerzo=1.0))
    assert avances[-1][0] == avances[-1][1] and r1.id_historial == 1 and r2.id_historial == 2
    g = GestorHistorial(hist)
    assert len(g.listar()) == 2 and g.obtener(1)["fecha_optima"] == r1.fecha_optima.fecha.isoformat()
    comp = g.comparar([1, 2])
    assert comp[0]["dif_kpi"] == 0 and comp[1]["dif_kpi"] < 0
    with pytest.raises(ValueError): g.comparar([99])
    assert g.guardar(r1.a_dict()) == 3
    assert len(o.listar_cultivos()) == 4


def test_fallo_de_repositorio_no_interrumpe():
    class Roto(RepositorioHistorialMemoria):
        def guardar(self, *a, **k): raise RuntimeError("bd caída")
    r = OrquestadorSimulacion(repo_historial=Roto()).ejecutar_simulacion(base())
    assert r.id_historial is None and r.kpi.valor > 0


def test_sin_repositorio_de_cultivos():
    assert OrquestadorSimulacion().listar_cultivos() == []


def test_rendimiento_10000_iteraciones_menos_de_30s():
    """RNF-03: 10 000 iteraciones en < 30 s."""
    import time
    d = base(iteraciones=10000)
    t = time.time(); OrquestadorSimulacion().ejecutar_simulacion(d)
    assert time.time() - t < 30


def test_serializacion_y_adaptador_json(tmp_path):
    ad = AdaptadorJSON()
    d = base()
    ruta = tmp_path / "entrada.json"
    ad.escribir_json(str(ruta), d.a_dict())
    datos = ad.leer_json(str(ruta))
    assert ad.validar(datos) == []
    assert ad.a_datos_entrada(datos).a_dict() == d.a_dict()
    assert ad.validar({"cultivo": {}}) and ad.validar({"cultivo": {"x": 1}, "deterministas": {}, "estocasticos": {}})
    (tmp_path / "malo.json").write_text("{no es json")
    (tmp_path / "lista.json").write_text("[1]")
    with pytest.raises(ValueError): ad.leer_json(str(tmp_path / "malo.json"))
    with pytest.raises(ValueError): ad.leer_json(str(tmp_path / "lista.json"))
    r = OrquestadorSimulacion().ejecutar_simulacion(d).a_dict()
    ad.exportar_csv(str(tmp_path / "r.csv"), r)
    assert (tmp_path / "r.csv").read_text(encoding="utf-8").startswith("fecha,kpi")
    json.dumps(r)  # el resultado es serializable


def test_repositorios_memoria():
    c = RepositorioCultivosMemoria(precargar=False)
    i = c.guardar({"nombre": "X"})
    assert c.obtener(i)["nombre"] == "X" and c.eliminar(i) and not c.eliminar(i) and c.listar() == []
    e = RepositorioDatosExternosMemoria()
    assert e.ultimo() is None
    e.guardar("sim", {"a": 1}); assert e.ultimo()["origen"] == "sim"
    cfg = RepositorioConfiguracionesMemoria(); j = cfg.guardar("n", {}); assert cfg.obtener(j) and cfg.listar()
