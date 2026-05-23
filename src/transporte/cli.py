"""
cli.py — Interfaz de Línea de Comandos (CLI) unificada e interactiva
para resolver problemas de transporte con múltiples algoritmos.
"""

from __future__ import annotations

from typing import List, Optional

from transporte.groq import generar_conclusion
from transporte.models import Matriz, ResultadoTransporte, Vector
from transporte.solvers import (
    resolver_coste_minimo,
    resolver_esquina_noroeste,
    resolver_vogel,
    resolver_hungaro,
)



# ─────────────────────────────────────────────
# Estilizado visual y decoradores
# ─────────────────────────────────────────────
def _encabezado(titulo: str, ancho: int = 70) -> str:
    return f"\n{'═' * ancho}\n  {titulo}\n{'═' * ancho}"


def _imprimir_matriz(
    titulo: str,
    matriz: Matriz,
    origenes: List[str],
    destinos: List[str],
    oferta: Optional[Vector] = None,
    demanda: Optional[Vector] = None,
) -> None:
    print(f"\n  {titulo}")
    destinos_header = list(destinos)
    if oferta is not None:
        destinos_header.append("Oferta")

    ancho_col = max(10, max([len(d) for d in destinos_header]) + 2)
    ancho_fila = max(12, max([len(o) for o in origenes] + [len("Demanda")]) + 2)

    print(f"  {'':>{ancho_fila}}", end="")
    for d in destinos_header:
        print(f"{d:>{ancho_col}}", end="")
    print()

    for i, fila in enumerate(matriz):
        etiqueta = origenes[i] if i < len(origenes) else f"Ficticio {i+1}"
        print(f"  {etiqueta:>{ancho_fila}}", end="")
        for val in fila:
            print(f"{val:>{ancho_col}.1f}", end="")
        if oferta is not None and i < len(oferta):
            print(f"{oferta[i]:>{ancho_col}.1f}", end="")
        print()

    if demanda is not None:
        print(f"  {'Demanda':>{ancho_fila}}", end="")
        for val in demanda:
            print(f"{val:>{ancho_col}.1f}", end="")
        if oferta is not None:
            print(f"{sum(oferta):>{ancho_col}.1f}", end="")
        print()


def _imprimir_vector(titulo: str, vector: Vector, etiquetas: List[str]) -> None:
    partes = [f"'{e}': {v}" for e, v in zip(etiquetas, vector)]
    print(f"  {titulo}: {', '.join(partes)}")


# ─────────────────────────────────────────────
# Lectores interactivos validados
# ─────────────────────────────────────────────
def _leer_entero_positivo(mensaje: str) -> int:
    while True:
        try:
            valor = int(input(f"  {mensaje}: "))
            if valor <= 0:
                print("  ✗ Debe ser un número entero positivo.")
                continue
            return valor
        except ValueError:
            print("  ✗ Entrada inválida. Ingresa un número entero.")


def _leer_nombres(mensaje: str, cantidad: int) -> List[str]:
    nombres: List[str] = []
    print(f"\n  ── Nombres de {mensaje}s ──")
    for i in range(cantidad):
        nombre = (
            input(
                f"    Nombre del {mensaje} {i + 1} (Enter para usar '{mensaje} {i+1}'): "
            )
            .strip()
        )
        if not nombre:
            nombre = f"{mensaje} {i+1}"
        nombres.append(nombre)
    return nombres


def _leer_vector_con_nombres(mensaje: str, nombres: List[str]) -> Vector:
    vector: Vector = []
    print(f"\n  ── {mensaje} ──")
    # Obtener el tipo de vector para una etiqueta amigable (ej. "Oferta" o "Demanda")
    tipo = mensaje.replace("Vector de ", "")
    for nombre in nombres:
        while True:
            try:
                valor = float(input(f"    {tipo} para '{nombre}': "))
                if valor < 0:
                    print("    ✗ El valor no puede ser negativo.")
                    continue
                vector.append(valor)
                break
            except ValueError:
                print("    ✗ Entrada inválida. Ingresa un número válido.")
    return vector


def _leer_matriz_con_nombres(
    nombres_orig: List[str], nombres_dest: List[str]
) -> Matriz:
    matriz: Matriz = []
    print("\n  ── MATRIZ DE COSTOS UNITARIOS ──")
    for origen in nombres_orig:
        print(f"\n    Costos desde '{origen}':")
        fila: Vector = []
        for destino in nombres_dest:
            while True:
                try:
                    costo = float(input(f"      Costo hacia '{destino}': "))
                    if costo < 0:
                        print("      ✗ El costo no puede ser negativo.")
                        continue
                    fila.append(costo)
                    break
                except ValueError:
                    print("      ✗ Entrada inválida. Ingresa un número válido.")
        matriz.append(fila)
    return matriz


# ─────────────────────────────────────────────
# Visualizador de resultados
# ─────────────────────────────────────────────
def mostrar_resultado_cli(
    resultado: ResultadoTransporte,
    nombres_orig: List[str],
    nombres_dest: List[str],
    titulo_metodo: str,
) -> None:
    m_o = len(resultado.matriz_costos_original)
    n_o = len(resultado.matriz_costos_original[0])
    m_b = len(resultado.matriz_costos_balanceada)
    n_b = len(resultado.matriz_costos_balanceada[0])

    or_b = list(nombres_orig)
    if m_b > m_o:
        or_b.append("Origen Ficticio")

    de_b = list(nombres_dest)
    if n_b > n_o:
        de_b.append("Destino Ficticio")

    print(_encabezado("DATOS DE ENTRADA"))
    _imprimir_matriz(
        "Matriz de Costos (Original):",
        resultado.matriz_costos_original,
        nombres_orig,
        nombres_dest,
        resultado.oferta_original,
        resultado.demanda_original,
    )
    _imprimir_vector("Oferta", resultado.oferta_original, nombres_orig)
    _imprimir_vector("Demanda", resultado.demanda_original, nombres_dest)

    print(_encabezado("BALANCEO"))
    if resultado.fue_balanceada:
        print(f"  ⚠ {resultado.tipo_balanceo}")
        _imprimir_matriz(
            "Matriz de Costos (Balanceada):",
            resultado.matriz_costos_balanceada,
            or_b,
            de_b,
            resultado.oferta_balanceada,
            resultado.demanda_balanceada,
        )
    else:
        print("  ✓ La tabla ya estaba balanceada; no se requirieron ajustes.")

    print(_encabezado(f"SOLUCIÓN — {titulo_metodo}"))
    _imprimir_matriz("Matriz de Asignaciones:", resultado.asignaciones, or_b, de_b, resultado.oferta_balanceada, resultado.demanda_balanceada)
    print(f"\n  ★ COSTO TOTAL DISTRIBUIDO: {resultado.costo_total:.2f}")

    print(_encabezado("PASOS DEL ALGORITMO"))
    for paso in resultado.pasos:
        print(f"  {paso}\n")


# ─────────────────────────────────────────────
# Función Principal CLI
# ─────────────────────────────────────────────
def main() -> None:
    print(_encabezado("SISTEMA UNIFICADO DE OPTIMIZACIÓN DE TRANSPORTE"))
    print("  Selecciona el método de resolución matemático:")
    print("    1. Método de la Esquina Noroeste")
    print("    2. Método del Costo Mínimo")
    print("    3. Método de Aproximación de Vogel (VAM)")
    print("    4. Método Húngaro (Asignación)")

    metodo = 0
    while True:
        try:
            opcion = int(input("\n  Opción (1-4): "))
            if opcion in (1, 2, 3, 4):
                metodo = opcion
                break
            print("  ✗ Por favor, selecciona una opción entre 1 y 4.")
        except ValueError:
            print("  ✗ Entrada inválida. Digita un número del 1 al 4.")

    nombres_metodos = {
        1: ("MÉTODO DE LA ESQUINA NOROESTE", resolver_esquina_noroeste),
        2: ("MÉTODO DEL COSTO MÍNIMO", resolver_coste_minimo),
        3: ("MÉTODO DE APROXIMACIÓN DE VOGEL (VAM)", resolver_vogel),
        4: ("MÉTODO HÚNGARO (ASIGNACIÓN)", resolver_hungaro),
    }

    titulo_metodo, solver_func = nombres_metodos[metodo]

    maximizar = False
    if metodo == 4:
        print("\n  Selecciona el tipo de optimización para el Método Húngaro:")
        print("    1. Minimizar costos")
        print("    2. Maximizar beneficios")
        opt_tipo = 0
        while True:
            try:
                opt_opcion = int(input("\n    Opción (1-2): "))
                if opt_opcion in (1, 2):
                    opt_tipo = opt_opcion
                    break
                print("    ✗ Por favor, selecciona 1 o 2.")
            except ValueError:
                print("    ✗ Entrada inválida. Ingresa un número del 1 al 2.")
        if opt_tipo == 2:
            maximizar = True
            titulo_metodo = "MÉTODO HÚNGARO (MAXIMIZACIÓN DE ASIGNACIÓN)"
        else:
            titulo_metodo = "MÉTODO HÚNGARO (MINIMIZACIÓN DE ASIGNACIÓN)"

    print(_encabezado(f"CONFIGURACIÓN — {titulo_metodo}"))

    # Dimensiones
    num_origenes = _leer_entero_positivo("Número de orígenes (filas)")
    num_destinos = _leer_entero_positivo("Número de destinos (columnas)")

    # Nombres
    nombres_orig = _leer_nombres("Origen", num_origenes)
    nombres_dest = _leer_nombres("Destino", num_destinos)

    # Costos, Oferta y Demanda
    costos = _leer_matriz_con_nombres(nombres_orig, nombres_dest)
    if metodo == 4:
        print("\n  ℹ Para el Método Húngaro, la Oferta y Demanda se configuran automáticamente en 1.")
        oferta = [1.0] * num_origenes
        demanda = [1.0] * num_destinos
    else:
        oferta = _leer_vector_con_nombres("Vector de Oferta", nombres_orig)
        demanda = _leer_vector_con_nombres("Vector de Demanda", nombres_dest)


    print(_encabezado("EJECUTANDO CÁLCULOS..."))

    try:
        if metodo == 4:
            resultado = solver_func(costos, oferta, demanda, maximizar=maximizar)
        else:
            resultado = solver_func(costos, oferta, demanda)
    except Exception as e:
        print(f"\n  ✗ Error interno al resolver: {e}\n")
        return

    # Mostrar Resultados
    mostrar_resultado_cli(resultado, nombres_orig, nombres_dest, titulo_metodo)

    # Conclusión Ejecutiva Groq AI
    print(_encabezado("CONCLUSIÓN EJECUTIVA (Groq AI)"))
    print("  Generando análisis logístico con IA...")
    conclusion = "No disponible por error de conexión."
    try:
        conclusion = generar_conclusion(resultado, nombres_orig, nombres_dest)
        print(f"\n{conclusion}\n")
    except Exception as e:
        print(f"\n  ✗ Error al conectar con Groq AI: {e}\n")

    # Guardar reporte en TXT
    try:
        from transporte.core import guardar_reporte_txt
        guardar_reporte_txt(resultado, nombres_orig, nombres_dest, titulo_metodo, conclusion)
        print(f"\n{'═'*70}\n  ✓ REPORTE GUARDADO AUTOMÁTICAMENTE EN: 'reporte_transporte.txt'\n{'═'*70}")
    except Exception as e:
        print(f"\n  ⚠ Error al guardar el archivo de reporte: {e}\n")

    print(_encabezado("FIN DE LA EJECUCIÓN"))


if __name__ == "__main__":
    main()
