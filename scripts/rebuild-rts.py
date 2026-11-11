#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Rebuild the bindist's C RTS objects with independently collectable sections.

Use the matching, verified GHC source and the bindist's configuration/ABI.
Keep its native Cmm/assembler objects. This is a bring-up builder, not yet a
configuration of the complete GHC distribution for a new target OS.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import toolchain

ROOT = Path('/work')
OUTPUT = ROOT / 'build/runtime/rts'
SOURCE = ROOT / '.cache/ghc-9.14.1/rts'
REPLACED = {'RtsStartup.o', 'CheckUnload.o', 'Interpreter.o', 'Ticker.o',
            'Signals.o', 'OSMem.o', 'GetTime.o', 'Select.o', 'ProfHeap.o'}


def main():
    toolchain.prepare_source()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    include = Path(subprocess.check_output(
        ['ghc-pkg', 'field', 'rts', 'include-dirs', '--simple-output'], text=True).strip())
    original = include.parent / 'libHSrts-1.0.3.a'
    members = subprocess.check_output(['ar', 't', str(original)], text=True).splitlines()
    sources = {}
    for directory in ('', 'sm', 'prim', 'hooks', 'posix', 'linker', 'linker/macho', 'adjustor'):
        for path in (SOURCE / directory).glob('*.c'):
            member = path.stem + '.o'
            if member in members and member not in REPLACED:
                if member in sources:
                    raise SystemExit(f'Ambiguous source for {member}')
                sources[member] = path
    flags = ['gcc', '-m32', '-O2', '-fomit-frame-pointer', '-fno-strict-aliasing',
             '-fno-pie', '-fno-stack-protector', '-ffunction-sections', '-fdata-sections',
             '-DCOMPILING_RTS', '-DFS_NAMESPACE=rts', '-DRtsWay="rts_v"',
             '-I' + str(include), '-I' + str(SOURCE), '-I' + str(SOURCE / 'include'),
             '-I' + str(SOURCE.parent / 'utils/fs')]
    headers = hashlib.sha256()
    for directory in (SOURCE, include, SOURCE.parent / 'utils/fs'):
        for header in sorted(directory.rglob('*.h')):
            headers.update(str(header).encode())
            headers.update(header.read_bytes())
    header_hash = headers.hexdigest()

    def compile_one(item):
        member, source = item
        target = OUTPUT / member
        extra = []
        if member == 'GC.o':
            extra = ['-I' + str(source.parent)]
            text = source.read_text()
            old = '/ pow(2, '
            if text.count(old) != 1:
                raise RuntimeError('GHC GC power-of-two call changed; review port')
            text = 'extern double house_pow2(double, double);\n' + text.replace(old, '/ house_pow2(2, ')
            source = OUTPUT / 'GC.c'
            source.write_text(text)
        key = hashlib.sha256(source.read_bytes() + json.dumps(flags + extra).encode() + header_hash.encode()).hexdigest()
        stamp = target.with_suffix('.sha256')
        if target.exists() and stamp.exists() and stamp.read_text() == key:
            return target
        result = subprocess.run([*flags, *extra, '-c', str(source), '-o', str(target)],
                                capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f'{source}:\n{result.stdout}{result.stderr}')
        stamp.write_text(key)
        return target

    with ThreadPoolExecutor(max_workers=4) as pool:
        objects = list(pool.map(compile_one, sorted(sources.items())))
    archive = OUTPUT.parent / 'libhouse-rts.a'
    shutil.copyfile(original, archive)
    subprocess.run(['ar', 'd', str(archive), *sorted(REPLACED)], check=True)
    subprocess.run(['ar', 'r', str(archive), *map(str, objects)], check=True)
    subprocess.run(['ranlib', str(archive)], check=True)
    (OUTPUT / 'build.json').write_text(json.dumps({
        'source': str(SOURCE), 'original_archive': str(original), 'flags': flags,
        'rebuilt_objects': sorted(sources),
        'retained_bindist_objects': sorted(set(members) - set(sources) - REPLACED),
        'replaced_platform_objects': sorted(REPLACED),
        'headers_sha256': header_hash,
        'source_archive_sha256': toolchain.LOCK['source']['sha256'],
        'source_files_sha256': {str(p.relative_to(SOURCE)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(sources.values())},
        'collector_change': 'Redirect the sole pow(2, x) call to house_pow2 using x87',
    }, indent=2) + '\n')
    print(f'Rebuilt {len(objects)} C objects; retained {len(members)-len(objects)-len(REPLACED)} native objects.', flush=True)


if __name__ == '__main__':
    main()
