# Karaoke Subtitle Video Generator

This script takes an input video and word timings from a WhisperX JSON file (see example.json), and generate an complex ffmpeg filter with karaoke-style subtitles.

## Features

- **Karaoke-style highlighting:** Words are highlighted as they are sung.
- **Customizable appearance:** Font, size, color, and position of subtitles can be adjusted.

## Demonstration

![Karaoke Subtitles Demonstration](https://via.placeholder.com/800x450.png?text=Karaoke+Subtitles+Demonstration)

## Dependencies

- **Python 3**
- **ffmpeg and ffprobe:** Must be installed and available in your system's PATH.
- **Pillow:** The Python Imaging Library (`pip install Pillow`).
- **A monospaced font:** The script defaults to Nimbus Mono PS, but you can specify any font file.

## Usage

The script is controlled via command-line arguments.

```bash
python3 karaoke.py [OPTIONS]
```

### Options

| Argument | Description | Default |
|---|---|---|
| `--input-video` | Path to the input video file. | `original.mp4` |
| `--json-file` | Path to the WhisperX JSON file with word timings. | `vocals-en-corrected-aligned.json` |
| `--acc-wav` | Path to the accompaniment audio WAV file. | `original_accompaniment.wav` |
| `--voc-wav` | Path to the vocals audio WAV file. | `vocals-en.wav` |
| `--filter-graph` | Output path for the generated ffmpeg filter graph file. | `filter_graph.txt` |
| `--font-path` | Path to the TTF font file to use for subtitles. | `/usr/share/fonts/opentype/urw-base35/NimbusMonoPS-Bold.otf` |
| `--font-size` | Font size in pixels. | `60` |
| `--margin` | Bottom margin for the subtitles in pixels. | `400` |
| `--max-words` | Maximum number of words to display in a single subtitle line. | `5` |
| `--pad` | Padding around each highlight box in pixels. | `10` |
| `--box-color` | Highlight box color in hex format (e.g., `0x00A5FF`). | `0x00A5FF` |
| `--font-color` | Font color for the text overlay. | `white` |

## Example

The script will print an `ffmpeg` command to the console. You can execute this command to generate the final video.

1.  **Generate the filter graph:**

    ```bash
    python3 karaoke.py \
        --input-video my_video.mp4 \
        --json-file my_lyrics.json \
        --acc-wav accompaniment.wav \
        --voc-wav vocals.wav
    ```

2.  **Run the `ffmpeg` command:**

    The script will output a command similar to this:

    ```bash
    ffmpeg -threads 16 -filter_complex_threads 16 -i my_video.mp4 -i accompaniment.wav -i vocals.wav -filter_complex_script filter_graph.txt -map [v] -map [aout] -c:v h264_nvenc -crf 18 -preset medium -c:a aac -b:a 192k -shortest output_karaoke.mp4
    ```

    Copy and paste this command into your terminal and run it to create the final `output_karaoke.mp4` file.

```
