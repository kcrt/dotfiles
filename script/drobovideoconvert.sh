#!/bin/zsh

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Converts video files (MP4, MTS) found in /Volumes/HomeVideo/CamTemp/(DCIM|AVCHD)/"
    echo "to H.264 MP4 format (1920x1080, AAC audio 256k) and saves them to /Volumes/HomeVideo/Converted/."
    echo "It also creates a smaller version (960x540, AAC audio 128k) in /Volumes/HomeVideo/ConvertedMini/."
    echo "The script checks if /Volumes/HomeVideo/ is mounted and if output files already exist to avoid reconversion."
    echo "Requires ffmpeg."
    exit 0
fi

if [[ ! -e /Volumes/HomeVideo/ ]]; then
	echo "/Volumes/HomeVideo/ not mounted"
	exit 1 # Changed to exit 1 for error
fi

rm /Volumes/HomeVideo/Converted/*.converting.mp4
rm /Volumes/HomeVideo/ConvertedMini/*.converting.mp4
rm /Volumes/HomeVideo/HEVC/*.converting.mp4

for i in /Volumes/HomeVideo/CamTemp/(DCIM|AVCHD)/**/*.(MP4|MTS); do
	echo "processing $i..."
	basename=${i:t}
	basename=${basename:r}
	if [[ ! -e /Volumes/HomeVideo/Converted/$basename.mp4 ]]; then
		echo "converting $basename"
		nice ffmpeg -i $i -s 1920x1080 -vcodec libx264 -acodec aac -ac 2 -ab 256k /Volumes/HomeVideo/Converted/$basename.converting.mp4
		mv /Volumes/HomeVideo/Converted/$basename.converting.mp4 /Volumes/HomeVideo/Converted/$basename.mp4
	fi
	if [[ ! -e /Volumes/HomeVideo/ConvertedMini/$basename.mp4 ]]; then
		echo "converting minisize of $basename"
		nice ffmpeg -i /Volumes/HomeVideo/Converted/$basename.mp4 -s 960x540 -vcodec libx264 -acodec aac -ac 2 -ab 128k /Volumes/HomeVideo/ConvertedMini/$basename.converting.mp4
		mv /Volumes/HomeVideo/ConvertedMini/$basename.converting.mp4 /Volumes/HomeVideo/ConvertedMini/$basename.mp4
	fi
	# HEVC is too heavy for now
	#if [[ ! -e /Volumes/HomeVideo/HEVC/$basename.mp4 ]]; then
	#	echo "converting HEVC version of $basename"
	#	nice ffmpeg -i $i -s 960x540 -vcodec hevc -acodec aac -ac 2 -ab 128k /Volumes/HomeVideo/HEVC/$basename.converting.mp4 < /dev/null
	#	mv /Volumes/HomeVideo/HEVC/$basename.converting.mp4 /Volumes/HomeVideo/HEVC/$basename.mp4
	#fi
done
# rsync -vru --progress --stats --human-readable /Volumes/HomeVideo/ConvertedMini ~/nosync/
# rsync -vru --progress --stats --human-readable /Volumes/HomeVideo/HEVC /nosync/
