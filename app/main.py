from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.session import engine, Base
from app.api.routes import registros, excel
from app.config import ALLOWED_ORIGINS

# Crear tablas
Base.metadata.create_all(bind=engine)

# Inicializar FastAPI
app = FastAPI(
    title="Sistema de Registro API",
    description="API para gestión de registros de estudiantes con importación/exportación Excel",
    version="2.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(registros.router, prefix="/api", tags=["Registros"])
app.include_router(excel.router, prefix="/api", tags=["Excel"])

@app.get("/")
def root():
    return {
        "success": True,
        "message": "API de Sistema de Registro",
        "version": "2.0.0",
        "endpoints": {
            "docs": "/docs",
            "registros": "/api/registros",
            "estudios": "/api/estudios",
            "exportar": "/api/excel/exportar",
            "importar": "/api/excel/importar",
            "plantilla": "/api/excel/plantilla"
        }
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)