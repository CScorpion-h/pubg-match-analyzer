# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata


project_dir = Path(SPECPATH).resolve()
pages_dir = project_dir / "pubg_match_analyzer" / "pages"

datas = [
    (str(project_dir / "app.py"), "."),
    (str(project_dir / ".streamlit" / "config.toml"), ".streamlit"),
]
datas += copy_metadata("streamlit")
datas += collect_data_files("streamlit")
for page_file in pages_dir.glob("*.py"):
    datas.append((str(page_file), "pubg_match_analyzer/pages"))

hiddenimports = collect_submodules("pubg_match_analyzer")
hiddenimports += collect_submodules("streamlit")

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
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="pubg_match_analyzer",
)


