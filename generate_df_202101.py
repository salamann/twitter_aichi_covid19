import camelot
import pandas
import os
import copy
import PyPDF2

pdf_file_path = os.path.join("data", "202101.pdf")

print(f"generating {pdf_file_path}")


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

df_all = copy.deepcopy(df_total)

df_all.columns = df_all.iloc[0, :]
df_all = df_all.sort_values("No")
df_all = df_all[df_all["No"] != "No"]
df_all = df_all.set_index("No")

exceptions = [index for index in df_all.index if "陽性者公表数の修正" in index]

df_all2 = df_all.drop(exceptions[0], axis=0)

new_index = []
new_date = []
for no in df_all2.index:
    if df_all2.at[no, "発表日"] == "":
        _no, _date = no.split()
    else:
        _no, _date = no, df_all2.at[no, "発表日"]
    new_index.append(_no)
    new_date.append(_date.replace("※", ""))

df_all2.index = new_index
df_all2["発表日"] = new_date

df_all2.index = [int(_) for _ in df_all2.index]
df_all2 = df_all2.sort_index()


df_all2["発表日"] = pandas.to_datetime(
    ['2021年' + _ if no > 16577 else '2020年' + _ for no, _ in zip(df_all2.index, df_all2['発表日'])], format='%Y年%m月%d日')


df_all2.to_pickle(f"{os.path.splitext(pdf_file_path)[0]}.zip")
