import json
import orjson
from collections import defaultdict, Counter
from bs4 import BeautifulSoup
from urllib.parse import urlparse
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
    def normalize_and_tokenize_for_html(text):
        text = re.sub(r'\n', ' ', text)
        text = re.sub(r'(?<!\d)[^\w\s]|[^\w\s](?!\d)', ' ', text)
        text = re.sub(r"\s+", " ", text).strip()
        return text.lower().split(' ')

    @staticmethod
    def process_html_file(file_path, url, doc_id):
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()
        
        soup = BeautifulSoup(html, 'lxml')  
        text = soup.get_text()
        tokens = FileHandler.normalize_and_tokenize_for_html(text)
        doc_length = len(tokens)
        
        tokens_counter = Counter(tokens)
        
        positions_map = defaultdict(list)
        for i, tok in enumerate(tokens):
            if len(positions_map[tok]) < 15:
                positions_map[tok].append(i)
        
        title_text = []
        if soup.title:
            title_text = FileHandler.normalize_and_tokenize_for_html(soup.title.text)
        title_counter = Counter(title_text)
        
        meta_desc_text = []
        meta_tag = soup.find('meta', attrs={'name': 'description'})
        if meta_tag and 'content' in meta_tag.attrs:
            meta_desc_text = FileHandler.normalize_and_tokenize_for_html(meta_tag['content'])
        meta_counter = Counter(meta_desc_text)
        
        headings = []
        for i in range(1, 7):
            for heading in soup.find_all(f'h{i}'):
                headings.extend(FileHandler.normalize_and_tokenize_for_html(heading.text))
        headings_counter = Counter(headings)

        anchors_tokens = []
        anchors_counter = Counter(anchors_tokens)
        
        url_path = urlparse(url).path
        domain = urlparse(url).netloc

        hit_lists = {}
        for word in tokens:
            hit_list = []
            hit_list.append(doc_id)
            hit_list.append(positions_map.get(word, []))
            hit_list.append([
                title_counter[word],
                meta_counter[word],
                headings_counter[word],
                tokens_counter[word],
                anchors_counter[word],
                1 if word in domain else 0,
                1 if word in url_path else 0,
                doc_length
            ])
            hit_lists[word] = hit_list

        title = soup.title.text if soup.title else ""
        meta_desc_text = meta_tag['content'] if meta_tag and 'content' in meta_tag.attrs else ""
        
        return hit_lists, title, meta_desc_text, text

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
    
    @staticmethod
    def save_temp_file_html(file_content, save_name):
        save_path = os.path.join(os.getcwd(), 'data', 'temp', save_name)
        with open(save_path, 'wb') as f:
            f.write(file_content)
        return save_path
    
    @staticmethod
    def pdf_to_json(pdf_bytes, filename):
        """
        Convert PDF bytes to CORD-19 JSON format.
        
        Args:
            pdf_bytes: Binary PDF content
            filename: Original PDF filename
        
        Returns:
            dict: CORD-19 format JSON document with structure:
                {
                    "metadata": { "title": "<title>", "authors": [...] },
                    "abstract": [{ "text": "<abstract>" }],
                    "body_text": [{ "text": "<paragraph text>" }, ...]
                }
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PyMuPDF library not available. Install with: pip install PyMuPDF")
        
        # Open PDF from bytes
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Extract text from all pages
        full_text = ""
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            full_text += page.get_text() + "\n"
        
        pdf_doc.close()
        
        # Validate extracted text
        if not full_text or not full_text.strip():
            raise ValueError("PDF file is empty or contains no extractable text")
        
        # Clean up text - split into lines and filter empty lines
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
        
        # Helper function to check if line contains URLs
        def has_url(text):
            url_pattern = r'http[s]?://|www\.|\.com|\.org|\.edu|\.net|\.gov|\.in|ISSN'
            return bool(re.search(url_pattern, text, re.IGNORECASE))
        
        # Helper function to check if line is journal metadata
        def is_journal_metadata(text):
            text_lower = text.lower()
            metadata_keywords = ['issn', 'volume', 'vol.', 'issue', 'pp.', 'pages', 'page', 'doi:', 'doi.org']
            return any(keyword in text_lower for keyword in metadata_keywords) or bool(re.search(r'\b\d{4}\b', text))  # Year pattern
        
        # Helper function to check if line is all caps (potential title)
        def is_all_caps(text):
            # Check if text is mostly uppercase (allowing some lowercase for articles)
            if len(text) < 5:
                return False
            upper_count = sum(1 for c in text if c.isupper())
            alpha_count = sum(1 for c in text if c.isalpha())
            if alpha_count == 0:
                return False
            return (upper_count / alpha_count) > 0.7  # At least 70% uppercase
        
        # Helper function to check if line contains numbers (likely not title)
        def has_numbers(text):
            return bool(re.search(r'\d', text))
        
        # ========== TITLE EXTRACTION ==========
        extracted_title = filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ').strip()
        title_idx = -1
        
        # Strategy 1: Find first all-caps line without numbers, URLs, or journal metadata
        for i, line in enumerate(lines[:15]):
            if (len(line) > 10 and len(line) < 250 and 
                is_all_caps(line) and not has_numbers(line) and 
                not has_url(line) and not is_journal_metadata(line)):
                extracted_title = line
                title_idx = i
                break
        
        # Strategy 2: Find first large text block above author/metadata section
        if title_idx == -1:
            for i, line in enumerate(lines[:15]):
                if (len(line) > 20 and len(line) < 250 and 
                    not has_url(line) and not is_journal_metadata(line) and
                    not has_numbers(line)):
                    # Check if next few lines look like authors or metadata
                    if i + 3 < len(lines):
                        next_lines = ' '.join(lines[i+1:i+4]).lower()
                        if not any(keyword in next_lines for keyword in ['abstract', 'introduction', 'keywords']):
                            extracted_title = line
                            title_idx = i
                            break
        
        # Strategy 3: First substantial line (fallback)
        if title_idx == -1:
            for i, line in enumerate(lines[:10]):
                if len(line) > 15 and len(line) < 250:
                    if not has_url(line) and not is_journal_metadata(line):
                        extracted_title = line
                        title_idx = i
                        break
        
        # Clean title - remove any remaining URLs or metadata
        extracted_title = re.sub(r'http[s]?://[^\s]+|www\.[^\s]+|[^\s]+\.(com|org|edu|net|gov|in)[^\s]*', '', extracted_title, flags=re.IGNORECASE)
        extracted_title = re.sub(r'\bISSN[:\s]*[\d\-X]+\b', '', extracted_title, flags=re.IGNORECASE)
        extracted_title = re.sub(r'\b(Volume|Vol\.?|Issue|No\.?|Pages?|PP\.?|P\.?)[\s:]*[\d\-,\s]+\b', '', extracted_title, flags=re.IGNORECASE)
        extracted_title = re.sub(r'\s+', ' ', extracted_title).strip()
        
        # ========== AUTHOR EXTRACTION ==========
        authors = []
        author_start_idx = title_idx + 1 if title_idx >= 0 else 1
        
        # Keywords to exclude from author lines
        exclude_keywords = ['issn', 'volume', 'vol.', 'issue', 'page', 'pages', 'abstract', 
                           'introduction', 'keywords', 'university', 'department', 'institute',
                           'corresponding', 'email', '@', 'doi', 'www.', '.com', '.org', '.edu']
        
        def is_valid_author_line(line):
            line_lower = line.lower()
            # Exclude if contains metadata keywords
            if any(keyword in line_lower for keyword in exclude_keywords):
                return False
            # Exclude if mostly numbers
            if re.match(r'^[\d\s\-\.]+$', line):
                return False
            # Exclude URLs
            if has_url(line):
                return False
            # Should be reasonable length
            if len(line) < 3 or len(line) > 200:
                return False
            # Should contain letters
            if not re.search(r'[a-zA-Z]', line):
                return False
            return True
        
        # Extract authors from lines after title
        for i in range(author_start_idx, min(author_start_idx + 10, len(lines))):
            line = lines[i]
            
            # Skip if we hit abstract or introduction
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['abstract', 'introduction', 'keywords', '1. introduction']):
                break
            
            if not is_valid_author_line(line):
                continue
            
            # Handle comma-separated names
            if ',' in line:
                names = [name.strip() for name in line.split(',')]
                for name in names:
                    # Remove numeric prefixes like "1", "2", "3"
                    name = re.sub(r'^\d+[\.\)\s]*', '', name).strip()
                    if name and len(name) > 2 and len(name) < 100:
                        authors.append({"name": name})
                        if len(authors) >= 10:  # Limit authors
                            break
            else:
                # Single author name
                name = line
                # Remove numeric prefixes
                name = re.sub(r'^\d+[\.\)\s]*', '', name).strip()
                if name and len(name) > 2 and len(name) < 100:
                    authors.append({"name": name})
            
            if len(authors) >= 10:  # Limit total authors
                break
        
        # ========== ABSTRACT EXTRACTION ==========
        abstract_text = ""
        abstract_found = False
        abstract_end_idx = len(lines)
        
        for i, line in enumerate(lines):
            if 'abstract' in line.lower() and len(line) < 100:
                # Found abstract section, collect next lines until we hit a section header
                abstract_lines = []
                for j in range(i + 1, min(i + 50, len(lines))):
                    next_line = lines[j]
                    # Stop if we hit common section markers
                    if any(marker in next_line.lower()[:30] for marker in ['introduction', 'keywords', '1.', 'i.', '1 introduction']):
                        abstract_end_idx = j
                        break
                    abstract_lines.append(next_line)
                if abstract_lines:
                    abstract_text = ' '.join(abstract_lines[:30])  # Limit length
                    abstract_found = True
                    abstract_end_idx = i + len(abstract_lines) + 1
                break
        
        # Fallback: use first substantial paragraph if no abstract found
        if not abstract_found and lines:
            for line in lines[:20]:
                if len(line) > 50 and not has_url(line):
                    abstract_text = line[:1000]
                    break
        
        # ========== BODY TEXT STRUCTURE ==========
        # Find where body starts (after abstract/title/authors)
        body_start_idx = abstract_end_idx if abstract_found else (author_start_idx + len(authors) + 2)
        body_start_idx = max(body_start_idx, 5)  # At least skip first few lines
        
        # Helper to detect section headings
        def is_section_heading(line, prev_line_empty=False):
            line_lower = line.lower().strip()
            
            # Check for roman numerals (I, II, III, IV, etc.)
            if re.match(r'^[IVX]+[\.\)]?\s+[A-Z]', line):
                return True
            
            # Check for numbered sections (1., 2., 3., etc.)
            if re.match(r'^\d+[\.\)]\s+[A-Z]', line):
                return True
            
            # Check for all-caps short lines (likely headings)
            if len(line) < 80 and is_all_caps(line) and len(line) > 3:
                return True
            
            # Common section keywords
            section_keywords = ['introduction', 'methodology', 'methods', 'related work', 'background',
                              'results', 'discussion', 'conclusion', 'references', 'acknowledgment',
                              'acknowledgments', 'appendix', 'abstract', 'related', 'implementation',
                              'algorithm', 'experiment', 'evaluation', 'analysis']
            
            # Check if line is mostly a section keyword
            for keyword in section_keywords:
                if keyword in line_lower and len(line) < 100:
                    # Should be at start or after roman/numeral
                    if (line_lower.startswith(keyword) or 
                        re.match(r'^[IVX\d]+[\.\)]?\s*' + keyword, line_lower)):
                        return True
            
            return False
        
        # Build structured body text with sections
        body_sections = []
        current_section = {"section": "", "text": ""}
        in_body = False
        
        for i in range(body_start_idx, len(lines)):
            line = lines[i]
            
            # Skip empty lines
            if not line.strip():
                continue
            
            # Check if this is a section heading
            prev_empty = (i > 0 and not lines[i-1].strip()) if i > 0 else False
            if is_section_heading(line, prev_empty):
                # Save previous section if it has content
                if current_section["text"].strip():
                    body_sections.append(current_section)
                
                # Start new section
                current_section = {
                    "section": line.strip(),
                    "text": ""
                }
                in_body = True
            else:
                # Add to current section
                if in_body or i >= body_start_idx + 2:
                    if current_section["text"]:
                        current_section["text"] += " " + line
                    else:
                        current_section["text"] = line
                    in_body = True
        
        # Add final section
        if current_section["text"].strip():
            body_sections.append(current_section)
        
        # Remove abstract text if it appears in body
        if abstract_text:
            abstract_words = set(abstract_text.lower().split()[:20])  # First 20 words
            filtered_sections = []
            for section in body_sections:
                section_words = set(section["text"].lower().split()[:20])
                # If overlap is too high, skip (likely repeated abstract)
                overlap = len(abstract_words & section_words)
                if overlap < 10:  # Less than 10 words overlap
                    filtered_sections.append(section)
                elif len(section["text"]) > 500:  # Keep if very long (not just abstract)
                    filtered_sections.append(section)
            body_sections = filtered_sections if filtered_sections else body_sections
        
        # Convert to body_text format (CORD-19 style)
        body_text_items = []
        for section in body_sections:
            if section["text"].strip():
                # Use section heading as prefix if available, otherwise just text
                if section["section"]:
                    text_with_section = f"{section['section']}\n{section['text']}"
                else:
                    text_with_section = section["text"]
                body_text_items.append({"text": text_with_section.strip()})
        
        # Fallback: if no structured sections, use paragraph approach
        if not body_text_items:
            paragraphs = []
            current_para = []
            
            for line in lines[body_start_idx:]:
                if len(line) > 20:
                    current_para.append(line)
                else:
                    if current_para:
                        para_text = ' '.join(current_para)
                        if len(para_text.strip()) > 50:
                            paragraphs.append(para_text)
                        current_para = []
            
            if current_para:
                para_text = ' '.join(current_para)
                if len(para_text.strip()) > 50:
                    paragraphs.append(para_text)
            
            if paragraphs:
                body_text_items = [{"text": para.strip()} for para in paragraphs if para.strip()]
        
        # Final fallback: use remaining text
        if not body_text_items:
            remaining_text = ' '.join(lines[body_start_idx:])
            if remaining_text.strip():
                body_text_items = [{"text": remaining_text.strip()}]
            else:
                body_text_items = [{"text": full_text}]
        
        document = {
            "metadata": {
                "title": extracted_title,
                "authors": authors if authors else []
            },
            "abstract": [{"text": abstract_text.strip()}] if abstract_text.strip() else [],
            "body_text": body_text_items
        }
        
        return document
    





        
