# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_dir = Path(SPECPATH).resolve()
pages_dir = project_dir / "pubg_match_analyzer" / "pages"

datas = [
    (str(project_dir / "app.py"), "."),
    (str(project_dir / ".streamlit" / "config.toml"), ".streamlit"),
]
for page_file in pages_dir.glob("*.py"):
    datas.append((str(page_file), "pubg_match_analyzer/pages"))

hiddenimports = collect_submodules("pubg_match_analyzer")
hiddenimports.append("streamlit.web.cli")

a = Analysis(
    ["launcher.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pubg_match_analyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="pubg_match_analyzer",
)
