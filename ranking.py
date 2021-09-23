import camelot
import pandas
import collections
from datetime import datetime, timedelta
import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib.request import urlretrieve
from twitter_post import get_posts, post, image_post
import aichi
from twitter_text import parse_tweet
from rt import rt_post
from area_risk import image_file_name, generate_risk_map, create_df_per_capita

from utility import get_last_numbers_from_posts, get_speadsheet_data


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


def ranking_today2():
    df = get_speadsheet_data()
    rank = 0
    ranking = "昨日の新型コロナウイルス感染者数ランキング\n"
    is_same = False
    current_num = -1
    yesterday = str((datetime.today() - timedelta(days=1)).date())

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


def ranking_week2():
    data = get_speadsheet_data()
    rank = 0
    ranking = "昨日まで直近1週間の新型コロナウイルス感染者数ランキング\n"
    is_same = False
    current_num = -1
    yesterday = str((datetime.today() - timedelta(days=1)).date())

    df = pandas.DataFrame([])
    indices = data.index.sort_values(ascending=False)
    for num in range(len(indices) - 6):
        df1 = data.loc[indices[num:num + 7], :].sum().to_frame().transpose()
        df1.index = [indices[num]]
        df = pandas.concat([df, df1])

    for city, num in df.loc[yesterday].loc[yesterday].sort_values(ascending=False).to_dict().items():
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


def ranking_week_area2():
    data = create_df_per_capita(get_speadsheet_data())

    yesterday = str((datetime.today() - timedelta(days=1)).date())
    today_data = data.loc[yesterday].loc[yesterday].sort_values(
        ascending=False)

    ranking_text = "愛知県新型コロナ危険エリアランキング（昨日まで直近1週間の10万人あたり新型コロナウイルス感染者数）\n"
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


def ranking_today():
    if not(os.path.isfile("ranking_today.lock")):
        press_url = "https://www.pref.aichi.jp/site/covid19-aichi/index-2.html"
        html = requests.get(press_url)
        soup = BeautifulSoup(html.content, "html.parser")

        # デプロイ前にタイムデルタを取る
        # today = (datetime.today()).strftime('%Y年%-m月%-d日')
        today = (datetime.today() - timedelta(days=1) -
                 timedelta(hours=6)).strftime('%Y年%-m月%-d日')

        url_flake = ""
        for li in soup.find(class_="list_ccc").find_all("li"):
            if (today in li.text) & ("感染者の発生" in li.text) & ("愛知県職員における" not in li.text):
                url_flake = li.find("a")["href"]
        if url_flake != "":
            today_url = urljoin(multi_dirname(press_url, 3), url_flake)
            html = requests.get(today_url)
            soup = BeautifulSoup(html.content, "html.parser")
            pdf_url = urljoin(multi_dirname(press_url, 3), soup.find(
                class_="detail_free").find("a")["href"])
            pdf_file_path = os.path.join(
                "data", f"{str(datetime.today()-timedelta(hours=6)).split()[0]}_aichi.pdf")
            urlretrieve(pdf_url, pdf_file_path)

            tbls = camelot.read_pdf(pdf_file_path, pages='1-end')

            dfs = []
            for table in tbls:
                df = table.df
                dfs.append(df)
            df_all = pandas.concat(dfs)

            df_all.columns = df_all.iloc[0, :]
            df_all = df_all[df_all["年代"] != "年代"]

            # デプロイ前にタイムデルタを消す
            # _name = str(datetime.today()).split()[0]
            # _name = str(datetime.today() - timedelta(days=1)).split()[0]
            # df_zentai = pandas.read_pickle(
            #     os.path.join("data", f"{_name}_from_sum.zip"))
            df_zentai = get_last_numbers_from_posts(
                get_posts(tweet_number=30), day_before=1)
            df_zentai.pop("愛知県管轄")
            df_zentai = pandas.DataFrame.from_dict(df_zentai, orient="index")
            df_zentai.columns = ["本日"]

            aichi_kobetsu = pandas.DataFrame(
                collections.Counter(df_all["居住地"]).most_common())
            aichi_kobetsu = aichi_kobetsu.set_index(0)
            aichi_kobetsu.columns = ["本日"]
            aichi_total = pandas.concat(
                [aichi_kobetsu, df_zentai[df_zentai.index != "愛知県"]]).sort_values("本日", ascending=False)
            ranking_text = "昨日の新型コロナウイルス感染者数ランキング\n"
            rank = 0
            num_prior = 0
            yesterday = datetime.today() - timedelta(days=1)
            for city, num in zip(aichi_total.index, aichi_total["本日"]):
                if num == num_prior:
                    if parse_tweet(ranking_text).weightedLength > 233:
                        # if parse_tweet(ranking_text).weightedLength > 258:
                        ranking_text += f"(以下 https://narumi-midori.net/twitter_aichi_covid19/{str(yesterday.date())}.html)"
                        break
                    else:
                        ranking_text += f", {city}"
                else:
                    if parse_tweet(ranking_text).weightedLength > 226:
                        # if parse_tweet(ranking_text).weightedLength > 251:
                        ranking_text += f"(以下 https://narumi-midori.net/twitter_aichi_covid19/{str(yesterday.date())}.html)"
                        break
                    else:
                        rank += 1
                    ranking_text += f"\n{rank}位 {num}人: {city}"
                num_prior = num * 1
            # print(ranking_text)

            post(ranking_text)
            with open("ranking_today.lock", "w", encoding="utf-8") as f:
                f.write("")


def ranking_week():
    if not(os.path.isfile("ranking_week.lock")):
        this_mo = pandas.read_pickle("database.zip")
        # this_mo = pandas.read_pickle(f"{os.path.splitext(pdf_name)[0]}.zip")
        this_week = this_mo[this_mo["発表日"] >=
                            datetime.today() - timedelta(days=8) - timedelta(hours=6)]
        pd_week = pandas.DataFrame(
            collections.Counter(this_week["住居地"]).most_common())
        pd_week[0] = [_.replace("⻄", "西") for _ in pd_week[0]]

        ranking_text = "昨日まで直近1週間の新型コロナウイルス感染者数ランキング\n"
        rank = 0
        num_prior = 0
        yesterday = datetime.today() - timedelta(days=1)

        for city, num in zip(pd_week[0], pd_week[1]):
            if num == num_prior:
                # if parse_tweet(ranking_text).weightedLength > 258:
                if parse_tweet(ranking_text).weightedLength > 223:
                    ranking_text += f"(以下 https://narumi-midori.net/twitter_aichi_covid19/{str(yesterday.date())}_week.html)"
                    break
                else:
                    ranking_text += f", {city}"
            else:
                # if parse_tweet(ranking_text).weightedLength > 252:
                if parse_tweet(ranking_text).weightedLength > 227:
                    ranking_text += f"(以下 https://narumi-midori.net/twitter_aichi_covid19/{str(yesterday.date())}_week.html)"
                    break
                else:
                    rank += 1
                    ranking_text += f"\n{rank}位 {num}人: {city}"
            num_prior = num * 1
        # print(ranking_text, parse_tweet(ranking_text).weightedLength)
        post(ranking_text)
        # print(header)
        with open("ranking_week.lock", "w", encoding="utf-8") as f:
            f.write("")


def ranking_week_area():
    pops = pandas.read_pickle("population.zip")
    this_mo = pandas.read_pickle("database.zip")

    this_week = this_mo[this_mo["発表日"] >= datetime.today(
    ) - timedelta(days=8) - timedelta(hours=6)]
    pd_week = pandas.DataFrame(
        collections.Counter(this_week["住居地"]).most_common())
    pd_week[0] = [_.replace("⻄", "西").replace(
        '瀬⼾市', "瀬戸市").replace('⻑久⼿市', "長久手市").replace('⾧久手市', '長久手市') for _ in pd_week[0]]
    pd_week = pd_week[~pd_week[0].str.contains(
        "東京都|県|京都府|大阪府|北海道|堺市|関市|土岐市|千葉市")]
    # pd_week = pd_week[(pd_week[0] != "三重県") & (pd_week[0] != "岐阜県") & (pd_week[0] != "千葉県")]
    pd_week = pd_week[pd_week[0] != ""]
    per_capita = list()
    for city, num in zip(pd_week[0], pd_week[1]):
        if city in set(pops.index.to_list()):
            per_capita.append(int(num / pops.loc[city, "20201001"] * 10**5))
        else:
            per_capita.append(0)
    # pd_week["per_capita"] = [int(num / pops.loc[city, "20201001"] * 10**5)
    #                          for city, num in zip(pd_week[0], pd_week[1])]
    pd_week["per_capita"] = per_capita
    pd_week = pd_week.sort_values("per_capita", ascending=False)

    ranking_text = "愛知県新型コロナ危険エリアランキング（昨日まで直近1週間の10万人あたり新型コロナウイルス感染者数）\n"
    rank = 0
    num_prior = 0
    for city, num in zip(pd_week[0], pd_week["per_capita"]):
        if num == num_prior:
            if parse_tweet(ranking_text).weightedLength > 258:
                ranking_text += "(以下略)"
                break
            else:
                ranking_text += f", {city}"
        else:
            if parse_tweet(ranking_text).weightedLength > 252:
                ranking_text += "(以下略)"
                break
            else:
                rank += 1
                ranking_text += f"\n{rank}位 {num}人: {city}"
        num_prior = num * 1
    # print(ranking_text)
    generate_risk_map()
    # post(ranking_text)
    image_post(image_file_name, ranking_text)


def update_database():
    load_url = 'https://www.pref.aichi.jp/site/covid19-aichi'
    html = requests.get(load_url)
    soup = BeautifulSoup(html.content, "html.parser")
    # [nspan] = [num for num, _ in enumerate(
    #     soup.find_all("span")) if "愛知県内の発生事例" in _.text]
    # pdf_url = soup.find_all("span")[nspan+1].find("a")["href"]
    texts = "愛知県内の感染者の発生事例|愛知県内の発生事例"
    for p in soup.find_all("p"):
        if len(re.findall(texts, p.text)) > 0:
            try:
                pdf_url = p.next_sibling()[0]["href"]
            except KeyError:
                pdf_url = p.find("a").attrs["href"]
            # pdf_url = p.find("a")["href"]
    pdf_url = urljoin(os.path.dirname(os.path.dirname(load_url)), pdf_url)
    pdf_name = os.path.join("data", str(datetime.today() - timedelta(hours=6)).split()[
                            0].replace("-", "") + ".pdf")
    urlretrieve(pdf_url, pdf_name)

    aichi.generate_df_from_aichi(pdf_name)
    # update_database()

    pdf_name = os.path.join("data", str(datetime.today() - timedelta(hours=6)).split()[
                            0].replace("-", "") + ".zip")
    # df01 = pandas.read_pickle("202012.zip")
    # df01 = pandas.read_pickle("202101.zip")
    # df01 = pandas.read_pickle(os.path.join("data", "202104.zip"))
    # df01 = pandas.read_pickle(os.path.join("data", "202106.zip"))
    # df01 = pandas.read_pickle(os.path.join("data", "202107.zip"))
    df01 = pandas.read_pickle(os.path.join("data", "202108.zip"))
    df02 = pandas.read_pickle(pdf_name)
    df03 = pandas.concat([df01, df02])
    df03.to_pickle("database.zip")


if __name__ == "__main__":

    # try:
    from update_spreadsheet import main
    main()
    from html_gen import html_main
    html_main()
    # ranking_today()
    ranking_today2()
    ranking_week2()
    ranking_week_area2()
    # except:
    #     pass
    # update_database()
    # ranking_week()
    rt_post()

    # ranking_today2()
    # print(ranking_week2())
    # print(count_twitter("愛知県の1位\n愛媛 \n"))
    # print(ranking_week_area2())
