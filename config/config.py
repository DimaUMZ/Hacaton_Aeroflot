import os

class Config:
    PROJECT_ROOT = '/data/vscode/HacatonAeroflot/Aeroflot-project'
    DATASET_PATH = os.path.join(PROJECT_ROOT, 'yolo_dataset')
    MODEL_SAVE_DIR = os.path.join(PROJECT_ROOT, 'trained_models')
    PREDICTIONS_DIR = os.path.join(PROJECT_ROOT, 'predictions')
    UNLABELED_IMAGES_DIR = os.path.join(PROJECT_ROOT, 'unlabeled_images')
    
    CLASS_NAMES = [
        '1 Отвертка «-»',
        '10 Ключ рожковыйнакидной  ¾',
        '11 Бокорезы',
        '2 Отвертка «+»',
        '3 Отвертка на смещенный крест',
        '4 Коловорот',
        '5 Пассатижи контровочные',
        '6 Пассатижи',
        '7 Шэрница',
        '8 Разводной ключ',
        '9 Открывашка для банок с маслом'
    ]
    
    IMG_SIZE = 640
    BATCH_SIZE = 16
    EPOCHS = 100
    PATIENCE = 10

config = Config()