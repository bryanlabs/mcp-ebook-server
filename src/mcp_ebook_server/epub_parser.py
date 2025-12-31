"""
EPUB parsing utilities using ebooklib and BeautifulSoup.
Extracts metadata, chapters, and text content from EPUB files.
"""

import os
from dataclasses import dataclass
from typing import Optional
from ebooklib import epub, ITEM_DOCUMENT, ITEM_NAVIGATION
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


@dataclass
class Chapter:
    """Represents a chapter in an ebook."""
    number: int
    title: str
    file_name: str
    content: str  # Raw HTML content
    
    def get_text(self) -> str:
        """Extract plain text from HTML content."""
        soup = BeautifulSoup(self.content, 'html.parser')
        # Remove script and style elements
        for element in soup(['script', 'style']):
            element.decompose()
        # Get text and normalize whitespace
        text = soup.get_text(separator='\n')
        lines = (line.strip() for line in text.splitlines())
        return '\n'.join(line for line in lines if line)


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
    
    def get_chapters(self) -> list[Chapter]:
        """Extract all chapters from the EPUB."""
        if self._chapters is not None:
            return self._chapters
        
        book = self._load_book()
        chapters = []
        chapter_num = 0
        
        # Get items in spine order (reading order)
        spine_items = []
        for item_id, linear in book.spine:
            item = book.get_item_with_id(item_id)
            if item and item.get_type() == ITEM_DOCUMENT:
                spine_items.append(item)
        
        # If spine is empty, fall back to getting all document items
        if not spine_items:
            spine_items = list(book.get_items_of_type(ITEM_DOCUMENT))
        
        for item in spine_items:
            content = item.get_content().decode('utf-8', errors='replace')
            soup = BeautifulSoup(content, 'html.parser')
            
            # Try to extract chapter title from headings
            title = None
            for heading_tag in ['h1', 'h2', 'h3', 'title']:
                heading = soup.find(heading_tag)
                if heading:
                    title = heading.get_text().strip()
                    break
            
            # Skip items that look like front/back matter with no content
            text_content = soup.get_text().strip()
            if len(text_content) < 100:
                continue
            
            chapter_num += 1
            chapters.append(Chapter(
                number=chapter_num,
                title=title or f"Chapter {chapter_num}",
                file_name=item.get_name(),
                content=content,
            ))
        
        self._chapters = chapters
        logger.info(f"Found {len(chapters)} chapters in {self.file_path}")
        return chapters
    
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
        """Search for text in the book, returning matching passages with context."""
        results = []
        query_lower = query.lower()
        
        for chapter in self.get_chapters():
            text = chapter.get_text()
            text_lower = text.lower()
            
            start = 0
            while True:
                pos = text_lower.find(query_lower, start)
                if pos == -1:
                    break
                
                # Extract context around the match
                context_start = max(0, pos - context_chars)
                context_end = min(len(text), pos + len(query) + context_chars)
                context = text[context_start:context_end]
                
                # Add ellipsis if truncated
                if context_start > 0:
                    context = "..." + context
                if context_end < len(text):
                    context = context + "..."
                
                results.append({
                    'chapter_number': chapter.number,
                    'chapter_title': chapter.title,
                    'position': pos,
                    'context': context,
                })
                
                start = pos + 1
        
        return results

