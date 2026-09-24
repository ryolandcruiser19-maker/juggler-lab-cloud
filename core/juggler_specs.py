# ==================================
# ジャグラー機種別 設定確率マスタ
# ==================================
# 用途:
# - 設定1～6の統計的な設定推測
# - BB / RB / ぶどうの基準値を一元管理
# - 残り営業時間ぶんの期待差枚数の算出（diff_per_hour）
#
# 確率は「1 / 分母」の分母を数値で保持。
# 例: "bb": 273.1 は BB確率 1/273.1
#
# diff_per_hour は、1時間あたり850回転・3枚賭け固定で算出した
# 設定ごとの理論差枚（枚）。出典サイトの計算式をそのまま使用。
#
# 出典:
# https://smokefield.info/slot/jugglerspec.html
#
# 注意:
# ぶどうはプレイヤー入力がある場合のみ設定推測に使用する。
# 未入力の場合は統計計算から除外する。
# ==================================

JUGGLER_SPECS = {

    "マイジャグラーV": {
        1: {"bb": 273.1, "rb": 409.6, "grape": 5.90, "diff_per_hour": -55},
        2: {"bb": 270.8, "rb": 385.5, "grape": 5.86, "diff_per_hour": -28},
        3: {"bb": 266.4, "rb": 336.1, "grape": 5.82, "diff_per_hour": 20},
        4: {"bb": 254.0, "rb": 290.0, "grape": 5.80, "diff_per_hour": 96},
        5: {"bb": 240.1, "rb": 268.6, "grape": 5.78, "diff_per_hour": 163},
        6: {"bb": 229.1, "rb": 229.1, "grape": 5.67, "diff_per_hour": 269},
    },

    "ネオアイムジャグラーEX": {
        1: {"bb": 273.1, "rb": 439.8, "grape": 6.05, "diff_per_hour": -55},
        2: {"bb": 269.7, "rb": 399.6, "grape": 6.05, "diff_per_hour": -29},
        3: {"bb": 269.7, "rb": 331.0, "grape": 6.05, "diff_per_hour": 11},
        4: {"bb": 259.0, "rb": 315.1, "grape": 6.05, "diff_per_hour": 53},
        5: {"bb": 259.0, "rb": 255.0, "grape": 6.05, "diff_per_hour": 109},
        6: {"bb": 255.0, "rb": 255.0, "grape": 5.79, "diff_per_hour": 167},
    },

    "ファンキージャグラー2": {
        1: {"bb": 266.4, "rb": 439.8, "grape": 5.94, "diff_per_hour": -54},
        2: {"bb": 259.0, "rb": 407.1, "grape": 5.91, "diff_per_hour": -15},
        3: {"bb": 256.0, "rb": 366.1, "grape": 5.89, "diff_per_hour": 18},
        4: {"bb": 249.2, "rb": 322.8, "grape": 5.85, "diff_per_hour": 75},
        5: {"bb": 240.1, "rb": 299.3, "grape": 5.78, "diff_per_hour": 135},
        6: {"bb": 219.9, "rb": 262.1, "grape": 5.70, "diff_per_hour": 256},
    },

    "ゴーゴージャグラー3": {
        1: {"bb": 259.0, "rb": 354.2, "grape": 6.27, "diff_per_hour": -51},
        2: {"bb": 258.0, "rb": 332.7, "grape": 6.21, "diff_per_hour": -24},
        3: {"bb": 257.0, "rb": 306.2, "grape": 6.15, "diff_per_hour": 9},
        4: {"bb": 254.0, "rb": 268.6, "grape": 6.08, "diff_per_hour": 65},
        5: {"bb": 247.3, "rb": 247.3, "grape": 6.01, "diff_per_hour": 121},
        6: {"bb": 234.9, "rb": 234.9, "grape": 5.93, "diff_per_hour": 191},
    },

    "ジャグラーガールズSS": {
        1: {"bb": 273.1, "rb": 381.0, "grape": 5.99, "diff_per_hour": -55},
        2: {"bb": 270.8, "rb": 350.5, "grape": 5.99, "diff_per_hour": -32},
        3: {"bb": 260.1, "rb": 316.6, "grape": 5.99, "diff_per_hour": 20},
        4: {"bb": 250.1, "rb": 281.3, "grape": 5.99, "diff_per_hour": 79},
        5: {"bb": 243.6, "rb": 270.8, "grape": 5.90, "diff_per_hour": 126},
        6: {"bb": 226.0, "rb": 252.1, "grape": 5.84, "diff_per_hour": 218},
    },

    "ウルトラミラクルジャグラー": {
        1: {"bb": 267.5, "rb": 425.6, "grape": 5.94, "diff_per_hour": -54},
        2: {"bb": 261.1, "rb": 402.1, "grape": 5.94, "diff_per_hour": -15},
        3: {"bb": 256.0, "rb": 350.5, "grape": 5.94, "diff_per_hour": 18},
        4: {"bb": 242.7, "rb": 322.8, "grape": 5.94, "diff_per_hour": 75},
        5: {"bb": 233.2, "rb": 297.9, "grape": 5.88, "diff_per_hour": 135},
        6: {"bb": 216.3, "rb": 277.7, "grape": 5.82, "diff_per_hour": 256},
    },

    "ミスタージャグラー": {
        1: {"bb": 268.6, "rb": 374.5, "grape": 6.30, "diff_per_hour": -51},
        2: {"bb": 267.5, "rb": 354.2, "grape": 6.23, "diff_per_hour": -25},
        3: {"bb": 260.1, "rb": 331.0, "grape": 6.16, "diff_per_hour": 22},
        4: {"bb": 249.2, "rb": 291.3, "grape": 6.09, "diff_per_hour": 96},
        5: {"bb": 240.9, "rb": 257.0, "grape": 6.02, "diff_per_hour": 168},
        6: {"bb": 237.4, "rb": 237.4, "grape": 5.95, "diff_per_hour": 215},
    },

    "ハッピージャグラーVⅢ": {
        1: {"bb": 273.1, "rb": 397.2, "grape": 6.05, "diff_per_hour": -61},
        2: {"bb": 270.8, "rb": 362.1, "grape": 6.02, "diff_per_hour": -33},
        3: {"bb": 263.2, "rb": 332.7, "grape": 5.99, "diff_per_hour": 13},
        4: {"bb": 254.0, "rb": 300.6, "grape": 5.85, "diff_per_hour": 88},
        5: {"bb": 239.2, "rb": 273.1, "grape": 5.82, "diff_per_hour": 165},
        6: {"bb": 226.0, "rb": 256.0, "grape": 5.79, "diff_per_hour": 232},
    },
}


def get_juggler_spec(machine_name):
    """機種名から設定1～6の確率マスタを取得する。"""
    return JUGGLER_SPECS.get(machine_name)


def get_setting_spec(machine_name, setting):
    """機種名と設定番号から確率マスタを取得する。"""
    machine = JUGGLER_SPECS.get(machine_name)
    if machine is None:
        return None
    return machine.get(setting)
