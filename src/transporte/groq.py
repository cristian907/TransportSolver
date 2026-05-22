"""
groq.py — Integración modular con la API de Groq para conclusiones logísticas ejecutivas.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from transporte.models import Matriz, ResultadoTransporte, Vector

_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_MODELO_POR_DEFECTO = "llama-3.3-70b-versatile"


def _obtener_api_key() -> str:
    """Obtiene la clave de la API de Groq buscando en el entorno y archivos .env."""
    # 1. Intentar cargar usando python-dotenv si está disponible
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key

    # 2. Intentar cargar manualmente desde un archivo .env en directorios comunes
    ruta_script = os.path.dirname(os.path.abspath(__file__))
    rutas_env = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(ruta_script, "../..", ".env"),
        os.path.join(ruta_script, ".env"),
    ]

    for ruta in rutas_env:
        if os.path.isfile(ruta):
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    for linea in f:
                        linea = linea.strip()
                        if not linea or linea.startswith("#"):
                            continue
                        if "=" in linea:
                            k, v = linea.split("=", 1)
                            k = k.strip()
                            v = v.strip()
                            # Remover comillas si existen
                            if (v.startswith('"') and v.endswith('"')) or (
                                v.startswith("'") and v.endswith("'")
                            ):
                                v = v[1:-1]
                            if k == "GROQ_API_KEY" and v:
                                os.environ["GROQ_API_KEY"] = v
                                return v
            except Exception:
                pass

    raise RuntimeError(
        "No se encontró la clave de API de Groq (GROQ_API_KEY).\n"
        "Por favor, configúrala como variable de entorno o crea un archivo '.env' "
        "con: GROQ_API_KEY=tu_clave_aqui"
    )


def _fmt_matriz(
    matriz: Matriz,
    enc_col: Optional[List[str]] = None,
    enc_fila: Optional[List[str]] = None,
) -> str:
    """Formatea una matriz numérica como tabla en texto plano."""
    if not matriz:
        return "(vacía)"
    lineas: List[str] = []
    if enc_col:
        pre = "         " if enc_fila else ""
        lineas.append(pre + "  ".join(f"{h:>12}" for h in enc_col))
    for idx, fila in enumerate(matriz):
        pre = f"{enc_fila[idx]:>12} " if enc_fila else ""
        lineas.append(pre + "  ".join(f"{v:>12.1f}" for v in fila))
    return "\n".join(lineas)


def _fmt_vector(vector: Vector, etiquetas: Optional[List[str]] = None) -> str:
    """Formatea un vector numérico como cadena legible."""
    if etiquetas:
        return ", ".join(f"'{e}': {v}" for e, v in zip(etiquetas, vector))
    return ", ".join(str(v) for v in vector)


def _prompt_sistema() -> str:
    """Prompt de sistema para el consultor de IA."""
    return (
        "Eres un Consultor Senior de Cadena de Suministro y Logística. "
        "Analiza los resultados de un problema de transporte resuelto "
        "mediante modelos de optimización y redacta una conclusión "
        "ejecutiva sumamente profesional y breve (máximo 2 párrafos). "
        "Evalúa la eficiencia de las rutas elegidas, comenta si el balanceo "
        "afectó la logística real (creación de destinos o fuentes ficticias) "
        "y ofrece recomendaciones prácticas concisas. Responde en español."
    )


def _prompt_usuario(
    r: ResultadoTransporte,
    nombres_orig: Optional[List[str]] = None,
    nombres_dest: Optional[List[str]] = None,
) -> str:
    """Construye el prompt de usuario con los datos y pasos de la solución."""
    m_o = len(r.matriz_costos_original)
    n_o = len(r.matriz_costos_original[0])
    m_b = len(r.matriz_costos_balanceada)
    n_b = len(r.matriz_costos_balanceada[0])

    or_o = nombres_orig if nombres_orig else [f"O{i+1}" for i in range(m_o)]
    de_o = nombres_dest if nombres_dest else [f"D{j+1}" for j in range(n_o)]

    or_b = list(or_o)
    if m_b > m_o:
        or_b.append("Origen Ficticio")

    de_b = list(de_o)
    if n_b > n_o:
        de_b.append("Destino Ficticio")

    partes = [
        "=== ANÁLISIS DEL PROBLEMA DE TRANSPORTE ===",
        f"Orígenes: {m_o} | Destinos: {n_o}",
        f"Balanceo: {'Sí — ' + r.tipo_balanceo if r.fue_balanceada else 'No'}",
        "",
        "── Tabla de Costos Originales ──",
        _fmt_matriz(r.matriz_costos_original, de_o, or_o),
        f"Oferta original: {_fmt_vector(r.oferta_original, or_o)}",
        f"Demanda original: {_fmt_vector(r.demanda_original, de_o)}",
        "",
        "── Matriz de Asignaciones (Solución) ──",
        _fmt_matriz(r.asignaciones, de_b, or_b),
        f"\nCosto Total Mínimo Calculado: {r.costo_total:.2f}",
        "",
        "── Bitácora de Pasos del Algoritmo ──",
        "\n".join(r.pasos),
    ]
    return "\n".join(partes)


def generar_conclusion(
    resultado: ResultadoTransporte,
    nombres_orig: Optional[List[str]] = None,
    nombres_dest: Optional[List[str]] = None,
    modelo: str = _MODELO_POR_DEFECTO,
) -> str:
    """Envía los resultados a Groq y devuelve una conclusión logística ejecutiva.

    Args:
        resultado: Solución completa del problema de transporte.
        nombres_orig: Nombres personalizados de los orígenes.
        nombres_dest: Nombres personalizados de los destinos.
        modelo: Identificador del modelo LLM en Groq.

    Returns:
        Conclusión en texto plano generada por el LLM.
    """
    import urllib.error
    import urllib.request

    payload: Dict[str, Any] = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": _prompt_sistema()},
            {
                "role": "user",
                "content": _prompt_usuario(
                    resultado, nombres_orig, nombres_dest
                ),
            },
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    data_bytes = json.dumps(payload).encode("utf-8")

    api_key = _obtener_api_key()

    req = urllib.request.Request(
        _GROQ_API_URL,
        data=data_bytes,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Error HTTP {e.code} de Groq: {cuerpo}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Error de conexión con Groq: {e}") from e

    data: Dict[str, Any] = json.loads(body)

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(
            f"Respuesta inesperada de Groq: {json.dumps(data, indent=2)}"
        ) from e
