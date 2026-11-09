# OpenJev-0.6B 权重镜像（GitHub 源码包分发版）

内网无法访问 Hugging Face 时的替代分发：权重拆成 <100MB 分块作为普通 git 文件，通过 GitHub 源码压缩包直接下载。

## 下载与重建
1. 本页面点 **Code → Download ZIP**（或 `https://github.com/heheebei-rgb/openjev-0.6b-mirror/archive/refs/heads/main.zip`）
2. 解压后在本目录执行: `python3 merge_and_verify.py`（自动合并分块 + sha256 校验，纯标准库）
3. 产物: `qwen3-0.6b/model.safetensors`（1.50GB 基座）+ `meta/adapter_model.safetensors`（LoRA 4.5MB）+ head + 配置

## 配套代码（内网可直接克隆 GitHub）
git clone https://github.com/IamBusy/OpenJev
推理示例见其 README（OpenJevModel.from_pretrained 支持本地目录）。
