"""Automated AWS Spot Training Launcher for Option-Marker Joint Head.

Launches a 4x GPU Spot instance (g4dn.12xlarge), trains the single-pass
Option-Marker model with RLCD, syncs artifacts to S3, and auto-terminates.
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import time

VENV_AWS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".venv", "bin", "aws"))
AWS_CLI = VENV_AWS if os.path.exists(VENV_AWS) else (shutil.which("aws") or "/mnt/c/Program Files/Amazon/AWSCLIV2/aws.exe")
REGION = "us-west-2"
SUBNETS = [
    ("subnet-083ba040", "us-west-2a"),
    ("subnet-070e7461", "us-west-2b"),
    ("subnet-b75369ec", "us-west-2c"),
    ("subnet-a663228e", "us-west-2d"),
]
AMI_ID = "ami-0e24e0019a12c5b13"
CANDIDATE_TYPES = [
    ("g4dn.12xlarge", "4x NVIDIA T4 64GB, 48 vCPU (Spot ~$1.53/hr)"),
    ("g5.4xlarge", "1x NVIDIA A10G 24GB, 16 vCPU (Spot ~$0.69/hr)"),
    ("g5.2xlarge", "1x NVIDIA A10G 24GB, 8 vCPU (Spot ~$0.54/hr)"),
    ("g5.xlarge", "1x NVIDIA A10G 24GB, 4 vCPU (Spot ~$0.52/hr)"),
]
IAM_PROFILE = "AmazonSSMRoleForInstancesQuickSetup"
S3_TARGET = "s3://model-weight/von-option-marker"

USER_DATA_SCRIPT = """#!/bin/bash
set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# Hard safety watchdog: 120 minutes max
shutdown -h +120 &

echo "=== [VON OPTION-MARKER TRAINING START] ==="
export DEBIAN_FRONTEND=noninteractive

apt-get update && apt-get install -y awscli curl git

curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/root/.local/bin:$PATH"

mkdir -p /opt/von
aws s3 cp s3://model-weight/von-marker-src.tar.gz /tmp/von-marker-src.tar.gz
tar -xzf /tmp/von-marker-src.tar.gz -C /opt/von
cd /opt/von

/root/.local/bin/uv venv
/opt/von/.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
/opt/von/.venv/bin/pip install transformers datasets scipy sentencepiece tiktoken accelerate pydantic
/opt/von/.venv/bin/pip install -e /opt/von
export PYTHONPATH="/opt/von/src:$PYTHONPATH"

# Build operational decision training corpus
/opt/von/.venv/bin/python training/prepare_decision_dataset.py --max_train 65000 --val_samples 3000 --output_dir data_decision

# Detect GPUs and train with DDP
NUM_GPUS=$(nvidia-smi -L | wc -l)
echo "Detected $NUM_GPUS GPUs. Starting PyTorch DDP training..."

/opt/von/.venv/bin/torchrun --nproc_per_node=$NUM_GPUS training/train_option_marker.py \
    --train_data data_decision/train.jsonl \
    --val_data data_decision/val.jsonl \
    --base_model_id wfzyx/von-1.0 \
    --epochs 3 \
    --batch_size 8 \
    --grad_accum_steps 2 \
    --s3_target s3://model-weight/von-option-marker \
    --output_dir checkpoints/von-option-marker

aws s3 cp /var/log/user-data.log s3://model-weight/von-option-marker/run.log || true

echo "=== [OPTION-MARKER TRAINING COMPLETE - TERMINATING] ==="
shutdown -h now
"""


def run_aws(cmd: list) -> dict:
    full_cmd = [AWS_CLI] + cmd + ["--region", REGION, "--output", "json"]
    res = subprocess.run(full_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"AWS CLI error: {res.stderr.strip()}")
    if not res.stdout.strip():
        return {}
    return json.loads(res.stdout)


def launch():
    print("================================================================")
    print("  VON OPTION-MARKER TRAINING LAUNCHER")
    print("  Cluster Targets:  4x GPU (g4dn.12xlarge) / 1x GPU (g5.xlarge)")
    print("  Region:           us-west-2")
    print(f"  Target S3 Prefix: {S3_TARGET}")
    print("================================================================\n")

    encoded_user_data = base64.b64encode(USER_DATA_SCRIPT.encode("utf-8")).decode("utf-8")

    launched_instance_id = None

    for itype, desc in CANDIDATE_TYPES:
        print(f"\nEvaluating instance type: {itype} [{desc}]...")
        for subnet_id, az in SUBNETS:
            print(f"  -> Trying {itype} in {az} ({subnet_id})...")
            try:
                run_params = [
                    "ec2", "run-instances",
                    "--image-id", AMI_ID,
                    "--instance-type", itype,
                    "--subnet-id", subnet_id,
                    "--iam-instance-profile", f"Name={IAM_PROFILE}",
                    "--instance-initiated-shutdown-behavior", "terminate",
                    "--user-data", encoded_user_data,
                    "--instance-market-options", json.dumps({"MarketType": "spot"}),
                    "--tag-specifications", json.dumps([{
                        "ResourceType": "instance",
                        "Tags": [
                            {"Key": "Name", "Value": "von-option-marker-training"},
                            {"Key": "Project", "Value": "von"},
                        ]
                    }]),
                ]
                res = run_aws(run_params)
                launched_instance_id = res["Instances"][0]["InstanceId"]
                print(f"\n-> SUCCESS! Launched {itype} Spot instance in {az}: {launched_instance_id}")
                break
            except Exception as e:
                print(f"     Not available in {az}: {e}")

        if launched_instance_id:
            break

    if not launched_instance_id:
        print("\nERROR: Could not launch any Spot instance. Exiting.")
        sys.exit(1)

    print("\nWaiting for instance to enter 'running' state...")
    while True:
        desc = run_aws(["ec2", "describe-instances", "--instance-ids", launched_instance_id])
        state = desc["Reservations"][0]["Instances"][0]["State"]["Name"]
        print(f"  -> Instance {launched_instance_id} status: {state}")
        if state == "running":
            break
        time.sleep(5)

    print("\nOption-Marker Spot training instance is RUNNING!")
    print("Artifacts will automatically upload to s3://model-weight/von-option-marker and terminate.")


if __name__ == "__main__":
    launch()
