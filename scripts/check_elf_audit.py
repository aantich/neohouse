#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify real trap instructions are rejected despite GHC info-table data."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
from elf_audit import file_offset, load_segments, scan_system_calls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-info-table-case', action='store_true')
    args = parser.parse_args()
    output = Path('/work/build/runtime')
    kernel = output / 'kernel.elf'
    data = kernel.read_bytes()
    symbols = subprocess.check_output(['nm', '-n', str(kernel)], text=True)
    assembly = subprocess.check_output(['objdump', '-d', str(kernel)], text=True)
    rejected, tables = scan_system_calls(data, assembly, symbols)
    if rejected or (args.require_info_table_case and not tables):
        raise SystemExit('Original kernel did not exercise the expected audit case')
    entry = struct.unpack_from('<I', data, 24)[0]
    offset = file_offset(load_segments(data), entry, 3, flags=5)
    if offset is None:
        raise SystemExit('Invalid executable kernel entry')
    fixture = output / 'audit-fixture.elf'
    for instruction in (b'\xcd\x80', b'\x0f\x34', b'\x0f\x05', b'\x64\x0f\x05'):
        changed = bytearray(data)
        changed[offset:offset+len(instruction)] = instruction
        fixture.write_bytes(changed)
        disassembly = subprocess.check_output(['objdump', '-d', str(fixture)], text=True)
        found, _ = scan_system_calls(changed, disassembly, symbols)
        if not any(item['address'] == entry for item in found):
            raise SystemExit(f'Failed to reject executable opcode {instruction.hex()}')
    if tables:
        changed = bytearray(data)
        table_offset = file_offset(load_segments(data), tables[0]['table_address'], 12)
        tag = table_offset + tables[0]['table_size'] - 4
        changed[tag:tag+2] = b'\x00\x00'  # Invalid closure tag.
        fixture.write_bytes(changed)
        disassembly = subprocess.check_output(['objdump', '-d', str(fixture)], text=True)
        found, _ = scan_system_calls(changed, disassembly, symbols)
        if not any(item['address'] == tables[0]['address'] for item in found):
            raise SystemExit('Accepted opcode bytes without a valid GHC info table')
    fixture.unlink()
    (output / 'audit-check.json').write_text(json.dumps({
        'passed': True, 'real_opcodes_rejected': ['int 0x80', 'sysenter', 'syscall'],
        'info_table_cases': len(tables), 'invalid_table_rejected': bool(tables),
    }, indent=2) + '\n')
    print('ELF audit passed: real syscall opcodes rejected; GHC table data validated.')


if __name__ == '__main__':
    main()
