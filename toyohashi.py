
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import re

from utility import pre_post, post_city


def get_toyohashi_info(engine_number=1):

    today = datetime.today()
    yesterday = today - timedelta(days=1)

    today_date = f"{today.month}月{today.day}日"
    yesterday_date = f"{yesterday.month}月{yesterday.day}日"

    load_url = 'https://www.city.toyohashi.lg.jp/41805.htm'

    html = requests.get(load_url)
    soup = BeautifulSoup(html.content, "lxml")
    text_line = soup.find(class_='Item_normal')

    text_line_text = text_line.text.replace("\n", "").replace("\xa0", "")
    detailed_url = load_url

    today = datetime.today()
    yesterday = today - timedelta(days=1)

    today_date = f"{today.month}月{today.day}日"
    yesterday_date = f"{yesterday.month}月{yesterday.day}日"
    is_today = (today_date in text_line.text)
    is_yesterday = (yesterday_date in text_line.text)

    pattern = r'.*?新規感染者数：(\d+)件'

    # compile then match
    repatter = re.compile(pattern)
    result = repatter.match(text_line_text)

    today_number = int(result.group(1))
    return {"is_today": is_today, "is_yesterday": is_yesterday, "number": today_number, "url": detailed_url}


def post_toyohashi():
    post_city(pre_post("豊橋市", "toyohashi_lock.zip", get_toyohashi_info))


if __name__ == "__main__":
    print(get_toyohashi_info())
