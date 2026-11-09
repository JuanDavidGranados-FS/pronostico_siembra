"""Asistente sin internet, editor de matrices, CV-05 (extinción) y CV-06 (Poisson)."""
import math

import pytest

from src.aplicacion import asistente
from src.dominio import matrices as mx
from src.dominio.galton_watson import ProcesoGaltonWatson, probabilidad_extincion
from src.dominio.poisson import distribucion, probabilidad


def test_cv05_media_menor_que_uno_se_extingue():
    assert probabilidad_extincion(0.8) == pytest.approx(1.0)
    pr = ProcesoGaltonWatson(media_descendientes=0.8, plantas_iniciales=50, capacidad=1000, agotamiento=0.0)
    assert pr.probabilidad_extincion_largo_plazo() == pytest.approx(1.0)


def test_cv05_supercritico_puede_sobrevivir():
    assert probabilidad_extincion(2.5) < 0.2


def test_cv06_poisson_lambda_1_5():
    assert probabilidad(1.5, 0) == pytest.approx(math.exp(-1.5))
    assert round(probabilidad(1.5, 0) * 100) == 22
    d = distribucion(1.5)
    assert set(d) == {"0", "1", "2", "3+"} and sum(d.values()) == pytest.approx(1.0)


@pytest.mark.parametrize("q,tema", [("¿Qué es Poisson?", "Distribución de Poisson"), ("que es el factor de relebancia", "Factor de Relevancia"),
                                    ("¿Qué significa no viable?", "Probabilidad de éxito"), ("como exporto a pdf", "Exportar")])
def test_asistente_encuentra_el_tema(q, tema):
    assert asistente.responder(q)["tema"] == tema


def test_asistente_sin_coincidencia_ofrece_sugerencias():
    r = asistente.responder("xyzzy")
    assert r["tema"] is None and r["sugerencias"]


def test_asistente_responde_sobre_el_resultado_en_pantalla():
    ctx = {"resultado": {"justificacion": "Siembra el 14 de julio.", "justificacion_detalle": ["a", "b"]}}
    r = asistente.responder("¿Por qué esta fecha?", ctx)
    assert r["respuesta"] == "Siembra el 14 de julio." and r["mas"] == "a b"


def test_asistente_riesgos_del_resultado():
    ctx = {"resultado": {"riesgos": [{"etiqueta": "Plagas", "perdida_esperada": 0.13}]}}
    assert "13 %" in asistente.responder("¿qué riesgos tengo?", ctx)["respuesta"]


def test_glosario_y_faq():
    g = asistente.glosario()
    assert len(g) >= 10 and g == sorted(g, key=lambda f: asistente._norm(f[0]))
    assert len(asistente.PREGUNTAS_FRECUENTES) >= 5


def test_matrices_normalizar_agregar_quitar():
    m = mx.normalizar_filas([[2, 2], [0, 0]])
    assert m == [[0.5, 0.5], [0.0, 1.0]] and mx.filas_invalidas(m) == []
    est, m2 = mx.agregar_estado(["A", "B"], m, "C")
    assert est == ["A", "B", "C"] and m2[2] == [0, 0, 1] and mx.filas_invalidas(m2) == []
    est3, m3 = mx.quitar_estado(est, m2, "C")
    assert est3 == ["A", "B"] and mx.filas_invalidas(m3) == []
    assert mx.filas_invalidas([[0.5, 0.2], [0, 1]]) == [0]


def test_matrices_errores():
    with pytest.raises(ValueError):
        mx.agregar_estado(["A", "B"], [[1, 0], [0, 1]], "A")
    with pytest.raises(ValueError):
        mx.quitar_estado(["A", "B"], [[1, 0], [0, 1]], "A")
    with pytest.raises(ValueError):
        mx.quitar_estado(["A", "B", "C"], [[1, 0, 0]] * 3, "Z")
