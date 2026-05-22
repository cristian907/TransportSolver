"""
Paquete de Optimización de Transporte.
Proporciona modelos y algoritmos para resolver problemas de asignación de transporte.
"""

from __future__ import annotations

from transporte.core import balancear, validar_entradas, generar_texto_reporte, guardar_reporte_txt
from transporte.groq import generar_conclusion
from transporte.models import Matriz, ResultadoTransporte, Vector
from transporte.solvers import (
    resolver_coste_minimo,
    resolver_esquina_noroeste,
    resolver_vogel,
)

__all__ = [
    "Matriz",
    "Vector",
    "ResultadoTransporte",
    "validar_entradas",
    "balancear",
    "resolver_coste_minimo",
    "resolver_esquina_noroeste",
    "resolver_vogel",
    "generar_conclusion",
    "generar_texto_reporte",
    "guardar_reporte_txt",
]
