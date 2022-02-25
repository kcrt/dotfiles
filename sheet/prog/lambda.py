#!/usr/bin/env python3

from math import sqrt
from functools import partial


pythagoras = lambda a, b: sqrt(a ** 2 + b ** 2)
pythagoras(3, 4)

pythagoras3 = partial(pythagoras, a=3)
pythagoras3(b = 4)

# クラスメソッドにはpartialmethod
