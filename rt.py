import pandas
from collections import Counter
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib
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
    for city in nagoya.keys():
        plt.plot(nagoya.index, nagoya[city], label=city)

    plt.plot([nagoya.index[0], nagoya.index[-1]], [1, 1], "k--")
    plt.grid()
    plt.legend()
    plt.ylabel("Rt")
    plt.xticks(rotation=45)
    plt.suptitle("愛知県の実効再生産数(Rt)の推移(主要市および県全体)")
    file_name = "rt" + str(datetime.today().date()).replace(":", "") + ".png"
    plt.savefig(file_name, facecolor="w", dpi=150)

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
    # generate_rt_image_and_message()
    pass
