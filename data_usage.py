import psutil

data = psutil.net_io_counters()

def to_mb(_bytes):
    return _bytes / 1024 ** 2

mb_sent = to_mb(data.bytes_sent)
mb_recv = to_mb(data.bytes_recv)

print(f"Megabytes sent: {round(mb_sent)}M")
print(f"Megabytes received: {round(mb_recv)}M")
