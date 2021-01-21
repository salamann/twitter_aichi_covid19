import requests
from bs4 import BeautifulSoup
import difflib
from datetime import datetime
import time
import aichi
import os
import ranking

# while (1):
aichi.post_nagoya()
aichi.post_okazaki()
aichi.post_toyohashi()
aichi.post_aichi()
aichi.post_toyota()
aichi.post_zentai()
# ranking.ranking_today()
print(f"checked.. {datetime.today()}")
with open("checked.txt", mode="a", encoding="utf-8") as f:
    f.write(f"checked.. {datetime.today()}")

# time.sleep(600)

while(0):
    with open("nagoya.txt", "r", encoding="utf-8") as f:
        nagoya = f.read()

    with open("toyota.txt", "r", encoding="utf-8") as f:
        toyota = f.read()

    with open("okazaki.txt", "r", encoding="utf-8") as f:
        okazaki = f.read()

    with open("toyohashi.txt", "r", encoding="utf-8") as f:
        toyohashi = f.read()

    load_url = 'https://www.city.nagoya.jp/kenkofukushi/page/0000126920.html'
    html = requests.get(load_url)
    soup = BeautifulSoup(html.content, "html.parser")
    nagoya_new = str("\n".join([str(_) for _ in soup.find_all(
        class_="mol_attachfileblock")[1].find_all("li")]))

    load_url = 'https://www.city.toyohashi.lg.jp/41805.htm'
    html = requests.get(load_url)
    soup = BeautifulSoup(html.content, "html.parser")
    toyohashi_new = str(
        "\n".join([str(_) for _ in soup.find(id='ContentPane').find_all('h5')]))

    load_url = 'https://www.city.okazaki.lg.jp/1550/1562/1615/p025980.html'
    html = requests.get(load_url)
    soup = BeautifulSoup(html.content, "html.parser")
    okazaki_new = str(soup.find(class_="article"))

    load_url = 'https://www.city.toyota.aichi.jp/kurashi/kenkou/eisei/1039225.html'
    html = requests.get(load_url)
    soup = BeautifulSoup(html.content, "html.parser")
    toyota_new = str(soup.find(class_="objectlink"))

    print(datetime.now())
    print("名古屋市:")
    for _ in difflib.unified_diff(nagoya, nagoya_new):
        print(_[1:], end="")
    print("豊田市:")
    for _ in difflib.unified_diff(toyota, toyota_new):
        print(_[1:], end="")
    print("豊橋市:")
    for _ in difflib.unified_diff(toyohashi, toyohashi_new):
        print(_[1:], end="")
    print("岡崎市:")
    for _ in difflib.unified_diff(okazaki, okazaki_new):
        print(_[1:], end="")
    print("")
#     print(list())
#     print(list(difflib.unified_diff(toyota, toyota_new)))
#     print(list(difflib.unified_diff(toyohashi, toyohashi_new)))
#     print(list(difflib.unified_diff(okazaki, okazaki_new)))
    time.sleep(300)
