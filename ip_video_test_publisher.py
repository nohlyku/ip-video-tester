#!/usr/bin/env python3
"""
IP Video Stream Publisher
Generates and pushes 4 independent video streams to a remote server
(e.g. MediaMTX) using ffmpeg subprocesses. Supports RTSP and SRT protocols.
Auto-reconnects on failure.

Requirements:
    - Windows: Download ffmpeg from https://ffmpeg.org/download.html
    - Linux/Mac: sudo apt-get install ffmpeg (or brew install ffmpeg)

Usage:
    python ip_video_test_publisher.py
"""

import subprocess
import shutil
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import logging
import platform

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ip_video_publisher")

RECONNECT_DELAY = 3  # seconds between reconnect attempts

# ── Platform-specific font detection ─────────────────────────────────────────
def get_default_font():
    """Returns a font file path that exists on the current platform."""
    system = platform.system()
    
    if system == "Windows":
        # Common Windows fonts
        candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/verdana.ttf",
        ]
    elif system == "Darwin":  # macOS
        candidates = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    else:  # Linux
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]
    
    for font in candidates:
        try:
            # Check if file exists
            with open(font, 'rb'):
                return font
        except (FileNotFoundError, PermissionError):
            continue
    
    # Fallback - no text overlay if font not found
    log.warning("No suitable font found, text overlay will be disabled")
    return None


# ── Stream Definitions ────────────────────────────────────────────────────────
STREAM_PRESETS = [
    {
        "label": "Stream 1 - SMPTE Bars",
        "src": "smptebars=size=1280x720:rate=30",
        "rtsp_default_host": "127.0.0.1",
        "rtsp_default_port": "8554",
        "rtsp_default_path": "/stream1",
        "srt_default_host": "127.0.0.1",
        "srt_default_port": "8890",
        "srt_default_streamid": "stream1",
    },
    {
        "label": "Stream 2 - Test Pattern",
        "src": "testsrc=size=1280x720:rate=30",
        "rtsp_default_host": "127.0.0.1",
        "rtsp_default_port": "8554",
        "rtsp_default_path": "/stream2",
        "srt_default_host": "127.0.0.1",
        "srt_default_port": "8890",
        "srt_default_streamid": "stream2",
    },
    {
        "label": "Stream 3 - Color Bars",
        "src": "color=c=blue:size=1280x720:rate=30",
        "rtsp_default_host": "127.0.0.1",
        "rtsp_default_port": "8554",
        "rtsp_default_path": "/stream3",
        "srt_default_host": "127.0.0.1",
        "srt_default_port": "8890",
        "srt_default_streamid": "stream3",
    },
    {
        "label": "Stream 4 - Noise",
        "src": "nullsrc=size=1280x720:rate=30,geq=random(1)*255:128:128",
        "rtsp_default_host": "127.0.0.1",
        "rtsp_default_port": "8554",
        "rtsp_default_path": "/stream4",
        "srt_default_host": "127.0.0.1",
        "srt_default_port": "8890",
        "srt_default_streamid": "stream4",
    },
]


# ── Stream Publisher ──────────────────────────────────────────────────────────
class StreamPublisher:
    """
    Pushes an ffmpeg-generated test stream to a remote RTSP or SRT server
    (e.g. MediaMTX) via ffmpeg subprocess. Auto-reconnects on failure.
    """

    def __init__(self, protocol: str, host: str, port: int, path_or_streamid: str,
                 src_filter: str, label: str, stream_id: str, font_path: str = None):
        self.protocol = protocol.upper()  # "RTSP" or "SRT"
        self.host = host
        self.port = port
        self.path_or_streamid = path_or_streamid
        self.src_filter = src_filter
        self.label = label
        self.stream_id = stream_id
        self.font_path = font_path

        self._proc = None
        self._monitor_thread = None
        self._running = False
        self._should_run = False
        self._error = None
        self._reconnect_count = 0

    @property
    def url(self):
        if self.protocol == "RTSP":
            path = self.path_or_streamid if self.path_or_streamid.startswith("/") else f"/{self.path_or_streamid}"
            return f"rtsp://{self.host}:{self.port}{path}"
        else:  # SRT
            return f"srt://{self.host}:{self.port}?streamid=publish:{self.path_or_streamid}&pkt_size=1316"

    @property
    def display_url(self):
        if self.protocol == "RTSP":
            return self.url
        else:  # SRT
            return f"srt://{self.host}:{self.port} (/{self.path_or_streamid})"

    def _build_cmd(self):
        cmd = [
            "ffmpeg",
            "-re",
            "-f", "lavfi",
            "-i", self.src_filter,
        ]
        
        # Add text overlay if font is available
        if self.font_path:
            safe_label = self.label.replace(":", "\\:").replace("'", "\\'")
            label_filter = (
                f"drawtext=fontfile={self.font_path}:"
                f"text='ID\\: {self.stream_id}  {safe_label}':"
                f"fontsize=28:fontcolor=white:borderw=2:x=10:y=10"
            )
            clock_filter = (
                f"drawtext=fontfile={self.font_path}:"
                f"text='%{{localtime\\:%X}}':"
                f"fontsize=28:fontcolor=white:borderw=2:x=(w-tw-10):y=10"
            )
            overlay = f"{label_filter},{clock_filter}"
            cmd.extend(["-vf", overlay])
        
        # Common encoding settings
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-b:v", "2000k",
            "-g", "30",
        ])
        
        # Protocol-specific output settings
        if self.protocol == "RTSP":
            cmd.extend([
                "-f", "rtsp",
                "-rtsp_transport", "tcp",
                self.url,
            ])
        else:  # SRT
            cmd.extend([
                "-f", "mpegts",
                self.url,
            ])
        
        return cmd

    def _launch(self):
        cmd = self._build_cmd()
        log.info("Launching ffmpeg to %s", self.display_url)
        log.debug("Command: %s", " ".join(cmd))

        self._error = None
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._running = True
        log.info("ffmpeg started (pid %d), pushing to %s", self._proc.pid, self.display_url)

    def start(self):
        if self._should_run:
            log.warning("Publisher %s already active, ignoring start", self.display_url)
            return

        self._should_run = True
        self._reconnect_count = 0
        self._launch()

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True
        )
        self._monitor_thread.start()

    def _monitor_loop(self):
        """Monitor ffmpeg and auto-reconnect on unexpected exit."""
        while self._should_run:
            proc = self._proc
            if proc is None:
                break

            _, stderr = proc.communicate()
            rc = proc.returncode
            self._running = False

            output = stderr.decode(errors="replace").strip()

            if not self._should_run:
                log.debug("[ffmpeg pid %d] stopped by user", proc.pid)
                break

            if output:
                lines = output.splitlines()
                error_lines = [l for l in lines[-10:]
                               if not l.startswith("frame=") and l.strip()]
                for line in error_lines:
                    log.warning("[ffmpeg pid %d] %s", proc.pid, line)

            self._reconnect_count += 1
            log.warning(
                "Publisher for %s exited (code %d), reconnecting in %ds (attempt #%d)",
                self.display_url, rc, RECONNECT_DELAY, self._reconnect_count,
            )

            time.sleep(RECONNECT_DELAY)

            if self._should_run:
                try:
                    self._launch()
                except Exception as exc:
                    log.error("Reconnect failed for %s: %s", self.display_url, exc)
                    self._error = str(exc)
                    self._should_run = False

    def stop(self):
        if not self._should_run:
            return
        self._should_run = False
        self._running = False
        if self._proc and self._proc.poll() is None:
            log.info("Stopping publisher for %s (pid %d)", self.display_url, self._proc.pid)
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log.warning("Force-killing ffmpeg pid %d", self._proc.pid)
                self._proc.kill()
        log.info("Publisher stopped (%s)", self.display_url)

    @property
    def last_error(self):
        return self._error


# ── GUI ───────────────────────────────────────────────────────────────────────
class StreamRow:
    """One row of controls for a single stream."""

    def __init__(self, parent_frame, row_index: int, preset: dict, protocol_var: tk.StringVar, font_path: str):
        self.preset = preset
        self.protocol_var = protocol_var
        self.font_path = font_path
        self.publisher: StreamPublisher | None = None
        self._row = row_index

        # ── Label
        tk.Label(
            parent_frame,
            text=preset["label"],
            font=("Helvetica", 11, "bold"),
            anchor="w",
            width=26,
        ).grid(row=row_index, column=0, padx=(8, 4), pady=6, sticky="w")

        # ── Host
        tk.Label(parent_frame, text="Host:").grid(row=row_index, column=1, sticky="e")
        self.host_var = tk.StringVar(value=preset["rtsp_default_host"])
        self.host_entry = tk.Entry(parent_frame, textvariable=self.host_var, width=14)
        self.host_entry.grid(row=row_index, column=2, padx=4)

        # ── Port
        tk.Label(parent_frame, text="Port:").grid(row=row_index, column=3, sticky="e")
        self.port_var = tk.StringVar(value=preset["rtsp_default_port"])
        self.port_entry = tk.Entry(parent_frame, textvariable=self.port_var, width=6)
        self.port_entry.grid(row=row_index, column=4, padx=4)

        # ── Path/Stream ID (changes based on protocol)
        self.path_label = tk.Label(parent_frame, text="Path:")
        self.path_label.grid(row=row_index, column=5, sticky="e")
        self.path_var = tk.StringVar(value=preset["rtsp_default_path"])
        self.path_entry = tk.Entry(parent_frame, textvariable=self.path_var, width=14)
        self.path_entry.grid(row=row_index, column=6, padx=4)

        # ── Stream ID (display ID for overlay)
        tk.Label(parent_frame, text="ID:").grid(row=row_index, column=7, sticky="e")
        self.id_var = tk.StringVar(value=str(row_index + 1))
        self.id_entry = tk.Entry(parent_frame, textvariable=self.id_var, width=6)
        self.id_entry.grid(row=row_index, column=8, padx=4)

        # ── Start / Stop
        self.btn = tk.Button(
            parent_frame,
            text="▶ Start",
            bg="#28a745",
            fg="white",
            font=("Helvetica", 10, "bold"),
            width=9,
            command=self.toggle,
        )
        self.btn.grid(row=row_index, column=9, padx=6)

        # ── Status
        self.status_var = tk.StringVar(value="Stopped")
        self.status_label = tk.Label(
            parent_frame,
            textvariable=self.status_var,
            width=52,
            anchor="w",
            fg="#888",
            font=("Courier", 9),
        )
        self.status_label.grid(row=row_index, column=10, padx=(6, 8), sticky="w")

    def update_protocol_fields(self):
        """Update field labels and defaults when protocol changes."""
        protocol = self.protocol_var.get()
        
        if protocol == "RTSP":
            self.path_label.config(text="Path:")
            self.host_var.set(self.preset["rtsp_default_host"])
            self.port_var.set(self.preset["rtsp_default_port"])
            self.path_var.set(self.preset["rtsp_default_path"])
        else:  # SRT
            self.path_label.config(text="Stream ID:")
            self.host_var.set(self.preset["srt_default_host"])
            self.port_var.set(self.preset["srt_default_port"])
            self.path_var.set(self.preset["srt_default_streamid"])

    def toggle(self):
        if self.publisher and self.publisher._should_run:
            self._stop()
        else:
            self._start()

    def _start(self):
        try:
            host = self.host_var.get().strip()
            port = int(self.port_var.get().strip())
            path_or_streamid = self.path_var.get().strip()
            stream_id = self.id_var.get().strip()
            protocol = self.protocol_var.get()
        except ValueError:
            log.error("Invalid port value: %r", self.port_var.get())
            messagebox.showerror("Invalid Input", "Port must be an integer.")
            return

        try:
            self.publisher = StreamPublisher(
                protocol, host, port, path_or_streamid,
                self.preset["src"],
                self.preset["label"],
                stream_id,
                self.font_path,
            )
            self.publisher.start()
        except Exception as exc:
            log.error("Failed to start %s: %s", self.preset["label"], exc, exc_info=True)
            messagebox.showerror("Start Error", str(exc))
            return

        url = self.publisher.display_url
        self.status_var.set(f"● PUSHING  →  {url}")
        self.status_label.config(fg="#28a745")
        self.btn.config(text="■ Stop", bg="#dc3545")
        self._set_fields_state("disabled")

    def _stop(self):
        if self.publisher:
            log.info("Stopping %s", self.preset["label"])
            self.publisher.stop()
            self.publisher = None

        self.status_var.set("Stopped")
        self.status_label.config(fg="#888")
        self.btn.config(text="▶ Start", bg="#28a745")
        self._set_fields_state("normal")

    def _set_fields_state(self, state):
        for widget in [self.host_entry, self.port_entry, self.path_entry, self.id_entry]:
            widget.config(state=state)


class App:
    def __init__(self, root: tk.Tk, font_path: str):
        self.font_path = font_path
        root.title("IP Video Stream Publisher")
        root.resizable(True, False)

        # ── Header
        hdr = tk.Frame(root, bg="#1a1a2e", pady=10)
        hdr.pack(fill="x")
        tk.Label(
            hdr,
            text="IP Video Stream Publisher",
            bg="#1a1a2e",
            fg="white",
            font=("Helvetica", 16, "bold"),
        ).pack(side="left", padx=16)
        tk.Label(
            hdr,
            text="Push 4 test streams via RTSP or SRT",
            bg="#1a1a2e",
            fg="#aaa",
            font=("Helvetica", 10),
        ).pack(side="left")

        # ── Protocol Selector
        protocol_frame = tk.Frame(root, bg="#e8e8e8", pady=8)
        protocol_frame.pack(fill="x")
        
        tk.Label(
            protocol_frame,
            text="Protocol:",
            bg="#e8e8e8",
            font=("Helvetica", 10, "bold"),
        ).pack(side="left", padx=(16, 8))
        
        self.protocol_var = tk.StringVar(value="RTSP")
        
        rtsp_radio = tk.Radiobutton(
            protocol_frame,
            text="RTSP",
            variable=self.protocol_var,
            value="RTSP",
            bg="#e8e8e8",
            font=("Helvetica", 10),
            command=self._on_protocol_change,
        )
        rtsp_radio.pack(side="left", padx=8)
        
        srt_radio = tk.Radiobutton(
            protocol_frame,
            text="SRT",
            variable=self.protocol_var,
            value="SRT",
            bg="#e8e8e8",
            font=("Helvetica", 10),
            command=self._on_protocol_change,
        )
        srt_radio.pack(side="left", padx=8)
        
        tk.Label(
            protocol_frame,
            text="⚠ Change protocol before starting streams",
            bg="#e8e8e8",
            fg="#d9534f",
            font=("Helvetica", 9, "italic"),
        ).pack(side="left", padx=16)

        # ── Stream grid
        grid = tk.Frame(root, pady=6)
        grid.pack(fill="x", padx=8)

        headers = ["Stream", "Host", "", "Port", "", "Path/Stream ID", "", "ID", "", "Control", "Status / URL"]
        for col, text in enumerate(headers):
            tk.Label(grid, text=text, font=("Helvetica", 9, "bold"), fg="#555").grid(
                row=0, column=col, padx=4, sticky="w"
            )

        ttk.Separator(grid, orient="horizontal").grid(
            row=1, column=0, columnspan=len(headers), sticky="ew", pady=4
        )

        self.rows = []
        for i, preset in enumerate(STREAM_PRESETS):
            row = StreamRow(grid, i + 2, preset, self.protocol_var, self.font_path)
            self.rows.append(row)

        # ── Footer
        footer = tk.Frame(root, bg="#f4f4f4", pady=6)
        footer.pack(fill="x")

        tk.Button(
            footer,
            text="▶ Start All",
            bg="#007bff",
            fg="white",
            font=("Helvetica", 10, "bold"),
            command=self.start_all,
            width=12,
        ).pack(side="left", padx=10)

        tk.Button(
            footer,
            text="■ Stop All",
            bg="#6c757d",
            fg="white",
            font=("Helvetica", 10, "bold"),
            command=self.stop_all,
            width=12,
        ).pack(side="left", padx=4)

        self.footer_label = tk.Label(
            footer,
            text="RTSP: ffplay rtsp://host:port/path  |  SRT: ffplay srt://host:port?streamid=read:/streamid",
            bg="#f4f4f4",
            fg="#666",
            font=("Helvetica", 9, "italic"),
        )
        self.footer_label.pack(side="left", padx=20)

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _on_protocol_change(self):
        """Update all stream rows when protocol changes."""
        # Only allow changing if no streams are running
        for row in self.rows:
            if row.publisher and row.publisher._should_run:
                messagebox.showwarning(
                    "Streams Running",
                    "Stop all streams before changing protocol."
                )
                # Revert the selection
                self.protocol_var.set(row.publisher.protocol)
                return
        
        # Update all rows
        for row in self.rows:
            row.update_protocol_fields()

    def start_all(self):
        for row in self.rows:
            if not (row.publisher and row.publisher._should_run):
                row._start()

    def stop_all(self):
        for row in self.rows:
            if row.publisher and row.publisher._should_run:
                row._stop()

    def on_close(self):
        log.info("Shutting down - stopping all streams")
        self.stop_all()
        log.info("All streams stopped, exiting")
        root.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if shutil.which("ffmpeg") is None:
        msg = (
            "ffmpeg not found on PATH.\n\n"
            "Windows: Download from https://ffmpeg.org/download.html\n"
            "Linux: sudo apt-get install ffmpeg\n"
            "macOS: brew install ffmpeg"
        )
        log.critical(msg)
        messagebox.showerror("ffmpeg not found", msg)
        sys.exit(1)

    font_path = get_default_font()
    if font_path:
        log.info("Using font: %s", font_path)
    else:
        log.info("No font found - text overlay disabled")

    log.info("ffmpeg found - launching GUI")
    root = tk.Tk()
    App(root, font_path)
    root.mainloop()
