"""
models.py — Definición de estructuras de datos y tipos para el Problema de Transporte.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

# Tipos auxiliares para claridad semántica y validación de tipos
Matriz = List[List[float]]
Vector = List[float]


@dataclass
class ResultadoTransporte:
    """Encapsula la salida completa del algoritmo de transporte.

    Attributes:
        matriz_costos_original: Tabla de costos tal como fue proporcionada.
        matriz_costos_balanceada: Tabla de costos después del balanceo (puede
            incluir filas/columnas ficticias).
        oferta_original: Vector de oferta original.
        demanda_original: Vector de demanda original.
        oferta_balanceada: Vector de oferta tras el balanceo.
        demanda_balanceada: Vector de demanda tras el balanceo.
        asignaciones: Matriz con las cantidades asignadas a cada ruta.
        costo_total: Costo total mínimo resultante de la distribución.
        fue_balanceada: Indica si se requirió balanceo.
        tipo_balanceo: Descripción del tipo de balanceo aplicado, si aplica.
        pasos: Lista de cadenas que describen cada paso del algoritmo
            (útil para auditoría y explicación).
    """

    matriz_costos_original: Matriz
    matriz_costos_balanceada: Matriz
    oferta_original: Vector
    demanda_original: Vector
    oferta_balanceada: Vector
    demanda_balanceada: Vector
    asignaciones: Matriz
    costo_total: float
    fue_balanceada: bool
    tipo_balanceo: str
    pasos: List[str] = field(default_factory=list)
