#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pymupdf",
# ]
# ///
"""PDF 本文の指定した語句に蛍光マーカー（ハイライト注釈）を引く。

査読や調べ物で「原典のどこにそう書いてあるか」を人に見せるための下ごしらえ。
語句は本文テキストから探すので、**行またぎ・ハイフン分割・段組をまたぐ場合でも当たる**
（PDF ビューアの検索が落とすケース）。注釈にはメモ（なぜそこを見るか）を付けられる。

使い方:
    ./pdf_highlight.py paper.pdf -m "at least two relevant mite AIT prescriptions"
    ./pdf_highlight.py paper.pdf -m "38.6%" --note "3年時点の継続率" --color green
    ./pdf_highlight.py paper.pdf --json marks.json -o paper.highlighted.pdf
    ./pdf_highlight.py paper.pdf -m "38.6%" --overwrite     # 元ファイルに直接引く

`--json` は次の形（`note` と `color` は省略可）:
    [{"text": "探す語句", "note": "メモ", "color": "yellow"}, ...]

出力は既定では元ファイルを書き換えず `<元名>.highlighted.pdf` に書く（`--overwrite` で元ファイルへ
直接引く）。**1件も当たらなければ何も書かない**ので、上書きしても元ファイルは無傷で残る。
見つからなかった語句は終了時に一覧で報告する（黙って落とさない）。
"""

from __future__ import annotations

import argparse
import bisect
import json
import re
import sys
import tempfile
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import pymupdf

COLORS: Final[dict[str, tuple[float, float, float]]] = {
    "yellow": (1.0, 0.92, 0.23),
    "green": (0.56, 0.93, 0.56),
    "blue": (0.53, 0.81, 0.98),
    "pink": (1.0, 0.63, 0.76),
    "orange": (1.0, 0.75, 0.35),
}
DEFAULT_COLOR: Final[str] = "yellow"
HYPHENS: Final[tuple[str, ...]] = ("-", "‐", "­")
SAME_LINE_TOLERANCE: Final[float] = 1.0          # これ以下の y 差は同じ行とみなす（pt）
MAX_WORD_GAP: Final[float] = 1.0                 # 語間をつなぐ上限（行の高さに対する倍率）
LINE_NUMBER_RE: Final[re.Pattern[str]] = re.compile(r"\d{1,4}")   # 原稿 PDF の行番号
TRANSLATIONS: Final[dict[int, str]] = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "−": "-", " ": " ",
})


@dataclass(frozen=True)
class Mark:
    """探す語句1件。"""

    text: str
    note: str = ""
    color: str = DEFAULT_COLOR


@dataclass
class Token:
    """本文の1語（ハイフンで行分割された語は1つに結合してある）。"""

    text: str
    rects: list[pymupdf.Rect] = field(default_factory=list)


def normalize(text: str) -> str:
    """比較用に正規化する（全角・引用符・ダッシュの揺れを吸収し、小文字化する）。"""
    return unicodedata.normalize("NFKC", text).translate(TRANSLATIONS).lower().strip()


def page_tokens(page: pymupdf.Page) -> list[Token]:
    """ページを読み順の語リストにする。行末ハイフンで割れた語は結合する。"""
    words = sorted(page.get_text("words"), key=lambda w: (w[5], w[6], w[7]))
    tokens: list[Token] = []
    index = 0
    while index < len(words):
        x0, y0, x1, y1, text, _block, _line, _word_no = words[index]
        rects = [pymupdf.Rect(x0, y0, x1, y1)]
        # 行末のハイフンは組版上の分割（"ado-" + "lescents"）。次の語が別の行にあるときだけ結合する。
        while (
            text.endswith(HYPHENS)
            and index + 1 < len(words)
            and abs(words[index + 1][1] - y0) > SAME_LINE_TOLERANCE
        ):
            index += 1
            nx0, ny0, nx1, ny1, next_text, _b, _l, _w = words[index]
            text = text[:-1] + next_text
            rects.append(pymupdf.Rect(nx0, ny0, nx1, ny1))
            y0 = ny0
        normalized = normalize(text)
        if normalized:
            tokens.append(Token(normalized, rects))
        index += 1
    return tokens


def search_tokens(tokens: list[Token], indices: list[int], needle: str) -> list[list[int]]:
    """`indices` で選んだ語だけを対象に語句を探し、当たった語の番号リストを返す。"""
    haystack = " ".join(tokens[i].text for i in indices)
    offsets: list[int] = []
    position = 0
    for i in indices:
        offsets.append(position)
        position += len(tokens[i].text) + 1

    hits: list[list[int]] = []
    at = haystack.find(needle)
    while at != -1:
        start = bisect.bisect_right(offsets, at) - 1
        end = bisect.bisect_left(offsets, at + len(needle))
        hits.append(indices[start:max(end, start + 1)])
        at = haystack.find(needle, at + len(needle))
    return hits


def find_token_spans(tokens: list[Token], query: str) -> list[list[int]]:
    """語句に当たる語の番号を、そのページ内の全出現について返す。

    素の本文で当たらなければ、行番号（原稿 PDF の左端に振られた単独の数字）を
    飛ばして再検索する。査読原稿は本文の途中に行番号が挟まるため。
    """
    needle = " ".join(part for part in normalize(query).split() if part)
    if not needle:
        return []
    hits = search_tokens(tokens, list(range(len(tokens))), needle)
    if hits:
        return hits
    without_numbers = [i for i, token in enumerate(tokens) if not LINE_NUMBER_RE.fullmatch(token.text)]
    return search_tokens(tokens, without_numbers, needle)


def merge_rects(rects: list[pymupdf.Rect]) -> list[pymupdf.Rect]:
    """同じ行で隣り合う語の矩形を1つにつなぐ。

    語ごとの矩形をそのまま引くと**語間の空白が塗られず**、蛍光ペンが単語ごとに途切れる
    （"Hello, world" が [Hello,][world] に割れる）。行またぎ・段またぎ（`MAX_WORD_GAP` を
    超える横の空き＝段間の余白や表のセル境界）はつながない。
    """
    merged: list[pymupdf.Rect] = []
    for rect in rects:
        last = merged[-1] if merged else None
        if (
            last is not None
            and abs(rect.y0 - last.y0) <= SAME_LINE_TOLERANCE
            and last.x0 <= rect.x0
            and rect.x0 - last.x1 <= max(last.height, rect.height) * MAX_WORD_GAP
        ):
            merged[-1] = last | rect
        else:
            merged.append(rect)
    return merged


def highlight_page(page: pymupdf.Page, tokens: list[Token], mark: Mark) -> int:
    """1ページ分のハイライトを引き、引いた箇所の数を返す。"""
    color = COLORS.get(mark.color, COLORS[DEFAULT_COLOR])
    hits = 0
    for matched in find_token_spans(tokens, mark.text):
        rects = merge_rects([rect for index in matched for rect in tokens[index].rects])
        if not rects:
            continue
        annot = page.add_highlight_annot(rects)
        annot.set_colors(stroke=color)
        if mark.note:
            annot.set_info(title="Claude", content=mark.note)
        annot.update()
        hits += 1
    return hits


def save_document(document: pymupdf.Document, pdf_path: Path, out_path: Path) -> None:
    """保存する。元ファイルへの上書きは一時ファイル経由で行う（開いたまま同じ名前へは書けない）。"""
    if out_path != pdf_path:
        document.save(out_path, garbage=3, deflate=True)
        return
    with tempfile.NamedTemporaryFile(
        dir=pdf_path.parent, prefix=f".{pdf_path.stem}.", suffix=".pdf", delete=False
    ) as handle:
        temp_path = Path(handle.name)
    try:
        document.save(temp_path, garbage=3, deflate=True)
        temp_path.replace(pdf_path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def highlight(pdf_path: Path, marks: list[Mark], out_path: Path) -> dict[str, list[int]]:
    """PDF 全体にハイライトを引いて保存し、語句ごとの該当ページ（1始まり）を返す。

    1件も当たらなかったときは保存しない（`--overwrite` で元ファイルを壊さないため）。
    """
    found: dict[str, list[int]] = {mark.text: [] for mark in marks}
    with pymupdf.open(pdf_path) as document:
        for number, page in enumerate(document, start=1):
            tokens = page_tokens(page)
            for mark in marks:
                if highlight_page(page, tokens, mark):
                    found[mark.text].append(number)
        if any(found.values()):
            save_document(document, pdf_path, out_path)
    return found


def load_marks(args: argparse.Namespace) -> list[Mark]:
    marks = [Mark(text=text, note=args.note or "", color=args.color) for text in args.mark]
    if args.json:
        entries = json.loads(Path(args.json).read_text(encoding="utf-8"))
        marks += [
            Mark(
                text=entry["text"],
                note=entry.get("note", ""),
                color=entry.get("color", args.color),
            )
            for entry in entries
        ]
    return marks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pdf", type=Path, help="入力 PDF")
    parser.add_argument("-m", "--mark", action="append", default=[], metavar="TEXT", help="ハイライトする語句（複数可）")
    parser.add_argument("--note", default="", help="-m で指定した語句に付けるメモ")
    parser.add_argument("--color", default=DEFAULT_COLOR, choices=sorted(COLORS), help=f"色（既定: {DEFAULT_COLOR}）")
    parser.add_argument("--json", type=Path, help="語句・メモ・色をまとめて書いた JSON")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("-o", "--output", type=Path, help="出力先（既定: <元名>.highlighted.pdf）")
    output.add_argument("--overwrite", action="store_true", help="元ファイルに直接引く")
    args = parser.parse_args()

    if not args.pdf.is_file():
        print(f"PDF が見つからない: {args.pdf}", file=sys.stderr)
        return 1
    marks = load_marks(args)
    if not marks:
        print("ハイライトする語句が無い（-m か --json を指定する）", file=sys.stderr)
        return 1

    pdf_path = args.pdf.resolve()
    out_path = pdf_path if args.overwrite else (args.output or args.pdf.with_suffix(".highlighted.pdf")).resolve()
    found = highlight(pdf_path, marks, out_path)

    print(f"{out_path}" if any(found.values()) else "1件も当たらなかったので何も書いていない")
    missing = [text for text, pages in found.items() if not pages]
    for mark in marks:
        pages = found[mark.text]
        where = "見つからない" if not pages else "p." + ",".join(str(page) for page in pages)
        print(f"  [{where}] {mark.text[:70]}")
    if missing:
        print(f"⚠️ {len(missing)} 件が見つからなかった（表記揺れの可能性。短い語句で試す）", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
