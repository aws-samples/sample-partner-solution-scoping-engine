# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""PDF generation module using fpdf for SOW documents."""

import base64
import io
import logging
import os
import re
import tempfile
from typing import Optional

from fpdf import FPDF


logger = logging.getLogger(__name__)


class SOWPDF(FPDF):
    """Custom PDF class for SOW documents."""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
        """Add header to each page."""
        self.set_font('Arial', 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, 'Statement of Work', 0, 1, 'C')
        self.ln(5)
        
    def footer(self):
        """Add footer to each page."""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def strip_html_tags(html_text: str) -> str:
    """Remove HTML tags and convert basic formatting."""
    if not html_text:
        return ""
    
    # Convert common HTML entities
    html_text = html_text.replace('&amp;', '&')
    html_text = html_text.replace('&lt;', '<')
    html_text = html_text.replace('&gt;', '>')
    html_text = html_text.replace('&nbsp;', ' ')
    
    # Remove HTML tags but preserve basic structure
    html_text = re.sub(r'<br\s*/?>', '\n', html_text)
    html_text = re.sub(r'<p[^>]*>', '\n', html_text)
    html_text = re.sub(r'</p>', '\n', html_text)
    html_text = re.sub(r'<li[^>]*>', '• ', html_text)
    html_text = re.sub(r'</li>', '\n', html_text)
    html_text = re.sub(r'<h[1-6][^>]*>', '\n', html_text)
    html_text = re.sub(r'</h[1-6]>', '\n', html_text)
    html_text = re.sub(r'<div[^>]*>', '\n', html_text)
    html_text = re.sub(r'</div>', '\n', html_text)
    
    # Remove all remaining HTML tags
    html_text = re.sub(r'<[^>]+>', '', html_text)
    
    # Clean up whitespace
    html_text = re.sub(r'\n\s*\n', '\n\n', html_text)
    html_text = html_text.strip()
    
    return html_text


def extract_images_from_html(html_content: str) -> list:
    """Extract base64 images from HTML content."""
    images = []
    img_pattern = r'<img[^>]+src="data:image/([^;]+);base64,([^"]+)"[^>]*>'
    
    for match in re.finditer(img_pattern, html_content):
        img_format = match.group(1)
        img_data = match.group(2)
        
        try:
            # Decode base64 image
            img_bytes = base64.b64decode(img_data)
            images.append({
                'format': img_format,
                'data': img_bytes,
                'placeholder': match.group(0)
            })
        except Exception as e:
            logger.warning(f"Failed to decode image: {e}")
    
    return images


async def generate_sow_pdf(html_content: str, output_path: str, sow_request=None) -> str:
    """Generate PDF from HTML content using fpdf.
    
    Args:
        html_content: HTML content to convert to PDF
        output_path: Path where the PDF should be saved
        sow_request: Original SOW request object with data (unused)
        
    Returns:
        Path to the generated PDF file
        
    Raises:
        Exception: If PDF generation fails
    """
    try:
        logger.info(f"Generating PDF with fpdf at {output_path}")
        logger.info(f"HTML content length: {len(html_content)}")
        
        # Create PDF instance
        pdf = SOWPDF()
        pdf.add_page()
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(0, 0, 0)
        
        # Extract images from HTML
        images = extract_images_from_html(html_content)
        
        # Remove images from HTML for text processing
        text_content = html_content
        for img in images:
            text_content = text_content.replace(img['placeholder'], '\n[DIAGRAM]\n')
        
        # Convert HTML to plain text
        plain_text = strip_html_tags(text_content)
        
        # Split content into sections
        sections = plain_text.split('\n\n')
        
        for section in sections:
            if not section.strip():
                continue
                
            # Handle special markers
            if '[DIAGRAM]' in section:
                # Add images
                for img in images:
                    try:
                        # Save image temporarily using secure temp file
                        with tempfile.NamedTemporaryFile(suffix=f'.{img["format"]}', delete=False) as temp_file:
                            temp_file.write(img['data'])
                            img_path = temp_file.name
                        
                        # Add image to PDF
                        pdf.ln(5)
                        pdf.cell(0, 10, 'Architecture Diagram:', 0, 1, 'L')
                        pdf.ln(2)
                        
                        # Calculate image size to fit page
                        img_width = 150  # Max width
                        pdf.image(img_path, x=30, w=img_width)
                        pdf.ln(10)
                        
                        # Clean up temp file
                        os.unlink(img_path)
                        
                    except Exception as e:
                        logger.warning(f"Failed to add image to PDF: {e}")
                        pdf.cell(0, 10, '[Diagram could not be displayed]', 0, 1, 'C')
                        pdf.ln(5)
                continue
            
            # Detect headers (lines that end with ':' or are all caps)
            lines = section.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this looks like a header
                if (line.endswith(':') or 
                    (line.isupper() and len(line) > 3) or 
                    any(header in line.lower() for header in ['appendix', 'statement of work', 'executive summary'])):
                    
                    pdf.ln(5)
                    pdf.set_font('Arial', 'B', 14)
                    pdf.set_text_color(35, 47, 62)  # AWS dark blue
                    pdf.cell(0, 10, line, 0, 1, 'L')
                    pdf.ln(3)
                    pdf.set_font('Arial', '', 11)
                    pdf.set_text_color(0, 0, 0)
                    
                elif line.startswith('•'):
                    # Bullet point
                    pdf.cell(0, 6, line, 0, 1, 'L')
                    
                else:
                    # Regular text
                    # Handle long lines by wrapping
                    if len(line) > 80:
                        words = line.split(' ')
                        current_line = ""
                        for word in words:
                            if len(current_line + word) < 80:
                                current_line += word + " "
                            else:
                                if current_line:
                                    pdf.cell(0, 6, current_line.strip(), 0, 1, 'L')
                                current_line = word + " "
                        if current_line:
                            pdf.cell(0, 6, current_line.strip(), 0, 1, 'L')
                    else:
                        pdf.cell(0, 6, line, 0, 1, 'L')
            
            pdf.ln(2)
        
        # Save PDF
        pdf.output(output_path)
        
        logger.info(f"Successfully generated PDF: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to generate PDF with fpdf: {e}", exc_info=True)
        raise Exception(f"PDF generation failed: {str(e)}")