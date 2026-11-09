"""Casos límite del dominio y de la infraestructura ligera."""
import logging

import numpy as np
import pytest

from src.dominio import galton_watson as gw, poisson as po
from src.infraestructura import logger as lg


def test_poisson_limites():
    assert po.probabilidad(0, 0) == 1.0 and po.probabilidad(0, 3) == 0.0
    for args in ((-1, 0), (1, -1), (1, 0.5), (float("nan"), 0)):
        with pytest.raises(ValueError):
            po.probabilidad(*args)
    with pytest.raises(ValueError):
        po.distribucion(1, -1)
    assert po.perdida_esperada(1.0, 0.1) == pytest.approx(1 - np.exp(-0.1))
    for fn, a in ((po.perdida_esperada, (1.0, 2)), (po.factor_rendimiento, ([1], 2))):
        with pytest.raises(ValueError):
            fn(*a)
    assert po.factor_rendimiento([0, 1], 0.1).tolist() == pytest.approx([1.0, 0.9])


def test_galton_watson_validaciones_y_clasificacion():
    for kw in ({"media_descendientes": -1}, {"media_descendientes": 1, "plantas_iniciales": 0},
               {"media_descendientes": 1, "plantas_iniciales": 10, "capacidad": 5}, {"media_descendientes": 1, "agotamiento": 1.0}):
        with pytest.raises(ValueError):
            gw.ProcesoGaltonWatson(**kw)
    assert "crítico" in gw.clasificar(1.0) and "extingue" in gw.clasificar(0.5) and "crece" in gw.clasificar(2.0)
    with pytest.raises(ValueError):
        gw.probabilidad_extincion(-1)
    p = gw.ProcesoGaltonWatson(2.0, 10, 100, 0.1)
    assert p.media_temporada(1) == pytest.approx(1.8)
    assert 0 <= p.probabilidad_extincion_largo_plazo() < 1


def test_logger_configura_archivo(tmp_path):
    raiz = logging.getLogger()
    previo, manejadores = getattr(raiz, "_siembra_configurado", False), list(raiz.handlers)
    raiz._siembra_configurado = False
    try:
        lg.configurar_logger(archivo=str(tmp_path / "logs" / "app.log"))
        assert lg.configurar_logger() is raiz  # idempotente
        logging.getLogger("x").warning("hola")
        assert (tmp_path / "logs" / "app.log").exists()
        raiz._siembra_configurado = False
        lg.configurar_logger(archivo="/proc/no/puede/app.log")
    finally:
        for h in list(raiz.handlers):
            if h not in manejadores:
                raiz.removeHandler(h)
        raiz._siembra_configurado = previo
