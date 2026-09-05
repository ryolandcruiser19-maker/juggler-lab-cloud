"""
ジャグラーラボ
営業日判定共通処理

23:50取得開始
↓
0時跨ぎ
↓
前営業日として扱う

ための共通関数
"""


from datetime import datetime, timedelta



# ==================================
# 営業日取得
# ==================================

def get_business_date():

    """
    現在時刻から営業日を判定する

    0:00〜8:59
        前日営業日

    9:00以降
        当日営業日

    """

    now = datetime.now()


    if now.hour < 9:

        return (
            now.date()
            -
            timedelta(days=1)
        )


    else:

        return now.date()



# ==================================
# 文字列変換
# ==================================

def get_business_date_text():

    return (
        get_business_date()
        .strftime("%Y-%m-%d")
    )



def get_business_date_file():

    return (
        get_business_date()
        .strftime("%Y%m%d")
    )