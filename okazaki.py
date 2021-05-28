
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import urllib.parse
import re

from utility import pre_post, post_city


def get_okazaki_info(engine_number=1):

    today = datetime.today()
    yesterday = today - timedelta(days=1)

    today_date = f"{today.month}月{today.day}日"
    yesterday_date = f"{yesterday.month}月{yesterday.day}日"

    load_url = 'https://www.city.okazaki.lg.jp/1550/1562/1615/p025980.html'
    html = requests.get(load_url)
    soup = BeautifulSoup(html.content, "html.parser")
    h3 = soup.find(class_="article").find("h3")
    detailed_url = urllib.parse.urljoin(load_url,
                                        h3.find("a")['href'].replace("./", ""))

    if ("新規陽性者数は0件です" in h3.text):
        today_number = 0
    else:
        text_lines = h3.find_all("a")
        for text_line in text_lines:
            if "新型コロナウイルス" in text_line.text:
                break
        # print(text_line)

        pattern = r'.*?（(\d+)例目'
        pattern2 = r'.*?～(\d+)例目'

        # compile then match
        repatter = re.compile(pattern)
        result = repatter.match(text_line.text)
        today_number1 = int(result.group(1))

        repatter = re.compile(pattern2)
        result = repatter.match(text_line.text)
        today_number2 = int(result.group(1))

        today_number = today_number2 - today_number1 + 1

    today = datetime.today()
    yesterday = today - timedelta(days=1)

    today_date = f"{today.month}月{today.day}日"
    yesterday_date = f"{yesterday.month}月{yesterday.day}日"
    is_today = (today_date in text_line.text)
    is_yesterday = (yesterday_date in text_line.text)

    return {"is_today": is_today, "is_yesterday": is_yesterday, "number": today_number, "url": detailed_url}


def post_okazaki():
    post_city(pre_post("岡崎市", "okazaki_lock.zip", get_okazaki_info))


if __name__ == "__main__":
    print(get_okazaki_info())
