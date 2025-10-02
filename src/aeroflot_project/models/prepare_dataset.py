import os
import shutil
import argparse
import yaml
from typing import List
from sklearn.model_selection import train_test_split

def prepare_yolo_structure(dataset_path: str, output_path: str = 'yolo_dataset', val_ratio: float = 0.2, copy: bool = True) -> List[str]:
    # Получаем все папки
    all_folders = sorted([d for d in os.listdir(dataset_path) 
                         if os.path.isdir(os.path.join(dataset_path, d))])
    
    print(f"Найдено папок: {len(all_folders)}")
    print("Папки:", all_folders)
    
    # Создаем структуру папок
    for split in ['train', 'val']:
        os.makedirs(os.path.join(output_path, 'images', split), exist_ok=True)
        os.makedirs(os.path.join(output_path, 'labels', split), exist_ok=True)
    
    # Разделяем папки по типам
    tools_folders = [folder for folder in all_folders 
                    if 'групповые' not in folder.lower() 
                    and 'линейк' not in folder.lower()
                    and 'group' not in folder.lower()
                    and 'ruler' not in folder.lower()]

    group_folders = [folder for folder in all_folders 
                    if 'групповые' in folder.lower() 
                    or 'group' in folder.lower()]

    ruler_folders = [folder for folder in all_folders 
                    if 'линейк' in folder.lower() 
                    or 'ruler' in folder.lower()]
    
    print(f"Папки с инструментами: {len(tools_folders)}")
    print("Инструменты:", tools_folders)
    print(f"Групповые папки: {len(group_folders)}")
    print(f"Папки с линейкой: {len(ruler_folders)}")
    
    # Сохраняем классы инструментов
    classes_txt_path = os.path.join(output_path, 'classes.txt')
    with open(classes_txt_path, 'w') as f:
        for i, class_name in enumerate(tools_folders):
            f.write(f"{class_name}\n")
    
    # Обрабатываем отдельные инструменты
    process_single_tools(dataset_path, output_path, tools_folders, val_ratio=val_ratio, copy=copy)
    
    # Обрабатываем групповые фото (требуют специальной аннотации)
    process_group_photos(dataset_path, output_path, group_folders, copy=copy)
    
    # Обрабатываем фото с линейкой (как отдельные инструменты)
    process_ruler_photos(dataset_path, output_path, ruler_folders, copy=copy)

    # Write YOLO data.yaml
    data_yaml = {
        'path': os.path.abspath(output_path),
        'train': 'images/train',
        'val': 'images/val',
        'names': {i: name for i, name in enumerate(tools_folders)}
    }
    with open(os.path.join(output_path, 'data.yaml'), 'w', encoding='utf-8') as yf:
        yaml.safe_dump(data_yaml, yf, allow_unicode=True, sort_keys=False)

    print(f"\n✅ Wrote classes to: {classes_txt_path}")
    print(f"✅ Wrote YOLO data.yaml to: {os.path.join(output_path, 'data.yaml')}")
    return tools_folders

def process_single_tools(dataset_path: str, output_path: str, classes: List[str], val_ratio: float = 0.2, copy: bool = True):
    """Обрабатывает папки с отдельными инструментами"""
    print("\n=== Обработка отдельных инструментов ===")
    
    for class_idx, class_name in enumerate(classes):
        class_path = os.path.join(dataset_path, class_name)
        
        if not os.path.exists(class_path):
            print(f"Предупреждение: папка {class_path} не существует!")
            continue
            
        images = [f for f in os.listdir(class_path) 
                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff'))]
        
        print(f"{class_name}: {len(images)} изображений")
        
        if len(images) == 0:
            print(f"Предупреждение: в папке {class_name} нет изображений!")
            continue
        
        # Разделяем на train/val
        if len(images) == 1:
            train_imgs = images
            val_imgs = []
        else:
            train_imgs, val_imgs = train_test_split(images, test_size=val_ratio, random_state=42)
        
        print(f"  Train: {len(train_imgs)}, Val: {len(val_imgs)}")
        
        # Копируем изображения и создаем аннотации
        for split, img_list in [('train', train_imgs), ('val', val_imgs)]:
            for img_name in img_list:
                try:
                    # Копируем или линкуем изображение
                    src_img = os.path.join(class_path, img_name)
                    dst_img = os.path.join(output_path, 'images', split, img_name)
                    if copy:
                        shutil.copy2(src_img, dst_img)
                    else:
                        if not os.path.exists(dst_img):
                            os.symlink(src_img, dst_img)
                    
                    # Создаем YOLO аннотацию (объект занимает все изображение)
                    txt_name = os.path.splitext(img_name)[0] + '.txt'
                    with open(os.path.join(output_path, 'labels', split, txt_name), 'w') as f:
                        f.write(f"{class_idx} 0.5 0.5 1.0 1.0\n")
                        
                except Exception as e:
                    print(f"Ошибка при обработке {img_name}: {e}")

def process_group_photos(dataset_path: str, output_path: str, group_folders: List[str], copy: bool = True):
    """Обрабатывает групповые фотографии"""
    print("\n=== Обработка групповых фото ===")
    
    for group_folder in group_folders:
        group_path = os.path.join(dataset_path, group_folder)
        images = [f for f in os.listdir(group_path) 
                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff'))]
        
        print(f"{group_folder}: {len(images)} изображений")
        
        if len(images) == 0:
            print(f"Предупреждение: в папке {group_folder} нет изображений!")
            continue
        
        # Для групповых фото используем все изображения для тренировки
        # (требуют ручной аннотации bounding boxes)
        for img_name in images:
            try:
                # Копируем или линкуем изображение в train
                src_img = os.path.join(group_path, img_name)
                dst_img = os.path.join(output_path, 'images', 'train', img_name)
                if copy:
                    shutil.copy2(src_img, dst_img)
                else:
                    if not os.path.exists(dst_img):
                        os.symlink(src_img, dst_img)
                
                # Проверяем есть ли аннотация
                txt_name = os.path.splitext(img_name)[0] + '.txt'
                annotation_path = os.path.join(group_path, txt_name)
                
                if os.path.exists(annotation_path):
                    # Копируем существующую аннотацию
                    dst_txt = os.path.join(output_path, 'labels', 'train', txt_name)
                    shutil.copy2(annotation_path, dst_txt)
                    print(f"  Добавлена аннотация для {img_name}")
                else:
                    # Создаем пустую аннотацию (нужно будет аннотировать вручную)
                    dst_txt = os.path.join(output_path, 'labels', 'train', txt_name)
                    with open(dst_txt, 'w') as f:
                        # Пустой файл - нужно добавить bounding boxes вручную
                        pass
                    print(f"  Создана пустая аннотация для {img_name} (требует ручной разметки)")
                    
            except Exception as e:
                print(f"Ошибка при обработке группового фото {img_name}: {e}")

def process_ruler_photos(dataset_path: str, output_path: str, ruler_folders: List[str], copy: bool = True):
    """Обрабатывает фотографии с линейкой"""
    print("\n=== Обработка фото с линейкой ===")
    
    for ruler_folder in ruler_folders:
        ruler_path = os.path.join(dataset_path, ruler_folder)
        images = [f for f in os.listdir(ruler_path) 
                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff'))]
        
        print(f"{ruler_folder}: {len(images)} изображений")
        
        if len(images) == 0:
            print(f"Предупреждение: в папке {ruler_folder} нет изображений!")
            continue
        
        # Определяем класс инструмента по названию папки или изображения
        for img_name in images:
            try:
                # Пытаемся определить класс инструмента по имени файла
                tool_class_idx = None
                for i, tool_name in enumerate(ruler_folders):
                    if tool_name.lower() in img_name.lower():
                        tool_class_idx = i
                        break
                
                if tool_class_idx is None:
                    # Если не нашли по имени файла, используем первый класс
                    tool_class_idx = 0
                    print(f"  Предупреждение: не удалось определить класс для {img_name}, используется класс 0")
                
                # Копируем или линкуем изображение в train
                src_img = os.path.join(ruler_path, img_name)
                dst_img = os.path.join(output_path, 'images', 'train', img_name)
                if copy:
                    shutil.copy2(src_img, dst_img)
                else:
                    if not os.path.exists(dst_img):
                        os.symlink(src_img, dst_img)
                
                # Создаем аннотацию (инструмент занимает часть изображения)
                txt_name = os.path.splitext(img_name)[0] + '.txt'
                with open(os.path.join(output_path, 'labels', 'train', txt_name), 'w') as f:
                    # Примерные координаты (нужно настроить под ваши данные)
                    # Для фото с линейкой инструмент обычно занимает левую часть
                    f.write(f"{tool_class_idx} 0.3 0.5 0.5 0.8\n")
                
                print(f"  Добавлено фото с линейкой: {img_name} (класс: {ruler_folders[tool_class_idx]})")
                
            except Exception as e:
                print(f"Ошибка при обработке фото с линейкой {img_name}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Prepare YOLO dataset structure from raw folders')
    parser.add_argument('--dataset-path', type=str, default='datasets/raw', help='Path to raw dataset root')
    parser.add_argument('--output-path', type=str, default='yolo_dataset', help='Output YOLO dataset directory')
    parser.add_argument('--val-ratio', type=float, default=0.2, help='Validation split ratio for single tools')
    parser.add_argument('--no-copy', action='store_true', help='Use symlinks instead of copying files')
    args = parser.parse_args()

    dataset_path = args.dataset_path
    output_path = args.output_path
    
    # Проверяем существование пути
    if not os.path.exists(dataset_path):
        print(f"Ошибка: путь {dataset_path} не существует!")
        exit(1)
    
    prepare_yolo_structure(dataset_path, output_path, val_ratio=args.val_ratio, copy=(not args.no_copy))
    print("\n=== Подготовка данных завершена ===")