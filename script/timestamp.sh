#!/bin/sh

# RFC 3161 TSA. All of the below are free and need no registration.
# (sha256timestamp.ws.symantec.com is dead as of 2026-09; DigiCert took it over)
TSA="http://timestamp.digicert.com"
#TSA="http://timestamp.sectigo.com"
#TSA="http://time.certum.pl"
#TSA="http://timestamp.apple.com/ts01"
#TSA="http://zeitstempel.dfn.de"
#TSA="https://freetsa.org/tsr"  # needs FreeTSA's own cacert.pem as CAFILE

# Trust anchors used to verify the reply. The TSAs above (except FreeTSA)
# chain up to roots present in the system bundle.
CAFILE="${TIMESTAMP_CAFILE:-/etc/ssl/cert.pem}"

usage() {
	cat <<EOM
Usage: ${0##*/} filename [tsrfile]
       ${0##*/} -h | --help

Create an RFC 3161 timestamp for a file, then show and verify the reply.

Arguments:
  filename   File to be timestamped.
  tsrfile    Path of the timestamp reply to write (default: <filename>.tsr).

Options:
  -h, --help Show this help and exit.

TSA in use: ${TSA}
CA bundle:  ${CAFILE} (override with \$TIMESTAMP_CAFILE)
EOM
}

case ${1-} in
	-h | --help)
		usage
		exit 0
		;;
esac

if [ $# = 1 ]; then
	FILENAME=$1
	TSRFILE="$1.tsr"
elif [ $# = 2 ]; then
	FILENAME=$1
	TSRFILE=$2
else
	usage >&2
	exit 1
fi

openssl ts -query -data "$FILENAME" -sha256 -cert | curl -o "$TSRFILE" -sSH 'Content-Type: application/timestamp-query' --data-binary @- "$TSA"
openssl ts -reply -in "$TSRFILE" -text
echo "---"
openssl ts -verify -in "$TSRFILE" -data "$FILENAME" -CAfile "$CAFILE"
