import shutil
from ftplib import FTP_TLS
from pathlib import Path
from datetime import datetime, timedelta

from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt
import pandas

# from utility import get_spreadsheet_data
from config import spreadsheet_url2, password, host_name, user_name

cities = {'北名古屋市': "kitanagoya", '名古屋市': "nagoya", '一宮市': "ichinomiya", '豊橋市': "toyohashi",
          '豊田市': "toyota", '岡崎市': "okazaki", '瀬戸市': "seto",
          '半田市': "handa", '春日井市': "kasugai", '豊川市': "toyokawa", '津島市': "tsushima",
          '碧南市': "hekinan", '刈谷市': "kariya", '安城市': "anjo", '西尾市': "nishio", '蒲郡市': "gamagori",
          '犬山市': "inuyama", '常滑市': "tokoname", '江南市': "konan", '小牧市': "komaki", '稲沢市': "inazawa",
          '新城市': "shinshiro", '東海市': "tokai", '大府市': "obu", '知多市': "chita", '知立市': "chiryu",
          '尾張旭市': "owariasahi", '高浜市': "takahama", '岩倉市': "iwakura", '豊明市': "toyoake", '日進市': "nisshin",
          '田原市': "tawara", '愛西市': "aisai", '清須市': "kiyosu",
          '弥富市': "yatomi", 'みよし市': "miyoshi", 'あま市': "ama", '長久手市': "nagakute", '東郷町': "togo",
          '豊山町': "toyoyama", '大口町': "oguchi", '扶桑町': "fuso", '大治町': "oharu",
          '蟹江町': "kanie", '飛島村': "tobishima", '阿久比町': "akubi", '東浦町': "higashiura",
          '南知多町': "mitamichita", '美浜町': "mihama",
          '武豊町': "taketoyo", '幸田町': "koda", '設楽町': "shitara", '東栄町': "toei",
          '豊根村': "toyone", '県外': "kengai"}


# def get_speadsheet_data():

#     url = spreadsheet_url2
#     response = requests.get(url)
#     dfapi = pandas.DataFrame(response.json())
#     dfapi["日付"] = pandas.to_datetime(dfapi["日付"])
#     dfapi = dfapi.set_index("日付")

#     dfapi.index = dfapi.index.tz_convert('Asia/Tokyo')
#     return dfapi


def generate_ranking_text_day(data, date):
    if isinstance(data.loc[date], pandas.Series):
        data_dict = data.loc[date].sort_values(ascending=False).to_dict()
    elif isinstance(data.loc[date], pandas.DataFrame):
        data_dict = data.loc[date].loc[date].sort_values(
            ascending=False).to_dict()

    return generate_ranking_text(data_dict)


def generate_ranking_text(data_dict):
    rank = 0
    ranking = "<li>"
    is_same = False
    current_num = -1

    for city, num in data_dict.items():
        if current_num == num:
            is_same = True
        else:
            ranking += "</li>\n<li>"
            rank += 1
            is_same = False
        if not is_same:
            ranking += f"{rank}位 {num}人 {city}"
            current_num = num
        else:
            ranking += f", {city}"
    return ranking[9:] + "</li>"


def generate_date_html(data):
    for date in data.index:
        date = date.date().__str__()

        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template("base.html")

        rank_text = generate_ranking_text_day(data, date)

        for city in cities:
            if city != "名古屋市":
                rank_text = rank_text.replace(
                    city, f'<a href="{cities[city]}.html">{city}</a>')
            else:
                rank_text = rank_text.replace(
                    " " + city, f' <a href="{cities[city]}.html">{city}</a>')

        data1 = {"h1": "愛知県新型コロナウイルス感染者ランキング",
                 'title': f"愛知県新型コロナウイルス感染者数ランキング | {date}",
                 'date': date,
                 'table': rank_text}
        disp_text = template.render(data1)

        with open(f"html/{date}.html", "w", encoding="utf-8") as f:
            f.write(disp_text)


def generate_city_htmls(data):

    df = pandas.DataFrame([])
    indices = data.index.sort_values(ascending=False)
    for num in range(len(indices) - 6):
        df1 = data.loc[indices[num:num + 7], :].sum().to_frame().transpose()
        df1.index = [indices[num]]
        df = pandas.concat([df, df1])
    df.index = [
        f"{df.index[_i].date()}から{(df.index[_i] - timedelta(days=6)).date()}" for _i in range(len(df.index))]

    for city in cities:
        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template("base.html")

        table1 = data[city].sort_index(ascending=False).to_frame().to_html(
            index_names=False).replace("00:00:00+09:00", "")
        table1 = table1.replace(city, "1日あたり感染者数")
        table2 = df[city].to_frame().to_html().replace("00:00:00+09:00", "")
        table2 = table2.replace(city, "1週間あたりの感染者数")

        outer_table = f'<TABLE BORDER="0"><TR><TD valign="top">{table1}</TD><TD valign="top">{table2}</TD></TR></TABLE>'

        data1 = {'title': f"愛知県新型コロナウイルス感染者数プロット | {city}",
                 "h1": "新型コロナウイルス感染者",
                 "date": f"{city}",
                 'body': f'<img src="{cities[city]}.png">' + outer_table}

        disp_text = template.render(data1)

        with open(f"html/{cities[city]}.html", "w", encoding="utf-8") as f:
            f.write(disp_text)


def generate_plots(data):
    for city in cities:
        plt.figure(figsize=(6, 4))
        plt.grid()
        plt.bar(data.index, data[city])
        plt.xticks(rotation=30, fontsize="x-small")
        plt.ylabel("# of infected people")
        plt.xlim(data.index[-90], data.index[-1])
        plt.savefig(f"html/{cities[city]}.png", dpi=150, facecolor="white")
        plt.clf()
        plt.close()


def upload_file_with_ftp_over_ssl():
    yesterday = (datetime.today() - timedelta(days=1)).date().__str__()
    for _path in Path("html").glob("*"):
        # if 1:
        if ("2021" not in _path.name) or (yesterday in _path.name):
            local_path = "html/" + _path.name
            print("uploading..\t", local_path)
            remote_path = f"twitter_aichi_covid19/{local_path.split('/')[-1]}"
            with FTP_TLS(host=host_name, user=user_name, passwd=password) as ftp:
                with open(local_path, 'rb') as f:
                    ftp.storbinary(f'STOR {remote_path}', f)


def generate_week_html(data):

    df = pandas.DataFrame([])
    indices = data.index.sort_values(ascending=False)
    for num in range(len(indices) - 6):
        df1 = data.loc[indices[num:num + 7], :].sum().to_frame().transpose()
        df1.index = [indices[num]]
        df = pandas.concat([df, df1])

    for date in df.index:
        date = date.date().__str__()

        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template("base.html")

        rank_text = generate_ranking_text_day(df, date)

        for city in cities:
            if city != "名古屋市":
                rank_text = rank_text.replace(
                    city, f'<a href="{cities[city]}.html">{city}</a>')
            else:
                rank_text = rank_text.replace(
                    " " + city, f' <a href="{cities[city]}.html">{city}</a>')

        data1 = {"h1": "昨日まで直近1週間愛知県新型コロナウイルス感染者ランキング",
                 'title': f"愛知県新型コロナウイルス感染者数ランキング | {date} | 1週間合計",
                 'date': date,
                 'table': rank_text}
        disp_text = template.render(data1)

        with open(f"html/{date}_week.html", "w", encoding="utf-8") as f:
            f.write(disp_text)


def generate_index_page(data):
    text = ""
    for date in data.index.sort_values(ascending=False):
        date = date.date().__str__()

        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template("base.html")

        text += f'<li>{date}:\t<a href="{date}.html">1日あたりの感染者数</a>'
        if Path("html").joinpath(f"{date}_week.html").exists():
            text += f'\t|\t<a href="{date}_week.html">1週間あたりの感染者数</a>'
        if Path("html").joinpath(f"{date}_area.html").exists():
            text += f'\t|\t<a href="{date}_area.html">1週間の10万人あたり感染者数</a>'
        text += "</li>\n"

        data1 = {"h1": "愛知県新型コロナウイルス感染者数@AichiCovid19",
                 'title': "愛知県新型コロナウイルス感染者数@AichiCovid19 | Index",
                 'date': "日付インデックス",
                 'table': text}
        disp_text = template.render(data1)

    with open("html/index.html", "w", encoding="utf-8") as f:
        f.write(disp_text)


def create_df_per_capita(data):
    df = pandas.DataFrame([])
    indices = data.index.sort_values(ascending=False)
    for num in range(len(indices) - 6):
        df1 = data.loc[indices[num:num + 7], :].sum().to_frame().transpose()
        df1.index = [indices[num]]
        df = pandas.concat([df, df1])

    population = pandas.read_pickle("population.zip")
    population = population.to_dict()[population.columns[0]]

    infection_per_capitas = {}
    indices = []
    for date in df.index:
        indices.append(date)
        date = date.date().__str__()

        infected_people = df.loc[date, :].to_dict()
        # infected_people = df.loc[date].loc[date].to_dict()

        for city, num_infection in infected_people.items():
            if city != "県外":
                if city in infection_per_capitas.keys():
                    infection_per_capitas[city].append(
                        int(num_infection / population[city] * 10**5))
                else:
                    infection_per_capitas[city] = [
                        int(num_infection / population[city] * 10**5)]
    return pandas.DataFrame(infection_per_capitas, index=indices)


def generate_area_html(df_per_capita):
    for date in df_per_capita.index:
        date = date.date().__str__()
        rank_text = generate_ranking_text_day(df_per_capita, date)

        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template("base.html")

        for city in cities:
            if city != "名古屋市":
                rank_text = rank_text.replace(
                    city, f'<a href="{cities[city]}.html">{city}</a>')
            else:
                rank_text = rank_text.replace(
                    " " + city, f' <a href="{cities[city]}.html">{city}</a>')

        data1 = {"h1": "愛知県新型コロナ危険エリアランキング（昨日まで直近1週間の10万人あたり新型コロナウイルス感染者数）",
                 'title': f"愛知県新型コロナ危険エリアランキング（昨日まで直近1週間の10万人あたり新型コロナウイルス感染者数） | {date}",
                 'date': date,
                 'table': rank_text}
        if (img_path := Path("data").joinpath(f"risk_map_{date}.png")).exists():
            data1["image"] = f'<img src="{img_path.name}">'
            shutil.copy(img_path, Path("html"))
        disp_text = template.render(data1)

        with open(f"html/{date}_area.html", "w", encoding="utf-8") as f:
            f.write(disp_text)


def html_main():
    data = get_speadsheet_data()
    generate_city_htmls(data)
    generate_date_html(data)
    generate_week_html(data)
    generate_area_html(create_df_per_capita(data))
    generate_plots(data)
    generate_index_page(data)
    upload_file_with_ftp_over_ssl()


if __name__ == "__main__":
    html_main()
