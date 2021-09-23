import pandas
from collections import Counter
import PyPDF2
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib.request import urlretrieve
import os
from datetime import datetime, timedelta, timezone
import camelot
import copy
import json


def download_today_data():
    load_url = 'https://www.pref.aichi.jp/site/covid19-aichi'
    html = requests.get(load_url)
    soup = BeautifulSoup(html.content, "html.parser")
    for p in soup.find_all("p"):
        if "愛知県内の感染者の発生事例" in p.text:
            try:
                pdf_url = p.next_sibling()[0]["href"]
            except KeyError:
                pdf_url = p.find("a").attrs["href"]

    pdf_url = urljoin(os.path.dirname(os.path.dirname(load_url)), pdf_url)
    pdf_name = str(datetime.today()).split()[
        0].replace("-", "") + ".pdf"
    urlretrieve(pdf_url, pdf_name)
    return pdf_name


def cut_pdf(number, pdf_name, page_plus=0):
    from math import ceil
    page = ceil(number / 47) + 1 + page_plus

    import PyPDF2
    merger = PyPDF2.PdfFileMerger()

    merger.append(pdf_name, pages=PyPDF2.pagerange.PageRange(f'{-page}:'))

    merger.write(f'{pdf_name}_cut.pdf')
    merger.close()
    return f'{pdf_name}_cut.pdf'


def generate_df_from_aichi(pdf_file_path):
    print(f"generating {pdf_file_path}")

    pdf_read = PyPDF2.PdfFileReader(pdf_file_path)
    num_page = pdf_read.numPages

    if num_page > 10:
        page_list = list(range(10, num_page, 10))
    else:
        page_list = [num_page]
    init = 1
    dfs_lap = []
    import time
    time1 = time.time()
    for num in page_list:
        if num == page_list[-1]:
            num = "end"
        tbls = camelot.read_pdf(pdf_file_path, pages=f'{init}-{num}')
        if num != "end":
            init = num + 1

        dfs = []
        for table in tbls:
            df = table.df
            dfs.append(df)
        df_all = pandas.concat(dfs)
        dfs_lap.append(df_all)
    df_total = pandas.concat(dfs_lap)
    print(f"{time.time()-time1:.2f}")

    df_all = copy.deepcopy(df_total)

    df_all.columns = df_all.iloc[0, :]
    df_all = df_all.sort_values("No")
    df_all = df_all[df_all["No"] != "No"]
    df_all = df_all.set_index("No")

    exceptions3 = [index for index, _date in zip(
        df_all.index, df_all["年代・性別"]) if "削除" in _date]
    exceptions2 = [index for index, _date in zip(
        df_all.index, df_all["発表日"]) if "欠番" in _date]
    exceptions = [index for index in df_all.index if "陽性者公表数の修正" in index]
    exceptions += exceptions2 + exceptions3
    df_all = df_all.drop(exceptions, axis=0)

    # 10歳未満バグを回避
    for no in df_all[df_all["発表日"] == ""].index:
        df_all.at[no, "発表日"], df_all.at[no,
                                        "年代・性別"] = df_all.at[no, "年代・性別"].split()
    for index in df_all[df_all["年代・性別"] == ""].index.to_list():
        if len(happyoubi := df_all.loc[index, "発表日"].split("\n")) == 5:
            happyoubi.insert(2, "")
        else:
            add_number = 6 - len(happyoubi)
            happyoubi += [""] * add_number
        df_all.loc[index, :] = happyoubi

    df_all["発表日"] = pandas.to_datetime(
        ['2021年' + _ for _ in df_all['発表日']], format='%Y年%m月%d日')
    # df_all = df_all.set_index("No")
    try:
        assert ValueError
    except ValueError:
        # for -202011
        df202011 = copy.deepcopy(df_all.iloc[:10128, :])
        for i in range(len(df202011)):
            if df202011.iloc[i, 1] == '':
                no, date = df202011.iloc[i, 0].split()
                df202011.iloc[i, 1] = date.replace("※", '')
                df202011.iloc[i, 0] = no
        df202011['発表日'] = pandas.to_datetime(
            ['2020年' + _ for _ in df202011['発表日']], format='%Y年%m月%d日')

        df202011['No'] = [int(_) for _ in df202011["No"]]
        df202011 = df202011.sort_values("No")
        # df_all = df202011.set_index("No")

    corrected_city = list()
    for city in df_all["住居地"].to_list():
        if city == "⻑久⼿市":
            corrected_city.append("長久手市")
        elif (city == "⻄尾市"):
            corrected_city.append("西尾市")
        elif (city == "瀬⼾市"):
            corrected_city.append("瀬戸市")
        elif (city == "愛⻄市"):
            corrected_city.append("愛西市")
        else:
            corrected_city.append(city)
    df_all["住居地"] = corrected_city
    zip_name = f"{os.path.splitext(pdf_file_path)[0]}.zip"
    df_all.to_pickle(zip_name)
    return zip_name


def populate_sheet(pandas_zip_file):
    df = pandas.read_pickle(pandas_zip_file)
    # df = pandas.read_pickle("../data/20210629.zip")
    # df = pandas.read_pickle("202105.zip")
    df = df.set_index("発表日")

    cities = "名古屋市	一宮市	豊橋市	豊田市	岡崎市	瀬戸市	半田市	春日井市	豊川市	津島市	碧南市	刈谷市	安城市	西尾市	蒲郡市	犬山市	常滑市	江南市	小牧市	稲沢市	新城市	東海市	大府市	知多市	知立市	尾張旭市	高浜市	岩倉市	豊明市	日進市	田原市	愛西市	清須市	北名古屋市	弥富市	みよし市	あま市	長久手市	東郷町	豊山町	大口町	扶桑町	大治町	蟹江町	飛島村	阿久比町	東浦町	南知多町	美浜町	武豊町	幸田町	設楽町	東栄町	豊根村 県外"
    res = {city: [] for city in cities.split()}
    for day in sorted(list(set(df.index.to_list()))):
        num_outside = 0
        for key in (counts := Counter(df.loc[day, :]["住居地"])):
            if key in res.keys():
                res[key].append(counts[key])
            else:
                num_outside += counts[key]
        res[list(res.keys())[-1]].append(num_outside)
    #             res[list(res.keys())[-1]].append(counts[key])
        size = len(res["名古屋市"])
        for city in res.keys():
            if len(res[city]) < size:
                res[city].append(0)
    df0 = pandas.DataFrame(res)
    df0.index = sorted(list(set(df.index.to_list())))
    return df0


def write_numbers_to_spreadsheet(data):
    url = "https://script.google.com/macros/s/AKfycbwfgSEXCRsAB5wRyaoYeRX9YD0RM7MDJarITKOFiJ9Vs5pbUQ4s1rQXVgaqNZsQkSNI/exec"
    headers = {"Content-Type": "application/json"}
    json_data = json.dumps({"data": data})
    requests.post(url, json_data, headers=headers)


def generate_list_for_spreadsheet(date, df0):
    return [date] + df0.loc[date].to_list()


def get_yesterday_number():
    from twitter_post import get_posts
    import re
    from datetime import datetime, timedelta, timezone
    posts = get_posts()
    for post in posts:

        date = datetime.strptime(
            post['created_at'], "%a %b %d %H:%M:%S %z %Y") - timedelta(hours=6)
        date = date.astimezone(timezone(timedelta(hours=9)))
        yesterday = datetime.today().astimezone(
            timezone(timedelta(hours=9))) - timedelta(days=1)
        if "愛知県全体の本日の" in post["text"]:
            if date.date() == yesterday.date():
                break

    pattern = r'.*?本日の新型コロナウイルスの新規感染者数は(\d+)人'

    # compile then match
    repatter = re.compile(pattern)
    result = repatter.match(post["text"])

    return int(result.group(1))


def main():
    pdf = download_today_data()
    yesterday_number = get_yesterday_number()
    pdf2 = cut_pdf(yesterday_number + 200, pdf)
    zip_name = generate_df_from_aichi(pdf2)
    df0 = populate_sheet(zip_name)
    yesterday = datetime.today().astimezone(
        timezone(timedelta(hours=9))) - timedelta(days=1)
    write_numbers_to_spreadsheet(
        generate_list_for_spreadsheet(str(yesterday.date()), df0))


if __name__ == "__main__":
    main()
