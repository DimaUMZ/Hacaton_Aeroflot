# update_training_set.py
from pathlib import Path

def update_training_set():
    data_dir = Path('../yolo_dataset')
    pseudo_dir = Path('pseudo_labeled')
    
    print("Updating training set with pseudo-labeled images...")
    
    # Check if pseudo_labeled directory exists
    if not pseudo_dir.exists():
        print("ERROR: pseudo_labeled directory not found!")
        print("Make sure you ran the prediction step first")
        return False
    
    # Count pseudo-labeled images
    image_files = list(pseudo_dir.glob('*.JPG')) + list(pseudo_dir.glob('*.jpg')) + list(pseudo_dir.glob('*.png'))
    print(f"Found {len(image_files)} pseudo-labeled images")
    
    if len(image_files) == 0:
        print("No pseudo-labeled images found!")
        return False
    
    # Read original train.txt
    train_file = data_dir / 'train.txt'
    if not train_file.exists():
        print("ERROR: train.txt not found!")
        return False
    
    with open(train_file, 'r') as f:
        original_images = [line.strip() for line in f.readlines() if line.strip()]
    
    print(f"Original train.txt has {len(original_images)} images")
    
    # Add pseudo-labeled images (relative to data_dir)
    new_images = [f"./pseudo_labeled/{img_path.name}" for img_path in image_files]
    
    # Combine original and new images
    all_images = original_images + new_images
    
    # Write updated train.txt
    with open(train_file, 'w') as f:
        for img_path in all_images:
            f.write(f"{img_path}\n")
    
    print(f"✅ Updated train.txt: {len(original_images)} original + {len(new_images)} new = {len(all_images)} total images")
    return True

if __name__ == "__main__":
    update_training_set()