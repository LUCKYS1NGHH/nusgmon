import psutil

data = psutil.net_io_counters()

mb_sent = data.bytes_sent / 1024 ** 2
mb_recv = data.bytes_recv / 1024 ** 2

print(f"Megabytes sent: {mb_sent:.2f}M")
print(f"Megabytes received: {mb_recv:.2f}M")
