#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reject hosted/native-library leakage and record the exact kernel inputs."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path('/work')
OUT = ROOT / 'build/runtime'


def capture(name, command):
    text = subprocess.check_output(command, text=True)
    (OUT / name).write_text(text)
    return text


def main():
    kernel = OUT / 'kernel.elf'
    header = capture('elf-header.txt', ['readelf', '-h', str(kernel)])
    segments = capture('elf-segments.txt', ['readelf', '-Wl', str(kernel)])
    undefined = capture('undefined.txt', ['nm', '-u', str(kernel)])
    symbols = capture('symbols.txt', ['nm', '-n', str(kernel)])
    sizes = capture('size.txt', ['size', str(kernel)])
    if 'ELF32' not in header or 'Intel 80386' not in header or undefined.strip():
        raise SystemExit('Kernel format or unresolved-symbol audit failed')
    if re.search(r'^\s*(INTERP|DYNAMIC|TLS)\s', segments, re.M):
        raise SystemExit('Hosted ELF interpreter, dynamic segment or TLS in kernel')
    names = [line.split()[-1] for line in symbols.splitlines() if line.split()]
    forbidden = [n for n in names if n.startswith(('__gmp', 'ffi_', 'pthread_', 'iconv', 'epoll_'))
                 or n in ('mmap', 'munmap', 'dlopen', 'dlsym', 'syscall')]
    if forbidden:
        raise SystemExit(f'Unexpected OS/native dependency: {forbidden}')
    assembly = capture('disassembly.txt', ['objdump', '-d', str(kernel)])
    if re.search(r'\b(?:syscall|sysenter)\b|\bint\s+\$0x80\b', assembly):
        raise SystemExit('Linux syscall instruction in standalone kernel')
    link_map = (OUT / 'kernel.map').read_text()
    archive_members = sorted(set(re.findall(r'^(/[^\n]+\.a\([^\n]+\.o\))\s*$', link_map, re.M)))
    helpers = sorted(n for n in names if re.fullmatch(r'__(?:u?div|u?mod|u?divmod|[al]shr|ashl|mul)di[34]', n))
    licenses = OUT / 'dependency-notices'
    licenses.mkdir(exist_ok=True)
    for source, name in [
        (ROOT / '.cache/ghc-9.14.1/LICENSE', 'ghc-LICENSE'),
        (ROOT / '.cache/ghc-9.14.1/libraries/ghc-internal/LICENSE', 'ghc-internal-LICENSE'),
        (Path('/usr/share/doc/libgcc-12-dev/copyright'), 'libgcc-Debian-copyright'),
        (ROOT / 'LICENSES/MIT.txt', 'house-bootstrap-MIT.txt'),
    ]:
        shutil.copyfile(source, licenses / name)
    project_inputs = sorted(p for directory in ('bootstrap/runtime', 'bootstrap/serial', 'scripts', 'toolchain')
                            for p in (ROOT / directory).rglob('*')
                            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    report = {
        'kernel_sha256': hashlib.sha256(kernel.read_bytes()).hexdigest(),
        'ghc_version': subprocess.check_output(['ghc', '--numeric-version'], text=True).strip(),
        'gcc_package': subprocess.check_output(['dpkg-query', '-W', '-f=${Version}', 'libgcc-12-dev'], text=True),
        'external_guest_support': ['selected GHC RTS C/Cmm/assembler', 'original House bootstrap C/assembler',
                                   'selected libgcc integer arithmetic helpers'],
        'libgcc_helpers': helpers, 'archive_members_pulled': archive_members,
        'hosted_os_dependencies_found': forbidden,
        'project_inputs_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in project_inputs},
        'elf_size': sizes.strip(),
    }
    (OUT / 'dependencies.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Kernel audit passed: ELF32, no unresolved symbols, dynamic loader, TLS, Linux syscalls, GMP or libffi.')
    print('Compiler helpers: ' + ', '.join(helpers))


if __name__ == '__main__':
    main()
