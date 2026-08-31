import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Union

def play_audio_file(file_path: Union[str, Path]):
    """
    crossplatform async audio playback using native os tools.
    avoids holding longlived audio device streams open, preventing audio
    stalls after idle periods or output device changes
    """
    if not file_path:
        return

    path_str = str(file_path)
    if not os.path.exists(path_str):
        return

    try:
        if os.name == "nt":	# windows native win32 playsound via winsound stdlib
            import winsound
            winsound.PlaySound(path_str, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return

        if sys.platform == "darwin":	# macos builtin afplay utility (i didnt check this myself cause i dont have enough money but i hope it works :(
            subprocess.Popen(
                ["afplay", path_str],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            return

        for player in ["paplay", "pw-play", "aplay"]:	# linux pulseaudio, pipewire, alsa (possibly it will work on openbsd too but i did not check it, i hope itll work)
            if shutil.which(player):
                subprocess.Popen(
                    [player, path_str],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                return

        try:
            from PySide6.QtWidgets import QApplication	# fallback to qt beep
            QApplication.beep()
        except Exception:
            pass
    except Exception:
        pass

