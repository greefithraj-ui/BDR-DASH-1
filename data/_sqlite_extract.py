"""Minimal SQLite query - just get serials and dates."""
import sqlite3
conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=120)
cur = conn.cursor()
cur.execute("SELECT LOWER(serial_number), MIN(saved_at), MAX(saved_at), COUNT(*) FROM archive_entries GROUP BY LOWER(serial_number)")
with open(r"C:\Users\meshe\AppData\Local\Temp\sqlite_summary.txt", "w") as f:
    for row in cur:
        f.write(f"{row[0]}\t{row[1]}\t{row[2]}\t{row[3]}\n")
conn.close()
print("Done")
