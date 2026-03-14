#!/usr/bin/env python3
import psutil
import time
import sqlite3
from datetime import datetime, timedelta
import argparse
import sys
import os
import signal
import json
from collections import defaultdict


BLUE = "\033[94m"
GREEN = "\033[32m"
RESET = "\033[0m"


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

def to_gb(_bytes):
    return _bytes / (1024 ** 3)

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

def calculate_usage(rows):
    total_upload = 0
    total_download = 0

    for i in range(1, len(rows)):
        prev_sent, prev_recv = rows[i-1]
        curr_sent, curr_recv = rows[i]

        if curr_sent >= prev_sent:
            total_upload += curr_sent - prev_sent

        if curr_recv >= prev_recv:
            total_download += curr_recv - prev_recv

    return total_upload, total_download

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


def draw_graph(data, title, total, gb_show=False):
    max_val = max(
        max(v["up"], v["down"]) for v in data.values()
    ) if data else 0

    width = 32
    scale = max_val / width if max_val > width else 1

    print(f"\n  {title}")
    print(" ", "-" * (len(title) + 2))
    print(f"  {GREEN}█ Upload{RESET}  {BLUE}█ Download{RESET}\n")

    unit = "GB" if gb_show else "MB"

    for label, val in data.items():
        up = val["up"]
        down = val["down"]

        up_bar = "█" * int(up / scale)
        down_bar = "█" * int(down / scale)

        print(
            f"{label:>5} "
            f"{GREEN}{up_bar}{RESET}"
            f"{BLUE}{down_bar}{RESET} "
            f"{up:>6.2f}↑ {down:>6.2f}↓ {unit}"
        )

    print(f"\nTotal: {total['up']:.2f}↑ {total['down']:.2f}↓ {unit}")


def fetch_net_usage(today=False, thisweek=False, month=False, json_output=False, gb_show=False):
    rows = cur.execute("""
        SELECT timestamp, bytes_sent, bytes_recv
        FROM data_usage
        ORDER BY timestamp ASC
    """).fetchall()

    if len(rows) < 2:
        print("Not enough data.")
        return

    buckets = defaultdict(lambda: {"up": 0, "down": 0})
    total_up = 0
    total_down = 0
    now = datetime.now()

    for i in range(1, len(rows)):
        t1, s1, r1 = rows[i - 1]
        t2, s2, r2 = rows[i]

        up = max(0, s2 - s1)
        down = max(0, r2 - r1)

        dt = datetime.fromtimestamp(t2)

        if today:
            if dt.date() != now.date():
                continue
            key = f"{dt.hour:02d}:00"

        elif thisweek:
            start_of_week = now - timedelta(days=now.weekday())
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_week = start_of_week + timedelta(days=7)

            if not (start_of_week <= dt < end_of_week):
                continue

            key = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]

        elif month:
            if dt.year != now.year or dt.month != now.month:
                continue
            key = str(dt.day)

        else:
            continue

        buckets[key]["up"] += up
        buckets[key]["down"] += down

        total_up += up
        total_down += down

    convert = to_gb if gb_show else to_mb

    data = {
        k: {
            "up": convert(v["up"]),
            "down": convert(v["down"])
        }
        for k, v in buckets.items()
    }

    if not data:
        print("No data for this period.")
        return

    if today:
        title = "Today Usage"
        data = dict(sorted(data.items()))

    elif thisweek:
        title = "This Week Usage"
        order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        data = {d: data[d] for d in order if d in data}

    else:
        title = f"Month {now.month} Usage"
        data = dict(sorted(data.items(), key=lambda x: int(x[0])))

    total = {
        "up": round(convert(total_up), 2),
        "down": round(convert(total_down), 2)
    }

    if json_output:
        data["total"] = [total]
        pretty = json.dumps(data, indent=3)
        print(pretty)
    else:
        draw_graph(data, title, total, gb_show=gb_show)


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
parser.add_argument("--month", nargs="?", const=datetime.now().month, type=int, choices=range(1, 13), help="show any month's usage (default: current month)")
parser.add_argument("--json", action="store_true", help="output data JSON format")
parser.add_argument("-g", "--gigabyte", action="store_true", help="show data usage in giga byte (GB)")
parser.add_argument("-V", "--version", action="version", version="1.0.0")

args = parser.parse_args()


if args.command == "record":
    try:
        log_net_usage(args.wait, args.dry_run, args.verbose, args.json)
    finally:
        conn.commit()
        conn.close()

elif args.today:
    fetch_net_usage(today=args.today, json_output=args.json, gb_show=args.gigabyte)

elif args.thisweek:
    fetch_net_usage(thisweek=args.thisweek, json_output=args.json, gb_show=args.gigabyte)

elif args.month:
    fetch_net_usage(month=args.month, json_output=args.json, gb_show=args.gigabyte)

else:
    fetch_net_usage(today=True, json_output=args.json, gb_show=args.gigabyte)
