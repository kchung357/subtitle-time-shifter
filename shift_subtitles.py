import re
import sys

def time_to_seconds(time_str):
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s.replace(',', '.'))

def milliseconds_to_time(milliseconds):
    hours = int(milliseconds // 3600000)
    minutes = int((milliseconds % 3600000) // 60000)
    seconds = int((milliseconds % 60000) // 1000)
    ms = milliseconds % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"

def shift_time(match, shift_ms):
    start_time = time_to_seconds(match.group(1)) * 1000
    end_time = time_to_seconds(match.group(2)) * 1000
    
    new_start = milliseconds_to_time(int(start_time + shift_ms))
    new_end = milliseconds_to_time(int(end_time + shift_ms))
    
    return f"{new_start} --> {new_end}"

def process_file(input_file, output_file, shift):
    shift_ms = sum([int(x) * y for x, y in zip(shift[1:].split(':'), [3600000, 60000, 1000, 1])])
    if shift[0] == '-':
        shift_ms = -shift_ms
    
    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
        content = infile.read()
        new_content = re.sub(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', 
                             lambda m: shift_time(m, shift_ms), content)
        outfile.write(new_content)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python shift_subtitles.py input.srt output.srt +/-HH:MM:SS:mmm")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    time_shift = sys.argv[3]

    process_file(input_file, output_file, time_shift)
    print(f"Subtitle times shifted and saved to {output_file}")