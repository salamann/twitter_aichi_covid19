import camelot
import pandas
import os
import copy
from datetime import datetime, timedelta
import feedparser
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from twitter_post import post
import re
import PyPDF2


def get_day_of_week_jp(dt):
    w_list = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
    return(w_list[dt.weekday()])


def generate_df_from_aichi(pdf_file_path):
    print(f"generating {pdf_file_path}")

    # pdf_file_path = "20201222.pdf"

    pdf_read = PyPDF2.PdfFileReader(pdf_file_path)
    num_page = pdf_read.numPages

    if num_page > 10:
        page_list = list(range(10, num_page, 10))
    else:
        page_list = [num_page]
    init = 1
    dfs_lap = []
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

    # tbls = camelot.read_pdf(pdf_file_path, pages='1-end')

    # dfs = []
    # for table in tbls:
    #     df = table.df
    #     dfs.append(df)
    # df_all = pandas.concat(dfs)
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

    if 1:
        # index = [_i for _d, _i in zip(
        #     df_all["発表日"], df_all.index) if "患者発生届取り下げ" in _d][0]
        # df_all = df_all.drop(index, axis=0)
        # index = [_i for _d, _i in zip(
        #     df_all["発表日"], df_all.index) if "欠番" in _d][0]
        # df_all = df_all.drop(index, axis=0)

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

    df_all.to_pickle(f"{os.path.splitext(pdf_file_path)[0]}.zip")


def get_number_by_delta(data_frame, days_before, region=None):
    today = datetime.today()

    specific_day = today + timedelta(days_before)
    smonth = specific_day.month
    sday = specific_day.day

    if region is not None:
        if region == "愛知県":
            cond0 = (data_frame['住居地'] != '名古屋市')
            cond0 &= (data_frame['住居地'] != '豊橋市')
            cond0 &= (data_frame['住居地'] != '豊田市')
            cond0 &= (data_frame['住居地'] != '岡崎市')
            cond0 &= (data_frame['住居地'] != '一宮市')
            data_frame = data_frame[cond0]
        else:
            data_frame = data_frame[data_frame['住居地'] == region]
    # print(specific_day)
    n = 0
    for mo, da in zip(data_frame['発表日'].dt.month, data_frame['発表日'].dt.day):
        if (smonth == mo) and (sday == da):
            n += 1
    return n


def get_number_by_date(data_frame, date, delta=0):
    _date = datetime.strptime(date, '%Y/%m/%d') + timedelta(days=delta)

    n = 0
    for mo, da in zip(data_frame['発表日'].dt.month, data_frame['発表日'].dt.day):
        if (_date.month == mo) and (_date.day == da):
            n += 1
    return n


def post_okazaki():
    # if os.path.isfile("okazaki_lock.zip"):
    #     pass
    # else:
    # okazaki_url = 'https://www.city.okazaki.lg.jp/'
    load_url = 'https://www.city.okazaki.lg.jp/1550/1562/1615/p025980.html'
    html = requests.get(load_url)
    soup = BeautifulSoup(html.content, "html.parser")
    h3 = soup.find(class_="article").find("h3")
    is_num_today_zero = ("新規陽性者数は0件です" in h3.text)
    article_text = h3.find_all("a")
    if article_text == []:
        article_text = soup.find("h3")
    today = datetime.today()
    for a in article_text:
        # print(a.text)
        if (nums := re.findall(r"\d+", a.text)) != []:
            break
    date = datetime.strptime(f"{nums[0]}月{nums[1]}日", "%m月%d日")
    if (today.month == date.month) & (today.day == date.day):
        is_today = True
    else:
        is_today = False
    # is_today = True
    if is_today:
        if is_num_today_zero:
            num_today = 0
        elif (len(nums) == 6) or (len(nums) == 5):
            num_today = int(nums[4]) - int(nums[2]) + 1
        elif len(nums) == 4:
            num_today = 1
        elif len(nums) == 3:
            num_today = int(nums[2])
        df0 = pandas.read_pickle("database.zip")
        num_last_week = get_number_by_delta(df0, -7, region="岡崎市")
        if h3.find("a") is not None:
            article_url = urljoin(load_url,
                                  h3.find("a")['href'].replace("./", ""))
        else:
            article_url = load_url
        # print(article_url)
        youbi = get_day_of_week_jp(today)
        if not os.path.isfile("okazaki_lock.zip"):
            header = f'[速報]岡崎市の本日の新型コロナウイルスの新規感染者数は{num_today}人(先週の{youbi}に比べて{num_today-num_last_week:+}人)でした。詳細は公式サイトを参照 > {article_url}'
        elif int(pandas.read_pickle("okazaki_lock.zip").loc["岡崎市", "本日"]) < num_today:
            header = f'[更新]岡崎市の本日の新型コロナウイルスの新規感染者数は{num_today}人(先週の{youbi}に比べて{num_today-num_last_week:+}人)に更新されました。詳細は公式サイトを参照 > {article_url}'
        else:
            header = None
        if header is not None:
            post(header)
            # print(header)
            data_for_save = pandas.DataFrame(
                [{'本日': num_today, '先週': num_last_week}], index=['岡崎市'])
            data_for_save.to_pickle("okazaki_lock.zip")
            time.sleep(5)
            print("岡崎市更新しました", datetime.today())


def post_toyohashi():
    if os.path.isfile("toyohashi_lock.zip"):
        pass
    else:
        load_url = 'https://www.city.toyohashi.lg.jp/41805.htm'

        html = requests.get(load_url)
        soup = BeautifulSoup(html.content, "html.parser")
        toyohashi_new = soup.find(class_='Item_normal')

        # toyohashi_header = "豊橋市が新型コロナウイルス情報を更新しました > "
        article_text = toyohashi_new.text.replace("\n", "").replace("\xa0", "")
        article_url = load_url

        today = datetime.today()
        nums = re.findall(r"\d+", article_text)
        nums = [_num.translate(str.maketrans(
            {chr(0xFF01 + i): chr(0x21 + i) for i in range(94)})) for _num in nums]
        date = datetime.strptime(f"{nums[1]}月{nums[2]}日", "%m月%d日")
        if (today.month == date.month) & (today.day == date.day):
            is_today = True
        else:
            is_today = False
        # is_today = True
        if is_today:
            num_today = int(nums[3])
            df0 = pandas.read_pickle("database.zip")
            num_last_week = get_number_by_delta(df0, -7, region="豊橋市")
            youbi = get_day_of_week_jp(today)
            header = f'[速報]豊橋市の本日の新型コロナウイルスの新規感染者数は{num_today}人(先週の{youbi}に比べて{num_today-num_last_week:+}人)でした。詳細は公式サイトを参照 > {article_url}'
            post(header)
            data_for_save = pandas.DataFrame(
                [{'本日': num_today, '先週': num_last_week}], index=['豊橋市'])
            data_for_save.to_pickle("toyohashi_lock.zip")
            time.sleep(5)
            print("豊橋市更新しました", datetime.today())


def post_toyota():
    # if os.path.isfile("toyota_lock.zip"):
    #     pass
    # else:
    load_url = 'https://www.city.toyota.aichi.jp/kurashi/kenkou/eisei/1039225.html'
    html = requests.get(load_url)
    soup = BeautifulSoup(html.content, "html.parser")
    toyota_new = soup.find(class_="objectlink")
    today = f"{datetime.today().month}月{datetime.today().day}日"
    article_text = toyota_new.find("li").text
    article_url = urljoin(
        load_url, toyota_new.find("li").find('a')['href'])

    today = datetime.today()
    nums = re.findall(r"\d+", article_text)
    # print(nums)
    date = datetime.strptime(f"{nums[0]}月{nums[1]}日", "%m月%d日")
    if (today.month == date.month) & (today.day == date.day):
        is_today = True
    else:
        is_today = False

    is_zero = False
    if not is_today:
        load_url2 = "https://www.city.toyota.aichi.jp/kurashi/kenkou/eisei/1037578.html"

        html = requests.get(load_url2)
        soup = BeautifulSoup(html.content, "html.parser")
        toyota_new = soup.find("h2")
        article_text = toyota_new.next_element.next_element.next_element.text
        nums = re.findall(r"\d+", article_text)
        is_zero = "いません" in article_text
        date = datetime.strptime(f"{nums[0]}月{nums[1]}日", "%m月%d日")
        if (today.month == date.month) & (today.day == date.day):
            is_today = True
        else:
            is_today = False

    # ex1 = "市内在住者（3人）が新型コロナウイルスに感染したことが判明しました。（1248～1250例目）"
    if is_today:
        if len(nums) == 3:
            num_today = 1
        elif is_zero:
            num_today = 0
        else:
            num_today = int(nums[3]) - int(nums[2]) + 1
            # num_today = int(nums[2])
        df0 = pandas.read_pickle("database.zip")
        num_last_week = get_number_by_delta(df0, -7, region="豊田市")
        youbi = get_day_of_week_jp(today)

        if not os.path.isfile("toyota_lock.zip"):
            header = f'[速報]豊田市の本日の新型コロナウイルスの新規感染者数は{num_today}人(先週の{youbi}に比べて{num_today-num_last_week:+}人)でした。詳細は公式サイトを参照 > {article_url}'
        elif int(pandas.read_pickle("toyota_lock.zip").loc["豊田市", "本日"]) < num_today:
            header = f'[更新]豊田市の本日の新型コロナウイルスの新規感染者数は{num_today}人(先週の{youbi}に比べて{num_today-num_last_week:+}人)に更新されました。詳細は公式サイトを参照 > {article_url}'
        else:
            header = None
        if (header is not None) and (num_today > 0):
            data_for_save = pandas.DataFrame(
                [{'本日': num_today, '先週': num_last_week}], index=['豊田市'])
            data_for_save.to_pickle("toyota_lock.zip")
            post(header)
            time.sleep(5)
            print("豊田市更新しました", datetime.today())


def post_nagoya():
    if os.path.isfile("nagoya_lock.zip"):
        pass
    else:
        load_url = 'https://www.city.nagoya.jp/kenkofukushi/page/0000126920.html'
        html = requests.get(load_url)
        soup = BeautifulSoup(html.content, "html.parser")
        nagoya_h3 = soup.find("h3")
        date = datetime.strptime(nagoya_h3.text.split("令和3年")
                                 [1].split("現在")[0], '%m月%d日')
        # date = datetime.strptime(nagoya_h3.text.split("令和2年")
        #                          [1].split("現在")[0], '%m月%d日')
        today = datetime.today()
        if (today.month == date.month) & (today.day == date.day):
            is_today = True
        else:
            is_today = False
        article_text = nagoya_h3.next_element.next_element.find("p").text
        article_url = load_url
        num_today = int(re.sub("\\D", "", article_text))
        # is_today = True
        if is_today:
            df0 = pandas.read_pickle("database.zip")
            num_last_week = get_number_by_delta(df0, -7, region="名古屋市")
            youbi = get_day_of_week_jp(today)
            header = f'[速報]名古屋市の本日の新型コロナウイルスの新規感染者数は{num_today}人(先週の{youbi}に比べて{num_today-num_last_week:+}人)でした。詳細は公式サイトを参照 > {article_url}'
            post(header)
            data_for_save = pandas.DataFrame(
                [{'本日': num_today, '先週': num_last_week}], index=['名古屋市'])
            data_for_save.to_pickle("nagoya_lock.zip")
            time.sleep(5)
            print("名古屋市更新しました", datetime.today())


def post_aichi():
    if os.path.isfile("aichi_lock.zip"):
        pass
    else:
        d_atom = feedparser.parse(
            'https://www.pref.aichi.jp/rss/10/site-758.xml')

        is_today = False
        today = datetime.today() - timedelta(hours=6)
        for entry in d_atom['entries']:
            _day = datetime.strptime(
                entry['updated'], "%Y-%m-%dT%H:%M:%S+09:00")
            # print(_day.month, today.month, _day.day, today.day,
            #       entry['title'], '新型コロナウイルス感染症患者の発生について')
            if (_day.month == today.month) and (_day.day == today.day) and (entry['title'] == '新型コロナウイルス感染症患者の発生について'):
                article_url = entry['id']
                is_today = True
                break
        if is_today:
            load_url = article_url
            # load_url = 'https://www.pref.aichi.jp/site/covid19-aichi/pressrelease-ncov201208.html'
            html = requests.get(load_url)
            soup = BeautifulSoup(html.content, "html.parser")
            article_text = soup.find(class_="mol_textblock").text
            nums = re.findall(r"\d+", article_text)
            num_today = int(nums[0])
            df0 = pandas.read_pickle("database.zip")
            num_last_week = get_number_by_delta(df0, -7, region="愛知県")
            youbi = get_day_of_week_jp(today)
            header = f'[速報]愛知県管轄自治体（名古屋市・豊橋市・豊田市・岡崎市・一宮市を除く愛知県）の本日の新型コロナウイルスの新規感染者数は{num_today}人(先週の{youbi}に比べて{num_today-num_last_week:+}人)でした。詳細は公式サイトを参照 > {article_url}'
            post(header)
            data_for_save = pandas.DataFrame(
                [{'本日': num_today, '先週': num_last_week}], index=['愛知県'])
            data_for_save.to_pickle("aichi_lock.zip")
            time.sleep(5)
            print("愛知県更新しました", datetime.today())


def post_zentai():
    is_toyohashi_done = os.path.isfile("toyohashi_lock.zip")
    is_toyota_done = os.path.isfile("toyota_lock.zip")
    is_okazaki_done = os.path.isfile("okazaki_lock.zip")
    is_nagoya_done = os.path.isfile("nagoya_lock.zip")
    is_aichi_done = os.path.isfile("aichi_lock.zip")
    is_ichinomiya_done = os.path.isfile("ichinomiya_lock.zip")

    is_dones = [is_aichi_done, is_nagoya_done,
                is_okazaki_done, is_toyohashi_done, is_toyota_done, is_ichinomiya_done]
    if (all(is_dones)) and (not os.path.isfile("zentai.lock")):
        df_toyohashi = pandas.read_pickle("toyohashi_lock.zip")
        df_toyota = pandas.read_pickle("toyota_lock.zip")
        df_okazaki = pandas.read_pickle("okazaki_lock.zip")
        df_nagoya = pandas.read_pickle("nagoya_lock.zip")
        df_aichi = pandas.read_pickle("aichi_lock.zip")
        df_ichinomiya = pandas.read_pickle("ichinomiya_lock.zip")
        df_today = pandas.concat(
            [df_toyohashi, df_aichi, df_nagoya, df_toyota, df_okazaki, df_ichinomiya])
        num_today = df_today['本日'].sum()
        num_last_week = df_today['先週'].sum()
        youbi = get_day_of_week_jp(datetime.today() - timedelta(hours=6))

        article_url = 'https://www.pref.aichi.jp/site/covid19-aichi/'
        header = f'[速報]本日の愛知県全体の新型コロナウイルスの新規感染者数は{num_today}人(先週の{youbi}に比べて{num_today-num_last_week:+}人)でした。詳細は公式サイトを参照 > {article_url}'
        # print(header)
        post(header)
        df_today.to_pickle(os.path.join("data",
                                        f"{str(datetime.today()-timedelta(hours=6)).split()[0]}_from_sum.zip"))
        with open("zentai.lock", "w", encoding="utf-8") as f:
            f.write("")
        time.sleep(5)
        print("愛知県全体更新しました", datetime.today())


if __name__ == "__main__":
    # generate_df_from_aichi(os.path.join("data", "202101.pdf"))
    # generate_df_from_aichi("20201207.pdf")
    # post_toyohashi()
    # post_toyota()
    # post_aichi()
    # post_okazaki()
    pass
