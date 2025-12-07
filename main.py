from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from typing import Optional, List
import tempfile
import os
import json
import csv
import io
import logging

from file_parser import PDFExtractor
from doc_storage import DocumentStorage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PDF Document Analysis API",
    description="API for extracting and analyzing PDF document structure",
    version="1.0.0"
)

# Initialize components
pdf_extractor = PDFExtractor()
doc_storage = DocumentStorage()


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a PDF document."""

    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        # Create temporary file to save uploaded PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Process the PDF
        logger.info(f"Processing uploaded file: {file.filename}")
        elements, statistics = pdf_extractor.extract_structure(temp_file_path)

        # Save to database
        document_uuid = doc_storage.save_document(temp_file_path, elements, statistics, file.filename)

        # Clean up temporary file
        os.unlink(temp_file_path)

        return JSONResponse(
            status_code=201,
            content={
                "message": "Document processed successfully",
                "document_uuid": document_uuid,
                "filename": file.filename,
                "elements_count": len(elements),
                "statistics": statistics.to_dict()
            }
        )

    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass

        logger.error(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@app.get("/documents")
async def list_documents(limit: int = Query(100, ge=1, le=1000)):
    """Return list of analyzed documents."""
    try:
        documents = doc_storage.list_documents(limit=limit)
        return JSONResponse(
            content={
                "documents": documents,
                "count": len(documents)
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving documents: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {str(e)}")


@app.get("/documents/{document_uuid}/elements")
async def get_document_elements(
        document_uuid: str,
        element_type: Optional[str] = Query(None, description="Filter by element type"),
        page_number: Optional[int] = Query(None, ge=1, description="Filter by page number")
):
    """Return extracted elements for a specific document."""
    try:
        # Verify document exists
        doc_info = doc_storage.get_document_by_uuid(document_uuid)
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get elements with optional filtering
        elements = doc_storage.get_document_elements(
            document_uuid=document_uuid,
            element_type=element_type,
            page_number=page_number
        )

        return JSONResponse(
            content={
                "document_uuid": document_uuid,
                "filename": doc_info["filename"],
                "elements": elements,
                "count": len(elements),
                "filters": {
                    "element_type": element_type,
                    "page_number": page_number
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving elements: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving elements: {str(e)}")


@app.get("/documents/{document_uuid}/statistics")
async def get_document_stats(document_uuid: str):
    """Return statistics for a specific document."""
    try:
        # Verify document exists
        doc_info = doc_storage.get_document_by_uuid(document_uuid)
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get statistics
        statistics = doc_storage.get_document_statistics(document_uuid)

        return JSONResponse(
            content={
                "document_uuid": document_uuid,
                "filename": doc_info["filename"],
                "processed_at": doc_info["processed_at"],
                "statistics": statistics
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")


@app.get("/statistics/global")
async def get_global_stats():
    """Return statistics across all documents."""
    try:
        # Get all documents
        documents = doc_storage.list_documents(limit=1000)  # Adjust limit as needed

        if not documents:
            return JSONResponse(
                content={
                    "message": "No documents found",
                    "global_statistics": {}
                }
            )

        # Get element type summary
        element_summary = doc_storage.get_element_type_summary()

        # Calculate global statistics
        total_documents = len(documents)

        # Get statistics for each document to calculate averages
        all_stats = []
        for doc in documents:
            doc_stats = doc_storage.get_document_statistics(doc['document_uuid'])
            if doc_stats:
                all_stats.append(doc_stats)

        # Calculate averages
        avg_title_count = sum(s.get('title_count', 0) for s in all_stats) / len(all_stats) if all_stats else 0
        avg_section_count = sum(s.get('section_count', 0) for s in all_stats) / len(all_stats) if all_stats else 0
        avg_table_count = sum(s.get('table_count', 0) for s in all_stats) / len(all_stats) if all_stats else 0
        avg_image_count = sum(s.get('image_count', 0) for s in all_stats) / len(all_stats) if all_stats else 0
        avg_paragraph_length = sum(s.get('avg_paragraph_length', 0) for s in all_stats) / len(
            all_stats) if all_stats else 0
        avg_text_density = sum(s.get('avg_text_density_per_page', 0) for s in all_stats) / len(
            all_stats) if all_stats else 0

        global_statistics = {
            "total_documents": total_documents,
            "element_type_summary": element_summary,
            "averages_across_documents": {
                "avg_titles_per_document": round(avg_title_count, 2),
                "avg_sections_per_document": round(avg_section_count, 2),
                "avg_tables_per_document": round(avg_table_count, 2),
                "avg_images_per_document": round(avg_image_count, 2),
                "avg_paragraph_length": round(avg_paragraph_length, 2),
                "avg_text_density_per_page": round(avg_text_density, 2)
            }
        }

        return JSONResponse(
            content={
                "global_statistics": global_statistics
            }
        )

    except Exception as e:
        logger.error(f"Error retrieving global statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving global statistics: {str(e)}")


@app.get("/documents/{document_uuid}/export/csv")
async def export_elements_csv(
        document_uuid: str,
        element_type: Optional[str] = Query(None, description="Element type to export")
):
    """Export document elements as CSV."""
    doc_info = doc_storage.get_document_by_uuid(document_uuid)
    if not doc_info:
        raise HTTPException(status_code=404, detail="Document not found")

    elements = doc_storage.get_document_elements(document_uuid, element_type=element_type)
    if not elements:
        element_name = element_type or "elements"
        raise HTTPException(status_code=404, detail=f"No {element_name} found")

    output = io.StringIO()
    writer = csv.writer(output)

    # Dynamic headers based on element type
    element_name = element_type or "Element"
    writer.writerow([f"{element_name.title()}_ID", "Page", "Type", "Content"])

    for i, element in enumerate(elements):
        writer.writerow([
            element["id"],
            element["page_number"],
            element["element_type"],
            element["content"]
        ])

    # Dynamic filename
    type_suffix = f"_{element_type}" if element_type else "_all"
    filename = f"{doc_info['filename']}{type_suffix}.csv"

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/documents/{document_uuid}/export/json")
async def export_metadata_json(document_uuid: str):
    """Export document metadata as JSON."""
    doc_info = doc_storage.get_document_by_uuid(document_uuid)
    if not doc_info:
        raise HTTPException(status_code=404, detail="Document not found")

    statistics = doc_storage.get_document_statistics(document_uuid)
    metadata = {"document_info": doc_info, "statistics": statistics}

    return Response(
        content=json.dumps(metadata, indent=2, default=str, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={doc_info['filename']}_metadata.json"}
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        content={
            "status": "healthy",
            "message": "PDF Document Analysis API is running"
        }
    )

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "PDF Document Analysis API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health_check": "/health"
    }

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)