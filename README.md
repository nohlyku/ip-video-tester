# IP Video Stream Publisher

Pushes up to 4 test video streams to an RTSP or SRT server using ffmpeg. Good for testing video pipelines, NVRs, decoders, or anything else that needs a live stream without a real camera.

![screenshot placeholder]

---

## What you need

- **ffmpeg** — either on your PATH or placed next to the script/exe
- A streaming server — [MediaMTX](https://github.com/bluenviron/mediamtx) is the easiest option
- Python 3.10+ (only if running the script directly; not needed for the .exe)

---

## Quickstart

### 1. Get ffmpeg

**Windows** — download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (grab `ffmpeg-release-essentials.zip`), extract it, and either add the `bin/` folder to your PATH or drop `ffmpeg.exe` next to the app.

**Linux**
```bash
sudo apt install ffmpeg
```

**macOS**
```bash
brew install ffmpeg
```

### 2. Start a server

MediaMTX works out of the box with no config needed:

```bash
docker run --rm -p 8554:8554 -p 8890:8890/udp bluenviron/mediamtx
```

That gives you an RTSP server on port 8554 and SRT on 8890. Any path you publish to gets created automatically.

### 3. Run the app

**From the .exe** (Windows) — just double-click `IPVideoPublisher.exe`.

**From source**
```bash
python ip_video_test_publisher.py
```

No pip installs needed — only standard library.

---

## Using the app

Pick your protocol at the top (RTSP or SRT), then configure each stream row — host, port, and path. Hit **Start** on individual streams or **Start All** to kick them all off at once.

Each stream has a couple of extra options:

- **Source** — either a built-in test pattern or an MP4 file. For MP4, click Browse and pick a file; it'll loop automatically.
- **Overlay label** — text burned into the top-left of the video. Defaults to the stream name or filename. Clear it to hide.
- **Show clock** — real-time clock in the top-right corner. Uncheck to turn it off.

You can't switch protocols while streams are running — stop them first.

### Watching the streams

```bash
# RTSP
ffplay rtsp://127.0.0.1:8554/stream1

# SRT
ffplay srt://127.0.0.1:8890?streamid=read:/stream1
```

VLC works too — just paste the URL into Media → Open Network Stream.

### Default streams

| # | Pattern | RTSP | SRT stream ID |
|---|---------|------|---------------|
| 1 | SMPTE Bars | `/stream1` | `stream1` |
| 2 | Test Pattern | `/stream2` | `stream2` |
| 3 | Solid Blue | `/stream3` | `stream3` |
| 4 | Noise | `/stream4` | `stream4` |

All streams push **1280×720 @ 30fps, H.264, ~2 Mbps**.

---

## Building the .exe (Windows)

Place `ffmpeg.exe` in the repo folder, then run:

```bat
build.bat
```

This installs PyInstaller if needed and bundles everything into `dist\IPVideoPublisher.exe`. The resulting exe includes ffmpeg — no separate install required on the target machine.

---

## Troubleshooting

**"ffmpeg not found"** — Put `ffmpeg.exe` on your PATH or in the same folder as the script/exe.

**No text overlay** — The app couldn't find a TTF font. Streams still work fine, just without burned-in text. On Windows this shouldn't happen; on Linux you may need to install `fonts-dejavu`.

**Stream starts then immediately stops** — Check the server is up and the port is right. The console window (or log output) will have the ffmpeg error.

**MP4 won't play** — Make sure ffmpeg can decode the file. H.264/AAC .mp4 files work universally. Audio is stripped automatically.

