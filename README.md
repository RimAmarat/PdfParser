# PDF Document Analysis API

Structural analysis tool for PDF documents with automatic element extraction (titles, sections, tables, images) and detailed statistics calculation.

## 📋 Features

- **Element Extraction**: Titles, subtitles, sections, paragraphs, lists, tables, images
- **Relational Database**: SQLite storage with optimized schema
- **Complete REST API**: Endpoints for ingestion, retrieval, and export
- **Advanced Statistics**: Per-document and global metrics
- **Data Export**: CSV for tables, JSON for metadata

## 🚀 Installation and Execution

### Prerequisites
- Python 3.8+
- pip or conda

### Installing dependencies with pip
```bash
pip install -r requirements.txt
```

### Launching the API
```bash
python main.py
```

The API will be available at: `http://localhost:8000`

Interactive documentation: `http://localhost:8000/docs`

## 📖 Usage

### 1. Upload a PDF document
```bash
curl -X POST "http://localhost:8000/documents/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@example.pdf"
```

**Response:**
```json
{
  "message": "Document processed successfully",
  "document_uuid": "0317cd01-b194-...",
  "filename": "example.pdf",
  "elements_count": 151,
  "statistics": {
    "title_count": 2,
    "section_count": 1,
    "table_count": 2,
    "image_count": 13,
    "avg_text_density_per_page": 1488.66,
    "avg_hierarchical_depth": 1.88,
    "avg_paragraph_length": 19.62,
    "section_distribution": {
      "1": 1
    }
  }
}
```

### 2. List analyzed documents
```bash
curl -X GET "http://localhost:8000/documents"
```

### 3. Get elements from a document
```bash
# All elements
curl -X GET "http://localhost:8000/documents/{uuid}/elements"

# Filter by type
curl -X GET "http://localhost:8000/documents/{uuid}/elements?element_type=table"

# Filter by page
curl -X GET "http://localhost:8000/documents/{uuid}/elements?page_number=2"
```

### 4. View statistics
```bash
# Document statistics
curl -X GET "http://localhost:8000/documents/{uuid}/statistics"

# Global statistics
curl -X GET "http://localhost:8000/statistics/global"
```

### 5. Export data
```bash
# Export tables as CSV
curl -X GET "http://localhost:8000/documents/{uuid}/export/tables" \
     --output tables.csv

# Export metadata (document info and statistics) as JSON
curl -X GET "http://localhost:8000/documents/{uuid}/export/json" \
     --output metadata.json
```

## 🏗️ Architecture

```
├── main.py              # FastAPI entry point
├── file_parser.py       # Element extraction and classification
├── doc_storage.py       # SQLite database management
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

### Main Components

- **`PDFExtractor`**: Structural PDF analysis with PyMuPDF
- **`DocumentStorage`**: Database abstraction layer
- **REST API**: FastAPI endpoints for all operations

## 📊 Detected Element Types

| Type | Detection Criteria |
|------|-------------------|
| **Title** | Font size ≥16pt + bold |
| **Subtitle** | Font size ≥14pt + bold |
| **Section** | Font size ≥12pt + bold OR ≥13pt + ≤20 words |
| **Paragraph** | Standard text |
| **List Item** | Patterns: •, 1., a), -, etc. |
| **Table** | Automatic PyMuPDF detection |
| **Image** | Embedded image extraction |

## 📈 Calculated Statistics

### Per Document
- Count of titles, sections, tables, images
- Average hierarchical depth
- Text density per page
- Average paragraph length
- Section distribution by page

### Global
- Summary by element type
- Averages across all documents
- Comparative statistics

## 🔧 Configuration

### Database
Default: `pdf_documents.sqlite` in the current directory.

To modify:
```python
doc_storage = DocumentStorage(db_path="custom/path/documents.sqlite")
```

### Logging
Logs are configured at INFO level. For more details:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 🧪 Quick Tests

### Installation verification
```bash
curl -X GET "http://localhost:8000/health"
```

### Complete test
1. Upload a test PDF
2. Verify generated statistics
3. Test CSV/JSON exports
4. Check global statistics

## 🐛 Troubleshooting

### Common Errors

**"Only PDF files are allowed"**
- Check the file extension (.pdf)

**"Document not found"**
- Verify the UUID returned during upload

**"Error processing document"**
- Check that the PDF is not corrupted or password-protected

### Logs
Consult application logs for more details on errors.

## 📝 Technical Notes

- **PyMuPDF** for high-performance PDF extraction
- **SQLite** with optimized indexes for queries
- **FastAPI** with automatic data validation
- **Font-based classification** for element identification

## 🚀 Possible Improvements
- JSON and CSV export for all data types
- Download capability for figures and images
- Text content processing
