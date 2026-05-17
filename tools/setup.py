"""
Setup script for building RAM Optimizer as macOS .app bundle using py2app
"""
from setuptools import setup

APP = ["ram_optimizer.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "iconfile": None,
    "plist": {
        "CFBundleName": "RAM Optimizer",
        "CFBundleDisplayName": "RAM Optimizer",
        "CFBundleIdentifier": "com.membra.ram-optimizer",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSUIElement": True,  # Run as menu bar app (no dock icon)
    },
    "packages": ["rumps"],
}

setup(
    app=APP,
    name="RAM Optimizer",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
