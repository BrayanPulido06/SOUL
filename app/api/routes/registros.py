from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.api.deps import get_db
from app.models.registro import Registro
from app.schemas.registro import (
    RegistroCreate,
    RegistroUpdate,
    RegistroResponse,
    ResponseModel,
    RegistrosListResponse
)
from app.config import ESTUDIOS_DISPONIBLES

router = APIRouter()

@router.get("/estudios", response_model=ResponseModel)
def obtener_estudios():
    """Obtener lista de estudios disponibles"""
    return {
        "success": True,
        "message": "Estudios obtenidos correctamente",
        "data": ESTUDIOS_DISPONIBLES
    }

@router.post("/registros", response_model=ResponseModel, status_code=201)
def crear_registro(registro: RegistroCreate, db: Session = Depends(get_db)):
    """Crear un nuevo registro"""
    
    # Validar que el estudio sea válido
    if registro.estudio not in ESTUDIOS_DISPONIBLES:
        raise HTTPException(
            status_code=400,
            detail=f"Estudio inválido. Debe ser uno de: {', '.join(ESTUDIOS_DISPONIBLES)}"
        )
    
    # Verificar si el email ya existe
    existing = db.query(Registro).filter(Registro.email == registro.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="El email ya está registrado"
        )
    
    # Crear nuevo registro
    db_registro = Registro(**registro.dict())
    
    db.add(db_registro)
    db.commit()
    db.refresh(db_registro)
    
    return {
        "success": True,
        "message": "Registro creado exitosamente",
        "data": RegistroResponse.from_orm(db_registro)
    }

@router.get("/registros", response_model=ResponseModel)
def obtener_registros(
    skip: int = 0,
    limit: int = 100,
    estudio: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Obtener lista de registros con filtros opcionales"""
    query = db.query(Registro)
    
    if estudio:
        query = query.filter(Registro.estudio == estudio)
    
    total = query.count()
    registros = query.offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "message": "Registros obtenidos correctamente",
        "data": {
            "registros": [RegistroResponse.from_orm(r) for r in registros],
            "total": total
        }
    }

@router.get("/registros/{registro_id}", response_model=ResponseModel)
def obtener_registro(registro_id: int, db: Session = Depends(get_db)):
    """Obtener un registro específico por ID"""
    registro = db.query(Registro).filter(Registro.id == registro_id).first()
    
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    return {
        "success": True,
        "message": "Registro obtenido correctamente",
        "data": RegistroResponse.from_orm(registro)
    }

@router.put("/registros/{registro_id}", response_model=ResponseModel)
def actualizar_registro(
    registro_id: int,
    registro_update: RegistroUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar un registro existente"""
    
    # Validar estudio
    if registro_update.estudio not in ESTUDIOS_DISPONIBLES:
        raise HTTPException(
            status_code=400,
            detail=f"Estudio inválido. Debe ser uno de: {', '.join(ESTUDIOS_DISPONIBLES)}"
        )
    
    registro = db.query(Registro).filter(Registro.id == registro_id).first()
    
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    # Verificar si el nuevo email ya existe en otro registro
    if registro_update.email != registro.email:
        existing = db.query(Registro).filter(
            Registro.email == registro_update.email,
            Registro.id != registro_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Actualizar campos
    for field, value in registro_update.dict().items():
        setattr(registro, field, value)
    
    db.commit()
    db.refresh(registro)
    
    return {
        "success": True,
        "message": "Registro actualizado exitosamente",
        "data": RegistroResponse.from_orm(registro)
    }

@router.delete("/registros/{registro_id}", response_model=ResponseModel)
def eliminar_registro(registro_id: int, db: Session = Depends(get_db)):
    """Eliminar un registro"""
    registro = db.query(Registro).filter(Registro.id == registro_id).first()
    
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    db.delete(registro)
    db.commit()
    
    return {
        "success": True,
        "message": "Registro eliminado exitosamente",
        "data": None
    }