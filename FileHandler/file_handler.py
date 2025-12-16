import json
import orjson
from collections import defaultdict, Counter
import re
import os



class FileHandler:
    @staticmethod
    def normalize_and_tokenize(text):
        if not isinstance(text, str):
            return []
        
        tokens = []
        word = []
        
        for c in text:
            # Match C++ logic: isalnum(c) || c >= 128 (unicode)
            if c.isalnum() or ord(c) >= 128:
                word.append(c.lower())
            else:
                if word:
                    tokens.append(''.join(word))
                    word = []
        
        # Don't forget the last word
        if word:
            tokens.append(''.join(word))
        
        return tokens
    
    @staticmethod
    def process_json_file(file_path):
        MAX_POS = 15
        words = set()

        with open(file_path, 'r', encoding='utf-8') as f:
            doc = json.load(f)

        # Fix docid source - add P prefix for research papers
        docid = os.path.basename(file_path).replace(".json", "")
        positions_map = defaultdict(list)
        print(docid)

        # Section group counters:
        group1 = Counter()  # title + abstract + authors
        group2 = Counter()  # body_text
        group3 = Counter()  # references + ref_entries + back_matter

        pos = 0

        # ----- TITLE -----
        title = doc.get("metadata", {}).get("title", "")
        for tok in FileHandler.normalize_and_tokenize(title):
            words.add(tok)
            if len(positions_map[tok]) < MAX_POS:
                positions_map[tok].append(pos)
            group1[tok] += 1
            pos += 1

        # ----- ABSTRACT -----
        for item in doc.get("abstract", []):
            for tok in FileHandler.normalize_and_tokenize(item.get("text", "")):
                words.add(tok)
                if len(positions_map[tok]) < MAX_POS:
                    positions_map[tok].append(pos)
                group1[tok] += 1
                pos += 1

        # ----- AUTHORS -----
        # Match C++ logic: extract ALL fields from author objects
        for author in doc.get("metadata", {}).get("authors", []):
            if isinstance(author, str):
                # If author is a plain string
                for tok in FileHandler.normalize_and_tokenize(author):
                    words.add(tok)
                    if len(positions_map[tok]) < MAX_POS:
                        positions_map[tok].append(pos)
                    group1[tok] += 1
                    pos += 1
            elif isinstance(author, dict):
                # Extract all string fields from author object (first, last, middle, suffix, affiliation, email, etc.)
                for key, value in author.items():
                    if isinstance(value, str):
                        for tok in FileHandler.normalize_and_tokenize(value):
                            words.add(tok)
                            if len(positions_map[tok]) < MAX_POS:
                                positions_map[tok].append(pos)
                            group1[tok] += 1
                            pos += 1

        # ----- BODY TEXT -----
        for item in doc.get("body_text", []):
            for tok in FileHandler.normalize_and_tokenize(item.get("text", "")):
                words.add(tok)
                if len(positions_map[tok]) < MAX_POS:
                    positions_map[tok].append(pos)
                group2[tok] += 1
                pos += 1

        # ----- BIB ENTRIES (titles only) -----
        for ref in doc.get("bib_entries", {}).values():
            for tok in FileHandler.normalize_and_tokenize(ref.get("title", "")):
                words.add(tok)
                if len(positions_map[tok]) < MAX_POS:
                    positions_map[tok].append(pos)
                group3[tok] += 1
                pos += 1

        # ----- REF ENTRIES (FIGREF, TABREF...) -----
        for ref in doc.get("ref_entries", {}).values():
            for tok in FileHandler.normalize_and_tokenize(ref.get("text", "")):
                words.add(tok)
                if len(positions_map[tok]) < MAX_POS:
                    positions_map[tok].append(pos)
                group3[tok] += 1
                pos += 1

        # ----- BACK MATTER -----
        for item in doc.get("back_matter", []):
            for tok in FileHandler.normalize_and_tokenize(item.get("text", "")):
                words.add(tok)
                if len(positions_map[tok]) < MAX_POS:
                    positions_map[tok].append(pos)
                group3[tok] += 1
                pos += 1


        # ------------------ BUILD HITLISTS ------------------
        hitlists = {}
        for word in words:

            g1 = group1[word]
            g2 = group2[word]
            g3 = group3[word]
            total = g1 + g2 + g3

            # DROP empty words
            if total == 0:
                continue

            hitlists[word] = [
                docid,
                positions_map[word],
                [
                    g1,     # title + abstract + authors
                    g2,     # body
                    g3,     # references + ref_entries + back_matter
                    total,  # total
                    pos     # doc length
                ]
            ]

        return hitlists
    
    @staticmethod
    def extract_text_from_json(file_path):
        def recurse(obj, texts):
            if isinstance(obj, dict):
                for value in obj.values():
                    recurse(value, texts)
            elif isinstance(obj, list):
                for item in obj:
                    recurse(item, texts)
            elif isinstance(obj, str):
                texts.append(obj)

        with open(file_path, 'r', encoding='utf-8') as f:
            data = orjson.loads(f.read())

        texts = []
        recurse(data, texts)

        return " ".join(texts)

    @staticmethod
    def preprocess_text(text):
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', '', text)
        tokens = text.split()
        return tokens
    
    @staticmethod
    def save_temp_file_rp(file_content, save_name):
        save_path = os.path.join(os.getcwd(), 'data', 'temp', save_name)
        with open(save_path, 'wb') as f:
            f.write(file_content)
        return save_path



        
