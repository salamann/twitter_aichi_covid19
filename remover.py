import os
from pathlib import Path

if os.path.isfile((_path := "toyohashi_lock.zip")):
    os.remove(_path)
if os.path.isfile((_path := "toyota_lock.zip")):
    os.remove(_path)
if os.path.isfile((_path := "okazaki_lock.zip")):
    os.remove(_path)
if os.path.isfile((_path := "nagoya_lock.zip")):
    os.remove(_path)
if os.path.isfile((_path := "aichi_lock.zip")):
    os.remove(_path)
if (_path := Path("ichinomiya_lock.zip")).exists():
    _path.unlink()
if os.path.isfile((_path := "zentai.lock")):
    os.remove(_path)
if os.path.isfile((_path := "ranking_today.lock")):
    os.remove(_path)
if os.path.isfile((_path := "ranking_week.lock")):
    os.remove(_path)
