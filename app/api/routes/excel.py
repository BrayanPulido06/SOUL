from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
from datetime import datetime
from typing import List

from app.api.deps import get_db
from app.models.registro import Registro
from app.schemas.registro import RegistroResponse, ResponseModel
from app.utils.excel_handler import ExcelHandler
from app.config import UPLOADS_DIR, EXPORTS_DIR, MAX_FILE_SIZE, ALLOWED_EXTENSIONS

router = APIRouter()

@router.get("/excel/plantilla")
async def descargar_plantilla():
    """Descargar plantilla de Excel para importación"""
    try:
        filepath = ExcelHandler.create_template()
        
        return FileResponse(
            path=filepath,
            filename="plantilla_registros.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar plantilla: {str(e)}")

@router.get("/excel/exportar", response_model=None)
async def exportar_registros(
    estudio: str = None,
    db: Session = Depends(get_db)
):
    """Exportar todos los registros a Excel"""
    try:
        query = db.query(Registro)
        
        # Filtrar por estudio si se proporciona
        if estudio:
            query = query.filter(Registro.estudio == estudio)
        
        registros = query.all()
        
        if not registros:
            raise HTTPException(status_code=404, detail="No hay registros para exportar")
        
        # Convertir a diccionarios
        registros_data = []
        for registro in registros:
            registros_data.append({
                'id': registro.id,
                'nombres': registro.nombres,
                'apellidos': registro.apellidos,
                'email': registro.email,
                'estudio': registro.estudio,
                'fecha_registro': registro.fecha_registro
            })
        
        # Generar archivo Excel
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"registros_export_{timestamp}.xlsx"
        filepath = ExcelHandler.export_to_excel(registros_data, filename)
        
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al exportar registros: {str(e)}")

@router.post("/excel/importar", response_model=ResponseModel)
async def importar_registros(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Importar registros desde un archivo Excel"""
    
    # Validar extensión del archivo
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Use: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Validar tamaño del archivo
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Archivo muy grande. Tamaño máximo: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    # Guardar archivo temporalmente
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_filename = f"upload_{timestamp}_{file.filename}"
    temp_filepath = UPLOADS_DIR / temp_filename
    
    try:
        # Guardar archivo
        with temp_filepath.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Importar datos
        registros_validos, errores = ExcelHandler.import_from_excel(temp_filepath)
        
        # Procesar registros válidos
        registros_creados = []
        registros_duplicados = []
        errores_db = []
        
        for registro_data in registros_validos:
            try:
                # Verificar si el email ya existe
                existing = db.query(Registro).filter(
                    Registro.email == registro_data['email']
                ).first()
                
                if existing:
                    registros_duplicados.append(registro_data['email'])
                    continue
                
                # Crear registro
                nuevo_registro = Registro(**registro_data)
                db.add(nuevo_registro)
                db.flush()
                
                registros_creados.append(RegistroResponse.from_orm(nuevo_registro))
                
            except Exception as e:
                errores_db.append(f"Error al guardar {registro_data['email']}: {str(e)}")
        
        # Commit si hay registros creados
        if registros_creados:
            db.commit()
        
        # Preparar respuesta
        total_procesados = len(registros_validos)
        total_creados = len(registros_creados)
        total_duplicados = len(registros_duplicados)
        total_errores = len(errores) + len(errores_db)
        
        mensaje_partes = []
        
        if total_creados > 0:
            mensaje_partes.append(f"{total_creados} registro(s) importado(s) exitosamente")
        
        if total_duplicados > 0:
            mensaje_partes.append(f"{total_duplicados} registro(s) duplicado(s)")
        
        if total_errores > 0:
            mensaje_partes.append(f"{total_errores} error(es) encontrado(s)")
        
        mensaje = ". ".join(mensaje_partes) if mensaje_partes else "No se procesaron registros"
        
        return {
            "success": total_creados > 0,
            "message": mensaje,
            "data": {
                "registros_creados": registros_creados,
                "total_procesados": total_procesados,
                "total_creados": total_creados,
                "total_duplicados": total_duplicados,
                "emails_duplicados": registros_duplicados,
                "errores": errores + errores_db
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar archivo: {str(e)}")
    
    finally:
        # Limpiar archivo temporal
        if temp_filepath.exists():
            temp_filepath.unlink()