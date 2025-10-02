# create_splits.py
import os
import random
from pathlib import Path
import glob

def create_dataset_splits():
    data_dir = Path('/data/vscode/HacatonAeroflot/Aeroflot-project/yolo_dataset')
    images_dir = data_dir / 'visualizations'
    labels_dir = data_dir / 'labels'
    
    print(f"Images directory: {images_dir}")
    print(f"Labels directory: {labels_dir}")
    
    # Get all image files
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.JPG', '*.JPEG', '*.PNG']
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(images_dir.glob(ext))
    
    print(f"Found {len(image_files)} image files")
    
    # Filter images that have corresponding labels
    valid_images = []
    missing_labels = []
    
    for img_path in image_files:
        label_path = labels_dir / f"{img_path.stem}.txt"
        if label_path.exists():
            valid_images.append(img_path)
        else:
            missing_labels.append(img_path.name)
    
    print(f"Found {len(valid_images)} images with labels")
    print(f"Missing labels for {len(missing_labels)} images")
    
    if missing_labels:
        print("Sample of images missing labels:")
        for img_name in missing_labels[:5]:
            print(f"  - {img_name}")
    
    if len(valid_images) == 0:
        print("No valid image-label pairs found!")
        return
    
    # Shuffle and split
    random.seed(42)  # For reproducible splits
    random.shuffle(valid_images)
    
    train_ratio = 0.8
    val_ratio = 0.15
    test_ratio = 0.05
    
    total = len(valid_images)
    train_count = int(total * train_ratio)
    val_count = int(total * val_ratio)
    test_count = total - train_count - val_count
    
    train_files = valid_images[:train_count]
    val_files = valid_images[train_count:train_count + val_count]
    test_files = valid_images[train_count + val_count:]
    
    print(f"\nSplit counts:")
    print(f"  Train: {len(train_files)} images")
    print(f"  Val: {len(val_files)} images")
    print(f"  Test: {len(test_files)} images")
    
    # Write split files with relative paths
    def write_split(file_list, split_name):
        with open(data_dir / f'{split_name}.txt', 'w') as f:
            for img_path in file_list:
                # Use relative path from data directory
                rel_path = img_path.relative_to(data_dir)
                f.write(f"./{rel_path}\n")
    
    write_split(train_files, 'train')
    write_split(val_files, 'val') 
    write_split(test_files, 'test')
    
    print(f"\nCreated split files:")
    print(f"  - train.txt ({len(train_files)} images)")
    print(f"  - val.txt ({len(val_files)} images)")
    print(f"  - test.txt ({len(test_files)} images)")
    
    # Update data.yaml file
    yaml_content = f"""# YOLO Dataset Configuration
path: {data_dir}
train: train.txt
val: val.txt
test: test.txt

# Number of classes
nc: 12

# Class names
names:
  0: "1 Отвертка минус"
  1: "10 Ключ рожковый"
  2: "11 Бокорезы"
  3: "2 Отвертка плюс" 
  4: "3 Отвертка смещенный крест"
  5: "4 Коловорот"
  6: "5 Пассатижи контровочные"
  7: "6 Пассатижи"
  8: "7 Шерица"
  9: "8 Разводной ключ"
  10: "9 Открывашка банок"
"""
    
    with open(data_dir / 'data.yaml', 'w', encoding='utf-8') as f:
        f.write(yaml_content)
    
    print(f"\nUpdated data.yaml file")
    
    # Verify the splits
    print(f"\nVerifying splits:")
    for split_name in ['train', 'val', 'test']:
        split_file = data_dir / f'{split_name}.txt'
        if split_file.exists():
            with open(split_file, 'r') as f:
                lines = f.readlines()
            print(f"  {split_name}.txt: {len(lines)} lines")
    
    print(f"\nDataset preparation complete!")
    print(f"Total labeled images: {len(valid_images)}")
    print(f"You can now run: python ../src/main.py --mode active_learn")

if __name__ == "__main__":
    create_dataset_splits()