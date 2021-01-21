import requests
from bs4 import BeautifulSoup
import difflib
from datetime import datetime
import time
import aichi
import os
import ranking


aichi.post_nagoya()
aichi.post_okazaki()
aichi.post_toyohashi()
aichi.post_aichi()
aichi.post_toyota()
aichi.post_zentai()

print(f"checked.. {datetime.today()}")
with open("checked.txt", mode="a", encoding="utf-8") as f:
    f.write(f"checked.. {datetime.today()}")
