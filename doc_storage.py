import sqlite3
import uuid
from file_parser import *
from pathlib import Path
import json
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


CREATE_DOC_TABLE = """
               CREATE TABLE IF NOT EXISTS documents (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            document_uuid TEXT UNIQUE NOT NULL,
                            filename TEXT NOT NULL,
                            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP )
                       """
CREATE_ELEM_TABLE  = """
            CREATE TABLE IF NOT EXISTS elements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                element_type TEXT NOT NULL,
                content TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                position_x0 REAL,
                position_y0 REAL,
                position_x1 REAL,
                position_y1 REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            )
        """
CREATE_STATISTICS_TABLE = """
                CREATE TABLE IF NOT EXISTS document_statistics (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            document_id INTEGER NOT NULL,
                            title_count INTEGER,
                            section_count INTEGER,
                            table_count INTEGER,
                            image_count INTEGER,
                            avg_text_density_per_page REAL,
                            avg_hierarchical_depth REAL,
                            avg_paragraph_length REAL,
                            section_distribution TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                        )
                       """


class DocumentStorage:
    """
    Handles storage of extracted documents in SQLite relational database.
    Designed for easy querying and analysis of document structures.
    """

    def __init__(self, db_path: str = "pdf_documents.sqlite"):
        """Initialize database connection and create tables if they don't exist."""
        self.db_path = db_path
        self._create_tables()

    def _create_tables(self):
        """Create database tables for storing document data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Documents table - stores metadata about each processed document
            cursor.execute(CREATE_DOC_TABLE)

            # Elements table - stores individual document elements
            cursor.execute(CREATE_ELEM_TABLE)

            # Statistics table - stores document-level statistics
            cursor.execute(CREATE_STATISTICS_TABLE)


            # Create indexes for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_elements_document_id ON elements(document_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_elements_type ON elements(element_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_elements_page ON elements(page_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_uuid ON documents(document_uuid)")

            conn.commit()
            logger.info("Database tables created/verified successfully")

    def save_document(self, pdf_path: str, elements: List[DocumentElement],
                      stats: DocumentStatistics, original_filename: str) -> str:
        """
        Save extracted document data to SQLite database.
        Returns the document UUID for reference.
        """
        document_uuid = str(uuid.uuid4())
        pdf_path = Path(pdf_path)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            try:
                # Insert document metadata
                cursor.execute("""
                               INSERT INTO documents (document_uuid, filename)
                               VALUES (?, ?)
                               """, (
                                   document_uuid,
                                   original_filename,
                               ))

                document_id = cursor.lastrowid
                logger.info(f"Document saved with ID: {document_id}, UUID: {document_uuid}")

                # Insert elements
                element_data = []
                for elem in elements:
                    element_data.append((
                        document_id,
                        elem.element_type.value,
                        elem.content,
                        elem.page_number,
                        elem.position.get('x0'),
                        elem.position.get('y0'),
                        elem.position.get('x1'),
                        elem.position.get('y1'),
                    ))

                cursor.executemany("""
                                   INSERT INTO elements (document_id, element_type, content, page_number,
                                                         position_x0, position_y0, position_x1, position_y1)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                   """, element_data)

                # Insert statistics
                cursor.execute("""
                               INSERT INTO document_statistics (document_id, title_count,
                                                                section_count, table_count,
                                                                image_count,
                                                                avg_text_density_per_page,
                                                                avg_hierarchical_depth, avg_paragraph_length,
                                                                section_distribution)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                               """, (
                                   document_id,
                                   stats.title_count,
                                   stats.section_count,
                                   stats.table_count,
                                   stats.image_count,
                                   stats.avg_text_density_per_page,
                                   stats.avg_hierarchical_depth,
                                   stats.avg_paragraph_length,
                                   json.dumps(stats.section_distribution)
                               ))

                conn.commit()
                logger.info(f"Successfully saved {len(elements)} elements to database")
                return document_uuid

            except Exception as e:
                conn.rollback()
                logger.error(f"Error saving document to database: {e}")
                raise

    def get_document_by_uuid(self, document_uuid: str) -> Optional[Dict[str, Any]]:
        """Retrieve document metadata by UUID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()

            cursor.execute("""
                           SELECT *
                           FROM documents
                           WHERE document_uuid = ?
                           """, (document_uuid,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def get_document_elements(self, document_uuid: str,
                              element_type: Optional[str] = None,
                              page_number: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve elements for a document with optional filtering.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Build query with optional filters
            query = """
                    SELECT e.*
                    FROM elements e
                             JOIN documents d ON e.document_id = d.id
                    WHERE d.document_uuid = ?
                    """
            params = [document_uuid]

            if element_type:
                query += " AND e.element_type = ?"
                params.append(element_type)

            if page_number:
                query += " AND e.page_number = ?"
                params.append(page_number)

            query += " ORDER BY e.page_number, e.position_y0 DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def get_document_statistics(self, document_uuid: str) -> Dict[str, Any]:
        """Retrieve document statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                           SELECT title_count, section_count, table_count, image_count,
                                  avg_text_density_per_page,
                                  avg_hierarchical_depth, avg_paragraph_length, section_distribution
                            FROM document_statistics ds
                                    JOIN documents d ON ds.document_id = d.id
                           WHERE d.document_uuid = ?
                           """, (document_uuid,))

            row = cursor.fetchone()
            if not row:
                return {}

            stats = dict(row)
            # Only parse section_distribution as JSON
            if stats.get('section_distribution'):
                stats['section_distribution'] = json.loads(stats['section_distribution'])

            return stats

    def list_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all processed documents."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                           SELECT document_uuid,
                                  filename,
                                  processed_at
                           FROM documents
                           ORDER BY processed_at DESC LIMIT ?
                           """, (limit,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_element_type_summary(self) -> Dict[str, int]:
        """Get summary of element types across all documents."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                           SELECT element_type, COUNT(*) as count
                           FROM elements
                           GROUP BY element_type
                           ORDER BY count DESC
                           """)

            rows = cursor.fetchall()
            return {row[0]: row[1] for row in rows}

    def search_content(self, search_term: str, document_uuid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for content across documents."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
                    SELECT e.*, d.filename, d.document_uuid
                    FROM elements e
                             JOIN documents d ON e.document_id = d.id
                    WHERE e.content LIKE ? \
                    """
            params = [f"%{search_term}%"]

            if document_uuid:
                query += " AND d.document_uuid = ?"
                params.append(document_uuid)

            query += " ORDER BY d.filename, e.page_number"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]
