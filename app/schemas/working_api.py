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
import logging
import os

# ===== КОНФИГУРАЦИЯ =====
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
DATABASE_URL = "sqlite:///./tools.db"

# Коды ошибок
ERROR_CODES = {
    "ML_SERVICE_UNAVAILABLE": {
        "code": "API_ERR_001",
        "message": "ML сервис недоступен. Проверьте запуск сервиса компьютерного зрения."
    },
    "IMAGE_PROCESSING_ERROR": {
        "code": "API_ERR_002", 
        "message": "Ошибка обработки изображения. Проверьте корректность данных изображения."
    },
    "DETECTION_SERVICE_ERROR": {
        "code": "API_ERR_003",
        "message": "Ошибка сервиса распознавания. Не удалось выполнить детекцию инструментов."
    },
    "OPERATION_NOT_FOUND": {
        "code": "API_ERR_004",
        "message": "Операция не найдена. Проверьте корректность session_id."
    },
    "INVALID_IMAGE_DATA": {
        "code": "API_ERR_005",
        "message": "Неверные данные изображения. Изображение отсутствует или имеет неверный формат."
    },
    "DATABASE_ERROR": {
        "code": "API_ERR_006",
        "message": "Ошибка базы данных. Не удалось выполнить операцию с базой данных."
    }
}

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# ===== ML СЕРВИС =====
try:
    from ml_service import detection_service
    ML_AVAILABLE = detection_service is not None
    print("✅ ML сервис доступен")
except ImportError as e:
    print(f"⚠️ ML сервис недоступен: {e}")
    ML_AVAILABLE = False
except Exception as e:
    print(f"⚠️ Ошибка загрузки ML сервиса: {e}")
    ML_AVAILABLE = False

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def hash_password(password: str) -> str:
    """Простое хеширование пароля для демо"""
    return hashlib.sha256(f"{password}{SECRET_KEY}".encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    return hash_password(plain_password) == hashed_password

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_demo_data():
    """Создает демо-данные при первом запуске"""
    db = SessionLocal()
    try:
        if not db.query(User).first():
            demo_user = User(
                badge_id="demo",
                full_name="Иванов Иван Иванович",
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

class ErrorResponse(BaseModel):
    error_code: str
    error_message: str
    details: Optional[str] = None

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

@app.get("/")
async def read_root():
    return {
        "message": "Tool Management System API", 
        "version": "1.0.0",
        "ml_available": ML_AVAILABLE
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "service": "Tool Management System API",
        "ml_available": ML_AVAILABLE
    }

@app.get("/api/ml/status")
async def get_ml_status():
    """Проверка статуса ML сервиса"""
    if ML_AVAILABLE:
        return {
            "ml_available": True,
            "available_tools": detection_service.get_available_tools(),
            "message": "ML сервис готов к работе"
        }
    else:
        return {
            "ml_available": False,
            "available_tools": [],
            "message": "ML сервис недоступен"
        }

@app.post("/api/ml/detect")
async def detect_tools(request: dict):
    """Обнаружение инструментов на изображении с помощью ML модели"""
    if not ML_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error_code=ERROR_CODES["ML_SERVICE_UNAVAILABLE"]["code"],
                error_message=ERROR_CODES["ML_SERVICE_UNAVAILABLE"]["message"],
                details="ML сервис не запущен или недоступен"
            ).dict()
        )
    
    try:
        image_base64 = request.get("image_base64", "")
        confidence_threshold = request.get("confidence_threshold", 0.5)
        
        if not image_base64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ERROR_CODES["INVALID_IMAGE_DATA"]["code"],
                    error_message=ERROR_CODES["INVALID_IMAGE_DATA"]["message"],
                    details="Поле image_base64 не может быть пустым"
                ).dict()
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ERROR_CODES["DETECTION_SERVICE_ERROR"]["code"],
                error_message=ERROR_CODES["DETECTION_SERVICE_ERROR"]["message"],
                details=f"Ошибка при обработке изображения: {str(e)}"
            ).dict()
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
            full_name = "Иванов Иван Иванович" if not is_superuser else "Администратор Системы"
            
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

@app.get("/api/auth/me")
async def get_current_user(token: str = Depends(HTTPBearer())):
    """Получение информации о текущем пользователе"""
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        badge_id = payload.get("sub")
        
        db = SessionLocal()
        user = db.query(User).filter(User.badge_id == badge_id).first()
        db.close()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse.from_orm(user)
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/operations/start")
async def start_operation(operation_data: dict, db: Session = Depends(get_db)):
    """Начало новой операции с инструментами"""
    print(f"🔧 Starting operation for engineer: {operation_data.get('engineer_name')}")
    
    try:
        session_id = str(uuid.uuid4())
        
        operation = Operation(
            user_id=operation_data.get('user_id', 1),
            operation_type=operation_data.get('operation_type', 'checkout'),
            session_id=session_id,
            engineer_name=operation_data.get('engineer_name', ''),
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
    except Exception as e:
        logger.error(f"Database error in start_operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ERROR_CODES["DATABASE_ERROR"]["code"],
                error_message=ERROR_CODES["DATABASE_ERROR"]["message"],
                details=f"Не удалось создать операцию: {str(e)}"
            ).dict()
        )

@app.post("/api/operations/confirm")
async def confirm_operation(confirm_data: dict, db: Session = Depends(get_db)):
    """Подтверждение завершения операции с возможностью ML детекции"""
    print(f"✅ Confirming operation: {confirm_data.get('session_id')}")
    
    try:
        operation = db.query(Operation).filter(
            Operation.session_id == confirm_data.get("session_id")
        ).first()
        
        if not operation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ERROR_CODES["OPERATION_NOT_FOUND"]["code"],
                    error_message=ERROR_CODES["OPERATION_NOT_FOUND"]["message"],
                    details=f"Операция с session_id {confirm_data.get('session_id')} не найдена"
                ).dict()
            )
        
        # Если предоставлено изображение, используем ML для детекции
        image_base64 = confirm_data.get("image_base64")
        ml_used = False
        tools_data = []
        
        if image_base64:
            if ML_AVAILABLE:
                try:
                    ml_results = detection_service.detect_tools(image_base64)
                    if ml_results["success"]:
                        # Используем результаты ML
                        tools_data = ml_results["results"]["detected_tools"]
                        ml_used = True
                        print(f"🔍 ML detected {len(tools_data)} tools")
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=ErrorResponse(
                                error_code=ERROR_CODES["DETECTION_SERVICE_ERROR"]["code"],
                                error_message=ERROR_CODES["DETECTION_SERVICE_ERROR"]["message"],
                                details="ML сервис вернул ошибку при детекции"
                            ).dict()
                        )
                except Exception as e:
                    logger.error(f"ML detection failed: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=ErrorResponse(
                            error_code=ERROR_CODES["DETECTION_SERVICE_ERROR"]["code"],
                            error_message=ERROR_CODES["DETECTION_SERVICE_ERROR"]["message"],
                            details=f"Ошибка ML детекции: {str(e)}"
                        ).dict()
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=ErrorResponse(
                        error_code=ERROR_CODES["ML_SERVICE_UNAVAILABLE"]["code"],
                        error_message=ERROR_CODES["ML_SERVICE_UNAVAILABLE"]["message"],
                        details="Необходимо изображение для детекции, но ML сервис недоступен"
                    ).dict()
                )
        else:
            # Если изображение не предоставлено, возвращаем пустой список инструментов
            tools_data = []
            print("ℹ️ No image provided for detection")
        
        # Обновляем статус операции
        operation.status = "completed"
        db.commit()
        
        return {
            "message": "Operation confirmed successfully",
            "operation_id": operation.id,
            "tools": tools_data,
            "total_tools": len(tools_data),
            "match_percentage": 95.0 if tools_data else 0,
            "ml_used": ml_used
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error in confirm_operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ERROR_CODES["DATABASE_ERROR"]["code"],
                error_message=ERROR_CODES["DATABASE_ERROR"]["message"],
                details=f"Ошибка при подтверждении операции: {str(e)}"
            ).dict()
        )

@app.get("/api/users")
async def get_users(db: Session = Depends(get_db)):
    """Получить список пользователей (для тестирования)"""
    try:
        users = db.query(User).all()
        return [UserResponse.from_orm(user) for user in users]
    except Exception as e:
        logger.error(f"Database error in get_users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ERROR_CODES["DATABASE_ERROR"]["code"],
                error_message=ERROR_CODES["DATABASE_ERROR"]["message"],
                details=f"Ошибка при получении списка пользователей: {str(e)}"
            ).dict()
        )

if __name__ == "__main__":
    print("🚀 Starting Tool Management System API")
    print("📍 URL: http://localhost:8001")
    print("📚 Documentation: http://localhost:8001/docs")
    print("🔧 Health Check: http://localhost:8001/api/health")
    print(f"🤖 ML Service: {'✅ Available' if ML_AVAILABLE else '❌ Not available'}")
    print("=" * 50)
    
    uvicorn.run(
        app,
        host="0.0.0.0", 
        port=8001,
        reload=False
    )