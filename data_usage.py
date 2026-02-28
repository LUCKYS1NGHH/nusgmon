import psutil
import time
import sqlite3
from datetime import datetime

conn = sqlite3.connect("net_usage.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS data_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    bytes_sent INTEGER NOT NULL,
    bytes_recv INTEGER NOT NULL
)""")

old = psutil.net_io_counters()

def to_mb(_bytes):
    return _bytes / 1024 ** 2

while True:

    print("\nWait 3 seconds...\n")
    time.sleep(3)

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

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("INSERT INTO data_usage (timestamp, bytes_sent, bytes_recv) VALUES (?, ?, ?)",
        (int(time.time()), upload, download))
    conn.commit()

    old = new
