#!/usr/bin/env python3
"""
Sanitize repository copy for Phase4C project.
Creates `sanitized_repo/` with common secret patterns redacted.
"""
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'sanitized_repo'

RULES = [
    (re.compile(r'AKIA[0-9A-Z]{16}'), '[REDACTED_AWS_ACCESS_KEY_ID]'),
    (re.compile(r"(?i)(aws_secret_access_key\s*[:=]\s*)(['\"])?.{8,200}?\2"), r"\1'[REDACTED_AWS_SECRET_ACCESS_KEY]"),
    (re.compile(r"(?i)(\b(api_key|apikey|client_secret|client-secret|access_token|access-token|token|secret|password)\b\s*[:=]\s*)(['\"])?.{4,200}?\2"), r"\1'[REDACTED]"),
    (re.compile(r"`[A-Za-z0-9\-_/+=]{20,200}`"), '`[REDACTED_PRIVATE_KEY]`'),
    (re.compile(r'(Private Key \(WIF\):\s*).*$', re.IGNORECASE | re.MULTILINE), r'\1[REDACTED_PRIVATE_KEY]'),
    (re.compile(r'-----BEGIN ([A-Z ]*PRIVATE KEY)-----[\s\S]+?-----END \1-----'), '-----BEGIN \1-----\n[REDACTED_PRIVATE_KEY_BLOCK]\n-----END \1-----'),
]

SKIP_DIRS = {'.git', 'sanitized_repo', '__pycache__', '.venv', 'venv', 'env'}


def sanitize_text(text: str) -> str:
    out = text
    for pat, repl in RULES:
        try:
            out = pat.sub(repl, out)
        except re.error:
            continue
    return out


def should_process(path: Path) -> bool:
    if path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif', '.pyc', '.db', '.sqlite', '.exe'}:
        return False
    return True


def main() -> None:
    if OUT.exists():
        print(f"Removing existing sanitized output at: {OUT}")
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel_dir = Path(root).relative_to(ROOT)
        target_dir = OUT / rel_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        for fname in files:
            src_path = Path(root) / fname
            rel_path = src_path.relative_to(ROOT)
            dest_path = OUT / rel_path

            if not should_process(src_path):
                try:
                    shutil.copy2(src_path, dest_path)
                except Exception:
                    pass
                continue

            try:
                text = src_path.read_text(encoding='utf-8', errors='replace')
            except Exception:
                try:
                    shutil.copy2(src_path, dest_path)
                except Exception:
                    pass
                continue

            new_text = sanitize_text(text)
            dest_path.write_text(new_text, encoding='utf-8')

    print(f"Sanitized repository written to: {OUT}")


if __name__ == '__main__':
    main()
