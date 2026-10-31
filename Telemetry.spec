# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=[("qml", "qml"), ("assets", "assets"), ("LICENSE", ".")],
    hiddenimports=["keyring.backends.Windows"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Telemetry",
    icon="assets/Telemetry_Icon.png",
    console=False,
    disable_windowed_traceback=False,
)
