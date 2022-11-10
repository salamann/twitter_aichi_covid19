
from datetime import datetime, timedelta, timezone
from time import sleep

import feedparser
import requests
import pandas
from requests_oauthlib import OAuth1Session
import json
import camelot

from utility import get_spreadsheet_data
import config

spreadsheet_data = get_spreadsheet_data()


def get_url():
    today = datetime.today().astimezone(
        timezone(timedelta(hours=9))) - timedelta(hours=6)

    d_atom = feedparser.parse(
        'https://www.pref.aichi.jp/rss/10/site-758.xml')

    titles = ['新型コロナウイルス感染症患者の発生について',
              "新型コロナウイルス感染者の発生について"]

    # is_today = False
    article_url = None
    for entry in d_atom['entries']:
        _day = datetime.strptime(
            entry['updated'], "%Y-%m-%dT%H:%M:%S+09:00") - timedelta(hours=6)
        if _day.date() == today.date() and (entry['title'] in titles):
            article_url = entry['id']
            # is_today = True
            break
    # if is_today:
    #     html = requests.get(article_url)
    #     soup = BeautifulSoup(html.content, "lxml")
    #     a = soup.find(class_="detail_free").find('a')
    #     if '新型コロナウイルス感染者' in a.text:
    #         pdf_url = urljoin('https://www.pref.aichi.jp/', a.attrs['href'])
    #         urlretrieve(pdf_url, f"{str(datetime.today().date())}.pdf")
    return article_url


def parse_pdf():
    tbls = camelot.read_pdf(f"{str(datetime.today().date())}.pdf", pages=f'1')

    df1 = tbls[1].df.loc[1:, :]
    title_indices = [_index for _index in range(
        len(df1.columns)) if _index % 2 == 0]
    number_indices = [_index for _index in range(
        len(df1.columns)) if _index % 2 == 1]

    data = {}
    for title_index, number_index in zip(title_indices, number_indices):
        data |= {_title: int(_number.replace(',', '')) for _title, _number in zip(
            df1.loc[:, title_index].to_list(), df1.loc[:, number_index].to_list()) if _number != ''}
    data.pop('県内合計')
    cities = "名古屋市	一宮市	豊橋市	豊田市	岡崎市	瀬戸市	半田市	春日井市	豊川市	津島市	碧南市	刈谷市	安城市	西尾市	蒲郡市	犬山市	常滑市	江南市	小牧市	稲沢市	新城市	東海市	大府市	知多市	知立市	尾張旭市	高浜市	岩倉市	豊明市	日進市	田原市	愛西市	清須市	北名古屋市	弥富市	みよし市	あま市	長久手市	東郷町	豊山町	大口町	扶桑町	大治町	蟹江町	飛島村	阿久比町	東浦町	南知多町	美浜町	武豊町	幸田町	設楽町	東栄町	豊根村"
    return [str(datetime.today().date())] + [data[city]
                                             for city in cities.split()] + [0]


def pre_post(city: str, article_url: str) -> dict:
    today = datetime.today().astimezone(
        timezone(timedelta(hours=9))) - timedelta(hours=6)
    if '愛知県' not in city:
        num_today = spreadsheet_data.loc[str(today.date())].to_dict()[city]
    elif '愛知県管轄' in city:
        num_today = sum(spreadsheet_data.loc[str(today.date()), '瀬戸市':])
    elif '愛知県全体' in city:
        num_today = sum(spreadsheet_data.loc[str(today.date())])

    num_last_week = get_one_week_before()[city]

    info = {"number_last_week": num_last_week,
            "number_today": num_today,
            "city": city,
            "article_url": article_url,
            "weekday": get_day_of_week_jp(today)}
    info["headline"] = generate_post(info)
    return info


def get_one_week_before():
    dfapi = get_aichi_data_from_spreadsheet(day_before=7)
    cities = ["名古屋市", "一宮市", "豊橋市", "豊田市", "岡崎市"]
    res = {city: dfapi[city] for city in cities}
    res["愛知県管轄自治体（名古屋市・豊橋市・豊田市・岡崎市・一宮市を除く愛知県）"] = dfapi.sum() - \
        dfapi[cities].sum()
    res['愛知県全体'] = dfapi.sum()
    return res


def get_aichi_data_from_spreadsheet(day_before=0):
    dfapi = get_aichi_day_data_from_spreadsheet()
    return dfapi.loc[str((datetime.today().astimezone(timezone(timedelta(hours=9))) - timedelta(days=day_before)).date()), :]


def get_aichi_day_data_from_spreadsheet():
    spreadsheet_url2 = config.spreadsheet_url2
    response = requests.get(spreadsheet_url2)
    dfapi = pandas.DataFrame(response.json())
    dfapi["日付"] = pandas.to_datetime(dfapi["日付"])
    dfapi = dfapi.set_index("日付")

    dfapi.index = dfapi.index.tz_convert('Asia/Tokyo')
    return dfapi


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


def post(message):
    twitter_session = OAuth1Session(config.api_key,
                                    config.api_secret,
                                    config.access_token,
                                    config.access_token_secret)
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
    sleep(3)


def post_all_cities():

    article_url = get_url()
    if article_url is not None:
        cities = ['名古屋市', '豊橋市', '豊田市', '岡崎市', '一宮市',
                  '愛知県管轄自治体（名古屋市・豊橋市・豊田市・岡崎市・一宮市を除く愛知県）',
                  '愛知県全体']
        for city in cities:
            post(pre_post(city, article_url)['headline'])


if __name__ == "__main__":
    post_all_cities()
