from pathlib import Path
import sys


# プロジェクト直下をimport対象へ追加
PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

sys.path.append(
    str(PROJECT_ROOT)
)


from core.playwright_manager import PlaywrightManager



def get_html(url):

    pm = PlaywrightManager()

    page = None

    try:

        print("Playwright接続")

        page = pm.new_page()


        print("ページへアクセス中...")

        page.goto(url)

        page.wait_for_load_state(
            "networkidle"
        )

        page.wait_for_timeout(3000)


        print("スクロール開始")


        y = 0


        while True:

            page.evaluate(
                f"window.scrollTo(0,{y})"
            )

            page.wait_for_timeout(800)


            height = page.evaluate(
                "document.body.scrollHeight"
            )


            if y >= height:

                break


            y += 500



        print("HTML取得")


        html = page.content()


        print(
            "HTMLサイズ:",
            len(html)
        )


        with open(
            "debug.html",
            "w",
            encoding="utf-8"
        ) as f:

            f.write(html)


        return html


    finally:

        if page:

            pm.close_page(page)


        pm.close()