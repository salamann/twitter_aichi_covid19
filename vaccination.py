import requests
from pathlib import Path
import pandas
import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Union


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


def get_aichi_population() -> int:
    url_aichi_population = "https://www.pref.aichi.jp/toukei/"
    site = requests.get(url_aichi_population)
    soup = BeautifulSoup(site.content, "lxml")
    tds = soup.find(id="submenu_toukei_right_omonagyoumu").find_all("td")
    [num] = [i for i, _ in enumerate(tds) if "人口" in _.text]
    return int(tds[num + 1].text.replace("人", "").replace(",", ""))


def get_vaccination_number() -> int:
    # import ssl
    # context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    # context.set_ciphers('DEFAULT@SECLEVEL=1')
    url_medical_staff = "https://www.kantei.go.jp/jp/content/IRYO-kenbetsu-vaccination_data.xlsx"
    file_name_medical_staff = Path(url_medical_staff).name

    url_data_medical = requests.get(url_medical_staff).content

    with open(file_name_medical_staff, mode='wb') as f:
        f.write(url_data_medical)

    url_non_medical = "https://www.kantei.go.jp/jp/content/KOREI-kenbetsu-vaccination_data.xlsx"
    file_name_non_medical = Path(url_non_medical).name
    url_data_non_medical = requests.get(url_non_medical).content

    with open(file_name_non_medical, mode='wb') as f:
        f.write(url_data_non_medical)

    df_m = get_df(file_name_medical_staff, "医療従事者接種回数")
    df_g = get_df(file_name_non_medical, "高齢者等接種回数")
    if (path_df_vac := Path("df_vac.zip")).exists():
        df_vac = pandas.read_pickle(path_df_vac)
        df_today = pandas.concat([df_vac, df_m, df_g])
    else:
        df_today = pandas.concat([df_m, df_g])
    df_today.to_pickle("df_vac.zip")

    [nm] = df_m["医療従事者接種回数"].to_list()
    [ne] = df_g["高齢者等接種回数"].to_list()
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
            return True, nvac


def generate_headline():
    is_update, nvac = check_update()
    if is_update:
        url_kantei = "https://www.kantei.go.jp/jp/headline/kansensho/vaccine.html"
        return f"[更新]現在の愛知県の新型コロナワクチンの総接種回数は{nvac}回です。現在の人口カバー率は{nvac/get_aichi_population()/2*100:.2f}%です。詳しくは首相官邸サイトを参照 > {url_kantei}"
    else:
        return None


def post() -> None:
    from twitter_post import post

    headline = generate_headline()
    if headline is not None:
        post(headline)


if __name__ == "__main__":
    print(generate_headline())
