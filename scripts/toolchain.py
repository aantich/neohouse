#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fetch and run the pinned IA32 Linux compiler without changing host GHC."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "toolchain/lock.json").read_text())


def digest(path):
    with path.open("rb") as stream:
        result = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
        return result.hexdigest()


def fetch(component):
    item = LOCK[component]
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    destination = cache / item["filename"]
    partial = destination.with_name(destination.name + ".part")
    if destination.exists():
        if digest(destination) != item["sha256"]:
            raise SystemExit(f"Checksum mismatch: {destination}")
        print(f"Verified {destination.name}", flush=True)
        return
    if not partial.exists() or digest(partial) != item["sha256"]:
        subprocess.run([
            "curl", "--fail", "--location", "--retry", "3",
            "--continue-at", "-", "--output", str(partial), item["url"],
        ], check=True)
    if digest(partial) != item["sha256"]:
        raise SystemExit(f"Checksum mismatch: {partial}; refusing to install")
    partial.replace(destination)
    print(f"Verified {destination.name}", flush=True)


def run(arguments, *, interactive=False, image=None):
    command = ["docker", "run", "--rm", "--platform", LOCK["platform"],
               "--network", "none", "--mount",
               f"type=bind,source={ROOT},target=/work", "--workdir", "/work"]
    if interactive:
        command += ["-it"]
    subprocess.run(command + [image or LOCK["image"], *arguments], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    fetch_parser = sub.add_parser("fetch")
    fetch_parser.add_argument("--source", action="store_true")
    sub.add_parser("build")
    run_parser = sub.add_parser("run")
    run_parser.add_argument("-i", "--interactive", action="store_true")
    run_parser.add_argument("arguments", nargs=argparse.REMAINDER)
    sub.add_parser("hosted-check")
    args = parser.parse_args()

    if args.command == "fetch":
        fetch("source" if args.source else "compiler")
    elif args.command == "build":
        fetch("compiler")
        subprocess.run([
            "docker", "build", "--platform", LOCK["platform"],
            "--build-arg", f"BASE_IMAGE={LOCK['base_image']}",
            "--build-arg", f"DEBIAN_SNAPSHOT={LOCK['debian_snapshot']}",
            "--file", "toolchain/Dockerfile", "--tag", LOCK["image"], ".",
        ], cwd=ROOT, check=True)
    elif args.command == "run":
        arguments = args.arguments
        if arguments and arguments[0] == "--":
            arguments = arguments[1:]
        if not arguments:
            parser.error("run requires a command, for example: run -- ghc --info")
        run(arguments, interactive=args.interactive)
    else:
        run(["sh", "scripts/check-hosted.sh"])


if __name__ == "__main__":
    main()
