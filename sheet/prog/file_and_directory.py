#!/usr/bin/env python3

# テスト
# /data (Current Directory)
# ├── animals/
# │     ├── dog.txt
# │     └── elephant.txt
# ├── .secret
# ├── apple.jpg
# └── hello.txt

import os
import glob
import stat
import shutil
from pathlib import Path, PureWindowsPath

os.chdir("/data")
os.getcwd()  # => /data

# ファイルとディレクトリの列挙
# --- os.pathを用いた古式ゆかしき方法
os.listdir("/data")    # => ['apple.jpg', 'animals', 'hello.txt', '.secret']
glob.glob("/data/*")  # 絶対パス => ['/data/apple.jpg', '/data/animals', '/data/hello.txt']
glob.glob("./*")      # 相対パス => ['./apple.jpg', './animals', './hello.txt']
glob.glob("/data/**", recursive=True)    # サブディレクトリも含む、/data/も含むのに注意 => ['/data/', '/data/apple.jpg', '/data/animals', '/data/animals/dog.txt', '/data/animals/elephant.txt', '/data/hello.txt']
glob.glob(".*")         # ドット(.)で始まるファイル => ['.secret']
# *, ?, [] (例:[A-Z], [0-9]など), **(recursive) が使用できる
# /bin/[にマッチさせたい場合は => glob.glob("/bin/[[]")
# より低レベルな処理はos.scandirとfnmatchで行うことが出来る。

for file in glob.iglob("/data/*"):
    # forなどではイテレーターを返すiglobが便利
    print(file)

# パスの解釈
os.path.abspath("./apple.jpg")          # 例: => "/data/apple.jpg"
os.path.relpath("/data/apple.jpg")      # => ./apple.jpg
os.path.isabs("./appke.jpg")            # 絶対パスかどうか

os.path.expanduser("~/.vimrc")      # 例: => /Users/kcrt/.vimrc など
os.path.expandvars("$GOPATH/bin")   # 例: => /Users/kcrt/go/bin など
os.path.normpath("/usr/local/../../bin/bash")   # => /bin/bash

os.path.join("usr", "bin", "open")  # => /usr/bin/open

filename = "/data/animals/dog.txt"
os.path.basename(filename)      # => dog.txt
os.path.dirname(filename)       # => /data/animals
os.path.split(filename)  # => ['/data/animals', 'dog.txt']
os.path.splitext(filename)   # => ['/data/animals/dog', '.txt']

# 存在確認
os.path.exists(filename)
os.path.isfile(filename)         # 通常ファイルかどうか(シンボリックリンク含む)
os.path.isdir(filename)
# lexists: シンボリックリンクでの挙動に違い
# islink: ディレクトリをさすシンボリックリンクか
# ismount: マウントポイントか

# 属性確認
os.path.getsize(filename)        # ファイルサイズ
os.path.getatime(filename)       # アクセス時間 (epoch秒)
# getmtime (更新時間), getctime (変更時間)

# パーミション
st = os.stat(filename)
st.st_mode   # パーミッション
st.st_uid    # ユーザーID
st.st_gid    # グループID
st.st_ino    # ino 
# 今の権限でアクセスできるかの確認には
if os.access(filename, os.R_OK):
    print("You can read!")
    # 他にW_OK, X_OK
# パーミッションの変更
os.chmod("/data/hello.txt", stat.S_IRUSR | stat.S_IWUSR)
# chown

# --- pathlib (新しい方法)
# ファイルシステムにアクセスしないPurePathと、具体的なシステムのデータをハンドルするPathがある。
# たとえば、non-Windows上でも、PureWindowsPathならWindowsのパスを扱える
# ほとんどの場合はPathを使用する

p = Path(".")
list(p.iterdir())   # => ディレクトリ内のアイテムを刺すPathオブジェクト
list(p.glob("*"))   # 同上 (glob.globと違い、ドット(.)で始まるファイルも含む [[注意]] )
list(p.glob("**/*"))   # サブディレクトリも

# パスの解釈
Path("./apple.jpg").resolve()       # 絶対パスを取得
cwd = Path.cwd()                    # os.getcwd()のPath版
Path("/data/apple.jpg").relative_to(cwd)  # 相対パスへ
# os.path.relpathでは"./apple.jpg"
# Path.relative_toでは"apple.jpg" [[注意]]
p.is_absolute()     # 絶対パスかどうか

Path("~/.vimrc").expanduser()
Path("/usr/local/../../bin/bash").resolve()  # => /bin/bash

Path("/usr") / "bin" / "open"   # '/'でパスの結合

p = Path("/data/animals/dog.txt")
p.name      # => dog.txt
p.parent    # => /data/animals
p.stem      # => dog
p.suffix    # => .txt
print(p.drive)  # 空文字列

pwin = PureWindowsPath("C:\\Windows\\notepad.exe")
print(pwin.name)    # => notepad.exe
print(pwin.parent)  # => C:\Windows
print(pwin.suffix)  # => .exe
print(pwin.drive)   # => C:

# 存在確認
p.exists()
p.is_file()  # 通常ファイルか (シンボリックリンク含む)
p.is_dir()   # ディレクトリか
# is_symlink, is_mount

# 属性確認
p.stat().st_size    # ファイルサイズ
p.stat().st_atime   # アクセス時間
# st_mtime, st_ctime

# パーミッション
p.stat().st_mode    # パーミッション
p.owner()
p.group()
p.chmod(0o777)
# p.chownはない、os.chownを使用する

# os.pathと違い、ファイルの中身のアクセスも出来る
with p.open() as f:
    f.readline()
# p.read_bytes(), p.read_text(encoding=...)
# p.write_bytes(ddata), p.write_text(data, encoding=...)


# ファイルのコピーや移動
os.chdir("/data")
os.mkdir("yes")     # すでにディレクトリがあると例外
# または Path("/data/yes").mkdir(exist_ok=True)
os.makedirs("one/two/three")    # 再帰的に作成
# または Path("one/two/three").mkdir(parents=True)
shutil.copyfile("apple.jpg", "orange.jpg")  # (src, dest) - destがあると上書き [[注意]]
shutil.copy("orange.jpg", "animals")      # copyfileと違い、destはディレクトリでも可, copymode: パーミションをコピー, copystat: パーミション・属性をコピー, copy2: ファイルをメタデータごとコピー, copytree(src, dest): ディレクトリごと
os.rename("orange.jpg", "kiwi.jpg")
# または Path("orange.jpg").rename("kiwi.jpg")
shutil.move("kiwi.jpg", "animals")          # renameと違い、destはディレクトリでも可
os.remove("/data/animals/kiwi.jpg")   # os.unlinkも同じ動作
# または Path("......").unlink()
os.rmdir("/data/yes")
# または Path("/data/yes").rmdir()
os.removedirs("one/two/three")
# shutil.rmtree(path): 中身が入っていても削除


# その他
# ファイルやディレクトリの比較を行う filecmp, dircmp
