# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import os
import sys

datas = []
binaries = []

hiddenimports = [
    "replicate",
    "importlib.metadata",
    "django",
    "importlib",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.authentication",
    "rest_framework_simplejwt.state",
    "whitenoise",
    "whitenoise.middleware",
    "django.middleware",
    "django.core",
    "django.contrib",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

tmp_ret = collect_all('replicate')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

datas += [
    (os.path.join(BASE_DIR, "templates"), "templates"),
    (os.path.join(BASE_DIR, "static"), "static"),
]

a = Analysis(
    ['manage.py'],
    pathex=[BASE_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='manage',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
