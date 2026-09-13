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

2. **`requires-python` は呼ぶ側の最低値に合わせる。**
   現在の下限は `ffmpeg-convert.py` の 3.12。

3. **アプリ固有の判断を持ち込まない。**
   例: `progressbar.py` は「1行を書き換え続ける機構」だけを持ち、どの欄をどんな
   文言で出すかは呼ぶ側が `LiveLine.parts()` で決める。

## 中身

| モジュール | 中身 |
| --- | --- |
| `termtext.py` | 表示幅の勘定（全角2桁・結合文字0桁・SGRは0桁）、パディング、切り詰め |
| `termcolor.py` | 24bit色と256色、`NO_COLOR`/`TERM=dumb`/`--color` の判定 |
| `humanize.py` | バイト数（`1.2 MB`・`1.2MB`）、変換前後の増減、秒数（`1:02:03`） |
| `progressbar.py` | 進捗バーの描画と、1行を書き換え続ける `LiveLine` |
| `prompt.py` | 番号で選ばせる対話、端末かどうかの判定 |
| `trash.py` | macOSのゴミ箱へ移す（ボリュームを跨がない） |

## 利用しているスクリプト

`ffmpeg-convert.py` / `ble_monitor.py` / `snapshot_restore.py` / `compare_dir.py`
