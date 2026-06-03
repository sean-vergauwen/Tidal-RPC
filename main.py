"""TIDAL -> Discord Rich Presence.

Reads the currently playing track from the TIDAL desktop app's window title,
looks up album art via the TIDAL API, and shows it on Discord as a
"Listening to ..." activity with a progress bar.
"""

import re
import sys
import time
import ctypes
import webbrowser
from ctypes import wintypes
from pathlib import Path
from typing import Optional

import psutil
import tidalapi
from pypresence import Presence
from pypresence.types import ActivityType

# --- Paths (works whether run as a script or a frozen PyInstaller exe) ---
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent

SESSION_FILE = BASE_DIR / "tidal-session-oauth.json"

# --- Config ---
CLIENT_ID = 1236873477311430716
TIDAL_TEXT = "TIDAL"
FALLBACK_IMG = (
    "https://encrypted-tbn0.gstatic.com/images?"
    "q=tbn:ANd9GcS0TiNtfzWOOKq0-a6sRKgrRYGKdyjC2ICWnalfiLykMQ&s"
)

# Seconds between window-title checks. Short so a track change is noticed
# quickly; we only push to Discord when something actually changes, which keeps
# us within Discord's activity-update rate limit.
POLL_INTERVAL = 2
# Seconds to wait between attempts to (re)connect to Discord.
RECONNECT_DELAY = 15

_user32 = ctypes.windll.user32


def _window_title(hwnd) -> str:
    length = _user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    _user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def _window_pid(hwnd) -> int:
    pid = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _all_window_handles() -> list:
    """Return every top-level window handle via EnumWindows."""
    handles = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def collect(hwnd, _lparam):
        handles.append(hwnd)
        return True

    _user32.EnumWindows(collect, 0)
    return handles


def _parse_title(window_title: str):
    """Split a TIDAL window title ("Song - Artist") into (song, artist)."""
    parts = window_title.split(" - ")
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()
    return None, None


def get_current_track():
    """Return (song, artist) for the playing TIDAL track, or (None, None)."""
    tidal_pids = {
        proc.info["pid"]
        for proc in psutil.process_iter(["pid", "name"])
        if proc.info["name"] and "TIDAL.exe" in proc.info["name"]
    }
    if not tidal_pids:
        return None, None

    for hwnd in _all_window_handles():
        if _window_pid(hwnd) in tidal_pids:
            song, artist = _parse_title(_window_title(hwnd))
            if song and artist:
                return song, artist
    return None, None


def lookup_metadata(session: tidalapi.Session, song: str, artist: str):
    """Look up (album_art_url, album_name, duration_seconds) for a track.

    Falls back to a placeholder image and unknown album/duration when the
    TIDAL search returns no match.
    """
    results = session.search(f"{artist} - {song}", limit=1)
    tracks = results["tracks"]
    if not tracks:
        return FALLBACK_IMG, None, None

    track = tracks[0]
    album_art = session.album(track.album.id).image(640, 640)
    return album_art, track.album.name, track.duration


def show_login_prompt(text: str) -> None:
    """`fn_print` for hidden (no-console) mode: open the browser and surface the
    TIDAL login link in a message box so it's visible during first-time login.
    """
    match = re.search(r"https://\S+", text)
    if match:
        webbrowser.open(match.group(0))
    _user32.MessageBoxW(
        0,
        text + "\n\nA browser window was opened for you to log in to TIDAL.",
        "TIDAL RPC — first-time login",
        0x40,  # MB_ICONINFORMATION
    )


def connect_rpc() -> Presence:
    """Connect to Discord, retrying since it may not be running yet at boot."""
    while True:
        try:
            rpc = Presence(CLIENT_ID)
            rpc.connect()
            return rpc
        except Exception:
            time.sleep(RECONNECT_DELAY)


def show_track(rpc: Presence, session: tidalapi.Session, song: str, artist: str,
               start_ts: int) -> None:
    """Push the given track to Discord as a Listening activity."""
    album_art, album_name, duration = lookup_metadata(session, song, artist)

    rpc.update(
        activity_type=ActivityType.LISTENING,
        details=song,
        state=f"by {artist}",
        large_image=album_art,
        large_text=album_name or f"{artist} - {song}",  # shown on art hover
        small_image=FALLBACK_IMG,
        small_text=TIDAL_TEXT,  # shown on small-icon hover
        start=start_ts,
        end=start_ts + duration if duration else None,
    )


def main() -> None:
    session = tidalapi.Session()
    session.login_session_file(SESSION_FILE, fn_print=show_login_prompt)

    rpc = connect_rpc()
    current_key: Optional[str] = None  # track shown to Discord (None = nothing)

    while True:
        try:
            song, artist = get_current_track()
            key = f"{artist} - {song}" if (song and artist) else None

            if key != current_key:
                if key is not None:
                    # Stamp the start before the (slower) network lookups so the
                    # progress bar lines up. The window title has no playback
                    # position, so this assumes the track started when first
                    # seen (pause/seek won't be reflected).
                    show_track(rpc, session, song, artist, int(time.time()))
                else:
                    rpc.clear()  # nothing playing: remove the activity entirely
                current_key = key

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            try:
                rpc.close()
            except Exception:
                pass
            break
        except Exception:
            # Discord likely closed/restarted: reconnect and force a re-push.
            try:
                rpc.close()
            except Exception:
                pass
            rpc = connect_rpc()
            current_key = None
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
