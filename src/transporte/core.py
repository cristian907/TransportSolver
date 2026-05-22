"""
core.py — Funciones de núcleo y utilidades (validación y balanceo) del Problema de Transporte.
"""

from __future__ import annotations

import copy
from typing import Tuple

from transporte.models import Matriz, Vector


def validar_entradas(
    costos: Matriz,
    oferta: Vector,
    demanda: Vector,
) -> None:
    """Valida las entradas del problema de transporte.

    Raises:
        ValueError: Si alguna dimensión es inconsistente, hay valores
            negativos o las listas están vacías.
    """
    if not costos:
        raise ValueError("La matriz de costos no puede estar vacía.")
    if not oferta:
        raise ValueError("El vector de oferta no puede estar vacío.")
    if not demanda:
        raise ValueError("El vector de demanda no puede estar vacío.")

    num_filas = len(costos)
    num_columnas = len(costos[0])

    if num_filas != len(oferta):
        raise ValueError(
            f"La matriz de costos tiene {num_filas} filas, pero el vector "
            f"de oferta tiene {len(oferta)} elementos."
        )
    if num_columnas != len(demanda):
        raise ValueError(
            f"La matriz de costos tiene {num_columnas} columnas, pero el "
            f"vector de demanda tiene {len(demanda)} elementos."
        )

    for i, fila in enumerate(costos):
        if len(fila) != num_columnas:
            raise ValueError(
                f"La fila {i} tiene {len(fila)} columnas; se esperaban "
                f"{num_columnas}."
            )
        for j, costo in enumerate(fila):
            if costo < 0:
                raise ValueError(
                    f"Costo negativo detectado en ({i}, {j}): {costo}."
                )

    for i, s in enumerate(oferta):
        if s < 0:
            raise ValueError(f"Oferta negativa en origen {i}: {s}.")

    for j, d in enumerate(demanda):
        if d < 0:
            raise ValueError(f"Demanda negativa en destino {j}: {d}.")


def balancear(
    costos: Matriz,
    oferta: Vector,
    demanda: Vector,
) -> Tuple[Matriz, Vector, Vector, bool, str]:
    """Balancea la tabla de transporte agregando filas o columnas ficticias.

    Returns:
        Tupla con (costos_balanceados, oferta_balanceada, demanda_balanceada,
        fue_balanceada, tipo_balanceo).
    """
    total_oferta = sum(oferta)
    total_demanda = sum(demanda)

    # Copias profundas para no mutar los datos de entrada
    costos_b: Matriz = copy.deepcopy(costos)
    oferta_b: Vector = list(oferta)
    demanda_b: Vector = list(demanda)

    if total_oferta == total_demanda:
        return costos_b, oferta_b, demanda_b, False, "Ninguno (ya balanceada)"

    if total_oferta > total_demanda:
        diferencia = total_oferta - total_demanda
        # Agregar columna ficticia con costo 0
        for fila in costos_b:
            fila.append(0.0)
        demanda_b.append(diferencia)
        return (
            costos_b,
            oferta_b,
            demanda_b,
            True,
            f"Oferta > Demanda: se agregó destino ficticio con demanda = {diferencia}",
        )

    # total_demanda > total_oferta
    diferencia = total_demanda - total_oferta
    num_columnas = len(costos_b[0])
    costos_b.append([0.0] * num_columnas)
    oferta_b.append(diferencia)
    return (
        costos_b,
        oferta_b,
        demanda_b,
        True,
        f"Demanda > Oferta: se agregó origen ficticio con oferta = {diferencia}",
    )


def _format_matriz_reporte(
    matriz: Matriz,
    origenes: List[str],
    destinos: List[str],
) -> str:
    ancho_col = max(12, max([len(d) for d in destinos]) + 2)
    ancho_fila = max(16, max([len(o) for o in origenes]) + 2)

    res = f"  {'':>{ancho_fila}}"
    for d in destinos:
        res += f"{d:>{ancho_col}}"
    res += "\n"

    for i, fila in enumerate(matriz):
        etiq = origenes[i] if i < len(origenes) else f"Ficticio {i+1}"
        res += f"  {etiq:>{ancho_fila}}"
        for val in fila:
            res += f"{val:>{ancho_col}.1f}"
        res += "\n"
    return res


def _format_vector_reporte(titulo: str, vector: Vector, etiquetas: List[str]) -> str:
    partes = [f"'{e}': {v}" for e, v in zip(etiquetas, vector)]
    return f"  {titulo}: {', '.join(partes)}\n"


def generar_texto_reporte(
    resultado: ResultadoTransporte,
    nombres_orig: List[str],
    nombres_dest: List[str],
    titulo_metodo: str,
    conclusion: str,
) -> str:
    m_o, n_o = len(resultado.matriz_costos_original), len(resultado.matriz_costos_original[0])
    m_b, n_b = len(resultado.matriz_costos_balanceada), len(resultado.matriz_costos_balanceada[0])

    or_b = list(nombres_orig)
    if m_b > m_o:
        or_b.append("Origen Ficticio")
    de_b = list(nombres_dest)
    if n_b > n_o:
        de_b.append("Destino Ficticio")

    lineas = []
    def enc(tit):
        lineas.append(f"\n{'═'*70}\n  {tit}\n{'═'*70}")

    enc("DATOS DE ENTRADA")
    lineas.append("\n  Matriz de Costos (Original):")
    lineas.append(_format_matriz_reporte(resultado.matriz_costos_original, nombres_orig, nombres_dest))
    lineas.append(_format_vector_reporte("Oferta", resultado.oferta_original, nombres_orig))
    lineas.append(_format_vector_reporte("Demanda", resultado.demanda_original, nombres_dest))

    enc("BALANCEO")
    if resultado.fue_balanceada:
        lineas.append(f"  ⚠ {resultado.tipo_balanceo}\n")
        lineas.append("\n  Matriz de Costos (Balanceada):")
        lineas.append(_format_matriz_reporte(resultado.matriz_costos_balanceada, or_b, de_b))
    else:
        lineas.append("  ✓ La tabla ya estaba balanceada; no se requirieron ajustes.\n")

    enc(f"SOLUCIÓN — {titulo_metodo.upper()}")
    lineas.append("\n  Matriz de Asignaciones:")
    lineas.append(_format_matriz_reporte(resultado.asignaciones, or_b, de_b))
    lineas.append(f"  ★ COSTO TOTAL DISTRIBUIDO: {resultado.costo_total:.2f}\n")

    enc("PASOS DEL ALGORITMO")
    for paso in resultado.pasos:
        lineas.append(f"  {paso}\n")

    enc("CONCLUSIÓN EJECUTIVA (Groq AI)")
    lineas.append(conclusion)

    enc("FIN DE LA EJECUCIÓN")

    return "\n".join(lineas)


def guardar_reporte_txt(
    resultado: ResultadoTransporte,
    nombres_orig: List[str],
    nombres_dest: List[str],
    titulo_metodo: str,
    conclusion: str,
    ruta: str = "reporte_transporte.txt",
) -> None:
    texto = generar_texto_reporte(resultado, nombres_orig, nombres_dest, titulo_metodo, conclusion)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(texto)

