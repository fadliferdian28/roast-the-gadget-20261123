#!/usr/bin/env python3
"""Validate the roast line and copy it to the make.fun output directory."""

import hashlib
import os
import shutil
import sys
from pathlib import Path


MAX_CHARACTERS = 200


def fail(message):
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def prepare_output_directory(path):
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        fail(f"cannot create output directory {path}: {exc}")

    if not path.is_dir():
        fail(f"output path is not a directory: {path}")
    if not os.access(path, os.W_OK | os.X_OK):
        fail(f"output directory is not writable: {path}")

    probe = path / f".makefun-write-check-{os.getpid()}"
    try:
        with probe.open("xb") as handle:
            handle.write(b"probe")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        fail(f"output directory is not writable: {path}: {exc}")
    finally:
        try:
            probe.unlink()
        except OSError:
            pass


def main():
    source = Path(__file__).resolve().parent / "entry.txt"
    output_root = Path(os.environ.get("MAKEFUN_OUTPUT_DIR") or "output")
    destination = output_root / "entry.txt"

    try:
        raw = source.read_bytes()
    except OSError as exc:
        fail(f"cannot read {source}: {exc}")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        fail(f"{source} is not valid UTF-8: {exc}")

    if not 1 <= len(text) <= MAX_CHARACTERS:
        fail(
            f"{source} must contain 1 to {MAX_CHARACTERS} characters; "
            f"found {len(text)}"
        )
    if not text.strip():
        fail(f"{source} must not contain only whitespace")

    source_digest = sha256(raw)

    prepare_output_directory(output_root)

    try:
        if destination.exists() and source.samefile(destination):
            fail(f"source and destination are the same file: {source}")
    except OSError as exc:
        fail(f"cannot compare {source} and {destination}: {exc}")

    try:
        shutil.copyfile(source, destination)
    except shutil.SameFileError:
        fail(f"source and destination are the same file: {source}")
    except OSError as exc:
        fail(f"cannot write {destination}: {exc}")

    try:
        copied = destination.read_bytes()
    except OSError as exc:
        fail(f"cannot read back {destination}: {exc}")

    copied_digest = sha256(copied)
    if copied_digest != source_digest:
        fail(
            "sha256 mismatch after copy: "
            f"source={source_digest} copied={copied_digest}"
        )

    print(f"wrote {destination}")
    print(f"characters: {len(text)}")
    print(f"sha256: {source_digest}")


if __name__ == "__main__":
    main()
