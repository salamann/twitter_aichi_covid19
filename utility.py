from datetime import datetime, timedelta
import time
import pandas
import pathlib
from typing import Callable


def generate_post(gov_info: dict) -> str:
    num_last_week = gov_info["number_last_week"]
    num_today = gov_info["number_today"]
    city = gov_info["city"]
    article_url = gov_info["article_url"]
    weekday = gov_info["weekday"]
    return f'[速報]{city}の本日の新型コロナウイルスの新規感染者数は{num_today}人(先週の{weekday}に比べて{num_today-num_last_week:+}人)でした。詳細は公式サイトを参照 > {article_url}'


def post_city(info: dict) -> None:
    from twitter_post import post

    city = info["city"]
    if info["is_postable"]:
        post(info["headline"])

        data_for_save = pandas.DataFrame(
            [{'本日': info["number_today"], '先週': info["number_last_week"]}], index=[city])
        data_for_save.to_pickle(info["zip_path"])
        time.sleep(5)
        print(f"{city}更新しました", datetime.today())


def get_day_of_week_jp(dt):
    w_list = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
    return(w_list[dt.weekday()])


def get_number_by_delta(data_frame: pandas.DataFrame, days_before: int, region: str = None) -> int:
    today = datetime.today()

    specific_day = today + timedelta(days_before)
    smonth = specific_day.month
    sday = specific_day.day

    if region is not None:
        if region == "愛知県":
            cond0 = (data_frame['住居地'] != '名古屋市')
            cond0 &= (data_frame['住居地'] != '豊橋市')
            cond0 &= (data_frame['住居地'] != '豊田市')
            cond0 &= (data_frame['住居地'] != '岡崎市')
            cond0 &= (data_frame['住居地'] != '一宮市')
            data_frame = data_frame[cond0]
        else:
            data_frame = data_frame[data_frame['住居地'] == region]
    n = 0
    for mo, da in zip(data_frame['発表日'].dt.month, data_frame['発表日'].dt.day):
        if (smonth == mo) and (sday == da):
            n += 1
    return n


def get_last_week_number(city: str) -> int:
    return get_number_by_delta(pandas.read_pickle("database.zip"), -7, region=city)


def pre_post(city: str, zip_path: str, get_info: Callable) -> dict:
    today = datetime.today()
    city_info = get_info(engine_number=1)
    num_last_week = get_last_week_number(city)
    num_today = city_info["number"]

    zip_path = pathlib.Path(zip_path)
    is_postable = (city_info["is_today"]) & (
        not zip_path.exists()) & (num_today >= 0)
    info = {"number_last_week": num_last_week,
            "number_today": num_today,
            "city": city,
            "article_url": city_info["url"],
            "weekday": get_day_of_week_jp(today),
            "zip_path": zip_path,
            "is_postable": is_postable}
    info["headline"] = generate_post(info)
    return info


def convert_zenkaku(text):
    return text.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}))


if __name__ == "__main__":
    pass
