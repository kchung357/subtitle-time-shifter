import os
import re
import sys
import tempfile

USAGE = """\
Usage:
  python shift_subtitles.py FILE +2.5
  python shift_subtitles.py FILE -1:30
  python shift_subtitles.py FILE +500ms
  python shift_subtitles.py FILE +1m2s
  python shift_subtitles.py FILE 1:05.200 1:02.000
  python shift_subtitles.py FILE

FILE is overwritten in place.

One value shifts every cue. A bare number is seconds.
  +2.5          2.5 seconds later
  -0.25         0.25 seconds earlier
  +1:30         1 minute 30 seconds later
  +1:02:03.5    1 hour 2 minutes 3.5 seconds later
  +500ms        500 milliseconds later
  +1m2s         1 minute 2 seconds later
  +00:00:02:500 old format, still accepted

Two values:
  SENTENCE_START  SUBTITLE_START
Every cue moves so that subtitle start lands on the sentence start.

With no times, the script asks for those two moments.
"""

TIMESTAMP = r"\d+:\d{2}:\d{2},\d{3}"
CUE_RE = re.compile(rf"^({TIMESTAMP})\s+-->\s+({TIMESTAMP})(.*)$")
OFFSET_RE = re.compile(
    r"""
    ^\s*(?P<sign>[+-])\s*
    (?:
        (?P<clock4>\d+:\d+:\d+:\d+)
      | (?P<clock>(?:\d+:)?\d+:\d+(?:[.,]\d+)?)
      | (?P<units>(?:\d+(?:\.\d+)?(?:ms|h|m|s))+)
      | (?P<seconds>\d+(?:[.,]\d+)?)
    )\s*$
    """,
    re.VERBOSE | re.IGNORECASE,
)
UNIT_RE = re.compile(r"(\d+(?:\.\d+)?)(ms|h|m|s)", re.IGNORECASE)
MULTIPLIERS = {"ms": 1, "s": 1000, "m": 60_000, "h": 3_600_000}


def seconds_to_ms(text):
    return int(round(float(text.replace(",", ".")) * 1000))


def clock_to_ms(text):
    parts = text.replace(",", ".").split(":")
    if len(parts) == 4:
        hours, minutes, seconds, millis = parts
        return (
            int(hours) * 3_600_000
            + int(minutes) * 60_000
            + int(seconds) * 1000
            + int(millis)
        )
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3_600_000 + int(minutes) * 60_000 + seconds_to_ms(seconds)
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60_000 + seconds_to_ms(seconds)
    if len(parts) == 1:
        return seconds_to_ms(parts[0])
    raise ValueError(text)


def units_to_ms(text):
    total = 0
    pos = 0
    for match in UNIT_RE.finditer(text):
        if match.start() != pos:
            raise ValueError(text)
        unit = match.group(2).lower()
        total += int(round(float(match.group(1)) * MULTIPLIERS[unit]))
        pos = match.end()
    if pos != len(text):
        raise ValueError(text)
    return total


def parse_offset(text):
    match = OFFSET_RE.match(text)
    if not match:
        raise ValueError("offset must look like +2.5, -1:30, +500ms, or +1m2s")
    sign = 1 if match.group("sign") == "+" else -1
    if match.group("seconds") is not None:
        magnitude = seconds_to_ms(match.group("seconds"))
    elif match.group("units") is not None:
        magnitude = units_to_ms(match.group("units"))
    elif match.group("clock4") is not None:
        magnitude = clock_to_ms(match.group("clock4"))
    else:
        magnitude = clock_to_ms(match.group("clock"))
    return sign * magnitude


def parse_moment(text):
    text = text.strip()
    if text[:1] in "+-":
        raise ValueError("use an absolute time here, for example 1:05.200")
    try:
        return clock_to_ms(text)
    except ValueError as exc:
        raise ValueError("time must look like 65.2, 1:05.200, or 1:02:03,500") from exc


def timestamp_to_ms(timestamp):
    hours, minutes, rest = timestamp.split(":")
    seconds, millis = rest.split(",")
    return ((int(hours) * 60 + int(minutes)) * 60 + int(seconds)) * 1000 + int(millis)


def ms_to_timestamp(milliseconds):
    milliseconds = max(0, int(milliseconds))
    hours, rem = divmod(milliseconds, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def format_shift(shift_ms):
    sign = "+" if shift_ms >= 0 else "-"
    ms = abs(shift_ms)
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    if hours:
        body = f"{hours}:{minutes:02d}:{seconds:02d}.{millis:03d}"
    elif minutes:
        body = f"{minutes}:{seconds:02d}.{millis:03d}"
    else:
        body = f"{seconds}.{millis:03d}s"
    return sign + body


def shift_content(content, shift_ms):
    cues = 0
    clamped = 0
    lines = []
    for line in content.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        ending = line[len(body):]
        match = CUE_RE.match(body)
        if not match:
            lines.append(line)
            continue
        start = timestamp_to_ms(match.group(1)) + shift_ms
        end = timestamp_to_ms(match.group(2)) + shift_ms
        if start < 0 or end < 0:
            clamped += 1
        suffix = match.group(3)
        lines.append(
            f"{ms_to_timestamp(start)} --> {ms_to_timestamp(end)}{suffix}{ending}"
        )
        cues += 1
    return "".join(lines), cues, clamped


def rewrite(path, content):
    directory = os.path.dirname(path) or "."
    mode = os.stat(path).st_mode
    fd, tmp_path = tempfile.mkstemp(prefix=".shift-", suffix=".srt", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def ask(prompt):
    try:
        return input(prompt)
    except EOFError:
        print("No time entered.", file=sys.stderr)
        raise SystemExit(1)


def resolve_shift(times):
    if not times:
        times = [
            ask("When does the sentence start? "),
            ask("When does the subtitle start showing? "),
        ]
    if len(times) == 1:
        return parse_offset(times[0])
    if len(times) == 2:
        return parse_moment(times[0]) - parse_moment(times[1])
    raise ValueError("pass one offset, or the sentence time and the subtitle time")


def shift_file(path, shift_ms):
    try:
        with open(path, encoding="utf-8-sig", newline="") as handle:
            original = handle.read()
    except FileNotFoundError:
        print(f"File not found: {path}", file=sys.stderr)
        raise SystemExit(1)
    except UnicodeDecodeError:
        print(f"Could not read {path} as UTF-8.", file=sys.stderr)
        raise SystemExit(1)
    except OSError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)

    updated, cues, clamped = shift_content(original, shift_ms)
    if cues == 0:
        print(f"No subtitle cues found in {path}", file=sys.stderr)
        raise SystemExit(1)

    rewrite(os.path.realpath(path), updated)
    print(f"Shifted {cues} cues by {format_shift(shift_ms)}")
    print(f"Overwrote {path}")
    if clamped:
        print(f"Clamped {clamped} cues that would have gone before 00:00:00,000")
    return cues, clamped


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        stream = sys.stdout if args else sys.stderr
        print(USAGE, file=stream)
        raise SystemExit(0 if args else 1)

    path, *times = args
    try:
        shift_ms = resolve_shift(times)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)

    shift_file(path, shift_ms)


if __name__ == "__main__":
    main()
