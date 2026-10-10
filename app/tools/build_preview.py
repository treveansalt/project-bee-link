"""Bundle a double-clickable, offline demo preview; live capture uses server.py."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
html = (root / "dist/index.html").read_text(encoding="utf-8")
css = (root / "dist/style.css").read_text(encoding="utf-8")
js = (root / "dist/app.js").read_text(encoding="utf-8")
html = html.replace('<link rel="stylesheet" href="style.css">', '<style>' + css + '</style>')
html = html.replace('<script src="app.js" type="module"></script>', '<script>' + js + '</script>')
html = html.replace('href="guide.html"', 'href="dist/guide.html"')
(root / "OPEN-BEE-LINK.html").write_text(html, encoding="utf-8")
print("Offline preview generated: OPEN-BEE-LINK.html")
