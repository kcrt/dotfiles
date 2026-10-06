# script/lib

`script/` 直下のスクリプトから共有する小さなモジュール群。

## 使い方

```python
from lib.termtext import display_width
from lib.progressbar import BarSlot, LiveLine
```

`sys.path` をいじる必要はない。`uv run` は `sys.path[0]` をスクリプトの**実体の
あるディレクトリ**にするので、`script/` 直下から実行しても、別の場所から
フルパスで叩いても、PATH 上のシンボリックリンク経由でも `lib.*` が見つかる。
`__init__.py` も要らない（名前空間パッケージで動く。置いてあるのは意図を示すため）。

## 守ること

1. **標準ライブラリだけを使う。**
   PEP 723 の `dependencies` は実行されるスクリプトにしか書けない。ここで外部
   パッケージに依存すると、import する全スクリプトが同じ依存を書き並べる羽目になる。
   外部**コマンド**（`ffprobe.py` が叩く ffprobe など）は別だが、入っていないときは
   何が無いのか分かる例外にすること。

2. **`requires-python` は呼ぶ側の最低値に合わせる。**
   現在の下限は `ffmpeg-convert.py` の 3.12。

3. **アプリ固有の判断を持ち込まない。**
   例: `progressbar.py` は「1行を書き換え続ける機構」だけを持ち、どの欄をどんな
   文言で出すかは呼ぶ側が `LiveLine.parts()` で決める。`prompt_choice` の言語も
   同じ理由で呼ぶ側が `words=` で選ぶ（既定は日本語）。
   よくある組み合わせを既製品として置くのは構わない（`ProgressBar`）。ただし
   それは `LiveLine` を書く代わりの近道であって、置き換えではない。

4. **コメントとdocstringは英語で書く。**
   利用者に見える文字列（`prompt.py` の質問文や `humanize.py` の「削減」など）は
   呼ぶ側の出力に合わせて日本語のまま。

5. **人に向けた出力は stderr へ出し、stdout はスクリプトの成果物に空けておく。**
   進捗バーもログも同じ stream に乗せる必要がある。`LiveLine.report()` を通らない
   素の `print()` は、別の stream からバーの行を踏むため。`LiveLine` の既定も
   stderr。これで `cmd > out` はバーを見ながら成果物だけ取れ、`cmd | other` に
   経過報告が混ざらない。
   色の可否は**出力先ごと**に決まる（`use_color_for`）ので、`paint()` /
   `status_line()` / `size_change()` には出力先を渡すこと。省略時は stdout 判定
   になり、`cmd > out` で端末に出ている文字から色が落ちる。

## 中身

| モジュール | 中身 |
| --- | --- |
| `termtext.py` | 表示幅の勘定（全角2桁・結合文字0桁・SGRは0桁）、パディング、切り詰め |
| `termcolor.py` | 24bit色・256色・基本16色と太字、`NO_COLOR`/`TERM=dumb`/`--color` の判定 |
| `humanize.py` | バイト数（`1.2 MB`・`1.2MB`）、変換前後の増減、秒数（`1:02:03`） |
| `progressbar.py` | 進捗バーの描画と、1行を書き換え続ける `LiveLine`、欄を決め打ちにした `ProgressBar`（iterableを包むだけで使える） |
| `prompt.py` | y/n の確認、1行入力、番号で選ばせる対話（文言は `ChoiceWords` で日英切替）、端末かどうかの判定 |
| `ffprobe.py` | ffprobeで章と容器のメタデータを読む（`-show_streams` 等の生JSONも） |
| `par2.py` | PAR2ファイルをパケット単位で分解・再構成する（索引の抽出、リカバリスライスの取り出し、境界が揃いかつ端数の出ないスライスサイズの算出） |
| `trash.py` | macOSのゴミ箱へ移す（ボリュームを跨がない） |
| `with_secret.py` | 秘密の環境変数が無ければ `with-secret` 経由で自分を起動し直す（Touch ID で承認） |
| `sample.py` | 上記すべての動作確認・デモ（直接実行する） |

## 動作確認

lib を触ったら `sample.py` を直接叩く。各モジュールの出力を目で見て確かめられる
（桁揃え・色・進捗バーのアニメーション）ほか、答えが一つに決まる項目は自己検査
する。失敗が一つでもあれば終了コードは1。

```sh
./sample.py                       # 全部
./sample.py termtext ffprobe      # セクションを選ぶ
./sample.py --color never         # 色なしの経路を通す
./sample.py --seconds 8 --rainbow # 進捗バーを長めに見る
./sample.py --interactive         # confirm / prompt_choice を実際に答える
./sample.py --trash               # 一時ファイルを本当にゴミ箱へ入れて戻す
```

## 利用しているスクリプト

`grep -l '^from lib\.' script/*.py` で一覧が出る。現在23本:

| モジュール | 使っているスクリプト |
| --- | --- |
| `termtext.py` | `ffmpeg-convert.py` `ble_monitor.py` |
| `termcolor.py` | `ffmpeg-convert.py` `snapshot_restore.py` `check_network.py` `pubmed_get_abstract.py` `pubmed_listup_journal.py` `paper_backup.py` |
| `humanize.py` | `ffmpeg-convert.py` `compare_dir.py` `snapshot_restore.py` `fix-broken-movie.py` `repack_images.py` `split_mp4_by_chapter.py` `python_finddup.py` `average_filesize_in_zip.py` `paper_backup.py` |
| `progressbar.py` | `ffmpeg-convert.py` `repack_images.py` `paper_backup.py` |
| `prompt.py` | `ffmpeg-convert.py` `analyse-mail.py` `manage_imap_mail.py` `repack_images.py` `split_spread_pdf.py` `split_mp4_by_chapter.py` `paper_backup.py` |
| `ffprobe.py` | `split_mp4_by_chapter.py` `keep_only_audio_and_tag.py` |
| `par2.py` | `paper_backup.py` |
| `trash.py` | `ffmpeg-convert.py` |
| `with_secret.py` | `ai_draw.py` `ai_draw_gui.py` `summarize_md_claude.py` `mistral_ocr.py` `geocoding_latlon.py` `proxy_to_zai.py` |
