#!/usr/bin/env python3

import sys
import math
from decimal import Decimal
from fractions import Fraction

# 変数の宣言は不要
# 基本は型なし
v = 1
v = "a"

# [[Python 3.5]] 型ヒントもサポートされている (see: typing)
# str, int, float, List[A], Dict[A, B], Tuple[A, B], Union[A, B], Optional[A], Callable[[ARG_A, ARG_B, ...], RETTYPE], Any
helloMessage: str = "Hello, world"
numApple: int = 32
tempToday: float = 37.2

strangeValue: int = "Strange!"  # ...が、今のところ何をしている訳でもない…

# 整数
# Python 2ではintとlongがあったが、Python 3 ではint(上限なし)のみ
v = 1000000000000000000000000000000000000

# 浮動小数点: float(倍精度)のみ
f = 1.234
float('nan')          # または、math.nan
inf = float('inf')    # または、math.inf
print(math.isinf(inf))
# 他に、math.isfinite, math.isinf, math.isnan
a = 0.24
print(f"{a:f} {a:e} {a:g} {a:%}")
print("{0:e}".format(a))




# 論理型(bool)
False and True

# 定数
PI = 3.14               # 定数はない。慣習的に大文字を使う。

# intは上限・下限がないので、CのようなINT_MAX的な物はない。
print(sys.float_info.epsilon)   # DBL_EPSILON
print(sys.float_info.max, sys.float_info.min)  # DBL_MAX, DBL_MIN

# 言語固有
# 10進数を正確に表せるDecimal型
Decimal("1.1")          # ちょうど1.1
Decimal(1.1)            # floatの1.1は2進数で表せる近い数値( != "1.1")

# 分数型
Fraction(2, 3)   # => 2/3
Fraction(5, 10)  # => 1/2 (約分される)
Fraction(1.1)    # => [注意] 11/10ではない！
Fraction(Decimal("1.1"))    # => 11/10
float(Fraction(1, 3))  # => 0.33333...

# 型を調べる
type(v)      # => <class 'int'>
isinstance(v, int)  # => True


from decimal import Decimal, getcontext
getcontext().prec = 100
print(Decimal("1.20") * Decimal("2.30"))
print(Decimal("1") / Decimal("7"))
