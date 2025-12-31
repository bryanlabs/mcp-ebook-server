"""
Library management for discovering and indexing ebooks.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from .epub_parser import EpubParser, BookMetadata

logger = logging.getLogger(__name__)


class EbookLibrary:
    """
    Manages a collection of ebooks stored in a directory.
    Discovers EPUB files and provides access to their content.
    """
    
    SUPPORTED_EXTENSIONS = {'.epub'}
    
    def __init__(self, library_path: str):
        self.library_path = Path(library_path)
        self._books_cache: dict[str, EpubParser] = {}
        logger.info(f"Initialized library at: {self.library_path}")
    
    def discover_books(self) -> list[dict]:
        """
        Discover all ebooks in the library directory.
        Returns a list of book metadata dictionaries.
        """
        books = []
        
        if not self.library_path.exists():
            logger.warning(f"Library path does not exist: {self.library_path}")
            return books
        
        for root, dirs, files in os.walk(self.library_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.library_path)
                    
                    try:
                        parser = self._get_parser(file_path)
                        metadata = parser.get_metadata()
                        book_info = metadata.to_dict()
                        book_info['relative_path'] = relative_path
                        books.append(book_info)
                    except Exception as e:
                        logger.error(f"Error parsing {file_path}: {e}")
                        # Still include the book with basic info
                        books.append({
                            'title': file,
                            'author': 'Unknown',
                            'file_path': file_path,
                            'relative_path': relative_path,
                            'error': str(e),
                        })
        
        logger.info(f"Discovered {len(books)} books in library")
        return books
    
    def _get_parser(self, file_path: str) -> EpubParser:
        """Get or create a parser for a book."""
        if file_path not in self._books_cache:
            self._books_cache[file_path] = EpubParser(file_path)
        return self._books_cache[file_path]
    
    def _resolve_path(self, book_path: str) -> Optional[str]:
        """
        Resolve a book path to an absolute path.
        Accepts either relative paths (from library root) or absolute paths.
        """
        # If it's an absolute path and exists, use it
        if os.path.isabs(book_path) and os.path.exists(book_path):
            return book_path
        
        # Try as relative path from library
        full_path = self.library_path / book_path
        if full_path.exists():
            return str(full_path)
        
        # Try searching for a matching filename
        book_name = os.path.basename(book_path)
        for root, dirs, files in os.walk(self.library_path):
            for file in files:
                if file == book_name or book_name.lower() in file.lower():
                    return os.path.join(root, file)
        
        return None
    
    def get_book_info(self, book_path: str) -> Optional[dict]:
        """
        Get detailed information about a specific book.
        Includes metadata and chapter list.
        """
        resolved_path = self._resolve_path(book_path)
        if not resolved_path:
            logger.warning(f"Book not found: {book_path}")
            return None
        
        try:
            parser = self._get_parser(resolved_path)
            metadata = parser.get_metadata()
            chapters = parser.get_chapters()
            
            return {
                **metadata.to_dict(),
                'chapter_count': len(chapters),
                'chapters': [
                    {
                        'number': ch.number,
                        'title': ch.title,
                    }
                    for ch in chapters
                ],
            }
        except Exception as e:
            logger.error(f"Error getting book info for {resolved_path}: {e}")
            return {'error': str(e), 'file_path': resolved_path}
    
    def get_chapter(self, book_path: str, chapter_number: int) -> Optional[str]:
        """Get the text content of a specific chapter."""
        resolved_path = self._resolve_path(book_path)
        if not resolved_path:
            return None
        
        try:
            parser = self._get_parser(resolved_path)
            return parser.get_chapter_text(chapter_number)
        except Exception as e:
            logger.error(f"Error getting chapter {chapter_number} from {resolved_path}: {e}")
            return None
    
    def get_chapters_range(self, book_path: str, start: int, end: int) -> Optional[str]:
        """Get the text content of a range of chapters."""
        resolved_path = self._resolve_path(book_path)
        if not resolved_path:
            return None
        
        try:
            parser = self._get_parser(resolved_path)
            chapters = parser.get_chapters()
            
            texts = []
            for i in range(start, min(end + 1, len(chapters) + 1)):
                chapter = parser.get_chapter(i)
                if chapter:
                    texts.append(f"\n{'='*60}\n{chapter.title}\n{'='*60}\n\n")
                    texts.append(chapter.get_text())
            
            return '\n'.join(texts) if texts else None
        except Exception as e:
            logger.error(f"Error getting chapters {start}-{end} from {resolved_path}: {e}")
            return None
    
    def search_book(self, book_path: str, query: str) -> list[dict]:
        """Search for text within a specific book."""
        resolved_path = self._resolve_path(book_path)
        if not resolved_path:
            return []
        
        try:
            parser = self._get_parser(resolved_path)
            return parser.search(query)
        except Exception as e:
            logger.error(f"Error searching {resolved_path}: {e}")
            return []
    
    def search_library(self, query: str, max_results_per_book: int = 5) -> list[dict]:
        """Search for text across all books in the library."""
        all_results = []
        
        for book_info in self.discover_books():
            if 'error' in book_info:
                continue
            
            file_path = book_info.get('file_path')
            if not file_path:
                continue
            
            try:
                parser = self._get_parser(file_path)
                results = parser.search(query)
                
                for result in results[:max_results_per_book]:
                    result['book_title'] = book_info.get('title', 'Unknown')
                    result['book_author'] = book_info.get('author', 'Unknown')
                    result['book_path'] = file_path
                    all_results.append(result)
                    
            except Exception as e:
                logger.error(f"Error searching {file_path}: {e}")
        
        return all_results

