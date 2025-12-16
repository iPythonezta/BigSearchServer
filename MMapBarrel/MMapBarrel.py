import mmap
import ormsgpack
import json
import os


class MMapBarrel:
    def __init__(self, barrel_dir):
        self.barrel_dir = barrel_dir

        with open(os.path.join(barrel_dir, "offsets.json"), "r") as f:
            self.offsets = json.load(f)

        self.file = open(os.path.join(barrel_dir, "postings.bin"), "rb")
        self.mmap = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)

    def get_posting(self, word_index):
        offset, size = self.offsets[str(word_index)]
        blob = self.mmap[offset: offset + size]
        return ormsgpack.unpackb(blob)

    def _close_mmap(self):
        if self.mmap:
            self.mmap.close()
        if self.file:
            self.file.close()

    def _reopen_mmap(self):
        self.file = open(os.path.join(self.barrel_dir, "postings.bin"), "rb")
        self.mmap = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)

    def merge_new_data(self, data: dict, word_to_index: dict):
        postings_path = os.path.join(self.barrel_dir, "postings.bin")
        offsets_path = os.path.join(self.barrel_dir, "offsets.json")

        # ---- CLOSE mmap BEFORE TOUCHING FILE ----
        self._close_mmap()

        # ---- LOAD OLD OFFSETS ----
        with open(offsets_path, "r") as f:
            old_offsets = json.load(f)

        # ---- READ ALL OLD POSTINGS FIRST ----
        old_postings_map = {}

        with open(postings_path, "rb") as rf:
            for idx_str, (offset, size) in old_offsets.items():
                rf.seek(offset)
                blob = rf.read(size)
                old_postings_map[idx_str] = ormsgpack.unpackb(blob)

        # ---- NOW SAFE TO TRUNCATE & REWRITE ----
        cursor = 0
        new_offsets = {}

        with open(postings_path, "wb") as wf:
            for word, idx in word_to_index.items():
                idx_str = str(idx)

                prev = old_postings_map.get(idx_str, [])
                added = data.get(word, [])
                merged = prev + added

                blob = ormsgpack.packb(merged)
                wf.write(blob)

                new_offsets[idx_str] = (cursor, len(blob))
                cursor += len(blob)

        # ---- SAVE NEW OFFSETS ----
        with open(offsets_path, "w") as f:
            json.dump(new_offsets, f)

        self.offsets = new_offsets

        # ---- REOPEN mmap ----
        self._reopen_mmap()