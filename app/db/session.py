from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True) # Уникальный идентификатор пользователя
    badge_id = Column(String, unique=True, index=True, nullable=False) # ID бейджа сотрудника (уникальный)
    full_name = Column(String, nullable=False) # Полное имя пользователя
    hashed_password = Column(String, nullable=False) # Хэшированный пароль для аутентификации
    is_active = Column(Boolean, default=True) # Флаг активности учетной записи
    is_superuser = Column(Boolean, default=False) # Флаг администратора системы

    operations = relationship("Operation", back_populates="user") # Все операции пользователя
    audit_logs = relationship("AuditLog", back_populates="user") # Записи аудита для пользователя

class Tool(Base):
    __tablename__ = "tools"
    
    id = Column(Integer, primary_key=True, index=True) # Уникальный идентификатор инструмента
    name = Column(String, nullable=False) # Название инструмента (например, "Отвертка +")
    description = Column(String) # Описание инструмента
    is_active = Column(Boolean, default=True) # Флаг активности инструмента (для мягкого удаления)

    toolkit_associations = relationship("ToolkitTool", back_populates="tool") # Связи с наборами инструментов
    operation_details = relationship("OperationDetail", back_populates="tool") # Детали операций с этим инструментом

class Toolkit(Base):
    __tablename__ = "toolkits"

    id = Column(Integer, primary_key=True, index=True) # Уникальный идентификатор набора инструментов
    name = Column(String, unique=True, index=True, nullable=False) # Название набора (уникальное), например "Набор для RRJ"
    description = Column(String) # Описание набора инструментов
    is_active = Column(Boolean, default=True) # Флаг активности набора
    min_match_threshold = Column(Float, default=95.0) # Минимальный порог совпадения для автоматического подтверждения (%)

    tools = relationship("ToolkitTool", back_populates="toolkit") # Инструменты в этом наборе
    operations = relationship("Operation", back_populates="toolkit") # Операции с этим набором

class ToolkitTool(Base):
    __tablename__ = "toolkit_tools"
    
    id = Column(Integer, primary_key=True) # Уникальный идентификатор связи
    toolkit_id = Column(Integer, ForeignKey("toolkits.id")) # Ссылка на набор инструментов
    tool_id = Column(Integer, ForeignKey("tools.id")) # Ссылка на инструмент
    quantity = Column(Integer, default=1) # Количество данного инструмента в наборе

    toolkit = relationship("Toolkit", back_populates="tools") # Набор, к которому принадлежит инструмент
    tool = relationship("Tool", back_populates="toolkit_associations") # Инструмент в наборе


class Operation(Base):
    __tablename__ = "operations"

    id = Column(Integer, primary_key=True, index=True) # Уникальный идентификатор операции
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Ссылка на пользователя, выполнившего операцию
    toolkit_id = Column(Integer, ForeignKey("toolkits.id"), nullable=False) # Ссылка на используемый набор инструментов
    operation_type = Column(String, nullable=False) # Тип операции: "checkout" (выдача) или "checkin" (сдача)
    timestamp = Column(DateTime(timezone=True), server_default=func.now()) # Временная метка операции
    
    # Результаты автоматического подсчета
    total_expected = Column(Integer) # Общее количество инструментов, которое должно быть в наборе
    total_detected = Column(Integer) # Общее количество инструментов, распознанных системой
    match_percentage = Column(Float) # Процент совпадения между ожидаемым и распознанным количеством
    
    # Статус операции
    status = Column(String) # Статус: "success", "discrepancy", "manual_check", "in_progress"
    requires_manual_check = Column(Boolean, default=False) # Требуется ли ручная проверка 
    
    # Ссылки и метаданные
    related_operation_id = Column(Integer, ForeignKey("operations.id")) # Ссылка на связанную операцию (выдача -> сдача)
    camera_id = Column(String) # Идентификатор камеры, использованной для распознавания
    session_id = Column(String) # Уникальный идентификатор сессии для связи операций
    
    user = relationship("User", back_populates="operations") # Пользователь, выполнивший операцию
    toolkit = relationship("Toolkit", back_populates="operations") # Набор инструментов
    details = relationship("OperationDetail", back_populates="operation") # Детали по каждому инструменту в операции
    related_operation = relationship("Operation", remote_side=[id]) # Связанная операция (рекурсивная связь)

class OperationDetail(Base):
    __tablename__ = "operation_details"
    
    id = Column(Integer, primary_key=True) # Уникальный идентификатор детали операции
    operation_id = Column(Integer, ForeignKey("operations.id")) # Ссылка на родительскую операцию
    tool_id = Column(Integer, ForeignKey("tools.id")) # Ссылка на конкретный инструмент
    expected_quantity = Column(Integer, default=1) # Ожидаемое количество данного инструмента
    detected_quantity = Column(Integer, default=0) # Распознанное количество данного инструмента
    confidence = Column(Float) # Уровень уверенности распознавания для этого инструмента (0-100%)
    
    operation = relationship("Operation", back_populates="details") # Родительская операция
    tool = relationship("Tool", back_populates="operation_details") # Инструмент


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True) # Уникальный идентификатор записи аудита
    user_id = Column(Integer, ForeignKey("users.id")) # Пользователь, выполнивший действие (может быть NULL для системных действий)
    action = Column(String, nullable=False) # Тип действия: "create", "update", "delete", "login", etc.
    table_name = Column(String, nullable=False) # Название таблицы, в которой произошли изменения
    record_id = Column(Integer, nullable=False) # ID записи, которую изменили
    old_values = Column(JSON) # Значения до изменения (для отслеживания изменений)
    new_values = Column(JSON) # Значения после изменения
    timestamp = Column(DateTime(timezone=True), server_default=func.now()) # Временная метка действия
    
    user = relationship("User", back_populates="audit_logs") # Пользователь, выполнивший действие

# Индексы для улучшения производительности запросов
indexes = [
    Index('ix_operations_user_timestamp', Operation.user_id, Operation.timestamp), # Быстрый поиск операций по пользователю и времени
    Index('ix_operations_status_timestamp', Operation.status, Operation.timestamp), # Быстрый поиск операций по статусу и времени
    Index('ix_operations_session_id', Operation.session_id), # Быстрый поиск операций по идентификатору сессии
    Index('ix_operation_details_operation_id', OperationDetail.operation_id), # Быстрый поиск деталей операций по операции
    Index('ix_audit_logs_timestamp', AuditLog.timestamp), # Быстрый поиск записей аудита по времени
    Index('ix_toolkit_tools_toolkit_id', ToolkitTool.toolkit_id), # Быстрый поиск инструментов в наборах по набору
    Index('ix_toolkit_tools_tool_id', ToolkitTool.tool_id), # Быстрый поиск инструментов в наборах по инструменту
]