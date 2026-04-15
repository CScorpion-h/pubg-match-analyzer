"""Packaged launcher with a small control window for the Streamlit app."""

from __future__ import annotations

import asyncio
import os
import sys
import threading
import traceback
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


def _log_line(message: str) -> None:
    """Write launcher diagnostics to a local log file for EXE troubleshooting."""
    try:
        log_dir = Path(os.getenv("LOCALAPPDATA", Path.cwd()))
        log_file = log_dir / "pubg_match_analyzer_launcher.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as fh:
            fh.write(message + "\n")
    except OSError:
        pass


class StreamlitServerController:
    """Run the Streamlit server in a background thread and expose lifecycle hooks."""

    def __init__(self, app_path: Path) -> None:
        self.app_path = app_path
        self.ready_event = threading.Event()
        self.started_event = threading.Event()
        self.stopped_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.server = None
        self.url = "http://127.0.0.1:8501/"
        self.error: str | None = None
        self.flag_options: dict[str, object] = {
            "global.developmentMode": False,
            "server.fileWatcherType": "none",
            "browser.gatherUsageStats": False,
            "server.headless": True,
        }

    def start(self) -> None:
        self.thread = threading.Thread(target=self._thread_main, name="streamlit-server", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.server is not None and self.loop is not None and not self.stopped_event.is_set():
            try:
                self.loop.call_soon_threadsafe(self.server.stop)
            except RuntimeError:
                pass
        if self.thread is not None:
            self.thread.join(timeout=5)

    def _thread_main(self) -> None:
        try:
            os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
            sys.argv = ["streamlit", "run", str(self.app_path)]

            from streamlit.web import bootstrap, cli as stcli
            from streamlit.web.server import server_util

            main_script_path = os.path.abspath(self.app_path)
            stcli._config._main_script_path = main_script_path
            bootstrap.load_config_options(flag_options=self.flag_options)
            stcli.check_credentials()

            bootstrap._fix_sys_path(main_script_path)
            bootstrap._fix_tornado_crash()
            bootstrap._fix_sys_argv(main_script_path, [])
            bootstrap._install_config_watchers(self.flag_options)

            if bootstrap.config.get_option("server.useStarlette"):
                bootstrap.config._server_mode = "starlette-managed"
            else:
                bootstrap.config._server_mode = "tornado"

            self.server = bootstrap.Server(main_script_path, False)

            async def run_server() -> None:
                await self.server.start()
                self.url = server_util.get_url("127.0.0.1")
                _log_line(f"server started: {self.url}")
                self.started_event.set()
                self.ready_event.set()
                await self.server.stopped

            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            bootstrap._maybe_install_uvloop(False)
            self.loop.run_until_complete(run_server())
        except BaseException:
            self.error = traceback.format_exc()
            _log_line("launcher exception:")
            _log_line(self.error)
            self.ready_event.set()
        finally:
            self.stopped_event.set()
            if self.loop is not None and not self.loop.is_closed():
                self.loop.close()


class LauncherWindow:
    """Tiny desktop window to control the packaged Streamlit server."""

    def __init__(self, controller: StreamlitServerController) -> None:
        self.controller = controller
        self.browser_opened = False
        self.closing = False

        self.root = tk.Tk()
        self.root.title("PUBG Match Analyzer")
        self.root.geometry("460x220")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="PUBG Match Analyzer", font=("Microsoft YaHei", 16, "bold")).pack(anchor="w")

        self.status_var = tk.StringVar(value="正在启动服务...")
        self.url_var = tk.StringVar(value="http://127.0.0.1:8501/")

        ttk.Label(frame, textvariable=self.status_var, font=("Microsoft YaHei", 11)).pack(anchor="w", pady=(12, 8))
        ttk.Label(frame, text="访问地址", font=("Microsoft YaHei", 10)).pack(anchor="w")
        ttk.Entry(frame, textvariable=self.url_var, state="readonly", width=52).pack(fill="x", pady=(4, 12))

        button_row = ttk.Frame(frame)
        button_row.pack(fill="x")
        self.open_button = ttk.Button(button_row, text="打开页面", command=self.open_browser, state="disabled")
        self.open_button.pack(side="left")
        self.stop_button = ttk.Button(button_row, text="退出程序", command=self.on_close)
        self.stop_button.pack(side="right")

        ttk.Label(
            frame,
            text="关闭此窗口会同时停止本地服务。",
            font=("Microsoft YaHei", 9),
            foreground="#666666",
        ).pack(anchor="w", pady=(14, 0))

    def open_browser(self) -> None:
        webbrowser.open(self.url_var.get())

    def on_close(self) -> None:
        if self.closing:
            return
        self.closing = True
        self.status_var.set("正在关闭服务...")
        self.root.update_idletasks()
        self.controller.stop()
        self.root.destroy()

    def poll(self) -> None:
        if self.controller.error:
            self.status_var.set("启动失败")
            if not self.closing:
                self.closing = True
                messagebox.showerror("启动失败", self.controller.error)
                self.root.destroy()
            return

        if self.controller.started_event.is_set():
            self.url_var.set(self.controller.url)
            self.status_var.set("服务运行中，可关闭此窗口结束程序。")
            self.open_button.config(state="normal")
            if not self.browser_opened:
                self.browser_opened = True
                self.open_browser()

        if self.controller.stopped_event.is_set() and not self.closing:
            self.status_var.set("服务已停止")
            self.open_button.config(state="disabled")
            self.closing = True
            self.root.after(300, self.root.destroy)
            return

        self.root.after(500, self.poll)

    def run(self) -> int:
        self.poll()
        self.root.mainloop()
        return 0


def main() -> int:
    """Start the packaged Streamlit app and keep a small control window visible."""
    base_dir = Path(__file__).resolve().parent
    app_path = base_dir / "app.py"
    _log_line(f"launcher start: executable={sys.executable}")
    _log_line(f"launcher start: app_path={app_path} exists={app_path.exists()}")
    if not app_path.exists():
        raise FileNotFoundError(f"Application entry file not found: {app_path}")

    controller = StreamlitServerController(app_path)
    controller.start()
    return LauncherWindow(controller).run()


if __name__ == "__main__":
    raise SystemExit(main())
