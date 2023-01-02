from datetime import datetime, timedelta
from pathlib import Path

import pandas
import matplotlib
import matplotlib.pyplot as plt

# from utility import get_spreadsheet_data
# from config import spreadsheet_generation_url
from twitter_post import image_post
import sheets_api

matplotlib.rc('font', family='Noto Sans CJK JP')

today = datetime.today() - timedelta(hours=6)


def create_week_average(data: pandas.DataFrame) -> pandas.DataFrame:
    df = pandas.DataFrame([])
    indices = data.index.sort_values(ascending=False)
    for num in range(len(indices) - 6):
        df1 = data.loc[indices[num:num + 7], :].sum().to_frame().transpose()
        df1.index = [indices[num]]
        df = pandas.concat([df, df1])
    return df // 7


def create_graph(df2: pandas.DataFrame) -> str:
    for gen in df2.columns:
        plt.plot(df2.index[:35], df2[gen][:35], label=gen)

    line_styles = ['-', '--', '-.', ':']
    for index, line in enumerate(plt.gca().get_lines()):
        line.set_linestyle(line_styles[index % 4])
    plt.xlabel('日付')
    plt.ylabel('感染者数(7日移動平均)')
    plt.grid(ls=":")
    plt.xlim([df2.index[:35][-1], df2.index[:35][0]])
    plt.legend(loc="upper left", fontsize='small')
    plt.xticks(df2[:35].index[::2], fontsize="x-small",
               rotation=45, ha='right')
    plt.yticks(fontsize="small")
    plt.suptitle('愛知県の世代別感染者数（7日移動平均）')
    file_name = Path("data").joinpath(f'generation_{today.date()}.png')
    plt.savefig(file_name, facecolor="w", dpi=200)
    return file_name


def create_message(df2: pandas.DataFrame) -> str:
    message = "[更新]今日の愛知県内の世代別感染者数(7日間移動平均)ランキングは、"
    rankings = df2.loc[str(today.date()),
                       :].sort_values(ascending=False)
    for _index, (gen_name, number) in enumerate(zip(rankings.index, rankings.to_list())):
        message += f"{_index+1}位は{gen_name}で{number}人、"
        if _index >= 5:
            message = message[:-1] + 'でした。'
            break
    return message


def post_generation() -> None:

    # data = get_spreadsheet_data(
    #     url=spreadsheet_generation_url, index_name='date')
    data = sheets_api.get_data(spreadsheet_name="by_generation")
    df2 = create_week_average(data)
    file_name = create_graph(df2)
    message = create_message(df2)
    image_post(file_name, message)


if __name__ == "__main__":
    post_generation()
