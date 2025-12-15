import mmap
import ormsgpack
import json
import os

class MMapBarrel:
    def __init__(self, barrel_dir):
        # barrel_dir = path to barrel_0/ folder
        with open(os.path.join(barrel_dir, "offsets.json")) as f:
            self.offsets = json.load(f)
        self.file = open(os.path.join(barrel_dir, "postings.bin"), "rb")
        self.mmap = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)

    def get_posting(self, word_index):
        offset, size = self.offsets[str(word_index)]
        blob = self.mmap[offset:offset+size]
        return ormsgpack.unpackb(blob)
