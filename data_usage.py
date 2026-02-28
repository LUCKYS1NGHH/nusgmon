import psutil
import time

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

    old = new
