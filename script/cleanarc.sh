#!/bin/zsh

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Recursively finds RAR files (*.rar) in the current directory and subdirectories,"
    echo "converts them to ZIP files, and then cleans the ZIP files by removing common unwanted files"
    echo "(e.g., .txt, .lnk, Thumbs.db, __MACOSX, .DS_Store)."
    echo "Requires 'parallel', '7zz', and 'zip' commands."
    exit 0
fi

# RAR 1 本を同名の ZIP に変換し、成功したら元の RAR を消す（parallel から呼ばれる）
# unrar は入れていないので arepack (atool) は使えず、7zz で展開して zip で固め直す
if [ "$1" = "--convert-one" ]; then
	rar_path="${2:A}"
	zip_path="${rar_path:r}.zip"
	if [ -e "$zip_path" ]; then
		echo "skip: $zip_path already exists" >&2
		exit 1
	fi
	# 展開先は RAR の隣に作る（書き込める場所であることが確実で、同じボリュームに収まる）
	work_dir="$(mktemp -d "${rar_path:h}/.cleanarc.XXXXXX")" || exit 1
	trap 'rm -rf "$work_dir"' EXIT
	7zz x -y -bso0 -bsp0 -o"$work_dir" -- "$rar_path" || exit 1
	(cd "$work_dir" && zip -qry -X "$zip_path" .) || { rm -f "$zip_path"; exit 1; }
	rm -- "$rar_path"
	exit 0
fi

autoload zmv

for required_command in parallel 7zz zip; do
	if ! command -v "$required_command" > /dev/null 2>&1; then
		echo "Please install $required_command first."
		exit 1
	fi
done

find . -name "*.rar" -print0 | parallel -0 -r --bar -j4 "${0:A}" --convert-one {}
failed_count=$?
if [ "$failed_count" -ne 0 ]; then
	echo "warning: failed to convert $failed_count RAR file(s); they were left as is." >&2
fi

for i in **/*.zip(N); do
	zip --delete "$i" "*.txt"
	zip --delete "$i" "*.lnk"
	zip --delete "$i" "*.url"
	zip --delete "$i" "*.Url"
	zip --delete "$i" "*.URL"
	zip --delete "$i" "Thumbs*.db"
	zip --delete "$i" "__MACOSX*"
	zip --delete "$i" ".DS_Store"
	zip --delete "$i" "_____padding_file_"
	zip --delete "$i" "_____padding_file_*____"
	zip --delete "$i" ".@__thumb/*" ".@__thumb/"
done

echo "finish!"
