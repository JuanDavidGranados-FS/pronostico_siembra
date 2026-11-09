"""Relevancia (métodos y perfiles), historial, diagnóstico, preferencias, lector de histórico y exportes."""
import csv
import json
import os

import pytest
from matplotlib.figure import Figure

from src.aplicacion.diagnostico import Diagnostico
from src.aplicacion.gestor_historial import GestorHistorial
from src.aplicacion.gestor_relevancia import GestorRelevancia
from src.aplicacion.orquestador import OrquestadorSimulacion
from src.dominio import metodos_relevancia as mr
from src.dominio.entidades import datos_por_defecto
from src.infraestructura import exportador, graficas as g, repositorio_memoria as mem
from src.infraestructura.lector_historico import leer_historico
from src.infraestructura.preferencias import Preferencias


@pytest.fixture(scope="module")
def resultado():
    d = datos_por_defecto()
    d.iteraciones, d.semilla = 400, 2
    d.plan["temporadas"] = 4
    return OrquestadorSimulacion().ejecutar_simulacion(d).a_dict()


@pytest.fixture()
def gestor():
    return GestorRelevancia(mem.RepositorioConfigRelevanciaMemoria(), mem.RepositorioRegistrosCampoMemoria())


def test_perfiles_guardar_listar_duplicar_exportar_importar(gestor):
    i = gestor.guardar("Mi perfil", {"agua": 90, "ph": 10}, autor="Ana")
    assert gestor.cargar(i)["pesos"]["agua"] == 90
    j = gestor.duplicar(i)
    assert j != i and len(gestor.listar()) == 2
    doc = gestor.exportar(i)
    assert gestor.validar_documento(doc) == []
    assert gestor.importar(doc) not in (i, j)
    assert gestor.eliminar(j) and len(gestor.listar()) == 2
    assert gestor.crear_defecto()


def test_perfiles_validaciones(gestor):
    with pytest.raises(ValueError):
        gestor.guardar("  ", {"agua": 1})
    with pytest.raises(ValueError):
        gestor.guardar("x", {"agua": 101})
    with pytest.raises(ValueError):
        gestor.cargar(999)
    assert gestor.validar_documento({"nombre": "x"}) and gestor.validar_documento("no")
    assert gestor.validar_pesos({}) and gestor.validar_pesos({"a": True})


def test_ley_del_minimo():
    pesos, textos = GestorRelevancia.ley_del_minimo(datos_por_defecto())
    assert set(pesos) == set(mr.VARIABLES) and all(0 <= v <= 100 for v in pesos.values()) and textos


def test_historico_spearman_y_validaciones():
    filas = [{"agua": i, "temperatura": 30 - i % 7, "rendimiento": 2 * i + (i % 3)} for i in range(1, 16)]
    r = GestorRelevancia.desde_historico(filas)
    assert r["valido"] and r["pesos"]["agua"] == 100
    assert not GestorRelevancia.desde_historico([])["valido"]
    assert not GestorRelevancia.desde_historico([{"agua": 1, "x": 2}] * 12)["valido"]
    assert not GestorRelevancia.desde_historico([{"foo": 1, "rendimiento": 2}] * 12)["valido"]
    assert not GestorRelevancia.desde_historico(filas[:5])["valido"]
    assert mr.spearman([1, 2, 3, 4], [1, 2, 3, 4]) == pytest.approx(1.0)
    assert mr.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)


def test_ahp_consistente_e_inconsistente():
    pares = GestorRelevancia.pares_experto()
    assert len(pares) == 10
    ok = GestorRelevancia.desde_experto({p: 1.0 for p in pares})
    assert ok["consistente"] and ok["cr"] == pytest.approx(0, abs=1e-6)
    malo = GestorRelevancia.desde_experto({("agua", "temperatura"): 9, ("temperatura", "humedad"): 9, ("humedad", "agua"): 9})
    assert not malo["consistente"] and malo["parejas_a_revisar"]
    with pytest.raises(ValueError):
        GestorRelevancia.desde_experto({("agua", "temperatura"): 20})
    with pytest.raises(ValueError):
        GestorRelevancia.desde_experto({("agua", "agua"): 2})


def test_diario_de_campo(gestor):
    d = datos_por_defecto()
    r = gestor.desde_campo(d)
    assert r["usa_ley_minimo"] and "Faltan" in r["motivo"]
    for i, (v, rend) in enumerate([(5, 4), (4, 3.5), (3, 2.5), (2, 2), (1, 1), (6, 4.5)]):
        gestor.agregar_registro("2026-A", "agua", v, rend)
    assert len(gestor.registros()) == 6
    r2 = gestor.desde_campo(d)
    assert not r2["usa_ley_minimo"] and r2["pesos"]["agua"] > 0
    for args in (("", "agua", 1, 1), ("t", "zzz", 1, 1), ("t", "agua", "x", 1)):
        with pytest.raises(ValueError):
            gestor.agregar_registro(*args)
    assert gestor.eliminar_registro(gestor.registros()[0]["id"])
    assert "agua" in gestor.experimento("agua").lower()
    with pytest.raises(ValueError):
        GestorRelevancia(mem.RepositorioConfigRelevanciaMemoria()).agregar_registro("t", "agua", 1, 1)


def test_lector_historico_csv_y_excel(tmp_path):
    ruta = tmp_path / "h.csv"
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["agua", "rendimiento"])
        for i in range(12):
            w.writerow([i, i * 2])
    assert len(leer_historico(str(ruta))) == 12
    from openpyxl import Workbook
    wb = Workbook()
    wb.active.append(["agua", "rendimiento"])
    for i in range(12):
        wb.active.append([i, i * 2])
    wb.save(tmp_path / "h.xlsx")
    assert len(leer_historico(str(tmp_path / "h.xlsx"))) == 12
    with pytest.raises(ValueError):
        leer_historico(str(tmp_path / "h.txt"))


def test_historial_filtros_renombrar_comparar(resultado):
    repo = mem.RepositorioHistorialMemoria()
    gh = GestorHistorial(repo)
    a = gh.guardar(resultado, nombre="Siembra Ñandú")
    b = gh.guardar({**resultado, "cultivo": "Trigo"}, nombre="Otra")
    assert [f["id"] for f in gh.listar(texto="nandu")] == [a]
    assert gh.listar(desde="2999-01-01") == [] and gh.listar(hasta="2000-01-01") == []
    assert gh.renombrar(a, " Nueva ") and gh.obtener(a)["nombre"] == "Nueva"
    with pytest.raises(ValueError):
        gh.renombrar(a, " ")
    c = gh.comparar([a, b])
    assert c[1]["dif_kpi"] == pytest.approx(0)
    d = gh.comparar_detallado(a, b)
    assert d["mejor"] == "empate" and "Cambia el cultivo" in " ".join(d["diferencias"])
    with pytest.raises(ValueError):
        gh.comparar([a, 99])
    with pytest.raises(ValueError):
        gh.comparar_detallado(a, 99)
    assert gh.eliminar(b)


def test_historial_comparacion_con_diferencias(resultado):
    gh = GestorHistorial(mem.RepositorioHistorialMemoria())
    import copy
    r2 = copy.deepcopy(resultado)
    r2["fecha_optima"]["fecha"] = "2027-09-01"
    r2["kpi"]["valor"] = resultado["kpi"]["valor"] * 1.5
    r2["pesos"]["agua"] = 10
    i, j = gh.guardar(resultado), gh.guardar(r2, nombre="B")
    d = gh.comparar_detallado(i, j)
    assert d["mejor"] == "b" and "mayor" in d["resumen"] + " ".join(d["diferencias"]) and any("peso" in x for x in d["diferencias"])


def test_historial_repo_roto_devuelve_lista_vacia():
    class Roto:
        def listar(self, n):
            raise RuntimeError("x")
    assert GestorHistorial(Roto()).listar() == []


def test_diagnostico(tmp_path, gestor):
    cult = mem.RepositorioCultivosMemoria()
    dg = Diagnostico("memoria", lambda: False, cult, gestor, str(tmp_path))
    items = {i.clave: i for i in dg.ejecutar()}
    assert items["bd"].estado == "advertencia" and items["relevancia"].accion_id == "crear_relevancia" and items["json"].accion_id == "cargar_json"
    assert dg.listo(list(items.values())) and "docker compose" in dg.instrucciones_bd()
    dg.crear_relevancia_defecto()
    (tmp_path / "a.json").write_text("{}")
    items = {i.clave: i for i in dg.ejecutar()}
    assert items["relevancia"].estado == "ok" and items["json"].estado == "ok"
    vacio = Diagnostico("PostgreSQL", lambda: True, mem.RepositorioCultivosMemoria(precargar=False), gestor, str(tmp_path))
    it = {i.clave: i for i in vacio.ejecutar()}
    assert it["bd"].estado == "ok" and it["cultivos"].estado == "falta" and not vacio.listo(list(it.values()))
    assert vacio.cargar_cultivos_defecto() > 0
    roto = Diagnostico("PostgreSQL", lambda: 1 / 0, cult, gestor, str(tmp_path))
    assert roto.ejecutar()[0].estado == "advertencia"


def test_preferencias(tmp_path):
    p = Preferencias(str(tmp_path))
    assert p.obtener("x", 7) == 7
    p.guardar("x", 1)
    assert Preferencias(str(tmp_path)).obtener("x") == 1
    p.borrar("x")
    assert p.obtener("x") is None
    (tmp_path / "preferencias.json").write_text("{roto")
    assert Preferencias(str(tmp_path)).obtener("x") is None


@pytest.mark.parametrize("ext", [".pdf", ".xlsx", ".csv", ".json", ".png"])
def test_exportar_formatos(tmp_path, resultado, ext):
    ruta = tmp_path / f"r{ext}"
    exportador.exportar(str(ruta), resultado)
    assert ruta.stat().st_size > 500
    if ext == ".json":
        assert json.loads(ruta.read_text(encoding="utf-8"))["cultivo"] == "Maíz"


def test_exportar_sin_plan_ni_riesgos_y_formato_desconocido(tmp_path, resultado):
    r = {**resultado, "plan_temporadas": {}, "riesgos": [], "comparaciones": []}
    for ext in (".pdf", ".xlsx", ".png"):
        exportador.exportar(str(tmp_path / f"s{ext}"), r)
    with pytest.raises(ValueError):
        exportador.exportar(str(tmp_path / "x.doc"), resultado)


@pytest.mark.parametrize("tema", [g.TEMA_CLARO, g.TEMA_OSCURO])
def test_graficas(resultado, tema):
    for _, dibujar in g.GRAFICAS:
        dibujar(Figure(), resultado, tema)
    g.dibujar_comparacion(Figure(), resultado, resultado, tema)
    g.dibujar_riesgos(Figure(), {**resultado, "riesgos": []}, tema)
    assert g.familia_tipografica()
