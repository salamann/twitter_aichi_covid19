import pandas
import geopandas
import collections
import matplotlib
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta
matplotlib.rc('font', family='Noto Sans CJK JP')


def generate_risk_map(timedelta_from_today=0):
    database = pandas.read_pickle("database.zip")
    df2 = geopandas.read_file(os.path.join("shapes", "N03-19_23_190101.shp"))
    populations = pandas.read_pickle('population.zip')

    df2["city"] = ["名古屋市" if n03 == "名古屋市" else n04 for n03,
                   n04 in zip(df2.N03_003, df2.N03_004)]
    df3 = database[(
        datetime.today() - timedelta(days=8) - timedelta(days=timedelta_from_today) < database["発表日"]) & (
        database["発表日"] < datetime.today() - timedelta(days=timedelta_from_today))]

    covid_number_tmp = list()

    # print(datetime.today() - timedelta(days=8) -
    #       timedelta(days=timedelta_from_today))
    # print(datetime.today()-timedelta(days=timedelta_from_today))

    for city in df2["city"]:
        covid_number_tmp.append(collections.Counter(df3["住居地"])[city])
    df2["covid_number"] = covid_number_tmp
    # database[database['発表日'] > datetime.today() - timedelta(days=8)]
    # df2["covid_number"] = [collections.Counter(database[database['発表日'] > datetime.today(
    # ) - timedelta(days=8)-timedelta(days=timedelta_from_today)]["住居地"])[city] for city in df2["city"]]
    # df2["covid_number"] = [collections.Counter(database[database['発表日'] > datetime.today(
    # ) - timedelta(days=8)-timedelta(days=timedelta_from_today)]["住居地"])[city] for city in df2["city"]]
    df2["covid_number_per_capita"] = [None if city == "所属未定地" else 100000 * cnum /
                                      populations.loc[city, "20201001"] for cnum, city in zip(df2["covid_number"], df2["city"])]

    df2.plot(column="covid_number_per_capita", legend=True,
             cmap="Oranges", edgecolor="k", lw=0.1, vmax=80, vmin=0)
    plt.xticks([])
    plt.yticks([])
    plt.gca().spines['right'].set_visible(False)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['left'].set_visible(False)
    plt.gca().spines['bottom'].set_visible(False)
    plt.suptitle(f"""1週間の10万人あたり新型コロナウイルス感染者数
({str((datetime.today()-timedelta(days=timedelta_from_today)).date())})"""
                 )
    plt.text(plt.gca().get_xlim()[0] - 0.2,
             plt.gca().get_ylim()[0] - 0.15,
             """@AichiCovid19

データ元
感染者数：愛知県新型コロナウイルス感染症対策サイト(https://www.pref.aichi.jp/site/covid19-aichi/)
人口：愛知県の人口　愛知県人口動向調査結果(https://www.pref.aichi.jp/soshiki/toukei/jinko1new.html)
地図：国土交通省 国土数値情報 (https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N03-v2_4.html#prefecture23)
""",
             fontsize=7)

    image_file_name = os.path.join("data", "risk_map_" + str((datetime.today()-timedelta(days=timedelta_from_today)).date()
                                                             ).replace(":", "") + ".png")
    plt.savefig(image_file_name, dpi=200)
    plt.close()
    # plt.gca().yaxis.set_label_position("right")


if __name__ == "__main__":
    for num in range(365, 365+60):
        generate_risk_map(timedelta_from_today=num)
