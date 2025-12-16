import mmap
import os
import json
import ormsgpack


class LSMBarrel:
    def __init__(self, barrel_dir):
        self.dir = barrel_dir

        self.base_postings = os.path.join(barrel_dir, "postings.bin")
        self.base_offsets_f = os.path.join(barrel_dir, "offsets.json")
        self.delta_postings = os.path.join(barrel_dir, "delta_postings.bin")
        self.delta_offsets_f = os.path.join(barrel_dir, "delta_offsets.json")

        if not os.path.exists(self.base_postings) or not os.path.exists(self.base_offsets_f):
            raise FileNotFoundError("Base barrel files not found in LSMBarrel directory")

        # Load offsets
        self.base_offsets = json.load(open(self.base_offsets_f))
        self.delta_offsets = (
            json.load(open(self.delta_offsets_f))
            if os.path.exists(self.delta_offsets_f)
            else {}
        )

        # mmap base
        self.base_file = open(self.base_postings, "rb")
        self.base_mmap = mmap.mmap(self.base_file.fileno(), 0, access=mmap.ACCESS_READ)
        if os.path.exists(self.delta_postings) and len(self.delta_offsets) > 0:
            self.delta_file = open(self.delta_postings, "rb")
            self.delta_mmap = mmap.mmap(self.delta_file.fileno(), 0, access=mmap.ACCESS_READ)
        else:
            self.delta_file = None
            self.delta_mmap = None

        

    def get_posting(self, idx):
        postings = []

        # Base
        idx = str(idx)
        if idx in self.base_offsets:
            off, size = self.base_offsets[idx]
            postings += ormsgpack.unpackb(
                self.base_mmap[off:off + size]
            )

        # Delta
        if idx in self.delta_offsets:
            print(f"Reading delta postings for idx {idx}")
            for off, size in self.delta_offsets[idx]:
                postings += ormsgpack.unpackb(self.delta_mmap[off:off + size])

        return postings

    def append_delta(self, idx, postings):
        idx = str(idx)

        os.makedirs(self.dir, exist_ok=True)
        cursor = os.path.getsize(self.delta_postings) if os.path.exists(self.delta_postings) else 0

        blob = ormsgpack.packb(postings)
        with open(self.delta_postings, "ab") as f:
            f.write(blob)

        self.delta_offsets.setdefault(idx, []).append((cursor, len(blob)))
        with open(self.delta_offsets_f, "w") as f:
            json.dump(self.delta_offsets, f)
        if self.delta_file is None:
            self.delta_file = open(self.delta_postings, "rb")
        else:
            self.delta_file.close()
            self.delta_file = open(self.delta_postings, "rb")
        self.delta_mmap = mmap.mmap(self.delta_file.fileno(), 0, access=mmap.ACCESS_READ)
        print(f"Appended delta postings for idx {idx}")

    def compact(self):
        """
            Merge base + delta into a new base barrel.
            Delta is cleared after compaction.
            This should ONLY be called when no concurrent reads are happening
            (e.g. shutdown or background maintenance window).
        """

        # ---- Collect merged postings ----
        merged = {}

        all_indices = set(self.base_offsets.keys()) | set(self.delta_offsets.keys())
        for idx in all_indices:
            merged[idx] = self.get_posting(idx)

        # ---- Close mmap BEFORE rewriting base ----
        self.base_mmap.close()
        self.base_file.close()

        # ---- Rewrite base postings ----
        cursor = 0
        new_offsets = {}

        with open(self.base_postings, "wb") as f:
            for idx, postings in merged.items():
                blob = ormsgpack.packb(postings)
                f.write(blob)
                new_offsets[idx] = (cursor, len(blob))
                cursor += len(blob)

        # ---- Save new base offsets ----
        with open(self.base_offsets_f, "w") as f:
            json.dump(new_offsets, f)

        self.base_offsets = new_offsets

        # ---- Clear delta ----
        open(self.delta_postings, "wb").close()
        with open(self.delta_offsets_f, "w") as f:
            json.dump({}, f)

        self.delta_offsets = {}

        # ---- Re-open mmap ----
        self.base_file = open(self.base_postings, "rb")
        self.base_mmap = mmap.mmap(
            self.base_file.fileno(), 0, access=mmap.ACCESS_READ
        )

