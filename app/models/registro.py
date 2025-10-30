from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database.session import Base

class Registro(Base):
    __tablename__ = "registros"
    
    id = Column(Integer, primary_key=True, index=True)
    nombres = Column(String, nullable=False)
    apellidos = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    estudio = Column(String, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)