aplicacion"""
Aplicación de Registro Clínico
Python 3.11 | Tkinter | Windows 11
Carga padrón desde Excel, gestiona 30 filas, calcula IMC, colorea diagnósticos y exporta a Excel/PDF
"""

import os
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Dependencias
try:
    import pandas as pd
except ImportError:
    # FIX de sintaxis: Usar \n para salto de línea dentro de la cadena literal.
    messagebox.showerror("Error", "Falta pandas. Ejecuta:\npip install pandas openpyxl")
    sys.exit(1)

try:
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB_DISPONIBLE = True
except ImportError:
    REPORTLAB_DISPONIBLE = False


# ======================== UTILIDADES ========================

def normaliza(texto: str) -> str:
    """Normaliza texto: minúsculas, sin acentos, sin espacios extra."""
    if not isinstance(texto, str):
        texto = "" if texto is None else str(texto)
    texto = texto.lower().strip()
    # Remover acentos
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return texto


def calcular_imc(peso, estatura):
    """Calcula IMC = peso / estatura²"""
    try:
        p = float(str(peso).replace(",", "."))
        e = float(str(estatura).replace(",", "."))
        if e <= 0:
            return ""
        return round(p / (e * e), 2)
    except (ValueError, ZeroDivisionError):
        return ""


# Medicamentos por categoría
MEDICAMENTOS_DIABETES = [
    "insulina", "metformina", "dapagliflozina", 
    "vildagliptina", "sitagliptina"
]

MEDICAMENTOS_HTA = [
    "losartan", "losartán", "amlodipina", "carvedilol",
    "hidroclorotiazida", "bisoprolol", "enalapril",
    "telmisartan", "telmisartán", "valsartan", "valsartán"
]

MEDICAMENTOS_HIPOTIROIDISMO = ["levotiroxina"]

# Colores de fondo
COLOR_VIOLETA = "#9370DB"   # Diabetes
COLOR_CELESTE = "#87CEEB"   # HTA
COLOR_VERDE = "#90EE90"     # Hipotiroidismo
COLOR_ROJO = "#FF6B6B"      # Diabetes + HTA
COLOR_BLANCO = "#FFFFFF"    # Sin diagnóstico


def clasificar_paciente(diagnostico: str, tratamiento: str) -> str:
    """
    Clasifica al paciente según diagnóstico y medicamentos.
    Retorna: 'diabetes', 'hta', 'hipotiroidismo', 'mixto' o 'ninguno'
    """
    diag_norm = normaliza(diagnostico or "")
    trat_norm = normaliza(tratamiento or "")
    
    # Detectar diabetes
    es_diabetico = (
        "diabetes" in diag_norm or 
        "dmt2" in diag_norm or 
        "dm2" in diag_norm or
        "mellitus tipo 2" in diag_norm or
        any(med in trat_norm for med in MEDICAMENTOS_DIABETES)
    )
    
    # Detectar HTA
    es_hipertenso = (
        "hipertension" in diag_norm or
        "hipertensión arterial" in diag_norm or
        "hta" in diag_norm or
        any(med in trat_norm for med in MEDICAMENTOS_HTA)
    )
    
    # Detectar hipotiroidismo
    es_hipotiroideo = (
        "hipotiroidismo" in diag_norm or
        "hipot" in diag_norm or
        any(med in trat_norm for med in MEDICAMENTOS_HIPOTIROIDISMO)
    )
    
    # Prioridad: Diabetes + HTA > individual
    if es_diabetico and es_hipertenso:
        return "mixto"
    if es_diabetico:
        return "diabetes"
    if es_hipertenso:
        return "hta"
    if es_hipotiroideo:
        return "hipotiroidismo"
    
    return "ninguno"


def obtener_color_categoria(categoria: str) -> str:
    """Retorna el color hex según la categoría."""
    colores = {
        "diabetes": COLOR_VIOLETA,
        "hta": COLOR_CELESTE,
        "hipotiroidismo": COLOR_VERDE,
        "mixto": COLOR_ROJO,
        "ninguno": COLOR_BLANCO
    }
    return colores.get(categoria, COLOR_BLANCO)


def calcular_trimestre(fecha: datetime) -> int:
    """Calcula el trimestre (1-4) de una fecha."""
    return (fecha.month - 1) // 3 + 1


# ======================== CARGA DE PADRÓN ========================

def cargar_padron_desde_archivo(ruta: str) -> pd.DataFrame:
    """Carga el padrón desde un archivo Excel o CSV."""
    try:
        if ruta.endswith(".csv"):
            df = pd.read_csv(ruta, encoding="utf-8")
        else:
            df = pd.read_excel(ruta, engine="openpyxl")
        
        # Normalizar nombres de columnas
        df.columns = [str(c).strip() for c in df.columns]
        
        # Asegurar columnas mínimas
        for col in ["DNI", "Nombre", "Beneficio"]:
            if col not in df.columns:
                df[col] = ""
        
        return df
    except Exception as e:
        # FIX de sintaxis: Usar \n para salto de línea dentro de la cadena literal.
        messagebox.showerror("Error al cargar padrón", f"No se pudo leer el archivo:\n{e}")
        return pd.DataFrame(columns=["DNI", "Nombre", "Beneficio"])


# ======================== APLICACIÓN PRINCIPAL ========================

class RegistroClinicoApp(tk.Tk):
    """Aplicación principal de registro clínico."""
    
    def __init__(self):
        super().__init__()
        
        self.title("Registro Clínico - 30 Filas Editables")
        self.geometry("1400x750")
        self.minsize(1200, 650)
        
        # Estado
        self.padron_df = pd.DataFrame(columns=["DNI", "Nombre", "Beneficio"])
        self.padron_path = None
        
        # Columnas de la tabla
        self.columnas = [
            "DNI",
            "Nombre",
            "Beneficio",
            "Presión Arterial (mmHg)",
            "Peso (kg)",
            "Estatura (m)",
            "IMC",
            "Diagnóstico",
            "Tratamiento",
            "Fecha Atención"
        ]
        
        self._construir_interfaz()
        self._configurar_tags_color()
        self._poblar_filas_vacias(30)
        
        # Mensaje inicial
        self.actualizar_estado("Listo. Carga un padrón con 'Cargar Padrón'")
    
    
    def _construir_interfaz(self):
        """Construye la interfaz gráfica."""
        # ===== Barra superior =====
        frame_top = ttk.Frame(self)
        frame_top.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(frame_top, text="📂 Cargar Padrón", 
                   command=self.cargar_padron).pack(side="left", padx=5)
        
        ttk.Button(frame_top, text="📊 Resumen Trimestral", 
                   command=self.mostrar_resumen_trimestral).pack(side="left", padx=5)
        
        ttk.Button(frame_top, text="💾 Exportar Excel", 
                   command=self.exportar_excel).pack(side="left", padx=5)
        
        ttk.Button(frame_top, text="📄 Exportar PDF", 
                   command=self.exportar_pdf).pack(side="left", padx=5)
        
        ttk.Button(frame_top, text="🗑️ Limpiar Tabla", 
                   command=self.limpiar_tabla).pack(side="left", padx=5)
        
        ttk.Label(frame_top, text="💡 Doble clic para editar | IMC automático", 
                  foreground="#666").pack(side="right", padx=10)
        
        # ===== Tabla principal =====
        frame_tabla = ttk.Frame(self)
        frame_tabla.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Scrollbars
        scroll_y = ttk.Scrollbar(frame_tabla, orient="vertical")
        scroll_x = ttk.Scrollbar(frame_tabla, orient="horizontal")
        
        self.tree = ttk.Treeview(
            frame_tabla,
            columns=self.columnas,
            show="headings",
            height=25,
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )
        
        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)
        
        # Configurar columnas
        for col in self.columnas:
            self.tree.heading(col, text=col)
            ancho = 100
            if col in ("DNI", "IMC"):
                ancho = 80
            elif col in ("Nombre", "Diagnóstico", "Tratamiento"):
                ancho = 180
            elif col == "Fecha Atención":
                ancho = 120
            self.tree.column(col, width=ancho, anchor="center")
        
        # Grid
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        
        frame_tabla.rowconfigure(0, weight=1)
        frame_tabla.columnconfigure(0, weight=1)
        
        # Evento doble clic
        self.tree.bind("<Double-1>", self.editar_celda)
        
        # ===== Barra de estado =====
        frame_estado = ttk.Frame(self)
        frame_estado.pack(fill="x", padx=10, pady=(0, 10))
        
        self.label_estado = ttk.Label(frame_estado, text="Iniciando...", 
                                      relief="sunken", anchor="w")
        self.label_estado.pack(fill="x")
    
    
    def _configurar_tags_color(self):
        """Configura los tags de color para la tabla."""
        self.tree.tag_configure("tag_diabetes", background=COLOR_VIOLETA, foreground="#FFFFFF")
        self.tree.tag_configure("tag_hta", background=COLOR_CELESTE, foreground="#000000")
        self.tree.tag_configure("tag_hipotiroidismo", background=COLOR_VERDE, foreground="#000000")
        self.tree.tag_configure("tag_mixto", background=COLOR_ROJO, foreground="#FFFFFF")
        self.tree.tag_configure("tag_ninguno", background=COLOR_BLANCO, foreground="#000000")
    
    
    def _poblar_filas_vacias(self, n: int):
        """Crea N filas vacías en la tabla."""
        for _ in range(n):
            valores = [""] * len(self.columnas)
            self.tree.insert("", "end", values=valores, tags=("tag_ninguno",))
    
    
    def actualizar_estado(self, mensaje: str):
        """Actualiza la barra de estado."""
        self.label_estado.config(text=mensaje)
        self.update_idletasks()
    
    
    # ==================== CARGAR PADRÓN ====================
    
    def cargar_padron(self):
        """Abre diálogo para cargar archivo de padrón."""
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo de padrón",
            filetypes=[
                ("Archivos Excel", "*.xlsx *.xls"),
                ("Archivos CSV", "*.csv"),
                ("Todos los archivos", "*.*")
            ]
        )
        
        if not ruta:
            return
        
        self.padron_df = cargar_padron_desde_archivo(ruta)
        self.padron_path = ruta
        
        registros = len(self.padron_df)
        self.actualizar_estado(f"✅ Padrón cargado: {registros} registros desde {Path(ruta).name}")
        
        # FIX de sintaxis: Usar \n para salto de línea dentro de la cadena literal.
        messagebox.showinfo("Padrón cargado", 
                            f"Se cargaron {registros} registros correctamente.\n"
                            f"Ahora puedes ingresar DNI y autocompletar datos.")
    
    
    # ==================== EDICIÓN DE CELDAS ====================
    
    def editar_celda(self, event):
        """Maneja el doble clic para editar una celda."""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        
        fila_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)  # '#1', '#2', ...
        
        if not fila_id or not col_id:
            return
        
        col_index = int(col_id.replace("#", "")) - 1
        col_nombre = self.columnas[col_index]
        
        # Obtener coordenadas
        x, y, ancho, alto = self.tree.bbox(fila_id, col_id)
        valor_actual = self.tree.set(fila_id, col_nombre)
        
        # Crear Entry para edición
        editor = tk.Entry(self.tree, justify="center")
        editor.insert(0, valor_actual)
        editor.select_range(0, tk.END)
        editor.focus()
        
        def finalizar_edicion(event=None):
            nuevo_valor = editor.get().strip()
            editor.destroy()
            self.tree.set(fila_id, col_nombre, nuevo_valor)
            self.post_edicion(fila_id, col_nombre)
        
        def cancelar_edicion(event=None):
            editor.destroy()
        
        editor.bind("<Return>", finalizar_edicion)
        editor.bind("<FocusOut>", finalizar_edicion)
        editor.bind("<Escape>", cancelar_edicion)
        
        editor.place(x=x, y=y, width=ancho, height=alto)
    
    
    def post_edicion(self, fila_id, columna):
        """Aplica reglas después de editar una celda."""
        valores = self.tree.item(fila_id, "values")
        fila = {self.columnas[i]: valores[i] for i in range(len(self.columnas))}
        
        # 1. Autocompletar Nombre y Beneficio al ingresar DNI
        if columna == "DNI":
            dni = str(fila.get("DNI", "")).strip()
            if dni:
                nombre, beneficio = self.buscar_en_padron(dni)
                self.tree.set(fila_id, "Nombre", nombre)
                self.tree.set(fila_id, "Beneficio", beneficio)
                if nombre:
                    self.actualizar_estado(f"✅ Datos autocompletados para DNI: {dni}")
        
        # 2. Agregar unidad a Presión Arterial
        if columna == "Presión Arterial (mmHg)":
            pa = str(fila.get("Presión Arterial (mmHg)", "")).strip()
            if pa and "mmhg" not in normaliza(pa):
                self.tree.set(fila_id, "Presión Arterial (mmHg)", f"{pa} mmHg")
        
        # 3. Calcular IMC automáticamente
        if columna in ("Peso (kg)", "Estatura (m)"):
            peso = self.tree.set(fila_id, "Peso (kg)")
            estatura = self.tree.set(fila_id, "Estatura (m)")
            imc = calcular_imc(peso, estatura)
            self.tree.set(fila_id, "IMC", imc if imc != "" else "")
        
        # 4. Actualizar color según diagnóstico/tratamiento
        if columna in ("Diagnóstico", "Tratamiento"):
            self.actualizar_color_fila(fila_id)
    
    
    def buscar_en_padron(self, dni: str) -> tuple:
        """Busca DNI en el padrón y retorna (Nombre, Beneficio)."""
        if self.padron_df.empty:
            return "", ""
        
        df = self.padron_df.copy()
        df["DNI"] = df["DNI"].astype(str).str.strip()
        
        resultado = df[df["DNI"] == dni]
        if not resultado.empty:
            fila = resultado.iloc[0]
            nombre = str(fila.get("Nombre", "") or "")
            beneficio = str(fila.get("Beneficio", "") or "")
            return nombre, beneficio
        
        return "", ""
    
    
    def actualizar_color_fila(self, fila_id):
        """Actualiza el color de la fila según diagnóstico/tratamiento."""
        valores = self.tree.item(fila_id, "values")
        fila = {self.columnas[i]: valores[i] for i in range(len(self.columnas))}
        
        diagnostico = fila.get("Diagnóstico", "")
        tratamiento = fila.get("Tratamiento", "")
        
        categoria = clasificar_paciente(diagnostico, tratamiento)
        tag = f"tag_{categoria}"
        
        self.tree.item(fila_id, tags=(tag,))
    
    
    # ==================== FUNCIONES DE TABLA ====================
    
    def obtener_datos_tabla(self) -> list:
        """Retorna todos los datos de la tabla como lista de diccionarios."""
        filas = []
        for fila_id in self.tree.get_children():
            valores = self.tree.item(fila_id, "values")
            fila = {self.columnas[i]: str(valores[i]).strip() 
                    for i in range(len(self.columnas))}
            
            # Solo incluir filas con al menos DNI
            if fila.get("DNI"):
                filas.append(fila)
        
        return filas
    
    
    def limpiar_tabla(self):
        """Limpia todas las filas de la tabla."""
        if not messagebox.askyesno("Confirmar", "¿Limpiar toda la tabla?"):
            return
        
        for fila_id in self.tree.get_children():
            self.tree.delete(fila_id)
        
        self._poblar_filas_vacias(30)
        self.actualizar_estado("🗑️ Tabla limpiada")
    
    
    # ==================== RESUMEN TRIMESTRAL ====================
    
    def mostrar_resumen_trimestral(self):
        """Muestra ventana con resumen de atenciones por trimestre."""
        filas = self.obtener_datos_tabla()
        
        if not filas:
            messagebox.showinfo("Sin datos", "No hay datos para generar resumen.")
            return
        
        # Construir datos
        datos_resumen = []
        for fila in filas:
            dni = fila.get("DNI", "")
            fecha_str = fila.get("Fecha Atención", "")
            
            if not dni or not fecha_str:
                continue
            
            try:
                # Intentar varios formatos
                if "-" in fecha_str:
                    fecha = datetime.fromisoformat(fecha_str)
                else:
                    fecha = datetime.strptime(fecha_str, "%d/%m/%Y")
                
                datos_resumen.append({
                    "DNI": dni,
                    "Año": fecha.year,
                    "Trimestre": calcular_trimestre(fecha)
                })
            except ValueError:
                continue
        
        if not datos_resumen:
            messagebox.showinfo("Sin fechas válidas", 
                                "No se encontraron fechas válidas para el resumen.")
            return
        
        # Agrupar y contar
        df_resumen = pd.DataFrame(datos_resumen)
        resumen = df_resumen.groupby(["DNI", "Año", "Trimestre"]).size().reset_index(name="Atenciones")
        
        # Mostrar ventana
        ventana = tk.Toplevel(self)
        ventana.title("Resumen Trimestral de Atenciones")
        ventana.geometry("700x500")
        
        # Tabla
        cols = ["DNI", "Año", "Trimestre", "Atenciones"]
        tree = ttk.Treeview(ventana, columns=cols, show="headings")
        
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor="center")
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Poblar datos
        for _, row in resumen.iterrows():
            tree.insert("", "end", values=[
                row["DNI"], row["Año"], 
                f"Q{row['Trimestre']}", row["Atenciones"]
            ])
        
        ttk.Button(ventana, text="Cerrar", 
                   command=ventana.destroy).pack(pady=10)
    
    
    # ==================== EXPORTAR EXCEL ====================
    
    def exportar_excel(self):
        """Exporta los datos a un archivo Excel con colores."""
        filas = self.obtener_datos_tabla()
        
        if not filas:
            messagebox.showinfo("Sin datos", "No hay datos para exportar.")
            return
        
        ruta = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Archivo Excel", "*.xlsx")],
            title="Guardar como"
        )
        
        if not ruta:
            return
        
        try:
            df = pd.DataFrame(filas)
            
            with pd.ExcelWriter(ruta, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Datos")
                
                workbook = writer.book
                worksheet = writer.sheets["Datos"]
                
                # Formatos de color
                fmt_diabetes = workbook.add_format({
                    "bg_color": COLOR_VIOLETA, "font_color": "#FFFFFF"
                })
                fmt_hta = workbook.add_format({
                    "bg_color": COLOR_CELESTE
                })
                fmt_hipot = workbook.add_format({
                    "bg_color": COLOR_VERDE
                })
                fmt_mixto = workbook.add_format({
                    "bg_color": COLOR_ROJO, "font_color": "#FFFFFF"
                })
                
                # Aplicar formatos
                for i, fila in enumerate(filas, start=1):
                    categoria = clasificar_paciente(
                        fila.get("Diagnóstico", ""),
                        fila.get("Tratamiento", "")
                    )
                    
                    formato = None
                    if categoria == "diabetes":
                        formato = fmt_diabetes
                    elif categoria == "hta":
                        formato = fmt_hta
                    elif categoria == "hipotiroidismo":
                        formato = fmt_hipot
                    elif categoria == "mixto":
                        formato = fmt_mixto
                    
                    if formato:
                        worksheet.set_row(i, None, formato)
            
            self.actualizar_estado(f"✅ Excel exportado: {Path(ruta).name}")
            # FIX de sintaxis: Usar \n para salto de línea dentro de la cadena literal.
            messagebox.showinfo("Exportado", f"Archivo guardado:\n{ruta}")
            
        except Exception as e:
            # FIX de sintaxis: Usar \n para salto de línea dentro de la cadena literal.
            messagebox.showerror("Error al exportar", f"No se pudo exportar:\n{e}")
    
    
    # ==================== EXPORTAR PDF ====================
    
    def exportar_pdf(self):
        """Exporta los datos a un archivo PDF."""
        if not REPORTLAB_DISPONIBLE:
            # FIX de sintaxis: Usar \n para salto de línea dentro de la cadena literal.
            messagebox.showwarning("Reportlab no disponible", 
                                   "Instala reportlab con:\npip install reportlab")
            return
        
        filas = self.obtener_datos_tabla()
        
        if not filas:
            messagebox.showinfo("Sin datos", "No hay datos para exportar.")
            return
        
        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Archivo PDF", "*.pdf")],
            title="Guardar como"
        )
        
        if not ruta:
            return
        
        try:
            # Preparar tabla
            headers = self.columnas
            datos = [headers]
            
            for fila in filas:
                datos.append([fila.get(col, "") for col in headers])
            
            # Crear PDF
            doc = SimpleDocTemplate(
                ruta,
                pagesize=landscape(A4),
                leftMargin=15, rightMargin=15,
                topMargin=20, bottomMargin=20
            )
            
            elementos = []
            estilos = getSampleStyleSheet()
            
            titulo = Paragraph("Registro Clínico - Atenciones", estilos["Title"])
            elementos.append(titulo)
            elementos.append(Spacer(1, 12))
            
            tabla = Table(datos, repeatRows=1)
            
            # Estilos base
            estilo_tabla = [
                ("BACKGROUND", (0, 0), (-1, 0), rl_colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
            ]
            
            # Aplicar colores por fila
            for i, fila in enumerate(filas, start=1):
                categoria = clasificar_paciente(
                    fila.get("Diagnóstico", ""),
                    fila.get("Tratamiento", "")
                )
                
                color = obtener_color_categoria(categoria)
                estilo_tabla.append((
                    "BACKGROUND", (0, i), (-1, i), rl_colors.HexColor(color)
                ))
            
            tabla.setStyle(TableStyle(estilo_tabla))
            elementos.append(tabla)
            
            doc.build(elementos)
            
            self.actualizar_estado(f"✅ PDF exportado: {Path(ruta).name}")
            # FIX de sintaxis: Usar \n para salto de línea dentro de la cadena literal.
            messagebox.showinfo("Exportado", f"PDF guardado:\n{ruta}")
            
        except Exception as e:
            # FIX de sintaxis: Usar \n para salto de línea dentro de la cadena literal.
            messagebox.showerror("Error al exportar", f"No se pudo exportar:\n{e}")


# ======================== MAIN ========================

if __name__ == "__main__":
    app = RegistroClinicoApp()
    app.mainloop()
