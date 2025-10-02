# copy_pseudo_images.py
import json
import shutil
from pathlib import Path

def copy_pseudo_images():
    # Read predictions
    with open('unlabeled_predictions.json', 'r', encoding='utf-8') as f:
        predictions = json.load(f)
    
    pseudo_dir = Path('pseudo_labeled')
    pseudo_dir.mkdir(exist_ok=True)
    
    copied_count = 0
    missing_count = 0
    
    for pred in predictions:
        if pred['confidence'] > 0.7:  # Only high-confidence predictions
            src_path = Path(pred['image_path'])
            dst_path = pseudo_dir / src_path.name
            
            if src_path.exists():
                shutil.copy2(src_path, dst_path)
                copied_count += 1
            else:
                print(f"Missing: {src_path}")
                missing_count += 1
    
    print(f"✅ Copied {copied_count} images to pseudo_labeled/")
    print(f"❌ Missing {missing_count} source files")
    
    # Also copy labels
    labels_dir = pseudo_dir / 'labels'
    labels_dir.mkdir(exist_ok=True)
    
    # Create label files for pseudo-labeled images
    label_count = 0
    for pred in predictions:
        if pred['confidence'] > 0.7:
            src_path = Path(pred['image_path'])
            label_path = labels_dir / f"{src_path.stem}.txt"
            
            with open(label_path, 'w') as f:
                f.write(f"{pred['predicted_class']} 0.5 0.5 1.0 1.0\n")
            label_count += 1
    
    print(f"✅ Created {label_count} label files")

if __name__ == "__main__":
    copy_pseudo_images()