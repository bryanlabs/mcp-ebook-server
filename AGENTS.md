# mcp-ebook-server

## What it is

An MCP (Model Context Protocol) server that gives AI assistants direct access to an EPUB ebook library. Exposes tools for listing, reading, and searching books so AI can return verbatim text rather than hallucinated summaries.

## Where it's used

**Cluster:** Deployed as Deployment `mcp-ebook-server` in the `media-suite` namespace. Image: `ghcr.io/bryanlabs/mcp-ebook-server`. The ebook library directory is mounted as a volume at `/ebooks`.

**Local MCP:** Run via Docker or pip and connect any MCP-compatible client (Claude, Cursor, Zed) to `http://localhost:8080/mcp` (streamable-http transport).

## MCP surface

**Tools:**

| Tool | Purpose |
|------|---------|
| `list_books()` | List all EPUBs in the library with title, author, language, relative path |
| `get_book_info(book_path)` | Metadata + full chapter list for a specific book |
| `get_chapter(book_path, chapter_number)` | Full text of a single chapter (1-indexed) |
| `get_chapters_range(book_path, start_chapter, end_chapter)` | Text of a chapter range, concatenated |
| `search_book(book_path, query)` | Case-insensitive search within one book; returns matches with context |
| `search_library(query)` | Search across all books; returns up to 5 matches per book |

**Resource:**

| Resource | Purpose |
|----------|---------|
| `health://status` | Returns JSON with `status`, `library_path`, and `book_count` |

## How it works

- **Transport:** streamable-http via FastMCP (uvicorn/starlette). Listens on `0.0.0.0:8080`.
- **Backend:** No external service. Reads EPUB files directly from the mounted library directory using `ebooklib` for parsing and `beautifulsoup4`/`lxml` for HTML-to-text extraction.
- **Supported formats:** EPUB only. MOBI/AZW3 require prior conversion to EPUB. PDFs are not supported.
- **Book path resolution:** Accepts relative paths from library root, absolute paths, or bare filenames (fuzzy filename match).
- **Caching:** Parsed `EpubParser` instances are cached in memory per file path for the lifetime of the process.

## Code map

| File | Role |
|------|------|
| `src/mcp_ebook_server/server.py` | FastMCP setup, all tool and resource definitions, `main()` entrypoint |
| `src/mcp_ebook_server/library.py` | `EbookLibrary` class: directory walk, path resolution, chapter/search dispatch |
| `src/mcp_ebook_server/epub_parser.py` | `EpubParser` class: EPUB parsing, metadata extraction, chapter text, search |
| `src/mcp_ebook_server/__main__.py` | `python -m mcp_ebook_server` entrypoint |
| `pyproject.toml` | Package manifest; `mcp-ebook-server` CLI script |

## Build & deploy

**CI:** `.github/workflows/build.yml` builds and pushes to `ghcr.io/bryanlabs/mcp-ebook-server` on push to `main`. Publishes `linux/amd64` and `linux/arm64`.

**Local build:**
```bash
docker buildx build --builder cloud-bryanlabs-builder --platform linux/amd64 -t ghcr.io/bryanlabs/mcp-ebook-server:latest .
```

**Environment variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `EBOOK_LIBRARY_PATH` | `/ebooks` | Path to the EPUB library directory |
| `MCP_HOST` | `0.0.0.0` | Bind host |
| `MCP_PORT` | `8080` | Bind port |

## Gotchas

- Only EPUB is supported natively. MOBI/AZW3 files must be converted before mounting.
- `search_library` re-runs `discover_books()` on every call (full directory walk); performance degrades with large libraries.
- No authentication. The server trusts all incoming MCP requests; keep it internal or behind an ingress with auth.
- Health check POSTs to `/mcp` with a `ping` JSON-RPC call (not a GET to `/health`).
