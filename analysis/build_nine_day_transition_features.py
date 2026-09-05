from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# 設定
# ============================================================

BASE_DIR = Path(
    r"C:\Users\sphs4\OneDrive\デスクトップ\ジャグラーラボ"
)

OUTPUT_DIR = (
    BASE_DIR
    / "analysis"
    / "backtest_output"
)

ACTUAL_FILE = (
    OUTPUT_DIR
    / "nine_day_rotation_actual.csv"
)

OUTPUT_FEATURE_FILE = (
    OUTPUT_DIR
    / "nine_day_transition_features.csv"
)

OUTPUT_PAIR_FILE = (
    OUTPUT_DIR
    / "nine_day_transition_pairs.csv"
)

OUTPUT_DAILY_FILE = (
    OUTPUT_DIR
    / "nine_day_transition_daily.csv"
)


# ============================================================
# 表示
# ============================================================

def print_header(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


# ============================================================
# 日付 → 遷移タイプ
# ============================================================

def classify_transition_type(
    previous_date,
    current_date
):
    """
    9の日同士の遷移タイプ。

    9  -> 19
    19 -> 29
    29 -> 翌月9
    """

    previous_day = previous_date.day
    current_day = current_date.day

    if (
        previous_day == 9
        and current_day == 19
    ):
        return "9_to_19"

    if (
        previous_day == 19
        and current_day == 29
    ):
        return "19_to_29"

    if (
        previous_day == 29
        and current_day == 9
    ):
        return "29_to_9"

    return None


# ============================================================
# 島名
# ============================================================

def normalize_island_name(value):

    if pd.isna(value):
        return ""

    return str(value).strip()


# ============================================================
# リスト → 文字列
# ============================================================

def island_list_to_text(islands):

    if not islands:
        return ""

    return "|".join(
        sorted(set(islands))
    )


# ============================================================
# 文字列 → リスト
# ============================================================

def parse_island_list(value):

    if pd.isna(value):
        return []

    text = str(value).strip()

    if not text:
        return []

    return [
        item.strip()
        for item in text.split("|")
        if item.strip()
    ]


# ============================================================
# 1. 入力
# ============================================================

print_header(
    "9の日 島遷移特徴量生成"
)

print(
    f"ACTUAL_FILE : {ACTUAL_FILE}"
)

print(
    f"OUTPUT_DIR  : {OUTPUT_DIR}"
)


if not ACTUAL_FILE.exists():

    raise FileNotFoundError(
        f"実績ファイルが見つかりません。\n"
        f"{ACTUAL_FILE}"
    )


df = pd.read_csv(
    ACTUAL_FILE,
    encoding="utf-8-sig"
)


print()
print(
    f"読み込み行数: {len(df):,}"
)

print(
    f"カラム数    : {len(df.columns)}"
)


# ============================================================
# 2. カラム確認
# ============================================================

required_columns = [
    "日付",
    "島",
    "判定",
]

for column in required_columns:

    if column not in df.columns:

        raise ValueError(
            f"必要なカラムがありません: {column}"
        )


# ============================================================
# 3. データ整形
# ============================================================

work = df.copy()

work["analysis_date"] = pd.to_datetime(
    work["日付"],
    errors="coerce"
)

work["island_name"] = (
    work["島"]
    .apply(normalize_island_name)
)

work["judge"] = (
    work["判定"]
    .fillna("対象外")
    .astype(str)
    .str.strip()
)


# 不正データ除外

work = work[
    work["analysis_date"].notna()
    & (
        work["island_name"] != ""
    )
].copy()


# ============================================================
# 4. 9の日だけ
# ============================================================

work = work[
    work["analysis_date"]
    .dt.day
    .isin([9, 19, 29])
].copy()


# ============================================================
# 5. 判定フラグ
# ============================================================

work["is_strong"] = (
    work["judge"]
    == "強い全台系"
)

work["is_candidate"] = (
    work["judge"]
    == "全台系候補"
)

# 候補以上
#
# 強い全台系も候補以上に含める

work["is_candidate_plus"] = (
    work["is_strong"]
    | work["is_candidate"]
)


# ============================================================
# 6. 入力データ確認
# ============================================================

print_header(
    "判定集計"
)

print(
    work["judge"]
    .value_counts()
    .to_string()
)


print()
print(
    f"9の日数: "
    f"{work['analysis_date'].nunique()}"
)

print(
    f"島種類数: "
    f"{work['island_name'].nunique()}"
)


# ============================================================
# 7. 日付 × 島 データ
# ============================================================

daily_island = (
    work[
        [
            "analysis_date",
            "island_name",
            "judge",
            "is_strong",
            "is_candidate",
            "is_candidate_plus",
        ]
    ]
    .drop_duplicates(
        [
            "analysis_date",
            "island_name",
        ]
    )
    .sort_values(
        [
            "analysis_date",
            "island_name",
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# 8. 9の日ごとの島一覧
# ============================================================

daily_records = []

for analysis_date, group in (
    daily_island.groupby(
        "analysis_date"
    )
):

    strong_islands = (
        group.loc[
            group["is_strong"],
            "island_name",
        ]
        .tolist()
    )

    candidate_islands = (
        group.loc[
            group["is_candidate"],
            "island_name",
        ]
        .tolist()
    )

    candidate_plus_islands = (
        group.loc[
            group["is_candidate_plus"],
            "island_name",
        ]
        .tolist()
    )

    daily_records.append(
        {
            "analysis_date":
                analysis_date,

            "day_type":
                f"day_{analysis_date.day}",

            "strong_island_count":
                len(strong_islands),

            "candidate_island_count":
                len(candidate_islands),

            "candidate_plus_island_count":
                len(candidate_plus_islands),

            "strong_islands":
                island_list_to_text(
                    strong_islands
                ),

            "candidate_islands":
                island_list_to_text(
                    candidate_islands
                ),

            "candidate_plus_islands":
                island_list_to_text(
                    candidate_plus_islands
                ),
        }
    )


daily_summary = pd.DataFrame(
    daily_records
)


daily_summary = (
    daily_summary
    .sort_values(
        "analysis_date"
    )
    .reset_index(drop=True)
)


# ============================================================
# 9. 前回9の日との対応
# ============================================================

daily_summary["previous_date"] = (
    daily_summary[
        "analysis_date"
    ].shift(1)
)


daily_summary["previous_strong_islands"] = (
    daily_summary[
        "strong_islands"
    ].shift(1)
)


daily_summary[
    "previous_candidate_plus_islands"
] = (
    daily_summary[
        "candidate_plus_islands"
    ].shift(1)
)


# ============================================================
# 10. 遷移タイプ
# ============================================================

daily_summary["transition_type"] = None


for index, row in (
    daily_summary.iterrows()
):

    previous_date = (
        row["previous_date"]
    )

    current_date = (
        row["analysis_date"]
    )

    if pd.isna(previous_date):
        continue

    transition_type = (
        classify_transition_type(
            previous_date,
            current_date
        )
    )

    daily_summary.at[
        index,
        "transition_type"
    ] = transition_type


# 有効な遷移だけ

daily_summary = daily_summary[
    daily_summary[
        "transition_type"
    ].notna()
].copy()


# ============================================================
# 11. 全島一覧
# ============================================================

all_islands = sorted(
    daily_island[
        "island_name"
    ]
    .unique()
)


print()
print(
    f"全島数: {len(all_islands)}"
)

print(
    "島一覧:"
)

for island in all_islands:
    print(
        f"  - {island}"
    )


# ============================================================
# 12. 遷移ペア母数を作成
# ============================================================
#
# ここが今回の重要部分。
#
# 例えば、
#
# 前回 = ガール島
#
# のとき、
#
# 今回の全島について、
#
# 「強い」
# 「候補以上」
# 「その他」
#
# を記録する。
#
# これにより、
#
# transition_rate =
#   発生回数 / 観測回数
#
# を後から正しく計算できる。
#


pair_records = []


for _, row in (
    daily_summary.iterrows()
):

    previous_date = (
        row["previous_date"]
    )

    current_date = (
        row["analysis_date"]
    )

    transition_type = (
        row["transition_type"]
    )

    previous_strong = set(
        parse_island_list(
            row[
                "previous_strong_islands"
            ]
        )
    )

    previous_candidate_plus = set(
        parse_island_list(
            row[
                "previous_candidate_plus_islands"
            ]
        )
    )

    current_strong = set(
        parse_island_list(
            row[
                "strong_islands"
            ]
        )
    )

    current_candidate_plus = set(
        parse_island_list(
            row[
                "candidate_plus_islands"
            ]
        )
    )


    # ----------------------------------------
    # 前回の全島を起点にする
    # ----------------------------------------

    for from_island in all_islands:

        from_was_strong = (
            from_island
            in previous_strong
        )

        from_was_candidate_plus = (
            from_island
            in previous_candidate_plus
        )


        # ------------------------------------
        # 今回の全島を到達先にする
        # ------------------------------------

        for to_island in all_islands:

            to_is_strong = (
                to_island
                in current_strong
            )

            to_is_candidate_plus = (
                to_island
                in current_candidate_plus
            )


            pair_records.append(
                {
                    "previous_date":
                        previous_date,

                    "current_date":
                        current_date,

                    "transition_type":
                        transition_type,

                    "from_island":
                        from_island,

                    "to_island":
                        to_island,

                    "from_was_strong":
                        int(from_was_strong),

                    "from_was_candidate_plus":
                        int(
                            from_was_candidate_plus
                        ),

                    "to_is_strong":
                        int(to_is_strong),

                    "to_is_candidate_plus":
                        int(
                            to_is_candidate_plus
                        ),
                }
            )


pair_df = pd.DataFrame(
    pair_records
)


# ============================================================
# 13. 島遷移特徴量
# ============================================================

feature_records = []


if not pair_df.empty:

    group_columns = [
        "transition_type",
        "from_island",
        "to_island",
    ]


    grouped = (
        pair_df
        .groupby(
            group_columns,
            as_index=False
        )
    )


    for (
        transition_type,
        from_island,
        to_island
    ), group in grouped:

        sample_count = len(group)


        strong_count = int(
            group[
                "to_is_strong"
            ].sum()
        )


        candidate_plus_count = int(
            group[
                "to_is_candidate_plus"
            ].sum()
        )


        # ------------------------------------
        # 前回が強い島だったケース
        # ------------------------------------

        strong_from_group = group[
            group[
                "from_was_strong"
            ] == 1
        ]


        strong_from_sample_count = (
            len(strong_from_group)
        )


        strong_from_to_strong_count = int(
            strong_from_group[
                "to_is_strong"
            ].sum()
        )


        strong_from_to_candidate_plus_count = int(
            strong_from_group[
                "to_is_candidate_plus"
            ].sum()
        )


        # ------------------------------------
        # 前回が候補以上だったケース
        # ------------------------------------

        candidate_from_group = group[
            group[
                "from_was_candidate_plus"
            ] == 1
        ]


        candidate_from_sample_count = (
            len(candidate_from_group)
        )


        candidate_from_to_strong_count = int(
            candidate_from_group[
                "to_is_strong"
            ].sum()
        )


        candidate_from_to_candidate_plus_count = int(
            candidate_from_group[
                "to_is_candidate_plus"
            ].sum()
        )


        # ------------------------------------
        # raw rate
        # ------------------------------------

        strong_rate_raw = (
            strong_count
            / sample_count
            if sample_count > 0
            else 0.0
        )


        candidate_plus_rate_raw = (
            candidate_plus_count
            / sample_count
            if sample_count > 0
            else 0.0
        )


        strong_from_to_strong_rate = (
            strong_from_to_strong_count
            / strong_from_sample_count
            if strong_from_sample_count > 0
            else np.nan
        )


        strong_from_to_candidate_plus_rate = (
            strong_from_to_candidate_plus_count
            / strong_from_sample_count
            if strong_from_sample_count > 0
            else np.nan
        )


        candidate_from_to_strong_rate = (
            candidate_from_to_strong_count
            / candidate_from_sample_count
            if candidate_from_sample_count > 0
            else np.nan
        )


        candidate_from_to_candidate_plus_rate = (
            candidate_from_to_candidate_plus_count
            / candidate_from_sample_count
            if candidate_from_sample_count > 0
            else np.nan
        )


        feature_records.append(
            {
                "transition_type":
                    transition_type,

                "from_island":
                    from_island,

                "to_island":
                    to_island,

                "sample_count":
                    sample_count,

                "strong_count":
                    strong_count,

                "candidate_plus_count":
                    candidate_plus_count,

                "strong_rate_raw":
                    strong_rate_raw,

                "candidate_plus_rate_raw":
                    candidate_plus_rate_raw,

                "strong_from_sample_count":
                    strong_from_sample_count,

                "strong_from_to_strong_count":
                    strong_from_to_strong_count,

                "strong_from_to_strong_rate":
                    strong_from_to_strong_rate,

                "strong_from_to_candidate_plus_count":
                    strong_from_to_candidate_plus_count,

                "strong_from_to_candidate_plus_rate":
                    strong_from_to_candidate_plus_rate,

                "candidate_from_sample_count":
                    candidate_from_sample_count,

                "candidate_from_to_strong_count":
                    candidate_from_to_strong_count,

                "candidate_from_to_strong_rate":
                    candidate_from_to_strong_rate,

                "candidate_from_to_candidate_plus_count":
                    candidate_from_to_candidate_plus_count,

                "candidate_from_to_candidate_plus_rate":
                    candidate_from_to_candidate_plus_rate,
            }
        )


feature_df = pd.DataFrame(
    feature_records
)


# ============================================================
# 14. 出力
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


daily_summary.to_csv(
    OUTPUT_DAILY_FILE,
    index=False,
    encoding="utf-8-sig"
)


pair_df.to_csv(
    OUTPUT_PAIR_FILE,
    index=False,
    encoding="utf-8-sig"
)


feature_df.to_csv(
    OUTPUT_FEATURE_FILE,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 15. 結果表示
# ============================================================

print_header(
    "生成結果"
)

print(
    f"日別特徴量 : "
    f"{OUTPUT_DAILY_FILE}"
)

print(
    f"遷移明細   : "
    f"{OUTPUT_PAIR_FILE}"
)

print(
    f"遷移集計   : "
    f"{OUTPUT_FEATURE_FILE}"
)


print()
print(
    f"9の日実績日数       : "
    f"{daily_island['analysis_date'].nunique()}"
)

print(
    f"遷移比較数          : "
    f"{len(daily_summary):,}"
)

print(
    f"島種類数            : "
    f"{len(all_islands):,}"
)

print(
    f"遷移明細行数        : "
    f"{len(pair_df):,}"
)

print(
    f"遷移特徴量行数      : "
    f"{len(feature_df):,}"
)


# ============================================================
# 16. 遷移タイプ別
# ============================================================

print_header(
    "遷移タイプ別比較数"
)


transition_order = [
    "9_to_19",
    "19_to_29",
    "29_to_9",
]


transition_counts = (
    daily_summary[
        "transition_type"
    ]
    .value_counts()
    .reindex(
        transition_order,
        fill_value=0
    )
)


for transition_type in transition_order:

    print(
        f"{transition_type:12s}: "
        f"{transition_counts[transition_type]:3d} 比較"
    )


# ============================================================
# 17. 実績島一覧
# ============================================================

print_header(
    "9の日別 実績島"
)


for _, row in (
    daily_summary.iterrows()
):

    print()
    print(
        f"{row['analysis_date'].date()} "
        f"[{row['transition_type']}]"
    )

    print(
        f"  強い全台系       : "
        f"{row['strong_islands']}"
    )

    print(
        f"  候補以上         : "
        f"{row['candidate_plus_islands']}"
    )


# ============================================================
# 18. 遷移特徴量 TOP
# ============================================================

print_header(
    "遷移特徴量 TOP 50"
)


if not feature_df.empty:

    top_df = (
        feature_df[
            [
                "transition_type",
                "from_island",
                "to_island",
                "sample_count",
                "strong_count",
                "candidate_plus_count",
                "strong_rate_raw",
                "candidate_plus_rate_raw",
            ]
        ]
        .sort_values(
            [
                "transition_type",
                "candidate_plus_rate_raw",
                "strong_rate_raw",
            ],
            ascending=[
                True,
                False,
                False,
            ]
        )
        .head(50)
    )


    print(
        top_df.to_string(
            index=False
        )
    )


# ============================================================
# 19. ガール島確認
# ============================================================

print_header(
    "ガール島 遷移確認"
)


girl_df = feature_df[
    (
        feature_df[
            "from_island"
        ]
        == "ガール島"
    )
    |
    (
        feature_df[
            "to_island"
        ]
        == "ガール島"
    )
].copy()


if girl_df.empty:

    print(
        "ガール島の遷移データがありません。"
    )

else:

    print(
        girl_df.to_string(
            index=False
        )
    )


# ============================================================
# 20. 完了
# ============================================================

print()
print("=" * 80)
print(
    "9の日 島遷移特徴量生成 完了"
)
print("=" * 80)