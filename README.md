# Subtitle Time Shifter

A simple Python command-line tool for shifting SRT subtitle timestamps forward or backward.

It reads an input `.srt` file, applies a positive or negative time offset to every subtitle timestamp, and writes the adjusted subtitles to a new output `.srt` file.

## Features

- Shifts all SRT subtitle timestamps forward or backward
- Supports positive and negative time offsets
- Preserves subtitle text and numbering
- Writes the shifted subtitles to a new output file
- Simple command-line interface
- Uses only Python standard-library modules

## Requirements

- Python 3.8 or newer

No external Python packages are required.

## Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/subtitle-time-shifter.git
cd subtitle-time-shifter
```

No package installation is required.

## Usage

Run the script with an input subtitle file, an output subtitle file, and a time shift value:

```bash
python shift_subtitles.py input.srt output.srt +/-HH:MM:SS:mmm
```

## Time Shift Format

The time shift format is:

```text
+HH:MM:SS:mmm
```

or:

```text
-HH:MM:SS:mmm
```

Where:

| Part | Meaning |
|---|---|
| `+` | Shift subtitles later |
| `-` | Shift subtitles earlier |
| `HH` | Hours |
| `MM` | Minutes |
| `SS` | Seconds |
| `mmm` | Milliseconds |

## Examples

Shift subtitles forward by 2.5 seconds:

```bash
python shift_subtitles.py input.srt output.srt +00:00:02:500
```

Shift subtitles backward by 1 second:

```bash
python shift_subtitles.py input.srt output.srt -00:00:01:000
```

Shift subtitles forward by 1 minute:

```bash
python shift_subtitles.py input.srt output.srt +00:01:00:000
```

Shift subtitles backward by 1 hour:

```bash
python shift_subtitles.py input.srt output.srt -01:00:00:000
```

## Example

Input subtitle:

```text
1
00:00:10,000 --> 00:00:12,500
Hello world.

2
00:00:15,000 --> 00:00:18,000
This is a subtitle.
```

Command:

```bash
python shift_subtitles.py input.srt output.srt +00:00:02:000
```

Output subtitle:

```text
1
00:00:12,000 --> 00:00:14,500
Hello world.

2
00:00:17,000 --> 00:00:20,000
This is a subtitle.
```

## Important Notes

This script is intended for `.srt` subtitle files.

Make sure a negative shift does not move subtitle timestamps before:

```text
00:00:00,000
```

If subtitles are shifted too far backward, the output may contain invalid negative timing behavior.

The script writes to a new output file and does not modify the original input file.

## Privacy Notice

Do not commit private, copyrighted, or sensitive subtitle files to this repository.

This repository should contain only the script and project documentation.

## License

This project is licensed under the MIT License.
