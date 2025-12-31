# MCP Ebook Server

An MCP (Model Context Protocol) server that provides AI assistants with direct access to your ebook library. Works with Claude, Cursor, and other MCP-compatible clients.

## Features

- **List books** in your library with metadata (title, author, language)
- **Read chapters** individually or in ranges
- **Search** within books or across your entire library
- **EPUB support** with automatic text extraction

## Why Use This Instead of LLM Training Data?

LLMs like Claude have read millions of books during training, but they don't actually *have* those books—they have a compressed neural representation of patterns and themes. This creates real limitations:

| Question Type | LLM Training Data | MCP Ebook Server |
|--------------|-------------------|------------------|
| "What's the 10th word of chapter 2?" | ❌ Cannot answer | ✅ Exact answer |
| "Quote the opening paragraph" | ⚠️ Often paraphrased or hallucinated | ✅ Verbatim text |
| "How many times is 'magic' mentioned?" | ❌ Guesses | ✅ Precise count |
| "What happens in chapter 5?" | ⚠️ May confuse with similar books | ✅ Actual content |
| "Does this book mention X?" | ⚠️ Uncertain, may hallucinate | ✅ Searchable proof |

**The core problem:** LLMs retain the *gist* of books—major plot points, famous quotes, general themes—but lose precise details. When asked about specifics they don't know, they often hallucinate plausible-sounding answers rather than admitting uncertainty.

**The solution:** This MCP server gives AI direct access to the actual source text. Instead of guessing, the AI can read the exact chapter, search for specific terms, and cite real passages. No hallucinations, just the book.

## Installation

### Docker (Recommended)

```bash
docker run -p 8080:8080 -v /path/to/your/ebooks:/ebooks ghcr.io/bryanlabs/mcp-ebook-server:latest
```

### Docker Compose

```yaml
services:
  mcp-ebook-server:
    image: ghcr.io/bryanlabs/mcp-ebook-server:latest
    ports:
      - "8080:8080"
    volumes:
      - /path/to/your/ebooks:/ebooks:ro
```

### pip

```bash
pip install git+https://github.com/bryanlabs/mcp-ebook-server.git
mcp-ebook-server --library-path /path/to/your/ebooks
```

### From Source

```bash
git clone https://github.com/bryanlabs/mcp-ebook-server.git
cd mcp-ebook-server
pip install -e .
mcp-ebook-server
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `EBOOK_LIBRARY_PATH` | `/ebooks` | Path to your ebook directory |
| `MCP_HOST` | `0.0.0.0` | Host to bind the server |
| `MCP_PORT` | `8080` | Port for the SSE endpoint |

## Usage

Once the server is running, connect your MCP client to `http://localhost:8080/sse`.

## Available Tools

| Tool | Description | Example |
|------|-------------|---------|
| `list_books()` | List all ebooks with metadata | "What books do I have?" |
| `get_book_info(book_path)` | Get book details and chapter list | "How many chapters in The Magicians?" |
| `get_chapter(book_path, chapter_number)` | Read a specific chapter | "Read chapter 1" |
| `get_chapters_range(book_path, start, end)` | Read multiple chapters | "Get chapters 1-3" |
| `search_book(book_path, query)` | Search within a book | "Find mentions of 'magic'" |
| `search_library(query)` | Search all books | "Search for 'dragon'" |

## Supported Formats

| Format | Status |
|--------|--------|
| EPUB | Fully supported |
| MOBI | Requires conversion to EPUB |
| AZW3 | Requires conversion to EPUB |
| PDF | Not supported |

## License

MIT License - see [LICENSE](LICENSE) for details.
