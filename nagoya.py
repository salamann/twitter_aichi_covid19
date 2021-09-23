
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import re

from utility import pre_post, post_city


def get_nagoya_info(engine_number=1):

    today = datetime.today()
    yesterday = today - timedelta(days=1)

    today_date = f"{today.month}月{today.day}日"
    yesterday_date = f"{yesterday.month}月{yesterday.day}日"

    load_url = 'https://www.city.nagoya.jp/kenkofukushi/page/0000126920.html'
    html = requests.get(load_url)
    soup = BeautifulSoup(html.content, "lxml")
    nagoya_h3 = soup.find("h3")
    text_line = nagoya_h3.next_element.next_element.find("p")
    detailed_url = load_url

    today = datetime.today()
    yesterday = today - timedelta(days=1)

    today_date = f"{today.month}月{today.day}日"
    yesterday_date = f"{yesterday.month}月{yesterday.day}日"
    is_today = (today_date in nagoya_h3.text)
    is_yesterday = (yesterday_date in nagoya_h3.text)

    pattern = r'.*?(\d+)例'

    # compile then match
    repatter = re.compile(pattern)
    result = repatter.match(text_line.text)

    today_number = int(result.group(1))

    if "," in text_line.text:
        pattern = r'.*?(\d+),(\d+)例'

        # compile then match
        repatter = re.compile(pattern)
        result = repatter.match(text_line.text)

        today_number = int(result.group(1) + result.group(2))

    return {"is_today": is_today, "is_yesterday": is_yesterday, "number": today_number, "url": detailed_url}


def post_nagoya():
    post_city(pre_post("名古屋市", "nagoya_lock.zip", get_nagoya_info))


if __name__ == "__main__":
    print(get_nagoya_info())
