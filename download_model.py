import argparse
import os
import sys
import urllib.request

MODELS = {
    "lite": {
        "url": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
        "filename": "pose_landmarker_lite.task",
        "description": "Lite model (fastest, lower latency)",
    },
    "full": {
        "url": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task",
        "filename": "pose_landmarker.task",
        "description": "Full model (balanced speed and accuracy, default)",
    },
    "heavy": {
        "url": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task",
        "filename": "pose_landmarker_heavy.task",
        "description": "Heavy model (highest accuracy, higher latency)",
    },
}


def download_progress(count, block_size, total_size):
    if total_size > 0:
        percent = int(count * block_size * 100 / total_size)
        percent = min(100, percent)
        downloaded_mb = count * block_size / (1024 * 1024)
        total_mb = total_size / (1024 * 1024)
        sys.stdout.write(f"\rDownloading: {percent}% ({downloaded_mb:.1f} MB / {total_mb:.1f} MB)")
        sys.stdout.flush()


def download_model(model_variant="full", target_path=None, force=False):
    if model_variant not in MODELS:
        raise ValueError(f"Unknown model variant: {model_variant}. Available: {list(MODELS.keys())}")

    model_info = MODELS[model_variant]
    if target_path is None:
        target_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), model_info["filename"])

    if os.path.exists(target_path) and not force:
        file_size_mb = os.path.getsize(target_path) / (1024 * 1024)
        print(f"Model already exists at '{target_path}' ({file_size_mb:.1f} MB). Use --force to re-download.")
        return target_path

    print(f"Downloading {model_info['description']}...")
    print(f"Source URL: {model_info['url']}")
    print(f"Destination: {target_path}")

    urllib.request.urlretrieve(model_info["url"], target_path, reporthook=download_progress)
    print("\nDownload complete.")
    return target_path


def main():
    parser = argparse.ArgumentParser(description="Download MediaPipe Pose Landmarker models.")
    parser.add_argument(
        "--variant",
        choices=["lite", "full", "heavy"],
        default="full",
        help="Model variant to download (default: full)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Target output filepath (default: pose_landmarker.task in repo root)",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force re-download even if file already exists",
    )
    args = parser.parse_args()

    download_model(model_variant=args.variant, target_path=args.output, force=args.force)


if __name__ == "__main__":
    main()
