#
#	066-functions_ffmpeg.zsh
#		FFmpeg conversion functions
#
# Simple video conversion functions have been replaced by script/ffmpeg_convert.py
# Usage: ffmpeg_convert.py input.mp4 -s 720p -c hevc -q high [--tune animation]
#

function ffmpeg_gif(){
	ffmpeg -i "$1" -an -r 15 -pix_fmt rgb24 -f gif "${1:t:r}.gif"
}
function ffmpeg_deinterlaced_mp4(){
	ffmpeg -i "$1" -vf "yadif=0:-1" -pix_fmt yuv420p "${1:t:r}.mp4"
}
function use_for_regza(){
	ffmpeg -i "$1" -f mpegts -c:v libx265 -c:a aac "/Volumes/REGZA/${1:t:r}.ts"
}
function use_for_regza_withoutconvert(){
	ffmpeg -i "$1" -f mpegts -vcodec copy -acodec copy "/Volumes/REGZA/${1:t:r}.ts"
}
function ffmpeg_maximize(){
	MAXVOL=`ffmpeg -i "$1" -vn -af volumedetect -f null - 2>&1 | grep max_volume | sed "s/.*max_volume: -//" | sed "s/ dB//"`
	ffmpeg -i "$1" -af volume=${MAXVOL}dB "${1:t:r}_maximized.${1:e}"
}
