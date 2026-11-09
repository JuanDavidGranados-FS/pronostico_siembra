/* Motor de simulación en segundo plano: carga Python (Pyodide) + numpy y el código del proyecto,
   y atiende los pedidos de la página sin congelar la pantalla. */
const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.29.5/full/";
const VERSION = "1.2.0";

let motor = null;

function avisar(tipo, datos = {}) {
  self.postMessage({ tipo, ...datos });
}

async function iniciar() {
  try {
    avisar("estado", { texto: "Descargando Python…", avance: 10 });
    importScripts(PYODIDE_URL + "pyodide.js");
    const pyodide = await loadPyodide({ indexURL: PYODIDE_URL });

    avisar("estado", { texto: "Cargando librerías matemáticas…", avance: 55 });
    await pyodide.loadPackage("numpy");

    avisar("estado", { texto: "Preparando el motor de simulación…", avance: 85 });
    const resp = await fetch(`siembra.zip?v=${VERSION}`);
    if (!resp.ok) throw new Error(`No se pudo descargar el motor (${resp.status})`);
    pyodide.unpackArchive(await resp.arrayBuffer(), "zip", { extractDir: "/home/pyodide/siembra" });
    pyodide.runPython("import sys; sys.path.insert(0, '/home/pyodide/siembra')");
    motor = pyodide.pyimport("motor");

    avisar("listo", {
      catalogo: JSON.parse(motor.catalogo()),
      sugerencias: JSON.parse(motor.sugerencias_iniciales()),
    });
  } catch (err) {
    avisar("fallo", { texto: String(err && err.message ? err.message : err) });
  }
}

self.onmessage = (e) => {
  const { tipo, id } = e.data;
  if (!motor) {
    avisar("respuesta", { id, ok: false, errores: ["El motor todavía se está cargando."] });
    return;
  }
  try {
    if (tipo === "simular") {
      const progreso = (i, n) => avisar("progreso", { id, i, n });
      const r = JSON.parse(motor.simular(JSON.stringify(e.data.entrada), progreso));
      avisar("respuesta", { id, ...r });
    } else if (tipo === "preguntar") {
      avisar("respuesta", { id, ok: true, respuesta: JSON.parse(motor.preguntar(e.data.texto)) });
    }
  } catch (err) {
    avisar("respuesta", { id, ok: false, errores: [String(err && err.message ? err.message : err)] });
  }
};

iniciar();
