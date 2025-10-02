# update_training_set_fixed.py
from pathlib import Path

def update_training_set():
    data_dir = Path('../yolo_dataset')
    pseudo_dir = data_dir / 'pseudo_labeled'
    
    print("Updating training set with pseudo-labeled images...")
    print(f"Data dir: {data_dir}")
    print(f"Pseudo dir: {pseudo_dir}")
    print(f"Pseudo dir exists: {pseudo_dir.exists()}")
    
    if not pseudo_dir.exists():
        print("ERROR: pseudo_labeled directory not found in yolo_dataset!")
        return False
    
    # Get ACTUAL image files
    image_extensions = ['*.jpg', '*.JPG', '*.jpeg', '*.JPEG', '*.png', '*.PNG']
    actual_images = []
    for ext in image_extensions:
        actual_images.extend(pseudo_dir.glob(ext))
    
    print(f"Found {len(actual_images)} ACTUAL image files")
    
    if len(actual_images) == 0:
        print("No images found!")
        return False
    
    # Show some examples
    print("Sample files:")
    for img in actual_images[:5]:
        print(f"  - {img.name}")
    
    # Read original train.txt
    train_file = data_dir / 'train.txt'
    if not train_file.exists():
        print("ERROR: train.txt not found!")
        return False
    
    with open(train_file, 'r') as f:
        original_images = [line.strip() for line in f.readlines() if line.strip()]
    
    print(f"Original train.txt has {len(original_images)} images")
    
    # Add ACTUAL pseudo-labeled images
    new_images = [f"./pseudo_labeled/{img_path.name}" for img_path in actual_images]
    
    # Combine
    all_images = original_images + new_images
    
    # Write updated train.txt
    with open(train_file, 'w') as f:
        for img_path in all_images:
            f.write(f"{img_path}\n")
    
    print(f"✅ Updated train.txt: {len(original_images)} original + {len(new_images)} new = {len(all_images)} total images")
    return True

if __name__ == "__main__":
    update_training_set()