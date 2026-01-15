#
#	066-functions_ffmpeg.zsh
#		FFmpeg conversion functions
#

function ffmpeg_gif(){
	ffmpeg -i "$1" -an -r 15 -pix_fmt rgb24 -f gif "${1:t:r}.gif"
}
function ffmpeg_deinterlaced_mp4(){
	ffmpeg -i "$1" -vf "yadif=0:-1" -pix_fmt yuv420p "${1:t:r}.mp4"
}
function ffmpeg_480p_16:9_h264(){
	ffmpeg -i "$1" -vf scale=854:480 -c:v libx264 "${1:t:r} [480p h264].mp4"
}
function ffmpeg_480p_16:9_hevc(){
	ffmpeg -i "$1" -vf scale=854:480 -c:v libx265 "${1:t:r} [480p hevc].mp4"
}
function ffmpeg_480p_16:9_hevc_anime(){
	ffmpeg -i "$1" -vf scale=854:480 -c:v libx265 -tune animation "${1:t:r} [480p hevc].mp4"
}
function ffmpeg_720p_h264(){
	ffmpeg -i "$1" -vf scale=-1:720 -c:v libx264 "${1:t:r} [720p h264].mp4"
}
function ffmpeg_720p_hevc(){
	ffmpeg -i "$1" -vf scale=-1:720 -c:v libx265 "${1:t:r} [720p hevc].mp4"
}
function ffmpeg_720p_hevc_anime(){
	ffmpeg -i "$1" -vf scale=-1:720 -c:v libx265 -tune animation "${1:t:r} [720p hevc].mp4"
}
function ffmpeg_720p_av1(){
	ffmpeg -i "$1" -vf scale=-1:720 -c:v libsvtav1 "${1:t:r} [720p av1].mp4"
}
function ffmpeg_1080p_h264(){
	height=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=s=x:p=0 "$1")
	if [ "$height" -lt 1080 ]; then
		echo "height is less than 1080"
		return 1
	fi
	ffmpeg -i "$1" -vf scale=-1:1080 -c:v libx264 "${1:t:r} [1080p h264].mp4"
}
function ffmpeg_1080p_hevc_high_quality(){
	height=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=s=x:p=0 "$1")
	if [ "$height" -lt 1080 ]; then
		echo "height is less than 1080"
		return 1
	fi
	ffmpeg -i "$1" -vf scale=-1:1080 -c:v libx265 -x265-params crf=20 "${1:t:r} [1080p hevc].mp4"
}
function ffmpeg_1080p_hevc_default_quality(){
	height=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=s=x:p=0 "$1")
	if [ "$height" -lt 1080 ]; then
		echo "height is less than 1080"
		return 1
	fi
	ffmpeg -i "$1" -vf scale=-1:1080 -c:v libx265 "${1:t:r} [1080p hevc].mp4"
}
function ffmpeg_1080p_av1_default_quality(){
	height=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=s=x:p=0 "$1")
	if [ "$height" -lt 1080 ]; then
		echo "height is less than 1080"
		return 1
	fi
	ffmpeg -i "$1" -vf scale=-1:1080 -c:v libsvtav1 "${1:t:r} [1080p av1].mp4"
}
function ffmpeg_1080p_av1_high_quality(){
	height=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=s=x:p=0 "$1")
	if [ "$height" -lt 1080 ]; then
		echo "height is less than 1080"
		return 1
	fi
	ffmpeg -i "$1" -vf scale=-1:1080 -c:v libsvtav1 -crf 23 "${1:t:r} [1080p av1 crf23].mp4"
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
