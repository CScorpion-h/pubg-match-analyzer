"""EXE 打包入口，等价执行 `streamlit run app.py`。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from streamlit.web import cli as stcli


def main() -> int:
    """启动 Streamlit 应用。"""
    base_dir = Path(__file__).resolve().parent
    app_path = base_dir / "app.py"
    if not app_path.exists():
        raise FileNotFoundError(f"未找到应用入口文件：{app_path}")

    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    return stcli.main()


if __name__ == "__main__":
    raise SystemExit(main())
