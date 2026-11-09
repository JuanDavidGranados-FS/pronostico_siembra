/* Siembra web · réplica de la interfaz de escritorio (src/presentacion) que habla con el motor en Python
   (motor.worker.js + web/motor.py). Cada página y cada widget llevan el mismo nombre que en la versión de escritorio. */
"use strict";

/* ====================================================================== utilidades */
const $ = (s, r = document) => r.querySelector(s);
function h(tag, props, ...hijos) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style") el.style.cssText = v;
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (k in el && !["list", "form"].includes(k)) el[k] = v;
    else el.setAttribute(k, v);
  }
  for (const c of hijos.flat(Infinity)) if (c != null && c !== false) el.append(c instanceof Node ? c : String(c));
  return el;
}
const limpiar = (el) => { el.replaceChildren(); return el; };
const esMovil = () => matchMedia("(max-width: 899px)").matches;
const oscuro = () => document.documentElement.dataset.tema === "oscuro";
const copia = (x) => JSON.parse(JSON.stringify(x));
function numero(t) {
  const s = String(t ?? "").trim().replace(",", ".");
  if (s === "") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}
const g = (v) => (v == null || v === "" ? "" : Number.isInteger(+v) ? String(+v) : String(+(+v).toPrecision(6)));
const f2 = (v) => (+v).toFixed(2), f1 = (v) => (+v).toFixed(1), f0 = (v) => (+v).toFixed(0);
const pct = (p) => `${(p * 100).toFixed(0)} %`;

/* ====================================================================== motor (Python en el navegador) */
const worker = new Worker("motor.worker.js");
const pendientes = new Map();
let sigId = 1;

function pedir(tipo, datos = {}, alProgreso = null, transfer = []) {
  const id = sigId++;
  return new Promise((resolver) => {
    pendientes.set(id, { resolver, alProgreso });
    worker.postMessage({ tipo, id, ...datos }, transfer);
  });
}
async function llamar(funcion, args = [], opciones = {}) {
  const r = await pedir("llamar", { funcion, args, necesita: opciones.necesita || [], guardar: !!opciones.guardar });
  if (!r.ok) throw new Error(r.error);
  return r.valor;
}
worker.onmessage = (e) => {
  const m = e.data;
  if (m.tipo === "estado") {
    $("#carga-texto").textContent = m.texto;
    $("#carga-barra").style.width = `${m.avance}%`;
  } else if (m.tipo === "listo") {
    arrancar(m.inicio);
  } else if (m.tipo === "fallo") {
    $("#carga-texto").textContent = `No se pudo cargar el motor: ${m.texto}. Revisa tu conexión a internet y recarga la página.`;
  } else if (m.tipo === "guardado") {
    try { localStorage.setItem("siembra-datos", m.datos); } catch (err) { /* sin espacio: se sigue en memoria */ }
  } else if (m.tipo === "progreso" || m.tipo === "ocupado") {
    const p = pendientes.get(m.id);
    if (p && p.alProgreso) p.alProgreso(m);
  } else if (m.tipo === "respuesta") {
    const p = pendientes.get(m.id);
    if (p) { pendientes.delete(m.id); p.resolver(m); }
  }
};
worker.onerror = (e) => { $("#carga-texto").textContent = `Error al iniciar: ${e.message || "desconocido"}. Recarga la página.`; };
let guardado = "";
try { guardado = localStorage.getItem("siembra-datos") || ""; } catch (err) { guardado = ""; }
worker.postMessage({ tipo: "iniciar", guardado });

/* ====================================================================== estado de la aplicación */
const NAV = [["inicio", "Inicio"], ["datos", "Datos"], ["relevancia", "Relevancia"], ["simulacion", "Simulación"],
             ["resultados", "Resultados"], ["historial", "Historial"], ["ayuda", "Ayuda"]];
const app = {
  ini: null, datos: null, cultivos: [], pesosOrigen: "Valores sugeridos", resultado: null, ejecutando: false,
  pagina: "inicio", paginas: {}, errores: new Map(), registroJson: [], asistenteVisible: false,
};
const pref = {
  obtener(k, d) { try { const v = localStorage.getItem("siembra-" + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  guardar(k, v) { try { localStorage.setItem("siembra-" + k, JSON.stringify(v)); } catch (e) { /* nada */ } },
};

/* ====================================================================== widgets (widgets/base.py) */
function Boton(texto, comando, variante = "secundario", { tam = 11, ancho } = {}) {
  return h("button", { type: "button", class: `boton ${variante}${tam < 11 ? " t10" : ""}`, onclick: () => comando && comando(),
    style: ancho ? `min-width:${ancho}px` : null }, texto);
}
function Pastilla(texto, tono = "neutro") { return h("span", { class: `pastilla ${tono}` }, texto); }
function Tarjeta(relleno = 20) {
  const cuerpo = h("div", { class: "cuerpo-t", style: `padding:${relleno}px` });
  return { el: h("div", { class: "tarjeta" }, cuerpo), cuerpo };
}
let globo = null;
function mostrarGlobo(ancla, texto) {
  ocultarGlobo();
  const r = ancla.getBoundingClientRect();
  globo = h("div", { class: "globo" }, texto);
  document.body.append(globo);
  const ancho = globo.offsetWidth;
  globo.style.left = `${Math.max(8, Math.min(r.left + 12, innerWidth - ancho - 8))}px`;
  globo.style.top = `${r.bottom + 6}px`;
}
function ocultarGlobo() { if (globo) { globo.remove(); globo = null; } }
function Tooltip(el, texto) {
  if (!texto) return;
  el.addEventListener("mouseenter", () => !esMovil() && mostrarGlobo(el, texto));
  el.addEventListener("mouseleave", ocultarGlobo);
  el.addEventListener("focus", () => !esMovil() && mostrarGlobo(el, texto));
  el.addEventListener("blur", ocultarGlobo);
}
function AyudaBoton(texto, alPreguntar) {
  const b = h("button", { type: "button", class: "ayuda", "aria-label": "Ayuda: " + texto }, "?");
  Tooltip(b, texto);
  b.addEventListener("click", (e) => {
    e.stopPropagation();
    if (alPreguntar) { ocultarGlobo(); alPreguntar(); return; }
    if (globo) { ocultarGlobo(); return; }
    mostrarGlobo(b, texto);
    setTimeout(ocultarGlobo, 5000);
  });
  return b;
}
function etiqueta(texto, tam = 11, { peso, suave, clase = "" } = {}) {
  return h("p", { class: `t${tam}${peso ? " b" : ""}${suave ? " suave" : ""} ${clase}` }, texto);
}
function encabezado(titulo, subtitulo) {
  return h("div", { class: "encabezado" }, h("h1", null, titulo), subtitulo ? h("p", null, subtitulo) : null);
}
function GrupoAcordeon() {
  const secciones = [];
  return {
    crear(titulo, opciones = {}) {
      const s = Seccion(titulo, { ...opciones, alAbrir: (x) => { secciones.forEach((o) => o !== x && o.cerrar()); opciones.alAbrir && opciones.alAbrir(x); } });
      secciones.push(s);
      return s;
    },
  };
}
function Seccion(titulo, { resumen = "", ayuda = "", alPreguntar, alAbrir } = {}) {
  const res = h("span", { class: "resumen" }, resumen);
  const cuerpo = h("div", { class: "cuerpo-s", hidden: true });
  const cab = h("div", { class: "cab", role: "button", tabindex: 0, "aria-expanded": "false" },
    h("span", { class: "flecha" }, "›"), h("span", { class: "titulo" }, titulo), ayuda ? AyudaBoton(ayuda, alPreguntar) : null, res);
  const el = h("div", { class: "seccion" }, cab, cuerpo);
  const s = {
    el, cuerpo, abierta: false,
    ponerResumen(t) { res.textContent = t; },
    abrir() { if (s.abierta) return; alAbrir && alAbrir(s); s.abierta = true; el.classList.add("abierta"); cuerpo.hidden = false; cab.setAttribute("aria-expanded", "true"); },
    cerrar() { s.abierta = false; el.classList.remove("abierta"); cuerpo.hidden = true; cab.setAttribute("aria-expanded", "false"); },
    alternar() { s.abierta ? s.cerrar() : s.abrir(); },
  };
  cab.addEventListener("click", () => s.alternar());
  cab.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); s.alternar(); } });
  return s;
}
function Segmentado(opciones, alCambiar, inicial) {
  const el = h("div", { class: "segmentado", role: "tablist" });
  const botones = {};
  const seg = {
    el, clave: null,
    elegir(clave, notificar = true) {
      seg.clave = clave;
      for (const [c, b] of Object.entries(botones)) { b.classList.toggle("sel", c === clave); b.setAttribute("aria-selected", String(c === clave)); }
      if (notificar && alCambiar) alCambiar(clave);
    },
  };
  for (const [clave, texto] of opciones) {
    botones[clave] = h("button", { type: "button", role: "tab", onclick: () => seg.elegir(clave) }, texto);
    el.append(botones[clave]);
  }
  if (inicial !== null) seg.elegir(inicial || opciones[0][0], false);
  return seg;
}
function Metrica(rotulo, valor, nota = "", ayuda = "") {
  return h("div", { class: "metrica" }, h("div", { class: "fila" }, h("span", { class: "t10 suave" }, rotulo), ayuda ? AyudaBoton(ayuda) : null),
    h("div", { class: "valor" }, valor), h("div", { class: "nota" }, nota));
}
function Deslizador(rotulo, valor, ayuda, alCambiar) {
  const salida = h("span", { class: "valor" }, f0(valor));
  const rango = h("input", { type: "range", min: 0, max: 100, step: 1, value: valor, "aria-label": rotulo });
  rango.addEventListener("input", () => { salida.textContent = f0(rango.value); alCambiar && alCambiar(); });
  return {
    el: h("div", { class: "deslizador" }, h("div", { class: "fila-d" }, h("span", null, rotulo), ayuda ? AyudaBoton(ayuda) : null, salida), rango),
    poner(v) { rango.value = v; salida.textContent = f0(v); },
    obtener() { return Math.round(+rango.value * 10) / 10; },
  };
}
/* Tabla tipo Treeview: selecciona tocando las filas. */
function Tabla(columnas, { seleccion = null, alto } = {}) {
  const cuerpo = h("tbody");
  const tabla = h("table", { class: `tabla${seleccion ? " seleccionable" : ""}` },
    h("thead", null, h("tr", null, columnas.map(([, t]) => h("th", null, t)))), cuerpo);
  const sel = new Set();
  const t = {
    el: h("div", { class: "tabla-scroll", style: alto ? `max-height:${alto}px;overflow-y:auto` : null }, tabla),
    filas(filas) {
      const previas = new Set(sel);
      sel.clear();
      limpiar(cuerpo);
      for (const f of filas) {
        const tr = h("tr", null, columnas.map(([k]) => h("td", { title: String(f[k] ?? "") }, f[k] ?? "")));
        tr.dataset.id = f.id ?? "";
        if (previas.has(tr.dataset.id)) { sel.add(tr.dataset.id); tr.classList.add("sel"); }
        if (seleccion) tr.addEventListener("click", () => {
          const id = tr.dataset.id;
          if (seleccion === "una") { sel.clear(); cuerpo.querySelectorAll("tr.sel").forEach((x) => x.classList.remove("sel")); }
          if (sel.has(id)) { sel.delete(id); tr.classList.remove("sel"); } else { sel.add(id); tr.classList.add("sel"); }
        });
        cuerpo.append(tr);
      }
    },
    seleccion() { return [...sel].map(Number); },
  };
  return t;
}
/* Campo numérico «rótulo + entrada + ?» (PaginaDatos._fila). Guarda los errores de formato como hace volcar(). */
function Campo(rotulo, clave, valor, poner, { ayuda = "", ancho = 14, entero = false, texto = false, alPreguntar } = {}) {
  const entrada = h("input", { value: texto ? (valor ?? "") : g(valor), inputmode: texto ? "text" : "decimal", style: `width:${ancho + 2}ch`, "aria-label": rotulo });
  entrada.addEventListener("input", () => {
    if (texto) { poner(entrada.value.trim()); app.errores.delete(clave); actualizarResumenes(); return; }
    const n = numero(entrada.value);
    if (n === null) app.errores.set(clave, `«${rotulo}» debe ser un número.`);
    else { app.errores.delete(clave); poner(entero ? Math.round(n) : n); }
    actualizarResumenes();
  });
  return h("div", { class: "campo-fila" }, h("span", { class: "rot" }, rotulo),
    h("span", { class: "entrada" }, entrada, ayuda ? AyudaBoton(ayuda, alPreguntar) : null));
}
let avisoId = null;
function aviso(texto, tono = "ok", ms = 4200) {
  let el = $("#aviso");
  if (!el) { el = h("div", { id: "aviso", class: "aviso", role: "status" }); document.body.append(el); }
  const c = { ok: ["var(--primario)", "var(--sobre-primario)"], error: ["var(--error)", "#fff"], aviso: ["var(--aviso)", "#1b1300"] }[tono];
  el.style.background = c[0]; el.style.color = c[1];
  el.textContent = texto; el.hidden = false;
  clearTimeout(avisoId);
  if (ms) avisoId = setTimeout(() => { el.hidden = true; }, ms);
}
function elegirArchivo(accept) {
  return new Promise((resolver) => {
    const i = h("input", { type: "file", accept, style: "display:none" });
    i.addEventListener("change", () => { resolver(i.files[0] || null); i.remove(); });
    document.body.append(i);
    i.click();
  });
}
function descargar(nombre, contenido, tipo = "application/octet-stream") {
  const url = URL.createObjectURL(new Blob([contenido], { type: tipo }));
  const a = h("a", { href: url, download: nombre, style: "display:none" });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

/* ====================================================================== ventana principal (main_window.py) */
function arrancar(ini) {
  app.ini = ini;
  app.datos = copia(ini.datos);
  app.cultivos = ini.cultivos;
  construir();
  $("#carga-barra").style.width = "100%";
  setTimeout(() => $("#carga").classList.add("oculta"), 200);
  if (!pref.obtener("tour_visto", false)) setTimeout(() => Tour.iniciar(), 700);
}

function construir() {
  const raiz = limpiar($("#app"));
  app.navEsc = Segmentado(NAV, ir, app.pagina);
  app.navMov = Segmentado(NAV, ir, app.pagina);
  app.semaforo = IndicadorConexion(() => { ir("inicio"); app.paginas.inicio && app.paginas.inicio.abrirRegistro(); });
  app.btnTema = Boton(oscuro() ? "☀" : "☾", cambiarTema, "fantasma", { ancho: 44 });
  app.btnTema.setAttribute("aria-label", "Cambiar tema claro/oscuro");
  const cabecera = h("header", { class: "cabecera" },
    h("span", { class: "logo", "aria-hidden": "true" }, "✿"), h("span", { class: "nombre" }, "Siembra"),
    h("nav", { class: "nav-escritorio", "aria-label": "Secciones" }, app.navEsc.el),
    h("div", { class: "derecha" }, app.semaforo.el, app.btnTema, Boton("✦ Preguntar", alternarAsistente, "primario")));
  app.zona = h("main", { class: "zona" });
  app.asistente = PanelAsistente();
  app.asistente.el.hidden = true;
  raiz.append(cabecera, h("nav", { class: "nav-movil", style: "padding:0 12px 6px", "aria-label": "Secciones" }, app.navMov.el),
    h("div", { class: "cuerpo" }, app.zona, app.asistente.el));
  app.paginas = {};
  mostrar(app.pagina);
}

function ir(clave, guardarHist = true) {
  if (esMovil() && app.asistenteVisible) alternarAsistente();
  mostrar(clave);
  app.navEsc.elegir(clave, false); app.navMov.elegir(clave, false);
  if (guardarHist) history.pushState({ pagina: clave }, "", `#${clave}`);
  window.scrollTo(0, 0);
}
window.addEventListener("popstate", (e) => app.ini && ir((e.state && e.state.pagina) || "inicio", false));
history.replaceState({ pagina: "inicio" }, "", location.pathname);

const PAGINAS = {};
function mostrar(clave) {
  for (const pg of Object.values(app.paginas)) pg.el.hidden = true;
  if (!app.paginas[clave]) { app.paginas[clave] = PAGINAS[clave](); app.zona.append(app.paginas[clave].el); }
  app.pagina = clave;
  const pg = app.paginas[clave];
  pg.el.hidden = false;
  if (pg.alMostrar) pg.alMostrar();
}
function rehacer(...claves) {
  for (const k of claves) if (app.paginas[k]) { app.paginas[k].el.remove(); delete app.paginas[k]; }
}
function reemplazarDatos(datos) {
  app.datos = datos;
  app.errores.clear();
  rehacer("datos", "relevancia", "simulacion");
}
function cambiarTema() {
  const t = oscuro() ? "claro" : "oscuro";
  document.documentElement.dataset.tema = t;
  document.querySelector('meta[name="theme-color"]').content = t === "oscuro" ? "#0f1613" : "#1f7a4d";
  pref.guardar("tema", t);
  try { localStorage.setItem("siembra-tema", t); } catch (e) { /* nada */ }
  app.btnTema.textContent = t === "oscuro" ? "☀" : "☾";
  const r = app.paginas.resultados;
  if (r && r.redibujar) r.redibujar();
}

function validarDatos() {
  const errores = [...app.errores.values()];
  for (const [clave, ch] of Object.entries(app.datos.estado)) {
    ch.matriz.forEach((fila, i) => {
      const s = fila.reduce((a, b) => a + b, 0);
      if (Math.abs(s - 1) > 1e-6) errores.push(`En «${CADENAS[clave] || clave}», la fila «${ch.estados[i]}» no suma 1. Usa «Normalizar filas».`);
    });
  }
  return errores;
}

async function ejecutar() {
  if (app.ejecutando) return;
  const errores = validarDatos();
  if (errores.length) { aviso(errores[0], "error"); ir("datos"); return; }
  app.ejecutando = true;
  const pg = app.paginas.simulacion;
  if (pg) pg.alIniciar();
  const r = await pedir("simular", { datos: app.datos }, (m) => {
    if (pg) pg.alProgreso(m.i, m.n);
    if (app.pagina !== "simulacion") aviso(`Simulando… fecha ${m.i} de ${m.n}`, "ok", 0);
  });
  app.ejecutando = false;
  if (pg) pg.alTerminar();
  if (r.ok) {
    app.resultado = r.valor;
    rehacer("resultados");
    if (app.paginas.historial) app.paginas.historial.alMostrar();
    ir("resultados");
    aviso("Listo: ya tienes tu recomendación.");
  } else {
    aviso(r.error, "error");
  }
}

/* ----------------------------------------------------------- semáforo (widgets/indicador_conexion.py) */
function IndicadorConexion(alClic) {
  const TEXTOS = { conectado: "Datos recibidos", sin_datos: "Sin datos recientes", error: "Último archivo inválido", espera: "Sin conexión" };
  const punto = h("span", { style: "width:10px;height:10px;border-radius:50%;display:inline-block;background:var(--suave)" });
  const texto = h("span", { class: "t10 suave nav-escritorio", style: "padding:0 6px" }, TEXTOS.espera);
  const el = h("button", { type: "button", class: "boton fantasma", style: "padding:0 6px;gap:0", onclick: alClic, title: "Estado de la conexión con un simulador o mod externo. Toca para ver el registro." }, punto, texto);
  let marca = null, estado = "espera";
  const ind = {
    el,
    actualizar(nuevo, m) {
      estado = nuevo; if (m) marca = m;
      punto.style.background = { conectado: "var(--ok)", sin_datos: "var(--aviso)", error: "var(--error)" }[estado] || "var(--suave)";
      texto.textContent = TEXTOS[estado] + (marca ? ` · ${marca.toTimeString().slice(0, 5)}` : "");
    },
  };
  setInterval(() => { if (estado === "conectado" && marca && Date.now() - marca > 5 * 60000) ind.actualizar("sin_datos"); }, 30000);
  return ind;
}

/* ====================================================================== asistente (panel_asistente.py) */
function PanelAsistente() {
  const chat = h("div", { class: "chat", "aria-live": "polite" });
  const sugs = h("div", { class: "sugs" });
  const entrada = h("input", { placeholder: "Escribe tu pregunta…", "aria-label": "Tu pregunta" });
  let ultimo = null;
  const panel = {
    el: h("aside", { class: "asistente", "aria-label": "Asistente" },
      h("div", { class: "cab-a" }, h("span", { class: "t13 b" }, "✦ Asistente"), h("span", { style: "margin-left:auto" }, Boton("✕", alternarAsistente, "fantasma", { tam: 10, ancho: 36 }))),
      h("p", { class: "intro" }, "Pregunta lo que quieras: respondo en pocas líneas y, si quieres, amplío."),
      chat, sugs,
      h("form", { class: "enviar", onsubmit: (e) => { e.preventDefault(); const t = entrada.value.trim(); if (t) { entrada.value = ""; panel.preguntar(t); } } },
        entrada, h("button", { type: "submit", class: "boton primario", style: "min-width:76px" }, "Enviar"))),
    async preguntar(texto) {
      chat.append(h("p", { class: "yo" }, texto));
      let r;
      try { r = await llamar("preguntar", [texto, app.pagina]); } catch (e) { r = { respuesta: e.message, sugerencias: [] }; }
      ultimo = r;
      if (r.tema) chat.append(h("p", { class: "tema" }, r.tema));
      chat.append(h("p", null, r.respuesta));
      chat.scrollTop = chat.scrollHeight;
      panel.sugerir(r.sugerencias, r.mas);
    },
    sugerir(lista, mas) {
      limpiar(sugs);
      if (mas) sugs.append(Boton("Ver más detalle", () => { chat.append(h("p", null, mas)); chat.scrollTop = chat.scrollHeight; panel.sugerir((ultimo || {}).sugerencias || []); }, "primario", { tam: 10 }));
      for (const s of (lista || []).slice(0, 3)) sugs.append(Boton(s, () => panel.preguntar(s), "secundario", { tam: 10 }));
    },
  };
  panel.sugerir(app.ini.sugerencias);
  return panel;
}
function alternarAsistente() {
  app.asistenteVisible = !app.asistenteVisible;
  app.asistente.el.hidden = !app.asistenteVisible;
  if (app.asistenteVisible && !esMovil()) app.asistente.el.querySelector("input").focus();
}
function preguntar(texto) {
  if (!app.asistenteVisible) alternarAsistente();
  app.asistente.preguntar(texto);
}

/* ====================================================================== recorrido (tour.py) */
const PASOS = [
  ["inicio", "Bienvenido", "Esta aplicación te dice cuándo sembrar. Aquí empiezas y ves si todo está listo."],
  ["datos", "1. Tus datos", "Elige el cultivo y revisa el suelo y el clima. Ya traen valores sugeridos: puedes cambiarlos o no."],
  ["relevancia", "2. Qué te importa", "Con los deslizadores dices cuánto pesa cada variable. Puedes dejar que el programa lo calcule."],
  ["simulacion", "3. Simular", "Pulsa «Ejecutar simulación». Tarda unos segundos y no necesitas internet."],
  ["resultados", "4. Resultados", "Ves la fecha recomendada y por qué. Puedes pedir más detalle y exportar un informe."],
  ["ayuda", "¿Dudas?", "En cualquier momento pulsa «✦ Preguntar» o el «?» junto a un término. Puedes repetir este recorrido desde Ayuda."],
];
const Tour = {
  i: 0, el: null,
  iniciar() { Tour.i = 0; Tour.paso(); },
  paso() {
    if (Tour.el) Tour.el.remove();
    const [pagina, titulo, texto] = PASOS[Tour.i];
    ir(pagina);
    const ultimo = Tour.i === PASOS.length - 1;
    Tour.el = h("div", { class: "tour", role: "dialog", "aria-label": "Recorrido guiado" },
      h("p", { class: "t9 b primario-c" }, `Paso ${Tour.i + 1} de ${PASOS.length}`),
      h("p", { class: "t14 b" }, titulo), h("p", { class: "texto" }, texto),
      h("div", { class: "fila", style: "justify-content:space-between" }, Boton("Saltar", Tour.cerrar, "fantasma", { ancho: 70 }),
        Boton(ultimo ? "Terminar" : "Siguiente", Tour.siguiente, "primario")));
    document.body.append(Tour.el);
  },
  siguiente() { if (Tour.i === PASOS.length - 1) Tour.cerrar(); else { Tour.i++; Tour.paso(); } },
  cerrar() { if (Tour.el) Tour.el.remove(); Tour.el = null; pref.guardar("tour_visto", true); ir("inicio"); },
};

/* ====================================================================== páginas */
const DIAG_TONO = { ok: "ok", advertencia: "aviso", falta: "error" };
const DIAG_TXT = { ok: "Listo", advertencia: "Opcional", falta: "Falta" };

/* ----------------------------------------------------------- Inicio (paginas/inicio.py) */
PAGINAS.inicio = () => {
  const el = h("section", { class: "pagina" });
  el.append(h("div", { style: "margin-bottom:20px" }, encabezado("¿Cuándo es mejor sembrar?", "Responde en unos pasos y te recomendamos una fecha, con el motivo y el riesgo."),
    h("div", { class: "fila", style: "margin:18px 0" }, Boton("Comenzar simulación", () => ir("datos"), "primario", { ancho: 210 }),
      Boton("Ejecutar con valores sugeridos", ejecutar), Boton("Recorrido de 1 minuto", () => Tour.iniciar(), "fantasma"))));
  const grupo = GrupoAcordeon();
  const sEstado = grupo.crear("Estado del sistema", { ayuda: "Comprueba que la base de datos, los cultivos y la relevancia estén listos.", alPreguntar: () => preguntar("¿Funciona sin PostgreSQL?") });
  const sJson = grupo.crear("Datos de un simulador (JSON)", { resumen: "Opcional", ayuda: "Un simulador o mod puede enviarte datos como archivo JSON.", alPreguntar: () => preguntar("¿Puedo usar datos de un simulador?") });
  el.append(sEstado.el, sJson.el);
  const tabla = Tabla([["hora", "Hora"], ["archivo", "Archivo"], ["estado", "Estado"], ["detalle", "Detalle"]]);
  sJson.cuerpo.append(etiqueta("En la versión web, el archivo se carga con «Cargar JSON» (no hay carpeta de entrada).", 10, { suave: true }),
    h("div", { class: "fila", style: "margin:10px 0" }, Boton("Cargar JSON", cargarJson, "primario"),
      Boton("Guía de integración", () => { ir("ayuda"); app.paginas.ayuda.abrir("integracion"); }, "fantasma")), tabla.el);

  async function armarEstado() {
    let items = [];
    try { items = await llamar("diagnostico", [app.registroJson.length]); } catch (e) { items = []; }
    limpiar(sEstado.cuerpo);
    for (const it of items) {
      sEstado.cuerpo.append(h("div", { class: "fila", style: "margin:6px 0;flex-wrap:nowrap" }, Pastilla(DIAG_TXT[it.estado], DIAG_TONO[it.estado]),
        h("span", { class: "b", style: "padding:0 4px;white-space:nowrap" }, it.titulo), h("span", { class: "t10 suave", style: "flex:1" }, it.mensaje),
        it.accion ? Boton(it.accion, () => accion(it.accion_id), "secundario", { tam: 10 }) : null));
    }
    sEstado.ponerResumen(items.every((i) => i.estado !== "falta") ? "Todo listo" : "Hay algo por arreglar");
  }
  async function accion(id) {
    if (id === "crear_relevancia") {
      try { await llamar("crear_relevancia_defecto", [], { guardar: true }); aviso("Se creó la configuración de relevancia por defecto."); } catch (e) { aviso(e.message, "error"); }
    } else if (id === "cargar_json") { await cargarJson(); }
    armarEstado();
  }
  function refrescarRegistro() {
    tabla.filas(app.registroJson.slice(0, 20).map((r) => ({ hora: r.hora.toTimeString().slice(0, 8), archivo: r.archivo, estado: r.valido ? "Válido" : "Inválido", detalle: r.detalle })));
    const n = app.registroJson.length;
    sJson.ponerResumen(n ? `${n} recibido${n !== 1 ? "s" : ""}` : "Opcional");
  }
  armarEstado();
  refrescarRegistro();
  return { el, alMostrar: armarEstado, refrescarRegistro, abrirRegistro: () => sJson.abrir() };
};

async function cargarJson() {
  const f = await elegirArchivo(".json,application/json");
  if (!f) return;
  const ahora = new Date();
  let r;
  try { r = await llamar("recibir_json", [await f.text(), f.name]); } catch (e) { r = { valido: false, detalle: e.message }; }
  app.registroJson.unshift({ hora: ahora, archivo: f.name, valido: r.valido, detalle: r.detalle });
  app.registroJson.length = Math.min(app.registroJson.length, 100);
  app.semaforo.actualizar(r.valido ? "conectado" : "error", ahora);
  if (r.valido) { reemplazarDatos(r.datos); aviso(`Datos de «${f.name}» cargados.`); }
  else aviso(`«${f.name}» no es válido: ${r.detalle}`, "error", 7000);
  const pg = app.paginas.inicio;
  if (pg) pg.refrescarRegistro();
}

/* ----------------------------------------------------------- Datos (paginas/datos.py) */
const PARAMS = { normal: [["media", "Media"], ["std", "Desviación"]], uniforme: [["min", "Mínimo"], ["max", "Máximo"]],
                 triangular: [["min", "Mínimo"], ["moda", "Más probable"], ["max", "Máximo"]] };
const VARS_CLIMA = { temperatura: "Temperatura (°C)", lluvia: "Lluvia (mm/día)", humedad: "Humedad (%)" };
const CADENAS = { salud: "Salud de la planta", enfermedad: "Enfermedad", crecimiento: "Crecimiento" };
const EVENTOS = { plagas: "Plagas", heladas: "Heladas", lluvias_intensas: "Lluvias intensas" };
let actualizarResumenes = () => {};

PAGINAS.datos = () => {
  const d = app.datos;
  const el = h("section", { class: "pagina" }, encabezado("Tus datos", "Abre cada sección solo si quieres cambiar algo: ya traen valores sugeridos."));
  const grupo = GrupoAcordeon();
  const defs = [["cultivo", "Cultivo", "Qué vas a sembrar y qué necesita.", "¿Qué es el rango de cosecha?"],
    ["suelo", "Suelo y manejo", "pH, nutrientes (N, P, K), resistencia y riego.", "¿Qué es el pH del suelo?"],
    ["clima", "Clima", "Cuánto puede variar la temperatura, la lluvia y la humedad.", "¿Qué son las distribuciones?"],
    ["estado", "Estado de la planta", "Probabilidades de pasar de un estado a otro cada semana (cadena de Márkov).", "¿Qué es una cadena de Márkov?"],
    ["eventos", "Eventos raros", "Plagas, heladas y lluvias intensas que ocurren pocas veces.", "¿Qué es la distribución de Poisson?"],
    ["plan", "Plan de temporadas", "Cuántas temporadas planear seguidas.", "¿Qué es Galton-Watson?"]];
  const sec = {};
  for (const [k, tit, ayuda, preg] of defs) { sec[k] = grupo.crear(tit, { ayuda, alPreguntar: () => preguntar(preg) }); el.append(sec[k].el); }

  // ---- cultivo
  const sel = h("select", { "aria-label": "Cultivo", style: "min-width:24ch" }, app.cultivos.map((c) => h("option", { selected: c.nombre === d.cultivo.nombre }, c.nombre)));
  const camposCultivo = h("div", { class: "rejilla2" });
  sec.cultivo.cuerpo.append(h("div", { class: "campo-fila", style: "margin-bottom:8px" }, h("span", { class: "rot" }, "Cultivo"), h("span", { class: "entrada" }, sel)), camposCultivo);
  function pintarCultivo() {
    limpiar(camposCultivo);
    const c = app.datos.cultivo;
    [["dias_crecimiento", "Días de crecimiento", "", true], ["temp_min", "Temperatura mínima (°C)", "Por debajo, la planta sufre."],
     ["temp_max", "Temperatura máxima (°C)", "Por encima, la planta sufre."], ["requerimiento_agua", "Agua que pide (mm/día)", ""],
     ["resistencia_plagas", "Resistencia a plagas (0–100)", "Qué tan bien aguanta plagas y enfermedades."],
     ["rendimiento_base", "Rendimiento base (t/ha)", "Cosecha ideal en condiciones perfectas."]]
      .forEach(([k, rot, ay, ent]) => camposCultivo.append(Campo(rot, "c_" + k, c[k], (v) => { app.datos.cultivo[k] = v; }, { ayuda: ay, entero: ent })));
  }
  sel.addEventListener("change", () => {
    const c = app.cultivos.find((x) => x.nombre === sel.value);
    if (c) { app.datos.cultivo = copia(c); [...app.errores.keys()].filter((k) => k.startsWith("c_")).forEach((k) => app.errores.delete(k)); pintarCultivo(); actualizarResumenes(); }
  });
  pintarCultivo();

  // ---- suelo
  const suelo = h("div", { class: "rejilla2" });
  [["fecha", "Fecha inicial (AAAA-MM-DD)", "Desde qué día se exploran fechas de siembra.", true], ["ph", "pH del suelo", "0 a 14; ideal cerca de 6,5."],
   ["nitrogeno", "Nitrógeno (kg/ha)", ""], ["fosforo", "Fósforo (kg/ha)", ""], ["potasio", "Potasio (kg/ha)", ""],
   ["resistencia", "Resistencia de la semilla (0–100)", ""], ["agua", "Riego (mm/día)", "Agua que tú aportas, además de la lluvia."]]
    .forEach(([k, rot, ay, txt]) => suelo.append(Campo(rot, "d_" + k, d.deterministas[k], (v) => { app.datos.deterministas[k] = v; }, { ayuda: ay, texto: txt })));
  sec.suelo.cuerpo.append(suelo);

  // ---- clima
  for (const [k, rot] of Object.entries(VARS_CLIMA)) {
    const e = d.estocasticos[k];
    const params = h("div", { class: "params" });
    const tipo = h("select", { "aria-label": `Cómo varía ${rot}` }, Object.keys(PARAMS).map((t) => h("option", { selected: t === e.tipo }, t)));
    const pintar = () => {
      limpiar(params);
      const ee = app.datos.estocasticos[k];
      for (const [pk, prot] of PARAMS[ee.tipo]) params.append(campoMini(prot, `e_${k}_${pk}`, ee.parametros[pk], (v) => { ee.parametros[pk] = v; }));
      if (PARAMS[ee.tipo].length === 2) params.append(h("span"));
      params.append(campoMini("Cambio por estación", `e_${k}_amplitud_estacional`, ee.amplitud_estacional, (v) => { ee.amplitud_estacional = v; }),
        campoMini("Día pico del año", `e_${k}_dia_pico`, ee.dia_pico, (v) => { ee.dia_pico = Math.round(v); }));
    };
    tipo.addEventListener("change", () => {
      const ee = app.datos.estocasticos[k];
      const def = { media: 20, std: 3, min: 0, max: 10, moda: 5 };
      ee.tipo = tipo.value;
      ee.parametros = Object.fromEntries(PARAMS[ee.tipo].map(([pk]) => [pk, def[pk]]));
      [...app.errores.keys()].filter((x) => x.startsWith(`e_${k}_`)).forEach((x) => app.errores.delete(x));
      pintar();
    });
    pintar();
    sec.clima.cuerpo.append(h("div", { class: "caja-clima" }, etiqueta(rot, 12, { peso: true }),
      h("div", { class: "campo-fila", style: "margin:6px 0" }, h("span", { class: "rot", style: "width:14ch" }, "Cómo varía"),
        h("span", { class: "entrada" }, tipo, AyudaBoton("Normal: media y desviación. Uniforme: entre un mínimo y un máximo. Triangular: mínimo, más probable y máximo."))), params));
  }
  function campoMini(rot, clave, valor, poner) {
    const i = h("input", { value: g(valor), inputmode: "decimal", "aria-label": rot });
    i.addEventListener("input", () => { const n = numero(i.value); if (n === null) app.errores.set(clave, `«${rot}» debe ser un número.`); else { app.errores.delete(clave); poner(n); } });
    return h("label", null, rot, i);
  }

  // ---- estado de la planta (Márkov)
  let cadena = "salud";
  const mk = h("div", { class: "tabla-scroll" });
  const msg = etiqueta("", 10, { suave: true });
  msg.style.marginTop = "8px";
  const segCad = Segmentado(Object.entries(CADENAS), (c) => { cadena = c; pintarMatriz(); });
  sec.estado.cuerpo.append(h("div", { style: "margin-bottom:10px" }, segCad.el), mk,
    h("div", { class: "fila", style: "margin-top:12px" }, [["Normalizar filas", normalizar], ["Agregar estado", agregarEstado], ["Quitar estado", quitarEstado],
      ["Guardar matriz", guardarMatriz], ["Cargar guardada", cargarMatriz]].map(([t, fn]) => Boton(t, fn, "secundario", { tam: 10 }))), msg);
  function pintarMatriz() {
    const ch = app.datos.estado[cadena];
    const est = ch.estados;
    const sumas = [];
    const sumar = (i) => {
      const s = ch.matriz[i].reduce((a, b) => a + b, 0);
      const ok = Math.abs(s - 1) < 1e-6;
      sumas[i].textContent = String(+s.toPrecision(3));
      sumas[i].style.color = ok ? "var(--ok)" : "var(--error)";
    };
    const filas = est.map((e, i) => {
      sumas[i] = h("td", { class: "suma" });
      return h("tr", null, h("th", null, e),
        est.map((_, j) => {
          const inp = h("input", { value: g(ch.matriz[i][j]), inputmode: "decimal", "aria-label": `De ${e} a ${est[j]}` });
          inp.addEventListener("input", () => {
            const n = numero(inp.value), clave = `mk_${cadena}_${i}_${j}`;
            if (n === null) { app.errores.set(clave, `Hay un valor que no es número en la matriz de «${CADENAS[cadena]}».`); sumas[i].textContent = "?"; sumas[i].style.color = "var(--error)"; return; }
            app.errores.delete(clave); ch.matriz[i][j] = n; sumar(i);
          });
          return h("td", null, inp);
        }),
        sumas[i],
        h("td", null, (() => {
          const inp = h("input", { value: g(ch.rendimiento_por_estado[e] ?? 0.5), inputmode: "decimal", "aria-label": `Rinde ${e}` });
          inp.addEventListener("input", () => { const n = numero(inp.value); if (n !== null) ch.rendimiento_por_estado[e] = n; });
          return inp;
        })()));
    });
    const ini = h("select", { "aria-label": "Estado inicial" }, est.map((e) => h("option", { selected: e === ch.estado_inicial }, e)));
    ini.addEventListener("change", () => { ch.estado_inicial = ini.value; });
    limpiar(mk).append(h("table", { class: "matriz" },
      h("thead", null, h("tr", null, h("th", { class: "t9 suave" }, "De ↓ / A →"), est.map((e) => h("th", null, e)), h("th", null, "Suma"), h("th", null, "Rinde (0–1)"))),
      h("tbody", null, filas)),
      h("div", { class: "campo-fila", style: "margin-top:10px" }, h("span", { class: "rot", style: "width:14ch" }, "Estado inicial"), h("span", { class: "entrada" }, ini)));
    est.forEach((_, i) => sumar(i));
    actualizarResumenes();
  }
  async function normalizar() {
    const ch = app.datos.estado[cadena];
    try { ch.matriz = await llamar("normalizar", [JSON.stringify(ch.matriz)]); limpiarErroresMatriz(); pintarMatriz(); msg.textContent = "Filas normalizadas: ahora todas suman 1."; } catch (e) { msg.textContent = e.message; }
  }
  async function agregarEstado() {
    const nombre = prompt("Nombre del nuevo estado:");
    if (!nombre) return;
    const ch = app.datos.estado[cadena];
    try {
      const r = await llamar("agregar_estado", [JSON.stringify(ch.estados), JSON.stringify(ch.matriz), nombre]);
      ch.estados = r.estados; ch.matriz = r.matriz; ch.rendimiento_por_estado[nombre.trim()] = 0.5;
      limpiarErroresMatriz(); pintarMatriz(); msg.textContent = `Estado «${nombre.trim()}» agregado (absorbente). Ajusta sus probabilidades.`;
    } catch (e) { msg.textContent = e.message; }
  }
  async function quitarEstado() {
    const ch = app.datos.estado[cadena];
    const nombre = ch.estados[ch.estados.length - 1];
    try {
      const r = await llamar("quitar_estado", [JSON.stringify(ch.estados), JSON.stringify(ch.matriz), nombre]);
      ch.estados = r.estados; ch.matriz = r.matriz; delete ch.rendimiento_por_estado[nombre];
      if (ch.estado_inicial === nombre) ch.estado_inicial = ch.estados[0];
      limpiarErroresMatriz(); pintarMatriz(); msg.textContent = `Estado «${nombre}» quitado (el último de la lista).`;
    } catch (e) { msg.textContent = e.message; }
  }
  async function guardarMatriz() {
    const ch = app.datos.estado[cadena];
    const malas = ch.matriz.findIndex((f) => Math.abs(f.reduce((a, b) => a + b, 0) - 1) > 1e-6);
    if (malas >= 0) { msg.textContent = `En «${CADENAS[cadena]}», la fila «${ch.estados[malas]}» no suma 1. Usa «Normalizar filas».`; return; }
    const hoy = new Date().toLocaleDateString("es-CO", { day: "2-digit", month: "2-digit", year: "numeric" });
    try { await llamar("guardar_matriz", [`${CADENAS[cadena]} ${hoy}`, cadena, JSON.stringify(ch.estados), JSON.stringify(ch.matriz)], { guardar: true }); msg.textContent = "Matriz guardada."; }
    catch (e) { msg.textContent = `No se pudo guardar: ${e.message}`; }
  }
  async function cargarMatriz() {
    const m = await llamar("cargar_matriz", [cadena]).catch(() => null);
    if (!m) { msg.textContent = "Aún no hay matrices guardadas para esta cadena."; return; }
    const ch = app.datos.estado[cadena];
    ch.estados = [...m.estados]; ch.matriz = m.matriz_transicion;
    ch.rendimiento_por_estado = Object.fromEntries(ch.estados.map((e) => [e, ch.rendimiento_por_estado[e] ?? 0.5]));
    if (!ch.estados.includes(ch.estado_inicial)) ch.estado_inicial = ch.estados[0];
    limpiarErroresMatriz(); pintarMatriz(); msg.textContent = `Cargada: ${m.nombre}.`;
  }
  function limpiarErroresMatriz() { [...app.errores.keys()].filter((k) => k.startsWith(`mk_${cadena}_`)).forEach((k) => app.errores.delete(k)); }
  pintarMatriz();

  // ---- eventos raros y plan
  const ev = h("div", { class: "rejilla2" });
  for (const [k, e] of Object.entries(d.eventos_raros)) {
    ev.append(Campo(`${EVENTOS[k] || k}: por mes`, `ev_${k}_tasa`, e.tasa_mensual, (v) => { app.datos.eventos_raros[k].tasa_mensual = v; }, { ayuda: "Cuántas veces ocurre en promedio cada mes." }),
      Campo("Pérdida por evento", `ev_${k}_perdida`, e.perdida, (v) => { app.datos.eventos_raros[k].perdida = v; }, { ayuda: "Fracción de cosecha que se pierde (0 a 1)." }));
  }
  sec.eventos.cuerpo.append(ev);
  const pl = h("div", { class: "rejilla2" });
  [["temporadas", "Temporadas (1–10)", "Con más de 10 el programa avisa que es menos confiable.", true], ["media_descendientes", "Descendientes por planta", "Si es menor que 1, el cultivo se extingue."],
   ["plantas_iniciales", "Plantas iniciales", "", true], ["capacidad", "Capacidad del terreno", "Máximo de plantas que caben.", true],
   ["agotamiento_suelo", "Agotamiento del suelo", "Cuánto empeora el suelo cada temporada (0 a 1)."]]
    .forEach(([k, rot, ay, ent]) => pl.append(Campo(rot, "p_" + k, d.plan[k], (v) => { app.datos.plan[k] = v; }, { ayuda: ay, entero: ent })));
  sec.plan.cuerpo.append(pl);

  el.append(h("div", { style: "margin:18px 0" }, Boton("Continuar → Relevancia", () => ir("relevancia"), "primario", { ancho: 220 })));

  actualizarResumenes = () => {
    const x = app.datos;
    sec.cultivo.ponerResumen(x.cultivo.nombre);
    sec.suelo.ponerResumen(`pH ${g(x.deterministas.ph)} · ${x.deterministas.fecha}`);
    sec.clima.ponerResumen("3 variables");
    sec.estado.ponerResumen(`${Object.keys(x.estado).length} cadenas`);
    sec.eventos.ponerResumen(`${Object.keys(x.eventos_raros).length} eventos`);
    const t = Math.round(x.plan.temporadas || 1);
    sec.plan.ponerResumen(`${t} temporada${t !== 1 ? "s" : ""}`);
  };
  actualizarResumenes();
  return { el };
};

/* ----------------------------------------------------------- Relevancia (paginas/relevancia.py) */
const AYUDAS_REL = { agua: "Cuánto te importa que el agua sea la adecuada.", temperatura: "Cuánto te importa la temperatura.",
  humedad: "Cuánto te importa la humedad del aire.", ph: "Cuánto te importa la acidez del suelo.",
  nutrientes: "Cuánto te importan nitrógeno, fósforo y potasio. Pon 0 si tu simulador no los usa." };
const METODOS = [["manual", "Sugeridos"], ["minimo", "Ley del Mínimo"], ["historico", "Mi histórico"], ["experto", "Modo experto"], ["campo", "Diario de campo"]];
const ESCALA = [["a es mucho más importante", 9], ["a es más importante", 5], ["a es algo más importante", 3], ["Igual", 1],
  ["b es algo más importante", 1 / 3], ["b es más importante", 1 / 5], ["b es mucho más importante", 1 / 9]];

PAGINAS.relevancia = () => {
  const E = app.ini.etiquetas;
  const el = h("section", { class: "pagina" }, encabezado("¿Qué te importa más?", "Cuánto pesa cada variable en tu caso, de 0 (se ignora) a 100 (máxima importancia)."));
  const t = Tarjeta(22);
  t.el.style.marginBottom = "12px";
  const origen = etiqueta("", 10, { suave: true });
  origen.style.marginTop = "8px";
  const sl = {};
  const cambio = (soloTexto) => { if (!soloTexto) { app.pesosOrigen = "Ajuste manual"; volcar(); } origen.textContent = `Origen: ${app.pesosOrigen}`; };
  for (const v of app.ini.variables) { sl[v] = Deslizador(E[v], app.datos.pesos[v] ?? app.ini.pesos_defecto[v] ?? 50, AYUDAS_REL[v], () => cambio(false)); t.cuerpo.append(sl[v].el); }
  t.cuerpo.append(origen);
  cambio(true);
  const volcar = () => { for (const [v, s] of Object.entries(sl)) app.datos.pesos[v] = s.obtener(); };
  const poner = (pesos, org) => { for (const [v, s] of Object.entries(sl)) if (v in pesos) s.poner(+pesos[v]); app.pesosOrigen = org; cambio(true); volcar(); };
  const grupo = GrupoAcordeon();
  const sMet = grupo.crear("Calcularlo automáticamente", { resumen: "Opcional", ayuda: "Ley del Mínimo, tu histórico, comparaciones de experto o tu diario de campo.", alPreguntar: () => preguntar("¿Qué es la Ley del Mínimo?") });
  const sPerf = grupo.crear("Mis configuraciones guardadas", { ayuda: "Guarda, carga, duplica y comparte tus pesos.", alPreguntar: () => preguntar("¿Cómo comparto mi configuración de relevancia?") });
  el.append(t.el, sMet.el, sPerf.el, h("div", { style: "margin:16px 0" }, Boton("Continuar → Simulación", () => ir("simulacion"), "primario", { ancho: 220 })));

  const panel = h("div");
  const seg = Segmentado(METODOS, metodo);
  sMet.cuerpo.append(h("div", { style: "margin-bottom:12px" }, seg.el), panel);
  function resultado(c, res, org) {
    for (const txt of Object.values(res.justificaciones || {})) c.append(etiqueta(`•  ${txt}`, 10, { clase: "", }));
    if (res.resumen_consistencia) c.append(h("p", { class: "t10 b", style: "margin:6px 0" }, res.resumen_consistencia));
    c.append(h("div", { style: "margin:8px 0" }, Boton("Usar estos pesos", () => poner(res.pesos, org), "primario")));
  }
  async function metodo(clave) {
    const c = limpiar(panel);
    if (clave === "manual") {
      c.append(etiqueta("Mueve los deslizadores a tu gusto. Los valores iniciales son sugerencias para agricultura real.", 11),
        h("p", { class: "t9 suave", style: "margin:8px 0" }, app.ini.fuente_defecto),
        Boton("Restaurar valores sugeridos", () => poner({ ...app.ini.pesos_defecto }, "Valores sugeridos")));
    } else if (clave === "minimo") {
      c.append(h("p", { style: "margin-bottom:8px" }, "Calcula la relevancia sola: lo que está más lejos de su valor ideal pesa más."));
      try { resultado(c, await llamar("ley_minimo", [JSON.stringify(app.datos)]), "Ley del Mínimo"); } catch (e) { c.append(etiqueta(e.message, 10)); }
    } else if (clave === "historico") {
      const zona = h("div", { style: "margin:8px 0" });
      c.append(h("p", { style: "margin-bottom:8px" }, "Sube un CSV o Excel con tus temporadas pasadas (columna «rendimiento», al menos 10 filas)."),
        Boton("Elegir archivo…", async () => {
          const f = await elegirArchivo(".csv,.txt,.xlsx,.xlsm");
          if (!f) return;
          limpiar(zona).append(etiqueta("Leyendo…", 10, { suave: true }));
          const buf = await f.arrayBuffer();
          const r = await pedir("archivo", { funcion: "historico", nombre: f.name, bytes: buf }, null, [buf]);
          limpiar(zona);
          if (!r.ok) { zona.append(etiqueta(`No pude leer el archivo: ${r.error}`, 10)); return; }
          if (!r.valor.valido) { zona.append(etiqueta(r.valor.motivo || "El archivo no sirve.", 10)); return; }
          resultado(zona, r.valor, "Mi histórico (Spearman)");
        }), zona);
    } else if (clave === "experto") {
      const cmp = [];
      c.append(h("p", { style: "margin-bottom:8px" }, "Compara las variables de dos en dos. Si dudas, deja «Igual»."));
      for (const [a, b] of app.ini.pares_experto) {
        const s = h("select", { "aria-label": `${E[a]} frente a ${E[b]}` }, ESCALA.map(([t]) => h("option", { selected: t === "Igual" }, t)));
        cmp.push([a, b, s]);
        c.append(h("div", { class: "campo-fila" }, h("span", { class: "rot t10", style: "width:34ch" }, `${E[a]} (a) frente a ${E[b]} (b)`), h("span", { class: "entrada" }, s)));
      }
      const zona = h("div");
      c.append(h("div", { style: "margin:8px 0" }, Boton("Calcular", async () => {
        limpiar(zona);
        const esc = Object.fromEntries(ESCALA);
        try { resultado(zona, await llamar("experto", [JSON.stringify(cmp.map(([a, b, s]) => [a, b, esc[s.value]]))]), "Modo experto (AHP)"); } catch (e) { zona.append(etiqueta(e.message, 10)); }
      })), zona);
    } else if (clave === "campo") {
      const vSel = h("select", { "aria-label": "Variable" }, app.ini.variables.map((v) => h("option", { value: v }, v)));
      const exp = etiqueta("", 10, { suave: true });
      const ponerExp = async () => { exp.textContent = await llamar("experimento", [vSel.value]).catch(() => ""); };
      vSel.addEventListener("change", ponerExp);
      const rv = { temporada: h("input", { style: "width:12ch" }), valor: h("input", { style: "width:12ch", inputmode: "decimal" }), rendimiento: h("input", { style: "width:12ch", inputmode: "decimal" }) };
      const n = etiqueta("", 10, { suave: true });
      const contar = async () => { n.textContent = `Registros guardados: ${await llamar("n_registros").catch(() => 0)}`; };
      const zona = h("div");
      c.append(h("p", { style: "margin-bottom:8px" }, "Prueba una variable a la vez en tu terreno y anota lo que pase. Con 5 registros calculo tu relevancia."),
        vSel, h("div", { style: "margin:4px 0" }, exp),
        h("div", { class: "fila", style: "margin:6px 0" }, [["temporada", "Temporada"], ["valor", "Valor de la variable"], ["rendimiento", "Rendimiento"]]
          .map(([k, rot]) => h("label", { class: "t10 suave", style: "display:flex;flex-direction:column" }, rot, rv[k])),
        Boton("Anotar", async () => {
          try { await llamar("agregar_registro", [rv.temporada.value, vSel.value, rv.valor.value, rv.rendimiento.value], { guardar: true }); Object.values(rv).forEach((i) => { i.value = ""; }); contar(); }
          catch (e) { aviso(e.message, "error"); }
        }, "secundario", { tam: 10 })),
        n, h("div", { style: "margin:6px 0" }, Boton("Calcular con mis registros", async () => {
          limpiar(zona);
          try {
            const res = await llamar("desde_campo", [JSON.stringify(app.datos)]);
            if (res.motivo) zona.append(etiqueta(res.motivo, 10));
            resultado(zona, res, res.usa_ley_minimo ? "Ley del Mínimo (pocos registros)" : "Mi diario de campo");
          } catch (e) { zona.append(etiqueta(e.message, 10)); }
        }, "primario")), zona);
      ponerExp(); contar();
    }
  }
  metodo("manual");

  // ---- perfiles
  const nombre = h("input", { style: "width:28ch", "aria-label": "Nombre de la configuración" });
  const lista = Tabla([["nombre", "Configuración"], ["metodo", "Método"]], { seleccion: "una", alto: 200 });
  sPerf.cuerpo.append(h("div", { class: "campo-fila", style: "margin-bottom:10px" }, h("span", { class: "rot", style: "width:10ch" }, "Nombre"),
    h("span", { class: "entrada" }, nombre, Boton("Guardar", guardar, "primario", { tam: 10 }))), lista.el,
    h("div", { class: "fila", style: "margin:10px 0" }, [["Cargar", cargar], ["Duplicar", duplicar], ["Eliminar", eliminar], ["Descargar", exportar], ["Importar", importar]]
      .map(([t, fn]) => Boton(t, fn, "secundario", { tam: 10 }))));
  async function listar() {
    const cfg = await llamar("perfiles").catch(() => []);
    lista.filas(cfg);
    sPerf.ponerResumen(`${cfg.length} guardada${cfg.length !== 1 ? "s" : ""}`);
  }
  const sel1 = () => { const s = lista.seleccion(); if (!s.length) { aviso("Elige una configuración de la lista.", "aviso"); return null; } return s[0]; };
  async function guardar() { volcar(); try { await llamar("guardar_perfil", [nombre.value, JSON.stringify(app.datos.pesos)], { guardar: true }); listar(); aviso("Configuración guardada."); } catch (e) { aviso(e.message, "error"); } }
  async function cargar() { const i = sel1(); if (i == null) return; try { const c = await llamar("cargar_perfil", [i]); poner(c.pesos, `Guardada: ${c.nombre}`); } catch (e) { aviso(e.message, "error"); } }
  async function duplicar() { const i = sel1(); if (i == null) return; await llamar("duplicar_perfil", [i], { guardar: true }).catch((e) => aviso(e.message, "error")); listar(); }
  async function eliminar() { const i = sel1(); if (i == null) return; await llamar("eliminar_perfil", [i], { guardar: true }).catch((e) => aviso(e.message, "error")); listar(); }
  async function exportar() { const i = sel1(); if (i == null) return; const doc = await llamar("exportar_perfil", [i]); descargar("relevancia.json", JSON.stringify(doc, null, 2), "application/json"); aviso("Configuración descargada."); }
  async function importar() {
    const f = await elegirArchivo(".json,application/json");
    if (!f) return;
    try { await llamar("importar_perfil", [await f.text()], { guardar: true }); listar(); aviso("Configuración importada."); } catch (e) { aviso(`No se pudo importar: ${e.message}`, "error"); }
  }
  listar();
  return { el, alMostrar: listar };
};

/* ----------------------------------------------------------- Simulación (paginas/simulacion.py) */
PAGINAS.simulacion = () => {
  const el = h("section", { class: "pagina" }, encabezado("Simulación", "Todo listo cuando quieras. Tarda unos segundos."));
  const t = Tarjeta();
  t.el.style.marginBottom = "14px";
  const resumen = etiqueta("", 12);
  const boton = Boton("Ejecutar simulación", ejecutar, "primario", { ancho: 220 });
  const barra = h("div", { class: "barra-prog", hidden: true }, h("div"));
  const estado = h("span", { class: "t10 suave", hidden: true });
  t.cuerpo.append(resumen, h("div", { class: "fila", style: "margin-top:16px;gap:16px" }, boton, barra, estado));
  const grupo = GrupoAcordeon();
  const s = grupo.crear("Ajustes avanzados", { resumen: "Opcional", ayuda: "Cuántos escenarios simular, la ventana de fechas y el nombre de esta simulación.", alPreguntar: () => preguntar("¿Qué es Montecarlo?") });
  el.append(t.el, s.el);
  const campos = [["nombre", "Nombre (opcional)", "Para encontrarla luego en el Historial.", "¿Qué es el historial?"],
    ["iteraciones", "Escenarios a simular", "Más escenarios dan resultados más estables, pero tardan más.", "¿Qué es Montecarlo?"],
    ["semilla", "Semilla aleatoria (opcional)", "Con la misma semilla obtienes el mismo resultado.", "¿Qué es la semilla aleatoria?"],
    ["ventana_dias", "Ventana de fechas (días)", "Cuántos días explorar desde la fecha inicial.", "¿Qué es la ventana y el paso?"],
    ["paso_dias", "Paso entre fechas (días)", "Cada cuántos días se prueba una fecha.", "¿Qué es la ventana y el paso?"],
    ["esfuerzo", "Esfuerzo o costo relativo", "0 o más. Más esfuerzo baja el KPI.", "¿Qué es el esfuerzo?"]];
  for (const [k, rot, ay, preg] of campos) {
    const opcional = k === "nombre" || k === "semilla";
    const fila = Campo(rot, "s_" + k, app.datos[k], (v) => { app.datos[k] = v; }, { ayuda: ay, texto: opcional, ancho: 18, entero: ["iteraciones", "ventana_dias", "paso_dias"].includes(k), alPreguntar: () => preguntar(preg) });
    if (k === "semilla") fila.querySelector("input").addEventListener("input", (e) => { const n = numero(e.target.value); app.datos.semilla = n === null ? null : Math.round(n); });
    fila.querySelector(".rot").style.width = "26ch";
    s.cuerpo.append(fila);
  }
  const ponerResumen = () => {
    const d = app.datos;
    resumen.textContent = `Cultivo: ${d.cultivo.nombre}  ·  Siembra desde: ${d.deterministas.fecha}  ·  Temporadas: ${Math.round(d.plan.temporadas || 1)}  ·  Relevancia: ${app.pesosOrigen}`;
  };
  ponerResumen();
  return {
    el, alMostrar: ponerResumen,
    alIniciar() { boton.disabled = true; barra.hidden = false; estado.hidden = false; barra.firstChild.style.width = "0"; estado.textContent = "Empezando…"; },
    alProgreso(i, n) { barra.firstChild.style.width = `${(i / n) * 100}%`; estado.textContent = `Probando fecha ${i} de ${n}`; },
    alTerminar() { boton.disabled = false; barra.hidden = true; estado.hidden = true; },
  };
};

/* ----------------------------------------------------------- Resultados (paginas/resultados.py) */
const MIME = { ".pdf": "application/pdf", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".csv": "text/csv",
  ".json": "application/json", ".png": "image/png" };

PAGINAS.resultados = () => {
  const r = app.resultado;
  const el = h("section", { class: "pagina" });
  if (!r) {
    el.append(encabezado("Resultados", "Aún no hay resultados."), etiqueta("Ejecuta una simulación y aquí verás la fecha recomendada.", 12, { suave: true }),
      h("div", { style: "margin:16px 0" }, Boton("Ir a Simulación", () => ir("simulacion"), "primario")));
    return { el };
  }
  const fo = r.fecha_optima, est = r.estadisticas_rendimiento;
  el.append(encabezado(r.nombre || "Resultados", r.cultivo || ""));
  // Recomendación
  const t = Tarjeta(26);
  t.el.style.marginBottom = "14px";
  const detalle = h("div", { hidden: true, style: "margin-top:12px" }, (r.justificacion_detalle || []).map((d) => h("p", { style: "margin:3px 0" }, "•  " + d)));
  t.cuerpo.append(Pastilla(fo.viable ? "Recomendado" : "No viable", fo.viable ? "ok" : "error"),
    fo.viable ? h("p", { class: "t26 b primario-c", style: "margin:10px 0 4px" }, fo.fecha_larga)
      : h("p", { class: "t22 b error-c", style: "margin:10px 0 4px" }, "No encontré una fecha segura"),
    h("p", { class: "t12", style: "margin:4px 0 12px;max-width:640px" }, r.justificacion || ""),
    h("div", { class: "fila" }, Boton("¿Por qué esta fecha?", () => { detalle.hidden = !detalle.hidden; }), Boton("Preguntar al asistente", () => preguntar("¿Por qué esta fecha?"), "fantasma")),
    detalle);
  el.append(t.el);
  // Tres números
  const fila = h("div", { class: "rejilla3", style: "margin-bottom:14px;gap:14px" });
  [["KPI", f2(r.kpi.valor), "Puntaje de esta fecha (más alto es mejor).", "El KPI combina rendimiento, relevancia y esfuerzo."],
   ["Probabilidad de éxito", pct(fo.probabilidad_exito), "De los escenarios simulados, los que llegan a buena cosecha.", "Se considera éxito llegar al menos al 40 % del rendimiento base."],
   ["Cosecha esperada", `${f1(est.p10)}–${f1(est.p90)}`, "toneladas por hectárea (8 de cada 10 casos).", "Va del percentil 10 al 90."]]
    .forEach(([rot, val, nota, ay]) => { const c = Tarjeta(18); c.cuerpo.append(Metrica(rot, val, nota, ay)); fila.append(c.el); });
  el.append(fila);
  // Vistas bajo demanda
  const vistas = [["graficas", "Gráficas"], ["comparacion", "Comparación"], ["riesgos", "Riesgos"]];
  if (r.plan_temporadas) vistas.push(["temporadas", "Temporadas"]);
  vistas.push(["exportar", "Exportar"]);
  const zona = h("div", { style: "margin:12px 0" });
  const seg = Segmentado(vistas, vista, null);
  el.append(etiqueta("¿Quieres ver más?", 12, { peso: true }), h("div", { style: "margin-top:8px" }, seg.el), zona);
  let graficaActual = null, redibujar = null;

  function card() { const c = Tarjeta(20); zona.append(c.el); return c.cuerpo; }
  function vista(clave) {
    limpiar(zona); redibujar = null;
    const c = card();
    if (clave === "graficas") {
      const opciones = app.ini.graficas.filter((n) => n !== "Temporadas" || r.plan_temporadas).map((n) => [n, n]);
      const lienzo = h("div", { class: "grafica" });
      const dibujar = async (nombre) => {
        graficaActual = nombre;
        lienzo.textContent = "Dibujando la gráfica… (la primera vez tarda un poco más)";
        try {
          const svg = await llamar("grafica", [nombre, oscuro(), esMovil()], { necesita: ["matplotlib"] });
          if (graficaActual === nombre) lienzo.innerHTML = svg;
        } catch (e) { lienzo.textContent = `No se pudo dibujar: ${e.message}`; }
      };
      redibujar = () => dibujar(graficaActual);
      c.append(h("div", { style: "margin-bottom:10px" }, Segmentado(opciones, dibujar).el), lienzo);
      dibujar(opciones[0][0]);
    } else if (clave === "comparacion") {
      c.append(h("p", { class: "t12 b", style: "margin-bottom:10px" }, "¿Cuánto mejor es esta fecha que otras opciones?"));
      for (const x of r.comparaciones || []) {
        c.append(h("div", { class: "fila", style: "margin:6px 0;align-items:baseline" }, h("span", { class: "b", style: "min-width:22ch" }, x.etiqueta),
          h("span", { style: "min-width:24ch" }, x.fecha_larga), h("span", { class: "t10 suave" }, `KPI ${f2(x.kpi)} · éxito ${pct(x.probabilidad_exito)}`),
          x.ventaja_pct != null ? h("span", { style: "margin-left:auto" }, Pastilla(`la óptima es ${f0(x.ventaja_pct)} % mejor`, x.ventaja_pct >= 0 ? "ok" : "aviso")) : null));
      }
    } else if (clave === "riesgos") {
      c.append(etiqueta("Riesgos identificados", 12, { peso: true }), h("p", { class: "t10 suave", style: "margin-bottom:10px" }, "Probabilidad de que ocurra cada evento raro durante el ciclo del cultivo."));
      for (const x of r.riesgos || []) {
        const pr = x.probabilidades, per = x.perdida_esperada * 100;
        c.append(h("div", { class: "fila", style: "margin:7px 0" }, h("span", { class: "b", style: "min-width:18ch" }, x.etiqueta),
          h("span", { class: "t10 suave" }, `Ninguno ${pct(pr["0"])} · 1 vez ${pct(pr["1"])} · 2 veces ${pct(pr["2"])} · 3 o más ${pct(pr["3+"])}`),
          h("span", { style: "margin-left:auto" }, Pastilla(`pérdida esperada ${f0(per)} %`, per >= 15 ? "error" : per >= 5 ? "aviso" : "ok"))));
      }
      c.append(h("div", { style: "margin-top:10px" }, Boton("¿Qué es Poisson?", () => preguntar("¿Qué es la distribución de Poisson?"), "fantasma", { tam: 10 })));
    } else if (clave === "temporadas") {
      const plan = r.plan_temporadas;
      c.append(Pastilla(plan.riesgo_extincion ? "Riesgo de extinción" : "Se sostiene", plan.riesgo_extincion ? "error" : "ok"),
        h("p", { style: "margin:10px 0;max-width:640px" }, plan.recomendacion));
      if (plan.aviso_largo_plazo) c.append(h("p", { class: "t10 suave", style: "margin-bottom:8px" }, "Más de 10 temporadas: las proyecciones son menos confiables."));
      const tb = Tabla([["t", "Temporada"], ["f", "Siembra"], ["n", "Plantas"], ["c", "Cosecha (t/ha)"], ["s", "Semillas a guardar"]]);
      tb.filas(plan.filas.map((x) => ({ t: x.temporada, f: x.fecha_siembra, n: f0(x.poblacion_esperada), c: f2(x.cosecha_estimada), s: x.semillas_guardar })));
      c.append(tb.el);
    } else if (clave === "exportar") {
      c.append(h("p", { class: "t12 b", style: "margin-bottom:10px" }, "Guarda tus resultados"),
        h("div", { class: "fila" }, Object.entries(app.ini.formatos).map(([ext, nombre]) => Boton(nombre.split(" (")[0], () => exportar(ext)))));
    }
  }
  async function exportar(ext) {
    aviso("Preparando el archivo… (la primera vez tarda un poco más)", "ok", 0);
    const res = await pedir("exportar", { ext });
    if (!res.ok) { aviso(`No se pudo exportar: ${res.error}`, "error"); return; }
    descargar(`pronostico_siembra${ext}`, res.bytes, MIME[ext]);
    aviso("Archivo guardado.");
  }
  return { el, redibujar: () => redibujar && redibujar() };
};

/* ----------------------------------------------------------- Historial (paginas/historial.py) */
PAGINAS.historial = () => {
  const el = h("section", { class: "pagina" }, encabezado("Historial", "Tus simulaciones guardadas. Elige una para abrirla o dos para compararlas."));
  const texto = h("input", { style: "width:24ch", "aria-label": "Buscar" });
  const desde = h("input", { style: "width:12ch", placeholder: "AAAA-MM-DD", "aria-label": "Desde" });
  const hasta = h("input", { style: "width:12ch", placeholder: "AAAA-MM-DD", "aria-label": "Hasta" });
  [texto, desde, hasta].forEach((i) => i.addEventListener("input", () => listar()));
  el.append(h("div", { class: "fila", style: "margin-bottom:10px;gap:6px 12px" },
    h("label", { class: "fila t10 suave", style: "gap:6px" }, "Buscar", texto), h("label", { class: "fila t10 suave", style: "gap:6px" }, "Desde", desde),
    h("label", { class: "fila t10 suave", style: "gap:6px" }, "Hasta", hasta), AyudaBoton("Escribe las fechas como AAAA-MM-DD (por ejemplo 2026-11-01).")));
  const t = Tabla([["n", "Nombre"], ["e", "Ejecutada"], ["f", "Fecha óptima"], ["k", "KPI"], ["p", "Éxito"]], { seleccion: "varias", alto: 420 });
  const vacio = etiqueta("", 11, { suave: true });
  el.append(t.el, h("div", { class: "fila", style: "margin:12px 0" },
    [["Abrir", abrir, "primario"], ["Comparar dos", comparar, "secundario"], ["Reutilizar configuración", reutilizar, "secundario"], ["Renombrar", renombrar, "secundario"], ["Eliminar", eliminar, "peligro"]]
      .map(([tx, fn, v]) => Boton(tx, fn, v, { tam: 10 }))), vacio);
  async function listar() {
    const filas = await llamar("listar_historial", [texto.value, desde.value.trim(), hasta.value.trim()]).catch(() => []);
    t.filas(filas.map((x) => ({ id: String(x.id), n: x.nombre || "", e: String(x.fecha_ejecucion || "").slice(0, 16).replace("T", " "), f: x.fecha_optima || "",
      k: f2(x.kpi_esperado || 0), p: `${f0(x.probabilidad_exito || 0)} %` })));
    vacio.textContent = filas.length ? "" : texto.value ? "Ninguna coincide con tu búsqueda." : "Aún no hay simulaciones guardadas.";
  }
  const uno = () => { const ids = t.seleccion(); if (ids.length !== 1) { aviso("Elige una sola simulación de la lista.", "aviso"); return null; } return ids[0]; };
  async function abrir() {
    const i = uno(); if (i == null) return;
    try { app.resultado = await llamar("abrir_simulacion", [i]); rehacer("resultados"); ir("resultados"); } catch (e) { aviso(e.message, "error"); }
  }
  async function renombrar() {
    const i = uno(); if (i == null) return;
    const n = prompt("Nuevo nombre:");
    if (n) { try { await llamar("renombrar", [i, n], { guardar: true }); listar(); } catch (e) { aviso(e.message, "error"); } }
  }
  async function eliminar() {
    const i = uno(); if (i == null) return;
    await llamar("eliminar_simulacion", [i], { guardar: true }).catch(() => null);
    listar(); aviso("Simulación eliminada.");
  }
  async function reutilizar() {
    const i = uno(); if (i == null) return;
    try { reemplazarDatos(await llamar("reutilizar", [i])); aviso("Configuración cargada. Revísala en Datos o ejecútala de nuevo."); ir("simulacion"); }
    catch (e) { aviso(e.message, "aviso"); }
  }
  async function comparar() {
    const ids = t.seleccion();
    if (ids.length !== 2) { aviso("Elige exactamente dos simulaciones para compararlas.", "aviso"); return; }
    let c;
    try { c = await llamar("comparar", ids); } catch (e) { aviso(e.message, "error"); return; }
    const lienzo = h("div", { class: "grafica" }, "Dibujando la gráfica…");
    const capa = h("div", { class: "capa", role: "dialog", "aria-label": "Comparación" }, h("div", { class: "contenido" },
      Boton("← Volver", () => capa.remove(), "secundario"),
      h("p", { class: "t20 b", style: "margin:18px 0 4px" }, "Comparación"), h("p", { class: "t12", style: "margin-bottom:12px;max-width:900px" }, c.resumen),
      h("div", { class: "dos" }, ["a", "b"].map((k) => {
        const s = c[k], tj = Tarjeta(16);
        if (c.mejor === k) tj.cuerpo.append(h("div", { style: "margin-bottom:6px" }, Pastilla("Mejor KPI", "ok")));
        tj.cuerpo.append(etiqueta(s.nombre, 13, { peso: true }),
          h("p", { class: "t10 suave", style: "margin:2px 0 8px" }, `${s.cultivo} · óptima ${s.fecha_optima}`),
          h("p", null, `KPI ${f2(s.kpi)}   ·   éxito ${pct(s.probabilidad_exito)}   ·   ${f1(s.p10)}–${f1(s.p90)} t/ha`));
        return tj.el;
      })),
      h("div", { style: "margin:10px 0" }, c.diferencias.map((d) => h("p", { style: "margin:2px 0" }, "•  " + d))), lienzo));
    document.body.append(capa);
    try { lienzo.innerHTML = await llamar("grafica_comparacion", [ids[0], ids[1], oscuro(), esMovil()], { necesita: ["matplotlib"] }); }
    catch (e) { lienzo.textContent = `No se pudo dibujar: ${e.message}`; }
  }
  listar();
  return { el, alMostrar: listar };
};

/* ----------------------------------------------------------- Ayuda (paginas/ayuda.py) */
PAGINAS.ayuda = () => {
  const el = h("section", { class: "pagina" }, encabezado("Ayuda", "Elige qué quieres consultar. También puedes preguntar al asistente en cualquier momento."));
  const zona = h("div");
  const seg = Segmentado([["recorrido", "Recorrido"], ["glosario", "Glosario"], ["faq", "Preguntas frecuentes"], ["integracion", "Guía de integración"]], (k) => abrir(k, false));
  el.append(h("div", { style: "margin-bottom:14px" }, seg.el), zona);
  function abrir(clave, sincronizar = true) {
    if (sincronizar) seg.elegir(clave, false);
    limpiar(zona);
    if (clave === "recorrido") {
      const t = Tarjeta(22);
      t.cuerpo.append(etiqueta("Recorrido guiado", 14, { peso: true }), h("p", { class: "suave", style: "margin:8px 0" }, "Un minuto para ver los pasos: datos, relevancia, simulación y resultados."),
        Boton("Iniciar recorrido", () => Tour.iniciar(), "primario"));
      zona.append(t.el);
    } else if (clave === "glosario") {
      const busca = h("input", { style: "width:32ch;margin-bottom:10px", "aria-label": "Buscar en el glosario" });
      const lista = h("div");
      const pintar = () => {
        const q = busca.value.toLowerCase();
        limpiar(lista);
        for (const [term, defin] of app.ini.glosario) {
          if (q && !term.toLowerCase().includes(q) && !defin.toLowerCase().includes(q)) continue;
          const t = Tarjeta(14);
          t.el.style.margin = "4px 0";
          t.cuerpo.append(etiqueta(term, 12, { peso: true }), h("p", { class: "t10 suave", style: "margin-top:2px;max-width:640px" }, defin));
          lista.append(t.el);
        }
      };
      busca.addEventListener("input", pintar);
      zona.append(busca, lista);
      pintar();
    } else if (clave === "faq") {
      for (const [q, a] of app.ini.faq) { const s = Seccion(q); s.cuerpo.append(h("p", { style: "max-width:640px" }, a)); zona.append(s.el); }
    } else if (clave === "integracion") {
      const caja = h("div", { class: "tarjeta", style: "padding:18px 22px" });
      let code = null;
      for (const ln of app.ini.guia_integracion.split("\n")) {
        if (ln.startsWith("```")) { if (code) { caja.append(code); code = null; } else code = h("pre", { style: "background:var(--tarjeta-2);padding:8px;overflow-x:auto;font-size:13.3px" }); continue; }
        if (code) code.append(ln + "\n");
        else if (ln.startsWith("# ")) caja.append(h("p", { class: "t18 b", style: "font-size:24px;margin-bottom:10px" }, ln.slice(2)));
        else if (ln.startsWith("## ")) caja.append(h("p", { class: "t14 b", style: "margin:12px 0 6px" }, ln.slice(3)));
        else caja.append(h("p", { style: "margin-bottom:4px;min-height:.6em" }, ln.replace(/[*`]/g, "")));
      }
      zona.append(caja);
    }
  }
  abrir("recorrido", false);
  return { el, abrir };
};
