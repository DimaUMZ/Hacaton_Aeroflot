## model_trainer.py
import os
import torch
import yaml
import numpy as np
from torch.utils.data import DataLoader, Dataset
import cv2
from PIL import Image, ImageFile
import torch.nn as nn
import torch.optim as optim
from torchvision import transforms
import matplotlib.pyplot as plt
import json
from pathlib import Path
import glob

# Allow loading of truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Force CPU usage
torch.set_num_threads(4)
device = torch.device('cpu')

def validate_image_file(img_path):
    """Check if image file is valid and can be opened"""
    try:
        with Image.open(img_path) as img:
            img.verify()  # Verify that it's a valid image
        return True
    except (IOError, SyntaxError, Exception) as e:
        print(f"Invalid image file {img_path}: {e}")
        return False

def find_data_yaml():
    """Find the data.yaml file in common locations"""
    possible_paths = [
        'yolo_dataset/data.yaml',
        '../yolo_dataset/data.yaml',
        '../../yolo_dataset/data.yaml',
        'datasets/data.yaml',
        '../datasets/data.yaml',
        '../../datasets/data.yaml',
        'data.yaml',
        '../data.yaml'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"Found data.yaml at: {path}")
            return path
    
    return None

def create_dataset_splits(data_yaml_path):
    """Create train/val splits if they don't exist"""
    data_dir = Path(data_yaml_path).parent
    visualizations_dir = data_dir / 'visualizations'
    labels_dir = data_dir / 'labels'
    
    if not visualizations_dir.exists():
        print(f"Visualizations directory not found: {visualizations_dir}")
        return False
    
    # Get all image files
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
        image_files.extend(glob.glob(str(visualizations_dir / ext)))
        image_files.extend(glob.glob(str(visualizations_dir / '**' / ext), recursive=True))
    
    print(f"Found {len(image_files)} images in {visualizations_dir}")
    
    if len(image_files) == 0:
        print("No images found!")
        return False
    
    # Shuffle and split
    np.random.shuffle(image_files)
    split_idx = int(0.8 * len(image_files))
    train_files = image_files[:split_idx]
    val_files = image_files[split_idx:]
    
    # Create relative paths for YOLO
    def make_relative_paths(file_list):
        return [str(Path(f).relative_to(data_dir)) for f in file_list]
    
    train_relative = make_relative_paths(train_files)
    val_relative = make_relative_paths(val_files)
    
    # Write train.txt
    with open(data_dir / 'train.txt', 'w') as f:
        for path in train_relative:
            f.write(f"{path}\n")
    
    # Write val.txt
    with open(data_dir / 'val.txt', 'w') as f:
        for path in val_relative:
            f.write(f"{path}\n")
    
    print(f"Created train split with {len(train_files)} images")
    print(f"Created val split with {len(val_files)} images")
    
    return True

class ToolDataset(Dataset):
    def __init__(self, data_yaml, transform=None, mode='train'):
        # Resolve the full path
        data_yaml_path = Path(data_yaml)
        if not data_yaml_path.is_absolute():
            data_yaml_path = Path.cwd() / data_yaml_path
        
        print(f"Loading dataset from: {data_yaml_path}")
        
        if not os.path.exists(data_yaml_path):
            raise FileNotFoundError(f"data.yaml not found at: {data_yaml_path}")
        
        with open(data_yaml_path, 'r', encoding='utf-8') as f:
            data_config = yaml.safe_load(f)
        
        self.data_dir = Path(data_config['path'])
        self.transform = transform
        self.mode = mode
        
        # Get the appropriate dataset split file
        split_file = data_config[mode]
        split_path = self.data_dir / split_file
        
        print(f"Loading {mode} split from: {split_path}")
        
        if not split_path.exists():
            raise FileNotFoundError(f"Split file not found: {split_path}")
        
        with open(split_path, 'r') as f:
            raw_image_paths = [line.strip() for line in f.readlines() if line.strip()]
        
        # Filter valid images
        self.image_paths = []
        self.valid_indices = []
        
        print(f"Validating {len(raw_image_paths)} images...")
        invalid_count = 0
        
        for idx, img_rel_path in enumerate(raw_image_paths):
            # Image path is relative to data_dir, may start with ./
            if img_rel_path.startswith('./'):
                img_rel_path = img_rel_path[2:]
            
            img_path = self.data_dir / img_rel_path
            
            if validate_image_file(img_path):
                self.image_paths.append(img_rel_path)
                self.valid_indices.append(idx)
            else:
                invalid_count += 1
        
        print(f"Found {len(self.image_paths)} valid images, skipped {invalid_count} invalid images")
        
        # Load class names
        self.classes = data_config['names']
        self.num_classes = data_config['nc']
        
        print(f"Final dataset: {len(self.image_paths)} images for {mode}")
        print(f"Number of classes: {self.num_classes}")
        
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        img_rel_path = self.image_paths[idx]
        img_path = self.data_dir / img_rel_path
        
        # Convert image path to label path
        label_path = str(img_path).replace('visualizations', 'labels').replace('.jpg', '.txt').replace('.png', '.txt').replace('.JPG', '.txt')
        label_path = Path(label_path)
        
        # Load image with error handling
        try:
            image = Image.open(img_path).convert('RGB')
        except Exception as e:
            print(f"Error loading image {img_path}, using dummy image: {e}")
            # Return a dummy image
            image = Image.new('RGB', (224, 224), color='gray')
        
        # Load YOLO format labels
        labels = []

        if label_path.exists():
            try:
                # Пробуем разные кодировки
                with open(label_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                try:
                    with open(label_path, 'r', encoding='cp1251') as f:  # Windows Cyrillic
                        lines = f.readlines()
                except UnicodeDecodeError:
                    try:
                        with open(label_path, 'r', encoding='latin-1') as f:  # Fallback
                            lines = f.readlines()
                    except:
                        lines = []
            
            for line in lines:
                data = line.strip().split()
                if len(data) >= 5:  # class, x_center, y_center, width, height
                    try:
                        class_id = int(data[0])
                        labels.append(class_id)
                    except ValueError:
                        continue
        
        # Use the first object's class as image label
        if labels:
            label = labels[0]
            # Ensure label is within valid range
            if label >= self.num_classes:
                print(f"Warning: Label {label} out of bounds in {img_path}, using 0")
                label = 0
        else:
            label = 0
        
        if self.transform:
            try:
                image = self.transform(image)
            except Exception as e:
                print(f"Error transforming image {img_path}: {e}")
                # Create a dummy transformed image
                image = torch.randn(3, 224, 224)
        
        return image, label

class SimpleToolClassifier(nn.Module):
    def __init__(self, num_classes):
        super(SimpleToolClassifier, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.AdaptiveAvgPool2d((7, 7))
        )
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(128 * 7 * 7, 512),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, num_classes)
        )
    
    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x

def train_model(data_yaml=None, model_save_path='tool_classifier_cpu.pth'):
    if data_yaml is None:
        data_yaml = find_data_yaml()
        if data_yaml is None:
            print("ERROR: Could not find data.yaml file. Please specify the path manually.")
            return None
    
    print("Setting up data transforms...")
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.3),
        transforms.RandomRotation(10),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                           std=[0.229, 0.224, 0.225])
    ])
    
    print("Loading datasets...")
    try:
        train_dataset = ToolDataset(data_yaml, transform, 'train')
        val_dataset = ToolDataset(data_yaml, transform, 'val')
    except Exception as e:
        print(f"Error loading datasets: {e}")
        print("Please check your data.yaml file and dataset structure")
        return None
    
    if len(train_dataset) == 0:
        print("No valid training images found!")
        return None
    
    # Use smaller batch size for stability
    batch_size = 4
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    
    print(f"Training on {len(train_dataset)} images, validating on {len(val_dataset)} images")
    print(f"Number of classes: {train_dataset.num_classes}")
    
    model = SimpleToolClassifier(num_classes=train_dataset.num_classes)
    model.to(device)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=15, gamma=0.5)
    
    num_epochs = 15
    train_losses = []
    val_accuracies = []
    
    print("Starting training...")
    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0
        correct_train = 0
        total_train = 0
        batch_count = 0
        
        for batch_idx, (images, labels) in enumerate(train_loader):
            try:
                images, labels = images.to(device), labels.to(device)
                
                # Skip batches with NaN values
                if torch.isnan(images).any() or torch.isnan(labels).any():
                    print(f"Skipping batch {batch_idx} due to NaN values")
                    continue
                
                optimizer.zero_grad()
                outputs = model(images)
                loss = criterion(outputs, labels)
                
                if torch.isnan(loss):
                    print(f"Skipping batch {batch_idx} due to NaN loss")
                    continue
                
                loss.backward()
                optimizer.step()
                
                running_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total_train += labels.size(0)
                correct_train += (predicted == labels).sum().item()
                batch_count += 1
                
            except Exception as e:
                print(f"Error in training batch {batch_idx}: {e}")
                continue
        
        if batch_count == 0:
            print(f"Epoch {epoch+1}: No valid batches processed")
            continue
            
        train_accuracy = 100 * correct_train / total_train if total_train > 0 else 0
        
        # Validation
        model.eval()
        correct_val = 0
        total_val = 0
        
        with torch.no_grad():
            for images, labels in val_loader:
                try:
                    images, labels = images.to(device), labels.to(device)
                    outputs = model(images)
                    _, predicted = torch.max(outputs.data, 1)
                    total_val += labels.size(0)
                    correct_val += (predicted == labels).sum().item()
                except Exception as e:
                    print(f"Error in validation batch: {e}")
                    continue
        
        val_accuracy = 100 * correct_val / total_val if total_val > 0 else 0
        avg_loss = running_loss / batch_count if batch_count > 0 else 0
        
        train_losses.append(avg_loss)
        val_accuracies.append(val_accuracy)
        
        print(f'Epoch [{epoch+1}/{num_epochs}], Loss: {avg_loss:.4f}, Train Acc: {train_accuracy:.2f}%, Val Acc: {val_accuracy:.2f}%')
        
        scheduler.step()
    
    torch.save(model.state_dict(), model_save_path)
    print(f"Model saved to {model_save_path}")
    
    # Plot training history
    if len(train_losses) > 1:
        plt.figure(figsize=(12, 4))
        plt.subplot(1, 2, 1)
        plt.plot(train_losses)
        plt.title('Training Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        
        plt.subplot(1, 2, 2)
        plt.plot(val_accuracies)
        plt.title('Validation Accuracy')
        plt.xlabel('Epoch')
        plt.ylabel('Accuracy (%)')
        
        plt.tight_layout()
        plt.savefig('training_history.png')
        plt.close()
        print("Training history plot saved to training_history.png")
    
    return model


def predict_unlabeled_images(model, unlabeled_dir='../datasets/raw/', data_yaml=None):
    if data_yaml is None:
        data_yaml = find_data_yaml()
    
    print("Loading class names...")
    with open(data_yaml, 'r', encoding='utf-8') as f:
        data_config = yaml.safe_load(f)
    class_names = data_config['names']
    
    model.eval()
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                           std=[0.229, 0.224, 0.225])
    ])
    
    predictions = []
    
    raw_path = Path(unlabeled_dir)
    if not raw_path.exists():
        print(f"Unlabeled directory not found: {unlabeled_dir}")
        return []
    
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.JPG', '*.JPEG', '*.PNG']
    
    print(f"Searching for images in {raw_path}...")
    
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(str(raw_path / ext)))
        image_files.extend(glob.glob(str(raw_path / '**' / ext), recursive=True))
    
    print(f"Found {len(image_files)} images to process")
    
    valid_images = 0
    for i, img_path in enumerate(image_files):
        if not validate_image_file(img_path):
            print(f"Skipping invalid image: {img_path}")
            continue
            
        try:
            image = Image.open(img_path).convert('RGB')
            input_tensor = transform(image).unsqueeze(0).to(device)
            
            with torch.no_grad():
                outputs = model(input_tensor)
                probabilities = torch.nn.functional.softmax(outputs, dim=1)
                confidence, predicted = torch.max(probabilities, 1)
            
            predicted_class = predicted.item()
            confidence_score = confidence.item()
            
            class_name = class_names.get(predicted_class, f"Class_{predicted_class}")
            
            predictions.append({
                'image_path': str(img_path),
                'predicted_class': predicted_class,
                'class_name': class_name,
                'confidence': confidence_score
            })
            
            valid_images += 1
            print(f"[{valid_images}/{len(image_files)}] {Path(img_path).name} -> {class_name} ({confidence_score:.3f})")
            
        except Exception as e:
            print(f"Error processing {img_path}: {e}")
    
    with open('unlabeled_predictions.json', 'w', encoding='utf-8') as f:
        json.dump(predictions, f, indent=2, ensure_ascii=False)
    
    print(f"Predictions saved to unlabeled_predictions.json")
    print(f"Successfully processed {valid_images} out of {len(image_files)} images")
    return predictions

def prepare_pseudo_labels(predictions, confidence_threshold=0.7):
    high_confidence_preds = [p for p in predictions if p['confidence'] > confidence_threshold]
    
    print(f"Found {len(high_confidence_preds)} high-confidence predictions (confidence > {confidence_threshold})")
    
    # Create a directory for pseudo-labeled images
    pseudo_dir = Path('pseudo_labeled')
    pseudo_dir.mkdir(exist_ok=True)
    
    for pred in high_confidence_preds:
        img_path = Path(pred['image_path'])
        
        # Copy image to pseudo-labeled directory
        new_img_path = pseudo_dir / img_path.name
        import shutil
        shutil.copy2(img_path, new_img_path)
        
        # Create labels directory
        labels_dir = pseudo_dir / 'labels'
        labels_dir.mkdir(exist_ok=True)
        
        label_path = labels_dir / f"{img_path.stem}.txt"
        
        # Create YOLO format label (full image bounding box)
        with open(label_path, 'w') as f:
            f.write(f"{pred['predicted_class']} 0.5 0.5 1.0 1.0\n")
    
    print(f"Pseudo-labeled images saved to {pseudo_dir}")
    return high_confidence_preds

def analyze_dataset(data_yaml=None):
    if data_yaml is None:
        data_yaml = find_data_yaml()
        if data_yaml is None:
            print("ERROR: Could not find data.yaml file")
            return None
    
    print("Analyzing dataset...")
    with open(data_yaml, 'r', encoding='utf-8') as f:
        data_config = yaml.safe_load(f)
    
    class_names = data_config['names']
    
    data_dir = Path(data_yaml).parent
    visualizations_dir = data_dir / 'visualizations'
    labels_dir = data_dir / 'labels'
    
    print(f"Data directory: {data_dir}")
    print(f"Visualizations directory: {visualizations_dir}")
    print(f"Labels directory: {labels_dir}")
    
    # Count images and labels
    image_count = 0
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
        image_count += len(glob.glob(str(visualizations_dir / ext)))
        image_count += len(glob.glob(str(visualizations_dir / '**' / ext), recursive=True))
    
    label_count = len(glob.glob(str(labels_dir / '*.txt')))
    
    print(f"Total images: {image_count}")
    print(f"Total labels: {label_count}")
    print(f"Classes: {class_names}")
    
    # Show class distribution
    if labels_dir.exists():
        class_distribution = {class_id: 0 for class_id in class_names.keys()}
        for label_file in labels_dir.glob('*.txt'):
            with open(label_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        class_id = int(parts[0])
                        if class_id in class_distribution:
                            class_distribution[class_id] += 1
        
        print("\nClass distribution in labels:")
        for class_id, count in class_distribution.items():
            class_name = class_names.get(class_id, f"Class_{class_id}")
            print(f"  {class_name}: {count} instances")
    
    return class_names

if __name__ == "__main__":
    print("This file contains training and prediction functions.")
    print("Run main.py to start the training pipeline.")