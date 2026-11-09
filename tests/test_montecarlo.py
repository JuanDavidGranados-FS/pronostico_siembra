import numpy as np
import pytest

from src.dominio.montecarlo import SimuladorMontecarlo

D = {"t": {"tipo": "normal", "parametros": {"media": 20, "std": 2}},
     "u": {"tipo": "uniforme", "parametros": {"min": 0, "max": 1}},
     "tr": {"tipo": "triangular", "parametros": {"min": 0, "moda": 1, "max": 4}}}


def test_forma_y_reproducibilidad():
    a = SimuladorMontecarlo(500, 7).generar_escenarios(D, 10)
    b = SimuladorMontecarlo(500, 7).generar_escenarios(D, 10)
    assert a.shape == (500, 10, 3) and np.array_equal(a, b)
    assert not np.array_equal(a, SimuladorMontecarlo(500, 8).generar_escenarios(D, 10))


def test_distribuciones_estadisticas():
    e = SimuladorMontecarlo(20000, 1).generar_escenarios(D, 5)
    assert e[:, :, 0].mean() == pytest.approx(20, abs=0.1)
    assert 0 <= e[:, :, 1].min() and e[:, :, 1].max() <= 1
    assert e[:, :, 2].mean() == pytest.approx(5 / 3, abs=0.05)


def test_desplazamiento_y_limites():
    d = {"x": {"tipo": "uniforme", "parametros": {"min": 0, "max": 0}, "desplazamiento": [1, 2, 3], "limites": [0, 2]}}
    e = SimuladorMontecarlo(10, 1).generar_escenarios(d, 3)
    assert list(e[0, :, 0]) == [1, 2, 2]
    with pytest.raises(ValueError):
        SimuladorMontecarlo(10, 1).generar_escenarios({"x": {**d["x"], "desplazamiento": [1]}}, 3)


def test_triangular_degenerada():
    d = {"x": {"tipo": "triangular", "parametros": {"min": 2, "moda": 2, "max": 2}}}
    assert (SimuladorMontecarlo(5, 1).generar_escenarios(d, 2) == 2).all()


def test_perfil_estacional():
    p = SimuladorMontecarlo.perfil_estacional(100, 3, 5.0, 100)
    assert p[0] == pytest.approx(5.0) and p.shape == (3,)


@pytest.mark.parametrize("dist", [
    {"tipo": "normal", "parametros": {"media": 0, "std": -1}},
    {"tipo": "normal", "parametros": {"media": 0}},
    {"tipo": "uniforme", "parametros": {"min": 2, "max": 1}},
    {"tipo": "triangular", "parametros": {"min": 0, "moda": 5, "max": 1}},
    {"tipo": "beta", "parametros": {}},
])
def test_distribuciones_invalidas(dist):
    with pytest.raises(ValueError):
        SimuladorMontecarlo(5, 1).generar_escenarios({"x": dist}, 2)


def test_parametros_invalidos():
    with pytest.raises(ValueError): SimuladorMontecarlo(0)
    with pytest.raises(ValueError): SimuladorMontecarlo(5).generar_escenarios(D, 0)
    with pytest.raises(ValueError): SimuladorMontecarlo(5).generar_escenarios({}, 3)


def test_calcular_rendimiento():
    esc = SimuladorMontecarlo(1000, 3).generar_escenarios(D, 4)
    r = SimuladorMontecarlo.calcular_rendimiento(esc, lambda e: e[:, :, 0].mean(axis=1))
    assert r["p10"] < r["p50"] < r["p90"] and r["media"] == pytest.approx(20, abs=0.5)
    with pytest.raises(ValueError):
        SimuladorMontecarlo.calcular_rendimiento(esc, lambda e: e)
