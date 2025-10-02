# fix_label_classes.py
from pathlib import Path

def fix_label_classes():
    data_dir = Path('../yolo_dataset')
    labels_dirs = [
        data_dir / 'labels',
        data_dir / 'pseudo_labeled' / 'labels'
    ]
    
    num_classes = 12  # У вас 12 классов (0-11)
    fixed_count = 0
    error_count = 0
    
    for labels_dir in labels_dirs:
        if not labels_dir.exists():
            print(f"Labels directory not found: {labels_dir}")
            continue
            
        print(f"Checking labels in: {labels_dir}")
        
        for label_file in labels_dir.glob('*.txt'):
            try:
                with open(label_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                new_lines = []
                has_error = False
                
                for line in lines:
                    parts = line.strip().split()
                    if parts:
                        try:
                            class_id = int(parts[0])
                            # Проверяем что класс в допустимом диапазоне
                            if 0 <= class_id < num_classes:
                                new_lines.append(line)
                            else:
                                print(f"Invalid class {class_id} in {label_file.name}")
                                # Заменяем на класс 0 (безопасный вариант)
                                parts[0] = '0'
                                new_lines.append(' '.join(parts) + '\n')
                                fixed_count += 1
                                has_error = True
                        except ValueError:
                            # Если не число, заменяем на класс 0
                            parts[0] = '0'
                            new_lines.append(' '.join(parts) + '\n')
                            fixed_count += 1
                            has_error = True
                
                # Перезаписываем файл если были исправления
                if has_error:
                    with open(label_file, 'w', encoding='utf-8') as f:
                        f.writelines(new_lines)
                    error_count += 1
                    
            except Exception as e:
                print(f"Error processing {label_file}: {e}")
    
    print(f"\n✅ Fixed {fixed_count} invalid class labels")
    print(f"✅ Fixed {error_count} files with errors")
    return fixed_count

def check_pseudo_labels():
    """Проверить псевдо-метки на корректность классов"""
    import json
    
    print("Checking pseudo-labeled predictions...")
    
    try:
        with open('unlabeled_predictions.json', 'r', encoding='utf-8') as f:
            predictions = json.load(f)
        
        invalid_predictions = []
        for pred in predictions:
            class_id = pred['predicted_class']
            if not (0 <= class_id < 12):
                invalid_predictions.append(pred)
                print(f"Invalid prediction: {pred['image_path']} -> class {class_id}")
        
        if invalid_predictions:
            print(f"Found {len(invalid_predictions)} invalid predictions")
            # Исправим их
            for pred in invalid_predictions:
                pred['predicted_class'] = 0  # Заменяем на класс 0
                pred['class_name'] = '1 Отвертка минус'  # Имя класса 0
            
            # Сохраняем исправленные предсказания
            with open('unlabeled_predictions.json', 'w', encoding='utf-8') as f:
                json.dump(predictions, f, indent=2, ensure_ascii=False)
            
            print("Fixed invalid predictions in unlabeled_predictions.json")
    
    except Exception as e:
        print(f"Error checking predictions: {e}")

if __name__ == "__main__":
    print("Fixing label classes...")
    fix_label_classes()
    print("\nChecking pseudo-labels...")
    check_pseudo_labels()