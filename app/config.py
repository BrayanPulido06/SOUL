import os
from pathlib import Path

# Directorios base
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
EXPORTS_DIR = BASE_DIR / "exports"

# Crear directorios si no existen
UPLOADS_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

# Configuración de base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/registros_db")

# Estudios disponibles (ACTUALIZADO para coincidir con frontend)
ESTUDIOS_DISPONIBLES = [
    'Desarrollo Web',
    'Desarrollo Móvil',
    'Bases de Datos',
    'Redes y Seguridad',
    'Diseño Gráfico',
    'Marketing Digital',
    'Administración de Empresas',
    'Contabilidad',
    'Electricidad',
    'Sistemas'
]

# Configuración de CORS
ALLOWED_ORIGINS = [
    "http://localhost:4200",
    "http://localhost",
    "http://localhost:3000"
]

# Configuración de archivos
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {'.xlsx', '.xls'}