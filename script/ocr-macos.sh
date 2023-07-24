#!/bin/bash
# from https://gist.github.com/rok-git/f2f3e58ca93e2fe69f92555f95fb3a4a


SCRIPTNAME=$(basename "$0")

function realpath () {
	f=$@;
	if [ -d "$f" ]; then
		base="";
		dir="$f";
	else
		base="/$(basename "$f")";
		dir=$(dirname "$f");
	fi;
	dir=$(cd "$dir" && /bin/pwd);
	echo "$dir$base"
}

function OCR () {
	/usr/bin/osascript <<EOF
use framework "Quartz"
use framework "Vision"
global CA, request
set CA to current application
set request to CA's VNRecognizeTextRequest's alloc's init
request's setRecognitionLevel:(CA's VNRequestTextRecognitionLevelAccurate)
request's setUsesLanguageCorrection:true
on ocrPDF(filePath, dpi)
	set doc to CA's PDFDocument's alloc's initWithURL:(CA's NSURL's fileURLWithPath:filePath)
	set pageCount to doc's pageCount
	set resultTexts to CA's NSMutableArray's new()
	repeat with i from 1 to pageCount
		set scaleFactor to (dpi / (72.0 * (CA's NSScreen's mainScreen's backingScaleFactor)))
		set pdfImageRep to (CA's NSPDFImageRep's imageRepWithData:((doc's pageAtIndex:(i - 1))'s dataRepresentation))
		set originalSize to pdfImageRep's |bounds|
		set originalWidth to CA's NSWidth(originalSize)
		set originalHeight to CA's NSHeight(originalSize)
		set scaledSize to CA's NSMakeSize(originalWidth * scaleFactor, originalHeight * scaleFactor)
		set targetRect to CA's NSMakeRect(0, 0, scaledSize's width, scaledSize's height)
		set image to (CA's NSImage's alloc's initWithSize:(targetRect's item 2))
		image's lockFocus()
		CA's NSColor's whiteColor's |set|()
		(CA's NSBezierPath's fillRect:targetRect)
		(pdfImageRep's drawInRect:targetRect)
		image's unlockFocus()
		set tiff to image's TIFFRepresentation
		set ocrText to my ocrTIFF(tiff)
		(resultTexts's addObject:ocrText)
	end repeat
	return (resultTexts's componentsJoinedByString:linefeed) as text
end ocrPDF
on ocrImage(filePath)
	set scaleFactor to CA's NSScreen's mainScreen's backingScaleFactor
	set bitmapImageRep to (CA's NSBitmapImageRep's imageRepWithData:((CA's NSImage's alloc's initWithContentsOfFile:(filePath))'s TIFFRepresentation))
	set srcSize to CA's NSMakeSize((bitmapImageRep's pixelsWide as real) / scaleFactor, (bitmapImageRep's pixelsHigh as real) / scaleFactor)
	set srcImage to (CA's NSImage's alloc's initWithSize:srcSize)
	srcImage's addRepresentation:bitmapImageRep
	set newImage to (CA's NSImage's alloc's initWithSize:srcSize)
	set targetRect to CA's NSMakeRect(0, 0, srcSize's width, srcSize's height)
	newImage's lockFocus()
	CA's NSColor's whiteColor's |set|()
	(CA's NSBezierPath's fillRect:targetRect)
	(srcImage's drawInRect:targetRect)
	newImage's unlockFocus()
	set tiff to newImage's TIFFRepresentation
	return my ocrTIFF(tiff)
end ocrImage
on ocrTIFF(tiff)
	set resultTexts to CA's NSMutableArray's new()
	set requestHandler to (CA's VNImageRequestHandler's alloc's initWithData:tiff options:(missing value))
	(requestHandler's performRequests:[request] |error|:(missing value))
	set results to request's results()
	repeat with aResult in results
		(resultTexts's addObject:(((aResult's topCandidates:1)'s objectAtIndex:0)'s |string|()))
	end repeat
	return (resultTexts's componentsJoinedByString:linefeed) as text
end ocrTIFF
on ocr(filePath, lang, dpi)
	if lang is "ja" then
		request's setRecognitionLanguages:["ja", "en"]
	else
		request's setRecognitionLanguages:["en"]
	end if
	set pathExtension to ((CA's NSString's stringWithString:filePath)'s pathExtension as text)
	if pathExtension is "pdf" then
		my ocrPDF(filePath, dpi)
	else
		my ocrImage(filePath)
	end if
end ocr
my ocr("$1", "$2", $3)
EOF
}

function usage() {
	echo "Usage: $SCRIPTNAME [--lang <LANG>] [--dpi <VALUE>] <input1> <input2> ..."
	echo
	echo "Input file types: pdf/jpg/png"
	echo "Options:"
	echo "  -h, --help      Show help"
	echo "  --lang <LANG>   Set OCR language (ja/en) (default: ja)"
	echo "  --dpi <VALUE>   Set DPI value for PDF rasterization (default: 200)"
	echo
}

# parse arguments
declare -a args=("$@")
declare -a params=()

LANG=ja
DPI=200

I=0
while [ $I -lt ${#args[@]} ]; do
	OPT="${args[$I]}"
	case $OPT in
		-h | --help )
			usage
			exit 0
			;;
		--lang )
			if [[ -z "${args[$(($I+1))]}" ]]; then
				echo "$SCRIPTNAME: option requires an argument -- $OPT" 1>&2
				exit 1
			fi
			LANG="${args[$(($I+1))]}"
			I=$(($I+1))
			;;
		--dpi )
			if [[ -z "${args[$(($I+1))]}" ]]; then
				echo "$SCRIPTNAME: option requires an argument -- $OPT" 1>&2
				exit 1
			fi
			DPI="${args[$(($I+1))]}"
			I=$(($I+1))
			;;
		-- | -)
			I=$(($I+1))
			while [ $I -lt ${#args[@]} ]; do
				params+=("${args[$I]}")
				I=$(($I+1))
			done
			break
			;;
		-*)
			echo "$SCRIPTNAME: illegal option -- '$(echo $OPT | sed 's/^-*//')'" 1>&2
			exit 1
			;;
		*)
			if [[ ! -z "$OPT" ]] && [[ ! "$OPT" =~ ^-+ ]]; then
				params+=( "$OPT" )
			fi
			;;
	esac
	I=$(($I+1))
done

# handle invalid arguments
if [ ${#params[@]} -eq 0 ]; then
	echo "$SCRIPTNAME: too few arguments" 1>&2
	echo "Try '$SCRIPTNAME --help' for more information." 1>&2
	exit 1
fi

for FILE in "${params[@]}"; do
	OCR "$(realpath $FILE)" $LANG $DPI
done
