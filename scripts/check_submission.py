#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check native guest execution and rejection of an ill-typed submission."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


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
    }, indent=2) + '\n')
    if not passed:
        raise SystemExit('Type-error rejection check failed; inspect build/submission-tests/')
    print('Native submission passed: real GHC, guest output, large Integer, OS effects, exception recovery.')
    print('Ill-typed submission rejected before boot; existing runtime image preserved.')


if __name__ == '__main__':
    main()
