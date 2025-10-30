from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, Any, List

class RegistroBase(BaseModel):
    nombres: str = Field(..., min_length=1, max_length=100)
    apellidos: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    estudio: str

class RegistroCreate(RegistroBase):
    pass

class RegistroUpdate(RegistroBase):
    pass

class RegistroResponse(RegistroBase):
    id: int
    fecha_registro: datetime
    
    class Config:
        from_attributes = True

class ResponseModel(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

class RegistrosListResponse(BaseModel):
    registros: List[RegistroResponse]
    total: int