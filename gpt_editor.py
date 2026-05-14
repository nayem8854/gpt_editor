#!/usr/bin/env python3

import struct
import sys
import os
import zlib


class GPTEditor:

    GPT_HEADER_SIZE = 92
    GPT_ENTRY_SIZE = 128
    MAX_ENTRIES = 128
    SECTOR_SIZE = 512

    def __init__(self, filename):

        self.filename = filename

        with open(filename, 'rb') as f:
            self.data = bytearray(f.read())

        print(f"[*] Loaded {filename}, size: {len(self.data)} bytes")

        self.primary_header_offset = -1
        self.backup_header_offset = -1

        self.primary_entries_offset = -1
        self.backup_entries_offset = -1

        self.num_entries = 128
        self.entry_size = 128

        self.parse_gpt()

    #
    # FIND GPT HEADERS
    #
    def find_gpt_headers(self):

        sig = b'EFI PART'
        offsets = []

        for i in range(0, len(self.data) - 8):

            if self.data[i:i + 8] == sig:
                offsets.append(i)

        return offsets

    #
    # PARSE GPT
    #
    def parse_gpt(self):

        offsets = self.find_gpt_headers()

        if len(offsets) == 0:

            print("[-] No GPT header found")
            return False

        print(f"[*] Found {len(offsets)} GPT headers")

        #
        # PRIMARY
        #
        self.primary_header_offset = offsets[0]
        self._parse_header(self.primary_header_offset, "Primary")

        #
        # BACKUP
        #
        if len(offsets) > 1:

            self.backup_header_offset = offsets[-1]
            self._parse_header(self.backup_header_offset, "Backup")

        return True

    #
    # PARSE HEADER
    #
    def _parse_header(self, offset, name):

        if offset + 92 > len(self.data):

            print(f"[!] Invalid GPT header at 0x{offset:x}")
            return

        hdr = self.data[offset:offset + 92]

        signature = hdr[0:8].decode('ascii', errors='replace')

        revision = struct.unpack('<I', hdr[8:12])[0]

        header_size = struct.unpack('<I', hdr[12:16])[0]

        crc32_val = struct.unpack('<I', hdr[16:20])[0]

        my_lba = struct.unpack('<Q', hdr[24:32])[0]

        partition_entry_lba = struct.unpack('<Q', hdr[72:80])[0]

        self.num_entries = struct.unpack('<I', hdr[80:84])[0]

        self.entry_size = struct.unpack('<I', hdr[84:88])[0]

        print(f"\n[*] {name} GPT Header")

        print(f"    Signature  : {signature}")
        print(f"    Revision   : 0x{revision:08x}")
        print(f"    HeaderSize : {header_size}")
        print(f"    CRC32      : 0x{crc32_val:08x}")
        print(f"    MyLBA      : {my_lba}")
        print(f"    EntriesLBA : {partition_entry_lba}")
        print(f"    Entries    : {self.num_entries}")
        print(f"    EntrySize  : {self.entry_size}")

        entries_offset = partition_entry_lba * self.SECTOR_SIZE

        if name == "Primary":

            self.primary_entries_offset = entries_offset

            print(
                f"    Primary Entries Offset : "
                f"0x{entries_offset:x}"
            )

        elif name == "Backup":

            self.backup_entries_offset = entries_offset

            print(
                f"    Backup Entries Offset  : "
                f"0x{entries_offset:x}"
            )

    #
    # DECODE PARTITION NAME
    #
    def decode_partition_name(self, data, offset):

        try:

            raw = data[offset:offset + 72]

        except:

            return "?"

        name = ""

        for i in range(0, len(raw), 2):

            if i + 2 > len(raw):
                break

            try:

                char_code = struct.unpack(
                    '<H',
                    raw[i:i + 2]
                )[0]

            except:

                break

            if char_code == 0:
                break

            if 32 <= char_code < 127:

                name += chr(char_code)

            else:

                name += '.'

        return name.strip() if name.strip() else "(empty)"

    #
    # LIST PARTITIONS
    #
    def list_partitions(self):

        if self.primary_entries_offset < 0:

            print("[-] Invalid GPT entries offset")
            return

        print("\n[*] Partition Table:")

        print(
            f"{'#':<4} "
            f"{'Name':<22} "
            f"{'Start LBA':<12} "
            f"{'End LBA':<12} "
            f"{'Size':<10} "
            f"{'GUID'}"
        )

        print("-" * 90)

        count = 0

        for i in range(self.num_entries):

            entry_offset = (
                self.primary_entries_offset +
                (i * self.entry_size)
            )

            if entry_offset + self.entry_size > len(self.data):
                break

            entry = self.data[
                entry_offset:
                entry_offset + self.entry_size
            ]

            partition_type_guid = entry[0:16]

            #
            # EMPTY ENTRY
            #
            if all(b == 0 for b in partition_type_guid):
                continue

            unique_guid = entry[16:32]

            start_lba = struct.unpack(
                '<Q',
                entry[32:40]
            )[0]

            end_lba = struct.unpack(
                '<Q',
                entry[40:48]
            )[0]

            name = self.decode_partition_name(
                entry,
                56
            )

            size_sectors = end_lba - start_lba + 1
            size_bytes = size_sectors * 512

            if size_bytes >= (1024 ** 3):

                size_str = (
                    f"{size_bytes / (1024 ** 3):.1f}GB"
                )

            elif size_bytes >= (1024 ** 2):

                size_str = (
                    f"{size_bytes / (1024 ** 2):.1f}MB"
                )

            elif size_bytes >= 1024:

                size_str = (
                    f"{size_bytes / 1024:.1f}KB"
                )

            else:

                size_str = f"{size_bytes}B"

            guid_hex = unique_guid.hex()

            guid_str = (
                f"{guid_hex[:8]}-"
                f"{guid_hex[8:12]}-"
                f"{guid_hex[12:16]}"
            )

            print(
                f"{i:<4} "
                f"{name:<22} "
                f"{start_lba:<12} "
                f"{end_lba:<12} "
                f"{size_str:<10} "
                f"{guid_str}"
            )

            count += 1

        print(f"\n[*] Total partitions found: {count}")

    #
    # FIND PARTITION
    #
    def find_partition(self, partition_input):

        #
        # BY INDEX
        #
        if str(partition_input).isdigit():

            idx = int(partition_input)

            if idx < 0 or idx >= self.MAX_ENTRIES:
                return -1, -1

            entry_offset = (
                self.primary_entries_offset +
                (idx * self.entry_size)
            )

            if entry_offset + self.entry_size > len(self.data):
                return -1, -1

            entry = self.data[
                entry_offset:
                entry_offset + self.entry_size
            ]

            partition_type_guid = entry[0:16]

            #
            # EMPTY ENTRY
            #
            if all(b == 0 for b in partition_type_guid):
                return -1, -1

            return idx, entry_offset

        #
        # BY NAME
        #
        for i in range(self.MAX_ENTRIES):

            entry_offset = (
                self.primary_entries_offset +
                (i * self.entry_size)
            )

            if entry_offset + 72 > len(self.data):
                break

            current_name = self.decode_partition_name(
                self.data,
                entry_offset + 56
            )

            if partition_input.lower() in current_name.lower():

                return i, entry_offset

        return -1, -1

    #
    # RENAME PARTITION
    #
    def rename_partition(self, old_input, new_name):

        found = False

        #
        # INDEX MODE
        #
        if str(old_input).isdigit():

            target_index = int(old_input)

        else:

            target_index = None

        for copy_name, entries_offset in [

            ("Primary", self.primary_entries_offset),

            ("Backup", self.backup_entries_offset)

        ]:

            if entries_offset < 0:
                continue

            for i in range(self.MAX_ENTRIES):

                entry_offset = (
                    entries_offset +
                    (i * self.entry_size)
                )

                if entry_offset + 72 > len(self.data):
                    break

                current_name = self.decode_partition_name(
                    self.data,
                    entry_offset + 56
                )

                #
                # MATCH
                #
                matched = False

                #
                # BY INDEX
                #
                if target_index is not None:

                    if i == target_index:
                        matched = True

                #
                # BY NAME
                #
                else:

                    if (
                        old_input.lower() ==
                        current_name.lower()

                        or

                        old_input.lower() in
                        current_name.lower()
                    ):

                        matched = True

                #
                # RENAME
                #
                if matched:

                    print(
                        f"[+] Found '{current_name}' "
                        f"(index {i}) in {copy_name}"
                    )

                    new_name_utf16 = bytearray(72)

                    for j, ch in enumerate(new_name[:36]):

                        struct.pack_into(
                            '<H',
                            new_name_utf16,
                            j * 2,
                            ord(ch)
                        )

                    self.data[
                        entry_offset + 56:
                        entry_offset + 128
                    ] = new_name_utf16

                    print(
                        f"    Renamed -> '{new_name}'"
                    )

                    found = True

        return found

    #
    # UPDATE CRC32
    #
    def update_crc32(self):

        try:

            for name, hdr_offset, entries_offset in [

                (
                    "Primary",
                    self.primary_header_offset,
                    self.primary_entries_offset
                ),

                (
                    "Backup",
                    self.backup_header_offset,
                    self.backup_entries_offset
                )
            ]:

                if hdr_offset < 0 or entries_offset < 0:
                    continue

                entries_end = (
                    entries_offset +
                    (self.MAX_ENTRIES * self.entry_size)
                )

                if entries_end > len(self.data):
                    entries_end = len(self.data)

                entries_data = bytes(
                    self.data[
                        entries_offset:
                        entries_end
                    ]
                )

                entries_crc = (
                    zlib.crc32(entries_data)
                    & 0xFFFFFFFF
                )

                #
                # CLEAR OLD HEADER CRC
                #
                self.data[
                    hdr_offset + 16:
                    hdr_offset + 20
                ] = b'\x00\x00\x00\x00'

                #
                # WRITE ENTRY CRC
                #
                self.data[
                    hdr_offset + 88:
                    hdr_offset + 92
                ] = struct.pack(
                    '<I',
                    entries_crc
                )

                #
                # HEADER CRC
                #
                header_data = bytes(
                    self.data[
                        hdr_offset:
                        hdr_offset + 92
                    ]
                )

                header_crc = (
                    zlib.crc32(header_data)
                    & 0xFFFFFFFF
                )

                #
                # WRITE HEADER CRC
                #
                self.data[
                    hdr_offset + 16:
                    hdr_offset + 20
                ] = struct.pack(
                    '<I',
                    header_crc
                )

                print(
                    f"[*] {name} CRC updated "
                    f"(header=0x{header_crc:08x}, "
                    f"entries=0x{entries_crc:08x})"
                )

        except Exception as e:

            print(f"[!] CRC update failed: {e}")

    #
    # SAVE FILE
    #
    def save(self, output_filename):

        with open(output_filename, 'wb') as f:
            f.write(self.data)

        print(f"[+] Saved -> {output_filename}")


#
# MAIN
#
if __name__ == '__main__':

    if len(sys.argv) < 3:

        print("Usage:")

        print(
            "  python3 gpt_editor.py "
            "<gpt_file> list"
        )

        print(
            "  python3 gpt_editor.py "
            "<gpt_file> rename "
            "<old1/index1> <new1> "
            "[old2/index2 new2] ..."
        )

        sys.exit(1)

    filename = sys.argv[1]
    command = sys.argv[2]

    editor = GPTEditor(filename)

    #
    # LIST
    #
    if command == "list":

        editor.list_partitions()

    #
    # RENAME
    #
    elif command == "rename":

        #
        # Must be pair
        #
        if (
            len(sys.argv) < 5
            or
            (len(sys.argv) - 3) % 2 != 0
        ):

            print("Usage:")

            print(
                "  python3 gpt_editor.py "
                "<gpt_file> rename "
                "<old1/index1> <new1> "
                "[old2/index2 new2] ..."
            )

            sys.exit(1)

        renamed_any = False

        #
        # PROCESS ALL PAIRS
        #
        for i in range(3, len(sys.argv), 2):

            old_name = sys.argv[i]
            new_name = sys.argv[i + 1]

            print(
                f"\n[*] Rename: "
                f"{old_name} -> {new_name}"
            )

            if editor.find_partition(old_name)[0] >= 0:

                if editor.rename_partition(
                    old_name,
                    new_name
                ):

                    renamed_any = True

                else:

                    print("[-] Rename failed")

            else:

                print(
                    f"[-] Partition "
                    f"'{old_name}' not found"
                )

        #
        # SAVE ONCE
        #
        if renamed_any:

            editor.update_crc32()

            base, ext = os.path.splitext(filename)

            output_file = (
                f"{base}_modified{ext}"
            )

            editor.save(output_file)

        else:

            print("[-] No partitions renamed")

    #
    # INVALID COMMAND
    #
    else:

        print(
            f"[-] Unknown command: {command}"
        )

        print("Usage:")

        print(
            "  python3 gpt_editor.py "
            "<gpt_file> list"
        )

        print(
            "  python3 gpt_editor.py "
            "<gpt_file> rename "
            "<old1/index1> <new1> "
            "[old2/index2 new2] ..."
        )