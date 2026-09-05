"""
ジャグラーラボ
Prediction Engine

並び期待補正ルール

長期的な並び実績と、
直近の並び発生状況を組み合わせて補正する。
"""

import pandas as pd


def get_alignment_score(
    row,
    alignment_history,
    current_date=None
):
    """
    過去の並び傾向＋直近ローテーションから
    並び補正値を返す。

    Parameters
    ----------
    row : pandas.Series
        予測対象台

    alignment_history : pandas.DataFrame
        alignment_history の全履歴

    current_date : str or None
        予測基準日。
        例: "2026-08-09"

    Returns
    -------
    int
        並び補正値
    """

    no = int(row["台番号"])
    island = str(row["島"])

    # ========================================================
    # 基本
    # ========================================================

    if alignment_history is None:
        return 0

    if alignment_history.empty:
        return 0

    # ========================================================
    # 必要列確認
    # ========================================================

    required_columns = {
        "島",
        "開始台番号",
        "終了台番号",
        "発生回数",
    }

    # alignment_history_analysis を渡した場合
    # 日付がないため、長期実績だけで評価する。
    if required_columns.issubset(
        set(alignment_history.columns)
    ):

        target = alignment_history[
            alignment_history["島"] == island
        ].copy()

    else:
        return 0

    if target.empty:
        return 0

    # ========================================================
    # 数値型
    # ========================================================

    for column in [
        "開始台番号",
        "終了台番号",
        "発生回数",
    ]:

        target[column] = pd.to_numeric(
            target[column],
            errors="coerce"
        )

    target = target.dropna(
        subset=[
            "開始台番号",
            "終了台番号",
            "発生回数",
        ]
    )

    if target.empty:
        return 0

    # ========================================================
    # この台を含む過去の並び
    # ========================================================

    near = target[
        (target["開始台番号"] <= no)
        &
        (target["終了台番号"] >= no)
    ]

    if near.empty:
        return 0

    # ========================================================
    # 長期実績評価
    #
    # 過去に何度も使われている場所ほど
    # 少しだけプラス。
    #
    # ここでは「固定化」を防ぐため、
    # 最大でも +4 に抑える。
    # ========================================================

    max_count = int(
        near["発生回数"].max()
    )

    history_score = 0

    if max_count >= 12:

        history_score = 4

    elif max_count >= 9:

        history_score = 3

    elif max_count >= 6:

        history_score = 2

    elif max_count >= 3:

        history_score = 1

    # ========================================================
    # 島全体の並び傾向
    #
    # 島そのものに並びが多い場合は
    # わずかにプラス。
    #
    # これも最大 +2。
    # ========================================================

    island_count = int(
        target["発生回数"].sum()
    )

    island_score = 0

    if island_count >= 30:

        island_score = 2

    elif island_count >= 15:

        island_score = 1

    # ========================================================
    # ここまでが「長期傾向」
    # ========================================================

    score = (
        history_score
        +
        island_score
    )

    # ========================================================
    # 直近ローテーション補正
    #
    # alignment_history_analysis には日付がないため、
    # current_date が指定され、日付列が存在する場合のみ実施。
    # ========================================================

    if (
        current_date is not None
        and
        "日付" in alignment_history.columns
    ):

        raw = alignment_history.copy()

        raw["開始台番号"] = pd.to_numeric(
            raw["開始台番号"],
            errors="coerce"
        )

        raw["終了台番号"] = pd.to_numeric(
            raw["終了台番号"],
            errors="coerce"
        )

        raw["日付"] = pd.to_datetime(
            raw["日付"],
            errors="coerce"
        )

        raw = raw.dropna(
            subset=[
                "日付",
                "開始台番号",
                "終了台番号",
            ]
        )

        raw = raw[
            raw["島"] == island
        ]

        # この台を含む並びだけ
        raw = raw[
            (raw["開始台番号"] <= no)
            &
            (raw["終了台番号"] >= no)
        ]

        if not raw.empty:

            base_date = pd.to_datetime(
                current_date
            )

            raw["経過日数"] = (
                base_date
                -
                raw["日付"]
            ).dt.days

            # 予測基準日より未来の履歴は除外
            raw = raw[
                raw["経過日数"] >= 0
            ]

            if not raw.empty:

                # 最も最近の並び発生日
                days_since = int(
                    raw["経過日数"].min()
                )

                # ------------------------------------------------
                # ローテーション補正
                # ------------------------------------------------

                if days_since == 0:

                    # 当日すでに並びが入った
                    rotation_score = -5

                elif days_since == 1:

                    rotation_score = -5

                elif days_since <= 3:

                    rotation_score = -3

                elif days_since <= 7:

                    rotation_score = -1

                elif days_since <= 14:

                    rotation_score = 0

                else:

                    # 長期間出ていない場所は
                    # ローテーション候補として少し優遇
                    rotation_score = 1

                score += rotation_score

    # ========================================================
    # スコア上限・下限
    #
    # 並び補正だけで総合順位が決まりすぎないようにする。
    # ========================================================

    score = max(
        -5,
        min(6, score)
    )

    return int(score)