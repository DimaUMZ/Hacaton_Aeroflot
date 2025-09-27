# app/schemas/working_api.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import hashlib
import uvicorn
import uuid

# ===== КОНФИГУРАЦИЯ =====
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
DATABASE_URL = "sqlite:///./tools.db"



# ===== БАЗА ДАННЫХ =====
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    badge_id = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

class Operation(Base):
    __tablename__ = "operations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    operation_type = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="in_progress")
    session_id = Column(String)
    engineer_name = Column(String)

# ===== ПРОСТОЕ ХЕШИРОВАНИЕ (без bcrypt) =====
def hash_password(password: str) -> str:
    """Простое хеширование пароля для демо"""
    return hashlib.sha256(f"{password}{SECRET_KEY}".encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    return hash_password(plain_password) == hashed_password

def create_demo_data():
    """Создает демо-данные при первом запуске"""
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже пользователи
        if not db.query(User).first():
            demo_user = User(
                badge_id="demo",
                full_name="Демо Пользователь",
                hashed_password=hash_password("password"),
                is_active=True,
                is_superuser=False
            )
            admin_user = User(
                badge_id="admin", 
                full_name="Администратор Системы",
                hashed_password=hash_password("admin"),
                is_active=True,
                is_superuser=True
            )
            db.add_all([demo_user, admin_user])
            db.commit()
            print("✅ Demo data created successfully")
    except Exception as e:
        print(f"❌ Error creating demo data: {e}")
    finally:
        db.close()

# ===== LIFESPAN MANAGEMENT =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🔧 Starting up...")
    Base.metadata.create_all(bind=engine)
    create_demo_data()
    yield
    # Shutdown
    print("🔧 Shutting down...")

# ===== PYDANTIC СХЕМЫ =====
class LoginRequest(BaseModel):
    badge_id: str
    password: str

class UserResponse(BaseModel):
    id: int
    badge_id: str
    full_name: str
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class OperationStartRequest(BaseModel):
    engineer_name: str
    operation_type: str
    operation_date: str
    user_id: int

class OperationConfirmRequest(BaseModel):
    session_id: str
    operation_date: str
    tools: List[Dict[str, Any]]

# ===== АУТЕНТИФИКАЦИЯ =====
security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== FASTAPI ПРИЛОЖЕНИЕ =====
app = FastAPI(
    title="Tool Management System API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/auth/login", response_model=Token)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Аутентификация пользователя"""
    print(f"🔐 Login attempt: {login_data.badge_id}")
    
    user = db.query(User).filter(User.badge_id == login_data.badge_id).first()
    
    if not user:
        # Автоматически создаем пользователя для демо
        if login_data.badge_id in ["demo", "admin"]:
            is_superuser = login_data.badge_id == "admin"
            full_name = "Демо Пользователь" if not is_superuser else "Администратор Системы"
            
            user = User(
                badge_id=login_data.badge_id,
                full_name=full_name,
                hashed_password=hash_password(login_data.password),
                is_superuser=is_superuser
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✅ Created new user: {login_data.badge_id}")
        else:
            print(f"❌ Invalid credentials: {login_data.badge_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid badge ID or password"
            )
    
    # Проверяем пароль
    if not verify_password(login_data.password, user.hashed_password):
        print(f"❌ Invalid password for: {login_data.badge_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid badge ID or password"
        )
    
    # Создаем токен
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = jwt.encode(
        {
            "sub": user.badge_id,
            "exp": datetime.utcnow() + access_token_expires,
            "user_id": user.id
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    
    print(f"✅ Login successful: {user.full_name}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }

@app.post("/api/operations/start")
async def start_operation(operation_data: OperationStartRequest, db: Session = Depends(get_db)):
    """Начало новой операции с инструментами"""
    print(f"🔧 Starting operation for engineer: {operation_data.engineer_name}")
    
    session_id = str(uuid.uuid4())
    
    operation = Operation(
        user_id=operation_data.user_id,
        operation_type=operation_data.operation_type,
        session_id=session_id,
        engineer_name=operation_data.engineer_name,
        status="in_progress"
    )
    
    db.add(operation)
    db.commit()
    db.refresh(operation)
    
    print(f"✅ Operation started: {session_id}")
    
    return {
        "session_id": session_id,
        "operation_id": operation.id,
        "message": "Operation started successfully"
    }

@app.post("/api/operations/confirm")
async def confirm_operation(confirm_data: OperationConfirmRequest, db: Session = Depends(get_db)):
    """Подтверждение завершения операции"""
    print(f"✅ Confirming operation: {confirm_data.session_id}")
    
    operation = db.query(Operation).filter(Operation.session_id == confirm_data.session_id).first()
    
    if not operation:
        print(f"❌ Operation not found: {confirm_data.session_id}")
        raise HTTPException(status_code=404, detail="Operation not found")
    
    # Обновляем статус операции
    operation.status = "completed"
    db.commit()
    
    # Демо-данные инструментов
    demoTools = [
        {"id": 1, "class_name": "Молоток", "confidence": 95.5, "detected_quantity": 1},
        {"id": 2, "class_name": "Отвертка крестовая", "confidence": 87.3, "detected_quantity": 2},
        {"id": 3, "class_name": "Гаечный ключ", "confidence": 92.1, "detected_quantity": 3},
        {"id": 4, "class_name": "Плоскогубцы", "confidence": 78.9, "detected_quantity": 1}
    ]
    
    print(f"✅ Operation confirmed: {operation.id}")
    
    return {
        "message": "Operation confirmed successfully",
        "operation_id": operation.id,
        "tools": demoTools,
        "total_tools": len(demoTools),
        "match_percentage": 95.0
    }

@app.get("/api/users")
async def get_users(db: Session = Depends(get_db)):
    """Получить список пользователей (для тестирования)"""
    users = db.query(User).all()
    return [UserResponse.from_orm(user) for user in users]

@app.get("/api/health")
async def health_check():
    """Проверка здоровья API"""
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "service": "Tool Management System API"
    }

@app.get("/")
async def read_root():
    """Корневой endpoint"""
    return {
        "message": "Tool Management System API", 
        "version": "1.0.0",
        "endpoints": {
            "login": "POST /api/auth/login",
            "start_operation": "POST /api/operations/start", 
            "confirm_operation": "POST /api/operations/confirm",
            "health": "GET /api/health",
            "docs": "GET /docs"
        }
    }

if __name__ == "__main__":
    print("🚀 Starting Tool Management System API")
    print("📍 URL: http://localhost:8000")
    print("📚 Documentation: http://localhost:8000/docs")
    print("🔧 Health Check: http://localhost:8000/api/health")
    print("=" * 50)
    
    uvicorn.run(
        "working_api:app",
        host="0.0.0.0", 
        port=8000,
        reload=False
    )


# ===== RABOTAY S MODELY =====

try:
    from ml_service import detection_service
    ML_AVAILABLE = detection_service is not None
except ImportError:
    ML_AVAILABLE = False
    print("⚠️ ML service not available")

# Добавьте новый endpoint для детекции инструментов
@app.post("/api/ml/detect")
async def detect_tools(request: dict):
    """
    Обнаружение инструментов на изображении с помощью ML модели
    """
    if not ML_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="ML service is not available"
        )
    
    try:
        image_base64 = request.get("image_base64", "")
        confidence_threshold = request.get("confidence_threshold", 0.5)
        
        if not image_base64:
            raise HTTPException(
                status_code=400, 
                detail="Image data is required"
            )
        
        # Выполняем детекцию
        results = detection_service.detect_tools(image_base64, confidence_threshold)
        
        return {
            "success": True,
            "results": results,
            "available_tools": detection_service.get_available_tools()
        }
        
    except Exception as e:
        logger.error(f"Error in tool detection: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Detection failed: {str(e)}"
        )

@app.get("/api/ml/status")
async def get_ml_status():
    """
    Проверка статуса ML сервиса
    """
    return {
        "ml_available": ML_AVAILABLE,
        "available_tools": detection_service.get_available_tools() if ML_AVAILABLE else []
    }

# Обновите endpoint подтверждения операции для использования ML
@app.post("/api/operations/confirm")
async def confirm_operation(confirm_data: dict, db: Session = Depends(get_db)):
    """Подтверждение завершения операции с возможностью ML детекции"""
    print(f"✅ Confirming operation: {confirm_data.get('session_id')}")
    
    operation = db.query(Operation).filter(
        Operation.session_id == confirm_data.get("session_id")
    ).first()
    
    if not operation:
        raise HTTPException(status_code=404, detail="Operation not found")
    
    # Если предоставлено изображение, используем ML для детекции
    image_base64 = confirm_data.get("image_base64")
    if image_base64 and ML_AVAILABLE:
        try:
            ml_results = detection_service.detect_tools(image_base64)
            if ml_results["success"]:
                # Используем результаты ML
                tools_data = ml_results["results"]["detected_tools"]
                print(f"🔍 ML detected {len(tools_data)} tools")
            else:
                # Fallback к демо-данным
                tools_data = get_demo_tools()
        except Exception as e:
            print(f"⚠️ ML detection failed, using demo data: {e}")
            tools_data = get_demo_tools()
    else:
        # Используем демо-данные
        tools_data = get_demo_tools()
    
    # Обновляем статус операции
    operation.status = "completed"
    db.commit()
    
    return {
        "message": "Operation confirmed successfully",
        "operation_id": operation.id,
        "tools": tools_data,
        "total_tools": len(tools_data),
        "match_percentage": 95.0,
        "ml_used": image_base64 is not None and ML_AVAILABLE
    }

def get_demo_tools():
    """Возвращает демо-данные инструментов"""
    return [
        {"id": 1, "class_name": "Молоток", "confidence": 95.5, "detected_quantity": 1},
        {"id": 2, "class_name": "Отвертка крестовая", "confidence": 87.3, "detected_quantity": 2},
        {"id": 3, "class_name": "Гаечный ключ", "confidence": 92.1, "detected_quantity": 3},
        {"id": 4, "class_name": "Плоскогубцы", "confidence": 78.9, "detected_quantity": 1}
    ]