"""Pruebas de la versión web: el puente `web/motor.py` y que `web/siembra.zip` esté al día."""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "web"))

import empaquetar  # noqa: E402
import motor  # noqa: E402


def test_zip_actualizado():
    """Si falla: ejecuta `python web/empaquetar.py` y sube el zip nuevo."""
    assert empaquetar.diferencias() == []


def test_catalogo_trae_cultivos_y_valores_sugeridos():
    c = json.loads(motor.catalogo())
    assert {x["nombre"] for x in c["cultivos"]} >= {"Maíz", "Papa"}
    assert set(c["pesos"]) == {"agua", "temperatura", "humedad", "ph", "nutrientes"}
    assert "media" in c["clima"]["temperatura"]


def test_simular_con_datos_del_formulario():
    avances = []
    entrada = {"cultivo": {"nombre": "Papa", "rendimiento_base": "20"}, "deterministas": {"ph": "6,8"},
               "clima": {"temperatura": {"media": "18"}}, "pesos": {"agua": 90}, "iteraciones": 500, "temporadas": 3}
    r = json.loads(motor.simular(json.dumps(entrada), lambda i, n: avances.append((i, n))))
    assert r["ok"], r
    res = r["resultado"]
    assert res["cultivo"] == "Papa" and res["iteraciones"] == 500
    assert res["fecha_optima"]["fecha_larga"] and all(x["fecha_larga"] for x in res["comparaciones"])
    assert len(res["plan_temporadas"]["filas"]) == 3
    assert avances and avances[-1][0] == avances[-1][1]


def test_simular_con_dato_invalido_devuelve_error_legible():
    r = json.loads(motor.simular(json.dumps({"deterministas": {"ph": "20"}, "iteraciones": 300})))
    assert not r["ok"] and "ph" in r["errores"][0]


def test_asistente_responde():
    r = json.loads(motor.preguntar("¿Qué es Montecarlo?"))
    assert r["respuesta"]
