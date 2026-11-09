/* Siembrate web: interfaz. El cálculo lo hace motor.worker.js (Python en el navegador). */
"use strict";

const $ = (sel, raiz = document) => raiz.querySelector(sel);
const $$ = (sel, raiz = document) => Array.from(raiz.querySelectorAll(sel));
// Decimales con punto (igual que los textos del motor) y miles con espacio: 3 000 escenarios, 10.53
const fmt = (n, dec = 1) => Number(n).toFixed(dec);
const entero = (n) => Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
const pct = (p) => `${Math.round(p * 100)} %`;
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

const PESOS = [["agua", "Agua"], ["temperatura", "Temperatura"], ["humedad", "Humedad"], ["ph", "pH"], ["nutrientes", "Nutrientes"]];
const CADENAS = { salud: "Salud de la planta", enfermedad: "Enfermedad", crecimiento: "Crecimiento" };
const NO_APLICA_WEB = ["¿Cómo exporto los resultados?"];

const estado = { catalogo: null, resultado: null, grafica: null, vistaGrafica: "rendimiento", cadena: "salud", ultimaEntrada: null };

/* ------------------------------------------------------------------ motor */
const worker = new Worker("motor.worker.js");
const pendientes = new Map();
let siguienteId = 1;

function pedir(tipo, datos, alProgreso) {
  const id = siguienteId++;
  return new Promise((resolver) => {
    pendientes.set(id, { resolver, alProgreso });
    worker.postMessage({ tipo, id, ...datos });
  });
}

worker.onmessage = (e) => {
  const m = e.data;
  if (m.tipo === "estado") {
    $("#carga-texto").textContent = m.texto;
    $("#carga-barra").style.width = `${m.avance}%`;
  } else if (m.tipo === "listo") {
    estado.catalogo = m.catalogo;
    llenarFormulario(m.catalogo);
    sugerir(m.sugerencias.filter((s) => !NO_APLICA_WEB.includes(s)));
    $("#carga-barra").style.width = "100%";
    $$("button[disabled]").forEach((b) => (b.disabled = false));
    setTimeout(() => $("#carga").classList.add("oculta"), 250);
  } else if (m.tipo === "fallo") {
    $("#carga-texto").textContent = `No se pudo cargar el motor: ${m.texto}. Revisa tu conexión a internet y recarga la página.`;
  } else if (m.tipo === "progreso") {
    const p = pendientes.get(m.id);
    if (p && p.alProgreso) p.alProgreso(m.i, m.n);
  } else if (m.tipo === "respuesta") {
    const p = pendientes.get(m.id);
    if (p) { pendientes.delete(m.id); p.resolver(m); }
  }
};
worker.onerror = (e) => {
  $("#carga-texto").textContent = `Error al iniciar: ${e.message || "desconocido"}. Recarga la página.`;
};

/* ------------------------------------------------------------------ navegación */
function ir(vista, guardar = true) {
  if (vista === "resultados" && !estado.resultado) vista = "datos";
  $$(".vista").forEach((v) => v.classList.toggle("activa", v.id === `vista-${vista}`));
  if (guardar && vista !== "simulando") history.pushState({ vista }, "", `#${vista}`);
  window.scrollTo({ top: 0, behavior: "instant" });
}
window.addEventListener("popstate", (e) => ir((e.state && e.state.vista) || "inicio", false));
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-ir]");
  if (b) { e.preventDefault(); ir(b.dataset.ir); }
});

/* ------------------------------------------------------------------ formulario */
function campo(nombre) { return $(`#form [name="${nombre}"]`); }

function ponerCultivo(c) {
  ["dias_crecimiento", "rendimiento_base", "temp_min", "temp_max", "requerimiento_agua", "resistencia_plagas"].forEach((k) => {
    campo(k).value = c[k];
  });
  $("#r-cultivo").textContent = c.nombre;
}

function llenarFormulario(cat) {
  const sel = $("#sel-cultivo");
  sel.innerHTML = cat.cultivos.map((c) => `<option>${c.nombre}</option>`).join("");
  ponerCultivo(cat.cultivos[0]);
  sel.addEventListener("change", () => ponerCultivo(cat.cultivos.find((c) => c.nombre === sel.value)));

  const d = cat.deterministas;
  campo("fecha").value = cat.hoy;
  ["ph", "agua", "nitrogeno", "fosforo", "potasio", "resistencia"].forEach((k) => (campo(k).value = d[k]));
  Object.entries(cat.clima).forEach(([v, params]) => Object.entries(params).forEach(([p, x]) => {
    const c = campo(`${v}.${p}`);
    if (c) c.value = x;
  }));

  $("#pesos").innerHTML = PESOS.map(([k, rot]) => `
    <label class="peso">
      <span class="peso-fila">${rot}<output id="o-${k}">${cat.pesos[k]}</output></span>
      <input type="range" min="0" max="100" step="5" name="peso.${k}" value="${cat.pesos[k]}"
             oninput="document.getElementById('o-${k}').textContent=this.value">
    </label>`).join("");
  campo("temporadas").innerHTML = Array.from({ length: 10 }, (_, i) =>
    `<option value="${i + 1}"${i + 1 === cat.temporadas ? " selected" : ""}>${i + 1} temporada${i ? "s" : ""}</option>`).join("");
  actualizarResumenes();
  $("#form").addEventListener("input", actualizarResumenes);
}

function actualizarResumenes() {
  $("#r-suelo").textContent = `pH ${campo("ph").value} · desde ${campo("fecha").value}`;
  const it = campo("iteraciones");
  $("#r-sim").textContent = `${it.options[it.selectedIndex].text.split(" (")[0]} escenarios · ${campo("temporadas").value || 1} temp.`;
}

function leerFormulario() {
  const val = (k) => campo(k).value.trim().replace(",", ".");
  const entrada = {
    cultivo: { nombre: campo("cultivo").value },
    deterministas: { fecha: campo("fecha").value },
    clima: { temperatura: {}, lluvia: {}, humedad: {} },
    pesos: {},
    iteraciones: Number(campo("iteraciones").value),
    temporadas: Number(campo("temporadas").value),
  };
  ["dias_crecimiento", "rendimiento_base", "temp_min", "temp_max", "requerimiento_agua", "resistencia_plagas"].forEach((k) => (entrada.cultivo[k] = val(k)));
  ["ph", "agua", "nitrogeno", "fosforo", "potasio", "resistencia"].forEach((k) => (entrada.deterministas[k] = val(k)));
  $$("#form input[name*='.']").forEach((i) => {
    const [a, b] = i.name.split(".");
    if (a === "peso") entrada.pesos[b] = Number(i.value);
    else entrada.clima[a][b] = i.value.trim().replace(",", ".");
  });
  return entrada;
}

/* ------------------------------------------------------------------ simular */
async function simular(entrada) {
  estado.ultimaEntrada = entrada;
  $("#error-datos").hidden = true;
  $("#sim-barra").style.width = "0%";
  $("#sim-texto").textContent = "Probando fechas de siembra";
  ir("simulando");
  const r = await pedir("simular", { entrada }, (i, n) => {
    $("#sim-barra").style.width = `${Math.round((i / n) * 100)}%`;
    $("#sim-texto").textContent = `Fecha ${i} de ${n}`;
  });
  if (!r.ok) {
    $("#error-datos").textContent = r.errores[0];
    $("#error-datos").hidden = false;
    ir("datos", false);
    return;
  }
  estado.resultado = r.resultado;
  mostrarResultado(r.resultado);
  ir("resultados");
}

$("#form").addEventListener("submit", (e) => { e.preventDefault(); simular(leerFormulario()); });
$("#btn-sugeridos").addEventListener("click", () => simular(leerFormulario()));
$("#btn-otra").addEventListener("click", () => simular(estado.ultimaEntrada || leerFormulario()));

/* ------------------------------------------------------------------ resultados */
function mostrarResultado(r) {
  const fo = r.fecha_optima, est = r.estadisticas_rendimiento;
  $("#res-cultivo").textContent = `${r.cultivo} · ${entero(r.iteraciones)} escenarios simulados`;
  const pas = $("#res-pastilla");
  pas.textContent = fo.viable ? "Recomendado" : "No viable";
  pas.className = `pastilla${fo.viable ? "" : " mala"}`;
  const t = $("#t-res");
  t.textContent = fo.viable ? fo.fecha_larga : "No encontré una fecha segura";
  t.className = `fecha${fo.viable ? "" : " mala"}`;
  $("#res-justificacion").textContent = r.justificacion || "";
  $("#res-detalle").innerHTML = (r.justificacion_detalle || []).map((d) => `<li>${escapar(d)}</li>`).join("");
  $("#m-kpi").textContent = fmt(r.kpi.valor, 2);
  $("#m-exito").textContent = pct(fo.probabilidad_exito);
  $("#m-cosecha").textContent = `${fmt(est.p10)}–${fmt(est.p90)}`;

  const hayPlan = r.plan_temporadas && (r.plan_temporadas.filas || []).length > 1;
  $("#tab-temporadas").hidden = !hayPlan;
  pintarComparacion(r);
  pintarRiesgos(r);
  if (hayPlan) pintarTemporadas(r.plan_temporadas);

  const opciones = [["rendimiento", "Rendimiento"], ["fechas", "Por fecha"], ["estados", "Estado de la planta"], ["riesgos", "Riesgos"]];
  if (hayPlan) opciones.push(["poblacion", "Temporadas"]);
  if (!opciones.some(([k]) => k === estado.vistaGrafica)) estado.vistaGrafica = "rendimiento";
  $("#chips-graficas").innerHTML = opciones.map(([k, rot]) => `<button type="button" data-grafica="${k}">${rot}</button>`).join("");
  $("#chips-cadenas").innerHTML = Object.entries(CADENAS).map(([k, rot]) => `<button type="button" data-cadena="${k}">${rot}</button>`).join("");
  elegirPestana("graficas");
  dibujar();
}

function escapar(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function elegirPestana(tab) {
  $$("#pestanas button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === tab)));
  ["graficas", "comparacion", "riesgos", "temporadas"].forEach((k) => ($(`#panel-${k}`).hidden = k !== tab));
}
$("#pestanas").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-tab]");
  if (b) elegirPestana(b.dataset.tab);
});
$("#chips-graficas").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-grafica]");
  if (b) { estado.vistaGrafica = b.dataset.grafica; dibujar(); }
});
$("#chips-cadenas").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-cadena]");
  if (b) { estado.cadena = b.dataset.cadena; dibujar(); }
});

function pintarComparacion(r) {
  $("#panel-comparacion").innerHTML = `<h3>¿Cuánto mejor es esta fecha?</h3>` + (r.comparaciones || []).map((x) => {
    const ventaja = x.ventaja_pct == null ? "" :
      `<span class="pastilla${x.ventaja_pct >= 0 ? "" : " aviso"}">la óptima es ${Math.round(x.ventaja_pct)} % mejor</span>`;
    return `<div class="fila-dato"><div><strong>${escapar(x.etiqueta)}</strong>${escapar(x.fecha_larga)}
      <p class="nota">KPI ${fmt(x.kpi, 2)} · éxito ${pct(x.probabilidad_exito)}</p></div>${ventaja}</div>`;
  }).join("");
}

function pintarRiesgos(r) {
  const filas = (r.riesgos || []).map((x) => {
    const p = x.probabilidades, per = x.perdida_esperada * 100;
    const tono = per >= 15 ? " mala" : per >= 5 ? " aviso" : "";
    return `<div class="fila-dato"><div><strong>${escapar(x.etiqueta)}</strong>
      <p class="nota">Ninguno ${pct(p["0"])} · 1 vez ${pct(p["1"])} · 2 veces ${pct(p["2"])} · 3 o más ${pct(p["3+"])}</p></div>
      <span class="pastilla${tono}">pérdida esperada ${Math.round(per)} %</span></div>`;
  }).join("");
  $("#panel-riesgos").innerHTML = `<h3>Riesgos identificados</h3>
    <p class="nota">Probabilidad de que ocurra cada evento raro durante el ciclo del cultivo (distribución de Poisson).</p>${filas || "<p>No hay eventos raros configurados.</p>"}`;
}

function pintarTemporadas(plan) {
  const filas = plan.filas.map((f) => `<tr><td>${f.temporada}</td><td>${f.fecha_siembra}</td><td>${entero(f.poblacion_esperada)}</td>
    <td>${fmt(f.cosecha_estimada, 2)}</td><td>${f.semillas_guardar}</td></tr>`).join("");
  $("#panel-temporadas").innerHTML = `
    <span class="pastilla${plan.riesgo_extincion ? " mala" : ""}">${plan.riesgo_extincion ? "Riesgo de extinción" : "Se sostiene"}</span>
    <p>${escapar(plan.recomendacion)}</p>
    ${plan.aviso_largo_plazo ? '<p class="nota">Más de 10 temporadas: las proyecciones son menos confiables.</p>' : ""}
    <div class="tabla-scroll"><table>
      <thead><tr><th>Temporada</th><th>Siembra</th><th>Plantas</th><th>Cosecha (t/ha)</th><th>Semillas a guardar</th></tr></thead>
      <tbody>${filas}</tbody></table></div>`;
}

/* ------------------------------------------------------------------ gráficas */
function dibujar() {
  const r = estado.resultado;
  if (!r || typeof Chart === "undefined") return;
  $$("#chips-graficas button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.grafica === estado.vistaGrafica)));
  $$("#chips-cadenas button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.cadena === estado.cadena)));
  $("#chips-cadenas").hidden = estado.vistaGrafica !== "estados";

  const texto = css("--texto"), suave = css("--suave"), borde = css("--borde");
  const series = [css("--serie-1"), css("--serie-2"), css("--serie-3"), css("--serie-4")];
  Chart.defaults.color = suave;
  Chart.defaults.borderColor = borde;
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.locale = "es";

  const cfg = construirGrafica(estado.vistaGrafica, r, series, texto);
  cfg.options = Object.assign({
    responsive: true, maintainAspectRatio: false, animation: { duration: 350 },
    plugins: { legend: { position: "bottom", labels: { boxWidth: 12, usePointStyle: true } } },
  }, cfg.options || {});
  cfg.options.plugins = Object.assign({ legend: { position: "bottom", labels: { boxWidth: 12, usePointStyle: true } } }, cfg.options.plugins || {});
  if (estado.grafica) estado.grafica.destroy();
  estado.grafica = new Chart($("#grafica"), cfg);
}

function eje(titulo, extra = {}) {
  return Object.assign({ title: { display: !!titulo, text: titulo }, grid: { color: css("--borde") } }, extra);
}

function construirGrafica(tipo, r, s) {
  const nota = $("#nota-grafica");
  if (tipo === "rendimiento") {
    const h = r.histograma_rendimiento, st = r.estadisticas_rendimiento, b = h.bordes;
    const medios = h.conteos.map((_, i) => (b[i] + b[i + 1]) / 2);
    nota.textContent = `Promedio: ${fmt(st.media, 2)} t/ha. Las barras oscuras son el 80 % central de los casos (${fmt(st.p10)}–${fmt(st.p90)} t/ha).`;
    return {
      type: "bar",
      data: {
        labels: medios.map((m) => fmt(m)),
        datasets: [{
          label: "Escenarios simulados", data: h.conteos, borderRadius: 3,
          backgroundColor: medios.map((m) => (m >= st.p10 && m <= st.p90 ? s[0] : s[0] + "55")),
        }],
      },
      options: { plugins: { legend: { display: false } }, scales: { x: eje("Cosecha (t/ha)"), y: eje("Cantidad de escenarios") } },
    };
  }
  if (tipo === "fechas") {
    const fechas = Object.keys(r.resultados_por_fecha), opt = r.fecha_optima.fecha;
    nota.textContent = "Probabilidad de buena cosecha según el día de siembra. El punto grande es la fecha recomendada.";
    return {
      type: "line",
      data: {
        labels: fechas.map((f) => f.slice(8, 10) + "/" + f.slice(5, 7) + "/" + f.slice(2, 4)),
        datasets: [{
          label: "Probabilidad de éxito (%)", data: fechas.map((f) => r.resultados_por_fecha[f].probabilidad_exito * 100),
          borderColor: s[0], backgroundColor: s[0], tension: .3,
          pointRadius: fechas.map((f) => (f === opt ? 8 : 3)), pointBackgroundColor: fechas.map((f) => (f === opt ? s[1] : s[0])),
        }],
      },
      options: { plugins: { legend: { display: false } }, scales: { x: eje("Fecha de siembra"), y: eje("Probabilidad (%)", { min: 0, max: 100 }) } },
    };
  }
  if (tipo === "estados") {
    const cad = r.evolucion_estados[estado.cadena] || Object.values(r.evolucion_estados)[0];
    const n = Object.values(cad)[0].length;
    nota.textContent = "Probabilidad de cada estado semana a semana (cadena de Márkov).";
    return {
      type: "line",
      data: {
        labels: Array.from({ length: n }, (_, i) => i),
        datasets: Object.entries(cad).map(([est, serie], j) => ({
          label: est, data: serie.map((v) => v * 100), borderColor: s[j % 4], backgroundColor: s[j % 4], pointRadius: 0, tension: .3,
        })),
      },
      options: { scales: { x: eje("Semana"), y: eje("Probabilidad (%)", { min: 0, max: 100 }) } },
    };
  }
  if (tipo === "riesgos") {
    const rs = r.riesgos || [], claves = [["0", "Ninguno"], ["1", "1 vez"], ["2", "2 veces"], ["3+", "3 o más"]];
    nota.textContent = "Cuántas veces podría ocurrir cada evento durante el ciclo (Poisson).";
    return {
      type: "bar",
      data: {
        labels: rs.map((x) => x.etiqueta),
        datasets: claves.map(([k, rot], j) => ({ label: rot, data: rs.map((x) => x.probabilidades[k] * 100), backgroundColor: s[j % 4], borderRadius: 3 })),
      },
      options: { scales: { x: eje(""), y: eje("Probabilidad (%)", { min: 0, max: 100 }) } },
    };
  }
  // población (Galton-Watson)
  const plan = r.plan_temporadas, tr = plan.trayectoria, xs = tr.media.map((_, i) => `T${i}`);
  nota.textContent = "Plantas esperadas por temporada; la banda es el 80 % de los casos.";
  return {
    type: "line",
    data: {
      labels: xs,
      datasets: [
        { label: "p10", data: tr.p10, borderColor: "transparent", pointRadius: 0, fill: false },
        { label: "80 % de los casos", data: tr.p90, borderColor: "transparent", backgroundColor: s[0] + "33", pointRadius: 0, fill: "-1" },
        { label: "Población esperada", data: tr.media, borderColor: s[0], backgroundColor: s[0], tension: .3 },
        { label: "Capacidad del terreno", data: xs.map(() => plan.capacidad), borderColor: css("--suave"), borderDash: [6, 4], pointRadius: 0 },
      ],
    },
    options: {
      plugins: { legend: { position: "bottom", labels: { boxWidth: 12, usePointStyle: true, filter: (it) => it.text !== "p10" } } },
      scales: { x: eje("Temporada"), y: eje("Plantas", { beginAtZero: true }) },
    },
  };
}

matchMedia("(prefers-color-scheme: dark)").addEventListener("change", dibujar);

/* ------------------------------------------------------------------ asistente */
function abrirAsistente() { $("#hoja").hidden = false; setTimeout(() => $("#pregunta").focus(), 50); }
function cerrarAsistente() { $("#hoja").hidden = true; }
$("#btn-asistente").addEventListener("click", abrirAsistente);
$$("#hoja [data-cerrar]").forEach((el) => el.addEventListener("click", cerrarAsistente));
document.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrarAsistente(); });

function sugerir(lista) {
  $("#sugerencias").innerHTML = (lista || []).filter((s) => !NO_APLICA_WEB.includes(s)).slice(0, 3)
    .map((s) => `<button type="button">${escapar(s)}</button>`).join("");
}
$("#sugerencias").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (b) preguntar(b.textContent);
});
$("#form-preguntar").addEventListener("submit", (e) => {
  e.preventDefault();
  const t = $("#pregunta").value.trim();
  if (t) { $("#pregunta").value = ""; preguntar(t); }
});

async function preguntar(texto) {
  const chat = $("#chat");
  chat.insertAdjacentHTML("beforeend", `<p class="yo">${escapar(texto)}</p>`);
  const m = await pedir("preguntar", { texto });
  const r = m.ok ? m.respuesta : { respuesta: m.errores[0], sugerencias: [] };
  chat.insertAdjacentHTML("beforeend", (r.tema ? `<p class="tema">${escapar(r.tema)}</p>` : "") +
    `<p>${escapar(r.respuesta)}</p>` + (r.mas ? `<p class="nota">${escapar(r.mas)}</p>` : ""));
  chat.scrollTop = chat.scrollHeight;
  sugerir(r.sugerencias);
}

/* ------------------------------------------------------------------ inicio */
history.replaceState({ vista: "inicio" }, "", location.pathname);
