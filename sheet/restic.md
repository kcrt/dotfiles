## SNAPSHOTS
restic snapshots [--compact]            # 全世代
restic snapshots --tag documents        # ソースで絞る
restic snapshots --latest 1             # 各グループの最新だけ
restic stats [--mode raw-data]          # 復元サイズ

## BROWSE
restic ls latest                        # 最新の中身
restic ls <ID> /Users/kcrt/Documents    # パスを指定
restic ls -l --recursive <ID>           # ls -l 相当
restic find `'確定申告*'`               # 全世代からファイル名で探す
restic dump <ID> /path/to/file > out    # 1ファイルだけ標準出力へ
restic mount ~/mnt/restic               # Finder で開く (macFUSE 必要)

## RESTORE
restic restore <ID> --target /tmp/r [--include `'**/musicsheet/**'`]

## DIFF
restic diff <古いID> <新しいID>
restic diff <ID1> <ID2> --metadata      # mode/mtime の差も出す

## BACKUP (手打ちは非推奨: タグ/除外/整合コピー/排他ロックが抜ける)
restic backup ~/foo --tag foo

## FORGET / PRUNE
restic forget --tag foo --dry-run --keep-within 7d
restic forget <ID>                      # 名指しで1本消す
restic prune                            # 参照されていないデータを実際に回収

## CHECK
restic check                            # 構造だけ (速い)
restic check --read-data                # 全パック実読み (数時間)
restic check --read-data-subset=1/12    # 1/12 だけ。月1で回せば年1周

## LOCK
restic list locks
restic cat lock <完全なID>               # {time, hostname, pid, ...}
restic unlock                           # stale なものを外す
restic unlock --remove-all              # 生きているものも含めて全部 (危険)

## KEY
restic key list | add | remove <ID>     # パスワードを追加 (複数持てる)

## THIS MACHINE (/Volumes/microSD/backup)
`./restic_backup.sh`                    # 全ターゲット。cron 用
`./restic_cleanup.sh`                   # 何が消えるか見るだけ (既定)
