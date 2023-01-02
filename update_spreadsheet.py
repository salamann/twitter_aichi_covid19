import os
import json
from math import ceil
import pickle
from collections import Counter
import requests
from urllib.parse import urljoin
from urllib.request import urlretrieve
from datetime import datetime, timedelta, timezone

import pandas
import PyPDF2
import camelot
from bs4 import BeautifulSoup
from tqdm import tqdm
import feedparser

from utility import get_spreadsheet_data
from config import spreadsheet_url2
from config import spreadsheet_generation_url
import sheets_api

def download_today_data():
    load_url = 'https://www.pref.aichi.jp/site/covid19-aichi'
    html = requests.get(load_url)
    soup = BeautifulSoup(html.content, "html.parser")
    for p in soup.find_all("p"):
        if "愛知県内の感染者の発生事例" in p.text:
            # try:
            #     pdf_url = p.next_sibling()[0]["href"]
            # except KeyError:
            pdf_url = p.find("a").attrs["href"]

    pdf_url = urljoin(os.path.dirname(os.path.dirname(load_url)), pdf_url)
    pdf_name = str(datetime.today()).split()[
        0].replace("-", "") + ".pdf"
    urlretrieve(pdf_url, pdf_name)
    return pdf_name


def cut_pdf(number, pdf_name, page_plus=0):
    page = ceil(number / 47) + 1 + page_plus

    pdf_read = PyPDF2.PdfFileReader(pdf_name)
    num_page = pdf_read.numPages
    if page >= num_page:
        page = num_page

    merger = PyPDF2.PdfFileMerger()

    merger.append(pdf_name, pages=PyPDF2.pagerange.PageRange(f'{-page}:'))

    merger.write(f'{pdf_name[:-4]}_cut.pdf')
    merger.close()
    return f'{pdf_name[:-4]}_cut.pdf'


def generate_df_from_aichi(pdf_file_path: str, is_debug=False) -> pandas.DataFrame:
    print(f"generating {pdf_file_path}")

    def set_columns_by_first_row(data_frame: pandas.DataFrame) -> pandas.DataFrame:
        data_frame.columns = data_frame.iloc[0, :]
        return data_frame.iloc[1:, :].copy()

    def refine_date(data_frame: pandas.DataFrame) -> pandas.DataFrame:
        data_frame.loc[:, '発表日'] = [
            _.split("日")[0] + "日" for _ in data_frame['発表日'].to_list()]
        return data_frame

    def set_new_columns_for_pending_nagoya(data_frame: pandas.DataFrame) -> pandas.DataFrame:
        new_columns = []
        for _column in data_frame.columns:
            new_columns += [_ for _ in _column.split("\n") if _ != ""]
        if len(data_frame.columns) == 7:
            # when number of columns is correct (7)
            data_frame.columns = new_columns
            return data_frame
        else:
            # when number of column is less than 7
            new_dict = {}
            for _column in new_columns:
                if _column in data_frame.columns:
                    new_dict[_column] = data_frame.loc[:, _column].to_list()
                else:
                    new_dict[_column] = [None] * len(data_frame.index)
            return pandas.DataFrame(new_dict)

    def set_city_when_city_is_blank(data_frame: pandas.DataFrame) -> pandas.DataFrame:
        new_city = []
        for old_city, note in zip(data_frame['住居地'].to_list(), data_frame['備考'].to_list()):
            if old_city in ["-", "ー", "", None]:
                new_city.append(note.split("発表")[0])
            else:
                new_city.append(old_city)
        data_frame.loc[:, '住居地'] = new_city
        return data_frame

    def city_name_correction(data_frame: pandas.DataFrame) -> pandas.DataFrame:
        corrected_city = list()
        cities = {"⻑久⼿市": "長久手市", "⻄尾市": "西尾市", "瀬⼾市": "瀬戸市", "愛⻄市": "愛西市"}
        for city in data_frame["住居地"].to_list():
            if city in cities.keys():
                corrected_city.append(cities[city])
            else:
                corrected_city.append(city)
        data_frame.loc[:, "住居地"] = corrected_city
        return data_frame

    def set_index(data_frame: pandas.DataFrame):
        return data_frame.set_index("No")

    def cope_with_less_than_10y(data_frame: pandas.DataFrame) -> pandas.DataFrame:
        new_age = []
        new_date = []
        for _date, _age in zip(data_frame["発表日"], data_frame["年代・性別"]):
            if "日" == _date:
                _date, _age = _age.split()
            new_age.append(_age)
            new_date.append(_date)
        data_frame.loc[:, "発表日"] = new_date
        data_frame.loc[:, "年代・性別"] = new_age
        return data_frame

    def change_date_format(data_frame: pandas.DataFrame) -> pandas.DataFrame:
        data_frame.loc[:, "発表日"] = pandas.to_datetime(
            ['2022年' + _ for _ in data_frame['発表日'].to_list()], format='%Y年%m月%d日')
        return data_frame

    def remove_ketsuban(data_frame: pandas.DataFrame) -> pandas.DataFrame:
        return data_frame[~data_frame["発表日"].str.contains("欠番")]

    if not is_debug:
        pdf_read = PyPDF2.PdfFileReader(pdf_file_path)
        num_page = pdf_read.numPages
        if num_page > 10:
            page_list = list(range(10, num_page, 10))
        else:
            page_list = [num_page]

        init = 1
        dfs = []
        for end_id in page_list:
            if end_id == page_list[-1]:
                end_id = "end"
            tbls = camelot.read_pdf(pdf_file_path, pages=f'{init}-{end_id}')
            if end_id != "end":
                init = end_id + 1

            for table in tbls:
                df = table.df
                dfs.append(df)
        # for debug
        with open("list_data.pickle", "wb") as f:
            pickle.dump(dfs, f)
    else:
        with open("list_data.pickle", "rb") as f:
            dfs = pickle.load(f)

    df = pandas.DataFrame()
    for df_tmp in tqdm(dfs):
        df_tmp = set_columns_by_first_row(df_tmp)
        df_tmp = set_new_columns_for_pending_nagoya(df_tmp)
        df_tmp = refine_date(df_tmp)
        df_tmp = set_city_when_city_is_blank(df_tmp)
        df_tmp = set_index(df_tmp)
        df_tmp = cope_with_less_than_10y(df_tmp)
        df_tmp = remove_ketsuban(df_tmp)
        df_tmp = change_date_format(df_tmp)
        df_tmp = city_name_correction(df_tmp)
        df = pandas.concat([df, df_tmp])
    zip_name = "data_list.zip"
    df.to_pickle(zip_name)
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
        _data_day = df.loc[day, "住居地"]
        if isinstance(_data_day, str):
            _data_day = {_data_day: 1}
        for key in (counts := Counter(_data_day)):
            if key in res.keys():
                res[key].append(counts[key])
            else:
                num_outside += counts[key]
        res[list(res.keys())[-1]].append(num_outside)
    #             res[list(res.keys())[-1]].append(counts[key])
        size = max([len(_) for _ in res.values()])
        for city in res.keys():
            if len(res[city]) < size:
                res[city].append(0)
    df0 = pandas.DataFrame(res)
    df0.index = sorted(list(set(df.index.to_list())))
    return df0


def write_numbers_to_spreadsheet(data: list, url=spreadsheet_url2) -> None:
    headers = {"Content-Type": "application/json"}
    json_data = json.dumps({"data": data})
    requests.post(url, json_data, headers=headers)


def generate_list_for_spreadsheet(date: str, df0: pandas.DataFrame) -> list:
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
    if result is None:
        return 20000
    elif (number := int(result.group(1))) > 1000:
        return number
    else:
        return 20000


def status_data_of_the_day(days_before: int = 0):
    today = datetime.today().astimezone(
        timezone(timedelta(hours=9))) - timedelta(hours=6) - timedelta(days=days_before)

    d_atom = feedparser.parse(
        'https://www.pref.aichi.jp/rss/10/site-758.xml')

    titles = ['新型コロナウイルス感染症患者の発生について',
              "新型コロナウイルス感染者の発生について"]

    is_today = False
    article_url = None
    for entry in d_atom['entries']:
        _day = datetime.strptime(
            entry['updated'], "%Y-%m-%dT%H:%M:%S+09:00") - timedelta(hours=6)
        if _day.date() == today.date() and (entry['title'] in titles):
            article_url = entry['id']
            is_today = True
            break
    return {"date": today, "is_available": is_today, "url": article_url}


def is_data_already_of_the_day(days_before: int = 0):
    today = datetime.today().astimezone(
        timezone(timedelta(hours=9))) - timedelta(hours=6) - timedelta(days=days_before)
    spreadsheet_data = sheets_api.get_data()
    return str(today.date()) in [str(date.date()) for date in spreadsheet_data.index]


def download_pdf_of_the_day(days_before: int = 0):
    status = status_data_of_the_day(days_before=days_before)
    is_already = is_data_already_of_the_day(days_before=days_before)

    if (status["is_available"]) & (not is_already):
        html = requests.get(status["url"])
        soup = BeautifulSoup(html.content, "lxml")
        a = soup.find(class_="detail_free").find('a')
        if '新型コロナウイルス感染者' in a.text:
            pdf_filename = f"{str(status['date'].date())}.pdf"
            pdf_url = urljoin('https://www.pref.aichi.jp/', a.attrs['href'])
            urlretrieve(pdf_url, pdf_filename)
        return pdf_filename
    else:
        return None


def parse_pdf(pdf_filename: str, days_before=0) -> list:
    tbls = camelot.read_pdf(pdf_filename, pages='1')

    df1 = tbls[1].df.loc[1:, :]
    title_indices = [_index for _index in range(
        len(df1.columns)) if _index % 2 == 0]
    number_indices = [_index for _index in range(
        len(df1.columns)) if _index % 2 == 1]

    data = {}
    for title_index, number_index in zip(title_indices, number_indices):
        data |= {_title: int(_number.replace(',', '').replace('県内合計', '')) for _title, _number in zip(
            df1.loc[:, title_index].to_list(), df1.loc[:, number_index].to_list()) if _number != ''}
    if '県内合計' in data.keys():
        data.pop('県内合計')
    cities = "名古屋市	一宮市	豊橋市	豊田市	岡崎市	瀬戸市	半田市	春日井市	豊川市	津島市	碧南市	刈谷市	安城市	西尾市	蒲郡市	犬山市	常滑市	江南市	小牧市	稲沢市	新城市	東海市	大府市	知多市	知立市	尾張旭市	高浜市	岩倉市	豊明市	日進市	田原市	愛西市	清須市	北名古屋市	弥富市	みよし市	あま市	長久手市	東郷町	豊山町	大口町	扶桑町	大治町	蟹江町	飛島村	阿久比町	東浦町	南知多町	美浜町	武豊町	幸田町	設楽町	東栄町	豊根村"
    return [str((datetime.today() - timedelta(days=days_before)).date())] + [data[city]
                                             for city in cities.split()] + [0]


def parse_data_per_age(pdf_filename: str) -> dict:
    tbls = camelot.read_pdf(pdf_filename, pages=f'1')

    df0 = tbls[0].df.loc[1:, :]

    title_indices = [_index for _index in df0.index if _index % 2 == 1]
    number_indices = [_index for _index in df0.index if _index % 2 == 0]

    data = {}
    for title_index, number_index in zip(title_indices, number_indices):
        titles = []
        for _item in df0.loc[title_index, :].to_list():
            titles += _item.split()
        numbers = []
        for _item in df0.loc[number_index, :].to_list():
            numbers += _item.split()
        data |= {_title: int(_number.replace(',', '')) for _title, _number in zip(
            titles, numbers) if _number != ''}
    old_names = {'0歳': '10歳未満', '1～4歳': '10歳未満', '5～9歳': '10歳未満', '10～19歳': '10代', '20～29歳': '20代',
                 '30～39歳': '30代', '40～49歳': '40代', '50～59歳': '50代', '60～64歳': '60代',
                 '65～69歳': '60代', '70～79歳': '70代', '80～89歳': '80代', '90代': '90歳以上', '100歳以上': '90歳以上'}
    refined_data = {}
    for key, value in data.items():
        if key in old_names.keys():
            if old_names[key] not in refined_data.keys():
                refined_data[old_names[key]] = 0
            refined_data[old_names[key]] += value
        else:
            refined_data[key] = value
    if '不明' not in data.keys():
        refined_data['不明'] = 0
    if '計' in refined_data.keys():
        refined_data.pop('計')
    if '合計' in refined_data.keys():
        refined_data.pop('合計')
    return refined_data


def generate_dataframe_from_pdf(pdf_filename: str, days_before: int = 0) -> pandas.DataFrame:

    res = {'date': []}
    data = parse_data_per_age(pdf_filename)
    res['date'].append(
        str((datetime.today() - timedelta(days=days_before)).date()))
    for key in data.keys():
        if key not in res.keys():
            res[key] = []
    for key, value in data.items():
        res[key].append(value)

    return pandas.DataFrame(res).set_index('date')


def main():
    days_before=1
    pdf_filename = download_pdf_of_the_day(days_before=days_before)
    if pdf_filename is not None:

        # update city-wise data
        today_data = parse_pdf(pdf_filename, days_before=days_before)
        sheets_api.update_values(today_data, spreadsheet_name='by_city')

        # update generation database
        data = generate_list_for_spreadsheet(pdf_filename.split('.')[0],
                                             generate_dataframe_from_pdf(pdf_filename, days_before=days_before))
        sheets_api.update_values(data, spreadsheet_name='by_generation')
        return True
    else:
        return None


if __name__ == "__main__":
    main()
