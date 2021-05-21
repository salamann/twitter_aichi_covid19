from bs4 import BeautifulSoup
import requests
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import re
import time
import pathlib

import pandas
from aichi import get_number_by_delta
from aichi import get_day_of_week_jp
from utility import generate_post
from twitter_post import post


def get_ichinomiya_info() -> dict:

    # Home page
    url = "https://www.city.ichinomiya.aichi.jp/covid19/1033846/index.html"
    res = requests.get(url)
    soup = BeautifulSoup(res.content, "html.parser")
    [element] = [a for a in soup.find(id="content").find_all(
        "a") if "市内での新型コロナウイルス感染者の情報について" in a.text]
    element_url = element.attrs["href"]

    # Detailed page
    detailed_url = urllib.parse.urljoin(url, element_url)
    res = requests.get(detailed_url)
    soup = BeautifulSoup(res.content, "html.parser")
    [text_line] = [p for p in soup.find(id="content").find_all(
        "p") if "新型コロナウイルス感染者の発生が確認されました" in p.text]

    today = datetime.today()
    yesterday = today - timedelta(days=1)

    today_date = f"{today.month}月{today.day}日"
    yesterday_date = f"{yesterday.month}月{yesterday.day}日"
    is_today = (today_date in text_line.text)
    is_yesterday = (yesterday_date in text_line.text)

    pattern = r'.*?(\d+)名'

    # compile then match
    repatter = re.compile(pattern)
    result = repatter.match(text_line.text)

    today_number = int(result.group(1))
    return {"is_today": is_today, "is_yesterday": is_yesterday, "number": today_number, "url": detailed_url}


def get_ichinomiya_last_week():
    df0 = pandas.read_pickle("database.zip")
    return get_number_by_delta(df0, -7, region="一宮市")


def post_ichinomiya():
    today = datetime.today()
    ichinomiya_info = get_ichinomiya_info()
    num_last_week = get_ichinomiya_last_week()
    article_url = ichinomiya_info["url"]
    num_today = ichinomiya_info["number"]

    zip_path = pathlib.Path("ichinomiya_lock.zip")
    if ichinomiya_info["is_today"] and not zip_path.exists() and num_today >= 0:
        youbi = get_day_of_week_jp(today)
        header = f'[速報]一宮市の本日の新型コロナウイルスの新規感染者数は{num_today}人(先週の{youbi}に比べて{num_today-num_last_week:+}人)でした。詳細は公式サイトを参照 > {article_url}'
        # print(header)
        post(header)

        data_for_save = pandas.DataFrame(
            [{'本日': num_today, '先週': num_last_week}], index=['一宮市'])
        data_for_save.to_pickle("ichinomiya_lock.zip")
        time.sleep(5)
        print("一宮市更新しました", datetime.today())


def prepost_ichinomiya() -> dict:
    city = "一宮市"
    today = datetime.today()
    ichinomiya_info = get_ichinomiya_info()
    num_last_week = get_ichinomiya_last_week()
    num_today = ichinomiya_info["number"]

    zip_path = pathlib.Path("ichinomiya_lock.zip")
    is_postable = (ichinomiya_info["is_today"]) & (
        not zip_path.exists()) & (num_today >= 0)
    info = {"number_last_week": num_last_week,
            "number_today": num_today,
            "city": city,
            "article_url": ichinomiya_info["url"],
            "weekday": get_day_of_week_jp(today),
            "zip_path": zip_path,
            "is_postable": is_postable}
    info["headline"] = generate_post(info)
    return info


if __name__ == "__main__":
    # post_ichinomiya()
    # print(get_ichinomiya_info())
    print(prepost_ichinomiya())
