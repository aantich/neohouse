#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build and boot the platform-only serial checkpoint (no Haskell RTS yet)."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess

import toolchain

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-image", default=toolchain.LOCK["image"],
                        help="Builder image; the dependencies-only image also suffices")
    args = parser.parse_args()
    qemu = shutil.which("qemu-system-i386")
    if qemu is None:
        raise SystemExit("qemu-system-i386 is required on the host")
    toolchain.run(["sh", "scripts/build-serial.sh"], image=args.build_image)
    output = ROOT / "build/serial"
    kernel = output / "kernel.elf"
    data = kernel.read_bytes()
    valid_header = any(
        magic == 0x1BADB002 and (magic + flags + checksum) & 0xFFFFFFFF == 0
        for magic, flags, checksum in
        (struct.unpack_from("<III", data, i) for i in range(0, min(8192, len(data)) - 11, 4))
    )
    if not valid_header:
        raise SystemExit("Valid aligned Multiboot header missing from first 8192 bytes")
    command = [
        qemu, "-machine", "pc-i440fx-11.1", "-accel", "tcg,thread=single",
        "-cpu", "qemu32", "-smp", "1", "-m", "256", "-display", "none",
        "-monitor", "none", "-serial", "stdio", "-nic", "none",
        "-kernel", str(kernel), "-no-reboot",
        "-device", "isa-debug-exit,iobase=0xf4,iosize=0x04",
    ]
    timed_out = False
    try:
        result = subprocess.run(command, input=b"", capture_output=True, timeout=15)
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as error:
        stdout, stderr, code = error.stdout or b"", error.stderr or b"", None
        timed_out = True
    (output / "serial.log").write_bytes(stdout)
    (output / "qemu.log").write_bytes(stderr)
    passed = code == 33 and b"IA32 entry and COM1 serial OK" in stdout
    (output / "run.json").write_text(json.dumps({
        "checkpoint": "platform-serial-only",
        "build_image": args.build_image,
        "haskell_rts_started": False,
        "command": command,
        "kernel_sha256": hashlib.sha256(data).hexdigest(),
        "qemu_exit_code": code,
        "timed_out": timed_out,
        "passed": passed,
    }, indent=2) + "\n")
    print(stdout.decode("ascii", errors="replace"), end="")
    if not passed:
        raise SystemExit(f"Serial platform checkpoint failed; inspect {output}")
    print("Platform serial checkpoint passed (Haskell boot remains pending).")


if __name__ == "__main__":
    main()
