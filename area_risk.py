from datetime import datetime, timedelta
import pandas
import geopandas
import collections
import matplotlib.pyplot as plt

database = pandas.read_pickle("database.zip")
df2 = geopandas.read_file("N03-19_23_190101.shp")
populations = pandas.read_pickle('population.zip')

df2["city"] = ["名古屋市" if n03 == "名古屋市" else n04 for n03,
               n04 in zip(df2.N03_003, df2.N03_004)]

df2[dfdatetime.today() - timedelta(days=8)

database[database['発表日'] > datetime.today() - timedelta(days=8)]
df2["covid_number"] = [collections.Counter(database[database['発表日'] > datetime.today() - timedelta(days=8)]["住居地"])[city] for city in df2["city"]]
df2["covid_number_per_capita"] = [None if city == "所属未定地" else 100000*cnum/populations.loc[city, "20201001"] for cnum, city in zip(df2["covid_number"], df2["city"])]

df2.plot(column="covid_number_per_capita", legend=True,
            cmap="Oranges", edgecolor="k", lw=0.1)
plt.xticks([])
plt.yticks([])
plt.gca().spines['right'].set_visible(False)
plt.gca().spines['top'].set_visible(False)
plt.gca().spines['left'].set_visible(False)
plt.gca().spines['bottom'].set_visible(False)
# plt.gca().yaxis.set_label_position("right")
# plt.suptitle("昨日まで直近1週間の10万人あたり新型コロナウイルス感染者数")
