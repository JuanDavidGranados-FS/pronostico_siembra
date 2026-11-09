import numpy as np
import pytest

from src.dominio.markov import CadenaMarkov

E = ["A", "B"]
P = [[0.9, 0.1], [0.5, 0.5]]


def test_validaciones():
    with pytest.raises(ValueError): CadenaMarkov([], [])
    with pytest.raises(ValueError): CadenaMarkov(["A", "A"], P)
    with pytest.raises(ValueError): CadenaMarkov(E, [[1, 0, 0], [0, 1, 0]])
    with pytest.raises(ValueError): CadenaMarkov(E, [[0.5, 0.4], [0.5, 0.5]])
    with pytest.raises(ValueError): CadenaMarkov(E, [[1.5, -0.5], [0.5, 0.5]])
    with pytest.raises(ValueError): CadenaMarkov(E, [[1, 0], [0]])
    with pytest.raises(ValueError): CadenaMarkov(E, [["x", 0], [0, 1]])


def test_probabilidad_estado():
    c = CadenaMarkov(E, P)
    assert c.probabilidad_estado("A", 0) == {"A": 1.0, "B": 0.0}
    r = c.probabilidad_estado("A", 1)
    assert r["A"] == pytest.approx(0.9) and sum(r.values()) == pytest.approx(1)
    with pytest.raises(ValueError): c.probabilidad_estado("Z", 1)
    with pytest.raises(ValueError): c.probabilidad_estado("A", -1)


def test_estacionaria():
    pi = CadenaMarkov(E, P).distribucion_estacionaria()
    assert pi["A"] == pytest.approx(5 / 6, abs=1e-6)
    absorbente = CadenaMarkov(["S", "M"], [[0.5, 0.5], [0, 1]]).distribucion_estacionaria()
    assert absorbente["M"] == pytest.approx(1.0, abs=1e-6)


def test_trayectoria_reproducible():
    c = CadenaMarkov(E, P)
    t1, t2 = c.simular_trayectoria(20, semilla=1), c.simular_trayectoria(20, semilla=1)
    assert t1 == t2 and len(t1) == 21
    assert c.simular_trayectoria(3, semilla=1, estado_inicial="B")[0] == "B"
    with pytest.raises(ValueError): c.simular_trayectoria(-1)


def test_evolucion_forma():
    assert CadenaMarkov(E, P).evolucion("A", 5).shape == (6, 2)
