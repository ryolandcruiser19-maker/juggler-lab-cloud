"""
ジャグラーラボ
リアルタイム分析エンジン

営業中のデータから、

・現在の高設定候補
・移動おすすめ台
・3台並び候補
・RB狙い候補
・全台系候補
・全台系島内の救済候補

を算出する。

※ リアルタイム分析は営業途中の暫定分析。
※ 設定を確定するものではない。
"""

from pathlib import Path
import sqlite3

import pandas as pd


# ==================================================
# プロジェクト設定
# ==================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "database" / "juggler.db"


# ==================================================
# DB接続
# ==================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


# ==================================================
# 数値変換
# ==================================================

def to_number(value):
    """
    数値文字列をfloatへ変換する。
    """

    if pd.isna(value):
        return None

    try:
        text = str(value)

        text = (
            text
            .replace(",", "")
            .replace("1/", "")
            .strip()
        )

        return float(text)

    except Exception:
        return None


# ==================================================
# 島情報取得
# ==================================================

def get_machine_master():
    """
    machinesテーブルから台番号・機種・島情報を取得する。
    """

    try:
        conn = get_connection()

        query = """
        SELECT
            machine,
            number,
            island
        FROM machines
        """

        df = pd.read_sql_query(
            query,
            conn
        )

        conn.close()

        return df

    except Exception:
        return pd.DataFrame()


# ==================================================
# リアルタイムデータ整形
# ==================================================

def prepare_realtime_data(df):

    result = df.copy()

    # ------------------------------------------
    # G数
    # ------------------------------------------

    if "累計ゲーム" in result.columns:

        result["G数"] = (
            result["累計ゲーム"]
            .apply(to_number)
        )

    elif "G数" not in result.columns:

        result["G数"] = None

    # ------------------------------------------
    # 合成確率
    # ------------------------------------------

    if "合成確率" in result.columns:

        result["合成"] = (
            result["合成確率"]
            .apply(to_number)
        )

    elif "合成" not in result.columns:

        result["合成"] = None

    # ------------------------------------------
    # BIG
    # ------------------------------------------

    if "BIG" in result.columns:

        result["BIG数"] = (
            result["BIG"]
            .apply(to_number)
        )

    elif "BB" in result.columns:

        result["BIG数"] = (
            result["BB"]
            .apply(to_number)
        )

    else:

        result["BIG数"] = None

    # ------------------------------------------
    # REG
    # ------------------------------------------

    if "REG" in result.columns:

        result["REG数"] = (
            result["REG"]
            .apply(to_number)
        )

    elif "RB" in result.columns:

        result["REG数"] = (
            result["RB"]
            .apply(to_number)
        )

    else:

        result["REG数"] = None

    # ------------------------------------------
    # 台番号
    # ------------------------------------------

    if "台番号" in result.columns:

        result["台番号数値"] = (
            result["台番号"]
            .astype(str)
            .str.extract(r"(\d+)")[0]
            .apply(to_number)
        )

    else:

        result["台番号数値"] = None

    # ------------------------------------------
    # 島情報をマスタから付与
    # ------------------------------------------

    master_df = get_machine_master()

    if not master_df.empty:

        master_df["number"] = (
            master_df["number"]
            .apply(to_number)
        )

        result = result.merge(
            master_df,
            left_on=[
                "台番号数値"
            ],
            right_on=[
                "number"
            ],
            how="left",
            suffixes=(
                "",
                "_master"
            )
        )

        # --------------------------------------
        # 島
        # --------------------------------------

        if "島" not in result.columns:

            result["島"] = (
                result["island"]
            )

        else:

            result["島"] = (
                result["島"]
                .fillna(
                    result["island"]
                )
            )

        # --------------------------------------
        # 機種
        # --------------------------------------

        if "機種" not in result.columns:

            result["機種"] = (
                result["machine"]
            )

        else:

            result["機種"] = (
                result["機種"]
                .fillna(
                    result["machine"]
                )

        )

    else:

        if "島" not in result.columns:

            result["島"] = "不明"

    # ------------------------------------------
    # 島の欠損を補完
    # ------------------------------------------

    result["島"] = (
        result["島"]
        .fillna("不明")
    )

    return result


# ==================================================
# 現在評価
# ==================================================

def calculate_current_evaluation(row):

    probability = row.get(
        "合成"
    )

    games = row.get(
        "G数"
    )

    if pd.isna(probability):

        return "－"

    if pd.notna(games):

        if games < 100:

            return "－"

    if probability <= 119:

        return "◎"

    if probability <= 129:

        return "○"

    if probability <= 149:

        return "△"

    return "－"


# ==================================================
# REG確率
# ==================================================

def calculate_reg_probability(row):

    games = row.get(
        "G数"
    )

    reg = row.get(
        "REG数"
    )

    if (
        pd.isna(games)
        or pd.isna(reg)
        or games <= 0
        or reg <= 0
    ):

        return None

    return games / reg


# ==================================================
# REG評価
# ==================================================

def calculate_reg_score(row):

    reg_probability = (
        calculate_reg_probability(
            row
        )
    )

    if reg_probability is None:

        return 0.0

    if reg_probability <= 120:

        return 30.0

    if reg_probability <= 140:

        return 25.0

    if reg_probability <= 160:

        return 20.0

    if reg_probability <= 180:

        return 12.0

    if reg_probability <= 210:

        return 5.0

    return 0.0


# ==================================================
# 台単体スコア
# ==================================================

def calculate_machine_score(row):

    score = 0.0

    probability = row.get(
        "合成"
    )

    games = row.get(
        "G数"
    )

    # ------------------------------------------
    # 合成
    # ------------------------------------------

    if pd.notna(probability):

        if probability <= 119:

            score += 60

        elif probability <= 129:

            score += 50

        elif probability <= 139:

            score += 38

        elif probability <= 149:

            score += 25

        elif probability <= 159:

            score += 12

    # ------------------------------------------
    # REG
    # ------------------------------------------

    score += calculate_reg_score(
        row
    )

    # ------------------------------------------
    # 稼働量
    # ------------------------------------------

    if pd.notna(games):

        if games >= 3000:

            score += 15

        elif games >= 2000:

            score += 12

        elif games >= 1000:

            score += 8

        elif games >= 500:

            score += 4

    return round(
        score,
        1
    )


# ==================================================
# 並び履歴取得
# ==================================================

def get_alignment_history():

    try:

        conn = get_connection()

        query = """
        SELECT
            島,
            開始台番号,
            終了台番号,
            発生回数,
            平均台数,
            平均並びスコア,
            強い並び回数,
            並び期待度
        FROM alignment_history_analysis
        """

        df = pd.read_sql_query(
            query,
            conn
        )

        conn.close()

        return df

    except Exception:

        return pd.DataFrame()


# ==================================================
# 直近並び履歴
# ==================================================

def get_recent_alignment():

    try:

        conn = get_connection()

        query = """
        SELECT
            日付,
            島,
            開始台番号,
            終了台番号,
            台数,
            ◎台数,
            ○台数,
            平均G数,
            平均合成確率,
            並びスコア,
            判定
        FROM alignment_history
        ORDER BY 日付 DESC
        """

        df = pd.read_sql_query(
            query,
            conn
        )

        conn.close()

        return df

    except Exception:

        return pd.DataFrame()


# ==================================================
# 過去実績のある機種取得
# ==================================================

def get_alignment_machine_history():

    """
    過去に並び実績が確認されている機種を取得する。

    現在のところ、
    alignment_history_analysis に存在する島から
    machinesテーブルを経由して機種を特定する。
    """

    try:

        conn = get_connection()

        query = """
        SELECT DISTINCT
            m.machine
        FROM alignment_history_analysis a
        INNER JOIN machines m
            ON m.island = a.島
        """

        df = pd.read_sql_query(
            query,
            conn
        )

        conn.close()

        if df.empty:

            return set()

        return set(
            df["machine"]
            .dropna()
            .astype(str)
        )

    except Exception:

        return set()


# ==================================================
# 直近使用による減点
# ==================================================

def calculate_recent_penalty(
    island,
    start_number,
    end_number,
    recent_df
):

    if recent_df.empty:

        return 0.0

    target = recent_df[
        (
            recent_df["島"]
            == island
        )
        &
        (
            recent_df["開始台番号"]
            == start_number
        )
        &
        (
            recent_df["終了台番号"]
            == end_number
        )
    ]

    if target.empty:

        return 0.0

    latest = target.iloc[0]

    try:

        recent_date = pd.to_datetime(
            latest["日付"]
        )

        today = pd.Timestamp.today()

        days = (
            today.normalize()
            - recent_date.normalize()
        ).days

    except Exception:

        return 0.0

    if days <= 1:

        return 30.0

    if days <= 2:

        return 20.0

    if days <= 3:

        return 12.0

    if days <= 5:

        return 6.0

    return 0.0


# ==================================================
# 3台並び候補
# ==================================================

def calculate_alignment_candidates(df):

    if df.empty:

        return pd.DataFrame()

    history_df = (
        get_alignment_history()
    )

    recent_df = (
        get_recent_alignment()
    )

    historical_machines = (
        get_alignment_machine_history()
    )

    candidates = []

    df = df.sort_values(
        [
            "島",
            "台番号数値"
        ]
    )

    for island, island_df in df.groupby(
        "島",
        sort=False
    ):

        island_df = (
            island_df
            .reset_index(drop=True)
        )

        for i in range(
            1,
            len(island_df) - 1
        ):

            left = island_df.iloc[i - 1]
            center = island_df.iloc[i]
            right = island_df.iloc[i + 1]

            left_number = int(
                left["台番号数値"]
            )

            center_number = int(
                center["台番号数値"]
            )

            right_number = int(
                right["台番号数値"]
            )

            # ----------------------------------
            # 連番チェック
            # ----------------------------------

            if (
                center_number
                - left_number
                != 1
            ):

                continue

            if (
                right_number
                - center_number
                != 1
            ):

                continue

            # ----------------------------------
            # 機種実績チェック
            # ----------------------------------

            machine_name = str(
                center["機種"]
            )

            has_history = (
                machine_name
                in historical_machines
            )

            # 過去に並び実績がない機種は
            # 原則として移動おすすめに出さない
            if not has_history:

                continue

            # ----------------------------------
            # 左右スコア
            # ----------------------------------

            left_score = float(
                left["台単体スコア"]
            )

            right_score = float(
                right["台単体スコア"]
            )

            center_score = float(
                center["台単体スコア"]
            )

            surrounding_score = (
                left_score
                + right_score
            )

            # 左右どちらも一定以上必要
            if (
                left_score < 25
                or right_score < 25
            ):

                continue

            # ----------------------------------
            # 並びスコア
            # ----------------------------------

            score = 0.0

            score += min(
                surrounding_score * 0.6,
                45
            )

            # ----------------------------------
            # 中央台
            # ----------------------------------

            center_games = (
                center["G数"]
            )

            if (
                pd.isna(center_games)
                or center_games < 100
            ):

                score += 15

                center_reason = (
                    "中央台が未稼働"
                )

            elif center_score < 25:

                score += 8

                center_reason = (
                    "中央台が弱く移動候補"
                )

            else:

                center_reason = (
                    "3台とも比較的強い"
                )

            # ----------------------------------
            # 過去実績
            # ----------------------------------

            historical_expectation = 0.0

            if not history_df.empty:

                target = history_df[
                    (
                        history_df["島"]
                        == island
                    )
                    &
                    (
                        history_df["開始台番号"]
                        == left_number
                    )
                    &
                    (
                        history_df["終了台番号"]
                        == right_number
                    )
                ]

                if not target.empty:

                    historical_expectation = float(
                        target.iloc[0][
                            "並び期待度"
                        ]
                    )

                    score += min(
                        historical_expectation * 0.15,
                        15
                    )

            # ----------------------------------
            # 直近使用減点
            # ----------------------------------

            recent_penalty = (
                calculate_recent_penalty(
                    island,
                    left_number,
                    right_number,
                    recent_df
                )
            )

            score -= recent_penalty

            # ----------------------------------
            # 上限
            # ----------------------------------

            score = max(
                0,
                min(
                    score,
                    85
                )
            )

            # ----------------------------------
            # 信頼度
            # ----------------------------------

            confidence = round(
                score,
                1
            )

            if confidence >= 70:

                recommendation = "強くおすすめ"

            elif confidence >= 55:

                recommendation = "おすすめ"

            elif confidence >= 40:

                recommendation = "候補"

            else:

                recommendation = "参考"

            reason = (
                f"{machine_name}で過去の並び実績あり・"
                f"左右の台が強い・{center_reason}"
            )

            if recent_penalty > 0:

                reason += (
                    "・直近使用のため減点"
                )

            candidates.append({

                "台番号": center_number,

                "機種": machine_name,

                "島": island,

                "G数": center["G数"],

                "合成": center["合成"],

                "左右スコア": round(
                    surrounding_score,
                    1
                ),

                "並び期待度": round(
                    historical_expectation,
                    1
                ),

                "直近減点": round(
                    recent_penalty,
                    1
                ),

                "信頼度": confidence,

                "おすすめ度": recommendation,

                "候補種別": "3台並び候補",

                "理由": reason

            })

    if not candidates:

        return pd.DataFrame()

    result = pd.DataFrame(
        candidates
    )

    return result.sort_values(
        "信頼度",
        ascending=False
    ).reset_index(
        drop=True
    )


# ==================================================
# RB狙い候補
# ==================================================

def calculate_reg_candidates(df):

    if df.empty:

        return pd.DataFrame()

    candidates = []

    for _, row in df.iterrows():

        games = row["G数"]

        reg_probability = (
            calculate_reg_probability(
                row
            )
        )

        if pd.isna(games):

            continue

        # 少なすぎるデータは除外
        if games < 1000:

            continue

        if reg_probability is None:

            continue

        # REG 1/160以下を候補
        if reg_probability > 160:

            continue

        score = 0.0

        if reg_probability <= 120:

            score = 85

        elif reg_probability <= 130:

            score = 75

        elif reg_probability <= 140:

            score = 65

        elif reg_probability <= 150:

            score = 55

        else:

            score = 45

        # G数による信頼度補正
        if games >= 3000:

            score += 10

        elif games >= 2000:

            score += 5

        score = min(
            score,
            95
        )

        # 合成が悪いほど
        # 「移動候補」として価値がある
        probability = row["合成"]

        if (
            pd.notna(probability)
            and probability > 149
        ):

            reason = (
                "合成は弱いがREG確率が良好"
            )

        else:

            reason = (
                "REG確率が良好"
            )

        candidates.append({

            "台番号": int(
                row["台番号数値"]
            ),

            "機種": row["機種"],

            "島": row["島"],

            "G数": games,

            "合成": probability,

            "REG確率": round(
                reg_probability,
                1
            ),

            "信頼度": round(
                score,
                1
            ),

            "おすすめ度": (
                "おすすめ"
                if score >= 70
                else "候補"
            ),

            "候補種別": "RB狙い",

            "理由": reason

        })

    if not candidates:

        return pd.DataFrame()

    result = pd.DataFrame(
        candidates
    )

    return result.sort_values(
        "信頼度",
        ascending=False
    ).reset_index(
        drop=True
    )


# ==================================================
# 全台系候補
# ==================================================

def calculate_all_setting_candidates(df):

    if df.empty:

        return pd.DataFrame()

    candidates = []

    for island, island_df in df.groupby(
        "島",
        sort=False
    ):

        if island == "不明":

            continue

        total = len(
            island_df
        )

        if total == 0:

            continue

        active = island_df[
            island_df["G数"]
            .fillna(0)
            >= 300
        ]

        if active.empty:

            continue

        excellent = len(
            active[
                active["現在評価"]
                == "◎"
            ]
        )

        good = len(
            active[
                active["現在評価"]
                == "○"
            ]
        )

        triangle = len(
            active[
                active["現在評価"]
                == "△"
            ]
        )

        strong = (
            excellent
            + good
        )

        evaluable = len(
            active
        )

        strong_rate = (
            strong
            / evaluable
            * 100
        )

        triangle_rate = (
            (
                strong
                + triangle
            )
            / evaluable
            * 100
        )

        average_score = (
            active[
                "台単体スコア"
            ].mean()
        )

        # ----------------------------------
        # 全台系スコア
        # ----------------------------------

        score = 0.0

        score += min(
            strong_rate * 0.60,
            60
        )

        score += min(
            triangle_rate * 0.20,
            20
        )

        score += min(
            average_score * 0.15,
            15
        )

        if evaluable >= total * 0.8:

            score += 5

        score = max(
            0,
            min(
                score,
                100
            )
        )

        if score >= 75:

            judgment = "高"

        elif score >= 60:

            judgment = "中"

        elif score >= 45:

            judgment = "低"

        else:

            judgment = "参考"

        candidates.append({

            "島": island,

            "対象台数": total,

            "判定可能台数": evaluable,

            "◎台数": excellent,

            "○台数": good,

            "△台数": triangle,

            "◎○以上率": round(
                strong_rate,
                1
            ),

            "△以上率": round(
                triangle_rate,
                1
            ),

            "平均台スコア": round(
                average_score,
                1
            ),

            "全台系スコア": round(
                score,
                1
            ),

            "判定": judgment

        })

    if not candidates:

        return pd.DataFrame()

    result = pd.DataFrame(
        candidates
    )

    return result.sort_values(
        "全台系スコア",
        ascending=False
    ).reset_index(
        drop=True
    )


# ==================================================
# 全台系島内の移動候補
# ==================================================

def calculate_all_setting_move_candidates(
    df,
    all_setting_df
):

    if (
        df.empty
        or all_setting_df.empty
    ):

        return pd.DataFrame()

    candidates = []

    # 全台系スコア60以上の島のみ
    target_islands = (
        all_setting_df[
            all_setting_df["全台系スコア"]
            >= 60
        ]
    )

    for _, island_info in (
        target_islands.iterrows()
    ):

        island = island_info["島"]

        island_df = df[
            df["島"]
            == island
        ]

        for _, row in island_df.iterrows():

            games = row["G数"]

            probability = row["合成"]

            # ----------------------------------
            # 十分なデータがない台は除外
            # ----------------------------------

            if pd.isna(games):

                continue

            if games < 300:

                continue

            # ----------------------------------
            # 既に強い台は移動候補にしない
            # ----------------------------------

            if (
                row["現在評価"]
                == "◎"
            ):

                continue

            # ----------------------------------
            # 合成が悪い台を拾う
            # ----------------------------------

            if pd.isna(probability):

                continue

            if probability <= 149:

                continue

            # ----------------------------------
            # 全台系島の中での救済候補
            # ----------------------------------

            island_score = float(
                island_info[
                    "全台系スコア"
                ]
            )

            score = (
                island_score
                * 0.75
            )

            # REGが良ければ加点
            reg_probability = (
                calculate_reg_probability(
                    row
                )
            )

            if (
                reg_probability is not None
                and reg_probability <= 160
            ):

                score += 15

                reason = (
                    "全台系期待島の中で合成は弱いが、"
                    "REG確率が良好"
                )

            else:

                reason = (
                    "全台系期待島の中で"
                    "現在の合成が弱い"
                )

            score = min(
                score,
                90
            )

            candidates.append({

                "台番号": int(
                    row["台番号数値"]
                ),

                "機種": row["機種"],

                "島": island,

                "G数": games,

                "合成": probability,

                "REG確率": (
                    round(
                        reg_probability,
                        1
                    )
                    if reg_probability
                    is not None
                    else None
                ),

                "全台系スコア": island_score,

                "信頼度": round(
                    score,
                    1
                ),

                "おすすめ度": (
                    "おすすめ"
                    if score >= 70
                    else "候補"
                ),

                "候補種別": (
                    "全台系島内候補"
                ),

                "理由": reason

            })

    if not candidates:

        return pd.DataFrame()

    result = pd.DataFrame(
        candidates
    )

    return result.sort_values(
        "信頼度",
        ascending=False
    ).reset_index(
        drop=True
    )


# ==================================================
# 移動おすすめ統合
# ==================================================

def calculate_move_recommendations(
    df,
    alignment_df,
    reg_df,
    all_setting_move_df
):

    candidates = []

    # ------------------------------------------
    # 3台並び
    # ------------------------------------------

    if not alignment_df.empty:

        for _, row in (
            alignment_df.iterrows()
        ):

            candidates.append({

                "台番号": row["台番号"],

                "機種": row["機種"],

                "島": row["島"],

                "G数": row["G数"],

                "合成": row["合成"],

                "信頼度": row["信頼度"],

                "おすすめ度": row["おすすめ度"],

                "候補種別": "3台並び候補",

                "理由": row["理由"]

            })

    # ------------------------------------------
    # RB狙い
    # ------------------------------------------

    if not reg_df.empty:

        for _, row in (
            reg_df.iterrows()
        ):

            candidates.append({

                "台番号": row["台番号"],

                "機種": row["機種"],

                "島": row["島"],

                "G数": row["G数"],

                "合成": row["合成"],

                "信頼度": row["信頼度"],

                "おすすめ度": row["おすすめ度"],

                "候補種別": "RB狙い",

                "理由": row["理由"]

            })

    # ------------------------------------------
    # 全台系島内
    # ------------------------------------------

    if not all_setting_move_df.empty:

        for _, row in (
            all_setting_move_df.iterrows()
        ):

            candidates.append({

                "台番号": row["台番号"],

                "機種": row["機種"],

                "島": row["島"],

                "G数": row["G数"],

                "合成": row["合成"],

                "信頼度": row["信頼度"],

                "おすすめ度": row["おすすめ度"],

                "候補種別": (
                    "全台系島内候補"
                ),

                "理由": row["理由"]

            })

    if not candidates:

        return pd.DataFrame()

    result = pd.DataFrame(
        candidates
    )

    # 同一台が複数候補に該当した場合
    # 最も強いものを残す
    result = (
        result
        .sort_values(
            "信頼度",
            ascending=False
        )
        .drop_duplicates(
            subset=[
                "台番号"
            ],
            keep="first"
        )
    )

    return result.reset_index(
        drop=True
    )


# ==================================================
# メイン分析
# ==================================================

def analyze_realtime(
    realtime_df
):

    if (
        realtime_df is None
        or realtime_df.empty
    ):

        return {

            "data": pd.DataFrame(),

            "alignment": pd.DataFrame(),

            "reg": pd.DataFrame(),

            "all_setting": pd.DataFrame(),

            "all_setting_move": pd.DataFrame(),

            "move": pd.DataFrame()

        }

    # ------------------------------------------
    # データ整形
    # ------------------------------------------

    df = prepare_realtime_data(
        realtime_df
    )

    # ------------------------------------------
    # 現在評価
    # ------------------------------------------

    df["現在評価"] = (
        df.apply(
            calculate_current_evaluation,
            axis=1
        )
    )

    # ------------------------------------------
    # 台単体スコア
    # ------------------------------------------

    df["台単体スコア"] = (
        df.apply(
            calculate_machine_score,
            axis=1
        )
    )

    # ------------------------------------------
    # 高設定候補
    # ------------------------------------------

    high_setting = df[
        df["現在評価"].isin(
            [
                "◎",
                "○",
                "△"
            ]
        )
    ].copy()

    high_setting = (
        high_setting
        .sort_values(
            "台単体スコア",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )

    # ------------------------------------------
    # 3台並び
    # ------------------------------------------

    alignment = (
        calculate_alignment_candidates(
            df
        )
    )

    # ------------------------------------------
    # RB候補
    # ------------------------------------------

    reg_df = (
        calculate_reg_candidates(
            df
        )
    )

    # ------------------------------------------
    # 全台系
    # ------------------------------------------

    all_setting = (
        calculate_all_setting_candidates(
            df
        )
    )

    # ------------------------------------------
    # 全台系島内候補
    # ------------------------------------------

    all_setting_move = (
        calculate_all_setting_move_candidates(
            df,
            all_setting
        )
    )

    # ------------------------------------------
    # 移動おすすめ統合
    # ------------------------------------------

    move = (
        calculate_move_recommendations(
            df,
            alignment,
            reg_df,
            all_setting_move
        )
    )

    return {

        "data": high_setting,

        "alignment": alignment,

        "reg": reg_df,

        "all_setting": all_setting,

        "all_setting_move": (
            all_setting_move
        ),

        "move": move

    }


# ==================================================
# テスト
# ==================================================

if __name__ == "__main__":

    print(
        "リアルタイム分析エンジン"
    )

    print(
        DB_PATH
    )