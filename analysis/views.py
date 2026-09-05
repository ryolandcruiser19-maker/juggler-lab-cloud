"""
ジャグラーラボ
分析ビュー取得

アプリ表示用データ取得層
"""

import pandas as pd

from database.db import (
    fetch_all,
    fetch_one,
)


# ==================================
# 最新営業日取得
# ==================================

def get_latest_date():

    row = fetch_one(
        """
        SELECT
            MAX(日付) AS 最新日
        FROM daily_data
        """
    )

    if row is None:
        return None

    return row["最新日"]


# ==================================
# 前回営業日取得
#
# 最新営業日の直前に存在する
# daily_data上の営業日を取得
# ==================================

def get_previous_date():

    latest_date = get_latest_date()

    if latest_date is None:
        return None

    row = fetch_one(
        """
        SELECT
            MAX(日付) AS 前回営業日
        FROM daily_data
        WHERE 日付 < ?
        """,
        [
            latest_date,
        ],
    )

    if row is None:
        return None

    return row["前回営業日"]


# ==================================
# 最新予測日取得
# ==================================

def get_latest_prediction_date():

    row = fetch_one(
        """
        SELECT
            MAX(日付) AS 最新予測日
        FROM prediction_score
        """
    )

    if row is None:
        return None

    return row["最新予測日"]


# ==================================
# 前日の概要
#
# 最新営業日の1つ前の営業日を対象
# ==================================

def get_latest_summary():

    previous_date = get_previous_date()

    if previous_date is None:
        return {}

    row = fetch_one(
        """
        SELECT

            ? AS 日付,

            COUNT(*) AS 対象台数,

            SUM(
                CASE
                    WHEN 評価 = '◎'
                    THEN 1
                    ELSE 0
                END
            ) AS ◎台数,

            SUM(
                CASE
                    WHEN 評価 = '○'
                    THEN 1
                    ELSE 0
                END
            ) AS ○台数,

            SUM(
                CASE
                    WHEN 評価 = '△'
                    THEN 1
                    ELSE 0
                END
            ) AS △台数,

            ROUND(
                AVG(G数),
                0
            ) AS 平均G数,

            ROUND(
                AVG(合成確率),
                1
            ) AS 平均合成確率

        FROM daily_data

        WHERE 日付 = ?

        """,
        [
            previous_date,
            previous_date,
        ],
    )

    if row is None:
        return {}

    result = dict(row)

    target_count = result.get("対象台数") or 0
    excellent_count = result.get("◎台数") or 0
    good_count = result.get("○台数") or 0
    triangle_count = result.get("△台数") or 0

    # ◎率
    if target_count > 0:

        result["◎率"] = round(
            excellent_count
            / target_count
            * 100,
            1,
        )

        # ◎＋○率
        result["高設定率"] = round(
            (
                excellent_count
                + good_count
            )
            / target_count
            * 100,
            1,
        )

        # ○率
        result["○率"] = round(
            good_count
            / target_count
            * 100,
            1,
        )

        # △率
        result["△率"] = round(
            triangle_count
            / target_count
            * 100,
            1,
        )

    else:

        result["◎率"] = 0.0
        result["高設定率"] = 0.0
        result["○率"] = 0.0
        result["△率"] = 0.0

    return result


# ==================================
# 旧関数互換
# ==================================

def get_today_summary():

    return get_latest_summary()


# ==================================
# 前日の島別状況
# ==================================

def get_latest_island_summary():

    previous_date = get_previous_date()

    if previous_date is None:
        return pd.DataFrame()

    rows = fetch_all(
        """
        SELECT

            島,

            COUNT(*) AS 台数,

            ROUND(
                AVG(G数),
                0
            ) AS 平均G数,

            ROUND(
                AVG(合成確率),
                1
            ) AS 平均合成,

            SUM(
                CASE
                    WHEN 評価 = '◎'
                    THEN 1
                    ELSE 0
                END
            ) AS ◎台数,

            SUM(
                CASE
                    WHEN 評価 = '○'
                    THEN 1
                    ELSE 0
                END
            ) AS ○台数

        FROM daily_data

        WHERE 日付 = ?

        GROUP BY 島

        ORDER BY
            ◎台数 DESC,
            ○台数 DESC

        """,
        [
            previous_date,
        ],
    )

    df = pd.DataFrame(
        [dict(row) for row in rows]
    )

    if df.empty:
        return df

    # 島ごとの高設定率を追加
    df["高設定率"] = (
        (
            df["◎台数"]
            + df["○台数"]
        )
        / df["台数"]
        * 100
    ).round(1)

    # 島ごとの◎率を追加
    df["◎率"] = (
        df["◎台数"]
        / df["台数"]
        * 100
    ).round(1)

    return df


# ==================================
# 前日の高評価台
# ==================================

def get_latest_good_machines():

    previous_date = get_previous_date()

    if previous_date is None:
        return pd.DataFrame()

    rows = fetch_all(
        """
        SELECT

            台番号,
            機種,
            島,
            BB,
            RB,
            G数,
            合成確率,
            評価

        FROM daily_data

        WHERE 日付 = ?

        AND 評価 IN ('◎', '○')

        ORDER BY

            CASE
                WHEN 評価 = '◎'
                THEN 1
                ELSE 2
            END,

            合成確率

        """,
        [
            previous_date,
        ],
    )

    return pd.DataFrame(
        [dict(row) for row in rows]
    )


# ==================================
# 予測ランキング
# ==================================

def get_prediction_top(limit=5):

    latest_prediction_date = (
        get_latest_prediction_date()
    )

    if latest_prediction_date is None:
        return pd.DataFrame()

    rows = fetch_all(
        """
        SELECT

            台番号,
            機種,
            島,

            ROUND(
                総合スコア,
                1
            ) AS 総合スコア,

            判定

        FROM prediction_score

        WHERE 日付 = ?

        ORDER BY
            総合スコア DESC

        LIMIT ?

        """,
        [
            latest_prediction_date,
            limit,
        ],
    )

    return pd.DataFrame(
        [dict(row) for row in rows]
    )


# ==================================
# 全台系候補
# ==================================

def get_all_setting_candidates(limit=10):

    latest_prediction_date = (
        get_latest_prediction_date()
    )

    if latest_prediction_date is None:
        return pd.DataFrame()

    rows = fetch_all(
        """
        SELECT

            日付,
            島,
            対象台数,
            △以上率,
            全台系スコア,
            判定,
            全台系差分台数

        FROM island_all_setting_analysis

        WHERE 日付 = ?

        ORDER BY
            全台系スコア DESC

        LIMIT ?

        """,
        [
            latest_prediction_date,
            limit,
        ],
    )

    return pd.DataFrame(
        [dict(row) for row in rows]
    )


# ==================================
# 台番号履歴
# ==================================

def get_machine_history(machine_number):

    rows = fetch_all(
        """
        SELECT

            日付,
            機種,
            台番号,
            BB,
            RB,
            G数,
            合成確率,
            評価,
            島

        FROM daily_data

        WHERE 台番号 = ?

        ORDER BY
            日付 DESC

        """,
        [
            machine_number,
        ],
    )

    return pd.DataFrame(
        [dict(row) for row in rows]
    )


# ==================================
# 台番号の過去統計
# ==================================

def get_machine_statistics(machine_number):

    rows = fetch_all(
        """
        SELECT

            COUNT(*) AS 総営業日数,

            SUM(
                CASE
                    WHEN G数 >= 500
                    THEN 1
                    ELSE 0
                END
            ) AS 判定可能日数,

            SUM(
                CASE
                    WHEN G数 >= 500
                    AND 評価 IN ('◎', '○')
                    THEN 1
                    ELSE 0
                END
            ) AS 高設定回数,

            SUM(
                CASE
                    WHEN G数 >= 500
                    AND 評価 = '◎'
                    THEN 1
                    ELSE 0
                END
            ) AS ◎回数,

            SUM(
                CASE
                    WHEN G数 >= 500
                    AND 評価 = '○'
                    THEN 1
                    ELSE 0
                END
            ) AS ○回数,

            SUM(
                CASE
                    WHEN G数 >= 500
                    AND 評価 = '△'
                    THEN 1
                    ELSE 0
                END
            ) AS △回数,

            ROUND(
                AVG(
                    CASE
                        WHEN G数 >= 500
                        THEN 合成確率
                    END
                ),
                1
            ) AS 平均合成,

            ROUND(
                AVG(
                    CASE
                        WHEN G数 >= 500
                        THEN G数
                    END
                ),
                0
            ) AS 平均G数,

            ROUND(
                AVG(
                    CASE
                        WHEN G数 >= 500
                        AND RB > 0
                        THEN CAST(G数 AS REAL) / RB
                    END
                ),
                1
            ) AS 平均RB確率

        FROM daily_data

        WHERE 台番号 = ?

        """,
        [
            machine_number,
        ],
    )

    if not rows:
        return {}

    result = dict(rows[0])

    evaluable = (
        result.get("判定可能日数") or 0
    )

    high_count = (
        result.get("高設定回数") or 0
    )

    excellent_count = (
        result.get("◎回数") or 0
    )

    good_count = (
        result.get("○回数") or 0
    )

    triangle_count = (
        result.get("△回数") or 0
    )

    if evaluable > 0:

        result["高設定率"] = round(
            high_count
            / evaluable
            * 100,
            1,
        )

        result["◎率"] = round(
            excellent_count
            / evaluable
            * 100,
            1,
        )

        result["○率"] = round(
            good_count
            / evaluable
            * 100,
            1,
        )

        result["△率"] = round(
            triangle_count
            / evaluable
            * 100,
            1,
        )

    else:

        result["高設定率"] = 0.0
        result["◎率"] = 0.0
        result["○率"] = 0.0
        result["△率"] = 0.0

    return result


# ==================================
# 最新日の台情報
# ==================================

def get_latest_machine_info():

    latest_date = get_latest_date()

    if latest_date is None:
        return pd.DataFrame()

    rows = fetch_all(
        """
        SELECT

            台番号,
            機種,
            島

        FROM daily_data

        WHERE 日付 = ?

        ORDER BY
            台番号

        """,
        [
            latest_date,
        ],
    )

    return pd.DataFrame(
        [dict(row) for row in rows]
    )


# ==================================
# 台番号指定用
# 最新日の状況取得
# ==================================

def get_latest_machine_status(machine_number):

    latest_date = get_latest_date()

    if latest_date is None:
        return {}

    rows = fetch_all(
        """
        SELECT

            日付,
            台番号,
            機種,
            島,
            BB,
            RB,
            G数,
            合成確率,
            評価

        FROM daily_data

        WHERE 日付 = ?

        AND 台番号 = ?

        LIMIT 1

        """,
        [
            latest_date,
            machine_number,
        ],
    )

    if not rows:
        return {}

    result = dict(rows[0])

    # ==================================
    # BIG確率
    # ==================================

    big = result.get("BB")
    games = result.get("G数")

    if (
        big is not None
        and games is not None
        and big > 0
    ):
        result["BIG確率"] = round(
            games / big,
            1,
        )
    else:
        result["BIG確率"] = None

    # ==================================
    # REG確率
    # ==================================

    reg = result.get("RB")

    if (
        reg is not None
        and games is not None
        and reg > 0
    ):
        result["REG確率"] = round(
            games / reg,
            1,
        )
    else:
        result["REG確率"] = None

    return result


# ==================================
# 台番号の現在順位
#
# 最新営業日の合成確率を基準に、
# 全対象台の中での順位を取得
# ==================================

def get_latest_machine_rank(machine_number):

    latest_date = get_latest_date()

    if latest_date is None:
        return {}

    rows = fetch_all(
        """
        SELECT

            台番号,
            合成確率

        FROM daily_data

        WHERE 日付 = ?

        AND 合成確率 IS NOT NULL

        ORDER BY
            合成確率 ASC

        """,
        [
            latest_date,
        ],
    )

    if not rows:
        return {}

    data = [
        dict(row)
        for row in rows
    ]

    target_rank = None

    for index, row in enumerate(
        data,
        start=1,
    ):

        if row["台番号"] == machine_number:

            target_rank = index
            break

    if target_rank is None:
        return {}

    return {
        "順位": target_rank,
        "対象台数": len(data),
    }


# ==================================
# 台番号詳細情報
# ==================================

def get_machine_detail(machine_number):

    return {
        "status": get_latest_machine_status(
            machine_number
        ),
        "statistics": get_machine_statistics(
            machine_number
        ),
        "rank": get_latest_machine_rank(
            machine_number
        ),
        "history": get_machine_history(
            machine_number
        ),
    }


# ==================================
# 動作確認
# ==================================

if __name__ == "__main__":

    print("=" * 60)

    print("最新営業日")
    print(
        get_latest_date()
    )

    print()

    print("前回営業日")
    print(
        get_previous_date()
    )

    print()

    print("最新予測日")
    print(
        get_latest_prediction_date()
    )

    print()

    print("【前日の概要】")
    print(
        get_latest_summary()
    )

    print()

    print("【前日の島別状況】")
    print(
        get_latest_island_summary()
    )

    print()

    print("【前日の高評価台】")
    print(
        get_latest_good_machines()
    )

    print()

    print("【予測ランキング】")
    print(
        get_prediction_top()
    )

    print()

    print("【全台系候補】")
    print(
        get_all_setting_candidates()
    )

    print()

    print("【969番台履歴】")
    print(
        get_machine_history(969)
    )

    print()

    print("【969番台統計】")
    print(
        get_machine_statistics(969)
    )

    print()

    print("【969番台最新状況】")
    print(
        get_latest_machine_status(969)
    )

    print()

    print("【969番台順位】")
    print(
        get_latest_machine_rank(969)
    )

    print()

    print("【969番台詳細】")
    print(
        get_machine_detail(969)
    )