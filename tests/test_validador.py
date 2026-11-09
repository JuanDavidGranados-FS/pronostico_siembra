import copy

from src.aplicacion.validador import ErrorValidacion, Validador
from src.dominio.entidades import Cultivo, datos_por_defecto

V = Validador()


def test_datos_por_defecto_validos():
    assert V.validar_datos_entrada(datos_por_defecto()) == []


def test_deterministas():
    d = datos_por_defecto().deterministas
    assert V.validar_deterministas({**d, "fecha": "31/12/2026"})
    assert V.validar_deterministas({**d, "ph": 15})
    assert V.validar_deterministas({**d, "agua": None})
    assert V.validar_deterministas({**d, "potasio": True})


def test_estocasticos():
    e = datos_por_defecto().estocasticos
    assert V.validar_estocasticos({}) and len(V.validar_estocasticos({})) == 3
    m = copy.deepcopy(e); m["temperatura"]["tipo"] = "beta"; assert V.validar_estocasticos(m)
    m = copy.deepcopy(e); m["temperatura"]["parametros"]["std"] = -1; assert V.validar_estocasticos(m)
    m = copy.deepcopy(e); del m["temperatura"]["parametros"]["media"]; assert V.validar_estocasticos(m)
    m = copy.deepcopy(e); m["humedad"]["parametros"] = {"min": 9, "max": 1}; assert V.validar_estocasticos(m)
    m = copy.deepcopy(e); m["lluvia"]["parametros"]["moda"] = 99; assert V.validar_estocasticos(m)
    m = copy.deepcopy(e); m["lluvia"]["dia_pico"] = "x"; assert V.validar_estocasticos(m)
    m = copy.deepcopy(e); m["temperatura"] = 5; assert V.validar_estocasticos(m)


def test_estado():
    s = datos_por_defecto().estado
    assert V.validar_estado({})
    m = copy.deepcopy(s); m["salud"]["matriz"][0] = [0.5, 0.1, 0.1, 0.1]; assert V.validar_estado(m)
    m = copy.deepcopy(s); m["salud"]["estado_inicial"] = "X"; assert V.validar_estado(m)


def test_cultivo_pesos_y_parametros():
    assert V.validar_cultivo(Cultivo("", 3, 30, 10, 0, 200, -1))
    assert V.validar_pesos({"agua": 101, "ph": "x"}) and not V.validar_pesos({"agua": 0})
    d = datos_por_defecto()
    d.iteraciones, d.ventana_dias, d.paso_dias, d.esfuerzo = 5, 0, 0, -1
    assert len(V.validar_datos_entrada(d)) >= 4
    d = datos_por_defecto(); d.ventana_dias, d.paso_dias = 730, 1
    assert V.validar_datos_entrada(d)


def test_error_validacion():
    e = ErrorValidacion(["a", "b"])
    assert e.errores == ["a", "b"] and "a; b" in str(e)
