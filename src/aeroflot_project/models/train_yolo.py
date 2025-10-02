"""
Train a YOLOv8 object detector for both single-object and group-object images.

This script expects a YOLO dataset folder with the structure created by
`prepare_dataset.py`, including a `data.yaml` file and `images/` + `labels/` splits.

Usage example (GPU):
  python -m src.aeroflot_project.models.train_yolo \
    --data yolo_dataset/data.yaml \
    --weights yolov8s.pt \
    --epochs 50 \
    --imgsz 640 \
    --batch 16 \
    --device 0 \
    --project runs/detect \
    --name yolov8s_tools

After training completes, the best weights are copied to
`src/aeroflot_project/models/best_tools_detection.pt` for inference in the app.
"""

import argparse
import os
import shutil
from ultralytics import YOLO


def train_yolo(
    data: str,
    weights: str,
    epochs: int,
    imgsz: int,
    batch: int,
    device: str,
    project: str,
    name: str,
    lr0: float,
    lrf: float,
    patience: int,
    workers: int,
    freeze: int,
    seed: int,
    mosaic: float,
    mixup: float,
):
    model = YOLO(weights)

    results = model.train(
        data=data,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project=project,
        name=name,
        lr0=lr0,
        lrf=lrf,
        patience=patience,
        workers=workers,
        freeze=freeze,
        seed=seed,
        mosaic=mosaic,
        mixup=mixup,
        verbose=True,
    )

    # Copy best weights into app models path for immediate use by API
    best_ckpt = os.path.join(project, name, 'weights', 'best.pt')
    target_dir = os.path.join('src', 'aeroflot_project', 'models')
    os.makedirs(target_dir, exist_ok=True)
    target_best = os.path.join(target_dir, 'best_tools_detection.pt')

    if os.path.exists(best_ckpt):
        shutil.copy2(best_ckpt, target_best)
        print(f"✅ Copied best weights to: {target_best}")
    else:
        print("⚠️ Best weights not found. Check your training run directory.")

    return results


def main():
    parser = argparse.ArgumentParser(description='Train YOLOv8 for tools detection')
    parser.add_argument('--data', type=str, default='yolo_dataset/data.yaml', help='Path to data.yaml')
    parser.add_argument('--weights', type=str, default='yolov8s.pt', help='Base model weights')
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--batch', type=int, default=16)
    parser.add_argument('--device', type=str, default='0', help='CUDA device id, "cpu" or "0,1"')
    parser.add_argument('--project', type=str, default='runs/detect')
    parser.add_argument('--name', type=str, default='yolov8_tools')
    parser.add_argument('--lr0', type=float, default=0.01)
    parser.add_argument('--lrf', type=float, default=0.01)
    parser.add_argument('--patience', type=int, default=20)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--freeze', type=int, default=0)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--mosaic', type=float, default=1.0)
    parser.add_argument('--mixup', type=float, default=0.0)

    args = parser.parse_args()

    # Validate paths
    if not os.path.exists(args.data):
        raise FileNotFoundError(f"data.yaml not found: {args.data}")

    print("🚀 Starting YOLOv8 training with args:")
    for k, v in vars(args).items():
        print(f"  {k}: {v}")

    train_yolo(
        data=args.data,
        weights=args.weights,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        lr0=args.lr0,
        lrf=args.lrf,
        patience=args.patience,
        workers=args.workers,
        freeze=args.freeze,
        seed=args.seed,
        mosaic=args.mosaic,
        mixup=args.mixup,
    )


if __name__ == '__main__':
    main()


