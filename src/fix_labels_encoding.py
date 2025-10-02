# fix_labels_encoding.py
from pathlib import Path
import chardet

def detect_encoding(file_path):
    """Определить кодировку файла"""
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    return chardet.detect(raw_data)['encoding']

def fix_labels_encoding():
    data_dir = Path('../yolo_dataset')
    labels_dirs = [
        data_dir / 'labels',
        data_dir / 'pseudo_labeled' / 'labels'
    ]
    
    fixed_count = 0
    problem_files = []
    
    for labels_dir in labels_dirs:
        if not labels_dir.exists():
            print(f"Labels directory not found: {labels_dir}")
            continue
            
        print(f"Checking labels in: {labels_dir}")
        
        for label_file in labels_dir.glob('*.txt'):
            try:
                # Попробуем прочитать как UTF-8
                with open(label_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Если успешно, файл уже в правильной кодировке
                continue
                
            except UnicodeDecodeError:
                # Пробуем определить кодировку
                encoding = detect_encoding(label_file)
                print(f"Fixing {label_file.name} - detected encoding: {encoding}")
                
                try:
                    # Читаем в правильной кодировке
                    with open(label_file, 'r', encoding=encoding) as f:
                        content = f.read()
                    
                    # Перезаписываем в UTF-8
                    with open(label_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    fixed_count += 1
                    
                except Exception as e:
                    print(f"Error fixing {label_file}: {e}")
                    problem_files.append(str(label_file))
    
    print(f"\n✅ Fixed {fixed_count} label files")
    if problem_files:
        print(f"❌ Could not fix {len(problem_files)} files:")
        for file in problem_files[:5]:  # Покажем первые 5 проблемных файлов
            print(f"   - {file}")
    
    return fixed_count

def create_simple_labels_for_pseudo():
    """Создать простые метки для псевдо-размеченных изображений"""
    pseudo_labels_dir = Path('../yolo_dataset/pseudo_labeled/labels')
    
    if not pseudo_labels_dir.exists():
        print("Pseudo labels directory not found")
        return
    
    created_count = 0
    
    for label_file in pseudo_labels_dir.glob('*.txt'):
        try:
            # Просто создаем простую метку (класс в центре изображения)
            with open(label_file, 'w', encoding='utf-8') as f:
                # Берем только первую строку из существующего файла
                with open(label_file, 'r', encoding='utf-8', errors='ignore') as old_f:
                    first_line = old_f.readline().strip()
                
                if first_line:
                    # Оставляем только класс и простые координаты
                    parts = first_line.split()
                    if len(parts) >= 1:
                        class_id = parts[0]
                        f.write(f"{class_id} 0.5 0.5 1.0 1.0\n")
                        created_count += 1
        
        except Exception as e:
            print(f"Error processing {label_file}: {e}")
            # Создаем простейшую метку
            with open(label_file, 'w', encoding='utf-8') as f:
                f.write("0 0.5 0.5 1.0 1.0\n")
            created_count += 1
    
    print(f"✅ Created/updated {created_count} simple label files")

if __name__ == "__main__":
    print("Fixing label files encoding...")
    fixed = fix_labels_encoding()
    
    if fixed == 0:
        print("\nTrying to create simple labels for pseudo-labeled images...")
        create_simple_labels_for_pseudo()