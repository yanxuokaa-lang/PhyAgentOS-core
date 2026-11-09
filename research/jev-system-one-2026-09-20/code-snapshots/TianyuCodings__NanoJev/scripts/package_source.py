#!/usr/bin/env python3
"""Create a local, curated source ZIP. Default: preview only; never publish.

Only scripts/*.py and scripts/*.mjs are enumerated. Everything else is an
explicit allowlist. No .env, research-directory glob, teacher label, model
weight, dependency installation, subprocess or network access is used.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import zipfile


REQUIRED = (
    "README.md", "README.en.md", "README.zh-CN.md", "LICENSE", "package.json", "package-lock.json", "requirements-toy.txt",
    "scripts/package_source.py", "research/release_scope_zh.md",
    "web/README.md", "web/index.html", "web/app.js", "web/style.css", "web/demo_results.json",
)
PUBLIC_REPORTS = (
    "research/implementation_plan_zh.md", "research/replication_plan_zh.md",
    "research/jev_public_sources_zh.md", "research/core_features_rlcd_zh.md",
    "research/query_distribution_zh.md", "research/training_design_zh.md",
    "research/rlcd_public_discussion_zh.md", "research/rlcd_theory_zh.md",
    "research/algorithm_architecture_audit_zh.md", "research/algorithm_fable_decisions_zh.md",
    "research/algorithm_training_contract_zh.md", "research/jevlike_repo_audit_zh.md",
    "research/openjev_repo_audit_zh.md", "research/toy_experiment_report_zh.md",
    "research/toy_teacher_audit_zh.md", "research/qwen_tree_check_zh.md",
    "research/trained_invariance_timing_zh.md", "research/distribution_probe_summary_zh.md",
    "research/student_distribution_probe_brief_zh.md", "research/probability_semantics_zh.md",
    "research/game_dataset_zh.md", "research/game_fable_review_zh.md",
    "research/navigation_failure_fable_zh.md", "research/pipeline_v2_protocol_zh.md",
    "research/pipeline_v2_report_zh.md", "research/pipeline_rollout_audit_zh.md",
    "research/web_reader_review_zh.md", "research/navigation_v3_source_audit_zh.md",
    "research/pipeline_runbook_zh.md",
    "research/pipeline_runbook.md",
    "research/navigation_v3_protocol_zh.md",
    "research/navigation_v3_regression_zh.md",
)
PUBLIC_RESULTS = (
    "research/toy_inference_example.json", "research/toy_results/summary.json",
    "research/toy_results/run_manifest.json", "research/toy_results/environment_freeze.txt",
    "research/tree_attention_check.json", "research/rlcd_algebra_check.json",
    "research/qwen_tree_check.json", "research/trained_invariance_timing.json",
    "research/dynamic_candidates_check.json", "research/dynamic_candidates_v2.json",
    "research/server_contract_check.json", "research/live_service_check_v2.json",
    "research/parallel_example_v2.json", "research/pipeline_v2_summary.json",
    "research/workflow_manifest_v2.json", "research/navigation_v3_input_audit.json",
    "research/navigation_v3_source_audit.json", "research/distribution_probe_inputs.json",
    "research/student_distribution_probe_summary.json", "research/toy_teacher_audit.json",
    "research/web_empty_browser_check.json",
    "research/web_live_browser_check.json", "research/web_live_browser_response.json",
    "research/source_gold_reproduction_check.json",
    "research/pipeline_runbook_check.json",
    "research/budget_summary.json",
    "research/live_service_check_v3.json", "research/parallel_example_v3.json",
    "research/navigation_v3_regression.json", "research/navigation_v3_training_manifest.json",
    "research/web_v3_live_browser_check.json",
    "research/web_v3_live_browser_response.json",
)
SCREENSHOTS: tuple[str, ...] = ()
# Current comparison images are listed below; historical local UI captures
# retain their original display labels and are not part of this release.

# Explicitly reviewed final results, including all actual V3 student/control traces.
# These contain student/program outputs, not raw Jev teacher-label responses.
FINAL_V3_RESULTS: tuple[str, ...] = (
    "research/navigation_v3_report_zh.md", "research/navigation_v3_summary.json",
    "research/navigation_v3_v3_gold_ascii_single_seed17_greedy.json",
    "research/navigation_v3_v3_gold_ascii_single_seed17_sample.json",
    "research/navigation_v3_v3_gold_ascii_multi_seed17_greedy.json",
    "research/navigation_v3_v3_gold_ascii_multi_seed17_sample.json",
    "research/navigation_v3_v3_gold_coords_single_seed17_greedy.json",
    "research/navigation_v3_v3_gold_coords_single_seed17_sample.json",
    "research/navigation_v3_v3_gold_coords_multi_seed17_greedy.json",
    "research/navigation_v3_v3_gold_coords_multi_seed17_sample.json",
    "research/navigation_v3_v3_teacher_coords_multi_seed17_greedy.json",
    "research/navigation_v3_v3_teacher_coords_multi_seed17_sample.json",
    "research/navigation_v3_random.json", "research/navigation_v3_oracle.json",
)

# Fresh, self-authored evaluation environments and actual three-system outputs.
# This explicit exception includes the minimal Jev evaluation receipts, never
# historical training labels or the private provider/credential envelope.
NANOJEV_COMPARISON = (
    "research/nanojev_comparison_protocol_zh.md",
    "research/nanojev_showcase_selection.json", "research/nanojev_showcase.md",
    "research/nanojev_comparison_zh.md",
    "research/nanojev_comparison_cohort.json",
    "research/nanojev_comparison_api_receipts.jsonl",
    "research/release_content_check.json",
    "research/nanojev_comparison_verification.json",
    "research/nanojev_comparison_public.json",
    "research/navigation_v3_native_qwen_zh.md",
    "research/navigation_v3_native_qwen_preflight.json",
    "research/navigation_v3_native_qwen_summary.json",
    "research/navigation_v3_native_qwen_audit.json",
    "research/navigation_v3_native_qwen_greedy.json",
    "research/navigation_v3_native_qwen_sample.json",
    "research/navigation_v3_jev_api_greedy.json",
    "research/navigation_v3_jev_api_sample.json",
    "web/comparison.html", "web/comparison.js", "web/comparison.css",
    "web/comparison_results.json",
    "assets/comparison_greedy.mp4", "assets/comparison_sample.mp4",
    "assets/comparison_greedy.gif", "assets/comparison_sample.gif",
    "assets/comparison_greedy.png", "assets/comparison_sample.png",
    "assets/comparison_media_manifest.json", "assets/comparison_playback_check.json",
)

EXCLUDED_NAMES = {
    "claude_review_raw.json", "claude_review_prompt.md", "claude_review_stderr.log",
    "docs_index.txt", "gateway_models.txt", "open_teacher_gateway_models.json",
}
WEIGHT_SUFFIXES = {".safetensors", ".pt", ".pth", ".bin", ".ckpt", ".gguf", ".onnx"}
SECRET_PATTERNS = tuple(re.compile(pattern) for pattern in (
    rb"\bAKIA[A-Z0-9]{16}\b",
    rb"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b",
    rb"\bgithub_pat_[A-Za-z0-9_]{30,}\b",
    rb"\bhf_[A-Za-z0-9]{20,}\b",
    rb"\bsk-[A-Za-z0-9_-]{20,}\b",
    rb"\bAIza[A-Za-z0-9_-]{30,}\b",
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    rb"\bBearer[ \t]+[A-Za-z0-9_-]{20,}(?:\.[A-Za-z0-9_-]+)*",
    rb"(?im)^[ \t]*(?:[\"']?)(?:AI_GATEWAY_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|AWS_SECRET_ACCESS_KEY|GITHUB_TOKEN)(?:[\"']?)[ \t]*[:=][ \t]*[\"']?[A-Za-z0-9_./+~-]{20,}",
))
TEXT_SUFFIXES = {".py", ".mjs", ".js", ".json", ".jsonl", ".md", ".txt", ".html", ".css"}


class PackageError(Exception):
    """Messages contain paths/reasons only, never credential match contents."""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def safe_relative(name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or "\\" in name or any(x in {"", ".", ".."} for x in name.split("/")):
        raise PackageError(f"不安全的相对路径：{name}")
    for part in p.parts:
        low = part.lower()
        if low.startswith((".", "private", "official_")) or low in {"node_modules", "__pycache__", "runs", "checkpoints", "weights"}:
            raise PackageError(f"拒绝纳入路径：{name}")
    if p.name in EXCLUDED_NAMES or p.suffix.lower() in WEIGHT_SUFFIXES:
        raise PackageError(f"拒绝纳入路径：{name}")
    return name


def check_source(root, name):
    safe_relative(name)
    current = root
    for part in PurePosixPath(name).parts:
        current = current / part
        if current.is_symlink():
            raise PackageError(f"拒绝符号链接：{name}")
    if current.exists() and not current.is_file():
        raise PackageError(f"不是普通文件：{name}")
    return current


def secret_paths(payloads):
    # Return filenames only. Do not retain or print matched secret values.
    return sorted(name for name, data in payloads.items()
                  if any(pattern.search(data) for pattern in SECRET_PATTERNS))


def provenance(name):
    if name == "LICENSE":
        return "license", "项目已有 MIT 许可文本，未修改", "MIT"
    if name in {"package.json", "package-lock.json", "requirements-toy.txt"}:
        return "dependency_specification", "项目依赖声明/锁定信息；不包含第三方依赖实现", "MIT; dependencies retain their own licenses"
    if name.startswith("scripts/") or (name.startswith("web/") and PurePosixPath(name).suffix in {".js", ".css", ".html"}):
        return "authored_source", "本项目自写实现；参考来源在研究报告中说明", "MIT"
    if name in NANOJEV_COMPARISON and not name.endswith(".md"):
        return "three_system_evaluation_evidence", "自写环境上的真实三方评测、最小Jev测评响应及其可视化；不含私有教师训练标签或供应商账户envelope", "authored environment data/code: CC0-1.0/MIT; external model outputs/marks retain applicable rights"
    if name == "research/distribution_probe_inputs.json" or name == "research/toy_inference_example.json":
        return "authored_programmatic_data", "本项目自写问题、状态或程序参考分布；不包含教师响应", "CC0-1.0"
    if name == "web/demo_results.json":
        return "student_and_program_replays", "真实学生推理和程序基线回放；源权重 SHA/运行元数据由 artifact 自身记录", "authored environment data: CC0-1.0; no model-weight license grant"
    if name in FINAL_V3_RESULTS and name.endswith(("_greedy.json", "_sample.json", "_random.json", "_oracle.json")):
        return "student_and_program_replays", "实际V3逐步闭环记录；teacher命名指训练后学生的训练目标，不是Jev原始标签", "authored environment data: CC0-1.0; no model-weight license grant"
    if name.startswith("research/web_screenshots/"):
        return "local_browser_evidence", "隔离本机 Chrome 捕获本项目真实页面，不是第三方网站快照", "project-authored screenshot; external names/marks retain their rights"
    if PurePosixPath(name).suffix == ".md":
        return "authored_documentation", "项目自写说明/分析；外部来源及摘引不主张项目所有权，私有原文不随包提供", "MIT for authored text; third-party material retains its rights"
    return "derived_experiment_evidence", "项目生成的聚合指标、检查证据或学生输出；不是教师原始响应/训练标签快照", "authored program data: CC0-1.0; third-party rights and weight licenses unaffected"


def selected_names(root):
    script_dir = root / "scripts"
    if script_dir.is_symlink():
        raise PackageError("拒绝符号链接：scripts")
    scripts = []
    if script_dir.is_dir():
        # This is the only directory enumeration: top-level authored source files.
        scripts = [p.relative_to(root).as_posix() for p in script_dir.iterdir()
                   if p.suffix in {".py", ".mjs"} and not p.name.startswith((".", "private"))]
    return sorted(set(REQUIRED + PUBLIC_REPORTS + PUBLIC_RESULTS + SCREENSHOTS + FINAL_V3_RESULTS + NANOJEV_COMPARISON + tuple(scripts)))


def unavailable_links(payloads):
    """List unresolved local Markdown links without following or opening them."""
    links = set()
    for name, data in payloads.items():
        if not name.endswith(".md"):
            continue
        for raw in re.findall(r"\]\(([^)]+)\)", data.decode("utf-8")):
            target = raw.strip().strip("<>").split("#", 1)[0]
            if not target or "://" in target or target.startswith(("mailto:", "data:")):
                continue
            # Keep only local link paths; do not resolve/read the destination.
            candidate = str(PurePosixPath(name).parent / target)
            parts = []
            for part in PurePosixPath(candidate).parts:
                if part == ".." and parts:
                    parts.pop()
                elif part != ".":
                    parts.append(part)
            resolved = "/".join(parts)
            if resolved not in payloads:
                links.add((name, target))
    return [{"document": a, "target_not_in_package": b} for a, b in sorted(links)]


def collect(root, require=()):
    names = selected_names(root)
    requested = set(require)
    for name in requested:
        safe_relative(name)
        if name not in names:
            raise PackageError(f"--require 不允许扩展清单，请先审阅并修改固定清单：{name}")
    payloads, missing = {}, []
    for name in names:
        path = check_source(root, name)
        if not path.exists():
            missing.append(name)
        else:
            payloads[name] = path.read_bytes()
    hits = secret_paths(payloads)
    manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "operation": "local_source_package_only_not_published",
        "file_count": len(payloads),
        "total_bytes": sum(map(len, payloads.values())),
        "files": [],
        "missing_required": sorted(set(missing) & (set(REQUIRED) | requested)),
        "missing_optional_allowlisted": sorted(set(missing) - (set(REQUIRED) | requested)),
        "secret_scan": {"credential_patterns_found_in_paths": hits, "prints_secret_values": False,
                        "limitation": "启发式样式扫描不证明不存在任意形式的凭据；固定路径清单与逐项来源记录另行限制范围"},
        "excluded_categories": [".env/credentials", "private research/Claude originals", "official/source snapshots",
                                "private teacher training responses and labels (explicit fresh evaluation receipts are included)", "model/tokenizer/checkpoints",
                                "node_modules/venv/cache", "unlisted research files"],
        "not_included_dependencies_or_artifacts": [
            "Python/CUDA/Node runtimes and installed packages; declarations only",
            "base model/tokenizer and local trained checkpoints",
            "historical frozen private teacher labels and exact train/optimizer snapshots",
            "private per-question prediction/run files needed to recompute all historical offline aggregates",
            "SSH hosts, API credentials, browser automation dependencies",
        ],
        "reproduction_limits": [
            "静态 web 回放可直接读取包内真实 demo_results.json；实时推理需包外兼容 checkpoint 与运行依赖。",
            "自写生成器可重建程序监督数据并运行 gold_distribution；这不等于重现已记录的教师或 warm-start V3 权重。",
            "教师实验复现需本机已冻结私有标签或用户自行重新标注；重新请求可能产生不同输出。",
            "文档保留历史协议/费用/失败边界；日期不同的实验报告不是同一配方。",
        ],
        "model_provenance": {
            "base_id": "Qwen/Qwen3-0.6B",
            "base_revision_recorded_in_README": "c1899de289a04d12100db370d81485cdf75e47ca",
            "source": "https://huggingface.co/Qwen/Qwen3-0.6B",
            "basis": "项目 README 与训练 artifact；本打包步骤不联网重新验证模型许可",
            "weights_included": False,
            "code_license_does_not_relicense_base_or_checkpoints": True,
        },
        "unavailable_local_document_links": unavailable_links(payloads),
    }
    for name, data in payloads.items():
        category, origin, license_scope = provenance(name)
        manifest["files"].append({"path": name, "bytes": len(data), "sha256": sha256(data),
                                  "category": category, "provenance": origin, "license_scope": license_scope})
    return payloads, manifest


def verify_ready(manifest):
    if manifest["secret_scan"]["credential_patterns_found_in_paths"]:
        raise PackageError("凭据样式命中，拒绝打包。路径：" + ", ".join(manifest["secret_scan"]["credential_patterns_found_in_paths"]))
    if manifest["missing_required"]:
        raise PackageError("缺少必需文件，拒绝打包。路径：" + ", ".join(manifest["missing_required"]))


def json_bytes(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def archive_bytes(payloads, manifest):
    verify_ready(manifest)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for name, data in list(payloads.items()) + [("SOURCE_MANIFEST.json", json_bytes(manifest))]:
            info = zipfile.ZipInfo("nanojev-source/" + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            zf.writestr(info, data)
    result = stream.getvalue()
    with zipfile.ZipFile(io.BytesIO(result)) as zf:
        if zf.testzip() is not None or set(zf.namelist()) != {"nanojev-source/" + n for n in payloads} | {"nanojev-source/SOURCE_MANIFEST.json"}:
            raise PackageError("生成 ZIP 的文件集合或 CRC 验证失败")
        for name, data in payloads.items():
            if sha256(zf.read("nanojev-source/" + name)) != sha256(data):
                raise PackageError(f"生成 ZIP 的 SHA256 验证失败：{name}")
    return result


def write_new(path, data):
    # Never overwrite a source, ongoing artifact or existing package.
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise PackageError(f"目标已存在，拒绝覆盖：{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(data)
    except FileExistsError as exc:
        raise PackageError(f"目标已存在，拒绝覆盖：{path}") from exc


def self_test():
    with tempfile.TemporaryDirectory(prefix="nanojev-package-test-") as directory:
        root = Path(directory)
        for name in REQUIRED:
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("{}\n" if name.endswith(".json") else "fixture\n")
        (root / ".env").write_text("DO_NOT_READ\n")
        (root / "research/private_teacher.json").write_text("DO_NOT_READ\n")
        (root / "research/official_api.md").write_text("DO_NOT_READ\n")
        (root / "scripts/extra.py").write_text("pass\n")
        payloads, manifest = collect(root)
        assert "scripts/extra.py" in payloads and not any("DO_NOT_READ" in x.decode() for x in payloads.values())
        assert not manifest["missing_required"] and manifest["missing_optional_allowlisted"]
        archive = archive_bytes(payloads, manifest)
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            actual = json.loads(zf.read("nanojev-source/SOURCE_MANIFEST.json"))
            assert actual["files"] == manifest["files"]
        secret = ("sk-" + "x" * 30).encode()
        assert secret_paths({"scripts/example.py": secret}) == ["scripts/example.py"]
        (root / "scripts/example.py").write_bytes(secret)
        _, blocked = collect(root)
        try:
            verify_ready(blocked)
        except PackageError as exc:
            assert secret.decode() not in str(exc) and "scripts/example.py" in str(exc)
        else:
            raise AssertionError("Credential pattern did not block build")
        (root / "scripts/example.py").unlink()
        (root / "scripts/link.py").symlink_to(root / ".env")
        try:
            collect(root)
        except PackageError:
            pass
        else:
            raise AssertionError("Symlink was accepted")
        (root / "scripts/link.py").unlink()
        for name in ("../escape", ".env", "research/private_a.json", "research/official_api.md", "x/model.safetensors"):
            try:
                safe_relative(name)
            except PackageError:
                pass
            else:
                raise AssertionError("Forbidden path was accepted")
        try:
            collect(root, require=("research/not_allowlisted.json",))
        except PackageError:
            pass
        else:
            raise AssertionError("--require expanded the allowlist")
        (root / "LICENSE").unlink()
        _, missing = collect(root)
        assert missing["missing_required"] == ["LICENSE"]
        output = root / "test.zip"
        write_new(output, archive)
        try:
            write_new(output, b"replacement")
        except PackageError:
            assert output.read_bytes() == archive
        else:
            raise AssertionError("Existing output overwritten")
    return {"self_test": "passed", "checks": ["strict curated file set", "manifest hashes and ZIP contents",
            "credential output redaction and build rejection", "symlink/private/weight rejection",
            "require cannot add files", "required/optional missing files", "existing output never overwritten"],
            "network_calls": 0, "real_archive_created": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--build", action="store_true", help="Write local source ZIP; never uploads or publishes")
    parser.add_argument("--output", type=Path, help="New ZIP path; required with --build, never overwritten")
    parser.add_argument("--manifest-output", type=Path, help="Optionally save this preview/build manifest to a NEW file")
    parser.add_argument("--require", action="append", default=[], help="Make an already allowlisted path required")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False))
        return
    if args.build != (args.output is not None):
        parser.error("--build 和 --output 必须同时指定；默认只预览")
    payloads, manifest = collect(args.root.resolve(), args.require)
    verify_ready(manifest)
    report = {"mode": "build" if args.build else "preview", "published": False,
              "file_count": manifest["file_count"], "total_bytes": manifest["total_bytes"],
              "categories": dict(Counter(f["category"] for f in manifest["files"])),
              "missing_required": manifest["missing_required"],
              "missing_optional_allowlisted": manifest["missing_optional_allowlisted"],
              "credential_match_paths": manifest["secret_scan"]["credential_patterns_found_in_paths"],
              "unavailable_local_document_link_count": len(manifest["unavailable_local_document_links"]),
              "selected_paths": list(payloads)}
    if args.build:
        data = archive_bytes(payloads, manifest)
        write_new(args.output, data)
        report.update(output=str(args.output), zip_bytes=len(data), zip_sha256=sha256(data))
    if args.manifest_output:
        write_new(args.manifest_output, json_bytes(manifest))
        report["manifest_output"] = str(args.manifest_output)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (PackageError, OSError, ValueError) as exc:
        # Standard exceptions here contain filenames/structural reasons only.
        print(json.dumps({"error": str(exc), "published": False}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
