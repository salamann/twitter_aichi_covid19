from numpy import core
import pandas
import geopandas
import collections
import matplotlib
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta
matplotlib.rc('font', family='Noto Sans CJK JP')

image_file_name = os.path.join("data", "risk_map_" + str(datetime.today().date()
                                                         ).replace(":", "") + ".png")


def generate_risk_map():
    database = pandas.read_pickle("database.zip")
    df2 = geopandas.read_file(os.path.join("shapes", "N03-19_23_190101.shp"))
    populations = pandas.read_pickle('population.zip')

    df2["city"] = ["名古屋市" if n03 == "名古屋市" else n04 for n03,
                   n04 in zip(df2.N03_003, df2.N03_004)]
    # corrected_city = list()
    # for city in database["住居地"].to_list():
    #     if city == "⻑久⼿市":
    #         corrected_city.append("長久手市")
    #     elif (city == "⻄尾市"):
    #         corrected_city.append("西尾市")
    #     elif (city == "瀬⼾市"):
    #         corrected_city.append("瀬戸市")
    #     elif (city == "愛⻄市"):
    #         corrected_city.append("愛西市")
    #     else:
    #         corrected_city.append(city)
    # database["住居地"] = corrected_city

    df2["covid_number"] = [collections.Counter(database[database['発表日'] > datetime.today(
    ) - timedelta(days=8)]["住居地"])[city] for city in df2["city"]]
    df2["covid_number_per_capita"] = [None if city == "所属未定地" else 100000 * cnum /
                                      populations.loc[city, "20201001"] for cnum, city in zip(df2["covid_number"], df2["city"])]

    df2.plot(column="covid_number_per_capita", legend=True,
             cmap="Oranges", edgecolor="k", lw=0.1)
    # pandas.DataFrame({city: cnpc for city, cnpc in zip(
    #     df2["city"], df2["covid_number_per_capita"])}, index=range(len(df2))).to_excel("test2.xlsx")
    plt.xticks([])
    plt.yticks([])
    plt.gca().spines['right'].set_visible(False)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['left'].set_visible(False)
    plt.gca().spines['bottom'].set_visible(False)
    plt.suptitle(f"""昨日まで直近1週間の10万人あたり新型コロナウイルス感染者数
({str(datetime.today().date())}現在)"""
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
    plt.savefig(image_file_name, dpi=200)
    plt.close()
    # plt.gca().yaxis.set_label_position("right")


if __name__ == "__main__":
    generate_risk_map()
