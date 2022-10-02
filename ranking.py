from datetime import datetime, timedelta, timezone
import os

import pandas

from twitter_post import post, image_post, get_posts
from twitter_text import parse_tweet
from rt import rt_post
from area_risk import image_file_name, generate_risk_map, create_df_per_capita
from utility import get_spreadsheet_data


def multi_dirname(path, n):
    for _ in range(n):
        path = os.path.dirname(path)
    return path


def count_twitter(text):
    import unicodedata
    ans = 0
    for string in text:
        judged = unicodedata.east_asian_width(string)
        if judged in ["F", "W"]:
            ans += 2
        else:
            ans += 1
    return ans


def ranking_today():
    df = get_spreadsheet_data()
    rank = 0
    ranking = "今日の新型コロナウイルス感染者数ランキング\n"
    is_same = False
    current_num = -1
    yesterday = str((datetime.today() - timedelta(days=0)).date())

    for city, num in df.loc[yesterday].sort_values(ascending=False).to_dict().items():
        if current_num == num:
            is_same = True
        else:
            ranking += "\n"
            rank += 1
            is_same = False
        if not is_same:
            if count_twitter(ranking) >= 230:
                ranking += f"(以下 https://narumi-midori.net/twitter_aichi_covid19/{yesterday}.html)"
                break
            else:
                ranking += f"{rank}位 {num}人 {city}"
                current_num = num
        else:
            if count_twitter(ranking) >= 230:
                ranking += f"(以下 https://narumi-midori.net/twitter_aichi_covid19/{yesterday}.html)"
                break
            else:
                ranking += f", {city}"
    post(ranking)

    return ranking


def ranking_week():
    data = get_spreadsheet_data()
    rank = 0
    ranking = "今日まで直近1週間の新型コロナウイルス感染者数ランキング\n"
    is_same = False
    current_num = -1
    yesterday = str((datetime.today() - timedelta(days=0)).date())

    df = pandas.DataFrame([])
    indices = data.index.sort_values(ascending=False)
    for num in range(len(indices) - 6):
        df1 = data.loc[indices[num:num + 7], :].sum().to_frame().transpose()
        df1.index = [indices[num]]
        df = pandas.concat([df, df1])

    for city, num in df.loc[yesterday].sort_values(ascending=False).to_dict().items():
        if current_num == num:
            is_same = True
        else:
            ranking += "\n"
            rank += 1
            is_same = False
        if not is_same:
            if count_twitter(ranking) >= 230:
                ranking += f"(以下 https://narumi-midori.net/twitter_aichi_covid19/{yesterday}_week.html)"
                break
            else:
                ranking += f"{rank}位 {num}人 {city}"
                current_num = num
        else:
            if count_twitter(ranking) >= 230:
                ranking += f"(以下 https://narumi-midori.net/twitter_aichi_covid19/{yesterday}_week.html)"
                break
            else:
                ranking += f", {city}"
    post(ranking)

    return ranking


def ranking_week_area():
    data = create_df_per_capita(get_spreadsheet_data())

    yesterday = str((datetime.today() - timedelta(days=0)).date())
    today_data = data.loc[yesterday].sort_values(
        ascending=False)

    ranking_text = "愛知県新型コロナ危険エリアランキング（今日まで直近1週間の10万人あたり新型コロナウイルス感染者数）\n"
    rank = 0
    num_prior = 0
    for city, num in today_data.items():
        if num == num_prior:
            if parse_tweet(ranking_text).weightedLength > 230:
                ranking_text += f"(以下 https://narumi-midori.net/twitter_aichi_covid19/{yesterday}_area.html)"
                break
            else:
                ranking_text += f", {city}"
        else:
            if parse_tweet(ranking_text).weightedLength > 230:
                ranking_text += f"(以下 https://narumi-midori.net/twitter_aichi_covid19/{yesterday}_area.html)"
                break
            else:
                rank += 1
                ranking_text += f"\n{rank}位 {num}人: {city}"
        num_prior = num * 1

    generate_risk_map()
    # post(ranking_text)
    image_post(image_file_name, ranking_text)
    return ranking_text


def is_already_posted():
    posts = get_posts()
    post_dates = [datetime.strptime(str(post["created_at"]), "%a %b %d %H:%M:%S %z %Y").astimezone(
        timezone(timedelta(hours=9))) for post in posts]
    posts_today = [post for date, post in zip(
        post_dates, posts) if datetime.today().date() == date.date()]
    return any(True if "ランキング" in post["text"] else False for post in posts_today)


if __name__ == "__main__":
    if not is_already_posted():
        from update_spreadsheet import main
        is_data_available = main()
        if is_data_available is not None:
            from html_gen import html_main
            html_main()
            ranking_today()
            ranking_week()
            ranking_week_area()
            rt_post()
