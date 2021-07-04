import re
import urllib.parse
from typing import Callable
from datetime import datetime, timedelta, timezone
import time

import feedparser
import pandas
from bs4 import BeautifulSoup
import requests


def get_aichi_day_data_from_spreadsheet():

    from config import spreadsheet_url
    response = requests.get(spreadsheet_url)
    dfapi = pandas.DataFrame(response.json())
    dfapi["日付"] = pandas.to_datetime(dfapi["日付"])
    dfapi = dfapi.set_index("日付")

    dfapi.index = dfapi.index.tz_convert('Asia/Tokyo')
    return dfapi


def get_aichi_data_from_spreadsheet(day_before=0):
    dfapi = get_aichi_day_data_from_spreadsheet()
    return dfapi.loc[str((datetime.today() - timedelta(days=day_before)).date()), :]


def get_one_week_before():
    dfapi = get_aichi_data_from_spreadsheet(day_before=7)
    cities = ["名古屋市", "一宮市", "豊橋市", "豊田市", "岡崎市"]
    res = {city: dfapi[city] for city in cities}
    res["愛知県管轄自治体（名古屋市・豊橋市・豊田市・岡崎市・一宮市を除く愛知県）"] = dfapi.sum() - \
        dfapi[cities].sum()
    return res


def get_day_of_week_jp(dt):
    w_list = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
    return(w_list[dt.weekday()])


def generate_post(gov_info: dict) -> str:
    num_last_week = gov_info["number_last_week"]
    num_today = gov_info["number_today"]
    city = gov_info["city"]
    article_url = gov_info["article_url"]
    weekday = gov_info["weekday"]
    return f'[速報]{city}の本日の新型コロナウイルスの新規感染者数は{num_today}人(先週の{weekday}に比べて{num_today-num_last_week:+}人)でした。詳細は公式サイトを参照 > {article_url}'


def pre_post(city: str, get_info: Callable, engine_number: int = 1) -> dict:
    today = datetime.today() - timedelta(hours=6)
    city_info = get_info(engine_number)
    num_last_week = get_one_week_before()[city]
    num_today = city_info["number"]

    is_postable = (city_info["is_today"]) & (num_today >= 0)
    info = {"number_last_week": num_last_week,
            "number_today": num_today,
            "city": city,
            "article_url": city_info["url"],
            "weekday": get_day_of_week_jp(today),
            "is_postable": is_postable}
    info["headline"] = generate_post(info)
    return info


def pre_post_zentai(get_info: Callable, tweets) -> dict:
    today = datetime.today() - timedelta(hours=6)
    city_info = get_info(numbers_from_tweets=tweets)
    num_last_week = sum(get_one_week_before().values())
    num_today = city_info["number"]

    is_postable = (city_info["is_today"]) & (num_today >= 0)
    info = {"number_last_week": num_last_week,
            "number_today": num_today,
            "city": "愛知県全体",
            "article_url": city_info["url"],
            "weekday": get_day_of_week_jp(today),
            "is_postable": is_postable}
    info["headline"] = generate_post(info)
    return info


def get_okazaki_info(engine_number=1):

    load_url = 'https://www.city.okazaki.lg.jp/1550/1562/1615/p025980.html'
    html = requests.get(load_url)
    soup = BeautifulSoup(html.content, "html.parser")
    h3 = soup.find(class_="article").find("h3")

    if ("新規陽性者数は0件です" in h3.text):
        today_number = 0
        text_line = h3
        detailed_url = load_url
    elif ("新規陽性者数は1件です" in h3.text):
        today_number = 1
        text_line = h3
        detailed_url = load_url
    else:
        detailed_url = urllib.parse.urljoin(load_url,
                                            h3.find("a")['href'].replace("./", ""))
        text_lines = h3.find_all("a")
        for text_line in text_lines:
            if "新型コロナウイルス" in text_line.text:
                break

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

    today = datetime.today() - timedelta(hours=6)
    yesterday = today - timedelta(days=1)

    today_date = f"{today.month}月{today.day}日"
    yesterday_date = f"{yesterday.month}月{yesterday.day}日"
    is_today = (today_date in text_line.text)
    is_yesterday = (yesterday_date in text_line.text)

    return {"is_today": is_today, "is_yesterday": is_yesterday, "number": today_number, "url": detailed_url}


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
    is_today = (today_date in convert_zenkaku(text_line.text))
    is_yesterday = (yesterday_date in convert_zenkaku(text_line.text))

    pattern = r'.*?新規感染者数：(\d+)件'

    # compile then match
    repatter = re.compile(pattern)
    result = repatter.match(text_line_text)

    today_number = int(result.group(1))
    return {"is_today": is_today, "is_yesterday": is_yesterday, "number": today_number, "url": detailed_url}


def convert_zenkaku(text):
    return text.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}))


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


def get_ichinomiya_info(engine_number=1) -> dict:

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

    text_line = None
    for text in [p for p in soup.find(id="content").find_all(
            "p") if "新型コロナウイルス感染者の発生が確認されました" in p.text]:
        text_line = text
    if text_line is not None:
        pattern = r'.*?(\d+)名'

        # compile then match
        repatter = re.compile(pattern)
        result = repatter.match(text_line.text)

        today_number = int(result.group(1))
    elif len(text_line := [p for p in soup.find(id="content").find_all(
            "p") if "新型コロナウイルスの新たな感染者の発生は確認されませんでした" in p.text]) == 1:
        today_number = 0
        [text_line] = text_line

    today = datetime.today() - timedelta(hours=6)
    yesterday = today - timedelta(days=1)

    today_date = f"{today.month}月{today.day}日"
    yesterday_date = f"{yesterday.month}月{yesterday.day}日"
    is_today = (today_date in text_line.text)
    is_yesterday = (yesterday_date in text_line.text)

    return {"is_today": is_today, "is_yesterday": is_yesterday, "number": today_number, "url": detailed_url}


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
    return {"is_today": is_today, "is_yesterday": is_yesterday, "number": today_number, "url": detailed_url}


def get_aichi_ken_info(engine_number=1):

    today = datetime.today() - timedelta(hours=6)

    d_atom = feedparser.parse(
        'https://www.pref.aichi.jp/rss/10/site-758.xml')

    is_today = False
    article_url = ""
    for entry in d_atom['entries']:
        _day = datetime.strptime(
            entry['updated'], "%Y-%m-%dT%H:%M:%S+09:00") - timedelta(hours=6)
        if _day.date() == today.date() and (entry['title'] == '新型コロナウイルス感染症患者の発生について'):
            article_url = entry['id']
            is_today = True
            break
    is_yesterday = False if is_today else False

    if is_today:
        html = requests.get(article_url)
        soup = BeautifulSoup(html.content, "lxml")
        article_text = soup.find(class_="mol_textblock")

        pattern = r'.*?新たに以下のとおり(\d+)名.*?'

        # compile then match
        repatter = re.compile(pattern)
        result = repatter.match(article_text.text)
        today_number = int(result.group(1))
    else:
        today_number = -1

    return {"is_today": is_today, "is_yesterday": is_yesterday, "number": today_number, "url": article_url}


def get_zentai_info(engine_number=1, numbers_from_tweets=None):
    if numbers_from_tweets is not None:
        is_today = all(True if value != -
                       1 else False for value in numbers_from_tweets.values())
        today_number = sum(numbers_from_tweets.values())
        load_url = 'https://www.pref.aichi.jp/site/covid19-aichi/'
        return {"is_today": is_today, "number": today_number, "url": load_url}


def get_last_numbers_from_posts(posts):
    today_date = (datetime.today().astimezone(
        timezone(timedelta(hours=9))) - timedelta(hours=6)).date()
    cities = ["名古屋市", "豊田市", "豊橋市", "岡崎市", "一宮市",
              "愛知県管轄自治体（名古屋市・豊橋市・豊田市・岡崎市・一宮市を除く愛知県）"]
    res = {city: -1 for city in cities}
    for post in posts[::-1]:
        date = datetime.strptime(
            post['created_at'], "%a %b %d %H:%M:%S %z %Y") - timedelta(hours=6)
        post_date = date.astimezone(timezone(timedelta(hours=9))).date()
        if post_date == today_date:
            for city in cities:
                if f"{city}の本日" in post["text"]:
                    pattern = r'.*?本日の新型コロナウイルスの新規感染者数は(\d+)人'

                    # compile then match
                    repatter = re.compile(pattern)
                    result = repatter.match(post["text"])

                    res[city] = int(result.group(1))
    # res["愛知県管轄"] = res.pop("愛知県管轄自治体（名古屋市・豊橋市・豊田市・岡崎市・一宮市を除く愛知県）")
    return res


def post_cities():
    from twitter_post import get_posts, post
    numbers_from_tweets = get_last_numbers_from_posts(get_posts())

    info = pre_post("岡崎市", get_okazaki_info)
    # print(info)
    if (info["is_postable"]) & (numbers_from_tweets[info["city"]] < info["number_today"]):
        # print(info["headline"])
        post(info["headline"])
    else:
        print(info["city"],
              info["is_postable"],
              numbers_from_tweets[info["city"]],
              info["number_today"])

    info = pre_post("豊橋市", get_toyohashi_info)
    # print(info)
    if (info["is_postable"]) & (numbers_from_tweets[info["city"]] < info["number_today"]):
        # print(info["headline"])
        post(info["headline"])
    else:
        print(info["city"],
              info["is_postable"],
              numbers_from_tweets[info["city"]],
              info["number_today"])

    info = pre_post("豊田市", get_toyota_info, engine_number=2)
    # print(info)
    if (info["is_postable"]) & (numbers_from_tweets[info["city"]] < info["number_today"]):
        # print(info["headline"])
        post(info["headline"])
    else:
        print(info["city"],
              info["is_postable"],
              numbers_from_tweets[info["city"]],
              info["number_today"])

    info = pre_post("一宮市", get_ichinomiya_info)
    # print(info)
    if (info["is_postable"]) & (numbers_from_tweets[info["city"]] < info["number_today"]):
        # print(info["headline"])
        post(info["headline"])
    else:
        print(info["city"],
              info["is_postable"],
              numbers_from_tweets[info["city"]],
              info["number_today"])

    info = pre_post("名古屋市", get_nagoya_info)
    # print(info)
    if (info["is_postable"]) & (numbers_from_tweets[info["city"]] < info["number_today"]):
        # print(info["headline"])
        post(info["headline"])
    else:
        print(info["city"],
              info["is_postable"],
              numbers_from_tweets[info["city"]],
              info["number_today"])

    info = pre_post("愛知県管轄自治体（名古屋市・豊橋市・豊田市・岡崎市・一宮市を除く愛知県）", get_aichi_ken_info)
    # print(info)
    if (info["is_postable"]) & (numbers_from_tweets[info["city"]] < info["number_today"]):
        # print(info["headline"])
        post(info["headline"])
    else:
        print(info["city"],
              info["is_postable"],
              numbers_from_tweets[info["city"]],
              info["number_today"])

    # info_list = [info_okazaki, info_toyohashi, info_toyota,
    #              info_ichinomiya, info_nagoya, info_aichi_ken]
    # for info in info_list:
    #     print(f"----------{info['city']}---------")
    #     print(numbers_from_tweets[info["city"]])
    #     print(info)
    #     if (info["is_postable"]) & (numbers_from_tweets[info["city"]] < info["number_today"]):
    #         print(info["headline"])
    #     else:
    #         print("Not postable", info['city'])
    time.sleep(20)
    numbers_from_tweets = get_last_numbers_from_posts(get_posts())
    info = pre_post_zentai(get_zentai_info, numbers_from_tweets)
    print("-------------全体-------------")
    # post(info_zentai["headline"])
    if (info["is_postable"]) & (sum(numbers_from_tweets.values()) < info["number_today"]):
        # print(info["headline"])
        post(info["headline"])
    else:
        print(info["city"],
              info["is_postable"],
              sum(numbers_from_tweets.values()),
              info["number_today"])


if __name__ == "__main__":
    # print(pre_post("岡崎市", get_okazaki_info))
    # print(pre_post("豊橋市", get_toyohashi_info))
    # print(pre_post("豊田市", get_toyota_info, engine_number=2))
    # print(pre_post("一宮市", get_ichinomiya_info))
    # print(pre_post("名古屋市", get_nagoya_info))
    # print(pre_post("愛知県管轄", get_aichi_ken_info))
    # post_cities()
    post_cities()
    # from for_cloud_function import get_posts
    # print(get_last_numbers_from_posts(get_posts()))
    pass
