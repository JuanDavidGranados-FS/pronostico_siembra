"""Pruebas de la versión web: el puente `web/motor.py` (lo que corre en el navegador) y que `web/siembra.zip` esté al día."""
import json
import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "web"))
os.environ.setdefault("MPLBACKEND", "Agg")

import empaquetar  # noqa: E402
import motor  # noqa: E402


def _r(texto):
    return json.loads(texto)


@pytest.fixture()
def inicio():
    motor.restaurar("{}")
    r = _r(motor.iniciar(""))
    assert r["ok"], r
    return r["valor"]


def _simular(datos):
    r = _r(motor.simular(json.dumps(datos)))
    assert r["ok"], r
    return r["valor"]


def test_zip_actualizado():
    """Si falla: ejecuta `python web/empaquetar.py` y sube el zip nuevo."""
    assert empaquetar.diferencias() == []


def test_iniciar_trae_lo_que_la_interfaz_necesita(inicio):
    assert {c["nombre"] for c in inicio["cultivos"]} >= {"Maíz", "Papa"}
    assert set(inicio["variables"]) == {"agua", "temperatura", "humedad", "ph", "nutrientes"}
    assert inicio["glosario"] and inicio["faq"] and inicio["pares_experto"]
    assert inicio["guia_integracion"].startswith("# Guía de integración")
    assert ".pdf" in inicio["formatos"]


def test_simular_guarda_en_historial_y_persiste(inicio):
    datos = inicio["datos"]
    datos["iteraciones"], datos["semilla"] = 300, 1
    avances = []
    r = _r(motor.simular(json.dumps(datos), lambda i, n: avances.append((i, n))))
    assert r["ok"] and r["valor"]["fecha_optima"]["fecha_larga"]
    assert avances and avances[-1][0] == avances[-1][1]
    foto = motor.instantanea()
    motor.restaurar("{}")
    assert _r(motor.listar_historial())["valor"] == []
    motor.restaurar(foto)
    filas = _r(motor.listar_historial())["valor"]
    assert len(filas) == 1
    assert _r(motor.reutilizar(filas[0]["id"]))["valor"]["iteraciones"] == 300


def test_dato_invalido_devuelve_error_legible(inicio):
    datos = inicio["datos"]
    datos["deterministas"]["ph"] = 20
    r = _r(motor.simular(json.dumps(datos)))
    assert not r["ok"] and "ph" in r["error"]


def test_relevancia_metodos_y_perfiles(inicio):
    datos = json.dumps(inicio["datos"])
    assert set(_r(motor.ley_minimo(datos))["valor"]["pesos"]) == set(inicio["variables"])
    assert "consistencia" in _r(motor.experto(json.dumps([["agua", "temperatura", 3]])))["valor"]["resumen_consistencia"]
    assert not _r(motor.agregar_registro("", "agua", "1", "2"))["ok"]
    assert _r(motor.guardar_perfil("Mío", json.dumps(inicio["pesos_defecto"])))["ok"]
    pid = _r(motor.perfiles())["valor"][0]["id"]
    doc = _r(motor.exportar_perfil(pid))["valor"]
    assert _r(motor.importar_perfil(json.dumps(doc)))["ok"]
    assert len(_r(motor.perfiles())["valor"]) == 2


def test_matrices_y_json_externo(inicio):
    salud = inicio["datos"]["estado"]["salud"]
    r = _r(motor.agregar_estado(json.dumps(salud["estados"]), json.dumps(salud["matriz"]), "Seco"))["valor"]
    assert r["estados"][-1] == "Seco" and len(r["matriz"]) == 5
    assert _r(motor.recibir_json(json.dumps(inicio["datos"]), "a.json"))["valor"]["valido"]
    assert not _r(motor.recibir_json("{malo", "b.json"))["valor"]["valido"]


def test_graficas_comparacion_y_exportes(inicio):
    datos = inicio["datos"]
    datos["iteraciones"] = 300
    _simular(datos)
    _simular(datos)
    for nombre in inicio["graficas"]:
        assert _r(motor.grafica(nombre, False, True))["valor"].lstrip().startswith("<?xml")
    a, b = [f["id"] for f in _r(motor.listar_historial())["valor"][:2]]
    assert "resumen" in _r(motor.comparar(a, b))["valor"]
    assert "<svg" in _r(motor.grafica_comparacion(a, b, True, False))["valor"]
    for ext in (".csv", ".json"):
        ruta = _r(motor.exportar(ext))["valor"]
        assert os.path.getsize(ruta) > 0


def test_asistente_responde(inicio):
    assert _r(motor.preguntar("¿Qué es Montecarlo?", "inicio"))["valor"]["respuesta"]
