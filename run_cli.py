#!/usr/bin/env python
"""
Lanzador rápido para la Interfaz de Línea de Comandos (CLI) interactiva de Optimización de Transporte.
"""

import os
import sys

# Agregar la carpeta 'src' al sys.path para permitir la importación local del paquete
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from transporte.cli import main

if __name__ == "__main__":
    main()
