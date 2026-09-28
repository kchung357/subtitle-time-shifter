# Subtitle Time Shifter

A simple Python command-line tool for shifting SRT subtitle timestamps forward or backward.

It reads an `.srt` file, applies a time offset to every subtitle timestamp, and overwrites that file in place.

## Features

- Shifts all SRT subtitle timestamps forward or backward
- Overwrites the subtitle file you pass in
- Accepts short offsets such as `+2.5`, `-1:30`, and `+500ms`
- Can compute the offset from when a sentence starts and when the subtitle appears
- Asks for those two moments when you pass only the file
- Preserves subtitle text and numbering
- Clamps timestamps that would move before `00:00:00,000`
- Uses only Python standard-library modules

## Requirements

- Python 3.8 or newer

No external Python packages are required.

## Installation

Clone the repository:

```bash
git clone https://github.com/kchung357/subtitle-time-shifter.git
cd subtitle-time-shifter
```

No package installation is required.

## Usage

```bash
python shift_subtitles.py FILE +2.5
python shift_subtitles.py FILE -1:30
python shift_subtitles.py FILE +500ms
python shift_subtitles.py FILE 1:05.200 1:02.000
python shift_subtitles.py FILE
```

The file is overwritten in place. There is no separate output path.

With no times, the script asks:

```text
When does the sentence start?
When does the subtitle start showing?
```

## Time Shift Format

One value shifts every cue by that amount. A bare number is seconds.

| Input | Meaning |
|---|---|
| `+2.5` | 2.5 seconds later |
| `-0.25` | 0.25 seconds earlier |
| `+1:30` | 1 minute 30 seconds later |
| `+1:02:03.5` | 1 hour, 2 minutes, 3.5 seconds later |
| `+500ms` | 500 milliseconds later |
| `+1m2s` | 1 minute 2 seconds later |
| `+1h` | 1 hour later |
| `+00:00:02:500` | old `+HH:MM:SS:mmm` format, still accepted |

`+` moves subtitles later. `-` moves them earlier.

## Sync From Two Moments

Pass the sentence time first and the current subtitle time second:

```bash
python shift_subtitles.py movie.srt 1:05.200 1:02.000
```

The shift is the sentence start minus the subtitle start. Every cue moves so the subtitle that appeared at `1:02.000` now appears at `1:05.200`.

Absolute times can be written as seconds (`65.2`), minutes and seconds (`1:05.200`), or hours, minutes, and seconds (`1:02:03,500`).

## Examples

Shift subtitles forward by 2.5 seconds:

```bash
python shift_subtitles.py movie.srt +2.5
```

Shift subtitles backward by 1.5 seconds:

```bash
python shift_subtitles.py movie.srt -1.5
```

Shift subtitles forward by 1 minute 30 seconds:

```bash
python shift_subtitles.py movie.srt +1:30
```

Shift subtitles backward by 500 milliseconds:

```bash
python shift_subtitles.py movie.srt -500ms
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
python shift_subtitles.py movie.srt +2
```

The same file then contains:

```text
1
00:00:12,000 --> 00:00:14,500
Hello world.

2
00:00:17,000 --> 00:00:20,000
This is a subtitle.
```

The script prints the shift it applied. Run the opposite offset to undo it. For this example, that is `-2`.

## Important Notes

This script is intended for `.srt` subtitle files.

The file you pass is replaced. The original bytes are read completely before that replacement happens.

A cue that would move before `00:00:00,000` is clamped to zero, and the script reports how many cues were clamped.

## Privacy Notice

Do not commit private, copyrighted, or sensitive subtitle files to this repository.

This repository should contain only the script and project documentation.

## License

This project is licensed under the MIT License.
