from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import fitz  # PyMuPDF
import re
from pathlib import Path
import json
from collections import Counter, defaultdict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ElementType(Enum):
    """Enumeration for different types of document elements."""
    TITLE = "title"
    SUBTITLE = "subtitle"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    TABLE = "table"
    IMAGE = "image"


@dataclass
class DocumentElement:
    """
    Represents a single element extracted from the PDF.
    This structure is designed to be easily serializable for database storage.
    """
    element_type: ElementType
    content: str
    page_number: int
    position: Dict[str, float]  # x0, y0, x1, y1 coordinates
    font_info: Dict[str, Any]  # font name, size, flags

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy serialization."""
        return {
            'element_type': self.element_type.value,
            'content': self.content,
            'page_number': self.page_number,
            'position': self.position,
            'font_info': self.font_info,
        }


@dataclass
class DocumentStatistics:
    """Statistics about the extracted document structure."""
    title_count: int
    section_count: int
    table_count: int
    image_count: int
    avg_text_density_per_page: float
    avg_hierarchical_depth: float
    avg_paragraph_length: float
    section_distribution: Dict[int, int]
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy serialization."""
        return {
            'title_count': self.title_count,
            'section_count': self.section_count,
            'table_count': self.table_count,
            'image_count': self.image_count,
            'avg_text_density_per_page': self.avg_text_density_per_page,
            'avg_hierarchical_depth': self.avg_hierarchical_depth,
            'avg_paragraph_length': self.avg_paragraph_length,
            'section_distribution': self.section_distribution
        }


def classify_items(text: str, font_info: Dict[str, Any]) -> ElementType:
    """Font based classification."""
    text_stripped = text.strip()
    word_count = len(text_stripped.split())
    is_bold = bool(font_info['flags'] & 16)

    # List item pattern checking
    list_patterns = [
        r'^\s*[•·▪▫‣⁃]\s+',  # Bullet points
        r'^\s*\d+[\.\)]\s+',  # Numbered lists
        r'^\s*[a-zA-Z][\.\)]\s+',  # Lettered lists
        r'^\s*[-\*\+]\s+',  # Dash/asterisk lists
    ]
    if any(re.match(pattern, text_stripped) for pattern in list_patterns):
        return ElementType.LIST_ITEM

    # Font-size based classification
    if font_info['size'] >= 16 and is_bold:
        return ElementType.TITLE
    elif font_info['size'] >= 14 and (is_bold or word_count <= 10):
        return ElementType.SUBTITLE
    elif font_info['size'] >= 10 and (word_count <= 20):
        return ElementType.SECTION
    else:
        return ElementType.PARAGRAPH

class PDFExtractor:
    """Main class for extracting structure from PDF documents."""

    def extract_structure(self, pdf_path: str) -> Tuple[List[DocumentElement], DocumentStatistics]:
        """
        Extract structure from a PDF file.
        Returns list of elements and document statistics.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Processing PDF: {pdf_path.name}")

        # Open PDF document
        doc = fitz.open(str(pdf_path))
        elements = []

        try:
            # Extract elements from each page
            logger.info("Extracting document elements...")
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_elements = self._extract_page_elements(page, page_num + 1)
                elements.extend(page_elements)

            # Generate statistics
            logger.info("Generating document statistics...")
            stats = self._generate_statistics(doc, elements)

            logger.info(f"Extraction complete: {len(elements)} elements found")
            return elements, stats

        finally:
            doc.close()

    def _extract_page_elements(self, page, page_number: int) -> List[DocumentElement]:
        """Extract elements from a single page."""
        elements = []

        # Extract text blocks with formatting
        blocks = page.get_text("dict")

        for block in blocks.get("blocks", []):
            if "lines" in block:  # Text block
                text_content = ""
                font_info = {}
                position = {
                    'x0': round(block['bbox'][0], 4),
                    'y0': round(block['bbox'][1], 4),
                    'x1': round(block['bbox'][2], 4),
                    'y1': round(block['bbox'][3], 4)
                }

                # Collect text and font info from spans
                for line in block["lines"]:
                    for span in line["spans"]:
                        text_content += span["text"]
                        if not font_info:  # Use first span's font info
                            font_info = {
                                'name': span["font"],
                                'size': span["size"],
                                'flags': span["flags"]
                            }

                # Skip empty or whitespace-only blocks
                if not text_content.strip():
                    continue

                # Classify the element
                element_type = classify_items(text_content, font_info)

                element = DocumentElement(
                    element_type=element_type,
                    content=text_content.strip().replace("\n", " ").replace("\t", ""),
                    page_number=page_number,
                    position=position,
                    font_info=font_info,
                )

                elements.append(element)

        # Extract images
        image_list = page.get_images(full=True)

        for img_index, img in enumerate(image_list):
            # Get image bounding box
            img_rect = page.get_image_bbox(img)

            element = DocumentElement(
                element_type=ElementType.IMAGE,
                content=f"Image_{page_number}_{img_index}",
                page_number=page_number,
                position={
                    'x0': img_rect.x0,
                    'y0': img_rect.y0,
                    'x1': img_rect.x1,
                    'y1': img_rect.y1
                },
                font_info={},
            )
            elements.append(element)

        tables = page.find_tables()
        for table_index, table in enumerate(tables):
            table_data = table.extract()

            # Handle None values in table cells
            clean_table_data = []
            for row in table_data:
                clean_row = [str(cell) if cell is not None else '' for cell in row]
                clean_table_data.append(clean_row)

            # Create table text representation
            table_text = '\n'.join(['\t'.join(row) for row in clean_table_data])

            element = DocumentElement(
                element_type=ElementType.TABLE,
                content=table_text,
                page_number=page_number,
                position={
                    'x0': table.bbox[0],
                    'y0': table.bbox[1],
                    'x1': table.bbox[2],
                    'y1': table.bbox[3]
                },
                font_info={},
            )
            elements.append(element)

        return elements

    def _generate_statistics(self, doc, elements: List[DocumentElement]) -> DocumentStatistics:
        """Generate comprehensive statistics about the document."""

        # Page counts
        total_pages = len(doc)

        # Element type counts
        element_counts = Counter(elem.element_type.value for elem in elements)
        title_count = element_counts.get(ElementType.TITLE.value, 0)
        section_count = element_counts.get(ElementType.SECTION.value, 0)
        table_count = element_counts.get(ElementType.TABLE.value, 0)
        image_count = element_counts.get(ElementType.IMAGE.value, 0)

        # Text density per page
        text_density_per_page = []
        for page_num in range(1, total_pages + 1):
            page_elements = [e for e in elements if e.page_number == page_num]
            page_text_length = sum(len(e.content) for e in page_elements)
            text_density_per_page.append(page_text_length)
        avg_text_density_per_page = round(sum(text_density_per_page)/len(text_density_per_page), 2)

        # Average hierarchical depth
        hierarchical_elements = [e for e in elements if
                                 e.element_type in [ElementType.TITLE, ElementType.SUBTITLE, ElementType.SECTION]]
        hierarchical_counts_per_page = defaultdict(int)
        avg_hierarchical_depth = 0
        for elem in hierarchical_elements:
            hierarchical_counts_per_page[elem.page_number] += 1
        if len(hierarchical_counts_per_page) != 0:
            avg_hierarchical_depth = round(sum(hierarchical_counts_per_page.values()) / len(hierarchical_counts_per_page), 2)

        # Average paragraph length
        paragraphs = [e for e in elements if e.element_type == ElementType.PARAGRAPH]
        avg_paragraph_length = round(sum(len(p.content.split()) for p in paragraphs) / len(paragraphs), 2) if paragraphs else 0

        # Section distribution by page
        section_distribution = defaultdict(int)
        for elem in elements:
            if elem.element_type == ElementType.SECTION:
                section_distribution[elem.page_number] += 1

        return DocumentStatistics(
            title_count=title_count,
            section_count=section_count,
            table_count=table_count,
            image_count=image_count,
            avg_text_density_per_page=avg_text_density_per_page,
            avg_hierarchical_depth=avg_hierarchical_depth,
            avg_paragraph_length=avg_paragraph_length,
            section_distribution=dict(section_distribution)
        )


    def save_to_json(self, elements: List[DocumentElement],
                     stats: DocumentStatistics, output_path: str):
        """Save extracted data to JSON file."""
        data = {
            'elements': [elem.to_dict() for elem in elements],
            'statistics': stats.to_dict()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Data saved to: {output_path}")

    def load_from_json(self, input_path: str) -> Tuple[List[Dict], Dict]:
        """Load data from JSON file."""
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return data['elements'], data['statistics']


