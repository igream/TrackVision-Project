from pathlib import Path


# Frontend Configuration
# GUI and UI settings for desktop, mobile, and web deployment
BASE_DIR = Path(__file__).resolve().parent.parent

# Color scheme: Royal Blue (#003366) and White (#FFFFFF)
PRIMARY_COLOR = "#003366"  # Royal Blue
SECONDARY_COLOR = "#004C99"  # Light Royal Blue
ACCENT_COLOR = "#0066CC"  # Bright Royal Blue
WHITE = "#FFFFFF"
LIGHT_GRAY = "#F5F5F5"
DARK_GRAY = "#333333"
BORDER_COLOR = "#CCCCCC"
SUCCESS_COLOR = "#28A745"
ERROR_COLOR = "#DC3545"

# Logo settings
LOGO_PATH = str(BASE_DIR / "src" / "LogoInApp.PNG")
LOGO_SIZE = (80, 80)

# Window settings
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800
WINDOW_MIN_WIDTH = 500
WINDOW_MIN_HEIGHT = 600
WINDOW_BG_COLOR = WHITE

# Font settings
TITLE_FONT = ("Segoe UI", 16, "bold")
SUBTITLE_FONT = ("Segoe UI", 12, "bold")
LABEL_FONT = ("Segoe UI", 10, "bold")
NORMAL_FONT = ("Segoe UI", 10)
SMALL_FONT = ("Segoe UI", 9)
TEXT_FONT = ("Courier New", 9)

# Image carousel settings
IMAGE_CAROUSEL_WIDTH = 600
IMAGE_CAROUSEL_HEIGHT = 400
IMAGE_CAROUSEL_BG = LIGHT_GRAY
CAROUSEL_BUTTON_SIZE = 30
CAROUSEL_DOT_SIZE = 8

# Image display settings
IMAGE_CELL_WIDTH = 280
IMAGE_CELL_HEIGHT = 200
IMAGE_GRID_COLS = 2
IMAGE_PADDING_X = 10
IMAGE_PADDING_Y = 10

# Text box settings
TEXT_BOX_HEIGHT = 12
TEXT_BOX_BG = WHITE
TEXT_BOX_FG = DARK_GRAY
TEXT_BOX_BORDER = BORDER_COLOR

# Button settings
BUTTON_PADDING_X = 10
BUTTON_PADDING_Y = 8
BUTTON_WIDTH = 150
BUTTON_BG = PRIMARY_COLOR
BUTTON_FG = WHITE

# Label wrapping
RUTA_LABEL_WRAPLENGTH = 700

# Frame padding
MAIN_FRAME_PADDING = 20
RESULT_FRAME_PADDING = 15
TEXT_FRAME_PADDING = 15
LOGO_FRAME_PADDING = 10

# Spacing
TITLE_PADY = (10, 20)
RUTA_PADY = (0, 15)
IMG_FRAME_PADY = (0, 15)
RESULT_PADY = (15, 0)
TEXT_FRAME_PADY = (10, 0)
BUTTON_PADY = 10

# Border radius simulation (via relief)
RELIEF_STYLE = "flat"
BORDER_WIDTH = 0
