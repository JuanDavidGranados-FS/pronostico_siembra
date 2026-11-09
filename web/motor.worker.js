/* Motor en segundo plano: carga Python (Pyodide), numpy y el código del proyecto, y atiende las llamadas de la
   página sin congelar la pantalla. matplotlib (gráficas y exportes) y openpyxl (Excel) se cargan solo la primera vez
   que se necesitan. */
const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.29.5/full/";
const VERSION = "2.0.0";

let pyodide = null;
let motor = null;
const cargados = new Set();

const avisar = (tipo, datos = {}) => self.postMessage({ tipo, ...datos });
const texto = (err) => String(err && err.message ? err.message : err);

async function asegurar(paquetes = []) {
  for (const p of paquetes) {
    if (cargados.has(p)) continue;
    if (p === "openpyxl") {
      await pyodide.loadPackage("micropip");
      await pyodide.pyimport("micropip").install("openpyxl");
    } else {
      await pyodide.loadPackage(p);
    }
    cargados.add(p);
  }
}

async function iniciar(guardado) {
  try {
    avisar("estado", { texto: "Descargando Python…", avance: 10 });
    importScripts(PYODIDE_URL + "pyodide.js");
    pyodide = await loadPyodide({ indexURL: PYODIDE_URL });

    avisar("estado", { texto: "Cargando librerías matemáticas…", avance: 55 });
    await asegurar(["numpy"]);

    avisar("estado", { texto: "Preparando el motor de simulación…", avance: 85 });
    const resp = await fetch(`siembra.zip?v=${VERSION}`);
    if (!resp.ok) throw new Error(`No se pudo descargar el motor (${resp.status})`);
    pyodide.unpackArchive(await resp.arrayBuffer(), "zip", { extractDir: "/home/pyodide/siembra" });
    pyodide.runPython("import sys; sys.path.insert(0, '/home/pyodide/siembra')");
    motor = pyodide.pyimport("motor");

    const r = JSON.parse(motor.iniciar(guardado || ""));
    if (!r.ok) throw new Error(r.error);
    avisar("listo", { inicio: r.valor });
  } catch (err) {
    avisar("fallo", { texto: texto(err) });
  }
}

function guardar() {
  avisar("guardado", { datos: motor.instantanea() });
}

self.onmessage = async (e) => {
  const m = e.data;
  if (m.tipo === "iniciar") return iniciar(m.guardado);
  const responder = (r) => avisar("respuesta", { id: m.id, ...r });
  if (!motor) return responder({ ok: false, error: "El motor todavía se está cargando." });
  try {
    if (m.tipo === "simular") {
      const r = JSON.parse(motor.simular(JSON.stringify(m.datos), (i, n) => avisar("progreso", { id: m.id, i, n })));
      responder(r);
      if (r.ok) guardar();
    } else if (m.tipo === "exportar") {
      avisar("ocupado", { id: m.id, texto: "Preparando el archivo…" });
      await asegurar(m.ext === ".xlsx" ? ["matplotlib", "openpyxl"] : ["matplotlib"]);
      const r = JSON.parse(motor.exportar(m.ext));
      if (!r.ok) return responder(r);
      const bytes = pyodide.FS.readFile(r.valor);
      self.postMessage({ tipo: "respuesta", id: m.id, ok: true, bytes }, [bytes.buffer]);
    } else if (m.tipo === "archivo") {
      // Escribe un archivo del usuario en el sistema de archivos de Python (p. ej. un histórico CSV/Excel).
      if (/\.xls[xm]$/i.test(m.nombre)) await asegurar(["openpyxl"]);
      const ruta = `/tmp/${m.nombre.replace(/[^\w.\-]/g, "_")}`;
      pyodide.FS.writeFile(ruta, new Uint8Array(m.bytes));
      responder(JSON.parse(motor[m.funcion](ruta)));
    } else if (m.tipo === "llamar") {
      if (m.necesita && m.necesita.length) {
        avisar("ocupado", { id: m.id, texto: "Cargando gráficas…" });
        await asegurar(m.necesita);
      }
      const r = JSON.parse(motor[m.funcion](...(m.args || [])));
      responder(r);
      if (m.guardar && r.ok) guardar();
    }
  } catch (err) {
    responder({ ok: false, error: texto(err) });
  }
};
