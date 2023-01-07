import os
from datetime import datetime, timedelta, timezone

import pandas
import matplotlib.pyplot as plt
import matplotlib

from twitter_post import image_post
# from utility import get_spreadsheet_data
import sheets_api


def get_city_num(data, city):
    span = 30
    data_city = {"days": [], "numbers": []}
    for days_before in range(0, span + 1):
        day = (datetime.today() - timedelta(days=days_before)
               ).astimezone(timezone(timedelta(hours=9)))
        day_before_week = (datetime.today(
        ) - timedelta(days=days_before + 7)).astimezone(timezone(timedelta(hours=9)))
        if city != "愛知県全体":
            number_of_day = data.loc[day_before_week:day, city].sum()
        else:
            number_of_day = data.loc[day_before_week:day, :].sum().sum()
        data_city["days"].append(day.date())
        data_city["numbers"].append(number_of_day)
    return pandas.DataFrame(data_city).set_index("days")


def calculate_rt(df: pandas.DataFrame):
    rts = {"days": [], "rt": []}
    for day in df.index[:-7]:
        rt = (df.loc[day, "numbers"] / df.loc[day -
                                              timedelta(days=7), "numbers"])**(2 / 7)
        rts["days"].append(day)
        rts["rt"].append(rt)
    return pandas.DataFrame(rts).set_index("days")


def generate_rts():
    # data = get_spreadsheet_data()
    data = sheets_api.get_data_as_df()
    cities = ["名古屋市", "豊田市", "豊橋市", "岡崎市", "一宮市", "愛知県全体"]

    df6 = pandas.DataFrame()
    for city in cities:
        df6[city] = calculate_rt(get_city_num(data, city)).loc[:, "rt"]
    return df6.sort_index()


def generate_rt_image_and_message():
    cities_data = generate_rts()
    plt.rcParams['figure.subplot.bottom'] = 0.18
    matplotlib.rc('font', family='Noto Sans CJK JP')
    markers = ["o", ">", "<", "^", "s", "*"]
    for city, marker in zip(cities_data.keys(), markers):
        if city in ["愛知県全体", "名古屋市"]:
            linewidth = 2
            marker_size = 4
        else:
            linewidth = 1
            marker_size = 2
        plt.plot(cities_data.index, cities_data[city],
                 label=city, ls="-", marker=marker, ms=marker_size, lw=linewidth)

    plt.plot([cities_data.index[0], cities_data.index[-1]], [1, 1], "k--")
    plt.xlim(cities_data.index[0], cities_data.index[-1])
    plt.grid(ls=":")
    plt.legend(loc="upper left")
    plt.ylabel("Rt")
    plt.yticks(fontsize="small")
    plt.xticks(cities_data.index, rotation=45, fontsize="small", ha="right")
    plt.suptitle(
        f"""愛知県の実効再生産数(Rt)の推移
(主要市および県全体, {str(datetime.today().date())}現在)""", )
    file_name = os.path.join(
        "data", "rt" + str(datetime.today().date()).replace(":", "") + ".png")
    ylims = plt.gca().get_ylim()
    # y_position = ylims[0] - (ylims[1] - ylims[0]) / 8 * 2
    plt.text(plt.gca().get_xlim()[1] + 0.1,
             ylims[0],
             """@AichiCovid19 - データ元
感染者数：愛知県新型コロナウイルス感染症対策サイト
    (https://www.pref.aichi.jp/site/covid19-aichi/)
実効再生産数の計算方法：Real-time estimation of the effective reproduction number of COVID-19 in Japan 
    (https://github.com/contactmodel/COVID19-Japan-Reff)
平均世代時間は2日、報告間隔は7日と仮定:Estimating Generation Time Of Omicron 
    (http://sonorouschocolate.com/covid19/index.php?title=Estimating_Generation_Time_Of_Omicron)
""",
             fontsize=5, verticalalignment="bottom", horizontalalignment="left", rotation=90)
    # print(y_position, ylims)
    plt.savefig(file_name, facecolor="w", dpi=200)
    plt.close()

    message = "[更新]今日の愛知県内の実効再生産数(Rt)は、"
    dfyesterday = cities_data.loc[cities_data.index[-1], :]
    for city, rt in zip(dfyesterday.keys(), dfyesterday.values):
        message += f"{city}は{round(rt, 2)}、"
    message = message[:-1]
    message += f"でした。グラフは実効再生産数の推移を表しています({datetime.today().date()}現在)。"
    return file_name, message


def rt_post():
    file_name, message = generate_rt_image_and_message()
    image_post(file_name, message)


if __name__ == "__main__":
    # plt.plot(generate_rts()["愛知県全体"])
    # plt.grid()
    # plt.ylim([0.8, 2.0])
    # plt.show()
    generate_rt_image_and_message()
    # rt_post()
    pass
