from bs4 import BeautifulSoup
import re
from datetime import datetime


def parse_html(html, machine_name):
    """
    P's CUBEのHTMLを解析し、
    台データのリストを返す
    """

    soup = BeautifulSoup(html, "html.parser")

    machines = []

    # 日付取得
    today = datetime.now().strftime("%Y%m%d")

    # li-数字4桁だけ取得
    for li in soup.find_all("li", id=re.compile("^li-\\d+$")):

        machine_no = li["id"].replace("li-", "")

        # 詳細ページURL作成
        detail_url = (
            "https://www.pscube.jp/dedamajyoho-P-townDMMpachi/"
            "c724041/cgi-bin/nc-v06-001.php?"
            f"cd_dai={machine_no}#{today}"
        )

        data = {
            "機種": machine_name,
            "台番号": machine_no,
            "詳細URL": detail_url
        }

        table = li.find("table")

        if table:

            for row in table.find_all("tr"):

                cols = row.find_all("td")

                if len(cols) == 2:

                    key = cols[0].get_text(strip=True)

                    value = cols[1].get_text(strip=True)

                    data[key] = value

        machines.append(data)

    print(f"{machine_name}：{len(machines)}台取得")

    return machines