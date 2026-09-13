import os
import streamlit

INJECT = (
    '<link rel="manifest" href="/static/manifest.json">\n'
    '<link rel="apple-touch-icon" href="/static/icon-192.png">\n'
    '<meta name="theme-color" content="#050b08">\n'
)

path = os.path.join(os.path.dirname(streamlit.__file__), "static", "index.html")

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

if "manifest.json" not in html:
    html = html.replace("</head>", INJECT + "</head>")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

print(f"Injected manifest link into {path}")
