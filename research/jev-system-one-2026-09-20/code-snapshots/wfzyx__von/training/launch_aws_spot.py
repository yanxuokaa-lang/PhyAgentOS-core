"""Automated AWS Spot Training Launcher with guaranteed self-termination.

Launches a 4x GPU Spot instance (g5.12xlarge), executes multi-GPU DDP training,
uploads the trained checkpoint to S3 (s3://model-weight/von-modernbert-rlcd/),
and terminates the instance immediately.
"""

import base64
import json
import os
import subprocess
import sys
import time


import shutil

VENV_AWS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".venv", "bin", "aws"))
AWS_CLI = VENV_AWS if os.path.exists(VENV_AWS) else (shutil.which("aws") or "/mnt/c/Program Files/Amazon/AWSCLIV2/aws.exe")
REGION = "us-west-2"
SUBNETS = [
    ("subnet-083ba040", "us-west-2a"),
    ("subnet-070e7461", "us-west-2b"),
    ("subnet-b75369ec", "us-west-2c"),
    ("subnet-a663228e", "us-west-2d"),
]
AMI_ID = "ami-0e24e0019a12c5b13"  # Deep Learning Base AMI with CUDA
CANDIDATE_TYPES = [
    ("g5.12xlarge", "4x NVIDIA A10G 96GB, 48 vCPU (Spot ~$3.67/hr - Blitz Mode)"),
    ("g4dn.12xlarge", "4x NVIDIA T4 64GB, 48 vCPU (Spot ~$1.53/hr)"),
    ("g5.4xlarge", "1x NVIDIA A10G 24GB, 16 vCPU (Spot ~$0.69/hr)"),
    ("g5.2xlarge", "1x NVIDIA A10G 24GB, 8 vCPU (Spot ~$0.54/hr)"),
    ("g5.xlarge", "1x NVIDIA A10G 24GB, 4 vCPU (Spot ~$0.52/hr)"),
]
IAM_PROFILE = "AmazonSSMRoleForInstancesQuickSetup"
S3_TARGET = "s3://model-weight/von-modernbert-rlcd"


USER_DATA_SCRIPT = """#!/bin/bash
set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# HARD RUNAWAY WATCHDOG: Self-terminate in 75 minutes max under any circumstances
shutdown -h +75 &

echo "=== [VON CLOUD TRAINING START] ==="
export DEBIAN_FRONTEND=noninteractive

# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/root/.local/bin:$PATH"

# Clone Von repository
git clone https://github.com/wfzyx/von.git /opt/von
cd /opt/von

# Setup environment
uv venv
source .venv/bin/activate
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
uv pip install transformers datasets scipy sentencepiece tiktoken accelerate awscli
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# Build operational decision training corpus (Phase 2)
python training/prepare_decision_dataset.py --max_train 65000 --val_samples 3000 --output_dir data_decision

# Detect GPUs and train with DDP
NUM_GPUS=$(nvidia-smi -L | wc -l)
echo "Detected $NUM_GPUS GPUs. Starting PyTorch DDP training..."

torchrun --nproc_per_node=$NUM_GPUS training/train_rlcd.py \
    --train_data data_decision/train.jsonl \
    --val_data data_decision/val.jsonl \
    --model_id wfzyx/von-1.0 \
    --epochs 1 \
    --batch_size 4 \
    --grad_accum_steps 4 \
    --s3_target s3://model-weight/von-modernbert-rlcd \
    --output_dir checkpoints/von-modernbert-rlcd

# Upload run logs for auditing
aws s3 cp /var/log/user-data.log s3://model-weight/von-modernbert-rlcd/run.log || true

echo "=== [VON TRAINING COMPLETE - TERMINATING INSTANCE] ==="
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
    print("  VON AWS SPOT TRAINING LAUNCHER")
    print("  Cluster Targets:  4x GPU (g4dn.12xlarge) / 1x GPU (g5.xlarge)")
    print(f"  Region:           {REGION}")
    print(f"  Safety Watchdog:  150-minute hard shutdown & auto-terminate")
    print(f"  Target S3 Prefix: {S3_TARGET}")
    print("================================================================\n")

    user_data_b64 = base64.b64encode(USER_DATA_SCRIPT.encode("utf-8")).decode("utf-8")

    instance_id = None
    chosen_type = None

    for inst_type, desc_str in CANDIDATE_TYPES:
        print(f"\nEvaluating instance type: {inst_type} [{desc_str}]...")
        for subnet_id, az_name in SUBNETS:
            print(f"  -> Trying {inst_type} in {az_name} ({subnet_id})...")
            launch_args = [
                "ec2", "run-instances",
                "--image-id", AMI_ID,
                "--instance-type", inst_type,
                "--subnet-id", subnet_id,
                "--iam-instance-profile", f"Name={IAM_PROFILE}",
                "--instance-initiated-shutdown-behavior", "terminate",
                "--instance-market-options", json.dumps({"MarketType": "spot", "SpotOptions": {"SpotInstanceType": "one-time"}}),
                "--block-device-mappings", json.dumps([
                    {
                        "DeviceName": "/dev/sda1",
                        "Ebs": {
                            "VolumeSize": 120,
                            "VolumeType": "gp3",
                            "DeleteOnTermination": True
                        }
                    }
                ]),
                "--tag-specifications", json.dumps([
                    {
                        "ResourceType": "instance",
                        "Tags": [{"Key": "Name", "Value": f"von-training-spot-{inst_type}"}]
                    }
                ]),
                "--user-data", user_data_b64,
            ]

            try:
                res = run_aws(launch_args)
                instances = res.get("Instances", [])
                if instances:
                    instance_id = instances[0]["InstanceId"]
                    chosen_type = inst_type
                    print(f"\n-> SUCCESS! Launched {inst_type} Spot instance in {az_name}: {instance_id}")
                    break
            except Exception as e:
                print(f"     Not available in {az_name}: {e}")

        if instance_id:
            break

    if not instance_id:
        print("\nAll Spot capacity temporarily exhausted in us-west-2.")
        print("Falling back to On-Demand g5.xlarge ($1.006/hr, ~$1.50 run cost, budget cap $10)...")
        for subnet_id, az_name in SUBNETS:
            print(f"  -> Trying On-Demand g5.xlarge in {az_name} ({subnet_id})...")
            launch_args = [
                "ec2", "run-instances",
                "--image-id", AMI_ID,
                "--instance-type", "g5.xlarge",
                "--subnet-id", subnet_id,
                "--iam-instance-profile", f"Name={IAM_PROFILE}",
                "--instance-initiated-shutdown-behavior", "terminate",
                "--block-device-mappings", json.dumps([
                    {
                        "DeviceName": "/dev/sda1",
                        "Ebs": {
                            "VolumeSize": 120,
                            "VolumeType": "gp3",
                            "DeleteOnTermination": True
                        }
                    }
                ]),
                "--tag-specifications", json.dumps([
                    {
                        "ResourceType": "instance",
                        "Tags": [{"Key": "Name", "Value": "von-training-ondemand-g5.xlarge"}]
                    }
                ]),
                "--user-data", user_data_b64,
            ]
            try:
                res = run_aws(launch_args)
                instances = res.get("Instances", [])
                if instances:
                    instance_id = instances[0]["InstanceId"]
                    chosen_type = "g5.xlarge (On-Demand)"
                    print(f"\n-> SUCCESS! Launched On-Demand g5.xlarge in {az_name}: {instance_id}")
                    break
            except Exception as e:
                print(f"     Failed in {az_name}: {e}")

    if not instance_id:
        raise RuntimeError("Could not find compute capacity in any availability zone!")

    print("\nWaiting for instance to enter 'running' state...")
    while True:
        desc = run_aws(["ec2", "describe-instances", "--instance-ids", instance_id])
        state = desc["Reservations"][0]["Instances"][0]["State"]["Name"]
        print(f"  -> Instance {instance_id} status: {state}")
        if state == "running":
            break
        if state in ("terminated", "shutting-down"):
            raise RuntimeError("Instance terminated prematurely!")
        time.sleep(15)

    print("\nSpot instance is RUNNING! Distributed training has started in background.")
    print(f"The instance will automatically upload checkpoints to {S3_TARGET} and terminate.\n")
    print("To monitor progress or download when done, run:")
    print(f'  "{AWS_CLI}" s3 ls {S3_TARGET}/')


if __name__ == "__main__":
    launch()
