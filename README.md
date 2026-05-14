````md id="v8u1ei"
# GPT Editor

Simple Python GPT partition table editor for Android / Qualcomm GPT images.

## Features

- List GPT partitions
- Rename partition names
- Rename multiple partitions at once
- Rename using:
  - partition name
  - partition index number
- Auto CRC32 update
- Supports:
  - Primary GPT
  - Backup GPT

---

## Requirements

- Python 3

---

## Usage

### List partitions

```bash
python3 gpt_editor.py gpt.bin list
````

---

### Rename partition by name

```bash
python3 gpt_editor.py gpt.bin rename vbmeta_a xbmeta
```

---

### Rename partition by index

```bash
python3 gpt_editor.py gpt.bin rename 72 xbmeta
```

---

### Rename multiple partitions

```bash
python3 gpt_editor.py gpt.bin rename \
72 xbmeta \
boot_a xboot \
vendor_boot_a xvendor
```

---

## Output

Modified GPT will be saved as:

```text
gpt_modified.bin
```

Example:

```text
gpt.bin
-> gpt_modified.bin
```

---

## Notes

* Partition names are UTF-16LE encoded
* CRC32 is automatically recalculated
* Empty GPT entries are skipped
* Original file is never overwritten

---

## Tested On

* Qualcomm GPT dumps
* Android GPT images
* GPT extracted from firehose dumps

---

## Warning

Editing GPT incorrectly may brick your device.

Always keep:

* original GPT backup
* full firmware backup

before flashing modified GPT.

---

## License

MIT

```
```
