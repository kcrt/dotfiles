#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
from pathlib import Path
import smtplib

from email.mime.text import MIMEText
from email.utils import formatdate

parser = argparse.ArgumentParser(
    description="Send mail with specified setting")
parser.add_argument("--subject", type=str,
                    help="Subject of mail", required=True)
parser.add_argument("--bodyfile", type=str, help="Body file", required=True)
parser.add_argument("--recipient", type=str, help="Recipient", required=True)
parser.add_argument("--fromaddr", type=str,
                    help="From (Address)", required=True)
parser.add_argument("--fromname", type=str, help="From (Name)", required=True)
parser.add_argument("--smtp", type=str, help="SMTP server", required=True)
parser.add_argument("--smtpport", type=str,
                    help="SMTP Server Port", default=587)
parser.add_argument("--smtpuser", type=str, help="SMTP ID", required=True)
parser.add_argument("--smtppass", type=str,
                    help="SMTP Password", required=True)
parser.add_argument("--dict", type=str, nargs='*',
                    help="Dictionary for mail body (e.g. 'name:山田'); use {name} for body template")
parser.add_argument('--printbody', default=False, action='store_true')
parser.add_argument('--no-printbody', dest='printbody', action='store_false')
parser.add_argument('--verbose', default=False, action='store_true')
args = parser.parse_args()


def main():

    body = Path(args.bodyfile).read_text()

    templatedict = {key: value for (key, value) in [
        pair.split(":") for pair in args.dict]}
    for key in templatedict:
        body = body.replace("{" + key + "}", templatedict[key])

    # -----
    print(f"From: {args.fromname} <{args.fromaddr}>")
    print(f"To: {args.recipient}")
    print(f"Subject: {args.subject}")
    print("-----")
    if(args.printbody):
        print("")
        print(body)
    # -----

    # メール本文の作成
    msg = MIMEText(body)
    msg["Subject"] = args.subject
    msg["From"] = args.fromaddr
    msg["To"] = args.recipient
    msg["Date"] = formatdate()
    if(args.verbose):
        print(msg)

    try:
        with smtplib.SMTP(args.smtp, args.smtpport) as smtp:
            smtp.starttls()
            smtp.login(args.smtpuser, args.smtppass)
            smtp.sendmail(args.fromaddr, args.recipient, msg.as_string())

        if args.verbose:
            print("done.")
    except smtplib.SMTPConnectError as err:
        print(f"Connection Error: {err}")
    except smtplib.SMTPAuthenticationError as err:
        print(f"Authentication Error: {err}")
    except smtplib.SMTPNotSupportedError as err:
        print(f"Unsupported method: {err}")
    except Exception as err:
        print(err)



if __name__ == '__main__':
    main()
