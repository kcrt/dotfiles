#!/usr/bin/env python3

# 例: ./arg.py -a --hello --miso=soup aaa.txt

import sys
import argparse


# モジュールを使わない場合
sys.argv  # => ['./arg.py', '-a', '--hello', '--miso=soup', 'aaa.txt']


# 引数の解析には、C言語スタイルのgetoptと、より便利なargparseがある
# ここでは、argparseのみ記載する。

parser = argparse.ArgumentParser(description='Awesome python program.')
parser.add_argument('filename', metavar='file', type=str,
                    nargs='+', help='Your file to process.')
parser.add_argument('-a', '--apple', action='store_true',
                    help='If you like an apple.')
parser.add_argument('-b', '--banana', action='store_true',
                    help='If you like a banana.')
parser.add_argument('--hello', action='store_true',
                    help='Specify this if you want to say hello to others.')
parser.add_argument('--miso', nargs=1, required=True,
                    choices=['soup', 'grill'], help='Your favorite miso dish')
parser.add_argument('--version', action='version', version='%(prog)s v.0.1')
# %(prog)sでargv[0]を参照できる

args = parser.parse_args()

args.apple  # => True
args.filename   # => ['aaa.txt']

# action (抜粋)
#  store (省略可): 入力を格納
#  store_true, store_false: 指定されていたらTrue(またはFalse)を格納
#  append: リストに追加 (複数回指定する引数など)
#  count: 数を数える(--verboseを意味する-vなど。-vvvで3。)
#  help: ヘルプ表示
#  version: バージョン表示
#   例：parser.add_argument('--version', action='version', version='%(prog)s')

# nargs: 必要な引数の数, * - 何個でも, + - 最低1個、何個でも
# choices: 選択肢から選ぶ場合

# helpも自動で表示してくれる
# 例: ./arg.py --help

# see: https://docs.python.org/ja/3.8/library/argparse.html
# see: https://docs.python.org/ja/3.8/library/getopt.html

