#!/usr/bin/env bash
# Build the lab book: dist/book.html, dist/book.epub, dist/book.pdf (pdf via headless Chromium).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p dist
mapfile -t CH < <(ls chapters/*.md | sort)
META=(--metadata title="המעבדה" --metadata subtitle="מתמטיקה, פיזיקה ובינה מלאכותית — ספר התיעוד של ESH27 Lab" \
      --metadata lang=he --metadata dir=rtl --metadata date="$(date +%Y-%m-%d)")
pandoc "${CH[@]}" "${META[@]}" -f markdown+tex_math_dollars+footnotes -s --toc --toc-depth=2 \
  --katex=https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/ --css book.css \
  -o dist/book.html
cp assets/book.css dist/
pandoc "${CH[@]}" "${META[@]}" -f markdown+tex_math_dollars+footnotes --toc --toc-depth=2 \
  --css assets/book.css --mathml -o dist/book.epub
# PDF: render the HTML with MathML (works offline) through Chromium
pandoc "${CH[@]}" "${META[@]}" -f markdown+tex_math_dollars+footnotes -s --toc --toc-depth=2 \
  --mathml --css book.css -o dist/book-print.html
node -e '
const {chromium}=require("playwright");
(async()=>{const b=await chromium.launch();const p=await b.newPage();
await p.goto("file://"+process.cwd()+"/dist/book-print.html",{waitUntil:"load"});
await p.emulateMedia({media:"print",colorScheme:"light"});
await p.pdf({path:"dist/book.pdf",format:"A4",margin:{top:"18mm",bottom:"18mm",left:"16mm",right:"16mm"},
 displayHeaderFooter:true,headerTemplate:"<span></span>",
 footerTemplate:"<div style=\"font-size:8px;width:100%;text-align:center\"><span class=pageNumber></span></div>"});
await b.close();})();'
rm -f dist/book-print.html
echo "built: $(ls dist)"
