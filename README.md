# IP Video Stream Publisher

A cross-platform Tkinter GUI tool that generates and pushes up to 4 independent test video streams to a remote server (e.g. MediaMTX) using ffmpeg. Supports both **RTSP** and **SRT** protocols.

## Prerequisites

- **Python 3.10+** (uses only standard library modules)
- **ffmpeg** with `libx264` support
- A streaming server accepting RTSP or SRT connections (e.g. [MediaMTX](https://github.com/bluenviron/mediamtx))

## Setup

### 1. Install ffmpeg

#### Windows
1. Download ffmpeg from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Extract the zip file
3. Add the `bin` folder to your PATH, or place `ffmpeg.exe` in the same folder as the script

#### Linux (including WSL)
```bash
sudo apt-get update && sudo apt-get install -y ffmpeg
```

#### macOS
```bash
brew install ffmpeg
```

### 2. Start a streaming server

If you don't already have one running, MediaMTX is the easiest option and supports both protocols:

```bash
# RTSP (port 8554) + SRT (port 8890)
docker run --rm -p 8554:8554 -p 8890:8890/udp bluenviron/mediamtx
```

This starts a server on `localhost` that auto-creates stream paths on first publish.

### 3. Run the publisher

```bash
python ip_video_test_publisher.py
```

Or on Windows, you can double-click the file if Python is associated with `.py` files.

No virtual environment or pip packages required — the script uses only the Python standard library.

## Usage

1. **Select Protocol** — Choose RTSP or SRT using the radio buttons at the top
2. **Configure Streams** — Each row represents one stream with configurable host, port, path/stream ID, and display ID
3. **Click "Start"** on individual streams or **"Start All"** to begin publishing
4. The status column shows `PUSHING → url` when a stream is active
5. **Click "Stop"** or **"Stop All"** to terminate streams

**Important**: Change the protocol BEFORE starting any streams. You cannot change protocols while streams are running.

### Viewing streams

#### RTSP
Connect to published streams with any RTSP client:

```bash
# ffplay
ffplay rtsp://127.0.0.1:8554/stream1

# VLC
vlc rtsp://127.0.0.1:8554/stream1

# Or in VLC: Media → Open Network Stream → paste the URL
```

#### SRT
Connect to published SRT streams:

```bash
# ffplay
ffplay srt://127.0.0.1:8890?streamid=read:/stream1

# VLC (if SRT support is enabled)
vlc srt://127.0.0.1:8890?streamid=read:/stream1
```

### Default Configuration

| Stream | Pattern | RTSP Path | SRT Stream ID |
|--------|---------|-----------|---------------|
| 1 | SMPTE Bars | `/stream1` | `stream1` |
| 2 | Test Pattern | `/stream2` | `stream2` |
| 3 | Blue + Label | `/stream3` | `stream3` |
| 4 | Noise | `/stream4` | `stream4` |

All streams output **1280x720 @ 30fps H.264** at **2 Mbps** with a real-time clock and stream ID overlay.

## Platform-Specific Notes

### Windows
- The GUI works natively on Windows 10/11
- Fonts are automatically detected from `C:/Windows/Fonts/`
- If ffmpeg is not in PATH, you can place `ffmpeg.exe` in the same folder as the script

### Linux
- Fonts are automatically detected from `/usr/share/fonts/`
- Requires X11 display (should work out of the box on most desktop distros)

### WSL (Windows Subsystem for Linux)
- **Windows 11 (WSL2)**: WSLg is built-in — the GUI should appear automatically
- **Windows 10**: Install [VcXsrv](https://sourceforge.net/projects/vcxsrv/) or similar X server, then run:
  ```bash
  export DISPLAY=:0
  python3 ip_video_test_publisher.py
  ```

### macOS
- Fonts are automatically detected from system font directories
- GUI uses native Tkinter (included with Python)

## Protocol Comparison

| Feature | RTSP | SRT |
|---------|------|-----|
| **Default Port** | 8554 | 8890 |
| **Transport** | TCP | UDP |
| **Latency** | ~1-2 seconds | ~200-500ms |
| **Network Resilience** | Good | Excellent (packet recovery) |
| **Firewall Friendly** | Yes (TCP) | May need UDP forwarding |
| **Use Case** | Standard IP cameras, general streaming | Low-latency, internet streaming |

## Logging

All events are logged to the console with timestamps:

```
14:20:08 [INFO] ffmpeg found - launching GUI
14:20:10 [INFO] Launching ffmpeg to rtsp://127.0.0.1:8554/stream1
14:20:10 [INFO] ffmpeg started (pid 10211), pushing to rtsp://127.0.0.1:8554/stream1
14:20:45 [INFO] Stopping publisher for rtsp://127.0.0.1:8554/stream1 (pid 10211)
```

Change `level=logging.INFO` in the script to reduce verbosity (only warnings and errors).

## Troubleshooting

### "ffmpeg not found"
- **Windows**: Ensure `ffmpeg.exe` is in PATH or in the same folder as the script
- **Linux/Mac**: Install with your package manager (`apt`, `brew`, etc.)

### No text overlay on streams
- The script couldn't find a suitable font file
- Streams will work fine, just without the clock and ID overlay
- On Windows, ensure fonts exist in `C:/Windows/Fonts/`

### Stream won't start or immediately fails
- Check that the server is running and accessible
- Verify the port is correct (8554 for RTSP, 8890 for SRT)
- Check the console logs for detailed ffmpeg error messages

### GUI doesn't appear (WSL on Windows 10)
- Install and configure an X server like VcXsrv
- Set `DISPLAY` environment variable: `export DISPLAY=:0`
