# SPDX-License-Identifier: MIT
"""IA32 ELF audit helpers for GHC's tables-next-to-code layout."""
import re
import struct


def load_segments(data):
    if data[:6] != b'\x7fELF\x01\x01':
        raise ValueError('Expected little-endian ELF32')
    start = struct.unpack_from('<I', data, 28)[0]
    size, count = struct.unpack_from('<HH', data, 42)
    return [struct.unpack_from('<8I', data, start + i * size) for i in range(count)]


def file_offset(segments, address, length=4, flags=None):
    for kind, offset, virtual, _physical, size, _memory, permissions, _alignment in segments:
        if (kind == 1 and virtual <= address and address + length <= virtual + size
                and (flags is None or permissions == flags)):
            return offset + address - virtual
    return None


def section_range(data, name):
    start = struct.unpack_from('<I', data, 32)[0]
    size, count, strings = struct.unpack_from('<HHH', data, 46)
    headers = [struct.unpack_from('<10I', data, start + i * size) for i in range(count)]
    string_header = headers[strings]
    names = data[string_header[4]:string_header[4] + string_header[5]]
    for header in headers:
        if names[header[0]:].split(b'\0', 1)[0] == name.encode():
            return header[3], header[3] + header[5]
    raise ValueError(f'Missing ELF section {name}')


def scan_system_calls(data, assembly, symbols):
    """Separate syscall mnemonics from a verified GHC info-table SRT field.

    Linear disassembly treats info-table words embedded in .text as code.
    Recognize pinned non-profiling IA32 constructor, return/thunk and compact FUN layouts:
    signed SRT offset, layout words, closure tag, srt-present=1. GET_SRT adds
    that offset to the entry immediately after the table. Require
    a referenced code entry and a real static closure in the writable segment.
    All other matches fail the audit; this is not a general code verifier.
    """
    segments = load_segments(data)
    rodata_start, rodata_end = section_range(data, '.rodata')
    symbol_map = {}
    for line in symbols.splitlines():
        parts = line.split()
        if len(parts) == 3:
            symbol_map.setdefault(int(parts[0], 16), set()).add(parts[2])
    infos = {address for address, names in symbol_map.items()
             if any(name.endswith('_info') for name in names)}
    srt_infos = {address for address, names in symbol_map.items()
                 if any(re.fullmatch(r'stg_SRT_\d+_info', name) for name in names)}
    rejected, tables = [], []
    pattern = re.compile(r'^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)'
                         r'(?:(?:cs|ss|ds|es|fs|gs|data16|addr16|repz|repnz|rep|bnd|lock)\s+)*'
                         r'(syscall|sysenter|int\s+\$0x80)\b', re.M)
    for match in pattern.finditer(assembly):
        address = int(match[1], 16)
        length = len(match[2].split())
        table = address & ~3
        accepted = False
        for size in (12, 16):
            offset = file_offset(segments, table, size, flags=5)
            if offset is None or address + length > table + 4:
                continue
            relative = struct.unpack_from('<i', data, offset)[0]
            closure_type, has_srt = struct.unpack_from('<HH', data, offset + size - 4)
            if size == 12:
                valid_layout = closure_type in (30, 31) or 15 <= closure_type <= 21
                classification = 'GHC return/thunk SRT offset data'
            else:
                fun_type, arity = struct.unpack_from('<HH', data, offset + 4)
                valid_layout = 8 <= closure_type <= 14 and 3 <= fun_type <= 28 and arity > 0
                classification = 'GHC compact FUN SRT offset data'
            entry = table + size
            target = entry + relative
            if (size == 12 and 1 <= closure_type <= 7 and
                    any(n.endswith('_con_info') for n in symbol_map.get(entry, ())) and
                    rodata_start <= target < rodata_end):
                description_offset = file_offset(segments, target, 1, flags=5)
                end = min(description_offset + 512, description_offset + rodata_end - target)
                description = data[description_offset:end].split(b'\0', 1)[0]
                if (description and len(description) < end - description_offset and
                        all(32 <= byte < 127 for byte in description) and b':' in description):
                    tables.append({'address': address, 'table_address': table, 'table_size': size,
                                   'entry_address': entry, 'description_address': target,
                                   'description': description.decode('ascii'),
                                   'classification': 'GHC constructor description offset data'})
                    accepted = True
                    break
            target_offset = file_offset(segments, target, flags=6)
            if (valid_layout and has_srt == 1 and target % 4 == 0
                    and target_offset is not None and (entry in infos or f'$0x{entry:x}' in assembly)):
                info = struct.unpack_from('<I', data, target_offset)[0]
                closure_names = sorted(n for n in symbol_map.get(target, ()) if n.endswith('_closure'))
                if info in infos and (closure_names or info in srt_infos):
                    tables.append({'address': address, 'table_address': table,
                                   'table_size': size,
                                   'entry_address': entry, 'srt_target': target,
                                   'closure_symbols': closure_names,
                                   'classification': classification})
                    accepted = True
                    break
        if not accepted:
            rejected.append({'address': address, 'instruction': match[3]})
    return rejected, tables
