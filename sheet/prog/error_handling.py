#!/usr/bin/env python3


# Python 2 と 3では構文が違うので要注意

try:
    print("Hello world.")
    raise ValueError("Value Error!")
except (ValueError, ZeroDivisionError) as err:
    print("Invalid value: {0}".format(err))
except OSError:
    print("Strange OS Error")
except:
    # その他のすべてのエラー (非推奨)
    print("Unknown error")
    raise
else:
    # エラーがなかった場合
    print("There is no error!")
finally:
    # エラーがあってもなくても
    print("Operation finished.")

# ユーザー定義例外
# Exceptionから派生させる
class MySpecialError(Exception):
    pass

# 主な例外(抜粋)
# ArithmeticError(FloatingPointError, OverflowError, ZeroDivisionError), AssertionError, AttributeError, BufferError, EOFError, ImportError, LookupError(IndexError, KeyError), MemoryError, NameError, OSError(ConnectionError, FileExistsError, FileNotFoundError, PermissionError), ReferenceError, RuntimeError(NotImplementedError), SystemError, TypeError, ValueError(UnicodeError)
# 例外の一覧は see: https://docs.python.jp/3/library/exceptions.html#exception-hierarchy 

# Warning(DeprecationWarning, RuntimeWarning, UserWarning, FutureWarning)に関しては see: https://docs.python.jp/3/library/warnings.html
