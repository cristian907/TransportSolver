"""
gui.py — Interfaz Gráfica de Usuario (GUI) unificada y premium usando PyQt6.
Permite configurar el problema de transporte, ingresar datos tipo Excel,
elegir el algoritmo de resolución y generar reportes con Groq AI.
"""

from __future__ import annotations

import sys
import threading
from typing import List

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from transporte.groq import generar_conclusion
from transporte.models import Matriz, ResultadoTransporte, Vector
from transporte.solvers import resolver_coste_minimo, resolver_esquina_noroeste, resolver_vogel

# ─────────────────────────────────────────────
# QSS (Hojas de Estilo de Qt) para estética Premium
# ─────────────────────────────────────────────
QSS_THEME = """
QMainWindow {
    background-color: #0f172a; /* Slate 900 */
}

QWidget {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    color: #e2e8f0;
}

QLabel {
    font-size: 14px;
}

QLineEdit {
    background-color: #1e293b; /* Slate 800 */
    border: 2px solid #334155;
    border-radius: 6px;
    padding: 8px 12px;
    color: #f8fafc;
    font-size: 14px;
}

QLineEdit:focus {
    border: 2px solid #6366f1; /* Indigo 500 */
}

QComboBox {
    background-color: #1e293b;
    border: 2px solid #334155;
    border-radius: 6px;
    padding: 8px 12px;
    color: #f8fafc;
    font-size: 14px;
}

QComboBox:focus {
    border: 2px solid #6366f1;
}

QPushButton {
    background-color: #3b82f6; /* Blue 500 */
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 14px;
}

QPushButton:hover {
    background-color: #2563eb;
}

QPushButton:pressed {
    background-color: #1d4ed8;
}

QPushButton#btn-resolver {
    background-color: #10b981; /* Emerald 500 */
}

QPushButton#btn-resolver:hover {
    background-color: #059669;
}

QPushButton#btn-back {
    background-color: #475569; /* Slate 600 */
}

QPushButton#btn-back:hover {
    background-color: #334155;
}

QTableWidget {
    background-color: #1e293b;
    gridline-color: #334155;
    border: 1px solid #334155;
    border-radius: 8px;
    font-size: 16px;
    color: #f8fafc;
}

QTableWidget::item {
    padding: 5px;
}

QTableWidget::item:focus {
    background-color: #334155;
    color: #f8fafc;
}

QHeaderView::section {
    background-color: #334155;
    color: #cbd5e1;
    font-weight: bold;
    font-size: 14px;
    border: 1px solid #1e293b;
    padding: 5px;
}

QTextEdit {
    background-color: #020617; /* Very Dark Slate */
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 15px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 14px;
    color: #38bdf8; /* Light Sky Blue */
}
"""


class WorkerSignals(QObject):
    """Canales de comunicación seguros para hilos secundarios."""

    finished = pyqtSignal(str)
    error = pyqtSignal(str)


class MainWindow(QMainWindow):
    """Ventana principal que gestiona las tres pantallas unificadas de la GUI."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Optimización de Transporte Inteligente — PyQt6")
        self.resize(1100, 750)
        self.setMinimumSize(900, 650)
        self.setStyleSheet(QSS_THEME)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        self.current_view = None
        self.mostrar_configuracion_inicial()

    def set_view(self, view_widget: QWidget):
        """Reemplaza dinámicamente la vista actual con animación de limpieza."""
        if self.current_view:
            self.current_view.deleteLater()
        self.current_view = view_widget
        self.main_layout.addWidget(self.current_view)

    # ── PANTALLA 1: CONFIGURACIÓN INICIAL ──
    def mostrar_configuracion_inicial(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(25)

        # Encabezado
        title = QLabel("<b>Optimización de Distribución y Transporte</b>")
        title.setStyleSheet("font-size: 26px; color: #f8fafc; font-weight: 800;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Configura los orígenes, destinos y el método matemático de resolución.")
        subtitle.setStyleSheet("font-size: 14px; color: #94a3b8;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Formulario
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(15)

        # Fila Orígenes
        h_ori = QHBoxLayout()
        lbl_ori = QLabel("Número de Orígenes (Fábricas / Fuentes):")
        lbl_ori.setStyleSheet("font-size: 15px; color: #cbd5e1; font-weight: 600;")
        self.txt_ori = QLineEdit("3")
        self.txt_ori.setMaximumWidth(150)
        h_ori.addWidget(lbl_ori)
        h_ori.addWidget(self.txt_ori)
        form_layout.addLayout(h_ori)

        # Fila Destinos
        h_des = QHBoxLayout()
        lbl_des = QLabel("Número de Destinos (Centros de Consumo):")
        lbl_des.setStyleSheet("font-size: 15px; color: #cbd5e1; font-weight: 600;")
        self.txt_des = QLineEdit("4")
        self.txt_des.setMaximumWidth(150)
        h_des.addWidget(lbl_des)
        h_des.addWidget(self.txt_des)
        form_layout.addLayout(h_des)

        # Fila Algoritmo
        h_alg = QHBoxLayout()
        lbl_alg = QLabel("Método de Optimización Matemática:")
        lbl_alg.setStyleSheet("font-size: 15px; color: #cbd5e1; font-weight: 600;")
        self.cmb_alg = QComboBox()
        self.cmb_alg.addItems(
            [
                "Método del Costo Mínimo",
                "Método de la Esquina Noroeste",
                "Aproximación de Vogel (VAM)",
            ]
        )
        self.cmb_alg.setMaximumWidth(300)
        h_alg.addWidget(lbl_alg)
        h_alg.addWidget(self.cmb_alg)
        form_layout.addLayout(h_alg)

        layout.addWidget(form_widget)

        # Botón Siguiente
        btn_next = QPushButton("Siguiente Paso ➔")
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.setStyleSheet("font-size: 16px; padding: 12px 30px; border-radius: 8px;")
        btn_next.clicked.connect(self.validar_e_ir_a_datos)
        
        h_btn = QHBoxLayout()
        h_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_btn.addWidget(btn_next)
        layout.addLayout(h_btn)

        self.set_view(w)

    def validar_e_ir_a_datos(self):
        try:
            r = int(self.txt_ori.text())
            c = int(self.txt_des.text())
            if r <= 0 or c <= 0:
                raise ValueError
            self.num_ori = r
            self.num_des = c
            self.metodo_seleccionado = self.cmb_alg.currentText()
        except ValueError:
            QMessageBox.critical(
                self,
                "Configuración Inválida",
                "Por favor, ingresa números enteros positivos mayores que cero para orígenes y destinos.",
            )
            return

        self.mostrar_matriz_datos()

    # ── PANTALLA 2: GRID DE DATOS EXCEL-LIKE ──
    def mostrar_matriz_datos(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(15)

        title = QLabel(f"<b>Matriz de Costos, Oferta y Demanda ({self.metodo_seleccionado})</b>")
        title.setStyleSheet("font-size: 18px; color: #f8fafc; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Double-click en los encabezados de fila y columna para personalizar nombres de orígenes y destinos."
        )
        subtitle.setStyleSheet("font-size: 13px; color: #94a3b8; font-style: italic;")
        layout.addWidget(subtitle)

        # Grid de datos
        r, c = self.num_ori, self.num_des
        self.table = QTableWidget(r + 1, c + 1)
        self.table.setAlternatingRowColors(True)

        # Encabezados por defecto
        origenes = [f"Origen {i+1}" for i in range(r)] + ["Demanda"]
        destinos = [f"Destino {j+1}" for j in range(c)] + ["Oferta"]

        self.table.setVerticalHeaderLabels(origenes)
        self.table.setHorizontalHeaderLabels(destinos)

        # Población inicial con 0s y bloqueo de celda muerta inferior derecha
        for i in range(r + 1):
            for j in range(c + 1):
                if i == r and j == c:
                    item = QTableWidgetItem("")
                    item.setFlags(Qt.ItemFlag.NoItemFlags)
                    item.setBackground(Qt.GlobalColor.darkGray)
                    self.table.setItem(i, j, item)
                else:
                    item = QTableWidgetItem("0")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(i, j, item)

        # Ajuste de tamaño automático
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Permitir renombrar haciendo doble clic en cabeceras
        self.table.horizontalHeader().sectionDoubleClicked.connect(
            self.editar_encabezado_horizontal
        )
        self.table.verticalHeader().sectionDoubleClicked.connect(
            self.editar_encabezado_vertical
        )

        layout.addWidget(self.table)

        # Controles inferiores
        h_btn = QHBoxLayout()
        
        btn_back = QPushButton("⬅ Modificar Dimensiones")
        btn_back.setObjectName("btn-back")
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self.mostrar_configuracion_inicial)
        h_btn.addWidget(btn_back)

        btn_solve = QPushButton("Resolver Problema ✔")
        btn_solve.setObjectName("btn-resolver")
        btn_solve.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_solve.clicked.connect(self.ejecutar_resolucion)
        h_btn.addWidget(btn_solve)

        layout.addLayout(h_btn)
        self.set_view(w)

    def editar_encabezado_horizontal(self, index: int):
        if index == self.num_des:
            return  # No renombrar la columna "Oferta"
        nuevo_nombre, ok = QInputDialog.getText(
            self,
            "Personalizar Destino",
            f"Ingresa el nombre personalizado para el Destino {index + 1}:",
        )
        if ok and nuevo_nombre.strip():
            self.table.horizontalHeaderItem(index).setText(nuevo_nombre.strip())

    def editar_encabezado_vertical(self, index: int):
        if index == self.num_ori:
            return  # No renombrar la fila "Demanda"
        nuevo_nombre, ok = QInputDialog.getText(
            self,
            "Personalizar Origen",
            f"Ingresa el nombre personalizado para el Origen {index + 1}:",
        )
        if ok and nuevo_nombre.strip():
            self.table.verticalHeaderItem(index).setText(nuevo_nombre.strip())

    def ejecutar_resolucion(self):
        r, c = self.num_ori, self.num_des
        costos = []
        oferta = []
        demanda = []

        try:
            for i in range(r):
                fila = []
                for j in range(c):
                    val = float(self.table.item(i, j).text())
                    if val < 0:
                        raise ValueError(f"El costo en ({i+1},{j+1}) no puede ser negativo.")
                    fila.append(val)
                costos.append(fila)

                of = float(self.table.item(i, c).text())
                if of < 0:
                    raise ValueError(f"La oferta en el Origen {i+1} no puede ser negativa.")
                oferta.append(of)

            for j in range(c):
                dem = float(self.table.item(r, j).text())
                if dem < 0:
                    raise ValueError(f"La demanda en el Destino {j+1} no puede ser negativa.")
                demanda.append(dem)

            if sum(oferta) == 0 or sum(demanda) == 0:
                raise ValueError("La oferta y demanda totales deben ser mayores que cero.")

        except ValueError as ve:
            QMessageBox.critical(
                self,
                "Error en Datos",
                str(ve) if str(ve) else "Asegúrate de ingresar únicamente números válidos.",
            )
            return
        except Exception as e:
            QMessageBox.critical(self, "Error de Entrada", f"Ocurrió un error inesperado: {e}")
            return

        # Recuperar nombres personalizados
        nombres_orig = [self.table.verticalHeaderItem(i).text() for i in range(r)]
        nombres_dest = [self.table.horizontalHeaderItem(j).text() for j in range(c)]

        # Seleccionar solucionador
        solvers_dict = {
            "Método del Costo Mínimo": resolver_coste_minimo,
            "Método de la Esquina Noroeste": resolver_esquina_noroeste,
            "Aproximación de Vogel (VAM)": resolver_vogel,
        }

        solver_func = solvers_dict[self.metodo_seleccionado]

        try:
            resultado = solver_func(costos, oferta, demanda)
        except Exception as e:
            QMessageBox.critical(self, "Error de Resolución", f"Error interno en el algoritmo: {e}")
            return

        self.mostrar_resultados(resultado, nombres_orig, nombres_dest)

    # ── PANTALLA 3: RESULTADOS PREMIUM Y CONEXIÓN CON GROQ AI ──
    def mostrar_resultados(
        self, resultado: ResultadoTransporte, nombres_orig: List[str], nombres_dest: List[str]
    ):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(15)

        title = QLabel(f"<b>Solución y Análisis — {self.metodo_seleccionado}</b>")
        title.setStyleSheet("font-size: 20px; color: #f8fafc; font-weight: 800;")
        layout.addWidget(title)

        # Consola de Resultados
        self.txt_reporte = QTextEdit()
        self.txt_reporte.setReadOnly(True)
        layout.addWidget(self.txt_reporte)

        def p(msg: str):
            self.txt_reporte.append(msg)

        def format_matriz(titulo: str, matriz: Matriz, origenes: List[str], destinos: List[str]) -> str:
            ancho_col = max(12, max([len(d) for d in destinos]) + 2)
            ancho_fila = max(16, max([len(o) for o in origenes]) + 2)

            res = f"\n  {titulo}\n"
            res += f"  {'':>{ancho_fila}}"
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

        def format_vector(titulo: str, vector: Vector, etiquetas: List[str]) -> str:
            partes = [f"'{e}': {v}" for e, v in zip(etiquetas, vector)]
            return f"  {titulo}: {', '.join(partes)}\n"

        m_o, n_o = len(resultado.matriz_costos_original), len(resultado.matriz_costos_original[0])
        m_b, n_b = len(resultado.matriz_costos_balanceada), len(resultado.matriz_costos_balanceada[0])
        or_b = list(nombres_orig) + ["Origen Ficticio"] if m_b > m_o else list(nombres_orig)
        de_b = list(nombres_dest) + ["Destino Ficticio"] if n_b > n_o else list(nombres_dest)

        # Imprimir bitácora inicial
        p("=" * 70)
        p("  1. DATOS ORIGINALES DEL PROBLEMA")
        p("=" * 70)
        p(format_matriz("Tabla de Costos Unitarios:", resultado.matriz_costos_original, nombres_orig, nombres_dest))
        p(format_vector("Oferta", resultado.oferta_original, nombres_orig))
        p(format_vector("Demanda", resultado.demanda_original, nombres_dest))

        p("\n" + "=" * 70)
        p("  2. PROCESO DE BALANCEO")
        p("=" * 70)
        if resultado.fue_balanceada:
            p(f"  [Ajuste de Capacidad]: {resultado.tipo_balanceo}")
            p(format_matriz("Tabla de Costos (Balanceada):", resultado.matriz_costos_balanceada, or_b, de_b))
        else:
            p("  [✓ OK]: Oferta y Demanda balanceadas perfectamente de forma nativa.")

        p("\n" + "=" * 70)
        p("  3. RESULTADO DE ASIGNACIONES ÓPTIMAS")
        p("=" * 70)
        p(format_matriz("Matriz de Asignaciones (Unidades a enviar):", resultado.asignaciones, or_b, de_b))
        p(f"  ★ COSTO TOTAL MÍNIMO DISTRIBUIDO: $ {resultado.costo_total:.2f}\n")

        p("=" * 70)
        p("  4. BITÁCORA DE PASOS PASO A PASO")
        p("=" * 70)
        for paso in resultado.pasos:
            p(f"  {paso}\n")

        p("\n" + "=" * 70)
        p("  5. CONCLUSIÓN LOGÍSTICA EJECUTIVA (Groq AI)")
        p("=" * 70)
        p("  ⏳ Conectando con la API de Groq para formular diagnóstico...")

        # Hilo de comunicación en segundo plano para Groq AI
        self.worker_signals = WorkerSignals()

        def al_terminar_ia(conclusion_texto):
            p(f"\n  ✓ DIAGNÓSTICO EJECUTIVO COMPLETADO:\n\n{conclusion_texto}")
            try:
                from transporte.core import guardar_reporte_txt
                guardar_reporte_txt(resultado, nombres_orig, nombres_dest, self.metodo_seleccionado, conclusion_texto)
                p(f"\n{'═'*70}\n  ✓ REPORTE GUARDADO AUTOMÁTICAMENTE EN: 'reporte_transporte.txt'\n{'═'*70}")
            except Exception as e:
                p(f"\n  ⚠ Error al guardar el archivo de reporte: {e}")

        def al_fallar_ia(err_msg):
            p(f"\n  ✗ ERROR AL CONECTAR CON EL ASISTENTE DE IA: {err_msg}")
            try:
                from transporte.core import guardar_reporte_txt
                guardar_reporte_txt(resultado, nombres_orig, nombres_dest, self.metodo_seleccionado, f"Error al generar la conclusión con IA: {err_msg}")
                p(f"\n{'═'*70}\n  ✓ REPORTE GUARDADO AUTOMÁTICAMENTE EN: 'reporte_transporte.txt' (sin conclusión de IA)\n{'═'*70}")
            except Exception as e:
                p(f"\n  ⚠ Error al guardar el archivo de reporte: {e}")

        self.worker_signals.finished.connect(al_terminar_ia)
        self.worker_signals.error.connect(al_fallar_ia)

        def query_ai_thread():
            try:
                conclusion = generar_conclusion(resultado, nombres_orig, nombres_dest)
                self.worker_signals.finished.emit(conclusion)
            except Exception as e:
                self.worker_signals.error.emit(str(e))

        threading.Thread(target=query_ai_thread, daemon=True).start()

        # Botón Volver a empezar
        btn_restart = QPushButton("Realizar Nuevo Análisis ➔")
        btn_restart.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_restart.clicked.connect(self.mostrar_configuracion_inicial)
        layout.addWidget(btn_restart)

        self.set_view(w)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
