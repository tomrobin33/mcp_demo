#!/usr/bin/env python3
"""
MCP Server Startup Script

This script provides a convenient way to start the File Converter MCP server
with proper configuration and error handling.
"""

import sys
import os
import logging
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def setup_logging():
    """Setup logging configuration for the MCP server"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr)  # 将日志输出到stderr
        ]
    )
    
    # Set MCP specific logging
    mcp_logger = logging.getLogger("mcp")
    mcp_logger.setLevel(logging.INFO)
    
    return logging.getLogger("file_converter_mcp")

def check_dependencies():
    """Check if all required dependencies are available"""
    try:
        import mcp
        import docx2pdf
        import pdf2docx
        from PIL import Image
        import pandas
        import pdfkit
        import markdown
        print("✓ All dependencies are available", file=sys.stderr)
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}", file=sys.stderr)
        print("Please run: python -m pip install -e .", file=sys.stderr)
        return False

def main():
    """Main entry point for the MCP server"""
    print("Starting File Converter MCP Server...", file=sys.stderr)
    
    # Setup logging
    logger = setup_logging()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    try:
        # Import and run the MCP server
        from file_converter_server import mcp
        
        print("✓ MCP server initialized successfully", file=sys.stderr)
        print("✓ Available tools:", file=sys.stderr)
        print("  - docx2pdf: Convert Word documents to PDF", file=sys.stderr)
        print("  - pdf2docx: Convert PDF to Word documents", file=sys.stderr)
        print("  - convert_image: Convert between image formats", file=sys.stderr)
        print("  - excel2csv: Convert Excel files to CSV", file=sys.stderr)
        print("  - html2pdf: Convert HTML/Markdown to PDF", file=sys.stderr)
        print("  - convert_file: Generic file conversion", file=sys.stderr)
        print("  - convert_content: Convert from base64 content", file=sys.stderr)
        print("  - upload_pdf_to_server: Upload PDF files to server", file=sys.stderr)
        print("  - upload_file_to_server: Upload any file format to server", file=sys.stderr)
        print("\nStarting server...", file=sys.stderr)
        
        # Run the MCP server
        mcp.run()
        
    except KeyboardInterrupt:
        print("\n✓ Server stopped by user", file=sys.stderr)
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 