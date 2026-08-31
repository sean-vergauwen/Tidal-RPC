# TIDAL Discord Rich Presence

Shows what you're currently playing on the TIDAL desktop app as a Discord
status. Discord displays it as **"Listening to …"** with the song title, artist,
album art, and a live progress bar. When nothing is playing, the activity is
removed entirely.

The card looks like:

```
Listening to TIDAL
<Song title>
by <Artist>
<Album name>
▓▓▓▓▓░░░░░  1:23 / 3:45
```

## PSA

I will not maintain this project anymore, fork it or clone it if you want to make any modifications, thank you.

## Two ways to run it

### A) Standalone Windows app (recommended)

A prebuilt, no-install executable that runs hidden in the background and can
start automatically with Windows. See [Build the exe](#build-the-exe) and
[Run at startup](#run-at-startup) below. All the logic lives in
[`main.py`](main.py).

### B) Plain Python script

Run [`main.py`](main.py) directly with Python.

## Dependencies

- Python 3.x
- [psutil](https://pypi.org/project/psutil/)
- [pypresence](https://pypi.org/project/pypresence/) (4.6+, for the
  "Listening to" activity type)
- [tidalapi](https://pypi.org/project/tidalapi/)

Install them from [`requirements.txt`](requirements.txt):

```bash
pip install -r requirements.txt
```

## Usage (Python script)

1. Make sure the **TIDAL desktop app** and **Discord** are running.
2. Run it:

   ```bash
   python main.py
   ```

3. **First run only:** a browser window and a popup open with a TIDAL login
   link. Log in once — your session is saved to `tidal-session-oauth.json`
   (next to the executable/script) and reused automatically afterwards.

Your Discord status updates within a couple of seconds of the track changing.

## Build the exe

Built with [PyInstaller](https://pyinstaller.org/) into a single hidden
(no-console) executable:

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name TidalRPC main.py
```

The result is `dist/TidalRPC.exe`.

## Run at startup

Copy `TidalRPC.exe` to a stable location and add a shortcut to your Windows
**Startup** folder so it launches at every login:

- Installed location: `%LOCALAPPDATA%\TidalRPC\TidalRPC.exe`
- Startup shortcut:
  `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TidalRPC.lnk`

> Tip: press <kbd>Win</kbd>+<kbd>R</kbd>, type `shell:startup`, and drop a
> shortcut to the exe in the folder that opens.

The first time it runs it will prompt for the one-time TIDAL login (browser +
popup). After that it runs silently every boot.

### To remove

- Delete the Startup shortcut (`shell:startup` → remove `TidalRPC.lnk`) to stop
  it launching at login.
- Delete the `%LOCALAPPDATA%\TidalRPC` folder to remove the app and its saved
  session.

## How it works

- Polls every couple of seconds for the running `TIDAL.exe` process and reads
  its window title to get the current "Song - Artist".
- Looks up the album art, album name, and track length via the official TIDAL
  API (using your saved login), and shows a progress bar for the song.
- Pushes a Discord Rich Presence update with `activity_type = Listening`, so
  Discord shows **"Listening to …"** instead of "Playing".
- Only sends an update when the track actually changes (staying within
  Discord's rate limit), and clears the activity when nothing is playing.
- If Discord isn't running yet (e.g. right after boot), it keeps retrying and
  reconnects automatically.

### Limitations

- Requires the **TIDAL desktop app** on Windows (it reads the native window
  title; the web player won't work).
- The window title has no playback position, so the progress bar assumes the
  song plays straight through from when it was detected — **pausing or seeking
  isn't reflected** until the next track.

## Customization

You can change the displayed text, the hover text, or the fallback image via
the constants near the top of [`main.py`](main.py) (e.g. `TIDAL_TEXT`,
`FALLBACK_IMG`, `POLL_INTERVAL`). Edits to `main.py` only affect the standalone
app after you rebuild the exe (see [Build the exe](#build-the-exe)).

## Issues and Contributions

Open an issue or pull request if you hit a problem or have an improvement.
