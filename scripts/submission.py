#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile a trusted Haskell module on the host, then boot it inside House.

This linked-image checkpoint incrementally builds and reboots the guest for each submission.
It is not yet a live REPL or an untrusted-code sandbox.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import toolchain

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Module HouseSubmission with submission :: OS ()')
    parser.add_argument('--build-only', action='store_true')
    args = parser.parse_args()
    # Copy bytes, not shell arguments/source fragments, into the fixed build
    # input. All compiler invocation arguments are separate argv elements.
    data = args.source.read_bytes()
    output = ROOT / 'build/submission'
    output.mkdir(parents=True, exist_ok=True)
    staged = output / 'HouseSubmission.hs'
    if not staged.exists() or staged.read_bytes() != data:
        staged.write_bytes(data)
    kernel = output / 'kernel.elf'
    kernel.unlink(missing_ok=True)
    report = {'checkpoint': 'host-compiled-native-submission',
              'source_sha256': hashlib.sha256(data).hexdigest(),
              'entry': 'HouseSubmission.submission :: OS ()', 'target': 'IA32 native, static Multiboot ELF32',
              'build_image': toolchain.LOCK['image'], 'built': False, 'ran': False}
    try:
        toolchain.run(['sh', 'scripts/build-runtime.sh', '--submission'])
        shutil.copyfile(ROOT / 'build/runtime/kernel.elf', kernel)
        for name in ('dependencies.json', 'ghc-link-arguments.json', 'link-command.json'):
            shutil.copyfile(ROOT / 'build/runtime' / name, output / name)
        dependencies = json.loads((output / 'dependencies.json').read_text())
        report['guest_api_interfaces_sha256'] = dependencies['guest_api_interfaces_sha256']
        report.update(built=True, kernel_sha256=hashlib.sha256(kernel.read_bytes()).hexdigest())
        if not args.build_only:
            qemu = shutil.which('qemu-system-i386')
            if not qemu:
                raise SystemExit('qemu-system-i386 is required')
            command = [qemu, '-machine', 'pc-i440fx-11.1', '-accel', 'tcg,thread=single',
                       '-cpu', 'qemu32', '-smp', '1', '-m', '256', '-display', 'none',
                       '-monitor', 'none', '-serial', 'stdio', '-nic', 'none',
                       '-kernel', str(kernel), '-no-reboot',
                       '-device', 'isa-debug-exit,iobase=0xf4,iosize=0x04']
            report['command'] = command
            try:
                result = subprocess.run(command, input=b'', capture_output=True, timeout=30)
                stdout, stderr, code = result.stdout, result.stderr, result.returncode
            except subprocess.TimeoutExpired as error:
                stdout, stderr, code = error.stdout or b'', error.stderr or b'', None
            (output / 'serial.log').write_bytes(stdout)
            (output / 'qemu.log').write_bytes(stderr)
            passed = (code == 33 and b'Native Haskell submission completed\r\n' in stdout
                      and b'Haskell entry completed\r\n' in stdout
                      and b'PANIC' not in stdout and b'CPU FAULT' not in stdout)
            report.update(ran=True, qemu_exit_code=code, passed=passed)
            print(stdout.decode('utf-8', errors='replace'), end='')
            if not passed:
                print(stderr.decode('utf-8', errors='replace'), end='')
                raise SystemExit('Native guest submission failed; inspect build/submission/')
    finally:
        (output / 'run.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
