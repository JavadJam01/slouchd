import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from src.config import get_app_dir

class SafeStreamToLogger:
    """safely redirects writes to logger without infinite recursion"""
    def __init__(self, logger, level, original_stream=None):
        self.logger = logger
        self.level = level
        self.original_stream = original_stream
        self._in_write = False

    def write(self, message):
        if self._in_write:
            if self.original_stream and hasattr(self.original_stream, "write"):
                try:
                    self.original_stream.write(message)
                except Exception:
                    pass
            return

        text = message.strip()
        if text:
            self._in_write = True
            try:
                self.logger.log(self.level, text)
                for h in self.logger.handlers:
                    h.flush()
            finally:
                self._in_write = False

        if self.original_stream and hasattr(self.original_stream, "write"):
            try:
                self.original_stream.write(message)
            except Exception:
                pass

    def flush(self):
        if self.original_stream and hasattr(self.original_stream, "flush"):
            try:
                self.original_stream.flush()
            except Exception:
                pass

def setup_logging():
    """sets up rotating log file in app data dir and redirects stdout/stderr"""
    app_dir = get_app_dir()
    log_file = app_dir / "slouchd.log"

    root_logger = logging.getLogger("slouchd")
    root_logger.setLevel(logging.INFO)

    if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
        try:
            file_handler = RotatingFileHandler(
                str(log_file),
                maxBytes=512 * 1024,	# 512 kb max per file
                backupCount=1,	# 1 backup file, keeps total log size under 1 mb
                encoding="utf-8"
            )
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            pass

    orig_stdout = sys.stdout
    orig_stderr = sys.stderr

    sys.stdout = SafeStreamToLogger(root_logger, logging.INFO, orig_stdout)
    sys.stderr = SafeStreamToLogger(root_logger, logging.ERROR, orig_stderr)

    root_logger.info(f"--- slouchd session started (log file: {log_file}) ---")
    for h in root_logger.handlers:
        h.flush()
