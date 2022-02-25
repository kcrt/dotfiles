#!/usr/bin/env python3

import logging

# 標準はstdout, WARNING
logging.basicConfig(filename="app.log",
                    level=logging.DEBUG,    # ログレベル
                    format="[%(created)f] %(message)s")
                    # format="[%(levelname)s] %(message)s")
# format
# %(messages): ログメッセージ
# %(asctime)s: 可読な時間
# %(created)f: epochよりの時間
# exc_info: 例外情報
# %(levelname)s: ログレベル
# %(levelno)s: ログレベル(数値)
# %(filename)s: 呼び出ししたファイル名
# %(pathname)s: フルパス
# %(module)s: モジュール名
# %(funcName)s: 関数名
# %(lineno)d: 行番号
# %(process)d: プロセスID
# %(processNmae)s: プロセス名
# %(thread)d: スレッドID
# %(threadNmae)s: スレッド名
# %(name)s: loggerの名前

logging.critical("critical")
logging.error("error")
logging.warning("warning")
logging.info("info")
logging.debug("debug")
logging.exception("exception")  # 例外時のみ、トレースを出力

# 個別の名前付きロガーを作ることも出来る
myLogger = logging.getLogger("Special")
