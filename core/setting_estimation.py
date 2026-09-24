# ==================================
# 台単体の設定推測ロジック
# ==================================
# 依存: core/juggler_specs.py（機種別・設定1〜6のBB/RB/ぶどう確率マスタ）
#
# 提供する情報:
# - SETTING POSSIBILITY: 設定1〜6それぞれの「相対的な可能性」(%)
#     ベイズ推定（一様事前分布）で、各設定を仮定した場合に
#     現在のBB・RB・(あれば)ぶどうの観測結果がどれくらい
#     起こりやすいかをポアソン近似で比較する。
#     「設定6である確率」と断定するものではない。
# - DATA CONFIDENCE: LOW / MEDIUM / HIGH
#     現在のBB+RB合算回数から、推測材料がどの程度
#     揃っているかを示す（SETTING POSSIBILITYの結果の
#     鋭さとは別軸）。
#
# 方針（引き継ぎ資料より）:
# - 全機種共通の閾値で低設定と判定しない（機種別マスタをそのまま使う）
# - BBとRBは分けて評価する（合成確率だけで判定しない）
# - ぶどうは任意入力。未入力なら計算から除外する
# - 4〜6を一括りにせず、設定1〜6を個別に表示する
# ==================================

from math import exp, log, lgamma
from juggler_specs import JUGGLER_SPECS


def _poisson_pmf(k, lam):
    """
    ポアソン分布の確率質量関数。P(k件; 期待値lam)
    ぶどうのようにkが大きくなる（数百件）場合に
    (lam**k)やfactorial(k)がオーバーフローしないよう、
    対数空間で計算してからexpに戻す。
    """
    if lam <= 0:
        return 0.0
    log_pmf = k * log(lam) - lam - lgamma(k + 1)
    return exp(log_pmf)


def get_setting_possibility(machine_name, G, bb, rb, grape_G=None, grape_n=None):
    """
    設定1〜6の相対的な可能性(%)を返す。

    machine_name: JUGGLER_SPECSのキー（例: "マイジャグラーV"）
    G:  現在の総ゲーム数
    bb: 現在のBB回数
    rb: 現在のRB回数
    grape_G: ぶどうを数えたゲーム数（任意。未入力ならNone）
    grape_n: ぶどう回数（任意。未入力ならNone）

    戻り値: {設定番号: 可能性(%)} の辞書（合計100%）
    """
    spec = JUGGLER_SPECS.get(machine_name)
    if spec is None:
        raise ValueError(f"未登録の機種です: {machine_name}")

    use_grape = grape_G is not None and grape_n is not None

    likelihoods = {}
    for setting in range(1, 7):
        p_bb = 1 / spec[setting]["bb"]
        p_rb = 1 / spec[setting]["rb"]

        likelihood = (
            _poisson_pmf(bb, G * p_bb)
            * _poisson_pmf(rb, G * p_rb)
        )

        if use_grape:
            p_grape = 1 / spec[setting]["grape"]
            likelihood *= _poisson_pmf(grape_n, grape_G * p_grape)

        likelihoods[setting] = likelihood

    total = sum(likelihoods.values())
    if total == 0:
        # 全設定で確率がほぼ0になるような極端な入力値の場合の保険
        return {s: round(100 / 6, 1) for s in range(1, 7)}

    return {s: round(likelihoods[s] / total * 100, 1) for s in range(1, 7)}


def get_data_confidence(bb, rb, low_threshold=10, high_threshold=20):
    """
    BB+RB合算回数から観測データの十分性を判定する。

    「設定6である確率」の高さではなく、あくまで
    推測材料（サンプル数）がどれだけ揃っているかを示す。
    ぶどうはここでは考慮しない（1回あたりの判別力が
    BB/RBよりかなり弱く、材料の充実度を過大評価するため）。
    """
    n_bonus = bb + rb
    if n_bonus < low_threshold:
        return "LOW"
    elif n_bonus < high_threshold:
        return "MEDIUM"
    else:
        return "HIGH"


def analyze_machine(machine_name, G, bb, rb, grape_G=None, grape_n=None):
    """
    1台分の設定推測結果をまとめて返す。
    UI側で「なぜその推測になっているか」を表示するための
    根拠データ（G数・BB確率・RB確率・合成確率）も含める。
    """
    spec = JUGGLER_SPECS.get(machine_name)
    if spec is None:
        raise ValueError(f"未登録の機種です: {machine_name}")

    possibility = get_setting_possibility(machine_name, G, bb, rb, grape_G, grape_n)
    confidence = get_data_confidence(bb, rb)

    bb_prob = G / bb if bb > 0 else None
    rb_prob = G / rb if rb > 0 else None
    total_prob = G / (bb + rb) if (bb + rb) > 0 else None
    grape_prob = (grape_G / grape_n) if (grape_G and grape_n) else None

    return {
        "machine": machine_name,
        "G": G,
        "bb": bb,
        "rb": rb,
        "bb_prob": bb_prob,       # 例: 1/800.0
        "rb_prob": rb_prob,       # 例: 1/200.0
        "total_prob": total_prob,  # 合成確率
        "grape_prob": grape_prob,  # ぶどう確率（未入力ならNone）
        "setting_possibility": possibility,   # {設定: %}
        "data_confidence": confidence,        # LOW/MEDIUM/HIGH
        "most_likely_setting": get_most_likely_setting(possibility),  # 最も可能性が高い設定番号
        "spec": spec,                         # {設定: {"bb":理論分母, "rb":理論分母, "grape":理論分母, "diff_per_hour":理論差枚/時}}
                                               # ＝可能性%の根拠（理論値）。画面側で
                                               # 「実際のBB/RB確率」と並べて表示する想定
    }


def get_most_likely_setting(possibility):
    """
    SETTING POSSIBILITY（{設定: 可能性%}）の中で、最も可能性が高い設定番号を返す。
    複数設定が同率トップの場合は、辞書の並び順（設定1→6）で最初に出てきたものを返す。
    """
    return max(possibility, key=possibility.get)


def estimate_expected_diff(setting_possibility, spec, remaining_games, base_spins_per_hour=850):
    """
    SETTING POSSIBILITY（{設定: 可能性%}）で加重平均した、
    残りゲーム数ぶんの期待差枚数を返す。

    setting_possibility: get_setting_possibility()の戻り値
    spec: analyze_machine()が返すspec（{設定: {..., "diff_per_hour": 理論差枚/時}}）
    remaining_games: 残りの見込みゲーム数（呼び出し側で「閉店までの時間×回転数/時」等から算出）
    base_spins_per_hour: diff_per_hourの算出基準回転数（出典サイト準拠、850回転/時固定）

    「最も可能性が高い設定」だけを使う方式だと、同じ機種で最有力設定さえ一致すれば
    BB/RBの偏りが違っても同じ期待差枚になってしまう（区別できない）ため、
    setting_possibilityそのもので加重平均することで、BB/RBの偏りの違いが
    自然に反映されるようにしている。
    """
    return sum(
        (setting_possibility[s] / 100)
        * (spec[s]["diff_per_hour"] / base_spins_per_hour)
        * remaining_games
        for s in range(1, 7)
    )


def get_diff_per_setting(spec, remaining_games, base_spins_per_hour=850):
    """
    設定1〜6それぞれを仮定した場合の期待差枚数（理論値）を、設定ごとに返す。
    画面側でSETTING POSSIBILITY（可能性%）と並べて表示し、
    プレイヤー自身が中身を判断できるようにする用途。
    """
    return {
        s: round(
            (spec[s]["diff_per_hour"] / base_spins_per_hour) * remaining_games, 1
        )
        for s in range(1, 7)
    }


# ==================================
# 隣接台（left_id/right_id）算出
# ==================================
# 方針：
# - 同じ島(island)の中で、台番号(number)が±1の台だけを隣接とみなす
# - 島をまたぐ隣接（番号は連続していても違う島）は対象にしない
#   （マイジャグラーであっても島またぎは並び判定を出さない、との合意事項）
# ==================================

def build_neighbor_ids(machines):
    """
    machines: [{"id": ..., "island": ..., "number": ...}, ...]
              （machinesテーブルの id・island・number、
               またはそれに相当するデータを想定）

    戻り値: {id: (left_id, right_id)}
    """
    number_to_id_by_island = {}
    for m in machines:
        island = m["island"]
        number_to_id_by_island.setdefault(island, {})[m["number"]] = m["id"]

    neighbor_ids = {}
    for m in machines:
        island = m["island"]
        number = m["number"]
        mapping = number_to_id_by_island[island]
        left_id = mapping.get(number - 1)   # 同じislandに該当番号がなければNone
        right_id = mapping.get(number + 1)
        neighbor_ids[m["id"]] = (left_id, right_id)

    return neighbor_ids


# ==================================
# MOVE候補ロジック
# ==================================
# 検証の結論：
# - 3台並び／全台系を専用の統計的検出ロジックとして作り込むのはやめる
#   （母数が小さく、統計的検定・パターンマッチいずれも検出力が低い）
# - 176台をSETTING POSSIBILITY（RBを正しく重み付けしたモデルスコア）で
#   ランキングするだけで、BBの引きだけを見る素朴な判断より
#   はるかに『見過ごされている高設定台』を拾える
# - ただしマイジャグラーに限り、自分のDATA CONFIDENCEが低くても、
#   両隣がマイジャグラーかつ高設定っぽければ「3並び疑い」フラグで
#   優先度を引き上げる（店舗特性：マイジャグラーはほぼ毎日3並びで
#   投入される傾向があるため。あくまで"今日の"隣接台のリアルタイム
#   データだけを使い、過去の日別傾向は混ぜない）
# ==================================

NARABI_TARGET_MACHINE = "マイジャグラーV"  # 3並び疑いフラグの対象機種（店舗傾向より）


def get_high_setting_score(possibility):
    """
    SETTING POSSIBILITY(%)から、設定4〜6の合計(%)を返す。
    MOVE候補のランキングに使う『高設定っぽさスコア』。
    """
    return possibility[4] + possibility[5] + possibility[6]


def check_narabi_suspicion(target, left, right,
                            high_score_threshold=50.0,
                            min_neighbor_confidence=("MEDIUM", "HIGH")):
    """
    マイジャグラーに限り、自分のDATA CONFIDENCEがLOWでも、
    両隣がマイジャグラーかつ十分なデータ・高い高設定っぽさスコアを
    持っていれば「3並び疑い」とみなす。

    target/left/right: analyze_machine()の戻り値と同じ形式の辞書。
                        左右どちらかがNoneの場合はフラグを立てない。

    シミュレーション結果（このロジックのおおもとの検証）:
    - 自分のスコアだけのランキングでは、低データの本物の
      高設定台を拾えたのは13.2%
    - この隣接台フラグを併用すると78.6%まで拾えるようになった
    - 一方、3並びが実在しない状況での誤フラグ率は12.6%
    """
    if target is None or left is None or right is None:
        return False
    if target["machine"] != NARABI_TARGET_MACHINE:
        return False
    if left["machine"] != NARABI_TARGET_MACHINE or right["machine"] != NARABI_TARGET_MACHINE:
        return False
    if target["data_confidence"] != "LOW":
        # 自分に十分なデータがあるなら、フラグに頼らず自分の推測を信頼する
        return False

    for neighbor in (left, right):
        if neighbor["data_confidence"] not in min_neighbor_confidence:
            return False
        neighbor_score = get_high_setting_score(neighbor["setting_possibility"])
        if neighbor_score <= high_score_threshold:
            return False
    return True


def build_move_candidates(machine_records, top_n=10):
    """
    複数台の分析結果からMOVE候補ランキングを作る。

    machine_records: 各台について以下を持つ辞書のリスト
        {
            "id": 台番号など一意な識別子,
            "machine": 機種名（JUGGLER_SPECSのキー）,
            "G": ..., "bb": ..., "rb": ...,
            "grape_G": 任意, "grape_n": 任意,
            "left_id": 物理的に左隣にある台のid（無ければNoneでよい）,
            "right_id": 物理的に右隣にある台のid（無ければNoneでよい）,
        }
        隣接情報（left_id/right_id）は台の物理配置をもとに、
        呼び出し側（DB・UI側）で組み立てて渡す想定
        （このモジュール単体では物理配置を持たない）。

    戻り値: 優先度順に並んだ候補リスト（上位top_n件）。
            各要素はanalyze_machine()の結果に
            own_score / narabi_suspicion / priority_score を
            追加したもの。
    """
    analyzed = {}
    for rec in machine_records:
        result = analyze_machine(
            rec["machine"], rec["G"], rec["bb"], rec["rb"],
            rec.get("grape_G"), rec.get("grape_n"),
        )
        result["id"] = rec["id"]
        result["left_id"] = rec.get("left_id")
        result["right_id"] = rec.get("right_id")
        analyzed[rec["id"]] = result

    candidates = []
    for result in analyzed.values():
        left = analyzed.get(result["left_id"]) if result["left_id"] is not None else None
        right = analyzed.get(result["right_id"]) if result["right_id"] is not None else None

        own_score = get_high_setting_score(result["setting_possibility"])
        suspicion = check_narabi_suspicion(result, left, right)

        # 3並び疑いフラグが立った台は、自分のスコアが低くても
        # ランキング上で埋もれないよう優先度を底上げする
        # （検証時の閾値50%と同等以上の扱いにする）
        priority_score = max(own_score, 50.0) if suspicion else own_score

        result["own_score"] = round(own_score, 1)
        result["narabi_suspicion"] = suspicion
        result["priority_score"] = round(priority_score, 1)
        candidates.append(result)

    candidates.sort(key=lambda r: r["priority_score"], reverse=True)
    return candidates[:top_n]


# ==================================
# 期待枚数ランキング
# ==================================
# 方針（引き継ぎ資料より）：
# - narabi_suspicionを含むpriority_score（%ベース）とは単位が違うため、
#   1本のランキングに混ぜず、独立したアウトプットとして提供する
# - 各台の「最も可能性が高い設定」を仮定し、その設定のdiff_per_hour（差枚/時、
#   850回転基準）から、残り営業時間ぶんの期待差枚数（枚）を算出してランキングする
# ==================================

def build_expected_diff_ranking(machine_records, remaining_games, top_n=None):
    """
    machine_records: build_move_candidatesと同じ形式の入力
    remaining_games: 残りの見込みゲーム数（呼び出し側で算出して渡す）
    top_n: Noneなら全件、指定すれば上位N件のみ返す

    戻り値: expected_diff（期待差枚数、枚）で降順ソートしたリスト。
            各要素はanalyze_machine()の結果に
            expected_diff（期待差枚数）を追加したもの。
    """
    results = []
    for rec in machine_records:
        result = analyze_machine(
            rec["machine"], rec["G"], rec["bb"], rec["rb"],
            rec.get("grape_G"), rec.get("grape_n"),
        )
        result["id"] = rec["id"]

        expected_diff = estimate_expected_diff(
            result["setting_possibility"], result["spec"], remaining_games
        )
        result["expected_diff"] = round(expected_diff, 1)
        # 設定1〜6それぞれを仮定した場合の期待差枚数（理論値）。
        # 画面側でSETTING POSSIBILITYと並べて表示する用途。
        result["expected_diff_by_setting"] = get_diff_per_setting(
            result["spec"], remaining_games
        )
        results.append(result)

    results.sort(key=lambda r: r["expected_diff"], reverse=True)
    if top_n is not None:
        results = results[:top_n]
    return results


if __name__ == "__main__":
    # 動作確認1：これまで検証した6ケースをマイジャグラーVで再実行
    test_cases = [
        (800, 1, 4),
        (1000, 2, 5),
        (2000, 8, 8),
        (3000, 12, 4),
        (4000, 15, 20),
        (5000, 20, 10),
    ]
    for G, bb, rb in test_cases:
        result = analyze_machine("マイジャグラーV", G, bb, rb)
        print(f"G={G} BB={bb} RB={rb} → {result['setting_possibility']} / {result['data_confidence']}")

    # 動作確認2：MOVE候補ロジック（3並び疑いフラグの例）
    print("\n--- MOVE候補ロジックの動作確認 ---")
    demo_records = [
        {"id": 10, "machine": "マイジャグラーV", "G": 3000, "bb": 15, "rb": 15,
         "left_id": None, "right_id": 11},
        {"id": 11, "machine": "マイジャグラーV", "G": 500, "bb": 2, "rb": 3,
         "left_id": 10, "right_id": 12},
        {"id": 12, "machine": "マイジャグラーV", "G": 3000, "bb": 15, "rb": 15,
         "left_id": 11, "right_id": None},
        {"id": 20, "machine": "ネオアイムジャグラーEX", "G": 3000, "bb": 12, "rb": 6,
         "left_id": None, "right_id": None},
    ]
    for c in build_move_candidates(demo_records):
        print(f"台{c['id']}({c['machine']}): own_score={c['own_score']}% "
              f"confidence={c['data_confidence']} "
              f"narabi_suspicion={c['narabi_suspicion']} "
              f"priority={c['priority_score']}")
