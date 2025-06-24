#!/bin/bash

# iCalendarファイル生成スクリプト
# macOSとUbuntuで動作します

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Interactively creates an iCalendar (.ics) file and a Google Calendar link."
    echo "Prompts for event title, location, description, start time, and end time."
    echo "The .ics file is saved in ~/Downloads/."
    exit 0
fi

# イベントタイトルを取得
echo "イベントのタイトルを入力してください："
read title

# タイトルが空の場合のデフォルト値設定
if [ -z "$title" ]; then
  title="新規イベント"
fi

# ファイル名を生成（スペースをアンダースコアに置換）
filename=~/Downloads/"$(echo "$title" | tr ' ' '_').ics"

# 場所の取得
echo "場所を入力してください（省略可能）："
read location

# 説明の取得
echo "説明を入力してください（省略可能）："
read description

# 開始日時と終了日時のフォーマット指示
echo "開始日時を入力してください（YYYY-MM-DD HH:MM 形式）："
read start_datetime

# 日時形式の検証と変換
if [[ ! $start_datetime =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}$ ]]; then
  echo "無効な日時形式です。YYYY-MM-DD HH:MM 形式で入力してください。"
  exit 1
fi

# 終了日時の入力
echo "終了日時を入力してください（YYYY-MM-DD HH:MM 形式）："
read end_datetime

# 日時形式の検証と変換
if [[ ! $end_datetime =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}$ ]]; then
  echo "無効な日時形式です。YYYY-MM-DD HH:MM 形式で入力してください。"
  exit 1
fi

# iCalフォーマット用に日時を変換（タイムゾーン情報を含む）
start_year=$(echo $start_datetime | cut -d'-' -f1)
start_month=$(echo $start_datetime | cut -d'-' -f2)
start_day=$(echo $start_datetime | cut -d'-' -f3 | cut -d' ' -f1)
start_hour=$(echo $start_datetime | cut -d' ' -f2 | cut -d':' -f1)
start_minute=$(echo $start_datetime | cut -d':' -f2)

end_year=$(echo $end_datetime | cut -d'-' -f1)
end_month=$(echo $end_datetime | cut -d'-' -f2)
end_day=$(echo $end_datetime | cut -d'-' -f3 | cut -d' ' -f1)
end_hour=$(echo $end_datetime | cut -d' ' -f2 | cut -d':' -f1)
end_minute=$(echo $end_datetime | cut -d':' -f2)

echo "タイムゾーン: JST が使用されます"
tz="Asia/Tokyo"

now=$(date -u +"%Y%m%dT%H%M%SZ")

# iCalフォーマット用に開始日時と終了日時を変換
start_ical="${start_year}${start_month}${start_day}T${start_hour}${start_minute}00"
end_ical="${end_year}${end_month}${end_day}T${end_hour}${end_minute}00"

# Google Calendar用のUTC形式の日時を生成
# 日本時間からUTCへの変換（-9時間）
start_hour_utc=$((10#$start_hour - 9))
end_hour_utc=$((10#$end_hour - 9))

# 日付の調整（時間が負になった場合は前日にする）
start_day_utc=$start_day
end_day_utc=$end_day

if [ $start_hour_utc -lt 0 ]; then
  start_hour_utc=$((start_hour_utc + 24))
  # 前日の日付を計算（簡易版）
  # 注：月末日処理は複雑なため、この簡易スクリプトでは省略
  start_day_utc=$((10#$start_day - 1))
fi

if [ $end_hour_utc -lt 0 ]; then
  end_hour_utc=$((end_hour_utc + 24))
  # 前日の日付を計算（簡易版）
  end_day_utc=$((10#$end_day - 1))
fi

# 桁合わせ
if [ $start_hour_utc -lt 10 ]; then start_hour_utc="0$start_hour_utc"; fi
if [ $end_hour_utc -lt 10 ]; then end_hour_utc="0$end_hour_utc"; fi
if [ $start_day_utc -lt 10 ]; then start_day_utc="0$start_day_utc"; fi
if [ $end_day_utc -lt 10 ]; then end_day_utc="0$end_day_utc"; fi

# Google Calendar用の日時形式を作成
start_gc="${start_year}${start_month}${start_day_utc}T${start_hour_utc}${start_minute}00Z"
end_gc="${end_year}${end_month}${end_day_utc}T${end_hour_utc}${end_minute}00Z"

# ユニークIDの生成
uid=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || echo "$(date +%s)-$(od -An -N4 -t x4 /dev/urandom | tr -d ' ')")

# iCalendarファイルの作成
cat > "$filename" << EOF
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//hacksw/handcal//NONSGML v1.0//EN
CALSCALE:GREGORIAN
BEGIN:VEVENT
UID:${uid}
DTSTAMP:${now}
DTSTART;TZID=${tz}:${start_ical}
DTEND;TZID=${tz}:${end_ical}
SUMMARY:${title}
LOCATION:${location}
DESCRIPTION:${description}
END:VEVENT
END:VCALENDAR
EOF

# URLエンコードした変数を準備
encoded_title=$(echo "$title" | python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip()))")
encoded_location=$(echo "$location" | python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip()))")
encoded_description=$(echo "$description" | python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip()))")

# Google Calendarのリンクを生成
gcal_link="https://calendar.google.com/calendar/r/eventedit?text=${encoded_title}&dates=${start_gc}/${end_gc}&location=${encoded_location}&details=${encoded_description}"

echo "iCalendarファイル「$filename」が正常に作成されました。"
echo "このファイルはApple Calendarなどのカレンダーアプリにインポートできます。"
echo ""
echo "Google Calendarに追加するためのリンク："
echo "$gcal_link"
