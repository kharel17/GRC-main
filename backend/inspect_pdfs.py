import fitz
import os

uploads_dir = "uploads"
for f in os.listdir(uploads_dir):
    if f.endswith(".pdf"):
        path = os.path.join(uploads_dir, f)
        try:
            doc = fitz.open(path)
            print(f"File: {f}, Pages: {len(doc)}, Size: {os.path.getsize(path)}")
            # print first page text snippet
            if len(doc) > 0:
                txt = doc[0].get_text("text").strip()
                print("  Page 1 Snippet:", repr(txt[:150]))
        except Exception as e:
            print(f"Error reading {f}: {e}")
