#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run House's Haskell character terminal in the current host terminal."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import toolchain

ROOT = Path(__file__).resolve().parents[1]


def command():
    qemu = shutil.which('qemu-system-i386')
    if not qemu:
        raise SystemExit('qemu-system-i386 is required')
    return [qemu, '-machine', 'pc-i440fx-11.1', '-accel', 'tcg,thread=single',
            '-cpu', 'qemu32', '-smp', '1', '-m', '256', '-display', 'none',
            '-monitor', 'none', '-chardev', 'stdio,id=console,signal=off',
            '-serial', 'chardev:console', '-nic', 'none',
            '-kernel', str(ROOT / 'build/runtime/kernel.elf'),
            '-append', 'house.shell=1', '-no-reboot',
            '-device', 'isa-debug-exit,iobase=0xf4,iosize=0x04']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-build', action='store_true')
    args = parser.parse_args()
    if not sys.stdin.isatty():
        raise SystemExit('Run this script in a normal interactive terminal')
    if not args.no_build:
        toolchain.run(['sh', 'scripts/build-runtime.sh'])
    result = subprocess.run(command())
    raise SystemExit(0 if result.returncode == 33 else result.returncode)


if __name__ == '__main__':
    main()
