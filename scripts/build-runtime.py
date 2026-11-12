#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Incremental builder for the pinned, freestanding House runtime (in /work)."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess

OUT = Path('build/runtime')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_state(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return {}


def compile_native(source, target, flags, compiler):
    dependencies = target.with_suffix('.d')
    state = target.with_suffix('.build.json')
    command = ['gcc', *flags, '-MD', '-MF', str(dependencies),
               '-c', str(source), '-o', str(target)]
    previous = read_state(state)
    inputs = previous.get('inputs_sha256', {})
    if (previous.get('command') == command and previous.get('compiler') == compiler
            and inputs and target.exists() and previous.get('object_sha256') == digest(target)
            and all(Path(p).exists() and digest(Path(p)) == h for p, h in inputs.items())):
        return False
    # Invalidate the stamp first so an interrupted/failed compiler cannot leave
    # a partially written object looking valid on the next invocation.
    state.unlink(missing_ok=True)
    subprocess.run(command, check=True)
    paths = shlex.split(dependencies.read_text().replace('\\\n', '').split(':', 1)[1])
    state.write_text(json.dumps({
        'command': command, 'compiler': compiler,
        'inputs_sha256': {p: digest(Path(p)) for p in paths},
        'object_sha256': digest(target),
    }, indent=2) + '\n')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--submission', action='store_true')
    args = parser.parse_args()
    if args.submission and not Path('build/submission/HouseSubmission.hs').is_file():
        parser.error('Missing build/submission/HouseSubmission.hs')
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run(['python3', 'scripts/rebuild-rts.py'], check=True)
    subprocess.run(['python3', 'scripts/rebuild-libraries.py'], check=True)
    include = subprocess.check_output(
        ['ghc-pkg', 'field', 'rts', 'include-dirs', '--simple-output'], text=True).strip()
    source = Path('.cache/ghc-9.14.1')
    compiler = {
        'gcc': subprocess.check_output(['gcc', '--version'], text=True),
        'lock_sha256': digest(Path('toolchain/lock.json')),
    }
    flags = ['-m32', '-O2', '-Wall', '-Wextra', '-Werror', '-ffreestanding', '-fno-pie',
             '-fno-stack-protector', '-ffunction-sections', '-fdata-sections', '-DCOMPILING_RTS',
             '-I' + include, '-I' + str(source / 'rts'),
             '-I' + str(source / 'libraries/ghc-internal/include'),
             '-I' + str(source / 'libraries/ghc-internal/cbits')]
    units = [
        (Path('bootstrap/serial/start.S'), OUT / 'start.o',
         ['-m32', '-ffreestanding', '-fno-pie', '-DHOUSE_RUNTIME']),
        (Path('bootstrap/runtime/faults.S'), OUT / 'fault_vectors.o', ['-m32']),
        *[(Path(f'bootstrap/runtime/{unit}.c'), OUT / f'{unit}.o', flags)
          for unit in ('entry', 'startup', 'iface', 'memory', 'clock', 'features',
                       'minic', 'faults', 'support_check')],
    ]
    rebuilt = sum(compile_native(src, obj, options, compiler) for src, obj, options in units)
    print(f'Bootstrap: compiled {rebuilt}; reused {len(units) - rebuilt} C/assembly objects.', flush=True)
    # GHC does not see the archive substituted by link-runtime.py, or changes
    # to that adapter/linker script. Invalidate only its intermediate linked
    # image when these inputs change; keep kernel.elf intact on compile failure.
    linked = OUT / 'kernel.linked.elf'
    command = ['ghc', '--make', '-fasm', '-O1', '-Wall', '-Werror', '-static', '-no-hs-main',
               '-package-db', str(OUT / 'library/package.conf.d')]
    if args.submission:
        command += ['-DHOUSE_SUBMISSION', '-ibuild/submission']
    command += ['-pgml', '/work/scripts/link-runtime.py', '-outputdir', str(OUT),
                '-ibootstrap/runtime', 'bootstrap/runtime/HouseKernel.hs',
                *[str(OUT / f'{unit}.o') for unit in (
                    'start', 'entry', 'startup', 'iface', 'memory', 'clock', 'features',
                    'minic', 'faults', 'fault_vectors', 'support_check')], '-o', str(linked)]
    link_inputs = [*(obj for _, obj, _ in units), OUT / 'libhouse-rts.a',
                   OUT / 'library/build.json', Path('scripts/link-runtime.py'),
                   Path('bootstrap/runtime/link.ld'), Path('toolchain/lock.json')]
    context = {'command': command, 'inputs_sha256': {str(p): digest(p) for p in link_inputs}}
    state = OUT / 'link-build.json'
    previous = read_state(state)
    if (previous.get('context') != context or not linked.exists()
            or previous.get('kernel_sha256') != digest(linked)):
        linked.unlink(missing_ok=True)
    subprocess.run(command, check=True)
    kernel_hash = digest(linked)
    kernel = OUT / 'kernel.elf'
    if not kernel.exists() or digest(kernel) != kernel_hash:
        shutil.copyfile(linked, kernel)
    state.write_text(json.dumps({'context': context, 'kernel_sha256': kernel_hash}, indent=2) + '\n')
    # Verification still runs for cached images and refreshes evidence/notice files.
    subprocess.run(['python3', 'scripts/audit-runtime.py'], check=True)


if __name__ == '__main__':
    main()
