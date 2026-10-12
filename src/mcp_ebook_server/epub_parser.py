"""
EPUB parsing utilities using ebooklib and BeautifulSoup.
Extracts metadata, chapters, and text content from EPUB files.
"""

import os
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional
from ebooklib import epub, ITEM_DOCUMENT, ITEM_NAVIGATION
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


NUMBER_WORDS = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
    'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12,
    'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16,
    'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
    'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
    'eighty': 80, 'ninety': 90,
}
ROMAN = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100}
SEPARATOR = r'(?:\s*[.:\-\u2013\u2014)]\s*|[\s\u2002\u2003]+|$)'


def parse_number(token: str, allow_roman: bool = False) -> Optional[int]:
    """Read "8", "0008", "eight", "twenty-one" or (when allowed) "VIII"."""
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    words = re.split(r'[\s-]+', token)
    if words and all(w in NUMBER_WORDS for w in words):
        total = sum(NUMBER_WORDS[w] for w in words)
        return total if len(words) == 1 or NUMBER_WORDS[words[0]] >= 20 else None
    if allow_roman and token and all(c in ROMAN for c in token):
        total, prev = 0, 0
        for c in reversed(token):
            v = ROMAN[c]
            total += -v if v < prev else v
            prev = max(prev, v)
        return total
    return None


def parse_chapter_label(label: str) -> tuple[Optional[int], str]:
    """Split a TOC label or heading into (printed chapter number, title rest).

    Recognises "Chapter 8", "Chapter Eight: Nape", "CHAPTER VIII", "8. Relaxation",
    "1 - Talk to Me", "1\u2003Welcome", "one" and "0008". Labels such as
    "Day 1", "Part I" or "Conversation 2" are not chapters and return None.
    """
    text = ' '.join(label.split())
    m = re.match(r'^(?:chapter|ch\.)\s+([0-9]+|[a-z]+(?:-[a-z]+)?)' + SEPARATOR + r'(.*)$', text, re.I)
    if m:
        n = parse_number(m.group(1), allow_roman=True)
        if n is not None:
            return n, m.group(2).strip()
    m = re.match(r'^([0-9]{1,4})' + SEPARATOR + r'(.*)$', text)
    if m:
        return int(m.group(1)), m.group(2).strip()
    m = re.match(r'^([a-z]+(?:-[a-z]+)?)(?:\s*[.:\-\u2013\u2014]\s*|$)(.*)$', text, re.I)
    if m:
        n = parse_number(m.group(1))
        if n is not None:
            return n, m.group(2).strip()
    return None, text


def normalize_with_map(text: str) -> tuple[str, list[int]]:
    """Lowercase, fold quote styles and drop punctuation, keeping a map from
    each normalized character back to its offset in the original text."""
    out: list[str] = []
    index: list[int] = []
    pending_space = False
    for i, ch in enumerate(text):
        folded = unicodedata.normalize('NFKD', ch)
        folded = ''.join(c for c in folded if not unicodedata.combining(c)).lower()
        for c in folded:
            if c.isalnum():
                if pending_space and out:
                    out.append(' ')
                    index.append(i)
                pending_space = False
                out.append(c)
                index.append(i)
            elif c in "'\u2019\u2018":
                continue
            else:
                pending_space = True
    return ''.join(out), index


MATTER = re.compile(
    r'^(?:front matter|back matter|copyright|contents|table of contents|dedication|'
    r'epigraphs?|praise|also by|other titles|about the authors?|a note about the author|'
    r'newsletter|acknowledge?ments|index|notes|bibliography|references|glossary|title page|cover)\b',
    re.I,
)


def _starts_new_part(heading: Optional[str]) -> bool:
    """True when an untitled-in-TOC section clearly opens something new, such
    as a numbered chapter heading, so it should not inherit the previous label."""
    if not heading:
        return False
    number, _ = parse_chapter_label(heading)
    return number is not None and bool(re.match(r'^(?:chapter|ch\.)\s', heading, re.I))


@dataclass
class Chapter:
    """One reading-order section (spine document) of an ebook.

    `number` is the section index used by get_chapter. `chapter` is the chapter
    number printed in the book (None for front matter, parts and unnumbered
    chapters) and `label` is what a reader would call the section.
    """
    number: int
    title: str
    file_name: str
    content: str  # Raw HTML content
    label: str = ''
    chapter: Optional[int] = None
    heading: Optional[str] = None
    _text: Optional[str] = field(default=None, repr=False)
    _normalized: Optional[tuple[str, list[int]]] = field(default=None, repr=False)

    def get_text(self) -> str:
        """Extract plain text from HTML content."""
        if self._text is None:
            soup = BeautifulSoup(self.content, 'html.parser')
            # Remove script and style elements
            for element in soup(['script', 'style']):
                element.decompose()
            # Get text and normalize whitespace
            text = soup.get_text(separator='\n')
            lines = (line.strip() for line in text.splitlines())
            self._text = '\n'.join(line for line in lines if line)
        return self._text

    def normalized(self) -> tuple[str, list[int]]:
        if self._normalized is None:
            self._normalized = normalize_with_map(self.get_text())
        return self._normalized


@dataclass
class BookMetadata:
    """Metadata for an ebook."""
    title: str
    author: str
    identifier: Optional[str]
    language: Optional[str]
    description: Optional[str]
    publisher: Optional[str]
    file_path: str
    
    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'author': self.author,
            'identifier': self.identifier,
            'language': self.language,
            'description': self.description,
            'publisher': self.publisher,
            'file_path': self.file_path,
        }


class EpubParser:
    """Parser for EPUB files."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._book: Optional[epub.EpubBook] = None
        self._chapters: Optional[list[Chapter]] = None
        self._metadata: Optional[BookMetadata] = None
    
    def _load_book(self) -> epub.EpubBook:
        """Load the EPUB book if not already loaded."""
        if self._book is None:
            logger.info(f"Loading EPUB: {self.file_path}")
            self._book = epub.read_epub(self.file_path)
        return self._book
    
    def get_metadata(self) -> BookMetadata:
        """Extract metadata from the EPUB."""
        if self._metadata is not None:
            return self._metadata
        
        book = self._load_book()
        
        def get_first_metadata(key: str) -> Optional[str]:
            data = book.get_metadata('DC', key)
            if data and len(data) > 0:
                return str(data[0][0])
            return None
        
        self._metadata = BookMetadata(
            title=get_first_metadata('title') or os.path.basename(self.file_path),
            author=get_first_metadata('creator') or 'Unknown',
            identifier=get_first_metadata('identifier'),
            language=get_first_metadata('language'),
            description=get_first_metadata('description'),
            publisher=get_first_metadata('publisher'),
            file_path=self.file_path,
        )
        return self._metadata
    
    def _toc_labels(self) -> dict[str, str]:
        """Map each spine file (basename) to the first table-of-contents label
        that points at it."""
        book = self._load_book()
        labels: dict[str, str] = {}

        def walk(entries):
            for entry in entries:
                if isinstance(entry, tuple):
                    section, children = entry
                    title, href = getattr(section, 'title', ''), getattr(section, 'href', '') or ''
                    if title and href:
                        labels.setdefault(href.split('#')[0].split('/')[-1], ' '.join(title.split()))
                    walk(children)
                else:
                    title, href = getattr(entry, 'title', ''), getattr(entry, 'href', '') or ''
                    if title and href:
                        labels.setdefault(href.split('#')[0].split('/')[-1], ' '.join(title.split()))

        walk(book.toc)
        return labels

    def get_chapters(self) -> list[Chapter]:
        """Extract all reading-order sections from the EPUB, labelled the way
        the printed book names them (from the table of contents)."""
        if self._chapters is not None:
            return self._chapters

        book = self._load_book()
        chapters = []
        chapter_num = 0
        toc = self._toc_labels()

        # Get items in spine order (reading order)
        spine_items = []
        for item_id, linear in book.spine:
            item = book.get_item_with_id(item_id)
            if item and item.get_type() == ITEM_DOCUMENT:
                spine_items.append(item)

        # If spine is empty, fall back to getting all document items
        if not spine_items:
            spine_items = list(book.get_items_of_type(ITEM_DOCUMENT))

        previous: Optional[Chapter] = None
        for item in spine_items:
            content = item.get_content().decode('utf-8', errors='replace')
            soup = BeautifulSoup(content, 'html.parser')

            # Skip items that look like front/back matter with no content.
            # A short file the table of contents names is still a chapter.
            toc_label = toc.get(item.get_name().split('/')[-1])
            text_content = soup.get_text().strip()
            if len(text_content) < (1 if toc_label else 100):
                continue

            heading = None
            for heading_tag in ['h1', 'h2', 'h3']:
                found = soup.find(heading_tag)
                if found and found.get_text().strip():
                    heading = ' '.join(found.get_text(separator=' ').split())
                    break

            chapter_num += 1
            if toc_label:
                label = toc_label
                printed, _ = parse_chapter_label(label)
            elif (previous is not None and not MATTER.search(previous.label)
                    and not _starts_new_part(heading)):
                # A file split out of a chapter belongs to the chapter before it.
                label, printed = previous.label, previous.chapter
            elif heading:
                label = heading
                printed, _ = parse_chapter_label(label)
            else:
                seen_chapter = any(c.chapter is not None for c in chapters)
                label, printed = ('Back matter' if seen_chapter else 'Front matter'), None

            chapter = Chapter(
                number=chapter_num,
                title=label,
                file_name=item.get_name(),
                content=content,
                label=label,
                chapter=printed,
                heading=heading,
            )
            chapters.append(chapter)
            previous = chapter

        self._chapters = chapters
        logger.info(f"Found {len(chapters)} sections in {self.file_path}")
        return chapters

    def get_chapter_groups(self) -> list[dict]:
        """Group consecutive sections that share a label into the chapters a
        reader sees."""
        groups: list[dict] = []
        for ch in self.get_chapters():
            if groups and groups[-1]['label'] == ch.label:
                groups[-1]['sections'].append(ch.number)
                continue
            groups.append({'label': ch.label, 'chapter': ch.chapter, 'sections': [ch.number]})
        return groups

    def find_printed_chapter(self, ref: str) -> list[dict]:
        """Resolve a reader's chapter reference ("8", "eight", "VIII",
        "Chapter 8", "Prologue", "Relaxation") to chapter groups."""
        groups = self.get_chapter_groups()
        text = ' '.join(str(ref).split())
        number, _ = parse_chapter_label(text)
        if number is None:
            number = parse_number(text, allow_roman=True)
        if number is not None:
            hits = [g for g in groups if g['chapter'] == number]
            if hits:
                return hits
        wanted = normalize_with_map(text)[0]
        if not wanted:
            return []
        exact = [g for g in groups if normalize_with_map(g['label'])[0] == wanted]
        if exact:
            return exact
        return [g for g in groups if wanted in normalize_with_map(g['label'])[0]]

    def get_chapter(self, chapter_number: int) -> Optional[Chapter]:
        """Get a specific chapter by number (1-indexed)."""
        chapters = self.get_chapters()
        if 1 <= chapter_number <= len(chapters):
            return chapters[chapter_number - 1]
        return None
    
    def get_chapter_text(self, chapter_number: int) -> Optional[str]:
        """Get the plain text content of a specific chapter."""
        chapter = self.get_chapter(chapter_number)
        if chapter:
            return chapter.get_text()
        return None
    
    def get_full_text(self) -> str:
        """Get the full text of the entire book."""
        chapters = self.get_chapters()
        texts = []
        for chapter in chapters:
            texts.append(f"\n\n{'='*60}\n{chapter.title}\n{'='*60}\n\n")
            texts.append(chapter.get_text())
        return ''.join(texts)
    
    def search(self, query: str, context_chars: int = 200) -> list[dict]:
        """Search for text in the book, returning matching passages with context.

        Matching ignores case, punctuation and quote styles, so "Im pretty much"
        finds "I’m pretty much"."""
        results = []
        wanted = normalize_with_map(query)[0]
        if not wanted:
            return results

        for chapter in self.get_chapters():
            text = chapter.get_text()
            norm, index = chapter.normalized()

            start = 0
            while True:
                npos = norm.find(wanted, start)
                if npos == -1:
                    break
                pos = index[npos]
                end = index[npos + len(wanted) - 1] + 1

                # Extract context around the match
                context_start = max(0, pos - context_chars)
                context_end = min(len(text), end + context_chars)
                context = text[context_start:context_end]

                # Add ellipsis if truncated
                if context_start > 0:
                    context = "..." + context
                if context_end < len(text):
                    context = context + "..."

                results.append({
                    'chapter_number': chapter.number,
                    'chapter_title': chapter.label,
                    'section': chapter.number,
                    'chapter': chapter.chapter,
                    'label': chapter.label,
                    'position': pos,
                    'match': text[pos:end],
                    'context': context,
                })

                start = npos + 1

        return results

    def find_quote(self, quote: str, context_chars: int = 300) -> Optional[dict]:
        """Locate a quoted passage and return the book's exact wording.

        Case, punctuation and quote styles are ignored. An ellipsis in the
        quote ("a ... b") matches text that skips ahead between the pieces.
        When no exact match exists, the closest passage with at least 85%
        similarity is returned with `exact: False`."""
        pieces = [normalize_with_map(p)[0] for p in re.split(r'\.\s*\.\s*\.|\u2026|\[\.\.\.\]', quote)]
        pieces = [p for p in pieces if p]
        if not pieces:
            return None

        for chapter in self.get_chapters():
            norm, index = chapter.normalized()
            start = norm.find(pieces[0])
            while start != -1:
                cursor = start + len(pieces[0])
                for piece in pieces[1:]:
                    nxt = norm.find(piece, cursor)
                    if nxt == -1 or nxt - cursor > 2000:
                        break
                    cursor = nxt + len(piece)
                else:
                    return self._quote_result(chapter, index[start], index[cursor - 1] + 1, True, context_chars)
                start = norm.find(pieces[0], start + 1)

        return self._fuzzy_quote(' '.join(pieces), context_chars)

    def _fuzzy_quote(self, wanted: str, context_chars: int) -> Optional[dict]:
        words = wanted.split()
        if len(words) < 6:
            return None
        window = 5
        best: Optional[tuple[float, Chapter, int, int]] = None
        for chapter in self.get_chapters():
            norm, index = chapter.normalized()
            seen: set[int] = set()
            for i in range(0, len(words) - window + 1, 2):
                probe = ' '.join(words[i:i + window])
                pos = norm.find(probe)
                while pos != -1:
                    approx = max(0, pos - len(' '.join(words[:i])) - (1 if i else 0))
                    if approx not in seen:
                        seen.add(approx)
                        lo = max(0, approx - 40)
                        region = norm[lo:approx + len(wanted) + 40]
                        matcher = SequenceMatcher(None, wanted, region, autojunk=False)
                        blocks = [b for b in matcher.get_matching_blocks() if b.size]
                        if blocks:
                            a = lo + blocks[0].b
                            b = lo + blocks[-1].b + blocks[-1].size
                            ratio = SequenceMatcher(None, wanted, norm[a:b], autojunk=False).ratio()
                            if best is None or ratio > best[0]:
                                best = (ratio, chapter, a, b)
                    pos = norm.find(probe, pos + 1)
        if best is None or best[0] < 0.85:
            return None
        ratio, chapter, a, b = best
        _, index = chapter.normalized()
        result = self._quote_result(chapter, index[a], index[b - 1] + 1, False, context_chars)
        result['similarity'] = round(ratio, 3)
        return result

    def _quote_result(self, chapter: Chapter, pos: int, end: int, exact: bool, context_chars: int) -> dict:
        text = chapter.get_text()
        while end < len(text) and text[end] in '.,!?;:\u201d"\u2019)':
            end += 1
        before = text[max(0, pos - context_chars):pos]
        after = text[end:end + context_chars]
        return {
            'exact': exact,
            'text': text[pos:end],
            'section': chapter.number,
            'chapter': chapter.chapter,
            'label': chapter.label,
            'position': pos,
            'before': before,
            'after': after,
        }
