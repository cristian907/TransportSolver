"""
solvers.py — Implementación de solucionadores para el Problema de Transporte:
1. Método de la Esquina Noroeste
2. Método del Costo Mínimo
3. Método de Aproximación de Vogel (VAM)
"""

from __future__ import annotations

import copy
from typing import List, Optional, Tuple

from transporte.core import balancear, validar_entradas
from transporte.models import Matriz, ResultadoTransporte, Vector


def _format_matriz_paso(
    matriz: Matriz,
    origenes: List[str],
    destinos: List[str],
    oferta: Optional[Vector] = None,
    demanda: Optional[Vector] = None,
) -> str:
    """Genera una representación de texto plano de la matriz para incluir en los pasos."""
    destinos_header = list(destinos)
    if oferta is not None:
        destinos_header.append("Oferta")

    ancho_col = max(12, max(len(d) for d in destinos_header) + 2)
    ancho_fila = max(16, max(len(o) for o in origenes) + 2)

    lineas = []
    # El encabezado debe alinearse exactamente con los valores de las filas.
    # El prefijo de fila es: 6 espacios + etiqueta de ancho_fila + ": " (2 chars)
    # Por lo tanto, el total de espacios del prefijo es ancho_fila + 8.
    encabezado = " " * (ancho_fila + 8)
    for d in destinos_header:
        encabezado += f"{d:>{ancho_col}}"
    lineas.append(encabezado)

    # Filas
    for i, fila in enumerate(matriz):
        etiqueta = origenes[i] if i < len(origenes) else f"Ficticio {i+1}"
        linea = f"      {etiqueta:>{ancho_fila}}: "
        for val in fila:
            linea += f"{val:>{ancho_col}.1f}"
        if oferta is not None and i < len(oferta):
            linea += f"{oferta[i]:>{ancho_col}.1f}"
        lineas.append(linea)

    if demanda is not None:
        linea_dem = f"      {'Demanda':>{ancho_fila}}: "
        for val in demanda:
            linea_dem += f"{val:>{ancho_col}.1f}"
        if oferta is not None:
            linea_dem += f"{sum(oferta):>{ancho_col}.1f}"
        lineas.append(linea_dem)

    return "\n".join(lineas)


# ─────────────────────────────────────────────
# 1. MÉTODO DE LA ESQUINA NOROESTE
# ─────────────────────────────────────────────
def resolver_esquina_noroeste(
    costos: Matriz,
    oferta: Vector,
    demanda: Vector,
) -> ResultadoTransporte:
    """Resuelve el problema de transporte por el Método de la Esquina Noroeste.

    Args:
        costos: Matriz m×n de costos unitarios.
        oferta: Vector de capacidades de origen (longitud m).
        demanda: Vector de requerimientos de destino (longitud n).

    Returns:
        Objeto ResultadoTransporte con la solución detallada.
    """
    # 1. Validación
    validar_entradas(costos, oferta, demanda)

    costos_orig: Matriz = copy.deepcopy(costos)
    oferta_orig: Vector = list(oferta)
    demanda_orig: Vector = list(demanda)

    # 2. Balanceo
    costos_b, oferta_b, demanda_b, fue_balanceada, tipo_balanceo = balancear(
        costos, oferta, demanda
    )

    pasos: List[str] = []
    if fue_balanceada:
        pasos.append(f"Balanceo aplicado: {tipo_balanceo}.")
    else:
        pasos.append("La tabla ya estaba balanceada; no se requirió ajuste.")

    m = len(costos_b)
    n = len(costos_b[0])

    or_b = [f"Origen {x+1}" if x < len(oferta) else "Ficticio" for x in range(m)]
    de_b = [f"Destino {y+1}" if y < len(demanda) else "Ficticio" for y in range(n)]

    oferta_disp: Vector = list(oferta_b)
    demanda_disp: Vector = list(demanda_b)

    asignaciones: Matriz = [[0.0] * n for _ in range(m)]

    # 3. Iteración de la Esquina Noroeste
    i, j = 0, 0
    iteracion = 0

    while i < m and j < n:
        cantidad = min(oferta_disp[i], demanda_disp[j])
        asignaciones[i][j] = cantidad
        oferta_disp[i] -= cantidad
        demanda_disp[j] -= cantidad

        iteracion += 1
        pasos.append(
            f"Iteración {iteracion}: Asignar {cantidad} unidades en la esquina "
            f"noroeste ({i}, {j}) a costo unitario {costos_b[i][j]}. "
            f"Oferta restante = {oferta_disp[i]}, Demanda restante = {demanda_disp[j]}.\n"
            f"    [Matriz de Asignaciones Actuales]:\n"
            f"{_format_matriz_paso(asignaciones, or_b, de_b, oferta_disp, demanda_disp)}"
        )

        # Manejo de degeneración y avance
        if oferta_disp[i] == 0 and demanda_disp[j] == 0:
            if i != m - 1 or j != n - 1:
                pasos.append(
                    f"  ⚠ Degeneración en ({i}, {j}): oferta y demanda agotadas "
                    f"simultáneamente. Se cancela la fila {i} y se avanza a la "
                    f"siguiente; la columna {j} mantiene demanda 0."
                )
                i += 1  # Estrategia: avanzar fila
            else:
                break
        elif oferta_disp[i] == 0:
            pasos.append(f"  Fila {i} agotada → avanzar hacia abajo.")
            i += 1
        else:
            pasos.append(f"  Columna {j} agotada → avanzar hacia la derecha.")
            j += 1

    # 4. Costo total
    costo_total: float = sum(
        asignaciones[r][c] * costos_b[r][c]
        for r in range(m)
        for c in range(n)
    )

    pasos.append(f"Costo total mínimo calculado: {costo_total}.")

    return ResultadoTransporte(
        matriz_costos_original=costos_orig,
        matriz_costos_balanceada=costos_b,
        oferta_original=oferta_orig,
        demanda_original=demanda_orig,
        oferta_balanceada=oferta_b,
        demanda_balanceada=demanda_b,
        asignaciones=asignaciones,
        costo_total=costo_total,
        fue_balanceada=fue_balanceada,
        tipo_balanceo=tipo_balanceo,
        pasos=pasos,
    )


# ─────────────────────────────────────────────
# 2. MÉTODO DEL COSTO MÍNIMO
# ─────────────────────────────────────────────
def _encontrar_celda_minima(
    costos: Matriz,
    oferta: Vector,
    demanda: Vector,
    filas_activas: List[bool],
    columnas_activas: List[bool],
) -> Optional[Tuple[int, int]]:
    """Localiza la celda activa con el costo unitario mínimo."""
    mejor: Optional[Tuple[int, int]] = None
    mejor_costo: float = float("inf")
    mejor_asignacion: float = -1.0

    for i in range(len(costos)):
        if not filas_activas[i]:
            continue
        for j in range(len(costos[0])):
            if not columnas_activas[j]:
                continue

            costo = costos[i][j]
            asignacion_posible = min(oferta[i], demanda[j])

            es_mejor = False
            if costo < mejor_costo:
                es_mejor = True
            elif costo == mejor_costo and asignacion_posible > mejor_asignacion:
                # Desempate: mayor asignación posible
                es_mejor = True

            if es_mejor:
                mejor = (i, j)
                mejor_costo = costo
                mejor_asignacion = asignacion_posible

    return mejor


def resolver_coste_minimo(
    costos: Matriz,
    oferta: Vector,
    demanda: Vector,
) -> ResultadoTransporte:
    """Resuelve el problema de transporte por el Método del Costo Mínimo.

    Args:
        costos: Matriz m×n de costos unitarios.
        oferta: Vector de capacidades de origen (longitud m).
        demanda: Vector de requerimientos de destino (longitud n).

    Returns:
        Objeto ResultadoTransporte con la solución detallada.
    """
    # ── 1. Validación ──
    validar_entradas(costos, oferta, demanda)

    # Guardar originales
    costos_orig: Matriz = copy.deepcopy(costos)
    oferta_orig: Vector = list(oferta)
    demanda_orig: Vector = list(demanda)

    # ── 2. Balanceo ──
    costos_b, oferta_b, demanda_b, fue_balanceada, tipo_balanceo = balancear(
        costos, oferta, demanda
    )

    pasos: List[str] = []
    if fue_balanceada:
        pasos.append(f"Balanceo aplicado: {tipo_balanceo}.")
    else:
        pasos.append("La tabla ya estaba balanceada; no se requirió ajuste.")

    m = len(costos_b)
    n = len(costos_b[0])

    or_b = [f"Origen {x+1}" if x < len(oferta) else "Ficticio" for x in range(m)]
    de_b = [f"Destino {y+1}" if y < len(demanda) else "Ficticio" for y in range(n)]

    # Vectores de trabajo
    oferta_disp: Vector = list(oferta_b)
    demanda_disp: Vector = list(demanda_b)

    filas_activas: List[bool] = [True] * m
    columnas_activas: List[bool] = [True] * n

    asignaciones: Matriz = [[0.0] * n for _ in range(m)]

    iteracion = 0

    # ── 3. Iteración de asignación ──
    while True:
        celda = _encontrar_celda_minima(
            costos_b, oferta_disp, demanda_disp, filas_activas, columnas_activas
        )
        if celda is None:
            break

        i, j = celda
        cantidad = min(oferta_disp[i], demanda_disp[j])
        asignaciones[i][j] = cantidad
        oferta_disp[i] -= cantidad
        demanda_disp[j] -= cantidad

        iteracion += 1
        pasos.append(
            f"Iteración {iteracion}: Asignar {cantidad} unidades a la celda "
            f"({i}, {j}) con costo unitario {costos_b[i][j]}. "
            f"Oferta restante fila {i} = {oferta_disp[i]}, "
            f"Demanda restante col {j} = {demanda_disp[j]}.\n"
            f"    [Matriz de Asignaciones Actuales]:\n"
            f"{_format_matriz_paso(asignaciones, or_b, de_b, oferta_disp, demanda_disp)}"
        )

        # ── Manejo de degeneración ──
        if oferta_disp[i] == 0 and demanda_disp[j] == 0:
            # Agotamiento simultáneo: cancelar solo una dimensión (fila)
            filas_activas[i] = False
            pasos.append(
                f"  ⚠ Degeneración: oferta y demanda agotadas simultáneamente "
                f"en ({i}, {j}). Se cancela la fila {i}; la columna {j} "
                f"permanece activa con demanda 0."
            )
        elif oferta_disp[i] == 0:
            filas_activas[i] = False
            pasos.append(f"  Fila {i} agotada → cancelada.")
        elif demanda_disp[j] == 0:
            columnas_activas[j] = False
            pasos.append(f"  Columna {j} agotada → cancelada.")

    # ── 4. Costo total ──
    costo_total: float = sum(
        asignaciones[i][j] * costos_b[i][j]
        for i in range(m)
        for j in range(n)
    )

    pasos.append(f"Costo total mínimo calculado: {costo_total}.")

    return ResultadoTransporte(
        matriz_costos_original=costos_orig,
        matriz_costos_balanceada=costos_b,
        oferta_original=oferta_orig,
        demanda_original=demanda_orig,
        oferta_balanceada=oferta_b,
        demanda_balanceada=demanda_b,
        asignaciones=asignaciones,
        costo_total=costo_total,
        fue_balanceada=fue_balanceada,
        tipo_balanceo=tipo_balanceo,
        pasos=pasos,
    )


# ─────────────────────────────────────────────
# 3. MÉTODO DE APROXIMACIÓN DE VOGEL (VAM)
# ─────────────────────────────────────────────
def resolver_vogel(
    costos: Matriz,
    oferta: Vector,
    demanda: Vector,
) -> ResultadoTransporte:
    """Resuelve el problema por el Método de Aproximación de Vogel (VAM).

    Args:
        costos: Matriz m×n de costos unitarios.
        oferta: Vector de capacidades de origen (longitud m).
        demanda: Vector de requerimientos de destino (longitud n).

    Returns:
        Objeto ResultadoTransporte con la solución detallada.
    """
    # 1. Validación y Copias
    validar_entradas(costos, oferta, demanda)
    costos_orig: Matriz = copy.deepcopy(costos)
    oferta_orig: Vector = list(oferta)
    demanda_orig: Vector = list(demanda)

    # 2. Balanceo
    costos_b, oferta_b, demanda_b, fue_balanceada, tipo_balanceo = balancear(
        costos, oferta, demanda
    )

    pasos: List[str] = []
    if fue_balanceada:
        pasos.append(f"Balanceo aplicado: {tipo_balanceo}.")
    else:
        pasos.append("La tabla ya estaba balanceada; no se requirió ajuste.")

    m = len(costos_b)
    n = len(costos_b[0])

    or_b = [f"Origen {x+1}" if x < len(oferta) else "Ficticio" for x in range(m)]
    de_b = [f"Destino {y+1}" if y < len(demanda) else "Ficticio" for y in range(n)]

    oferta_disp: Vector = list(oferta_b)
    demanda_disp: Vector = list(demanda_b)

    filas_activas = [True] * m
    cols_activas = [True] * n
    asignaciones: Matriz = [[0.0] * n for _ in range(m)]

    iteracion = 0

    # 3. Bucle Principal de Vogel
    while True:
        # Verificar si ya terminamos
        if not any(filas_activas) or not any(cols_activas):
            break

        iteracion += 1
        pasos.append(f"\n--- Iteración {iteracion} ---")

        # A) Calcular Penalizaciones (Diferencias)
        pen_filas = []
        for i in range(m):
            if filas_activas[i]:
                c_f = [costos_b[i][j] for j in range(n) if cols_activas[j]]
                if len(c_f) >= 2:
                    s = sorted(c_f)
                    pen_filas.append((i, s[1] - s[0]))
                elif len(c_f) == 1:
                    pen_filas.append((i, c_f[0]))
                else:
                    pen_filas.append((i, -1.0))
            else:
                pen_filas.append((i, -1.0))

        pen_cols = []
        for j in range(n):
            if cols_activas[j]:
                c_c = [costos_b[i][j] for i in range(m) if filas_activas[i]]
                if len(c_c) >= 2:
                    s = sorted(c_c)
                    pen_cols.append((j, s[1] - s[0]))
                elif len(c_c) == 1:
                    pen_cols.append((j, c_c[0]))
                else:
                    pen_cols.append((j, -1.0))
            else:
                pen_cols.append((j, -1.0))

        # Registrar el cálculo de diferencias en la bitácora
        dif_str = []
        for i, p in pen_filas:
            if p >= 0:
                dif_str.append(f"F{i}({p})")
        for j, p in pen_cols:
            if p >= 0:
                dif_str.append(f"C{j}({p})")

        pasos.append(f"Diferencias calculadas: {', '.join(dif_str)}")

        # B) Buscar la Máxima Diferencia
        max_pen = -1.0
        for _, p in pen_filas:
            if p > max_pen:
                max_pen = p
        for _, p in pen_cols:
            if p > max_pen:
                max_pen = p

        if max_pen == -1.0:
            break

        # C) Desempate: seleccionar la línea con la máxima penalización con menor costo unitario
        candidatos = []
        for i, p in pen_filas:
            if p == max_pen:
                candidatos.append((True, i))
        for j, p in pen_cols:
            if p == max_pen:
                candidatos.append((False, j))

        menor_costo_global = float("inf")
        mejor_celda = (-1, -1)
        mejor_linea_str = ""

        for es_fila, idx in candidatos:
            min_c = float("inf")
            celda = (-1, -1)

            if es_fila:
                for j in range(n):
                    if cols_activas[j] and costos_b[idx][j] < min_c:
                        min_c = costos_b[idx][j]
                        celda = (idx, j)
            else:
                for i in range(m):
                    if filas_activas[i] and costos_b[i][idx] < min_c:
                        min_c = costos_b[i][idx]
                        celda = (i, idx)

            if min_c < menor_costo_global:
                menor_costo_global = min_c
                mejor_celda = celda
                mejor_linea_str = f"Fila {idx}" if es_fila else f"Columna {idx}"

        i, j = mejor_celda
        if i == -1 or j == -1:
            break

        pasos.append(f"Máxima diferencia elegida: {max_pen} (en la {mejor_linea_str}).")

        # D) Asignar en la celda de menor costo
        cantidad = min(oferta_disp[i], demanda_disp[j])
        asignaciones[i][j] = cantidad
        oferta_disp[i] -= cantidad
        demanda_disp[j] -= cantidad

        pasos.append(
            f"  > Asignar {cantidad} unidades a Celda ({i}, {j}) con costo {costos_b[i][j]}."
        )
        pasos.append(
            f"  > Oferta restante F{i} = {oferta_disp[i]} | Demanda restante C{j} = {demanda_disp[j]}.\n"
            f"    [Matriz de Asignaciones Actuales]:\n"
            f"{_format_matriz_paso(asignaciones, or_b, de_b, oferta_disp, demanda_disp)}"
        )

        # E) Cancelar fila o columna (Manejo de Degeneración)
        if oferta_disp[i] == 0 and demanda_disp[j] == 0:
            filas_activas[i] = False
            pasos.append(
                f"  ⚠ Degeneración: Agotamiento simultáneo. Se cancela la Fila {i}; "
                f"la Columna {j} sigue activa con demanda 0."
            )
        elif oferta_disp[i] == 0:
            filas_activas[i] = False
            pasos.append(f"  > Fila {i} agotada → Cancelada.")
        else:
            cols_activas[j] = False
            pasos.append(f"  > Columna {j} agotada → Cancelada.")

    # 4. Cálculo del costo total
    costo_total = sum(
        asignaciones[i][j] * costos_b[i][j]
        for i in range(m)
        for j in range(n)
    )

    pasos.append(f"\n★ Costo total mínimo calculado (VAM): {costo_total}.")

    return ResultadoTransporte(
        matriz_costos_original=costos_orig,
        matriz_costos_balanceada=costos_b,
        oferta_original=oferta_orig,
        demanda_original=demanda_orig,
        oferta_balanceada=oferta_b,
        demanda_balanceada=demanda_b,
        asignaciones=asignaciones,
        costo_total=costo_total,
        fue_balanceada=fue_balanceada,
        tipo_balanceo=tipo_balanceo,
        pasos=pasos,
    )


# ─────────────────────────────────────────────
# 4. MÉTODO HÚNGARO (ALGORITMO DE ASIGNACIÓN)
# ─────────────────────────────────────────────
def _format_matriz_reduccion(C: Matriz, origenes: List[str], destinos: List[str]) -> str:
    """Genera una representación en texto plano de la matriz de reducción para la bitácora."""
    ancho_col = max(12, max(len(d) for d in destinos) + 2)
    ancho_fila = max(16, max(len(o) for o in origenes) + 2)
    
    lineas = []
    encabezado = " " * (ancho_fila + 8)
    for d in destinos:
        encabezado += f"{d:>{ancho_col}}"
    lineas.append(encabezado)
    
    for i, fila in enumerate(C):
        linea = f"      {origenes[i]:>{ancho_fila}}: "
        for val in fila:
            linea += f"{val:>{ancho_col}.1f}"
        lineas.append(linea)
        
    return "\n".join(lineas)


def resolver_hungaro(
    costos: Matriz,
    oferta: Vector,
    demanda: Vector,
    maximizar: bool = False,
) -> ResultadoTransporte:
    """Resuelve el problema de asignación por el Método Húngaro (Kuhn-Munkres).

    Args:
        costos: Matriz m×n de costos de asignación.
        oferta: Vector de oferta (esperado todos 1s).
        demanda: Vector de demanda (esperado todos 1s).
        maximizar: Indica si el problema es de maximización de beneficios.

    Returns:
        Objeto ResultadoTransporte con la asignación uno-a-uno y pasos del algoritmo.
    """
    # 1. Validación inicial básica
    validar_entradas(costos, oferta, demanda)

    costos_orig: Matriz = copy.deepcopy(costos)
    oferta_orig: Vector = list(oferta)
    demanda_orig: Vector = list(demanda)

    m = len(costos)
    n = len(costos[0])
    N = max(m, n)

    pasos: List[str] = []

    # 2. Balanceo para hacer la matriz cuadrada (N x N)
    costos_b = copy.deepcopy(costos)
    if m > n:
        for fila in costos_b:
            fila.extend([0.0] * (m - n))
        fue_balanceada = True
        tipo_balanceo = f"Matriz no cuadrada ({m}x{n}): se agregaron {m - n} destinos ficticios con costo 0 para hacer la matriz cuadrada."
        pasos.append(f"Matriz balanceada por el Método Húngaro: {tipo_balanceo}")
    elif m < n:
        for _ in range(n - m):
            costos_b.append([0.0] * n)
        fue_balanceada = True
        tipo_balanceo = f"Matriz no cuadrada ({m}x{n}): se agregaron {n - m} orígenes ficticios con costo 0 para hacer la matriz cuadrada."
        pasos.append(f"Matriz balanceada por el Método Húngaro: {tipo_balanceo}")
    else:
        fue_balanceada = False
        tipo_balanceo = "Ninguno (ya es cuadrada)"
        pasos.append("La matriz de costos ya era cuadrada; no se requirió balanceo adicional.")

    oferta_b: Vector = [1.0] * N
    demanda_b: Vector = [1.0] * N

    or_b = [f"Origen {x+1}" if x < m else "Ficticio" for x in range(N)]
    de_b = [f"Destino {y+1}" if y < n else "Ficticio" for y in range(N)]

    # Copiar la matriz cuadrada para manipulación
    C = [row[:] for row in costos_b]

    # Transformación para maximización si corresponde
    if maximizar:
        pasos.append("\nEl problema es de Maximización.")
        max_val = max(max(row) for row in costos_b)
        pasos.append(f"    - Elemento máximo de la matriz balanceada: {max_val:.1f}")
        pasos.append(f"    - Aplicando transformación de maximización: C'[i][j] = {max_val:.1f} - C[i][j]")
        for i in range(N):
            for j in range(N):
                C[i][j] = max_val - C[i][j]
        pasos.append(f"    [Matriz después de transformación de maximización]:\n{_format_matriz_reduccion(C, or_b, de_b)}")


    # Paso 1: Restar mínimos de filas
    pasos.append("\nPaso 1: Restar el valor mínimo de cada fila a todos los elementos de esa fila.")
    for i in range(N):
        min_f = min(C[i])
        for j in range(N):
            C[i][j] -= min_f
    pasos.append(f"    [Matriz después de reducción de filas]:\n{_format_matriz_reduccion(C, or_b, de_b)}")

    # Paso 2: Restar mínimos de columnas
    pasos.append("\nPaso 2: Restar el valor mínimo de cada columna a todos los elementos de esa columna.")
    for j in range(N):
        min_c = min(C[i][j] for i in range(N))
        for i in range(N):
            C[i][j] -= min_c
    pasos.append(f"    [Matriz después de reducción de columnas]:\n{_format_matriz_reduccion(C, or_b, de_b)}")

    # Paso 3 & 4: Iterar emparejamiento y ajuste
    iteracion = 0
    match_row = [-1] * N
    match_col = [-1] * N

    while True:
        iteracion += 1
        pasos.append(f"\n--- Iteración Húngara {iteracion} ---")

        # Eliminar imprecisiones de coma flotante
        for i in range(N):
            for j in range(N):
                if abs(C[i][j]) < 1e-9:
                    C[i][j] = 0.0

        # Encontrar emparejamiento bipartito máximo de ceros
        zeros = [[C[i][j] == 0.0 for j in range(N)] for i in range(N)]
        match_row = [-1] * N
        match_col = [-1] * N

        def dfs(u: int, visited: List[bool]) -> bool:
            for v in range(N):
                if zeros[u][v] and not visited[v]:
                    visited[v] = True
                    if match_col[v] < 0 or dfs(match_col[v], visited):
                        match_row[u] = v
                        match_col[v] = u
                        return True
            return False

        matching_size = 0
        for i in range(N):
            visited = [False] * N
            if dfs(i, visited):
                matching_size += 1

        pasos.append(f"  > Tamaño del emparejamiento máximo de ceros: {matching_size} de {N} necesarios.")

        # Si el emparejamiento es de tamaño N, hemos terminado
        if matching_size == N:
            pasos.append("  ✓ Emparejamiento perfecto encontrado. Asignación óptima completada.")
            break

        # Si es menor que N, cubrimos los ceros con la cantidad mínima de líneas (Teorema de König)
        visited_rows = [False] * N
        visited_cols = [False] * N
        unmatched_rows = [i for i in range(N) if match_row[i] < 0]

        queue = list(unmatched_rows)
        for r in unmatched_rows:
            visited_rows[r] = True

        while queue:
            u = queue.pop(0)
            for v in range(N):
                if zeros[u][v] and not visited_cols[v]:
                    visited_cols[v] = True
                    matched_row_idx = match_col[v]
                    if matched_row_idx >= 0 and not visited_rows[matched_row_idx]:
                        visited_rows[matched_row_idx] = True
                        queue.append(matched_row_idx)

        # El recubrimiento mínimo consiste en filas no visitadas y columnas visitadas
        covered_rows = [not visited_rows[i] for i in range(N)]
        covered_cols = [visited_cols[j] for j in range(N)]

        lineas_fil = [or_b[i] for i in range(N) if covered_rows[i]]
        lineas_col = [de_b[j] for j in range(N) if covered_cols[j]]

        pasos.append(
            f"  > Recubrimiento mínimo de ceros realizado con {matching_size} líneas:\n"
            f"    - Filas cubiertas: {', '.join(lineas_fil) if lineas_fil else 'Ninguna'}\n"
            f"    - Columnas cubiertas: {', '.join(lineas_col) if lineas_col else 'Ninguna'}"
        )

        # Encontrar el elemento más pequeño no cubierto
        delta = float("inf")
        for i in range(N):
            if not covered_rows[i]:
                for j in range(N):
                    if not covered_cols[j] and C[i][j] < delta:
                        delta = C[i][j]

        if delta == float("inf") or delta < 1e-9:
            pasos.append("  ⚠ Error matemático: delta es inválido. Deteniendo para evitar bucle.")
            break

        pasos.append(
            f"  > Ajuste de la matriz usando delta = {delta:.1f} (menor valor no cubierto):\n"
            f"    - Restar delta de todas las filas no cubiertas.\n"
            f"    - Sumar delta a todas las columnas cubiertas (creando intersecciones)."
        )

        # Ajustar la matriz
        for i in range(N):
            for j in range(N):
                if not covered_rows[i] and not covered_cols[j]:
                    C[i][j] -= delta
                elif covered_rows[i] and covered_cols[j]:
                    C[i][j] += delta

        pasos.append(f"    [Matriz Ajustada]:\n{_format_matriz_reduccion(C, or_b, de_b)}")

        if iteracion >= 100:
            pasos.append("  ⚠ Límite de iteraciones alcanzado en el bucle del Método Húngaro.")
            break

    # 4. Generación de Asignaciones y Cálculo de Costo Total
    asignaciones = [[0.0] * N for _ in range(N)]
    for i in range(N):
        if match_row[i] >= 0:
            asignaciones[i][match_row[i]] = 1.0

    costo_total = 0.0
    resumen_asig = []
    for i in range(N):
        col = match_row[i]
        if col >= 0:
            costo_unitario = costos_b[i][col]
            costo_total += costo_unitario
            if i < m and col < n:
                resumen_asig.append(f"Asignar '{or_b[i]}' a '{de_b[col]}' con costo unitario = {costo_unitario:.1f}")
            else:
                resumen_asig.append(f"Asignar '{or_b[i]}' a '{de_b[col]}' (Asignación Ficticia) con costo unitario = 0.0")

    pasos.append("\nResumen Final de Asignaciones Óptimas:")
    for res in resumen_asig:
        pasos.append(f"  - {res}")
    
    if maximizar:
        pasos.append(f"\n★ Beneficio total máximo calculado (Método Húngaro): {costo_total:.2f}")
    else:
        pasos.append(f"\n★ Costo total mínimo calculado (Método Húngaro): {costo_total:.2f}")

    return ResultadoTransporte(
        matriz_costos_original=costos_orig,
        matriz_costos_balanceada=costos_b,
        oferta_original=oferta_orig,
        demanda_original=demanda_orig,
        oferta_balanceada=oferta_b,
        demanda_balanceada=demanda_b,
        asignaciones=asignaciones,
        costo_total=costo_total,
        fue_balanceada=fue_balanceada,
        tipo_balanceo=tipo_balanceo,
        pasos=pasos,
    )

