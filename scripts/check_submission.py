#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check native execution, incremental rebuilding and type-error rejection."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def build_products():
    output = ROOT / 'build/runtime'
    paths = {*output.rglob('*.o'), *output.rglob('*.a'),
             output / 'kernel.linked.elf', output / 'kernel.elf',
             ROOT / 'build/submission/HouseSubmission.hs'}
    return {str(p.relative_to(ROOT)): (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
            for p in sorted(paths) if p.is_file()}


def main():
    output = ROOT / 'build/submission-tests'
    output.mkdir(parents=True, exist_ok=True)
    good = subprocess.run([sys.executable, str(ROOT / 'scripts/submission.py'),
                           str(ROOT / 'examples/repl/HelloHouse.hs')], cwd=ROOT,
                          capture_output=True, timeout=600)
    (output / 'success.log').write_bytes(good.stdout + good.stderr)
    markers = [b'Hello from an ordinary Haskell module\r\n', b'\r\n42\r\n',
               b'[2,4,6,8,10]\r\n',
               b'1606938044258990275541962092341162602522202993782792835301376\r\n',
               b'MemoryInfo {heapBytes = ', b'Recovered: divide by zero',
               b'The guest is still running after that exception\r\n',
               b'Native Haskell submission completed\r\n']
    if good.returncode or any(m not in good.stdout for m in markers):
        raise SystemExit('Native submission check failed; inspect build/submission-tests/success.log')
    successful = json.loads((ROOT / 'build/submission/run.json').read_text())
    (output / 'success-run.json').write_text(json.dumps(successful, indent=2) + '\n')
    before_products = build_products()
    started = time.monotonic()
    warm = subprocess.run([sys.executable, str(ROOT / 'scripts/submission.py'),
                           str(ROOT / 'examples/repl/HelloHouse.hs')], cwd=ROOT,
                          capture_output=True, timeout=600)
    warm_seconds = time.monotonic() - started
    (output / 'unchanged.log').write_bytes(warm.stdout + warm.stderr)
    if (warm.returncode or build_products() != before_products
            or b'RTS: compiled 0; reused 138 C objects;' not in warm.stdout
            or b'Bootstrap: compiled 0; reused 11 C/assembly objects.' not in warm.stdout
            or b'Compiling ' in warm.stdout or b'Linking ' in warm.stdout):
        raise SystemExit('Unchanged submission rebuilt products or failed; inspect unchanged.log')
    changed = output / 'Changed.hs'
    old_marker = b'Hello from an ordinary Haskell module'
    new_marker = b'Hello from an incrementally changed module'
    changed.write_bytes((ROOT / 'examples/repl/HelloHouse.hs').read_bytes().replace(old_marker, new_marker))
    edited = subprocess.run([sys.executable, str(ROOT / 'scripts/submission.py'), str(changed)],
                            cwd=ROOT, capture_output=True, timeout=600)
    (output / 'changed.log').write_bytes(edited.stdout + edited.stderr)
    after_products = build_products()
    touched = sorted(p for p, value in after_products.items() if before_products.get(p) != value)
    allowed = {'build/submission/HouseSubmission.hs', 'build/runtime/HouseSubmission.o',
               'build/runtime/SubmissionRunner.o', 'build/runtime/HouseKernel.o',
               'build/runtime/kernel.elf', 'build/runtime/kernel.linked.elf'}
    changed_report = json.loads((ROOT / 'build/submission/run.json').read_text())
    if (edited.returncode or new_marker + b'\r\n' not in edited.stdout
            or changed_report['kernel_sha256'] == successful['kernel_sha256']
            or 'build/runtime/HouseSubmission.o' not in touched or set(touched) - allowed):
        raise SystemExit('Changed submission failed to rebuild incrementally; inspect changed.log')
    kernel = ROOT / 'build/runtime/kernel.elf'
    before = hashlib.sha256(kernel.read_bytes()).hexdigest()
    invalid = output / 'IllTyped.hs'
    invalid.write_text('module HouseSubmission (submission) where\nimport House\n'
                       'submission :: OS ()\nsubmission = printValue console (True + 1)\n')
    bad = subprocess.run([sys.executable, str(ROOT / 'scripts/submission.py'), str(invalid)],
                         cwd=ROOT, capture_output=True, timeout=600)
    diagnostic = bad.stdout + bad.stderr
    (output / 'type-error.log').write_bytes(diagnostic)
    rejected = json.loads((ROOT / 'build/submission/run.json').read_text())
    passed = (bad.returncode != 0 and b'Bool' in diagnostic and b'error:' in diagnostic
              and not rejected['built'] and not rejected['ran']
              and before == hashlib.sha256(kernel.read_bytes()).hexdigest())
    (output / 'run.json').write_text(json.dumps({
        'checkpoint': 'native-guest-submission-and-type-error', 'passed': passed,
        'successful_kernel_sha256': successful['kernel_sha256'],
        'qemu_exit_code': successful['qemu_exit_code'], 'type_error_rejected': passed,
        'unchanged_submission_rebuilt_nothing': True, 'unchanged_submission_seconds': warm_seconds,
        'changed_submission_products': touched,
    }, indent=2) + '\n')
    if not passed:
        raise SystemExit('Type-error rejection check failed; inspect build/submission-tests/')
    print('Native submission passed: real GHC, guest output, large Integer, OS effects, exception recovery.')
    print(f'Unchanged submission rebuilt nothing ({warm_seconds:.1f}s including audit and QEMU).')
    print('Changed submission ran new code; unrelated build products were reused.')
    print('Ill-typed submission rejected before boot; existing runtime image preserved.')


if __name__ == '__main__':
    main()
