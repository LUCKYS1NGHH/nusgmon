import psutil
import time
import sqlite3
from datetime import datetime
import argparse
import sys

conn = sqlite3.connect("net_usage.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS data_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    bytes_sent INTEGER NOT NULL,
    bytes_recv INTEGER NOT NULL
)""")

def to_mb(_bytes):
    return _bytes / 1024 ** 2

def log_net_usage(wait=None, dry_run=None):
    wait = 3 if wait is None else wait

    old = psutil.net_io_counters()

    while True:
        print(f"\nWait {wait} seconds...\n")
        time.sleep(wait)

        new = psutil.net_io_counters()

        # speed calculate
        download = new.bytes_recv - old.bytes_recv
        upload = new.bytes_sent - old.bytes_sent

        print("-" * 40)

        print(f"Total Megabytes Received : {round(to_mb(new.bytes_recv))} MB")
        print(f"Total Megabytes Sent     : {round(to_mb(new.bytes_sent))} MB")

        print(f"Download                 : {download / 1024:.2f} KB/s")
        print(f"Upload                   : {upload / 1024:.2f} KB/s")

        print("-" * 40)

        if not dry_run:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("INSERT INTO data_usage (timestamp, bytes_sent, bytes_recv) VALUES (?, ?, ?)",
                (int(time.time()), upload, download))
            conn.commit()

        old = new

parser = argparse.ArgumentParser()

subparsers = parser.add_subparsers(dest="command")
record_parser = subparsers.add_parser("record")

record_parser.add_argument("-w", "--wait", type=float, help="record after certain seconds (default: 3)")
record_parser.add_argument("-d", "--dry-run", action="store_true", help="prevent logging to database")
args = parser.parse_args()

if args.command == "record":
    try:
        log_net_usage(args.wait, args.dry_run)
    except KeyboardInterrupt:
        sys.exit(130)
