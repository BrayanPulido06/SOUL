from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
from datetime import datetime
from typing import List, Optional

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
            filename="plantilla_registros_sena.xlsx",
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
        
        if estudio:
            query = query.filter(Registro.estudio == estudio)
        
        registros = query.all()
        
        if not registros:
            raise HTTPException(status_code=404, detail="No hay registros para exportar")
        
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
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"registros_sena_{timestamp}.xlsx"
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
    sheet_names: Optional[str] = None,  # Nombres de hojas separados por coma
    db: Session = Depends(get_db)
):
    """
    Importar registros desde un archivo Excel
    Puede procesar múltiples hojas si se especifica sheet_names
    """
    
    # Validar extensión
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Use: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Validar tamaño
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
        
        # Procesar hojas especificadas o todas
        sheets_to_process = None
        if sheet_names:
            sheets_to_process = [s.strip() for s in sheet_names.split(',')]
        
        # Importar desde múltiples hojas
        results_by_sheet = ExcelHandler.import_from_excel_multiple_sheets(
            temp_filepath,
            sheets_to_process
        )
        
        # Procesar todos los registros de todas las hojas
        total_registros_creados = []
        total_registros_duplicados = []
        total_errores = []
        sheets_processed = {}
        
        for sheet_name, (registros_validos, errores) in results_by_sheet.items():
            registros_creados_hoja = []
            duplicados_hoja = []
            errores_db_hoja = []
            
            for registro_data in registros_validos:
                try:
                    # Verificar duplicado
                    existing = db.query(Registro).filter(
                        Registro.email == registro_data['email']
                    ).first()
                    
                    if existing:
                        duplicados_hoja.append(registro_data['email'])
                        continue
                    
                    # Crear registro
                    nuevo_registro = Registro(**registro_data)
                    db.add(nuevo_registro)
                    db.flush()
                    
                    registros_creados_hoja.append(RegistroResponse.from_orm(nuevo_registro))
                    
                except Exception as e:
                    errores_db_hoja.append(f"{registro_data['email']}: {str(e)}")
            
            # Guardar estadísticas por hoja
            sheets_processed[sheet_name] = {
                "procesados": len(registros_validos),
                "creados": len(registros_creados_hoja),
                "duplicados": len(duplicados_hoja),
                "errores": len(errores) + len(errores_db_hoja)
            }
            
            total_registros_creados.extend(registros_creados_hoja)
            total_registros_duplicados.extend(duplicados_hoja)
            total_errores.extend(errores)
            total_errores.extend(errores_db_hoja)
        
        # Commit si hay registros creados
        if total_registros_creados:
            db.commit()
        
        # Preparar mensaje
        total_creados = len(total_registros_creados)
        total_duplicados = len(total_registros_duplicados)
        total_err = len(total_errores)
        
        mensaje_partes = []
        if total_creados > 0:
            mensaje_partes.append(f"{total_creados} registro(s) importado(s)")
        if total_duplicados > 0:
            mensaje_partes.append(f"{total_duplicados} duplicado(s)")
        if total_err > 0:
            mensaje_partes.append(f"{total_err} error(es)")
        
        mensaje = ". ".join(mensaje_partes) if mensaje_partes else "No se procesaron registros"
        
        return {
            "success": total_creados > 0,
            "message": mensaje,
            "data": {
                "registros_creados": total_registros_creados,
                "total_creados": total_creados,
                "total_duplicados": total_duplicados,
                "emails_duplicados": total_registros_duplicados,
                "errores": total_errores[:10],  # Solo primeros 10 errores
                "total_errores": total_err,
                "hojas_procesadas": sheets_processed
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar archivo: {str(e)}")
    
    finally:
        # Limpiar archivo temporal
        if temp_filepath.exists():
            temp_filepath.unlink()