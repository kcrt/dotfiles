#!/bin/sh

if [[ "$#" != 3 ]]; then
	echo "$0 <aud> <duration(min.)> <privatekey>"
	exit
fi

AUD=$1
DURATION=$2
PRIVATEKEY=$3

NOW=`date +%s`
EXP=$(($NOW + $DURATION * 60))

HEADER=`echo '{"typ":"JWT","alg":"RS256"}' | openssl enc -base64 | tr -d '[=\n]' | tr '+/' '-/'`
PAYLOAD=`echo "{\"iat\":$NOW,\"exp\":$EXP,\"aud\":\"$AUD\"}" | openssl enc -base64 | tr -d '[=\n]' | tr '+/' '-_'`

SIGNATURE=`/bin/echo -n "${HEADER}.${PAYLOAD}" | openssl dgst -sha256 -binary -sign $PRIVATEKEY | openssl enc -base64 | tr -d '[=\n]' | tr '+/' '-_'`

/bin/echo -n "${HEADER}.${PAYLOAD}.${SIGNATURE}"
