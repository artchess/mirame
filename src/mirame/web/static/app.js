// Mírame — app local. Sin dependencias ni compilación: una página con tres vistas.
"use strict";

const $ = (sel, raiz = document) => raiz.querySelector(sel);
const vista = $("#vista");
let ESTADO = null;          // /api/estado
let sondeo = null;          // temporizador de trabajos

// ---------------------------------------------------------------- utilidades
async function api(ruta, opciones = {}) {
  const r = await fetch(`/api/${ruta}`, {
    ...opciones,
    headers: { "Content-Type": "application/json", ...(opciones.headers || {}) },
    body: opciones.body && typeof opciones.body !== "string" && !(opciones.body instanceof Blob)
      ? JSON.stringify(opciones.body) : opciones.body,
  });
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(datos.error || `Error ${r.status}`);
  return datos;
}
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (v, d = 1) => v == null ? "—" : Number(v).toLocaleString("es", { minimumFractionDigits: d, maximumFractionDigits: d });
function hms(s) {
  if (s == null) return "—";
  s = Math.round(s);
  const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(x).padStart(2, "0")}` : `${m}:${String(x).padStart(2, "0")}`;
}
const tamano = mb => mb >= 1000 ? `${num(mb / 1000)} GB` : `${num(mb, 0)} MB`;
function fecha(iso) {
  if (!iso) return "";
  const d = new Date(`${iso.slice(0, 10)}T12:00:00`);
  return isNaN(d) ? iso : d.toLocaleDateString("es", { day: "numeric", month: "short", year: "numeric" });
}

function toast(texto, ms = 3500) {
  const t = $("#toast");
  t.textContent = texto; t.hidden = false;
  clearTimeout(toast.t); toast.t = setTimeout(() => { t.hidden = true; }, ms);
}

// Modal de confirmación: devuelve una promesa con true/false.
function confirmar({ titulo, texto, si = "Aceptar", peligro = false }) {
  const m = $("#modal");
  $("#modal-titulo").textContent = titulo;
  $("#modal-texto").innerHTML = texto;
  const bSi = $("#modal-si"), bNo = $("#modal-no");
  bSi.textContent = si;
  bSi.className = peligro ? "peligro" : "";
  m.hidden = false;
  bNo.focus();
  return new Promise(resolver => {
    const cerrar = v => { m.hidden = true; bSi.onclick = bNo.onclick = m.onclick = document.onkeydown = null; resolver(v); };
    bSi.onclick = () => cerrar(true);
    bNo.onclick = () => cerrar(false);
    m.onclick = e => { if (e.target === m) cerrar(false); };
    document.onkeydown = e => { if (e.key === "Escape") cerrar(false); };
  });
}

// ---------------------------------------------------------------- enrutador
const VISTAS = { "": verNuevo, biblioteca: verBiblioteca, ajustes: verAjustes };
async function enrutar() {
  const nombre = location.hash.replace(/^#\/?/, "").split("/")[0];
  const fn = VISTAS[nombre] || verNuevo;
  for (const a of document.querySelectorAll("[data-nav]"))
    a.classList.toggle("activo", a.dataset.nav === (nombre || "nuevo"));
  clearInterval(sondeo);
  ESTADO = await api("estado").catch(() => ESTADO);
  if (ESTADO) {
    $("#version").textContent = ESTADO.version;
    $("#carpeta-datos").textContent = `Datos en ${ESTADO.datos}`;
  }
  await fn();
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", enrutar);

function plantilla(id) {
  vista.replaceChildren($(`#${id}`).content.cloneNode(true));
}

// Globo en «Biblioteca» con los trabajos en curso, en todas las vistas.
async function revisarGlobo() {
  const trabajos = await api("trabajos").catch(() => []);
  const activos = trabajos.filter(t => t.estado === "en_cola" || t.estado === "corriendo").length;
  const g = $("#globo");
  g.hidden = !activos; g.textContent = activos;
  return trabajos;
}
setInterval(revisarGlobo, 4000);

// ---------------------------------------------------------------- Nuevo análisis
async function verNuevo() {
  plantilla("t-nuevo");
  const f = $("#f-nuevo");
  const aj = ESTADO?.ajustes || {};
  const op = $("#op-lecturas"), chk = f.separar_lecturas;
  if (aj.puede_separar_lecturas) {
    chk.checked = true;
  } else {
    chk.disabled = true;
    op.classList.add("apagado");
    $("#lecturas-nota").innerHTML = `Necesita una clave de IA (Groq es gratis). <a href="#/ajustes">Agrégala en Ajustes</a>. Sin ella el análisis funciona igual, solo que la lectura bíblica cuenta como mirar abajo.`;
  }
  const chkE = f.estructura;
  if (aj.puede_analizar_estructura) {
    chkE.checked = true;
  } else {
    chkE.disabled = true;
    $("#op-estructura").classList.add("apagado");
    $("#estructura-nota").innerHTML = `Necesita una clave de IA. <a href="#/ajustes">Agrégala en Ajustes</a>.`;
  }
  if (ESTADO && !ESTADO.ffmpeg) {
    mostrarError("error-nuevo", "No encuentro ffmpeg en tu computadora. Instálalo antes de analizar (ver README).");
  }

  let archivo = null;
  $("#archivo").addEventListener("change", e => {
    archivo = e.target.files[0] || null;
    $("#archivo-elegido").textContent = archivo ? `${archivo.name} (${tamano(archivo.size / 1e6)})` : "";
    if (archivo) f.origen.value = "";
  });
  f.origen.addEventListener("input", () => { if (f.origen.value) { archivo = null; $("#archivo-elegido").textContent = ""; } });

  f.addEventListener("submit", async e => {
    e.preventDefault();
    ocultarError("error-nuevo");
    const datos = Object.fromEntries(new FormData(f));
    datos.separar_lecturas = chk.checked;
    datos.estructura = chkE.checked;
    datos.solo_cabeza = f.solo_cabeza.checked;
    const b = $("#b-analizar");
    b.disabled = true;
    try {
      if (archivo) {
        b.textContent = "Subiendo el video…";
        const r = await fetch(`/api/subir?nombre=${encodeURIComponent(archivo.name)}`, { method: "POST", body: archivo });
        const j = await r.json();
        if (!r.ok) throw new Error(j.error || "No se pudo subir el video.");
        datos.origen = j.ruta;
        if (!datos.titulo) datos.titulo = archivo.name.replace(/\.[^.]+$/, "");
      }
      if (!datos.origen) throw new Error("Pega el enlace de YouTube o elige un archivo de video.");
      await api("analizar", { method: "POST", body: datos });
      location.hash = "#/biblioteca";
    } catch (err) {
      mostrarError("error-nuevo", err.message);
      b.disabled = false; b.textContent = "Analizar sermón";
    }
  });
  f.origen.focus();
}

function mostrarError(id, texto) { const el = $(`#${id}`); if (el) { el.textContent = texto; el.hidden = false; } }
function ocultarError(id) { const el = $(`#${id}`); if (el) el.hidden = true; }

// ---------------------------------------------------------------- Biblioteca
async function verBiblioteca() {
  plantilla("t-biblioteca");
  await Promise.all([pintarTrabajos(), pintarLista(), pintarAlmacen()]);
  let habiaActivos = true;
  sondeo = setInterval(async () => {
    const activos = await pintarTrabajos();
    if (habiaActivos && !activos) pintarLista();   // algo terminó: refrescar la lista
    habiaActivos = activos;
  }, 1000);
}

const TIPOS_TRABAJO = { lecturas: "Separar lectura bíblica y oración", estructura: "Analizar la estructura del sermón" };
const ETAPAS = { en_cola: "En cola", corriendo: "Analizando", listo: "Listo", error: "Error", cancelado: "Cancelado" };
let ultimosTrabajos = "";

async function pintarTrabajos() {
  const trabajos = await revisarGlobo();
  const caja = $("#trabajos");
  if (!caja) return false;
  const firma = JSON.stringify(trabajos);
  if (firma !== ultimosTrabajos) {
    ultimosTrabajos = firma;
    caja.innerHTML = trabajos.map(t => {
      const activo = t.estado === "en_cola" || t.estado === "corriendo";
      const pct = t.fraccion != null ? Math.round(t.fraccion * 100) : null;
      return `<div class="tarjeta trabajo ${t.estado}">
        <div class="trabajo-cabeza">
          <div>
            <div class="trabajo-titulo">${esc(t.titulo)}</div>
            <div class="trabajo-detalle">${TIPOS_TRABAJO[t.tipo] || "Nuevo análisis"}</div>
          </div>
          <div>
            <span class="etiqueta ${t.estado}">${ETAPAS[t.estado]}</span>
            ${activo ? `<button class="texto rojo chico" data-cancelar="${t.id}">Cancelar</button>` : ""}
            ${t.estado === "listo" && t.analisis ? `<a class="boton chico" href="/analisis/${encodeURIComponent(t.analisis)}/reporte.html${t.tipo === "estructura" ? "?vista=sermon" : ""}">Abrir reporte</a>` : ""}
          </div>
        </div>
        ${activo ? `<div class="barra-avance ${pct == null ? "indef" : ""}"><span style="width:${pct ?? 0}%"></span></div>
          <div class="trabajo-detalle"><b>${esc(t.etapa || "En cola")}</b>${t.mensaje ? ` · ${esc(t.mensaje)}` : ""}${pct != null ? ` · ${pct} %` : ""}</div>` : ""}
        ${t.estado === "error" ? `<div class="error">${esc(t.error)}</div>` : ""}
      </div>`;
    }).join("");
  }
  return trabajos.some(t => t.estado === "en_cola" || t.estado === "corriendo");
}

document.addEventListener("click", async e => {
  const c = e.target.closest("[data-cancelar]");
  if (!c) return;
  const ok = await confirmar({ titulo: "¿Cancelar el análisis?", texto: "Se pierde lo avanzado de este trabajo.", si: "Cancelar análisis", peligro: true });
  if (ok) { await api(`trabajos/${c.dataset.cancelar}/cancelar`, { method: "POST" }); ultimosTrabajos = ""; pintarTrabajos(); }
});

async function pintarLista() {
  const lista = await api("analisis").catch(err => { toast(err.message); return []; });
  const caja = $("#lista");
  if (!caja) return;
  if (!lista.length) {
    caja.innerHTML = `<div class="tarjeta vacio">Todavía no hay análisis.<br><br><a href="#/" class="boton">Analizar el primer sermón</a></div>`;
    return;
  }
  const puedeSeparar = ESTADO?.ajustes?.puede_separar_lecturas;
  const puedeEstructura = ESTADO?.ajustes?.puede_analizar_estructura;
  caja.innerHTML = lista.map(a => {
    const listo = a.pct_congregacion != null;
    const reparto = listo ? `<div class="reparto">
        <span style="width:${a.pct_congregacion}%;background:var(--verde)"></span>
        <span style="width:${a.pct_notas ?? 0}%;background:var(--ambar)"></span>
        <span style="width:${a.pct_biblia ?? 0}%;background:var(--azul)"></span></div>` : "";
    const origen = a.origen && a.origen.startsWith("http")
      ? `<a href="${esc(a.origen)}" target="_blank" rel="noopener">YouTube</a>` : "archivo local";
    return `<div class="tarjeta analisis">
      <div>
        <div class="analisis-titulo">${esc(a.titulo)}</div>
        <div class="analisis-meta">${fecha(a.creado)} · ${hms(a.duracion)} analizados${a.inicio ? ` desde el ${hms(a.inicio)}` : ""} · ${origen} · ${tamano(a.megabytes)}
          ${a.estado !== "listo" ? ` · <span class="etiqueta ${a.estado}">${a.estado === "en_proceso" ? "En proceso" : "Incompleto"}</span>` : ""}</div>
        ${listo ? `<div class="cifras">
          <div class="cifra verde"><b class="num">${num(a.pct_congregacion)} %</b><span>congregación</span></div>
          <div class="cifra ambar"><b class="num">${num(a.pct_notas)} %</b><span>${a.pct_biblia != null ? "notas" : "abajo"}</span></div>
          ${a.pct_biblia != null ? `<div class="cifra azul"><b class="num">${num(a.pct_biblia)} %</b><span>Biblia</span></div>` : ""}
          ${a.mirada_media != null ? `<div class="cifra"><b class="num">${num(a.mirada_media)} s</b><span>por mirada</span></div>` : ""}
        </div>${reparto}` : ""}
      </div>
      <div class="analisis-acciones">
        ${a.tiene_reporte ? `<a class="boton" href="/analisis/${encodeURIComponent(a.id)}/reporte.html">Abrir reporte</a>` : ""}
        ${listo && !a.con_lecturas ? `<button class="secundario chico" data-separar="${esc(a.id)}" ${puedeSeparar ? "" : "disabled title='Agrega una clave de IA en Ajustes'"}>Separar lectura bíblica</button>` : ""}
        ${listo && a.con_estructura ? `<a class="boton secundario chico" href="/analisis/${encodeURIComponent(a.id)}/reporte.html?vista=sermon">Ver estructura</a>` : ""}
        ${listo && !a.con_estructura ? `<button class="secundario chico" data-estructura="${esc(a.id)}" ${puedeEstructura ? "" : "disabled title='Agrega una clave de IA en Ajustes'"}>Analizar estructura</button>` : ""}
        <button class="texto rojo chico" data-borrar="${esc(a.id)}" data-titulo="${esc(a.titulo)}" data-mb="${a.megabytes}">Borrar</button>
      </div>
    </div>`;
  }).join("");

  caja.onclick = async e => {
    const b = e.target.closest("[data-borrar]");
    if (b) {
      const ok = await confirmar({
        titulo: "¿Borrar este análisis?",
        texto: `<b>${esc(b.dataset.titulo)}</b><br>Se borran sus datos, el reporte, las capturas y el video recortado (${tamano(+b.dataset.mb)}). No se puede deshacer.`,
        si: "Borrar", peligro: true,
      });
      if (!ok) return;
      try { await api(`analisis/${encodeURIComponent(b.dataset.borrar)}`, { method: "DELETE" }); toast("Análisis borrado."); }
      catch (err) { toast(err.message); }
      pintarLista(); pintarAlmacen();
      return;
    }
    const s = e.target.closest("[data-separar]");
    if (s) {
      try { await api(`analisis/${encodeURIComponent(s.dataset.separar)}/lecturas`, { method: "POST" }); ultimosTrabajos = ""; pintarTrabajos(); toast("Separando la lectura bíblica…"); }
      catch (err) { toast(err.message); }
      return;
    }
    const es = e.target.closest("[data-estructura]");
    if (es) {
      try { await api(`analisis/${encodeURIComponent(es.dataset.estructura)}/estructura`, { method: "POST" }); ultimosTrabajos = ""; pintarTrabajos(); toast("Analizando la estructura del sermón…"); }
      catch (err) { toast(err.message); }
    }
  };
}

async function pintarAlmacen() {
  const caja = $("#almacen");
  if (!caja || !ESTADO) return;
  const d = (await api("estado").catch(() => ESTADO)).descargas;
  caja.innerHTML = `<span>Videos completos descargados de YouTube (caché): <b>${d.archivos}</b> · ${tamano(d.megabytes)}.
      Se reutilizan si vuelves a analizar el mismo enlace; borrarlos no afecta los análisis.</span>
    ${d.archivos ? `<button class="secundario chico" id="vaciar">Vaciar caché</button>` : ""}`;
  const b = $("#vaciar");
  if (b) b.onclick = async () => {
    const ok = await confirmar({ titulo: "¿Vaciar la caché de descargas?", texto: `Se borran ${d.archivos} videos (${tamano(d.megabytes)}). Tus análisis y reportes no se tocan.`, si: "Vaciar", peligro: true });
    if (!ok) return;
    const r = await api("descargas/vaciar", { method: "POST" });
    toast(`${r.borrados} videos borrados.`);
    pintarAlmacen();
  };
}

// ---------------------------------------------------------------- Ajustes
async function verAjustes() {
  plantilla("t-ajustes");
  const f = $("#f-ajustes");
  const aj = await api("ajustes");
  for (const k of ["groq_clave", "openai_clave", "llm_url", "llm_clave", "llm_modelo"]) f[k].value = aj[k] || "";
  const otro = !!aj.llm_url;
  f.proveedor.value = otro ? "otro" : "groq";
  $("#otro-proveedor").hidden = !otro;
  if (aj.desde_entorno?.length) {
    $("#guardado-en").textContent = `Algunos valores vienen de variables de entorno y tienen prioridad: ${aj.desde_entorno.join(", ")}.`;
  } else {
    $("#guardado-en").textContent = `Se guardan solo en tu computadora (${ESTADO?.datos || ""}/configuracion.json).`;
  }

  for (const r of f.querySelectorAll("[name=proveedor]"))
    r.addEventListener("change", () => { $("#otro-proveedor").hidden = f.proveedor.value !== "otro"; });

  f.addEventListener("click", async e => {
    const ver = e.target.closest("[data-ver]");
    if (ver) {
      const input = f[ver.dataset.ver];
      input.type = input.type === "password" ? "text" : "password";
      ver.textContent = input.type === "password" ? "Ver" : "Ocultar";
    }
    const probar = e.target.closest("[data-probar]");
    if (probar) {
      const tipo = probar.dataset.probar;
      const caja = $(`#prueba-${tipo}`);
      caja.className = "resultado-prueba"; caja.textContent = "Probando…";
      try {
        const r = await api("ajustes/probar", { method: "POST", body: {
          tipo, groq_clave: f.groq_clave.value, openai_clave: f.openai_clave.value,
          llm_url: f.llm_url.value, llm_clave: f.llm_clave.value } });
        caja.className = `resultado-prueba ${r.ok ? "ok" : "mal"}`;
        caja.textContent = (r.ok ? "✓ " : "✗ ") + r.mensaje;
        if (r.ok && tipo === "llm") $("#modelos").innerHTML = r.modelos.map(m => `<option value="${esc(m)}">`).join("");
      } catch (err) { caja.className = "resultado-prueba mal"; caja.textContent = `✗ ${err.message}`; }
    }
  });

  f.addEventListener("submit", async e => {
    e.preventDefault();
    ocultarError("error-ajustes");
    const otro = f.proveedor.value === "otro";
    if (otro && (!f.llm_url.value || !f.llm_clave.value || !f.llm_modelo.value)) {
      mostrarError("error-ajustes", "Para otro proveedor completa la URL, la clave y el modelo.");
      return;
    }
    try {
      await api("ajustes", { method: "POST", body: {
        groq_clave: f.groq_clave.value,
        openai_clave: f.openai_clave.value,
        llm_url: otro ? f.llm_url.value : "",
        llm_clave: otro ? f.llm_clave.value : "",
        llm_modelo: otro ? f.llm_modelo.value : "",
      } });
      toast("Ajustes guardados.");
      ESTADO = await api("estado");
      verAjustes();
    } catch (err) { mostrarError("error-ajustes", err.message); }
  });
}

enrutar();
