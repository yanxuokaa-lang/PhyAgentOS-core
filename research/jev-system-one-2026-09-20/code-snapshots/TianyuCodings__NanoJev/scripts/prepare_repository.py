#!/usr/bin/env python3
"""Stage a new, explicitly curated NanoJev directory; no Git/network operations."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from package_source import (NANOJEV_COMPARISON, collect, json_bytes, provenance,
                            secret_paths, sha256, verify_ready, write_new)


PUBLIC_DOTFILES = {
    '.env.example': b'AI_GATEWAY_API_KEY=\n',
    '.gitignore': b'''# Local credentials and generated private data
.env
.env.*
!.env.example
node_modules/
.venv/
.cache/
__pycache__/
*.pyc
research/private*
research/claude_review_raw.json
research/claude_review_prompt.md
research/*_stderr.log
research/official_*
runs/
checkpoints/
weights/
data/
artifacts/
publish/
*.safetensors
*.pt
*.pth
.DS_Store
''',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error('Output must be a new directory; existing files are never replaced')
    payloads, manifest = collect(args.root.resolve(), require=NANOJEV_COMPARISON)
    verify_ready(manifest)
    payloads.update(PUBLIC_DOTFILES)
    hits = secret_paths(payloads)
    if hits:
        raise ValueError('Credential pattern in selected paths: ' + ', '.join(hits))
    oversized = [name for name, value in payloads.items() if len(value) >= 100 * 1024 * 1024]
    if oversized:
        raise ValueError('Files exceed the GitHub single-file limit: ' + ', '.join(oversized))
    manifest['operation'] = 'local_curated_repository_staging_no_network'
    manifest['project'] = 'NanoJev'
    manifest['created_at_utc'] = datetime.now(timezone.utc).isoformat()
    manifest['file_count'] = len(payloads)
    manifest['total_bytes'] = sum(map(len, payloads.values()))
    manifest['files'] = []
    for name, value in sorted(payloads.items()):
        category, origin, license_scope = provenance(name)
        if name in PUBLIC_DOTFILES:
            category, origin, license_scope = ('authored_configuration', 'Literal public defaults; never copied from credentials', 'MIT')
        manifest['files'].append({'path': name, 'bytes': len(value), 'sha256': sha256(value),
                                  'category': category, 'provenance': origin, 'license_scope': license_scope})
    for name, value in sorted(payloads.items()):
        write_new(args.output / name, value)
    write_new(args.output / 'SOURCE_MANIFEST.json', json_bytes(manifest))
    for name, value in payloads.items():
        if (args.output / name).read_bytes() != value:
            raise ValueError('Staging byte mismatch: ' + name)
    print(json.dumps({'output': str(args.output), 'files': len(payloads) + 1,
                      'bytes': manifest['total_bytes'], 'credential_match_paths': hits,
                      'network_calls': 0, 'weights_included': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
