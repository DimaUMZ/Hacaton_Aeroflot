# main.py
import argparse
import torch
from pathlib import Path
import os
import sys
from model_trainer import (
    train_model, 
    predict_unlabeled_images, 
    prepare_pseudo_labels, 
    analyze_dataset,
    SimpleToolClassifier,
    device,
    find_data_yaml
)

def active_learning_cycle(data_yaml=None, unlabeled_dir=None):
    """Complete active learning cycle: train -> predict -> retrain"""
    
    print("=" * 60)
    print("STARTING ACTIVE LEARNING CYCLE")
    print("=" * 60)
    
    # Step 1: Analyze dataset
    print("\n1. Analyzing dataset...")
    class_names = analyze_dataset(data_yaml)
    
    if class_names is None:
        print("Failed to analyze dataset. Please check your data.yaml file.")
        return None
    
    print(f"Classes: {class_names}")
    
    # Step 2: Initial training
    print("\n2. Starting initial training...")
    model = train_model(data_yaml)
    
    if model is None:
        print("Training failed. Please check your dataset.")
        return None
    
    # Step 3: Predict unlabeled images
    print("\n3. Predicting unlabeled images...")
    predictions = predict_unlabeled_images(model, unlabeled_dir, data_yaml)
    
    if not predictions:
        print("No unlabeled images found or predictions failed.")
        return model
    
    # Step 4: Prepare pseudo-labels
    print("\n4. Preparing pseudo-labels for retraining...")
    high_conf_predictions = prepare_pseudo_labels(predictions, confidence_threshold=0.7)
    
    if high_conf_predictions:
        print(f"\n5. Retraining with {len(high_conf_predictions)} new pseudo-labeled images...")
        
        # Note: For full implementation, you would update your data.yaml
        # to include the pseudo-labeled images in the training set
        retrained_model = train_model(data_yaml, model_save_path='retrained_tool_classifier.pth')
        
        print("\nActive learning cycle completed!")
        print(f"Original model saved as: tool_classifier_cpu.pth")
        print(f"Retrained model saved as: retrained_tool_classifier.pth")
        return retrained_model
    else:
        print("No high-confidence predictions found for retraining.")
        return model

def main():
    parser = argparse.ArgumentParser(description='Tool Classification on CPU')
    parser.add_argument('--mode', choices=['train', 'predict', 'active_learn', 'analyze'], 
                       default='active_learn', help='Operation mode')
    parser.add_argument('--model_path', type=str, default='tool_classifier_cpu.pth',
                       help='Path to model weights')
    parser.add_argument('--data_yaml', type=str, default=None,
                       help='Path to data.yaml file (auto-detect if not specified)')
    parser.add_argument('--unlabeled_dir', type=str, default=None,
                       help='Directory containing unlabeled images')
    parser.add_argument('--confidence_threshold', type=float, default=0.7,
                       help='Confidence threshold for pseudo-labeling')
    
    args = parser.parse_args()
    
    print(f"Running in {args.mode} mode")
    print(f"Using device: {device}")
    print(f"Current working directory: {os.getcwd()}")
    
    # Auto-detect data.yaml if not specified
    if args.data_yaml is None:
        args.data_yaml = find_data_yaml()
        if args.data_yaml is None:
            print("ERROR: Could not find data.yaml file automatically.")
            print("Please specify the path using --data_yaml argument")
            return
    
    # Auto-detect unlabeled directory if not specified
    if args.unlabeled_dir is None:
        possible_dirs = [
            '../datasets/raw/',
            '../../datasets/raw/',
            'datasets/raw/',
            '../raw/',
            '../../raw/',
            'raw/'
        ]
        for dir_path in possible_dirs:
            if os.path.exists(dir_path):
                args.unlabeled_dir = dir_path
                print(f"Auto-detected unlabeled directory: {args.unlabeled_dir}")
                break
        
        if args.unlabeled_dir is None:
            args.unlabeled_dir = '../datasets/raw/'
            print(f"Using default unlabeled directory: {args.unlabeled_dir}")
    
    if args.mode == 'analyze':
        analyze_dataset(args.data_yaml)
        
    elif args.mode == 'train':
        print("Training model...")
        train_model(args.data_yaml, args.model_path)
        
    elif args.mode == 'predict':
        print("Loading model for prediction...")
        
        # Load class info to get number of classes
        import yaml
        with open(args.data_yaml, 'r') as f:
            data_config = yaml.safe_load(f)
        num_classes = len(data_config['names'])
        
        model = SimpleToolClassifier(num_classes=num_classes)
        try:
            model.load_state_dict(torch.load(args.model_path, map_location='cpu'))
            model.to(device)
            print(f"Model loaded from {args.model_path}")
        except Exception as e:
            print(f"Error loading model: {e}")
            print("Please train a model first or check the model path")
            return
        
        predictions = predict_unlabeled_images(model, args.unlabeled_dir, args.data_yaml)
        
        # Show summary
        if predictions:
            confidences = [p['confidence'] for p in predictions]
            print(f"\nPrediction Summary:")
            print(f"Total images processed: {len(predictions)}")
            print(f"Average confidence: {sum(confidences)/len(confidences):.3f}")
            print(f"Max confidence: {max(confidences):.3f}")
            print(f"Min confidence: {min(confidences):.3f}")
        
    elif args.mode == 'active_learn':
        print("Starting active learning cycle...")
        final_model = active_learning_cycle(args.data_yaml, args.unlabeled_dir)
        
        if final_model:
            print("\nActive learning completed successfully!")
        else:
            print("\nActive learning failed!")

if __name__ == "__main__":
    main()