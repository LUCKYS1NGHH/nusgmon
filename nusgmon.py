#!/usr/bin/env python3
import psutil
import time
import sqlite3
from datetime import datetime
import argparse
import sys
import os
import signal
import json

DIR = os.path.expanduser("~/.nusgmon")
DB_FILE = os.path.join(DIR, "db.sqlite")
os.makedirs(DIR, exist_ok=True)

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS data_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    bytes_sent INTEGER NOT NULL,
    bytes_recv INTEGER NOT NULL
)""")


running = True
def handle_term(signum, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, handle_term)

def to_mb(_bytes):
    return _bytes / 1024 ** 2

def current_data_json_output(total_recv, total_sent, download, upload):
    """Just return the current data with pretty json"""

    output = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_bytes_sent': total_sent,
            'total_bytes_sent_mb': round(to_mb(total_sent)),
            'total_bytes_recv': total_recv,
            'total_bytes_recv_mb': round(to_mb(total_recv)),
            'download_kbps': download,
            'upload_kbps': upload
    }
    pretty = json.dumps(output, indent=3)
    return pretty


def log_net_usage(wait=None, dry_run=False, verbose=False, json_output=False):
    wait = 3 if wait is None else wait

    old = psutil.net_io_counters()
    count = 0

    while running:
        if verbose and not json_output:
            print(f"\nWait {wait} seconds...\n")
        time.sleep(wait)

        new = psutil.net_io_counters()

        if new.bytes_recv < old.bytes_recv or new.bytes_sent < old.bytes_sent:
            # reboot or interface reset
            old = new
            continue

        # speed calculate
        download = new.bytes_recv - old.bytes_recv
        upload = new.bytes_sent - old.bytes_sent

        if json_output:
            print(current_data_json_output(new.bytes_recv, new.bytes_sent, download, upload))

        elif verbose:
            print(f"{"-" * 8} {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {"-" * 8}")
            print(f"Total Megabytes Received : {round(to_mb(new.bytes_recv))} MB")
            print(f"Total Megabytes Sent     : {round(to_mb(new.bytes_sent))} MB")
            print(f"Download                 : {(download / wait) / 1024:.2f} KB/s")
            print(f"Upload                   : {(upload / wait) / 1024:.2f} KB/s")
            print("-" * 37)

        if not dry_run:
            count += 1
            cur.execute("INSERT INTO data_usage (timestamp, bytes_sent, bytes_recv) VALUES (?, ?, ?)",
                (int(time.time()), new.bytes_sent, new.bytes_recv))

            if count >= 50:
                conn.commit()
                count = 0

        old = new


def fetch_net_usage(today=False, thisweek=False):

    if today:
        rows = cur.execute("""
                SELECT 
                    COALESCE(SUM(bytes_sent), 0) AS total_sent,
                    COALESCE(SUM(bytes_recv), 0) AS total_recv
                FROM data_usage
                WHERE timestamp >= strftime('%s', 'now', 'start of day')
                AND timestamp <  strftime('%s', 'now', 'start of day', '+1 day');
            """).fetchall()
 
        if rows:
            upload, download = rows[0]

            print(f"{"-" * 5} Today {"-" * 5}")
            print(f"Upload   : {round(to_mb(upload))} MB")
            print(f"Download : {round(to_mb(download))} MB")
            print("-"*17)

    elif thisweek:
        rows = cur.execute("""
                SELECT
                    COALESCE(SUM(bytes_sent), 0),
                    COALESCE(SUM(bytes_recv), 0)
                FROM data_usage
                WHERE timestamp >= strftime('%s', 'now', 'weekday 0', '-6 days')
                AND timestamp <  strftime('%s', 'now', 'weekday 0', '+1 day');
            """).fetchall()

        if rows:
            upload, download = rows[0]

            print(f"{"-" * 6} This Week {"-" * 6}")
            print(f"Upload   : {round(to_mb(upload))} MB")
            print(f"Download : {round(to_mb(download))} MB")
            print("-"*23)


parser = argparse.ArgumentParser(
    prog="nusgmon",
    description=(
        "Network usage monitoring tool\n"
        "Record live bandwidth usage.\n"
    ), formatter_class=argparse.RawTextHelpFormatter)

subparsers = parser.add_subparsers(dest="command")
record_parser = subparsers.add_parser("record")

record_parser.add_argument("-w", "--wait", type=float, help="record after certain seconds (default: 3)")
record_parser.add_argument("-d", "--dry-run", action="store_true", help="prevent logging to database")
record_parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
record_parser.add_argument("--json", action="store_true", help="output data JSON format")

parser.add_argument("--today", action="store_true", help="show today's usage")
parser.add_argument("--thisweek", action="store_true", help="show this week's usage")
parser.add_argument("-V", "--version", action="version", version="1.0.0")

args = parser.parse_args()


if args.command == "record":
    try:
        log_net_usage(args.wait, args.dry_run, args.verbose, args.json)
    finally:
        conn.commit()
        conn.close()

elif args.today:
    fetch_net_usage(today=args.today)

elif args.thisweek:
    fetch_net_usage(thisweek=args.thisweek)
