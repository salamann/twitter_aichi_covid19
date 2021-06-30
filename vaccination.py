from pathlib import Path
import re
from datetime import datetime
from typing import Union

import pandas
import requests
from bs4 import BeautifulSoup


def get_open_data() -> str:
    url = "https://vrs-data.cio.go.jp/vaccination/opendata/latest/summary_by_prefecture.csv"
    file_name = Path(url).name

    url_data = requests.get(url).content

    with open(file_name, mode='wb') as f:
        f.write(url_data)
    return file_name


def get_vaccination_number_from_open_data(file_name) -> int:
    df = pandas.read_csv(file_name, encoding="sjis")
    df = df.set_index("prefecture_name")
    return sum(
        df.loc["愛知県", "count_first_or_mid_general":"count_second_or_full_general"])


def get_non_medical_number(file_name) -> dict:
    df = pandas.read_csv(file_name, encoding="sjis")
    df = df.set_index("prefecture_name")
    # df.loc["愛知県",
    #        "count_first_or_mid_general":"count_second_or_full_general"]
    n_first_dose = int(df.at["愛知県", "count_first_or_mid_general"])
    n_second_dose = int(df.at["愛知県", "count_second_or_full_general"])
    return {"1回目": n_first_dose, "2回目": n_second_dose}


def get_df(file_name: str, column_name: str) -> pandas.DataFrame:

    df_medical = pandas.read_excel(file_name)
    date_text = "".join(
        [_ for _ in df_medical.loc[0].to_list() if not pandas.isna(_)])

    pattern = r'.*?(\d+)月(\d+)日時点'

    repatter = re.compile(pattern)
    result = repatter.match(date_text)

    date_of_day = datetime.strptime(
        f"2021_{result.group(1)}_{result.group(2)}", "%Y_%m_%d")
#     df_medical = pandas.read_excel(file_name_medical_staff)
    df_medical.columns = df_medical.loc[1, :].to_list()
    df_medical = df_medical.loc[:, "都道府県名":"内２回目"]
    df_medical = df_medical.dropna()
    df_of_day = df_medical[df_medical["都道府県名"].str.contains("愛知県")]
    df_of_day = df_of_day.assign(Date=date_of_day).loc[:, [
        "接種回数", "Date"]].set_index("Date")
    df_of_day.columns = [column_name]
    return df_of_day


def get_medical_number(file_name: str) -> dict:

    df_medical = pandas.read_excel(file_name)
    date_text = "".join(
        [_ for _ in df_medical.loc[0].to_list() if not pandas.isna(_)])

    pattern = r'.*?(\d+)月(\d+)日時点'

    repatter = re.compile(pattern)
    result = repatter.match(date_text)

    # date_of_day = datetime.strptime(
    #     f"2021_{result.group(1)}_{result.group(2)}", "%Y_%m_%d")
#     df_medical = pandas.read_excel(file_name_medical_staff)
    df_medical.columns = df_medical.loc[1, :].to_list()
    df_medical = df_medical.loc[:, "都道府県名":"内２回目"]
    df_medical = df_medical.dropna()
    df_of_day = df_medical[df_medical["都道府県名"].str.contains("愛知県")]
    [n_first_dose] = df_of_day["内１回目"].to_list()
    [n_second_dose] = df_of_day["内２回目"].to_list()
    return {"1回目": n_first_dose, "2回目": n_second_dose}


def get_aichi_population() -> int:
    url_aichi_population = "https://www.pref.aichi.jp/toukei/"
    site = requests.get(url_aichi_population)
    soup = BeautifulSoup(site.content, "lxml")
    tds = soup.find(id="submenu_toukei_right_omonagyoumu").find_all("td")
    [num] = [i for i, _ in enumerate(tds) if "人口" in _.text]
    return int(tds[num + 1].text.replace("人", "").replace(",", ""))


def get_medical_data() -> str:
    url_medical_staff = "https://www.kantei.go.jp/jp/content/IRYO-kenbetsu-vaccination_data.xlsx"
    file_name_medical_staff = Path(url_medical_staff).name

    url_data_medical = requests.get(url_medical_staff).content

    with open(file_name_medical_staff, mode='wb') as f:
        f.write(url_data_medical)
    return file_name_medical_staff


def get_vaccination_number() -> int:
    # import ssl
    # context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    # context.set_ciphers('DEFAULT@SECLEVEL=1')
    url_medical_staff = "https://www.kantei.go.jp/jp/content/IRYO-kenbetsu-vaccination_data.xlsx"
    file_name_medical_staff = Path(url_medical_staff).name

    url_data_medical = requests.get(url_medical_staff).content

    with open(file_name_medical_staff, mode='wb') as f:
        f.write(url_data_medical)

    df_m = get_df(file_name_medical_staff, "医療従事者接種回数")
    [nm] = df_m["医療従事者接種回数"].to_list()

    # url_non_medical = "https://www.kantei.go.jp/jp/content/KOREI-kenbetsu-vaccination_data.xlsx"
    # file_name_non_medical = Path(url_non_medical).name
    # url_data_non_medical = requests.get(url_non_medical).content

    # with open(file_name_non_medical, mode='wb') as f:
    #     f.write(url_data_non_medical)

    # df_g = get_df(file_name_non_medical, "高齢者等接種回数")
    ne = get_vaccination_number_from_open_data(get_open_data())
    df_g = pandas.DataFrame(
        [ne], index=[datetime.today().date()], columns=["高齢者等接種回数"])
    # print(df_g)

    if (path_df_vac := Path("df_vac.zip")).exists():
        df_vac = pandas.read_pickle(path_df_vac)
        df_today = pandas.concat([df_vac, df_m, df_g])
    else:
        df_today = pandas.concat([df_m, df_g])
    df_today.to_pickle("df_vac.zip")

    # [ne] = df_g["高齢者等接種回数"].to_list()
    return nm + ne


def check_update() -> Union[bool, int]:
    nvac = get_vaccination_number()

    if not (vac_path := Path("vac_number_latest.txt")).exists():
        with open(vac_path, "w") as f:
            f.write(str(nvac))
        return True, nvac
    else:
        with open(vac_path, "r") as f:
            vac_number_ex = int(f.read())
        if nvac == vac_number_ex:
            return False, nvac
        elif nvac > vac_number_ex:
            with open(vac_path, "w") as f:
                f.write(str(nvac))
            return True, nvac


def generate_headline_first_second(medical_dict: dict, nonmedical_dict: dict) -> str:
    n_first_dose = medical_dict["1回目"] + nonmedical_dict["1回目"]
    n_second_dose = medical_dict["2回目"] + nonmedical_dict["2回目"]
    n_total = n_first_dose + n_second_dose
    aichi_pop = get_aichi_population()
    url_kantei = "https://www.kantei.go.jp/jp/headline/kansensho/vaccine.html"
    headline = f"[更新]現在の愛知県の新型コロナワクチンの総接種回数は{n_total}回"
    headline += f"(1回目接種{n_first_dose}回、2回目接種{n_second_dose}回)です。"
    headline += f"1回目接種率は{n_first_dose/aichi_pop*100:.2f}%、"
    headline += f"2回目接種率は{n_second_dose/aichi_pop*100:.2f}%です。"
    headline += f"詳しくは首相官邸サイトを参照 > {url_kantei}"
    return headline


def generate_headline() -> None:
    is_update, nvac = check_update()
    if is_update:
        url_kantei = "https://www.kantei.go.jp/jp/headline/kansensho/vaccine.html"
        return f"[更新]現在の愛知県の新型コロナワクチンの総接種回数は{nvac}回です。現在の人口カバー率は{nvac/get_aichi_population()/2*100:.2f}%です。詳しくは首相官邸サイトを参照 > {url_kantei}"
    else:
        return None


# def post() -> None:
#     from twitter_post import post

#     headline = generate_headline()
#     if headline is not None:
#         post(headline)


def post() -> None:
    from twitter_post import post
    medical = get_medical_number(get_medical_data())
    non_medical = get_non_medical_number(get_open_data())
    headline = generate_headline_first_second(medical, non_medical)

    last_number = get_last_total_number()
    current_numer = extract_total_number(headline)
    if current_numer > last_number:
        post(headline)
    else:
        print("The number is the same as the last number.")


def get_last_post(timelines) -> str:
    for timeline in timelines:
        if "コロナワクチン" in timeline["text"]:
            return timeline["text"]


def extract_total_number(text: str) -> int:
    pattern = r'.*?総接種回数は(\d+)回'

    # compile then match
    repatter = re.compile(pattern)
    result = repatter.match(text)

    return int(result.group(1))


def get_last_total_number() -> int:
    from twitter_post import get_posts
    timelines = get_posts()
    text_line_text = get_last_post(timelines)
    return extract_total_number(text_line_text)


if __name__ == "__main__":
    post()
    # post2_vaccination()
    # medical = get_medical_number(get_medical_data())
    # non_medical = get_non_medical_number(get_open_data())
    # print(generate_headline_first_second(medical, non_medical))
    # a = get_vaccination_number_from_open_data_df("summary_by_prefecture.csv")
    # print(a["count_first_or_mid_general"])
    # print(a["count_second_or_full_general"])
    # print(get_medical_number("IRYO-kenbetsu-vaccination_data.xlsx"))
    # df_m = get_df("IRYO-kenbetsu-vaccination_data.xlsx", "医療従事者接種回数")

    # print(generate_headline())
    # print(get_open_data())
    # print(get_vaccination_number())
