#!/usr/bin/env python3
"""
karaoke.py
Generate a CPU+GPU-accelerated karaoke-style highlight video from:
- an input video
- WhisperX JSON word timings
- two audio WAVs (accompaniment + vocals)

This script:
- Probes video resolution via ffprobe
- Reads WhisperX JSON with segment-level word timings
- Chunks words into groups (<= max_words or on punctuation)
- Draws solid-color boxes behind each word, expanded by pad
- Sequentially highlights words without flicker
- Overlays the full subtitle line with outline/shadow for readability
- Mixes the two audio tracks
- Writes out a filter_graph.txt and prints an ffmpeg command

Supports CUDA/HW acceleration for encode (-c:v h264_nvenc) and multithreading for filters.
"""
import json
import subprocess
import multiprocessing
import argparse
from pathlib import Path
from PIL import ImageFont


def parse_args():
    p = argparse.ArgumentParser(description="Generate CPU+GPU karaoke highlight video.")
    p.add_argument("--input-video",    default="original.mp4", help="Path to input video file")
    p.add_argument("--json-file",      default="vocals-en-corrected-aligned.json", help="Path to WhisperX JSON")
    p.add_argument("--acc-wav",        default="original_accompaniment.wav", help="Path to accompaniment WAV")
    p.add_argument("--voc-wav",        default="vocals-en.wav", help="Path to vocals WAV")
    p.add_argument("--filter-graph",   default="filter_graph.txt", help="Output filter_graph.txt path")
    p.add_argument("--font-path",      default="/usr/share/fonts/opentype/urw-base35/NimbusMonoPS-Bold.otf", help="Path to TTF font file")
    p.add_argument("--font-size",      type=int, default=60,   help="Font size in px")
    p.add_argument("--margin",         type=int, default=None,  help="Bottom margin in px")
    p.add_argument("--margin-percent", type=float, default=30, help="Bottom margin in percent of video height")
    p.add_argument("--max-words",      type=int, default=5,    help="Max words per subtitle chunk")
    p.add_argument("--pad",            type=int, default=10,   help="Padding around each highlight box in px")
    p.add_argument("--box-color",      default="0x00A5FF",    help="Highlight box color (hex) e.g. 0x00A5FF")
    p.add_argument("--font-color",     default="white",      help="Font color for text overlay")
    p.add_argument("--overwrite",      action="store_true",  help="Overwrite output file if it exists")
    return p.parse_args()


def get_video_resolution(path: str) -> tuple[int,int]:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json", path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    info = json.loads(res.stdout)
    return int(info["streams"][0]["width"]), int(info["streams"][0]["height"])


def chunk_words(words: list[dict], max_len: int) -> list[list[dict]]:
    chunks, curr = [], []
    for wd in words:
        curr.append(wd)
        txt = wd['word']
        if txt.endswith(('.', '?', '!')) or len(curr) >= max_len:
            chunks.append(curr)
            curr = []
    if curr:
        chunks.append(curr)
    return chunks


def main():
    args = parse_args()
    threads = multiprocessing.cpu_count()

    W, H = get_video_resolution(args.input_video)
    if args.margin is not None:
        margin_px = args.margin
    else:
        margin_px = H * (args.margin_percent / 100)
    data = json.loads(Path(args.json_file).read_text(encoding='utf-8'))
    font = ImageFont.truetype(args.font_path, args.font_size)
    y_base = H - margin_px

    filters = []
    for seg in data.get('segments', []):
        words = seg.get('words', [])
        if not words:
            continue
        for chunk in chunk_words(words, args.max_words):
            raw_line = ' '.join(w['word'] for w in chunk)
            safe = raw_line.replace('\\', '\\\\') \
                            .replace("'", "’") \
                            .replace(',', '\\,') \
                            .replace(':', '\\:') \
                            .replace('%', ' percent')
            lw, lh = font.getsize(raw_line)
            st, et = chunk[0]['start'], chunk[-1]['end']
            px = 0
            for i, wd in enumerate(chunk):
                s_t = wd['start']
                e_t = chunk[i+1]['start'] if i+1 < len(chunk) else wd['end']
                wtxt = wd['word']
                wpx, _ = font.getsize(wtxt)
                x0 = (W - lw)/2 + px - args.pad
                y0 = y_base - args.pad
                wbox, hbox = wpx + args.pad*2, lh + args.pad*2
                filters.append(
                    f"drawbox=x={x0:.1f}:y={y0:.1f}:w={wbox:.1f}:h={hbox:.1f}:"
                    f"color={args.box_color}:t=fill:"
                    f"enable='between(t,{s_t:.3f},{e_t:.3f})'"
                )
                adv, _ = font.getsize(wtxt + ' ')
                px += adv
            # text with border and shadow
            filters.append(
                f"drawtext=fontfile='{args.font_path}':"
                f"text='{safe}':"
                f"fontcolor={args.font_color}:fontsize={args.font_size}:"
                f"borderw=2:bordercolor=black:"
                f"shadowcolor=black:shadowx=2:shadowy=2:"
                f"x=(w-{lw})/2:y={y_base}:"
                f"enable='between(t,{st:.3f},{et:.3f})'"
            )

    vid_chain = f"[0:v]scale={W}:{H},format=yuv420p,{','.join(filters)}[v]"
    aud_chain = (
        "[1:a]volume=1.0[a1];"
        "[2:a]volume=1.0[a2];"
        "[a1][a2]amix=inputs=2:duration=longest[aout]"
    )
    Path(args.filter_graph).write_text(vid_chain + ";" + aud_chain, encoding='utf-8')
    # print(f"Wrote {args.filter_graph}")

    overwrite_flag = "-y " if args.overwrite else ""
    cmd = (
        f"ffmpeg {overwrite_flag}-threads {threads} -filter_complex_threads {threads} "
        f"-i {args.input_video} -i {args.acc_wav} -i {args.voc_wav} "
        f"-filter_complex_script {args.filter_graph} "
        f"-map [v] -map [aout] "
        f"-c:v h264_nvenc -crf 18 -preset medium "
        f"-c:a aac -b:a 192k -shortest output_karaoke.mp4"
    )
    print(cmd)

if __name__ == '__main__':
    main()

