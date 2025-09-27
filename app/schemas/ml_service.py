# app/schemas/ml_service.py
import cv2
import numpy as np
from ultralytics import YOLO
import base64
from typing import List, Dict, Any
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ToolDetectionService:
    def __init__(self, model_path: str):
        """
        Инициализация сервиса детекции инструментов
        
        Args:
            model_path: Путь к файлу модели .pt или .onnx
        """
        try:
            self.model = YOLO(model_path)
            logger.info(f"✅ Модель загружена: {model_path}")
            
            # Классы инструментов из вашего датасета
            self.tool_classes = {
                0: "1 Отвертка «-»",
                1: "10 Ключ рожковыйнакидной ¾", 
                2: "11 Бокорезы",
                3: "2 Отвертка «+»",
                4: "3 Отвертка на смещенный крест",
                5: "4 Коловорот",
                6: "5 Пассатижи контровочные",
                7: "6 Пассатижи",
                8: "7 Шэрница",
                9: "8 Разводной ключ",
                10: "9 Открывашка для банок с маслом"
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки модели: {e}")
            raise

    def base64_to_image(self, image_base64: str) -> np.ndarray:
        """
        Конвертирует base64 строку в изображение OpenCV
        
        Args:
            image_base64: Изображение в формате base64
            
        Returns:
            Изображение в формате numpy array
        """
        try:
            # Убираем префикс если есть
            if ',' in image_base64:
                image_base64 = image_base64.split(',')[1]
                
            image_data = base64.b64decode(image_base64)
            np_array = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
            return image
        except Exception as e:
            logger.error(f"❌ Ошибка декодирования base64: {e}")
            raise

    def detect_tools(self, image_base64: str, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """
        Обнаружение инструментов на изображении
        
        Args:
            image_base64: Изображение в формате base64
            confidence_threshold: Порог уверенности (0.0-1.0)
            
        Returns:
            Словарь с результатами детекции
        """
        try:
            # Конвертируем base64 в изображение
            image = self.base64_to_image(image_base64)
            
            # Выполняем детекцию
            results = self.model(image, conf=confidence_threshold, verbose=False)
            
            # Обрабатываем результаты
            detected_tools = []
            total_detected = 0
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Получаем данные бокса
                        confidence = float(box.conf[0])
                        class_id = int(box.cls[0])
                        class_name = self.tool_classes.get(class_id, f"Unknown_{class_id}")
                        
                        # Координаты bounding box
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        detected_tools.append({
                            "class_name": class_name,
                            "confidence": confidence * 100,  # В процентах
                            "bounding_box": {
                                "x1": x1, "y1": y1, "x2": x2, "y2": y2
                            },
                            "detected_quantity": 1
                        })
                        
                        total_detected += 1
            
            # Группируем инструменты по классам для подсчета количества
            tool_counts = {}
            for tool in detected_tools:
                class_name = tool["class_name"]
                if class_name in tool_counts:
                    tool_counts[class_name] += 1
                else:
                    tool_counts[class_name] = 1
            
            # Обновляем detected_quantity для каждого инструмента
            for tool in detected_tools:
                tool["detected_quantity"] = tool_counts[tool["class_name"]]
            
            # Убираем дубликаты, оставляя только уникальные классы с правильным количеством
            unique_tools = []
            seen_classes = set()
            for tool in detected_tools:
                if tool["class_name"] not in seen_classes:
                    unique_tools.append(tool)
                    seen_classes.add(tool["class_name"])
            
            logger.info(f"🔍 Обнаружено инструментов: {total_detected}")
            
            return {
                "detected_tools": unique_tools,
                "total_detected": total_detected,
                "processing_time": results[0].speed.get('preprocess', 0) + 
                                  results[0].speed.get('inference', 0) + 
                                  results[0].speed.get('postprocess', 0),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка детекции: {e}")
            return {
                "detected_tools": [],
                "total_detected": 0,
                "processing_time": 0,
                "success": False,
                "error": str(e)
            }

    def get_available_tools(self) -> List[str]:
        """
        Возвращает список доступных для детекции инструментов
        
        Returns:
            Список названий инструментов
        """
        return list(self.tool_classes.values())

# Создаем глобальный экземпляр сервиса
# Укажите правильный путь к вашей модели
MODEL_PATH = "/data/vscode/HacatonAeroflot/Aeroflot-project/src/aeroflot_project/models/best_tools_detection.pt"

try:
    detection_service = ToolDetectionService(MODEL_PATH)
    logger.info("✅ Сервис детекции инструментов инициализирован")
except Exception as e:
    logger.error(f"❌ Не удалось инициализировать сервис детекции: {e}")
    detection_service = None