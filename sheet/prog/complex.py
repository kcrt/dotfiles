#!/usr/bin/env python3

import cmath

# 複素数
# 虚数単位はj [[注意]]
z = 1 + 2j
z2 = z * z
print("z * z = {0} + {1}i".format(z2.real, z2.imag))  # => -3.0 + 4.0i

z3 = 3 + 0j         # 虚部が0の複素数型
z4 = complex(3, 0)  # complex()を使用しても良い

z.conjugate(), abs(z)   # 複素共役と絶対値
print(cmath.phase(z))   # 偏角
(abs_val, arg_val) = cmath.polar(z)
# cmath.rect()
# cmath.sqrt(), cmath.exp(), cmath.log(), ...
