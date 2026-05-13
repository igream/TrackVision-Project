import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, LargeBinary, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    
    detections = relationship("Detection", back_populates="user")


class Detection(Base):
    __tablename__ = 'detections'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    mode = Column(String(50))  # 'detect' or 'ocr'
    plate_text = Column(String(100))
    confidence = Column(Float)
    original_filename = Column(String(255))
    saved_dir = Column(String(255))
    summary_text = Column(Text)
    original_image_blob = Column(LargeBinary, nullable=True) # Para almacenar la imagen en la base de datos
    
    user = relationship("User", back_populates="detections")
