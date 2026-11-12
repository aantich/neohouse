#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise native cache invalidation using disposable inputs inside /work."""
import hashlib
import json
from pathlib import Path
import runpy
import tempfile


def main():
    compile_native = runpy.run_path('scripts/build-runtime.py')['compile_native']
    output = Path('build/native-cache-tests')
    output.mkdir(parents=True, exist_ok=True)
    passed = []
    with tempfile.TemporaryDirectory(dir=output) as directory:
        root = Path(directory)
        source, header, target = root / 'answer.c', root / 'answer.h', root / 'answer.o'
        header.write_text('#define ANSWER 41\n')
        source.write_text('#include "answer.h"\nint answer(void) { return ANSWER; }\n')
        flags, compiler = ['-m32', '-O2'], {'test': 'pinned compiler'}

        def check(name, expected):
            if compile_native(source, target, flags, compiler) != expected:
                raise SystemExit(f'Native cache check failed: {name}')
            passed.append(name)

        check('first compilation', True)
        before = target.stat().st_mtime_ns
        check('unchanged input reuse', False)
        assert target.stat().st_mtime_ns == before
        old_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        header.write_text('#define ANSWER 42\n')
        check('included header change', True)
        assert hashlib.sha256(target.read_bytes()).hexdigest() != old_hash
        source.write_text('#include "answer.h"\nint answer(void) { return ANSWER + 1; }\n')
        check('source change', True)
        flags.append('-DANOTHER_BUILD_FLAG=1')
        check('compiler flag change', True)
        compiler = {'test': 'different compiler identity'}
        check('compiler identity change', True)
        target.write_bytes(b'invalid object')
        check('damaged output repair', True)
        target.unlink()
        check('missing output repair', True)
        check('repaired output reuse', False)
    (output / 'run.json').write_text(json.dumps({'passed': True, 'checks': passed}, indent=2) + '\n')
    print(f'Native object cache passed {len(passed)} checks, including header and flag invalidation.')


if __name__ == '__main__':
    main()
