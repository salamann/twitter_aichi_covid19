
from bs4 import BeautifulSoup
import requests
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import re

from utility import pre_post, post_city


def get_toyota_info(engine_number=1) -> dict:

    today = datetime.today()
    yesterday = today - timedelta(days=1)

    today_date = f"{today.month}月{today.day}日"
    yesterday_date = f"{yesterday.month}月{yesterday.day}日"

    # First Engine
    if engine_number == 1:
        load_url = 'https://www.city.toyota.aichi.jp/kurashi/kenkou/eisei/1039225.html'
        html = requests.get(load_url)
        soup = BeautifulSoup(html.content, "lxml")
        toyota_new = soup.find(class_="objectlink")
        article_text = toyota_new.find("li").text
        article_url = urllib.parse.urljoin(
            load_url, toyota_new.find("li").find('a')['href'])

        is_today = (today_date in article_text)
        is_yesterday = (yesterday_date in article_text)

        pattern = r'.*?(\d+)例目'
        pattern2 = r'.*?(\d+)～'

        # compile then match
        repatter = re.compile(pattern)
        result = repatter.match(article_text)
        today_number1 = int(result.group(1))

        repatter = re.compile(pattern2)
        result = repatter.match(article_text)
        today_number2 = int(result.group(1))
        today_number = today_number1 - today_number2 + 1

    # Second Engine
    if engine_number == 2:
        load_url = "https://www.city.toyota.aichi.jp/kurashi/kenkou/eisei/1037578.html"
        article_url = load_url

        html = requests.get(load_url)
        soup = BeautifulSoup(html.content, "lxml")
        toyota_new = soup.find("h2")
        article_text = toyota_new.next_element.next_element.next_element.text
        is_today = (today_date in article_text)
        is_yesterday = (yesterday_date in article_text)

        pattern = r'.*?新規陽性者は(\d+)'

        # compile then match
        repatter = re.compile(pattern)
        result = repatter.match(article_text)
        today_number = int(result.group(1))

    return {"is_today": is_today, "is_yesterday": is_yesterday, "number": today_number, "url": article_url}


def post_toyota():
    post_city(pre_post("豊田市", "toyota_lock.zip", get_toyota_info))


if __name__ == "__main__":
    print(get_toyota_info())
