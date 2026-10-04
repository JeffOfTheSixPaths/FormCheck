import sqlite3
from pathlib import Path

db_path = Path("formcheck.db")
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Find rows where user_id IS NULL (seeded pro references)
cursor.execute("SELECT id, title, category, file_path, thumbnail_path FROM uploaded_videos WHERE user_id IS NULL")
rows = cursor.fetchall()
print(f"Found {len(rows)} seeded pro reference rows to delete:")
for r in rows:
    print(f"  ID {r[0]}: {r[1]} -> {r[3]}")

# Delete from database
cursor.execute("DELETE FROM uploaded_videos WHERE user_id IS NULL")
conn.commit()
print(f"\nDeleted {cursor.rowcount} rows from uploaded_videos.")

# Verify remaining rows
cursor.execute("SELECT id, user_id, title, category, file_path FROM uploaded_videos")
remaining = cursor.fetchall()
print(f"\nRemaining {len(remaining)} uploaded videos (all locally uploaded by users):")
for r in remaining:
    print(f"  ID {r[0]} (User {r[1]}): [{r[3]}] {r[2]} -> {r[4]}")

conn.close()

# Clean up un-uploaded dummy files on disk
pro_dir = Path("server_storage/pro")
thumb_dir = Path("server_storage/thumbnails")
geom_dir = Path("server_storage/geometry")
sig_dir = Path("server_storage/signatures")

for p in pro_dir.glob("pro_*.mp4"):
    print(f"Removing dummy video: {p}")
    p.unlink(missing_ok=True)

for p in thumb_dir.glob("thumb_pro_*.jpg"):
    print(f"Removing dummy thumbnail: {p}")
    p.unlink(missing_ok=True)

for p in geom_dir.glob("pro_*_geometry.json"):
    print(f"Removing dummy geometry cache: {p}")
    p.unlink(missing_ok=True)

for p in sig_dir.glob("pro_*_sig.json"):
    print(f"Removing dummy signature cache: {p}")
    p.unlink(missing_ok=True)

print("\nCleanup completed successfully.")
