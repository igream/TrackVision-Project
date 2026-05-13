import os

import cv2
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

from config.frontend import (
    PRIMARY_COLOR,
    SECONDARY_COLOR,
    ACCENT_COLOR,
    WHITE,
    LIGHT_GRAY,
    DARK_GRAY,
    BORDER_COLOR,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_BG_COLOR,
    TITLE_FONT,
    SUBTITLE_FONT,
    LABEL_FONT,
    NORMAL_FONT,
    SMALL_FONT,
    TEXT_FONT,
    LOGO_PATH,
    LOGO_SIZE,
    IMAGE_CAROUSEL_WIDTH,
    IMAGE_CAROUSEL_HEIGHT,
    IMAGE_CAROUSEL_BG,
    IMAGE_CELL_WIDTH,
    IMAGE_CELL_HEIGHT,
    IMAGE_PADDING_X,
    IMAGE_PADDING_Y,
    TEXT_BOX_HEIGHT,
    TEXT_BOX_BG,
    TEXT_BOX_FG,
    TEXT_BOX_BORDER,
    BUTTON_PADDING_X,
    RUTA_LABEL_WRAPLENGTH,
    MAIN_FRAME_PADDING,
    RESULT_FRAME_PADDING,
    TEXT_FRAME_PADDING,
    LOGO_FRAME_PADDING,
    TITLE_PADY,
    RUTA_PADY,
    IMG_FRAME_PADY,
    RESULT_PADY,
    TEXT_FRAME_PADY,
    BUTTON_PADY,
)
from ocr_core import DetectionResult, process_plate_image
from storage import save_detection_result


class ImageCarousel:
    """Carrusel de imágenes con navegación."""
    def __init__(self, parent, etapas, width, height):
        self.etapas = etapas
        self.current_index = 0
        self.photo_images = []
        
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas para mostrar la imagen
        self.canvas = tk.Canvas(
            self.frame,
            width=width,
            height=height,
            bg=IMAGE_CAROUSEL_BG,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR
        )
        self.canvas.pack(pady=(0, 10))
        
        # Frame para controles
        control_frame = ttk.Frame(self.frame)
        control_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Botón anterior
        prev_btn = ttk.Button(
            control_frame,
            text="◀ Anterior",
            command=self._prev_image
        )
        prev_btn.pack(side=tk.LEFT, padx=5)
        
        # Indicador de posición
        self.position_label = ttk.Label(
            control_frame,
            text=f"1 / {len(etapas)}",
            font=SMALL_FONT
        )
        self.position_label.pack(side=tk.LEFT, expand=True)
        
        # Botón siguiente
        next_btn = ttk.Button(
            control_frame,
            text="Siguiente ▶",
            command=self._next_image
        )
        next_btn.pack(side=tk.RIGHT, padx=5)
        
        # Etiqueta del título
        self.title_label = ttk.Label(
            self.frame,
            text="",
            font=LABEL_FONT,
            foreground=PRIMARY_COLOR
        )
        self.title_label.pack(pady=5)
        
        self._display_image()
    
    def _display_image(self):
        titulo, imagen = self.etapas[self.current_index]
        
        if len(imagen.shape) == 2:
            img_rgb = cv2.cvtColor(imagen, cv2.COLOR_GRAY2RGB)
        else:
            img_rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
        
        img_resized = cv2.resize(img_rgb, (IMAGE_CAROUSEL_WIDTH - 20, IMAGE_CAROUSEL_HEIGHT - 20))
        img_pil = Image.fromarray(img_resized)
        img_tk = ImageTk.PhotoImage(img_pil)
        
        self.photo_images = [img_tk]
        
        self.canvas.create_image(
            IMAGE_CAROUSEL_WIDTH // 2,
            IMAGE_CAROUSEL_HEIGHT // 2,
            image=img_tk
        )
        
        self.title_label.config(text=titulo)
        self.position_label.config(text=f"{self.current_index + 1} / {len(self.etapas)}")
    
    def _next_image(self):
        self.current_index = (self.current_index + 1) % len(self.etapas)
        self._display_image()
    
    def _prev_image(self):
        self.current_index = (self.current_index - 1) % len(self.etapas)
        self._display_image()


class OCRApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("OCR Placas - Detección Inteligente de Matrículas")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.configure(bg=WINDOW_BG_COLOR)
        
        # Configurar estilo
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=WHITE)
        style.configure('TLabel', background=WHITE, foreground=DARK_GRAY)
        style.configure('TButton', font=NORMAL_FONT)
        style.configure('TLabelFrame', background=WHITE, foreground=DARK_GRAY)
        style.map('TButton',
                  background=[('active', SECONDARY_COLOR), ('pressed', PRIMARY_COLOR)],
                  foreground=[('active', WHITE)])

        self.archivo_seleccionado = tk.StringVar(value="Ningún archivo seleccionado")
        self.carousel = None
        self.result_container = None
        self.logo_tk = None

        self._build_ui()

    def _build_ui(self) -> None:
        # Frame superior con logo y título
        header_frame = tk.Frame(self.root, bg=PRIMARY_COLOR, height=100)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)
        
        header_frame_inner = tk.Frame(header_frame, bg=PRIMARY_COLOR)
        header_frame_inner.pack(fill=tk.BOTH, expand=True, padx=LOGO_FRAME_PADDING, pady=LOGO_FRAME_PADDING)
        
        # Cargar y mostrar logo
        try:
            if os.path.exists(LOGO_PATH):
                logo_img = Image.open(LOGO_PATH)
                logo_img.thumbnail(LOGO_SIZE, Image.Resampling.LANCZOS)
                self.logo_tk = ImageTk.PhotoImage(logo_img)
                logo_label = tk.Label(header_frame_inner, image=self.logo_tk, bg=PRIMARY_COLOR)
                logo_label.pack(side=tk.LEFT, padx=(0, 15))
        except Exception:
            pass
        
        # Título
        title_label = tk.Label(
            header_frame_inner,
            text="OCR Placas",
            font=TITLE_FONT,
            bg=PRIMARY_COLOR,
            fg=WHITE
        )
        title_label.pack(side=tk.LEFT, anchor=tk.W)
        
        # Frame principal
        main_frame = ttk.Frame(self.root, padding=MAIN_FRAME_PADDING)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Sección de selección de archivo
        input_frame = ttk.LabelFrame(
            main_frame,
            text="Seleccionar Imagen",
            padding=RESULT_FRAME_PADDING,
        )
        input_frame.pack(fill=tk.X, pady=(0, 15))

        ruta_label = ttk.Label(
            input_frame,
            textvariable=self.archivo_seleccionado,
            wraplength=RUTA_LABEL_WRAPLENGTH,
            font=SMALL_FONT,
            foreground=DARK_GRAY
        )
        ruta_label.pack(fill=tk.X, pady=(0, 10))

        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill=tk.X)

        seleccionar_btn = ttk.Button(
            button_frame,
            text="📁 Seleccionar archivo",
            command=self._seleccionar_archivo,
            width=20
        )
        seleccionar_btn.pack(side=tk.LEFT, padx=(0, 10))

        procesar_btn = ttk.Button(
            button_frame,
            text="⚙️ Procesar",
            command=self._procesar_archivo,
            width=20
        )
        procesar_btn.pack(side=tk.LEFT)

        # Contenedor para resultados
        self.result_container = ttk.LabelFrame(
            main_frame,
            text="Resultados",
            padding=RESULT_FRAME_PADDING,
        )
        self.result_container.pack(fill=tk.BOTH, expand=True, pady=RESULT_PADY)
        self.result_container.columnconfigure(0, weight=1)

    def _seleccionar_archivo(self) -> None:
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen de matrícula",
            initialdir=os.getcwd(),
            filetypes=[
                ("Imágenes", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp"),
                ("Todos los archivos", "*"),
            ],
        )
        if ruta:
            self.archivo_seleccionado.set(ruta)

    def _procesar_archivo(self) -> None:
        ruta = self.archivo_seleccionado.get()
        if not ruta or ruta == "Ningún archivo seleccionado":
            messagebox.showwarning(
                "Archivo no seleccionado",
                "Seleccione primero un archivo antes de procesar.",
            )
            return

        try:
            resultado = process_plate_image(ruta)
        except Exception as error:
            messagebox.showerror("Error de procesamiento", str(error))
            return

        try:
            carpeta_guardado = save_detection_result(resultado)
            print(f"Detección guardada en: {carpeta_guardado}")
        except Exception:
            pass

        self._mostrar_resultados(resultado)

    def _mostrar_resultados(self, resultado: DetectionResult) -> None:
        for child in self.result_container.winfo_children():
            child.destroy()

        # Crear carrusel
        self.carousel = ImageCarousel(
            self.result_container,
            resultado.etapas,
            IMAGE_CAROUSEL_WIDTH,
            IMAGE_CAROUSEL_HEIGHT
        )

        # Frame para el resumen y métricas
        text_frame = ttk.LabelFrame(
            self.result_container,
            text="Resumen y Métricas",
            padding=TEXT_FRAME_PADDING
        )
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Scrollbar y Text widget
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_box = tk.Text(
            text_frame,
            height=TEXT_BOX_HEIGHT,
            yscrollcommand=scrollbar.set,
            font=TEXT_FONT,
            bg=TEXT_BOX_BG,
            fg=TEXT_BOX_FG,
            relief=tk.FLAT,
            borderwidth=1,
            highlightcolor=ACCENT_COLOR,
            highlightthickness=1
        )
        text_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_box.yview)

        # Insertar el texto
        for linea in resultado.resumen_texto:
            text_box.insert(tk.END, linea + "\n")

        text_box.config(state=tk.DISABLED)

        # Botón para procesar otra placa
        button_frame = ttk.Frame(self.result_container)
        button_frame.pack(fill=tk.X, pady=TEXT_FRAME_PADY)

        volver_btn = ttk.Button(
            button_frame,
            text="🔄 Procesar otra placa",
            command=self._limpiar_resultados,
            width=25
        )
        volver_btn.pack(side=tk.RIGHT)

    def _limpiar_resultados(self) -> None:
        self.archivo_seleccionado.set("Ningún archivo seleccionado")
        for child in self.result_container.winfo_children():
            child.destroy()

    def run(self) -> None:
        self.root.mainloop()
