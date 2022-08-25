import time
from datetime import date, datetime, timedelta, timezone
from typing import Callable
import json
from pathlib import Path
import re
import os
from collections import Counter
from urllib.parse import urljoin
from urllib.request import urlretrieve

import camelot
import pandas
from twitter_text import parse_tweet
import requests
from bs4 import BeautifulSoup
from requests_oauthlib import OAuth1Session
import feedparser


def multi_dirname(path, n):
    for _ in range(n):
        path = os.path.dirname(path)
    return path


def get_open_data() -> str:
    #     url = "https://vrs-data.cio.go.jp/vaccination/opendata/latest/summary_by_prefecture.csv"
    url = "https://data.vrs.digital.go.jp/vaccination/opendata/latest/summary_by_prefecture.csv"
    file_name = Path(url).name

    url_data = requests.get(url).content

    with open(f"/tmp/{file_name}", mode='wb') as f:
        f.write(url_data)
    return file_name


def get_non_medical_number(file_name) -> dict:
    df = pandas.read_csv(f"/tmp/{file_name}", encoding="sjis")
    df = df.set_index("prefecture_name")
    n_first_dose = int(df.at["愛知県", "count_first_shot_general"])
    n_second_dose = int(df.at["愛知県", "count_second_shot_general"])
    n_third_dose = int(df.at["愛知県", "count_third_shot_general"])
    return {"1回目": n_first_dose, "2回目": n_second_dose, "3回目": n_third_dose}


def get_medical_number(file_name: str) -> dict:
    df_medical = pandas.read_excel(f"/tmp/{file_name}", sheet_name="医療従事者等")
    df_medical.columns = df_medical.loc[1, :].to_list()
    df_medical = df_medical.loc[:, "都道府県名":"内２回目"]
    df_medical = df_medical.dropna()
    df_of_day = df_medical[df_medical["都道府県名"].str.contains("愛知県")]
    [n_first_dose] = df_of_day["内１回目"].to_list()
    [n_second_dose] = df_of_day["内２回目"].to_list()
    return {"1回目": n_first_dose, "2回目": n_second_dose}


def get_aichi_population() -> int:
    url_aichi_population = "https://www.pref.aichi.jp/toukei/"
    site = requests.get(url_aichi_population)
    soup = BeautifulSoup(site.content, "lxml")
    tds = soup.find(id="submenu_toukei_right_omonagyoumu").find_all("td")
    [num] = [i for i, _ in enumerate(tds) if "人口" in _.text]
    return int(tds[num + 1].text.replace("人", "").replace(",", ""))


def get_medical_data() -> str:
    # url_medical_staff = "https://www.kantei.go.jp/jp/content/IRYO-kenbetsu-vaccination_data2.xlsx"
    url_medical_staff = "https://www.kantei.go.jp/jp/content/kenbetsu-vaccination_data2.xlsx"
    # url_medical_staff = "https://www.kantei.go.jp/jp/content/000099046.xlsx"

    file_name_medical_staff = Path(url_medical_staff).name

    url_data_medical = requests.get(url_medical_staff).content

    with open(f"/tmp/{file_name_medical_staff}", mode='wb') as f:
        f.write(url_data_medical)
    return file_name_medical_staff


def generate_headline_first_second(medical_dict: dict, nonmedical_dict: dict) -> str:
    n_first_dose = medical_dict["1回目"] + nonmedical_dict["1回目"]
    n_second_dose = medical_dict["2回目"] + nonmedical_dict["2回目"]
    n_third_dose = nonmedical_dict["3回目"]
    n_total = n_first_dose+n_second_dose+n_third_dose
    aichi_pop = get_aichi_population()
    url_kantei = "https://www.kantei.go.jp/jp/headline/kansensho/vaccine.html"
    headline = f"[更新]現在の愛知県の新型コロナワクチンの総接種回数は{n_total}回"
    headline += f"(1回目接種{n_first_dose}回、2回目接種{n_second_dose}回、3回目接種{n_third_dose}回)です。"
    headline += f"1回目接種率は{n_first_dose/aichi_pop*100:.2f}%、"
    headline += f"2回目接種率は{n_second_dose/aichi_pop*100:.2f}%、"
    headline += f"3回目接種率は{n_third_dose/aichi_pop*100:.2f}%です。"
    headline += f"詳しくは首相官邸サイトを参照 > {url_kantei}"
    return headline


def post_vaccination() -> None:
    medical = get_medical_number(get_medical_data())
    non_medical = get_non_medical_number(get_open_data())
    headline = generate_headline_first_second(medical, non_medical)

    last_number = get_last_total_number()
    current_numer = extract_total_number(headline)
    if current_numer > last_number:
        post(headline)
    else:
        print("The number is the same as before.")


def get_last_post(timelines) -> str:
    for timeline in timelines:
        if "コロナワクチン" in timeline["text"]:
            return timeline["text"]


def extract_total_number(text: str) -> int:
    pattern = r'.*?総接種回数は(\d+)回'

    # compile then match
    repatter = re.compile(pattern)
    result = repatter.match(text)

    return int(result.group(1))


def get_last_total_number() -> int:
    timelines = get_posts()
    text_line_text = get_last_post(timelines)

    if text_line_text is not None:
        return extract_total_number(text_line_text)
    else:
        return -1


def get_posts(tweet_number=20) -> dict:
    credentials = os.environ
    twitter_session = OAuth1Session(credentials["api_key"],
                                    credentials["api_secret"],
                                    credentials["access_token"],
                                    credentials["access_token_secret"])
    url = "https://api.twitter.com/1.1/statuses/user_timeline.json"  # タイムライン取得エンドポイント

    params = {'count': tweet_number}  # 取得数
    res = twitter_session.get(url, params=params)
    timelines = json.loads(res.text)
    return timelines


def post(message):
    credentials = os.environ
    twitter_session = OAuth1Session(credentials["api_key"],
                                    credentials["api_secret"],
                                    credentials["access_token"],
                                    credentials["access_token_secret"])
    api_endpoint = "https://api.twitter.com/1.1/statuses/update.json"

    res = twitter_session.post(api_endpoint, params={"status": message})

    if res.status_code == 200:
        print("Success.")
    else:
        message = f"""Failed.
 - Responce Status Code : {res.status_code}
 - Error Code : {res.json()["errors"][0]["code"]}
 - Error Message : {res.json()["errors"][0]["message"]}
"""
        print(message)


def get_aichi_day_data_from_spreadsheet():
    spreadsheet_url = os.environ["spreadsheet_url"]
    # from config import spreadsheet_url
    response = requests.get(spreadsheet_url)
    dfapi = pandas.DataFrame(response.json())
    dfapi["日付"] = pandas.to_datetime(dfapi["日付"])
    dfapi = dfapi.set_index("日付")

    dfapi.index = dfapi.index.tz_convert('Asia/Tokyo')
    return dfapi


def get_aichi_data_from_spreadsheet(day_before=0):
    dfapi = get_aichi_day_data_from_spreadsheet()
    return dfapi.loc[str((datetime.today().astimezone(timezone(timedelta(hours=9))) - timedelta(days=day_before)).date()), :]


def get_one_week_before():
    dfapi = get_aichi_data_from_spreadsheet(day_before=7)
    cities = ["名古屋市", "一宮市", "豊橋市", "豊田市", "岡崎市"]
    res = {city: dfapi[city] for city in cities}
    res["愛知県管轄自治体（名古屋市・豊橋市・豊田市・岡崎市・一宮市を除く愛知県）"] = dfapi.sum() - \
        dfapi[cities].sum()
    return res


def get_day_of_week_jp(dt):
    w_list = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
    return (w_list[dt.weekday()])


def generate_post(gov_info: dict) -> str:
    num_last_week = gov_info["number_last_week"]
    num_today = gov_info["number_today"]
    city = gov_info["city"]
    article_url = gov_info["article_url"]
    weekday = gov_info["weekday"]
    return f'[速報]{city}の本日の新型コロナウイルスの新規感染者数は{num_today}人(先週の{weekday}に比べて{num_today-num_last_week:+}人)でした。詳細は公式サイトを参照 > {article_url}'


def pre_post(city: str, get_info: Callable, engine_number: int = 1) -> dict:
    today = datetime.today().astimezone(
        timezone(timedelta(hours=9))) - timedelta(hours=6)
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
    today = datetime.today().astimezone(
        timezone(timedelta(hours=9))) - timedelta(hours=6)
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
        detailed_url = urljoin(load_url, h3.find("a")[
                               'href'].replace("./", ""))
        if ("岡崎市における新規陽性者数" in h3.text) and (',' not in h3.text):
            pattern3 = r'.*?(\d+)件'
            text_line = h3
            repatter = re.compile(pattern3)
            result = repatter.match(h3.text)
            today_number = int(result.group(1))
        elif ("岡崎市における新規陽性者数" in h3.text) and (',' in h3.text):
            pattern3 = r'.*?(\d+),(\d+)件'
            text_line = h3
            repatter = re.compile(pattern3)
            result = repatter.match(h3.text)

            today_number = int(result.group(1)+result.group(2))
        else:
            text_lines = h3.find_all("a")
            for text_line in text_lines:
                if "新型コロナウイルス" in text_line.text:
                    break

            print(h3)
            pattern = r'.*?（(\d+)例目'
            pattern2 = r'.*?～(\d+)例目'

            # compile then match
            repatter = re.compile(pattern)
            result = repatter.match(text_line.text)
            if result is not None:
                today_number1 = int(result.group(1))
            else:
                pattern = r'.*?ついて(\d+)例目'
                repatter = re.compile(pattern)
                result = repatter.match(text_line.text)
                today_number1 = int(result.group(1))

            repatter = re.compile(pattern2)
            result = repatter.match(text_line.text)
            today_number2 = int(result.group(1))

            today_number = today_number2 - today_number1 + 1

    today = datetime.today().astimezone(
        timezone(timedelta(hours=9))) - timedelta(hours=6)
    yesterday = today - timedelta(days=1)

    today_date = f"{today.month}月{today.day}日"
    yesterday_date = f"{yesterday.month}月{yesterday.day}日"
    is_today = (today_date in text_line.text)
    is_yesterday = (yesterday_date in text_line.text)

    return {"is_today": is_today, "is_yesterday": is_yesterday, "number": today_number, "url": detailed_url}


def get_toyohashi_info(engine_number=1):

    today = datetime.today().astimezone(timezone(timedelta(hours=9)))
    yesterday = today - timedelta(days=1)

    today_date = f"{today.month}月{today.day}日"
    yesterday_date = f"{yesterday.month}月{yesterday.day}日"

    load_url = 'https://www.city.toyohashi.lg.jp/41805.htm'

    html = requests.get(load_url)
    soup = BeautifulSoup(html.content, "lxml")
    text_line = soup.find(class_='Item_normal')

    text_line_text = text_line.text.replace("\n", "").replace("\xa0", "")
    detailed_url = load_url

    today = datetime.today().astimezone(timezone(timedelta(hours=9)))
    yesterday = today - timedelta(days=1)

    today_date = f"{today.month}月{today.day}日"
    yesterday_date = f"{yesterday.month}月{yesterday.day}日"
    is_today = (today_date in convert_zenkaku(text_line.text))
    is_yesterday = (yesterday_date in convert_zenkaku(text_line.text))

    pattern = r'.*?新規感染者数：(\d+)件'

    # compile then match
    repatter = re.compile(pattern)
    result = repatter.match(text_line_text)

    if result is not None:
        today_number = int(result.group(1))
    else:
        pattern = r'.*?者数：(\d+)件'

        # compile then match
        repatter = re.compile(pattern)
        result = repatter.match(text_line_text)
        if result is not None:
            today_number = int(result.group(1))
        else:
            pattern = r'.*?者数：(\d+),(\d+)件'
            repatter = re.compile(pattern)
            result = repatter.match(text_line_text)
            today_number = int(result.group(1) + result.group(2))

    return {"is_today": is_today, "is_yesterday": is_yesterday, "number": today_number, "url": detailed_url}


def convert_zenkaku(text):
    return text.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}))


def get_toyota_info(engine_number=1) -> dict:

    today = datetime.today().astimezone(timezone(timedelta(hours=9)))
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
        article_url = urljoin(
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
        if 'ずれが生じています' in article_text:
            is_today = (today_date in article_text.split('ずれが生じています')[0])
            is_yesterday = (
                yesterday_date in article_text.split('ずれが生じています')[0])
        else:
            is_today = (today_date in article_text)
            is_yesterday = (yesterday_date in article_text)

        # more than one thousand
        pattern = r'.*?新規陽性者は(\d+),(\d+)人'
        repatter = re.compile(pattern)
        result = repatter.match(article_text)
        if result is not None:
            today_number = int(result.group(1)+result.group(2))

        # less than one thousand
        else:
            pattern = r'.*?新規陽性者は(\d+)人'

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
    detailed_url = urljoin(url, element_url)
    # print(detailed_url)
    res = requests.get(detailed_url)
    soup = BeautifulSoup(res.content, "html.parser")

    text_line = None
    for text in [p for p in soup.find(id="content").find_all(
            "p") if "新型コロナウイルス感染者の発生が確認されました" in p.text]:
        text_line = text
    if text_line is None:

        for text in [p for p in soup.find(id="content").find_all(
                "p") if "新型コロナウイルスに感染したことが判明しました" in p.text]:
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

    today = datetime.today().astimezone(
        timezone(timedelta(hours=9))) - timedelta(hours=6)
    yesterday = today - timedelta(days=1)

    today_date = f"{today.month}月{today.day}日"
    yesterday_date = f"{yesterday.month}月{yesterday.day}日"
    # print(text_line)
    is_today = (today_date in text_line.text)
    is_yesterday = (yesterday_date in text_line.text)

    return {"is_today": is_today, "is_yesterday": is_yesterday, "number": today_number, "url": detailed_url}


def get_nagoya_info(engine_number=1):

    today = datetime.today().astimezone(timezone(timedelta(hours=9)))
    yesterday = today - timedelta(days=1)

    today_date = f"{today.month}月{today.day}日"
    yesterday_date = f"{yesterday.month}月{yesterday.day}日"

    load_url = 'https://www.city.nagoya.jp/kenkofukushi/page/0000126920.html'
    html = requests.get(load_url)
    soup = BeautifulSoup(html.content, "lxml")
    text_line = soup.find("h3").next_element.next_element.find("p")
    detailed_url = load_url

    today = datetime.today().astimezone(
        timezone(timedelta(hours=9))) - timedelta(hours=6)
    yesterday = today - timedelta(days=1)

    today_date = f"{today.month}月{today.day}日"
    yesterday_date = f"{yesterday.month}月{yesterday.day}日"

    date_text = soup.find("h2").text
    is_today = (today_date in date_text)
    is_yesterday = (yesterday_date in date_text)

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

        today_number = int(result.group(1)+result.group(2))
    return {"is_today": is_today, "is_yesterday": is_yesterday, "number": today_number, "url": detailed_url}


def get_aichi_ken_info(engine_number=1):

    today = datetime.today().astimezone(
        timezone(timedelta(hours=9))) - timedelta(hours=6)

    d_atom = feedparser.parse(
        'https://www.pref.aichi.jp/rss/10/site-758.xml')

    titles = ['新型コロナウイルス感染症患者の発生について',
              "新型コロナウイルス感染者の発生について"]

    is_today = False
    article_url = ""
    for entry in d_atom['entries']:
        _day = datetime.strptime(
            entry['updated'], "%Y-%m-%dT%H:%M:%S+09:00") - timedelta(hours=6)
        if _day.date() == today.date() and (entry['title'] in titles):
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
        result = repatter.match(article_text.text.replace("\n", ""))
        if result is not None:
            today_number = int(result.group(1))
        else:
            pattern = r'.*?新たに以下のとおり(\d+),(\d+)名.*?'

            # compile then match
            repatter = re.compile(pattern)
            result = repatter.match(article_text.text.replace("\n", ""))
            today_number = int(result.group(1)+result.group(2))
    else:
        today_number = -1

    return {"is_today": is_today, "is_yesterday": is_yesterday, "number": today_number, "url": article_url}


def get_zentai_info(engine_number=1, numbers_from_tweets=None):
    if numbers_from_tweets is not None:
        _number = numbers_from_tweets.pop("愛知県全体")
        is_today = all(True if value != -
                       1 else False for value in numbers_from_tweets.values())
        today_number = sum(numbers_from_tweets.values())
        numbers_from_tweets["愛知県全体"] = _number
        load_url = 'https://www.pref.aichi.jp/site/covid19-aichi/'
        return {"is_today": is_today, "number": today_number, "url": load_url}


def get_last_numbers_from_posts(posts):
    today_date = (datetime.today().astimezone(
        timezone(timedelta(hours=9))) - timedelta(hours=6)).date()
    cities = ["名古屋市", "豊田市", "豊橋市", "岡崎市", "一宮市",
              "愛知県管轄自治体（名古屋市・豊橋市・豊田市・岡崎市・一宮市を除く愛知県）",
              "愛知県全体"]
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
    # from twitter_post import get_posts, post
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

    time.sleep(5)
    numbers_from_tweets = get_last_numbers_from_posts(get_posts())
    info = pre_post_zentai(get_zentai_info, numbers_from_tweets)
    print("-------------全体-------------")
    # post(info_zentai["headline"])
    if (info["is_postable"]) & (numbers_from_tweets[info["city"]] < info["number_today"]):
        # print(info["headline"])
        post(info["headline"])
    else:
        print(info["city"],
              info["is_postable"],
              numbers_from_tweets[info["city"]],
              info["number_today"])


def ranking_today():
    press_url = "https://www.pref.aichi.jp/site/covid19-aichi/index-2.html"
    html = requests.get(press_url)
    soup = BeautifulSoup(html.content, "html.parser")

    today = (datetime.today().astimezone(timezone(timedelta(hours=9))
                                         ) - timedelta(days=1)).strftime('%Y年%-m月%-d日')

    texts = "感染症患者の発生|感染者の発生"
    url_flake = ""
    for li in soup.find(class_="list_ccc").find_all("li"):
        if (today in li.text) & (len(re.findall(texts, li.text)) > 0) & ("愛知県職員における" not in li.text):
            url_flake = li.find("a")["href"]
    if url_flake != "":
        today_url = urljoin(multi_dirname(press_url, 3), url_flake)
        html = requests.get(today_url)
        soup = BeautifulSoup(html.content, "html.parser")
        pdf_url = urljoin(multi_dirname(press_url, 3), soup.find(
            class_="detail_free").find("a")["href"])
        pdf_file_path = "/tmp/yesterday.pdf"
        urlretrieve(pdf_url, pdf_file_path)

        tbls = camelot.read_pdf(pdf_file_path, pages='1-end')

        dfs = []
        for table in tbls:
            df = table.df
            dfs.append(df)
        df_all = pandas.concat(dfs)

        df_all.columns = df_all.iloc[0, :]
        df_all = df_all[df_all["年代"] != "年代"]

        df_zentai = get_last_numbers_from_posts(
            get_posts(tweet_number=30), day_before=1)
        df_zentai.pop("愛知県管轄")
        df_zentai = pandas.DataFrame.from_dict(df_zentai, orient="index")
        df_zentai.columns = ["本日"]

        aichi_kobetsu = pandas.DataFrame(
            Counter(df_all["居住地"]).most_common())
        aichi_kobetsu = aichi_kobetsu.set_index(0)
        aichi_kobetsu.columns = ["本日"]
        aichi_total = pandas.concat(
            [aichi_kobetsu, df_zentai[df_zentai.index != "愛知県"]]).sort_values("本日", ascending=False)
        ranking_text = "昨日の新型コロナウイルス感染者数ランキング\n"
        rank = 0
        num_prior = 0
        for city, num in zip(aichi_total.index, aichi_total["本日"]):
            if num == num_prior:
                if parse_tweet(ranking_text).weightedLength > 258:
                    ranking_text += "(以下略)"
                    break
                else:
                    ranking_text += f", {city}"
            else:
                if parse_tweet(ranking_text).weightedLength > 251:
                    ranking_text += "(以下略)"
                    break
                else:
                    rank += 1
                ranking_text += f"\n{rank}位 {num}人: {city}"
            num_prior = num * 1
        post(ranking_text)


def post_ranking():
    current_time = datetime.today().astimezone(timezone(timedelta(hours=9)))
    if (10 <= current_time.hour < 11) & (5 <= current_time.minute < 20):
        ranking_today()
    else:
        print("today's ranking is not posted",
              current_time.hour, current_time.minute)


def hello_pubsub(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """

    # Vacction post
    post_vaccination()

    # post each covid-19 number
    post_cities()

    # post yesterday's ranking
    post_ranking()
