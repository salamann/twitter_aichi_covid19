import os
from datetime import datetime, timedelta

import geopandas
import matplotlib
import matplotlib.pyplot as plt

from utility import get_spreadsheet_data
from html_gen import create_df_per_capita

matplotlib.rc('font', family='Noto Sans CJK JP')

image_file_name = os.path.join("data", "risk_map_" + str(datetime.today().date()
                                                         ).replace(":", "") + ".png")


def generate_risk_map():
    data = create_df_per_capita(get_spreadsheet_data())

    df2 = geopandas.read_file(os.path.join("shapes", "N03-19_23_190101.shp"))

    df2["city"] = ["名古屋市" if n03 == "名古屋市" else n04 for n03,
                   n04 in zip(df2.N03_003, df2.N03_004)]
    yesterday = str((datetime.today() - timedelta(days=1)).date())
    today_data = data.loc[yesterday]
    df2["covid_number_per_capita"] = [today_data[city]
                                      if city != "所属未定地" else None for city in df2["city"]]
    df2.plot(column="covid_number_per_capita", legend=True,
             cmap="Oranges", edgecolor="k", lw=0.1)
    plt.xticks([])
    plt.yticks([])
    plt.gca().spines['right'].set_visible(False)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['left'].set_visible(False)
    plt.gca().spines['bottom'].set_visible(False)
    plt.suptitle(f"""今日まで直近1週間の10万人あたり新型コロナウイルス感染者数
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


if __name__ == "__main__":
    generate_risk_map()
