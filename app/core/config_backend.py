import os
from pathlib import Path


# Backend Configuration
# OCR and storage settings
BASE_DIR = Path(__file__).resolve().parent.parent

SAVE_BASE_DIR = os.getenv("OCR_SAVE_BASE_DIR", str(BASE_DIR / "Detecciones"))
VALID_THRESHOLD = 0.80

# Web server settings
WEB_HOST = os.getenv("OCR_WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("OCR_WEB_PORT", "8000"))

# Session settings
SESSION_COOKIE_NAME = "session"
SESSION_MAX_AGE_SECONDS = int(os.getenv("OCR_SESSION_MAX_AGE_SECONDS", str(30 * 24 * 60 * 60)))
SESSION_SECRET = os.getenv("OCR_SESSION_SECRET", "ocr-placas-dev-session-secret-change-me")
SESSION_SECURE_COOKIE = os.getenv("OCR_SESSION_SECURE", "false").lower() in {"1", "true", "yes", "on"}

# PaddleOCR settings
OCR_LANG = "en"
OCR_USE_ANGLE_CLS = True
OCR_ENABLE_MKLDNN = False
OCR_DEVICE = "cpu"

# Image processing settings
CANNY_THRESHOLD_LOW = 30
CANNY_THRESHOLD_HIGH = 200
BILATERAL_FILTER_SIZE = 11
BILATERAL_FILTER_SIGMA_COLOR = 17
BILATERAL_FILTER_SIGMA_SPACE = 17
APPROX_CONTOUR_EPSILON = 0.018

# Padding settings
BORDER_PADDING = 15
BORDER_TYPE = "reflect"

# Contour settings
MAX_CONTOURS_TO_CHECK = 10
REQUIRED_POLYGON_POINTS = 4
