#!/usr/bin/env python3

# 一時ファイル
import tempfile
import os

tempfile.gettempdir()   # 使用される一時ディレクトリ

fp = tempfile.TemporaryFile()
fp.write(b"Hello")
fp.close()  # closeと同時に消去 [[注意]]

fp = tempfile.NamedTemporaryFile(delete=False)
print(fp.name)  # ファイル名
fp.write(b"Hello")
fp.close()
os.remove(fp.name)  # delete=Falseでは自分で消すこと

# seealso: SpooledTemporaryFile (メモリ上)

with tempfile.TemporaryDirectory() as tmpdir:
    pass  # tmpdirを利用して作業
# withを抜けるとディレクトリは削除される

(fno, filename) = tempfile.mkstemp("suffix", "prefix")
filename   # 例: => /tmp/prefixuzavw57rsuffix
os.remove(filename)  # きちんと消すこと！
