"""
ジャグラーラボ
Prediction Engine

補正ルール管理
"""


def get_holdover_score(row):
    """
    据置期待補正
    """

    rate = row["据え置き率"]
    count = row["前日高評価回数"]

    if count < 5:
        return 0

    if rate >= 40:
        return 10

    if rate >= 30:
        return 7

    if rate >= 20:
        return 4

    return 0


def get_reset_score(row):
    """
    リセット傾向補正
    """

    before = row["前日高評価回数"]
    after = row["翌日高評価回数"]

    if before < 5:
        return 0

    rate = after / before * 100

    if rate <= 5:
        return -5

    if rate <= 10:
        return -3

    return 0


def get_event_score(event):
    """
    イベント補正
    """

    scores = {
        "🔥9イベント": 5,
        "🔥5Fフロア紹介": 3,
        "🎰ゾロ目": 3,
        "📈0イベント": 2,
        "✨特殊": 6,
        "📅通常": 0,
    }

    return scores.get(event, 0)


def get_weekday_score(row):
    """
    曜日補正
    """

    rate = row.get(
        "高評価率",
        0
    )

    if rate >= 15:
        return 5

    if rate >= 10:
        return 3

    if rate >= 7:
        return 1

    return 0


def get_store_score(row):
    """
    店舗状態補正
    """

    score = row.get(
        "店舗スコア",
        0
    )

    if score >= 20:
        return 5

    if score >= 10:
        return 3

    return 0


def get_tail_score(rate):
    """
    台番号末尾補正
    """

    if rate >= 12:
        return 4

    if rate >= 10:
        return 2

    if rate >= 8:
        return 1

    return 0


def get_alignment_expect_score(row):
    """
    並び期待補正

    過去の並び発生傾向から
    今後入りやすい場所を評価する。

    row:
        発生回数
        強い並び回数
        並び期待度
    """

    count = row.get(
        "発生回数",
        0
    )

    strong = row.get(
        "強い並び回数",
        0
    )

    expectation = row.get(
        "並び期待度",
        0
    )

    if count < 2:
        return 0

    score = 0

    if count >= 5:
        score += 10

    elif count >= 3:
        score += 5

    if strong >= 3:
        score += 10

    elif strong >= 1:
        score += 5

    if expectation >= 1.5:
        score += 10

    elif expectation >= 1.0:
        score += 5

    return score

def get_all_setting_score(row):
    """
    全台系期待補正

    island_all_setting_analysis の過去実績から、
    島が今後全台系候補になる期待度を補正する。

    最大10点程度の補助スコアとして扱う。
    """

    strong_rate = row.get(
        "強い全台系率",
        0
    )

    candidate_rate = row.get(
        "全台系候補率",
        0
    )

    recent_rate = row.get(
        "直近全台系率",
        0
    )

    avg_strength = row.get(
        "平均結果強度",
        0
    )

    days_since = row.get(
        "最終全台系からの日数",
        None
    )

    try:
        strong_rate = float(strong_rate or 0)
    except (ValueError, TypeError):
        strong_rate = 0.0

    try:
        candidate_rate = float(candidate_rate or 0)
    except (ValueError, TypeError):
        candidate_rate = 0.0

    try:
        recent_rate = float(recent_rate or 0)
    except (ValueError, TypeError):
        recent_rate = 0.0

    try:
        avg_strength = float(avg_strength or 0)
    except (ValueError, TypeError):
        avg_strength = 0.0

    try:
        if days_since is None:
            days_since = None
        else:
            days_since = float(days_since)
    except (ValueError, TypeError):
        days_since = None

    score = 0.0

    # 長期の強い全台系実績
    if strong_rate >= 20:
        score += 3.0
    elif strong_rate >= 10:
        score += 2.0
    elif strong_rate >= 5:
        score += 1.0

    # 全台系候補全体の実績
    if candidate_rate >= 30:
        score += 2.0
    elif candidate_rate >= 15:
        score += 1.5
    elif candidate_rate >= 5:
        score += 0.5

    # 直近実績
    if recent_rate >= 20:
        score += 2.0
    elif recent_rate >= 10:
        score += 1.0
    elif recent_rate >= 5:
        score += 0.5

    # 結果強度
    if avg_strength >= 100:
        score += 2.0
    elif avg_strength >= 80:
        score += 1.0
    elif avg_strength >= 60:
        score += 0.5

    # 直近すぎる連続発生を少し抑える
    if days_since is not None:
        if days_since <= 0:
            score -= 2.0
        elif days_since == 1:
            score -= 1.5
        elif days_since == 2:
            score -= 0.5

    score = max(0.0, score)
    score = min(10.0, score)

    return round(score, 2)