"""Pruebas de humo de la interfaz (requieren pantalla; se omiten si no hay Tk o display)."""
import json
import os
import time

import pytest

tk = pytest.importorskip("tkinter")


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SIEMBRA_HOME", str(tmp_path))
    try:
        from main import construir_contexto
        from src.infraestructura.preferencias import Preferencias
        from src.presentacion.main_window import VentanaPrincipal
        pref = Preferencias(str(tmp_path))
        pref.guardar("tour_visto", True)
        ctx = construir_contexto(True, pref, str(tmp_path / "entrada"))
        os.makedirs(ctx.carpeta_entrada, exist_ok=True)
        w = VentanaPrincipal(ctx)
    except tk.TclError:
        pytest.skip("sin pantalla")
    yield w
    w.destroy()


def esperar(w, cond, seg=60):
    t = time.time()
    while not cond() and time.time() - t < seg:
        w.update()
        time.sleep(0.03)
    return cond()


def test_todas_las_paginas_abren_y_cambian_de_tema(app):
    for k in ("inicio", "datos", "relevancia", "simulacion", "resultados", "historial", "ayuda"):
        app.ir(k)
        assert app.pagina_actual == k
    app.cambiar_tema()
    assert app.p.oscuro and app.pagina_actual == "ayuda"


def test_flujo_completo_y_exportar(app, tmp_path):
    app.ir("datos")
    app.paginas["datos"].sec["estado"].abrir()
    app.datos.iteraciones, app.datos.semilla = 400, 1
    app.datos.plan["temporadas"] = 3
    app.ejecutar()
    assert esperar(app, lambda: app.resultado is not None)
    pg = app.paginas["resultados"]
    for v in ("graficas", "comparacion", "riesgos", "temporadas", "exportar"):
        pg.seg.elegir(v)
    for ext in (".pdf", ".xlsx", ".csv", ".json", ".png"):
        ruta = tmp_path / f"r{ext}"
        pg.exportar(ext, str(ruta))
        assert ruta.stat().st_size > 0
    app.ir("historial")
    assert len(app.paginas["historial"].t.get_children()) == 1


def test_datos_invalidos_no_ejecutan(app):
    app.ir("datos")
    app.paginas["datos"].vars["d_ph"].set("abc")
    app.ejecutar()
    assert not app.ejecutando and app.pagina_actual == "datos"


def test_matriz_con_fila_invalida_bloquea(app):
    app.ir("datos")
    pg = app.paginas["datos"]
    pg.mk_entradas["m"][0][0].set("0.5")
    assert pg.volcar()


def test_json_valido_e_invalido_y_semaforo(app, tmp_path):
    from src.dominio.entidades import datos_por_defecto
    ok = tmp_path / "ok.json"
    ok.write_text(json.dumps(datos_por_defecto().a_dict()), encoding="utf-8")
    assert app.recibir_json(str(ok)) and app.semaforo.estado == "conectado"
    mal = tmp_path / "mal.json"
    mal.write_text("{no es json", encoding="utf-8")
    assert not app.recibir_json(str(mal)) and app.semaforo.estado == "error"
    assert [r["valido"] for r in app.registro_json] == [False, True]


def test_semaforo_amarillo_tras_cinco_minutos(app):
    from datetime import datetime, timedelta
    app.semaforo.actualizar("conectado", datetime.now() - timedelta(minutes=6))
    app.semaforo._vigilar()
    assert app.semaforo.estado == "sin_datos"


def test_carpeta_de_entrada_se_vigila(app):
    ruta = os.path.join(app.ctx.carpeta_entrada, "a.json")
    from src.dominio.entidades import datos_por_defecto
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos_por_defecto().a_dict(), f)
    app._vigilar_carpeta()
    assert app.semaforo.estado == "conectado"


def test_asistente_y_perfiles(app):
    app.preguntar("¿Qué es Montecarlo?")
    assert app.asistente_visible and "Montecarlo" in app.asistente.chat.get("1.0", "end")
    app.ir("relevancia")
    pg = app.paginas["relevancia"]
    pg.sl["agua"].poner(90)
    pg.v_nombre.set("mi perfil")
    pg._guardar()
    assert len(app.ctx.relevancia.listar()) == 1
    pg.lista.selection_set(pg.lista.get_children()[0])
    pg.sl["agua"].poner(10)
    pg._cargar()
    assert pg.sl["agua"].obtener() == 90
    pg._m_minimo(pg._limpiar(), app.p)


def test_reutilizar_configuracion_desde_historial(app):
    app.datos.iteraciones, app.datos.nombre = 300, "otra"
    app.ejecutar()
    assert esperar(app, lambda: app.resultado is not None)
    app.ir("historial")
    h = app.paginas["historial"]
    h.t.selection_set(h.t.get_children()[0])
    h._reutilizar()
    assert app.datos.nombre == "otra"


def _con_resultado(app):
    app.datos.iteraciones = 300
    app.ejecutar()
    assert esperar(app, lambda: app.resultado is not None)


def test_ayuda_secciones_y_tour(app):
    from src.presentacion.tour import PASOS, Tour
    app.ir("ayuda")
    pg = app.paginas["ayuda"]
    for k in ("recorrido", "glosario", "faq", "integracion"):
        pg.abrir(k)
    assert "Guía de integración" in pg.zona.winfo_children()[0].get("1.0", "end")
    pg.abrir("glosario")
    t = Tour(app)
    t.iniciar()
    for _ in range(len(PASOS)):
        t._siguiente()
    assert app.ctx.preferencias.obtener("tour_visto") and app.pagina_actual == "inicio"


def test_inicio_acciones_y_registro(app, tmp_path):
    app.ir("inicio")
    pg = app.paginas["inicio"]
    for ident in ("cargar_cultivos", "crear_relevancia"):
        pg._accion(ident)
    app.cargar_json = lambda ruta=None: None
    pg._accion("cargar_json")
    app.recibir_json(str(tmp_path / "no_existe.json"))
    assert pg.tabla.get_children() and app.semaforo.estado == "error"
    app.mostrar_registro()
    assert pg.s_json.abierta


def test_datos_editor_de_matrices_y_clima(app):
    app.ir("datos")
    pg = app.paginas["datos"]
    pg.sec["estado"].abrir()
    ch = app.datos.estado["salud"]
    from src.dominio import matrices as mx
    ch["estados"], ch["matriz"] = mx.agregar_estado(ch["estados"], ch["matriz"], "Latente")
    ch["rendimiento_por_estado"]["Latente"] = 0.5
    pg._pintar_matriz()
    pg._quitar()
    assert "Latente" not in ch["estados"]
    pg.mk_entradas["m"][0][0].set("0.5")
    pg._normalizar()
    assert abs(sum(ch["matriz"][0]) - 1) < 1e-9
    pg._guardar_matriz()
    pg._cambiar_cadena("enfermedad")
    pg._guardar_matriz()
    pg._cargar_matriz()
    pg._cambiar_cadena("crecimiento")
    pg._cargar_matriz()
    pg.clima_vars["humedad"].set("triangular")
    pg._params_clima("humedad")
    assert not pg.volcar() and app.datos.estocasticos["humedad"]["tipo"] == "triangular"
    pg.var_cultivo.set(next(iter(pg.cultivos)))
    pg._elegir_cultivo()
    pg.refrescar()


def test_relevancia_metodos(app, tmp_path):
    from tkinter import filedialog
    app.ir("relevancia")
    pg = app.paginas["relevancia"]
    pg._metodo("manual")
    pg._poner({"agua": 33}, "Prueba")
    assert app.datos.pesos["agua"] == 33
    pg._m_manual(pg._limpiar(), app.p)
    pg._metodo("minimo")
    pg._metodo("experto")
    pg._calc_experto(app.p)
    for k, v in pg.cmp.items():
        v.set("a es mucho más importante" if k[0] == "agua" else "b es mucho más importante")
    pg._calc_experto(app.p)
    ruta = tmp_path / "h.csv"
    ruta.write_text("agua,rendimiento\n" + "\n".join(f"{i},{i * 2}" for i in range(1, 15)))
    pg._metodo("historico")
    filedialog.askopenfilename = lambda **k: str(ruta)
    pg._leer(pg.panel, app.p)
    ruta.write_text("foo,bar\n1,2\n")
    pg._leer(pg.panel, app.p)
    filedialog.askopenfilename = lambda **k: str(tmp_path / "x.txt")
    pg._leer(pg.panel, app.p)
    pg._metodo("campo")
    pg.v_var.set("agua")
    pg._calc_campo(app.p)
    for i in range(6):
        pg.rv["temporada"].set("A")
        pg.rv["valor"].set(str(i + 1))
        pg.rv["rendimiento"].set(str(i + 2))
        pg._anotar()
    pg._anotar()
    pg._calc_campo(app.p)
    pg._sel()
    pg.v_nombre.set("p1")
    pg._guardar()
    pg.lista.selection_set(pg.lista.get_children()[0])
    pg._duplicar()
    destino = tmp_path / "perfil.json"
    filedialog.asksaveasfilename = lambda **k: str(destino)
    pg._exportar()
    filedialog.askopenfilename = lambda **k: str(destino)
    pg._importar()
    pg.lista.selection_set(pg.lista.get_children()[0])
    pg._eliminar()
    filedialog.askopenfilename = lambda **k: str(tmp_path / "nada.json")
    pg._importar()


def test_historial_acciones(app, monkeypatch):
    from tkinter import simpledialog
    _con_resultado(app)
    app.datos.nombre = "segunda"
    app.resultado = None
    app.ejecutar()
    assert esperar(app, lambda: app.resultado is not None)
    app.ir("historial")
    h = app.paginas["historial"]
    ids = h.t.get_children()
    assert len(ids) == 2
    h.v_texto.set("segunda")
    h.al_mostrar()
    assert len(h.t.get_children()) == 1
    h.v_texto.set("zzz")
    h.al_mostrar()
    assert h.vacio.cget("text")
    h.v_texto.set("")
    h.al_mostrar()
    h.t.selection_set(ids[0])
    monkeypatch.setattr(simpledialog, "askstring", lambda *a, **k: "Renombrada")
    h._renombrar()
    h._abrir()
    assert app.resultado and app.pagina_actual == "resultados"
    app.ir("historial")
    h = app.paginas["historial"]
    h.t.selection_set(ids)
    h._abrir()
    h._renombrar()
    h._eliminar()
    h._reutilizar()
    h.t.selection_set(ids[0])
    h._comparar()
    h.t.selection_set(ids)
    h.t.selection_set(ids[0])
    h._eliminar()
    assert len(h.t.get_children()) == 1


def test_comparacion_ventana(app):
    _con_resultado(app)
    app.ejecutar()
    assert esperar(app, lambda: not app.ejecutando)
    app.ir("historial")
    h = app.paginas["historial"]
    h.t.selection_set(h.t.get_children())
    h._comparar()


def test_resultados_detalle_y_errores(app, tmp_path):
    from tkinter import filedialog
    app.ir("resultados")
    assert "Ejecuta una simulación" in str([w.cget("text") for w in app.paginas["resultados"].winfo_children() if hasattr(w, "cget") and "text" in w.keys()])
    _con_resultado(app)
    pg = app.paginas["resultados"]
    pg._alternar_detalle()
    pg._alternar_detalle()
    filedialog.asksaveasfilename = lambda **k: ""
    pg.exportar(".pdf")
    pg.exportar(".pdf", str(tmp_path / "no_existe" / "x.pdf"))
    app.aviso("probando", "aviso")
    app.aviso("probando", "error")


def test_ejecutar_con_error_inesperado_y_dos_veces(app, monkeypatch):
    app.ir("simulacion")
    monkeypatch.setattr(app.ctx.orquestador, "ejecutar_simulacion", lambda *a, **k: 1 / 0)
    app.ejecutar()
    app.ejecutar()  # ignorado mientras corre
    assert esperar(app, lambda: not app.ejecutando)
    assert app.resultado is None


def test_simulacion_ajustes_y_validacion(app):
    app.ir("simulacion")
    pg = app.paginas["simulacion"]
    pg.vars["iteraciones"].set("500")
    pg.vars["semilla"].set("7")
    pg.vars["nombre"].set("Mi prueba")
    pg.vars["esfuerzo"].set("x")
    assert pg.volcar()
    pg.vars["esfuerzo"].set("1,5")
    assert not pg.volcar() and app.datos.esfuerzo == 1.5 and app.datos.semilla == 7
    app.ir("datos")
    app.ir("simulacion")


def test_preferencia_tema_y_semaforo_clic(app):
    app.cambiar_tema()
    app.cambiar_tema()
    assert not app.p.oscuro
    app.alternar_asistente()
    app.asistente.var.set("riesgo")
    app.asistente.enviar()
    app.asistente._ver_mas("detalle")
    app.alternar_asistente()
    app.semaforo.actualizar("sin_datos")
    assert "Sin datos" in app.semaforo._texto.cget("text")


def test_widgets_basicos(app):
    from src.presentacion.widgets.base import Boton, Deslizador, Metrica, Pastilla, Tooltip
    p = app.p
    llamadas = []
    b = Boton(app.zona, p, "x", lambda: llamadas.append(1), "peligro")
    b.pack()
    for v in ("primario", "fantasma", "secundario", "peligro"):
        b.variante = v
        b._estado(True)
        b._estado(False)
    b._clic()
    b.activar(False)
    b._clic()
    b.poner_texto("y")
    assert llamadas == [1]
    for tono in ("ok", "aviso", "error", "info", "neutro"):
        Pastilla(app.zona, p, "t", tono)
    tt = Tooltip(b, "ayuda", p)
    tt._mostrar()
    tt._mostrar()
    tt._ocultar()
    d = Deslizador(app.zona, p, "x", 5, "ayuda")
    d.poner(40)
    assert d.obtener() == 40
    Metrica(app.zona, p, "a", "1", "n", "ay")
