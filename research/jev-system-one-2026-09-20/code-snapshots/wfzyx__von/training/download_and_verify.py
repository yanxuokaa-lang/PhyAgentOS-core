"""Poll S3 for completed Von checkpoint, download locally, and verify benchmark."""

import os
import subprocess
import time

AWS_CLI = "/mnt/c/Program Files/Amazon/AWSCLIV2/aws.exe"
S3_TARGET = "s3://model-weight/von-modernbert-rlcd"
LOCAL_DIR = "checkpoints/von-modernbert-rlcd"


def check_s3_ready() -> bool:
    res = subprocess.run([AWS_CLI, "s3", "ls", f"{S3_TARGET}/"], capture_output=True, text=True)
    if res.returncode != 0:
        return False
    files = res.stdout
    # Check if calibration.json and model weights exist
    return "calibration.json" in files and ("model.safetensors" in files or "config.json" in files)


def wait_and_download(poll_interval: int = 60):
    print("================================================================")
    print("  VON CHECKPOINT MONITOR & DOWNLOADER")
    print(f"  Watching: {S3_TARGET}/")
    print(f"  Target:   {LOCAL_DIR}/")
    print("================================================================\n")

    start_time = time.time()
    while True:
        elapsed_min = (time.time() - start_time) / 60.0
        if check_s3_ready():
            print(f"\n-> Checkpoint detected in S3 after {elapsed_min:.1f} minutes!")
            break
        print(f"[{time.strftime('%H:%M:%S')}] Waiting for training to complete ({elapsed_min:.1f}m elapsed)...")
        time.sleep(poll_interval)

    print(f"\nDownloading checkpoint from {S3_TARGET} to {LOCAL_DIR}...")
    os.makedirs(LOCAL_DIR, exist_ok=True)
    res = subprocess.run([AWS_CLI, "s3", "cp", "--recursive", S3_TARGET, LOCAL_DIR], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Download failed: {res.stderr}")

    print("Download complete! Files:")
    for f in os.listdir(LOCAL_DIR):
        print(f"  - {f}")

    print("\nRunning verification on OpenJev authored144 benchmark...")
    subprocess.run(["uv", "run", "python", "benchmarks/run_comparison.py", "--limit", "30"])


if __name__ == "__main__":
    wait_and_download()
