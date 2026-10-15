## PAR2 (par2cmdline) - 誤り訂正用の冗長データを作り、壊れたファイルを検証・修復する
par2 c | v | r                          # create / verify / repair (par2create 等の別名もある)

## CREATE
par2 c foo.par2 foo.zip                 # 冗長度 5% (既定)
par2 c -r10 foo.par2 *.flac             # 冗長度 10%
par2 c -rm200 foo.par2 foo.iso          # 冗長データを約 200MB に
par2 c -R photos.par2 photos            # サブディレクトリも含める
par2 c -n4 -u foo.par2 foo.iso          # 同じサイズの回復ファイル 4 個に分ける
# → foo.par2 (索引) + foo.vol000+NN.par2 (回復ブロック) ができる

## VERIFY
par2 v foo.par2                         # 終了コード: 0=無傷 1=修復可 2=修復不可
par2 v --full-hash foo.par2             # ファイル全体のハッシュも見る

## REPAIR
par2 r foo.par2                         # 元ファイルは foo.zip.1 として残る
par2 r -p foo.par2                      # 成功したら .1 と par2 ファイルを消す
par2 r foo.par2 *                       # 名前が変わったファイルも探して照合する

## OPTIONS
-q / -q -q                              # 静かに / 完全に無言
-t<n>                                   # スレッド数
-B<path>                                # ファイルパスの基準ディレクトリ
-b<n> / -s<n>                           # ブロック数 / ブロックサイズ (片方だけ)
