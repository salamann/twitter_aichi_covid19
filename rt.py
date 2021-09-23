import pandas
from collections import Counter
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib
import os
from twitter_post import image_post


def generate_rt(city, df):
    nums = {"days": [], city: []}
    for days_before in range(1, 41):
        cond = (datetime.today() - timedelta(days=days_before + 8) < df["発表日"])
        cond &= (datetime.today() -
                 timedelta(days=days_before + 1) >= df["発表日"])

        if city != "愛知県全体":
            cond &= (df["住居地"] == city)
        nums["days"].append(datetime.today().date() -
                            timedelta(days=days_before))
        nums[city].append(len(df[cond]))

    df2 = pandas.DataFrame(nums)
    df2 = df2.set_index("days")
    rts = {"days": [], city: []}
    for days_before2 in range(1, 21):
        num_day = df2.loc[datetime.today().date(
        ) - timedelta(days=days_before2), city]
        num_day_1week_bef = df2.loc[datetime.today(
        ).date() - timedelta(days=days_before2 + 7), city]
        rt = (num_day / num_day_1week_bef)**(5 / 7)
        rts["days"].append(datetime.today().date() -
                           timedelta(days=days_before2))
        rts[city].append(rt)
    return rts


def generate_rt_image_and_message():
    df = pandas.read_pickle("database.zip")
    large_cities = Counter(df["住居地"]).most_common()[:5]

    for num, [city, _] in enumerate(large_cities):
        if num == 0:
            rts = generate_rt(city, df)
        else:
            rts.update(generate_rt(city, df))
    rts.update(generate_rt("愛知県全体", df))

    nagoya = pandas.DataFrame(rts).sort_values("days").set_index("days")
    plt.rcParams['figure.subplot.bottom'] = 0.18
    matplotlib.rc('font', family='Noto Sans CJK JP')
    markers = ["o", ">", "<", "^", "s", "*"]
    for city, marker in zip(nagoya.keys(), markers):
        if city in ["愛知県全体", "名古屋市"]:
            linewidth = 2
            marker_size = 4
        else:
            linewidth = 1
            marker_size = 2
        plt.plot(nagoya.index, nagoya[city],
                 label=city, ls="-", marker=marker, ms=marker_size, lw=linewidth)

    plt.plot([nagoya.index[0], nagoya.index[-1]], [1, 1], "k--")
    plt.xlim(nagoya.index[0], nagoya.index[-1])
    plt.grid()
    plt.legend(loc="upper left")
    plt.ylabel("Rt")
    plt.xticks(rotation=30)
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
平均世代時間は5日、報告間隔は7日と仮定
""",
             fontsize=5, verticalalignment="bottom", horizontalalignment="left", rotation=90)
    # print(y_position, ylims)
    plt.savefig(file_name, facecolor="w", dpi=200)
    plt.close()

    message = "[更新]昨日の愛知県内の実効再生産数(Rt)は、"
    dfyesterday = nagoya.loc[nagoya.index[-1], :]
    for city, rt in zip(dfyesterday.keys(), dfyesterday.values):
        message += f"{city}は{round(rt, 2)}、"
    message = message[:-1]
    message += f"でした。グラフは実効再生産数の推移を表しています({datetime.today().date()}現在)。"
    return file_name, message


def rt_post():
    file_name, message = generate_rt_image_and_message()
    image_post(file_name, message)


if __name__ == "__main__":
    generate_rt_image_and_message()
    # rt_post()
    pass
