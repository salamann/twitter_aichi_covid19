import pandas
import geopandas
import collections
import matplotlib
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta
matplotlib.rc('font', family='Noto Sans CJK JP')

image_file_name = "risk_map_" + str(datetime.today().date()
                                    ).replace(":", "") + ".png"


def generate_risk_map():
    database = pandas.read_pickle("database.zip")
    df2 = geopandas.read_file(os.path.join("shapes", "N03-19_23_190101.shp"))
    populations = pandas.read_pickle('population.zip')

    df2["city"] = ["名古屋市" if n03 == "名古屋市" else n04 for n03,
                   n04 in zip(df2.N03_003, df2.N03_004)]

    database[database['発表日'] > datetime.today() - timedelta(days=8)]
    df2["covid_number"] = [collections.Counter(database[database['発表日'] > datetime.today(
    ) - timedelta(days=8)]["住居地"])[city] for city in df2["city"]]
    df2["covid_number_per_capita"] = [None if city == "所属未定地" else 100000*cnum /
                                      populations.loc[city, "20201001"] for cnum, city in zip(df2["covid_number"], df2["city"])]

    df2.plot(column="covid_number_per_capita", legend=True,
             cmap="Oranges", edgecolor="k", lw=0.1)
    plt.xticks([])
    plt.yticks([])
    plt.gca().spines['right'].set_visible(False)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['left'].set_visible(False)
    plt.gca().spines['bottom'].set_visible(False)
    # plt.suptitle("昨日まで直近1週間の10万人あたり新型コロナウイルス感染者数")
    plt.savefig(image_file_name)
    # plt.gca().yaxis.set_label_position("right")


if __name__ == "__main__":
    generate_risk_map()
