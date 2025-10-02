# app/schemas/working_api.py
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text
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
import base64
import requests

# ===== КОНФИГУРАЦИЯ =====
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
# Prefer DATABASE_URL from environment; fall back to local sqlite for dev
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tools.db")

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
"""
Create SQLAlchemy engine. For sqlite we must pass check_same_thread=False; for Postgres we should not.
"""
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)
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

class Engineer(Base):
    __tablename__ = "engineers"
    id = Column(Integer, primary_key=True, index=True)
    last_name = Column(String, index=True)
    first_name = Column(String, index=True)
    patronymic = Column(String, nullable=True)
    badge_id = Column(String, unique=True, index=True, nullable=True)

class Tool(Base):
    __tablename__ = "tools"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    sku = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)

class OperationItem(Base):
    __tablename__ = "operation_items"
    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(Integer, ForeignKey("operations.id"))
    tool_id = Column(Integer, ForeignKey("tools.id"), nullable=True)
    tool_name = Column(String, nullable=True)
    quantity = Column(Integer, default=1)

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

# Внешний ML сервис по HTTP (если задан)
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL")

def detect_with_external_ml(image_base64: str, confidence_threshold: float = 0.5) -> Dict[str, Any]:
    if not ML_SERVICE_URL:
        raise RuntimeError("ML_SERVICE_URL is not configured")
    try:
        resp = requests.post(
            f"{ML_SERVICE_URL}/detect",
            json={"image_base64": image_base64, "confidence_threshold": confidence_threshold},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"External ML call failed: {e}")
        raise

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

class EngineerCreate(BaseModel):
    last_name: str
    first_name: str
    patronymic: Optional[str] = None
    badge_id: Optional[str] = None

class EngineerUpdate(BaseModel):
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    patronymic: Optional[str] = None
    badge_id: Optional[str] = None

class EngineerResponse(BaseModel):
    id: int
    last_name: str
    first_name: str
    patronymic: Optional[str] = None
    badge_id: Optional[str] = None

    class Config:
        from_attributes = True

class ToolCreate(BaseModel):
    name: str
    sku: str
    description: Optional[str] = None

class ToolUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    description: Optional[str] = None

class ToolResponse(BaseModel):
    id: int
    name: str
    sku: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class OperationItemInput(BaseModel):
    tool_id: Optional[int] = None
    tool_name: Optional[str] = None
    quantity: int = 1

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
    if not ML_AVAILABLE and not ML_SERVICE_URL:
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
        
        # Внешний сервис имеет приоритет
        if ML_SERVICE_URL:
            return detect_with_external_ml(image_base64, confidence_threshold)

        # Внутренняя модель
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

@app.post("/api/ml/detect-upload")
async def detect_tools_upload(
    file: UploadFile = File(...),
    confidence_threshold: float = Form(0.5),
):
    """Загрузка изображения multipart/form-data и детекция инструментов"""
    try:
        content = await file.read()
        image_b64 = base64.b64encode(content).decode("utf-8")
        image_base64 = f"data:{file.content_type or 'image/jpeg'};base64,{image_b64}"

        if ML_SERVICE_URL:
            return detect_with_external_ml(image_base64, confidence_threshold)
        if not ML_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=ErrorResponse(
                    error_code=ERROR_CODES["ML_SERVICE_UNAVAILABLE"]["code"],
                    error_message=ERROR_CODES["ML_SERVICE_UNAVAILABLE"]["message"],
                    details="Нет доступного ML сервиса"
                ).dict()
            )
        results = detection_service.detect_tools(image_base64, confidence_threshold)
        return {
            "success": True,
            "results": results,
            "available_tools": detection_service.get_available_tools()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"detect-upload failed: {e}")
        raise HTTPException(status_code=500, detail="Image processing failed")

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

        # Save issued items if provided
        items: List[Dict[str, Any]] = operation_data.get('items', []) or []
        created_items = []
        for raw in items:
            tool_id = raw.get('tool_id')
            tool_name = raw.get('tool_name')
            quantity = int(raw.get('quantity', 1))
            oi = OperationItem(
                operation_id=operation.id,
                tool_id=tool_id,
                tool_name=tool_name,
                quantity=quantity,
            )
            db.add(oi)
            created_items.append(oi)
        if created_items:
            db.commit()
        
        print(f"✅ Operation started: {session_id}")
        
        return {
            "session_id": session_id,
            "operation_id": operation.id,
            "message": "Operation started successfully",
            "items_saved": len(created_items)
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
        accepted_tools_input: List[Dict[str, Any]] = confirm_data.get("accepted_tools", []) or []
        ml_used = False
        tools_data: List[Dict[str, Any]] = []
        
        if image_base64:
            if ML_SERVICE_URL:
                try:
                    ml_resp = detect_with_external_ml(image_base64)
                    if ml_resp.get("success"):
                        tools_data = ml_resp.get("results", {}).get("detected_tools", [])
                        ml_used = True
                    else:
                        raise HTTPException(status_code=500, detail="External ML returned error")
                except Exception as e:
                    logger.error(f"External ML detection failed: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="External ML service error"
                    )
            elif ML_AVAILABLE:
                try:
                    ml_results = detection_service.detect_tools(image_base64)
                    if ml_results["success"]:
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
        elif accepted_tools_input:
            # If tools provided manually
            tools_data = [
                {
                    "class_name": t.get("class_name") or t.get("name") or t.get("tool_name"),
                    "detected_quantity": int(t.get("quantity", 1)),
                    "confidence": 100.0,
                }
                for t in accepted_tools_input
            ]
        else:
            tools_data = []
            print("ℹ️ No tools provided for detection or manual acceptance")
        
        # Сравнение с последней выдачей инструментов для этого инженера
        engineer_name = operation.engineer_name
        last_checkout = db.query(Operation).filter(
            Operation.engineer_name == engineer_name,
            Operation.operation_type == 'checkout'
        ).order_by(Operation.timestamp.desc()).first()
        
        issued_map: Dict[str, int] = {}
        if last_checkout:
            issued_items = db.query(OperationItem).filter(OperationItem.operation_id == last_checkout.id).all()
            for it in issued_items:
                key = None
                if it.tool_id:
                    tool = db.query(Tool).get(it.tool_id)
                    key = tool.name if tool else it.tool_name
                else:
                    key = it.tool_name
                if not key:
                    continue
                issued_map[key] = issued_map.get(key, 0) + int(it.quantity or 1)
        
        accepted_map: Dict[str, int] = {}
        for td in tools_data:
            name = td.get("class_name") or td.get("name") or td.get("tool_name")
            qty = int(td.get("detected_quantity") or td.get("quantity") or 1)
            if not name:
                continue
            accepted_map[name] = accepted_map.get(name, 0) + qty
        
        missing: List[Dict[str, Any]] = []
        all_returned = True
        for name, qty in issued_map.items():
            accepted_qty = accepted_map.get(name, 0)
            if accepted_qty < qty:
                all_returned = False
                missing.append({"name": name, "issued": qty, "returned": accepted_qty, "missing": qty - accepted_qty})
        
        # Обновляем статус операции
        operation.status = "completed"
        db.commit()
        
        message = "Все инструменты сданы" if all_returned else "Обнаружены недосдачи"
        
        return {
            "message": message,
            "operation_id": operation.id,
            "engineer_name": engineer_name,
            "issued_summary": issued_map,
            "accepted_summary": accepted_map,
            "missing": missing,
            "total_missing": sum(m['missing'] for m in missing),
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

# ===== ENGINEERS CRUD =====
@app.post("/api/engineers", response_model=EngineerResponse)
async def create_engineer(payload: EngineerCreate, db: Session = Depends(get_db)):
    try:
        engineer = Engineer(
            last_name=payload.last_name,
            first_name=payload.first_name,
            patronymic=payload.patronymic,
            badge_id=payload.badge_id
        )
        db.add(engineer)
        db.commit()
        db.refresh(engineer)
        return engineer
    except Exception as e:
        logger.error(f"Database error in create_engineer: {e}")
        raise HTTPException(status_code=500, detail="Cannot create engineer")

@app.get("/api/engineers", response_model=List[EngineerResponse])
async def list_engineers(db: Session = Depends(get_db)):
    engineers = db.query(Engineer).order_by(Engineer.last_name, Engineer.first_name).all()
    return engineers

@app.get("/api/engineers/{engineer_id}", response_model=EngineerResponse)
async def get_engineer(engineer_id: int, db: Session = Depends(get_db)):
    engineer = db.query(Engineer).get(engineer_id)
    if not engineer:
        raise HTTPException(status_code=404, detail="Engineer not found")
    return engineer

@app.put("/api/engineers/{engineer_id}", response_model=EngineerResponse)
async def update_engineer(engineer_id: int, payload: EngineerUpdate, db: Session = Depends(get_db)):
    engineer = db.query(Engineer).get(engineer_id)
    if not engineer:
        raise HTTPException(status_code=404, detail="Engineer not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(engineer, field, value)
    db.commit()
    db.refresh(engineer)
    return engineer

@app.delete("/api/engineers/{engineer_id}")
async def delete_engineer(engineer_id: int, db: Session = Depends(get_db)):
    engineer = db.query(Engineer).get(engineer_id)
    if not engineer:
        raise HTTPException(status_code=404, detail="Engineer not found")
    db.delete(engineer)
    db.commit()
    return {"deleted": True}

# ===== TOOLS CRUD =====
@app.post("/api/tools", response_model=ToolResponse)
async def create_tool(payload: ToolCreate, db: Session = Depends(get_db)):
    try:
        tool = Tool(name=payload.name, sku=payload.sku, description=payload.description)
        db.add(tool)
        db.commit()
        db.refresh(tool)
        return tool
    except Exception as e:
        logger.error(f"Database error in create_tool: {e}")
        raise HTTPException(status_code=500, detail="Cannot create tool")

@app.get("/api/tools", response_model=List[ToolResponse])
async def list_tools(db: Session = Depends(get_db)):
    tools = db.query(Tool).order_by(Tool.name).all()
    return tools

@app.get("/api/tools/{tool_id}", response_model=ToolResponse)
async def get_tool(tool_id: int, db: Session = Depends(get_db)):
    tool = db.query(Tool).get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool

@app.put("/api/tools/{tool_id}", response_model=ToolResponse)
async def update_tool(tool_id: int, payload: ToolUpdate, db: Session = Depends(get_db)):
    tool = db.query(Tool).get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(tool, field, value)
    db.commit()
    db.refresh(tool)
    return tool

@app.delete("/api/tools/{tool_id}")
async def delete_tool(tool_id: int, db: Session = Depends(get_db)):
    tool = db.query(Tool).get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    db.delete(tool)
    db.commit()
    return {"deleted": True}

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