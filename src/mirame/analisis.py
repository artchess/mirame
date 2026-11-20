"""Calibrar, clasificar y resumir. Todo se puede recalcular desde fotogramas.csv."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import __version__
from .video import formato_tiempo

CONGREGACION, ABAJO, SIN_DATO, EXCLUIDO = "congregacion", "abajo", "sin_dato", "excluido"
LIMITE_SIN_DATO = 30.0  # % de segundos sin rostro a partir del cual el resultado es poco confiable


@dataclass
class Parametros:
    fps: float = 4.0
    umbral: float = 15.0
    base: float | None = None                       # pitch "mirando a la congregación" fijado a mano
    calibrar: tuple[float, float] | None = None     # rango (s) donde calibrar en vez de todo el sermón
    excluir: list[tuple[float, float]] = field(default_factory=list)
    ancho_minimo: int = 0                           # rostros más angostos cuentan como sin dato
    umbral_ojos: float | None = 0.45                # puntaje de ojos bajados; None = solo la cabeza


def calibrar(df: pd.DataFrame, p: Parametros) -> tuple[float, str]:
    if p.base is not None:
        return float(p.base), "manual"
    validos = df[df.rostro & ~df.excluido_]
    if p.calibrar:
        a, b = p.calibrar
        en_rango = validos[(validos.t >= a) & (validos.t < b)]
        if len(en_rango):
            return float(en_rango.pitch.median()), f"mediana {formato_tiempo(a)}–{formato_tiempo(b)}"
    if not len(validos):
        return 0.0, "sin datos"
    return float(validos.pitch.median()), "mediana del sermón"


def clasificar(df: pd.DataFrame, p: Parametros) -> tuple[pd.DataFrame, float, str]:
    """Agrega la columna `clase` a fotogramas. Devuelve (df, pitch_base, metodo)."""
    df = df.copy()
    df["rostro"] = df.rostro.astype(bool)
    excl = np.zeros(len(df), bool)
    for a, b in p.excluir:
        excl |= (df.t >= a) & (df.t < b)
    df["excluido_"] = excl
    if p.ancho_minimo:
        df.loc[df.ancho_rostro < p.ancho_minimo, "rostro"] = False

    base, metodo = calibrar(df, p)
    corte = base + p.umbral
    abajo = (df.pitch > corte).values
    if p.umbral_ojos is not None and "ojos" in df.columns:
        # Ojos bajados aunque la cabeza siga recta: lectura con la mirada.
        abajo = abajo | (df.ojos.fillna(-1) >= p.umbral_ojos).values
    clase = np.where(abajo, ABAJO, CONGREGACION)
    clase = np.where(df.rostro, clase, SIN_DATO)
    clase = np.where(df.excluido_, EXCLUIDO, clase)
    df["clase"] = clase
    return df.drop(columns="excluido_"), base, metodo


def por_segundo(df: pd.DataFrame, corte: float) -> pd.DataFrame:
    """Una fila por segundo con la clase mayoritaria. En empate entre congregación y
    abajo decide el pitch promedio; en empate con sin_dato gana la clase con dato."""
    filas = []
    seg = np.floor(df.t.values + 1e-6).astype(int)
    for s, grupo in df.groupby(seg, sort=True):
        cuentas = grupo.clase.value_counts()
        validos = grupo[grupo.clase.isin([CONGREGACION, ABAJO])]
        pitch = round(float(validos.pitch.mean()), 2) if len(validos) else None
        ojos = (round(float(validos.ojos.mean()), 3)
                if "ojos" in grupo.columns and len(validos) and validos.ojos.notna().any() else None)
        if cuentas.get(EXCLUIDO, 0) * 2 >= len(grupo):
            clase = EXCLUIDO
        else:
            c, a, n = (cuentas.get(k, 0) for k in (CONGREGACION, ABAJO, SIN_DATO))
            if max(c, a) == 0 or n > c + a:
                clase = SIN_DATO
            elif c > a:
                clase = CONGREGACION
            elif a > c:
                clase = ABAJO
            else:
                clase = ABAJO if pitch is not None and pitch > corte else CONGREGACION
        filas.append({"t": int(s), "clase": clase, "pitch": pitch, "ojos": ojos,
                      "n_fotogramas_validos": int(len(validos))})
    return pd.DataFrame(filas, columns=["t", "clase", "pitch", "ojos", "n_fotogramas_validos"])


def episodios(df: pd.DataFrame, fps: float) -> list[dict]:
    """Rachas de fotogramas consecutivos en `abajo`."""
    salida, inicio, n = [], None, 0
    for t, clase in zip(df.t.values, df.clase.values, strict=True):
        if clase == ABAJO:
            if inicio is None:
                inicio, n = float(t), 0
            n += 1
        elif inicio is not None:
            salida.append({"inicio": round(inicio, 3), "duracion": round(n / fps, 3)})
            inicio = None
    if inicio is not None:
        salida.append({"inicio": round(inicio, 3), "duracion": round(n / fps, 3)})
    return salida


def miradas(df: pd.DataFrame, fps: float, minimo: float = 1.0) -> list[dict]:
    """Tramos mirando a la congregación. Una mirada se corta solo cuando baja a sus notas
    `minimo` segundos o más, o cuando el rostro se pierde ese tiempo; los vistazos y
    parpadeos más cortos no la cortan."""
    clase = df.clase.values
    t = df.t.values
    n = len(clase)
    grupo = np.where(clase == CONGREGACION, 0, np.where(clase == ABAJO, 1, 2))
    corte = np.zeros(n, bool)
    i = 0
    while i < n:
        j = i
        while j < n and grupo[j] == grupo[i]:
            j += 1
        if grupo[i] != 0 and (j - i) / fps >= minimo:
            corte[i:j] = True
        i = j
    salida = []
    i = 0
    while i < n:
        if corte[i]:
            i += 1
            continue
        j = i
        while j < n and not corte[j]:
            j += 1
        dentro = np.flatnonzero(grupo[i:j] == 0)
        if len(dentro):
            a, b = i + dentro[0], i + dentro[-1]
            dur = (b - a + 1) / fps
            if dur >= minimo:
                salida.append({"inicio": round(float(t[a]), 3), "duracion": round(dur, 3)})
        i = j
    return salida


def _contacto(df: pd.DataFrame, fps: float) -> dict | None:
    ms = miradas(df, fps)
    if not ms:
        return None
    d = np.array([m["duracion"] for m in ms])
    mayor = max(ms, key=lambda m: (m["duracion"], -m["inicio"]))
    return {
        "miradas": len(ms),
        "duracion_media": round(float(d.mean()), 2),
        "duracion_mediana": round(float(np.median(d)), 2),
        "mirada_mas_larga": {"duracion": mayor["duracion"], "inicio": mayor["inicio"],
                             "minuto": formato_tiempo(mayor["inicio"])},
        "lista": ms,
    }


def en_tramos(t, tramos) -> np.ndarray:
    t = np.asarray(t, float)
    dentro = np.zeros(len(t), bool)
    for a, b in tramos:
        dentro |= (t >= a) & (t < b)
    return dentro


def _biblia(seg: pd.DataFrame, largos: list[dict], lecturas, con_dato: int, pct) -> dict:
    """Separa lo que mira abajo leyendo la Biblia de lo demás (notas, manuscrito)."""
    en_lectura = en_tramos(seg.t.values + 0.5, lecturas)
    validos = seg.clase.isin([CONGREGACION, ABAJO]).values
    abajo = (seg.clase == ABAJO).values
    fuera = [e for e in largos if not en_tramos([e["inicio"] + e["duracion"] / 2], lecturas)[0]]
    mayor = max(fuera, key=lambda e: (e["duracion"], -e["inicio"]), default=None)
    return {
        "tramos": len(lecturas),
        "segundos_lectura": int((en_lectura & validos).sum()),
        "pct_del_sermon": pct(int((en_lectura & validos).sum()), con_dato),
        "pct_abajo_leyendo_biblia": pct(int((abajo & en_lectura).sum()), con_dato),
        "pct_abajo_fuera_de_biblia": pct(int((abajo & ~en_lectura).sum()), con_dato),
        "pct_congregacion_fuera_de_biblia": pct(int((validos & ~abajo & ~en_lectura).sum()),
                                                int((validos & ~en_lectura).sum())),
        "pct_abajo_fuera_sobre_su_tiempo": pct(int((abajo & ~en_lectura).sum()),
                                               int((validos & ~en_lectura).sum())),
        "pct_abajo_durante_lectura": pct(int((abajo & en_lectura).sum()), int((validos & en_lectura).sum())),
        "episodios_fuera_de_biblia": len(fuera),
        "episodio_mas_largo_fuera": None if mayor is None else {
            "duracion": mayor["duracion"], "inicio": mayor["inicio"], "minuto": formato_tiempo(mayor["inicio"])},
    }


def resumir(df: pd.DataFrame, seg: pd.DataFrame, p: Parametros, base: float, metodo: str,
            video: dict, lecturas=None) -> dict:
    cuentas = seg.clase.value_counts()
    c, a, n = (int(cuentas.get(k, 0)) for k in (CONGREGACION, ABAJO, SIN_DATO))
    con_dato = c + a
    total = c + a + n
    eps = episodios(df, p.fps)
    largos = [e for e in eps if e["duracion"] >= 1.0]
    vistazos = [e for e in eps if e["duracion"] < 1.0]
    mayor = max(largos, key=lambda e: (e["duracion"], -e["inicio"]), default=None)

    def pct(x, sobre):
        return round(100 * x / sobre, 1) if sobre else 0.0

    pct_sin = pct(n, total)
    corte = base + p.umbral
    # Segundos "abajo" en que la cabeza no pasó el umbral: lo detectaron solo los ojos.
    solo_ojos = int(((seg.clase == ABAJO) & ~(seg.pitch > corte)).sum())
    advertencias = []
    if pct_sin > LIMITE_SIN_DATO:
        advertencias.append(
            f"{pct_sin} % de los segundos no tienen rostro (más del {LIMITE_SIN_DATO:.0f} %): "
            "resultado poco confiable.")
    return {
        "video": video,
        "parametros": {
            "fps": p.fps,
            "umbral": p.umbral,
            "pitch_calibracion": round(base, 2),
            "metodo_calibracion": metodo,
            "corte_abajo": round(base + p.umbral, 2),
            "excluir": [[a_, b_] for a_, b_ in p.excluir],
            "ancho_minimo": p.ancho_minimo,
            "umbral_ojos": p.umbral_ojos,
            "metodo": "cabeza" if p.umbral_ojos is None else "cabeza + ojos",
            "version": __version__,
        },
        "segundos_totales": total,
        "segundos_con_dato": con_dato,
        "segundos_excluidos": int(cuentas.get(EXCLUIDO, 0)),
        "pct_congregacion": pct(c, con_dato),
        "pct_abajo": pct(a, con_dato),
        "pct_abajo_solo_ojos": pct(solo_ojos, con_dato),
        "pct_sin_dato": pct_sin,
        "poco_confiable": pct_sin > LIMITE_SIN_DATO,
        "episodios_abajo": len(largos),
        "episodio_mas_largo": None if mayor is None else {
            "duracion": mayor["duracion"],
            "inicio": mayor["inicio"],
            "minuto": formato_tiempo(mayor["inicio"]),
        },
        "duracion_media_episodio": round(float(np.mean([e["duracion"] for e in largos])), 2) if largos else 0.0,
        "tiempo_abajo_en_episodios": round(sum(e["duracion"] for e in largos), 2),
        "vistazos": len(vistazos),
        "advertencias": advertencias,
        "biblia": _biblia(seg, largos, lecturas, con_dato, pct) if lecturas else None,
        "contacto": _contacto(df, p.fps),
        "episodios": largos,
    }


COLUMNAS = ["t", "rostro", "confianza", "pitch", "yaw", "roll", "ancho_rostro", "clase",
            "x", "y", "w", "h", "ojos", "ojos_abajo", "parpado", "apertura"]


def guardar(carpeta: Path, df: pd.DataFrame, p: Parametros, video: dict) -> dict:
    from dataclasses import replace

    from .lecturas import leer_lecturas
    lecturas = leer_lecturas(carpeta)
    oraciones = leer_lecturas(carpeta, "oraciones")
    # Las oraciones (ojos cerrados) se excluyen al clasificar, pero no se guardan como
    # parámetro: vienen de lecturas.json y cambian si se edita.
    df, base, metodo = clasificar(df, replace(p, excluir=p.excluir + oraciones))
    seg = por_segundo(df, base + p.umbral)
    seg["biblia"] = en_tramos(seg.t.values + 0.5, lecturas) if lecturas else False
    resumen = resumir(df, seg, p, base, metodo, video, lecturas)
    if oraciones:
        resumen["oracion"] = {"tramos": len(oraciones),
                              "segundos": round(sum(b - a for a, b in oraciones), 1),
                              "minutos": [formato_tiempo(a) for a, _ in oraciones]}

    salida = df[[c for c in COLUMNAS if c in df.columns]].copy()
    salida["rostro"] = np.where(df.rostro, "si", "no")
    salida.to_csv(carpeta / "fotogramas.csv", index=False, float_format="%.3f")
    seg.to_csv(carpeta / "segundos.csv", index=False, float_format="%.2f")
    (carpeta / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2) + "\n")
    return resumen


def leer_fotogramas(carpeta: Path) -> pd.DataFrame:
    df = pd.read_csv(carpeta / "fotogramas.csv")
    df["rostro"] = df.rostro.astype(str).str.lower().isin(["si", "sí", "true", "1"])
    return df


def leer_resumen(carpeta: Path) -> dict:
    return json.loads((carpeta / "resumen.json").read_text())


def parametros_de(resumen: dict) -> Parametros:
    pr = resumen["parametros"]
    return Parametros(
        fps=pr["fps"], umbral=pr["umbral"],
        base=pr["pitch_calibracion"] if pr.get("metodo_calibracion") == "manual" else None,
        excluir=[tuple(x) for x in pr.get("excluir", [])],
        ancho_minimo=pr.get("ancho_minimo", 0),
        umbral_ojos=pr.get("umbral_ojos"),
    )


def texto_resumen(r: dict) -> str:
    m = r["episodio_mas_largo"]
    lineas = [
        f"  Congregación: {r['pct_congregacion']} %   Abajo: {r['pct_abajo']} %   "
        f"Sin dato: {r['pct_sin_dato']} %",
        f"  Episodios abajo (≥1 s): {r['episodios_abajo']}   "
        f"duración media: {r['duracion_media_episodio']} s   vistazos (<1 s): {r['vistazos']}",
        "  Episodio más largo: " + (f"{m['duracion']} s en el minuto {m['minuto']}" if m else "—"),
        (f"  Abajo solo por los ojos (cabeza recta): {r['pct_abajo_solo_ojos']} %\n"
         if r.get("pct_abajo_solo_ojos") is not None and r["parametros"].get("umbral_ojos") is not None else "") +
        f"  Calibración: pitch {r['parametros']['pitch_calibracion']}° "
        f"({r['parametros']['metodo_calibracion']}), abajo desde {r['parametros']['corte_abajo']}°",
    ]
    c = r.get("contacto")
    if c:
        m2 = c["mirada_mas_larga"]
        lineas.append(f"  Miradas a la congregación: {c['miradas']}, media {c['duracion_media']} s "
                      f"(mediana {c['duracion_mediana']} s); la más larga {m2['duracion']} s en {m2['minuto']}")
    b = r.get("biblia")
    if b:
        mf = b["episodio_mas_largo_fuera"]
        lineas += [
            f"  Lectura bíblica: {b['tramos']} tramos, {b['pct_del_sermon']} % del sermón "
            f"(mira abajo el {b['pct_abajo_durante_lectura']} % mientras lee)",
            f"  Abajo leyendo la Biblia: {b['pct_abajo_leyendo_biblia']} %   "
            f"Abajo fuera de la Biblia: {b['pct_abajo_fuera_de_biblia']} %",
            f"  Fuera de la lectura: congregación {b['pct_congregacion_fuera_de_biblia']} %, "
            f"abajo {b['pct_abajo_fuera_sobre_su_tiempo']} %; episodios {b['episodios_fuera_de_biblia']}, "
            "el más largo " + (f"{mf['duracion']} s en {mf['minuto']}" if mf else "—"),
        ]
    o = r.get("oracion")
    if o:
        lineas.append(f"  Oración (excluida del cálculo): {o['tramos']} tramos, {o['segundos']:.0f} s "
                      f"({', '.join(o['minutos'])})")
    lineas += [f"  ⚠ {a}" for a in r["advertencias"]]
    return "\n".join(lineas)
