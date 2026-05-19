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

"""Template engine for SOW document generation using Jinja2."""

import base64
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Temporarily removing markdown import to test WeasyPrint issue

from jinja2 import Environment, FileSystemLoader, select_autoescape

# from .models import SOWRequest  # No longer needed - using dictionaries

logger = logging.getLogger(__name__)


def format_timeline_text(timeline_text: str) -> str:
    """Convert timeline text with markdown-like formatting to HTML."""
    if not timeline_text:
        return ""
    
    # Convert **text** to <strong>text</strong>
    formatted = timeline_text.replace('**', '</strong>').replace('**', '<strong>')
    
    # Split on phases and create proper HTML structure
    phases = formatted.split('**Phase ')
    if len(phases) > 1:
        html_parts = []
        for i, phase in enumerate(phases[1:], 1):  # Skip first empty part
            phase_content = f"Phase {phase}"
            # Split phase title from content
            if ':' in phase_content:
                title_part, content_part = phase_content.split(':', 1)
                title_part = title_part.strip()
                content_part = content_part.strip()
                
                # Remove closing strong tag if present
                if content_part.startswith('</strong>'):
                    content_part = content_part[9:].strip()
                
                html_parts.append(f"<h4><strong>{title_part}</strong></h4>")
                html_parts.append(f"<p>{content_part}</p>")
            else:
                html_parts.append(f"<p>{phase_content}</p>")
        
        return '\n'.join(html_parts)
    else:
        # Fallback - just convert ** to strong tags
        formatted = formatted.replace('**', '<strong>').replace('**', '</strong>')
        # Convert - bullets to proper list items
        lines = formatted.split('\n')
        html_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith('- '):
                html_lines.append(f"<li>{line[2:]}</li>")
            elif line:
                html_lines.append(f"<p>{line}</p>")
        
        return '\n'.join(html_lines)


def get_template_path() -> str:
    """Get the path to the templates directory."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'templates')


def create_jinja_env() -> Environment:
    """Create and configure Jinja2 environment."""
    # This is a standalone MCP server, not a Flask application.
    # We've enabled autoescaping for all templates by default to prevent XSS vulnerabilities.
    # nosemgrep: python.flask.security.xss.audit.direct-use-of-jinja2.direct-use-of-jinja2
    env = Environment(
        loader=FileSystemLoader(get_template_path()),
        autoescape=True,  # Enable autoescaping for all templates by default
        trim_blocks=True,
        lstrip_blocks=True
    )
    
    # Add custom filters
    env.filters['currency'] = lambda x: f"${x:,.2f}"
    env.filters['date_format'] = lambda x: x.strftime("%B %d, %Y") if x else ""
    env.filters['month_year'] = lambda x: x.strftime("%B %Y") if x else ""
    env.filters['format_timeline'] = format_timeline_text
    
    return env


async def render_sow_template_simple(sow_data: Dict[str, Any]) -> str:
    """Render SOW template with simplified data structure including appendices."""
    env = create_jinja_env()
    
    # Determine template file based on template type
    template_files = {
        "aws_map": "aws_map_sow.html",
        "aws_modernization": "aws_modernization_sow.html", 
        "standard_migration": "standard_migration_sow.html"
    }
    
    template_file = template_files.get(
        sow_data.get('template_type'),
        "base_sow.html"
    )
    
    try:
        template = env.get_template(template_file)
    except Exception:
        # Fallback to base template if specific template not found
        template = env.get_template("base_sow.html")
    
    # Add current date and other template variables
    sow_data['current_date'] = datetime.now()
    
    # Render main template
    html_content = template.render(**sow_data)
    
    # Generate appendices section if appendices exist
    appendices = sow_data.get('appendices', {})
    if appendices:
        logger.info("Generating appendices section for SOW")
        appendices_html = await render_appendices_section(appendices)
        
        if appendices_html:
            # Insert appendices before closing body tag
            html_content = html_content.replace('</body>', f'{appendices_html}</body>')
            logger.info("Successfully added appendices to SOW HTML")
        else:
            logger.info("No appendices content to add")
    else:
        logger.info("No appendices data provided")
    
    return html_content

async def render_sow_template(sow_data: Dict[str, Any]) -> str:
    """Render SOW template with the provided data (legacy function - now uses dict)."""
    env = create_jinja_env()
    
    # Determine template file based on template type
    template_files = {
        "aws_map": "aws_map_sow.html",
        "aws_modernization": "aws_modernization_sow.html", 
        "standard_migration": "standard_migration_sow.html"
    }
    
    template_file = template_files.get(
        sow_data.get('template_type'),
        "aws_map_sow.html"
    )
    
    logger.info(f"TEMPLATE_DEBUG: Using template '{template_file}' for type '{sow_data.get('template_type')}'")
    
    try:
        template = env.get_template(template_file)
    except Exception:
        # Fallback to base template if specific template not found
        template = env.get_template("base_sow.html")
    
    # Add current date and other template variables
    sow_data['current_date'] = datetime.now()
    
    # Render template
    html_content = template.render(**sow_data)
    
    return html_content


async def render_appendices_section(appendices: Dict[str, Any]) -> str:
    """Generate HTML for appendices section with embedded content.
    
    Args:
        appendices: Dictionary containing appendices data with content loaded
        
    Returns:
        HTML string for appendices section
    """
    if not appendices:
        return ""
    
    # Check if we have any appendices to render
    has_appendices = any(data.get("content") is not None for data in appendices.values())
    if not has_appendices:
        logger.info("No appendices content found, skipping appendices section")
        return ""
    
    logger.info("Rendering appendices section with embedded content")
    appendices_html = ['<div class="appendices-section">']
    appendices_html.append('<h1 style="page-break-before: always;">Appendices</h1>')
    
    appendix_letter = 'A'
    
    # 1. Embed architecture diagram if available
    if appendices.get("diagram", {}).get("content"):
        logger.info("Rendering architecture diagram appendix")
        diagram_data = appendices["diagram"]["content"]
        diagram_base64 = base64.b64encode(diagram_data).decode('utf-8')
        
        appendices_html.extend([
            '<div class="appendix-section">',
            f'<h2>Appendix {appendix_letter}: {appendices["diagram"]["title"]}</h2>',
            f'<p>{appendices["diagram"]["description"]}</p>',
            '<div class="diagram-container">',
            f'<img src="data:image/png;base64,{diagram_base64}" ',
            'style="max-width: 90%; height: auto; page-break-inside: avoid;" />',
            '</div>',
            '</div>'
        ])
        appendix_letter = chr(ord(appendix_letter) + 1)
    
    # 2. Embed pricing report content if available
    if appendices.get("pricing_report", {}).get("content"):
        logger.info("Rendering pricing report appendix")
        pricing_content = appendices["pricing_report"]["content"]
        
        # Convert markdown content to HTML
        import markdown2
        pricing_html = markdown2.markdown(pricing_content, extras=['tables', 'fenced-code-blocks'])
        
        appendices_html.extend([
            '<div class="appendix-section">',
            f'<h2>Appendix {appendix_letter}: {appendices["pricing_report"]["title"]}</h2>',
            f'<p>{appendices["pricing_report"]["description"]}</p>',
            '<div class="markdown-content">',
            pricing_html,
            '</div>',
            '</div>'
        ])
        appendix_letter = chr(ord(appendix_letter) + 1)
    
    # 3. Embed funding document content if available
    if appendices.get("funding_document", {}).get("content"):
        logger.info("Rendering funding document appendix")
        funding_content = appendices["funding_document"]["content"]
        
        # Convert markdown content to HTML
        funding_html = markdown2.markdown(funding_content, extras=['tables', 'fenced-code-blocks'])
        
        appendices_html.extend([
            '<div class="appendix-section">',
            f'<h2>Appendix {appendix_letter}: {appendices["funding_document"]["title"]}</h2>',
            f'<p>{appendices["funding_document"]["description"]}</p>',
            '<div class="markdown-content">',
            funding_html,
            '</div>',
            '</div>'
        ])
    
    appendices_html.append('</div>')
    
    final_html = '\n'.join(appendices_html)
    logger.info(f"Generated appendices HTML ({len(final_html)} characters)")
    
    return final_html


def prepare_template_context(sow_data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare the context data for template rendering (legacy function - now uses dict)."""
    # This function is no longer needed since we moved to render_sow_template_simple
    # but keeping it for backward compatibility
    logger.warning("prepare_template_context is deprecated - use render_sow_template_simple instead")
    return sow_data