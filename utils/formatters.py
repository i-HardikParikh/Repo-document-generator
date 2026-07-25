import json
import yaml
import io
from pathlib import Path
from typing import Dict, Any, Optional, Union, Callable
import markdown
from markdown.extensions.toc import TocExtension
from PyPDF2 import PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

class DocumentFormatter:
    """Handles conversion of documentation to various output formats."""
    
    @staticmethod
    def to_markdown(data: Dict[str, Any]) -> str:
        """Convert data to Markdown format."""
        return data.get('content', '')
    
    @staticmethod
    def to_html(data: Dict[str, Any]) -> str:
        """Convert markdown content to HTML with syntax highlighting."""
        content = data.get('content', '')
        return markdown.markdown(
            content,
            extensions=[
                'fenced_code',
                'codehilite',
                'tables',
                'toc',
                TocExtension(toc_depth=3)
            ],
            output_format='html5'
        )

    @staticmethod
    def to_json(data: Dict[str, Any], indent: int = 2) -> str:
        """Convert data to JSON format."""
        return json.dumps(data, indent=indent, ensure_ascii=False)

    @staticmethod
    def to_yaml(data: Dict[str, Any], **kwargs) -> str:
        """Convert data to YAML format."""
        default_kwargs = {
            'default_flow_style': False,
            'allow_unicode': True,
            'sort_keys': False
        }
        default_kwargs.update(kwargs)
        return yaml.dump(data, **default_kwargs)

    @staticmethod
    def to_pdf(data: Dict[str, Any], **kwargs) -> bytes:
        """
        Convert content to PDF using ReportLab for content creation
        and PyPDF for final assembly.
        
        Args:
            data: Dictionary containing 'content' with markdown text
            **kwargs: Additional arguments for PDF generation
            
        Returns:
            bytes: PDF file as bytes
            
        Raises:
            ValueError: If there's an error generating the PDF
        """
        try:
            # Create a buffer to hold the PDF
            buffer = io.BytesIO()
            
            # Create the PDF object with ReportLab
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=72, leftMargin=72,
                topMargin=72, bottomMargin=72
            )
            
            # Get styles
            styles = getSampleStyleSheet()
            
            # Define custom styles - only add if not already defined
            if 'Code' not in styles:
                styles.add(ParagraphStyle(
                    'Code',
                    fontName='Courier',
                    fontSize=9,
                    leading=12,
                    leftIndent=0,
                    rightIndent=0,
                    firstLineIndent=0,
                    alignment=0,
                    spaceBefore=6,
                    spaceAfter=6,
                    bulletFontName='Helvetica',
                    bulletFontSize=10,
                    bulletIndent=0,
                    textColor='black',
                    backColor=None,
                    wordWrap='LTR',
                    borderWidth=0,
                    borderPadding=0,
                    borderColor=None,
                    borderRadius=None,
                    allowWidows=1,
                    allowOrphans=0,
                    textTransform=None,
                    endDots=None,
                    splitLongWords=1,
                ))
            
            # Prepare content
            content = []
            
            # Add title
            title = data.get('metadata', {}).get('title', 'Documentation')
            if title:
                content.append(Paragraph(title, styles['Title']))
                content.append(Spacer(1, 12))
            
            # Add generation date if available
            if 'generated_at' in data.get('metadata', {}):
                date_str = f"<i>Generated on: {data['metadata']['generated_at']}</i>"
                content.append(Paragraph(date_str, styles['Italic']))
                content.append(Spacer(1, 24))
            
            # Get the markdown content
            markdown_content = data.get('content', '')
            if not markdown_content:
                raise ValueError("No content provided for PDF generation")
                
            # Convert markdown to simple paragraphs
            for line in markdown_content.split('\n'):
                line = line.strip()
                if not line:
                    content.append(Spacer(1, 12))
                    continue
                    
                # Simple markdown parsing
                if line.startswith('# '):
                    content.append(Paragraph(line[2:], styles['Heading1']))
                elif line.startswith('## '):
                    content.append(Paragraph(line[3:], styles['Heading2']))
                elif line.startswith('### '):
                    content.append(Paragraph(line[4:], styles['Heading3']))
                elif line.startswith('    '):  # Code block
                    content.append(Paragraph(f'<code>{line[4:]}</code>', styles['Code']))
                elif '`' in line:  # Inline code
                    parts = []
                    in_code = False
                    for part in line.split('`'):
                        if in_code:
                            parts.append(f'<code>{part}</code>')
                        else:
                            parts.append(part)
                        in_code = not in_code
                    content.append(Paragraph(''.join(parts), styles['Normal']))
                else:  # Normal text
                    content.append(Paragraph(line, styles['Normal']))
            
            # Build the PDF
            doc.build(content)
            
            # Get the PDF bytes and close the buffer
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            if not pdf_bytes:
                raise ValueError("Failed to generate PDF content")
                
            return pdf_bytes
            
        except Exception as e:
            raise ValueError(f"Error generating PDF: {str(e)}")

def get_formatter(format_type: str) -> Callable:
    """
    Get the appropriate formatter function.
    
    Args:
        format_type: The requested format (e.g., 'markdown', 'html', 'pdf')
        
    Returns:
        Callable: The formatter function for the requested format
        
    Raises:
        ValueError: If the requested format is not supported
    """
    if not format_type:
        raise ValueError("No format specified. Supported formats: markdown, html, json, yaml, pdf")
    
    # Normalize the format string
    normalized = format_type.lower().strip().replace('.', '').replace(' ', '')
    
    # Handle common format aliases
    format_aliases = {
        'md': 'markdown',
        'yml': 'yaml',
        'pdf': 'pdf'  # Explicitly include pdf in aliases
    }
    
    # Get the canonical format name
    canonical_format = format_aliases.get(normalized, normalized)
    
    # Create a mapping of format names to their respective DocumentFormatter methods
    formatters = {
        'markdown': DocumentFormatter.to_markdown,
        'html': DocumentFormatter.to_html,
        'json': DocumentFormatter.to_json,
        'yaml': DocumentFormatter.to_yaml,
        'pdf': DocumentFormatter.to_pdf  # Ensure this matches the method name in DocumentFormatter
    }
    
    # Debug: Print available formats and requested format
    print(f"Available formats: {list(formatters.keys())}")
    print(f"Requested format: '{format_type}' -> Canonical format: '{canonical_format}'")
    
    if canonical_format not in formatters:
        supported = ', '.join(f"'{f}'" for f in formatters.keys())
        raise ValueError(f"Unsupported format: '{format_type}'. Supported formats: {supported}")
    
    formatter = formatters[canonical_format]
    if formatter is None:
        raise ValueError(f"Formatter for format '{format_type}' is not properly configured")
        
    return formatter

def get_content_type(format_type: str) -> str:
    """
    Get the MIME type for the specified format.
    
    Args:
        format_type: The format to get the MIME type for
        
    Returns:
        str: The MIME type for the format
        
    Raises:
        ValueError: If the format is not supported
    """
    if not format_type:
        raise ValueError("No format specified. Supported formats: markdown, html, json, yaml, pdf")
        
    # Normalize the format string
    normalized = format_type.lower().strip().replace('.', '').replace(' ', '')
    
    # Handle common format aliases
    format_aliases = {
        'md': 'markdown',
        'yml': 'yaml'
    }
    
    # Get the canonical format name
    canonical_format = format_aliases.get(normalized, normalized)
    
    content_types = {
        'markdown': 'text/markdown',
        'html': 'text/html',
        'json': 'application/json',
        'yaml': 'application/yaml',
        'pdf': 'application/pdf'
    }
    
    if canonical_format not in content_types:
        supported = ', '.join(f"'{f}'" for f in content_types.keys())
        raise ValueError(f"Unsupported format: '{format_type}'. Supported formats: {supported}")
    
    return content_types[canonical_format]

def get_file_extension(format_type: str) -> str:
    """
    Get the standard file extension for the specified format.
    
    Args:
        format_type: The format to get the extension for
        
    Returns:
        str: The file extension (without dot)
        
    Raises:
        ValueError: If the format is not supported
    """
    if not format_type:
        raise ValueError("No format specified. Supported formats: markdown, html, json, yaml, pdf")
        
    # Normalize the format string
    normalized = format_type.lower().strip().replace('.', '').replace(' ', '')
    
    # Handle common format aliases
    format_aliases = {
        'md': 'markdown',
        'yml': 'yaml'
    }
    
    # Get the canonical format name
    canonical_format = format_aliases.get(normalized, normalized)
    
    extensions = {
        'markdown': 'md',
        'html': 'html',
        'json': 'json',
        'yaml': 'yaml',
        'pdf': 'pdf'
    }
    
    if canonical_format not in extensions:
        supported = ', '.join(f"'{f}'" for f in extensions.keys())
        raise ValueError(f"Unsupported format: '{format_type}'. Supported formats: {supported}")
    
    return extensions[canonical_format]