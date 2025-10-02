# check_structure.py
from pathlib import Path

def check_directory_structure():
    base_dir = Path('/data/vscode/HacatonAeroflot/Aeroflot-project')
    yolo_dir = base_dir / 'yolo_dataset'
    
    print("Checking directory structure...")
    print(f"Base directory: {base_dir}")
    print(f"YOLO directory exists: {yolo_dir.exists()}")
    
    if yolo_dir.exists():
        print("\nContents of yolo_dataset:")
        for item in yolo_dir.iterdir():
            if item.is_dir():
                file_count = len(list(item.glob('*')))
                print(f"  📁 {item.name}/ ({file_count} items)")
            else:
                print(f"  📄 {item.name}")
        
        # Check specific directories
        print("\nChecking specific directories:")
        for dir_name in ['visualizations', 'images', 'labels', 'annotations']:
            dir_path = yolo_dir / dir_name
            if dir_path.exists():
                files = list(dir_path.glob('*'))
                print(f"  {dir_name}: {len(files)} files")
                if files:
                    print(f"    Sample: {[f.name for f in files[:3]]}")

if __name__ == "__main__":
    check_directory_structure()