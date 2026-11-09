from datetime import date

import numpy as np
import pytest

from src.dominio.factor_relevancia import FactorRelevancia
from src.dominio.kpi import calcular_kpi, encontrar_fecha_optima

R = {"agua": (0, 5, 10), "ph": (4, 6.5, 9)}


def test_pesos_validos():
    for malo in (-1, 101, "x", True):
        with pytest.raises(ValueError): FactorRelevancia({"agua": malo})
    with pytest.raises(ValueError): FactorRelevancia({}, peso_por_defecto=200)
    with pytest.raises(ValueError): FactorRelevancia({}, {"agua": (5, 5, 10)})


def test_normalizar():
    fr = FactorRelevancia({}, R)
    assert fr.normalizar("agua", 5) == 1.0 and fr.normalizar("agua", 0) == 0.0
    assert fr.normalizar("agua", 2.5) == pytest.approx(0.5) and fr.normalizar("agua", 99) == 0.0
    assert list(fr.normalizar("agua", np.array([0, 5, 10]))) == [0, 1, 0]
    with pytest.raises(KeyError): fr.normalizar("otro", 1)


def test_kpi_ponderado():
    fr = FactorRelevancia({"agua": 100, "ph": 0}, R)
    assert fr.calcular_kpi_ponderado({"agua": 0.2, "ph": 1.0}) == pytest.approx(0.2)
    fr2 = FactorRelevancia({"agua": 100, "ph": 100}, R)
    assert fr2.calcular_kpi_ponderado({"agua": 0.2, "ph": 1.0}) == pytest.approx(0.6)
    assert FactorRelevancia({"agua": 0}, R).calcular_kpi_ponderado({"agua": 0.3}) == 1.0
    assert FactorRelevancia({}, R).peso("x") == 50
    arr = fr2.calcular_kpi_ponderado({"agua": np.array([0.0, 1.0]), "ph": 1.0})
    assert list(arr) == [0.5, 1.0]


def test_kpi():
    assert calcular_kpi(10, 0.5, 1) == 2.5
    with pytest.raises(ValueError): calcular_kpi(1, 1, -1)


def test_fecha_optima():
    r = {date(2026, 1, 1): 1.0, date(2026, 2, 1): 3.0, date(2026, 3, 1): 3.0}
    assert encontrar_fecha_optima(r) == (date(2026, 2, 1), 3.0)
    with pytest.raises(ValueError): encontrar_fecha_optima({})
