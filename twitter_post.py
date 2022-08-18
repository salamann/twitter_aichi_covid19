import json

from requests_oauthlib import OAuth1Session


def get_posts(tweet_number=20) -> dict:
    import config
    twitter_session = OAuth1Session(config.api_key,
                                    config.api_secret,
                                    config.access_token,
                                    config.access_token_secret)
    url = "https://api.twitter.com/1.1/statuses/user_timeline.json"  # タイムライン取得エンドポイント

    params = {'count': tweet_number}  # 取得数
    res = twitter_session.get(url, params=params)
    timelines = json.loads(res.text)
    return timelines


def post(message):
    import config
    twitter_session = OAuth1Session(config.api_key,
                                    config.api_secret,
                                    config.access_token,
                                    config.access_token_secret)
    api_endpoint = "https://api.twitter.com/1.1/statuses/update.json"

    res = twitter_session.post(api_endpoint, params={"status": message})

    if res.status_code == 200:
        print("Success.")
    else:
        message = f"""Failed.
 - Responce Status Code : {res.status_code}
 - Error Code : {res.json()["errors"][0]["code"]}
 - Error Message : {res.json()["errors"][0]["message"]}
"""
        print(message)


def image_post(file_name, message):

    # Twitter APIのAuthToken等は事前に用意
    # OAuth認証 セッションを開始
    import config
    twitter_session = OAuth1Session(config.api_key,
                                    config.api_secret,
                                    config.access_token,
                                    config.access_token_secret)

    url_media = "https://upload.twitter.com/1.1/media/upload.json"
    url_text = "https://api.twitter.com/1.1/statuses/update.json"

    # 画像をひらく
    with open(file_name, "rb") as f:
        data = f.read()
    files = {"media": data}
    req_media = twitter_session.post(url_media, files=files)

    # レスポンス
    if req_media.status_code != 200:
        print("画像アップロード失敗: %s", req_media.text)
        exit()

    # media_id を取得
    media_id = json.loads(req_media.text)['media_id']

    # 投稿した画像をツイートに添付したい場合はこんな風に取得したmedia_idを"media_ids"で指定してツイートを投稿
    params = {'status': message, "media_ids": [media_id]}
    req_media = twitter_session.post(url_text, params=params)


if __name__ == "__main__":
    # image_post("rt2021-01-23.png", "実行再生産数")
    pass
