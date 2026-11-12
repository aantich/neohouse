#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Boot the standalone native-Haskell allocation/GC checkpoint in QEMU."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import toolchain

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-build', action='store_true', help='Reuse the existing test image')
    parser.add_argument('--debug', action='store_true', help='Record QEMU instruction/fault tracing')
    args = parser.parse_args()
    if not args.no_build:
        toolchain.run(['sh', 'scripts/build-runtime.sh'])
    output = ROOT / 'build/runtime'
    kernel = output / 'kernel.elf'
    data = kernel.read_bytes()
    if not any(a == 0x1badb002 and (a + b + c) & 0xffffffff == 0
               for a, b, c in (struct.unpack_from('<III', data, i)
                               for i in range(0, min(len(data), 8192) - 11, 4))):
        raise SystemExit('Invalid or missing Multiboot header')
    qemu = shutil.which('qemu-system-i386')
    if not qemu:
        raise SystemExit('qemu-system-i386 is required')
    command = [qemu, '-machine', 'pc-i440fx-11.1', '-accel', 'tcg,thread=single',
               '-cpu', 'qemu32', '-smp', '1', '-m', '256', '-display', 'none',
               '-monitor', 'none', '-serial', 'stdio', '-nic', 'none',
               '-kernel', str(kernel), '-no-reboot',
               '-device', 'isa-debug-exit,iobase=0xf4,iosize=0x04']
    if args.debug:
        command += ['-d', 'in_asm,int', '-D', str(output / 'cpu.log')]
    timed_out = False
    try:
        result = subprocess.run(command, input=b'', capture_output=True, timeout=30)
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as error:
        stdout, stderr, code = error.stdout or b'', error.stderr or b'', None
        timed_out = True
    (output / 'serial.log').write_bytes(stdout)
    (output / 'qemu.log').write_bytes(stderr)
    counters = re.search(rb'GC checkpoint passed; collections=(\d+); allocated_bytes=(\d+)', stdout)
    library_passed = (b'Standalone Haskell library checkpoint passed; bignum_backend=native' in stdout
                      and b'Haskell exceptions passed:' in stdout and b'recovered=42' in stdout)
    passed = (code == 33 and counters is not None and int(counters[1]) >= 24
              and int(counters[2]) > 1000000 and b'Haskell entry completed' in stdout
              and library_passed
              and b'PANIC' not in stdout and b'CPU FAULT' not in stdout)
    (output / 'run.json').write_text(json.dumps({
        'checkpoint': 'standalone-native-haskell-gc',
        'build_image': toolchain.LOCK['image'], 'command': command,
        'kernel_sha256': hashlib.sha256(data).hexdigest(),
        'qemu_exit_code': code, 'timed_out': timed_out, 'passed': passed,
        'collections': int(counters[1]) if counters else None,
        'allocated_bytes': int(counters[2]) if counters else None,
        'library_passed': library_passed,
    }, indent=2) + '\n')
    print(stdout.decode('ascii', errors='replace'), end='')
    if not passed:
        print(stderr.decode('utf-8', errors='replace'), end='')
        raise SystemExit(f'Standalone runtime checkpoint failed (exit {code}); inspect {output}')
    print('Standalone native Haskell allocation/GC checkpoint passed.')


if __name__ == '__main__':
    main()
