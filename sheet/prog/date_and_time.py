#!/usr/bin/env python3

from datetime import (datetime, date, timedelta, timezone)
import time
import calendar
import locale

# == 型 ==
# datetime.date, datetime.time, datetime.datetime
# 時間の差分情報としてdatetime.timedelataが使用される
# C言語と同様の使用できるtime.struct_timeもある

# == 現在の日付と時刻 ==
date.today()  # 日付のみ(date型)
datetime.today()  # 日付と時刻(datetime型)
nowvar = datetime.now()  # todayと同じだが環境によっては高精度


# == オブジェクトの生成 ==
bday = date(1984, 9, 24)  # 日付のみ、月は1-12で指定
btime = datetime(1984, 9, 24, 12, 3, 24)
btime = datetime.strptime("1984/09/24 12:03:24", "%Y/%m/%d %H:%M:%S")

# == オブジェクトからのアイテムの取得 ==
print(btime.year, btime.month, btime.day, btime.hour,
      btime.minute, btime.second, btime.microsecond)

# == 曜日 ==
btime.weekday()  # Mon = 0, ..., Sun = 6
btime.isoweekday()  # Mon = 1, ..., Sun = 7

# == Unix time ==
time.time()  # 現在の時刻 (sec)
birth_epoch = btime.timestamp()  # Unix timeへ
datetime.fromtimestamp(birth_epoch)  # Unix timeから

# == プロセッサー時間・高分解能時間 ==
# time.clock() は3.3で撤廃された
time.monotonic()  # モノトニッククロック(sec) - 必ず時間が増加する
time.perf_counter()  # (sec, flaot) 高分解能
time.perf_counter_ns()  # (ns, int)
time.process_time()  # (sec, float) プロセスごとのCPU時間
time.process_time_ns()  # (ns, int)

# == 時間の計算 ==
delta = btime - nowvar  # 差でtimedeltaを取得
print(nowvar + delta)  # timedeltaは演算に使える
delta.total_seconds()  # 長さを秒で取得
mydelta = timedelta(seconds=30)  # 30秒間を示すオブジェクト

# == 時差関連 ==
# 時差情報をもったawareともっていないnaiveがある
utc_naive = datetime.utcnow()  # naiveを返す
utc_aware = datetime.now(timezone.utc)  # awareを返す
my_utc_naive = utc_aware.replace(tzinfo=None)  # tzinfoを外すとnaiveになる
btime.astimezone(tz=timezone.utc)

# == 文字列へ ==
btime.isoformat()  # "1984-09-24T12:03:24"
btime.strftime("%Y/%m/%d %H:%M:%S")  # man strftime参照

# == その他 ==
calendar.isleap(2018)   # 閏年か
calendar.prcal(2018)    # カレンダー表示
list(calendar.day_name)  # ['Monday', 'Tuesday', 'Wednesday', ...]
list(calendar.day_abbr)  # ['Mon', 'Tue', 'Wed', ...]
list(calendar.month_name)     # => ['', 'January', 'February', 'March', ...]
list(calendar.month_abbr)     # => ['', 'Jan', 'Feb', 'Mar', ...]

locale.setlocale(locale.LC_ALL, 'ja_JP')
list(calendar.day_name)  # => ['月曜日', '火曜日', '水曜日' ...]

time.sleep(5)  # 5秒スリープ
