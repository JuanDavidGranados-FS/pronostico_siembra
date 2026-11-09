"""Páginas de la aplicación (una a la vez en pantalla)."""
from src.presentacion.paginas.ayuda import PaginaAyuda
from src.presentacion.paginas.datos import PaginaDatos
from src.presentacion.paginas.historial import PaginaHistorial
from src.presentacion.paginas.inicio import PaginaInicio
from src.presentacion.paginas.relevancia import PaginaRelevancia
from src.presentacion.paginas.resultados import PaginaResultados
from src.presentacion.paginas.simulacion import PaginaSimulacion

PAGINAS = {"inicio": PaginaInicio, "datos": PaginaDatos, "relevancia": PaginaRelevancia, "simulacion": PaginaSimulacion,
           "resultados": PaginaResultados, "historial": PaginaHistorial, "ayuda": PaginaAyuda}
