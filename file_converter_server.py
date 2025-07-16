"""
File Converter MCP Server

This MCP server provides multiple file conversion tools for AI Agents to use.
It supports various file format conversions such as:
- DOCX to PDF
- PDF to DOCX
- Image format conversions
- And more

The server is built using the Model Context Protocol (MCP) Python SDK.
"""

from mcp.server.fastmcp import FastMCP, Context
import os
import base64
from pathlib import Path
import tempfile
import mimetypes
import json
import glob
import logging
import sys
import time
import traceback
import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("file_converter_mcp")

# Initialize MCP server
mcp = FastMCP("File Converter")

# Helper functions
def validate_file_exists(file_path: str, expected_extension: str = None) -> str:
    """
    Validate that a file exists and optionally check its extension.
    Returns the actual file path that exists.
    """
    logger.info(f"Looking for file: {file_path}")
    
    # First check if the file exists as is
    path = Path(file_path)
    if path.exists():
        logger.info(f"Found file at original path: {file_path}")
        # Check extension if needed
        if expected_extension and not file_path.lower().endswith(expected_extension.lower()):
            raise ValueError(f"File must have {expected_extension} extension, got: {file_path}")
        return file_path

    # Get the filename and possible variations
    filename = os.path.basename(file_path)
    filename_no_ext = os.path.splitext(filename)[0]
    possible_filenames = [
        filename,  # Original filename
        filename.lower(),  # Lowercase version
        filename.upper(),  # Uppercase version
    ]
    
    # If an extension is expected, add variants with that extension
    if expected_extension:
        for name in list(possible_filenames):  # Create a copy to iterate over
            name_no_ext = os.path.splitext(name)[0]
            possible_filenames.append(f"{name_no_ext}{expected_extension}")
            possible_filenames.append(f"{name_no_ext}{expected_extension.lower()}")
    
    # Add wildcard pattern for files with similar names (ignoring case)
    for name in list(possible_filenames):
        name_no_ext = os.path.splitext(name)[0]
        possible_filenames.append(f"{name_no_ext}.*")
    
    logger.info(f"Looking for file variations: {possible_filenames}")
    
    # Places to search
    search_locations = []
    
    # Current directory and subdirectories (recursive)
    search_locations.append(".")
    
    # Temp directories
    temp_dir = tempfile.gettempdir()
    search_locations.append(temp_dir)
    
    # Common upload directories
    for common_dir in ['/tmp', './uploads', '/var/tmp', '/var/upload', os.path.expanduser('~/tmp'), os.path.expanduser('~/Downloads')]:
        if os.path.exists(common_dir):
            search_locations.append(common_dir)
    
    # Claude specific upload locations (based on observation)
    claude_dirs = ['./claude_uploads', './uploads', './input', './claude_files', '/tmp/claude']
    for claude_dir in claude_dirs:
        if os.path.exists(claude_dir):
            search_locations.append(claude_dir)
    
    logger.info(f"Searching in locations: {search_locations}")
    
    # Gather all files in these locations
    all_files = []
    for location in search_locations:
        logger.info(f"Searching in: {location}")
        # First try direct match
        for name in possible_filenames:
            if "*" not in name:  # Skip wildcard patterns for direct match
                potential_path = os.path.join(location, name)
                if os.path.exists(potential_path):
                    logger.info(f"Found direct match: {potential_path}")
                    all_files.append(potential_path)
        
        # Then try recursive search with wildcard patterns
        try:
            for name in possible_filenames:
                pattern = os.path.join(location, "**", name)
                matches = glob.glob(pattern, recursive=True)
                if matches:
                    logger.info(f"Found matches for pattern {pattern}: {matches}")
                    all_files.extend(matches)
        except Exception as e:
            logger.warning(f"Error during recursive search in {location}: {str(e)}")
    
    # Log all the files found
    logger.info(f"All found files: {all_files}")
    
    # If we found matches, use the most likely one
    if all_files:
        # Prioritize exact matches
        for file in all_files:
            if os.path.basename(file) == filename:
                logger.info(f"Selected exact match: {file}")
                return file
        
        # If no exact match, use the first file found
        actual_path = all_files[0]
        logger.info(f"Selected first match: {actual_path}")
        
        # Check extension if needed
        if expected_extension and not actual_path.lower().endswith(expected_extension.lower()):
            logger.warning(f"File doesn't have expected extension {expected_extension}: {actual_path}")
            # Let's be flexible and NOT raise an error here, just log a warning
            # raise ValueError(f"File must have {expected_extension} extension, got: {actual_path}")
        
        return actual_path
    
    # Special case for Claude: try to use a simple glob in the current directory
    try:
        # This is a common pattern in Claude uploads - it adds random numbers
        last_resort_patterns = [
            f"*{filename}*",  # Anything containing the filename
            f"*{filename_no_ext}*.*",  # Anything containing the filename without extension
        ]
        
        for pattern in last_resort_patterns:
            logger.info(f"Trying last resort pattern: {pattern}")
            matches = glob.glob(pattern)
            if matches:
                logger.info(f"Found last resort matches: {matches}")
                for match in matches:
                    if os.path.isfile(match):
                        if expected_extension and not match.lower().endswith(expected_extension.lower()):
                            logger.warning(f"Last resort file doesn't have expected extension {expected_extension}: {match}")
                            # Be flexible here too
                        logger.info(f"Selected last resort file: {match}")
                        return match
    except Exception as e:
        logger.warning(f"Error during last resort search: {str(e)}")
    
    # If we reach here, we couldn't find the file
    error_msg = f"File not found: {file_path}. Searched in multiple locations with various filename patterns."
    logger.error(error_msg)
    raise ValueError(error_msg)

def get_base64_encoded_file(file_path: str) -> str:
    """
    Read a file and return its base64 encoded content.
    """
    with open(file_path, "rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")

def format_error_response(error_msg: str) -> dict:
    """
    Format error message as a proper JSON response.
    """
    # Ensure returning a pure dictionary without any prefix
    return {
        "success": False,
        "error": str(error_msg)
    }

def format_success_response(data: str) -> dict:
    """
    Format successful response as a proper JSON response.
    """
    # Ensure returning a pure dictionary without any prefix
    return {
        "success": True,
        "data": data
    }

# Custom JSON encoder to ensure all responses are valid JSON
class SafeJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that safely handles various types.
    """
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            # For objects that cannot be serialized, convert to string
            return str(obj)

# 修改debug_json_response函数
def debug_json_response(response):
    """
    Debug JSON response to ensure it's valid.
    """
    try:
        # 使用自定义编码器确保所有响应都是有效的JSON
        json_str = json.dumps(response, cls=SafeJSONEncoder)
        json.loads(json_str)  # 验证JSON是否有效
        logger.info(f"Valid JSON response: {json_str[:100]}...")
        return response
    except Exception as e:
        logger.error(f"Invalid JSON response: {str(e)}")
        logger.error(f"Response type: {type(response)}")
        logger.error(f"Response content: {str(response)[:100]}...")
        # 返回一个安全的错误响应
        return {"success": False, "error": "Internal server error: Invalid JSON response"}

# Enhanced JSON parsing
original_parse_json = mcp.parse_json if hasattr(mcp, 'parse_json') else None

def enhanced_parse_json(text):
    """Enhanced JSON parsing with detailed error information"""
    try:
        # Check if there's a non-JSON prefix
        if text and not text.strip().startswith('{') and not text.strip().startswith('['):
            # Try to find the start of JSON
            json_start = text.find('{')
            if json_start == -1:
                json_start = text.find('[')
            
            if json_start > 0:
                logger.warning(f"Found non-JSON prefix: '{text[:json_start]}'")
                text = text[json_start:]
                logger.info(f"Stripped prefix, new text: '{text[:100]}...'")
        
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        logger.error(f"Problematic string: '{text}'")
        logger.error(f"Position {e.pos}: {text[max(0, e.pos-10):e.pos]}[HERE>{text[e.pos:e.pos+1]}<HERE]{text[e.pos+1:min(len(text), e.pos+10)]}")
        logger.error(f"Full error: {traceback.format_exc()}")
        raise

# If mcp has parse_json attribute, replace it
if hasattr(mcp, 'parse_json'):
    mcp.parse_json = enhanced_parse_json
else:
    logger.warning("Cannot enhance JSON parsing, mcp object doesn't have parse_json attribute")

# 辅助函数：判断input_file是否为URL并自动下载

def download_file_from_url(url):
    """
    下载远程文件到本地临时文件，返回本地路径
    """
    response = requests.get(url, stream=True)
    response.raise_for_status()
    suffix = os.path.splitext(url.split("?")[0])[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        for chunk in response.iter_content(chunk_size=8192):
            tmp_file.write(chunk)
        return tmp_file.name

def handle_input_file_with_url(input_file, expected_extension: str = None):
    """
    如果input_file是URL则下载，否则走原有逻辑。返回(实际本地路径, 是否为临时文件)
    """
    if input_file and (input_file.startswith("http://") or input_file.startswith("https://")):
        local_path = download_file_from_url(input_file)
        return local_path, True
    elif input_file:
        # 只在expected_extension不为None时传递
        if expected_extension:
            path = validate_file_exists(input_file, expected_extension)
        else:
            path = validate_file_exists(input_file)
        return path, False
    else:
        return None, False

def download_url_to_tempfile(url, suffix):
    """下载URL内容到临时文件，返回临时文件路径"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        response = requests.get(url)
        response.raise_for_status()
        tmp_file.write(response.content)
        return tmp_file.name

# 在OUTPUT_DIR定义后自动创建目录
OUTPUT_DIR = "/root/files"
import os
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_download_url(filename):
    host = "8.156.74.79"
    port = 8001
    return f"http://{host}:{port}/{filename}"

# DOCX to PDF conversion tool
@mcp.tool("docx2pdf")
def convert_docx_to_pdf(input_file: str = None, file_content_base64: str = None) -> dict:
    try:
        logger.info(f"Starting DOCX to PDF conversion")
        temp_files = []
        # 如果input_file是URL，自动下载到临时文件
        if input_file and (input_file.startswith("http://") or input_file.startswith("https://")):
            try:
                input_file = download_url_to_tempfile(input_file, ".docx")
                temp_files.append(input_file)
                logger.info(f"已下载DOCX到临时文件: {input_file}, 大小: {os.path.getsize(input_file) if os.path.exists(input_file) else '不存在'} 字节")
            except Exception as e:
                logger.error(f"下载DOCX失败: {str(e)}")
                return {"success": False, "error": f"Error downloading file from URL: {str(e)}"}
        if input_file is None and file_content_base64 is None:
            return {"success": False, "error": "You must provide either input_file or file_content_base64"}
        temp_dir = tempfile.mkdtemp()
        temp_input_file = os.path.join(temp_dir, f"input_{int(time.time())}.docx")
        temp_output_file = os.path.join(temp_dir, f"output_{int(time.time())}.pdf")
        # Handle direct content mode
        if file_content_base64:
            try:
                file_content = base64.b64decode(file_content_base64)
                with open(temp_input_file, "wb") as f:
                    f.write(file_content)
                actual_file_path = temp_input_file
                logger.info(f"已写入base64 DOCX到临时文件: {temp_input_file}, 大小: {os.path.getsize(temp_input_file)} 字节")
            except Exception as e:
                import shutil
                shutil.rmtree(temp_dir)
                logger.error(f"写入base64 DOCX失败: {str(e)}")
                return {"success": False, "error": f"Error processing input file content: {str(e)}"}
        else:
            try:
                actual_file_path = input_file
            except Exception as e:
                import shutil
                shutil.rmtree(temp_dir)
                for f in temp_files:
                    os.remove(f)
                logger.error(f"查找DOCX文件失败: {str(e)}")
                return {"success": False, "error": f"Error finding DOCX file: {str(e)}"}
        try:
            from docx2pdf import convert
            logger.info(f"开始转换: {actual_file_path} -> {temp_output_file}")
            convert(actual_file_path, temp_output_file)
        except Exception as e:
            import shutil
            shutil.rmtree(temp_dir)
            for f in temp_files:
                os.remove(f)
            logger.error(f"DOCX转换异常: {str(e)}")
            return {"success": False, "error": f"Error converting DOCX to PDF: {str(e)}"}
        import shutil
        output_file = f"{OUTPUT_DIR}/output_{int(time.time())}.pdf"
        logger.info(f"准备保存输出文件到: {output_file}")
        try:
            shutil.move(temp_output_file, output_file)
            logger.info(f"已成功保存输出文件到: {output_file}")
        except Exception as e:
            logger.error(f"移动输出文件失败: {str(e)}")
            shutil.rmtree(temp_dir)
            for f in temp_files:
                os.remove(f)
            return {"success": False, "error": f"Error moving output file: {str(e)}"}
        shutil.rmtree(temp_dir)
        for f in temp_files:
            os.remove(f)
        return {"success": True, "output_file": output_file, "download_url": get_download_url(os.path.basename(output_file))}
    except Exception as e:
        logger.error(f"Unexpected error in convert_docx_to_pdf: {str(e)}")
        return debug_json_response(format_error_response(f"Error converting DOCX to PDF: {str(e)}"))

# PDF to DOCX conversion tool
@mcp.tool("pdf2docx")
def convert_pdf_to_docx(input_file: str = None, file_content_base64: str = None) -> dict:
    """
    Convert a PDF file to DOCX format. Supports both file path, URL, and direct file content input.
    """
    try:
        logger.info(f"Starting PDF to DOCX conversion")
        temp_files = []
        # 如果input_file是URL，自动下载到临时文件
        if input_file and (input_file.startswith("http://") or input_file.startswith("https://")):
            try:
                input_file = download_url_to_tempfile(input_file, ".pdf")
                temp_files.append(input_file)
                logger.info(f"已下载PDF到临时文件: {input_file}, 大小: {os.path.getsize(input_file) if os.path.exists(input_file) else '不存在'} 字节")
            except Exception as e:
                logger.error(f"下载PDF失败: {str(e)}")
                return {"success": False, "error": f"Error downloading file from URL: {str(e)}"}
        if input_file is None and file_content_base64 is None:
            logger.error("No input provided: both input_file and file_content_base64 are None")
            return {"success": False, "error": "You must provide either input_file or file_content_base64"}
        # 检查 input_file、input_format、output_format 类型，避免 None 传递给 str
        if input_file is not None and not isinstance(input_file, str):
            logger.error(f"input_file 类型错误: {type(input_file)}")
            return {"success": False, "error": "input_file must be a string or None"}
        if file_content_base64 is not None and not isinstance(file_content_base64, str):
            logger.error(f"file_content_base64 类型错误: {type(file_content_base64)}")
            return {"success": False, "error": "file_content_base64 must be a string or None"}
        temp_dir = tempfile.mkdtemp()
        temp_input_file = os.path.join(temp_dir, f"input_{int(time.time())}.pdf")
        temp_output_file = os.path.join(temp_dir, f"output_{int(time.time())}.docx")
        is_temp_url = False
        # Handle direct content mode
        if file_content_base64:
            try:
                file_content = base64.b64decode(file_content_base64)
                with open(temp_input_file, "wb") as f:
                    f.write(file_content)
                actual_file_path = temp_input_file
                logger.info(f"已写入base64 PDF到临时文件: {temp_input_file}, 大小: {os.path.getsize(temp_input_file)} 字节")
            except Exception as e:
                import shutil
                shutil.rmtree(temp_dir)
                logger.error(f"写入base64 PDF失败: {str(e)}")
                return {"success": False, "error": f"Error processing input file content: {str(e)}"}
        else:
            try:
                actual_file_path = input_file
            except Exception as e:
                import shutil
                shutil.rmtree(temp_dir)
                for f in temp_files:
                    os.remove(f)
                logger.error(f"查找PDF文件失败: {str(e)}")
                return {"success": False, "error": f"Error finding PDF file: {str(e)}"}
        # 执行转换
        try:
            from pdf2docx import Converter
            logger.info(f"开始转换: {actual_file_path} -> {temp_output_file}")
            cv = Converter(actual_file_path)
            cv.convert(temp_output_file, start=0, end=-1)
            cv.close()
            logger.info(f"转换完成，检查临时输出文件是否存在: {temp_output_file}, 存在: {os.path.exists(temp_output_file)}")
            if not os.path.exists(temp_output_file):
                logger.error(f"转换失败，未生成临时输出文件: {temp_output_file}")
                import shutil
                shutil.rmtree(temp_dir)
                for f in temp_files:
                    os.remove(f)
                return {"success": False, "error": f"PDF转换未生成输出文件，可能源文件损坏或格式不支持。"}
        except Exception as e:
            import shutil
            shutil.rmtree(temp_dir)
            for f in temp_files:
                os.remove(f)
            logger.error(f"PDF转换异常: {str(e)}")
            return {"success": False, "error": f"Error converting PDF to DOCX: {str(e)}"}
        import shutil
        output_file = f"{OUTPUT_DIR}/output_{int(time.time())}.docx"
        logger.info(f"准备保存输出文件到: {output_file}")
        # 自动创建输出文件目录
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)
        # 判断临时输出文件是否存在
        if not os.path.exists(temp_output_file):
            logger.error(f"临时输出文件未生成: {temp_output_file}")
            import shutil
            shutil.rmtree(temp_dir)
            for f in temp_files:
                os.remove(f)
            return {"success": False, "error": f"临时输出文件未生成: {temp_output_file}"}
        try:
            shutil.move(temp_output_file, output_file)
            logger.info(f"已成功保存输出文件到: {output_file}")
            # === 集成自动上传到静态服务器 ===
            try:
                from upload_to_server import upload_to_static_server
                remote_file = f"/root/files/{os.path.basename(output_file)}"
                hostname = "8.156.74.79"
                username = "root"
                password = "zfsZBC123."
                upload_success = upload_to_static_server(output_file, remote_file, hostname, username, password)
                if not upload_success:
                    logger.error(f"自动上传到静态服务器失败: {remote_file}")
                    return {"success": False, "error": f"自动上传到静态服务器失败: {remote_file}"}
                logger.info(f"自动上传到静态服务器成功: {remote_file}")
            except Exception as e:
                logger.error(f"自动上传到静态服务器异常: {str(e)}")
                return {"success": False, "error": f"自动上传到静态服务器异常: {str(e)}"}
            # === END ===
        except Exception as e:
            logger.error(f"移动输出文件失败: {str(e)}")
            shutil.rmtree(temp_dir)
            for f in temp_files:
                os.remove(f)
            return {"success": False, "error": f"Error moving output file: {str(e)}"}
        shutil.rmtree(temp_dir)
        for f in temp_files:
            os.remove(f)
        return {"success": True, "output_file": output_file, "download_url": get_download_url(os.path.basename(output_file))}
    except Exception as e:
        logger.error(f"Unexpected error in convert_pdf_to_docx: {str(e)}")
        return debug_json_response(format_error_response(f"Error converting PDF to DOCX: {str(e)}"))

# Image format conversion tool
@mcp.tool("convert_image")
def convert_image(input_file: str = None, file_content_base64: str = None, output_format: str = None, input_format: str = None) -> dict:
    try:
        temp_files = []
        if input_file and (input_file.startswith("http://") or input_file.startswith("https://")):
            try:
                # 自动识别后缀
                suffix = f".{input_format.lower()}" if input_format else ".img"
                input_file = download_url_to_tempfile(input_file, suffix)
                temp_files.append(input_file)
                logger.info(f"已下载图片到临时文件: {input_file}, 大小: {os.path.getsize(input_file) if os.path.exists(input_file) else '不存在'} 字节")
            except Exception as e:
                logger.error(f"下载图片失败: {str(e)}")
                return {"success": False, "error": f"Error downloading image from URL: {str(e)}"}
        if input_file is None and file_content_base64 is None:
            return {"success": False, "error": "You must provide either input_file or file_content_base64"}
        valid_formats = ["jpg", "jpeg", "png", "webp", "gif", "bmp", "tiff"]
        if not output_format or output_format.lower() not in valid_formats:
            return {"success": False, "error": f"Unsupported output format: {output_format}. Supported formats: {', '.join(valid_formats)}"}
        temp_dir = tempfile.mkdtemp()
        if file_content_base64:
            if not input_format:
                import shutil
                shutil.rmtree(temp_dir)
                return {"success": False, "error": "input_format is required when using file_content_base64"}
            temp_input_file = os.path.join(temp_dir, f"input_{int(time.time())}.{input_format.lower()}")
            temp_output_file = os.path.join(temp_dir, f"output_{int(time.time())}.{output_format.lower()}")
            try:
                file_content = base64.b64decode(file_content_base64)
                with open(temp_input_file, "wb") as f:
                    f.write(file_content)
                actual_file_path = temp_input_file
                logger.info(f"已写入base64图片到临时文件: {temp_input_file}, 大小: {os.path.getsize(temp_input_file)} 字节")
            except Exception as e:
                import shutil
                shutil.rmtree(temp_dir)
                for f in temp_files:
                    os.remove(f)
                logger.error(f"写入base64图片失败: {str(e)}")
                return {"success": False, "error": f"Error processing input file content: {str(e)}"}
        else:
            try:
                actual_file_path = input_file
                input_format = os.path.splitext(actual_file_path)[1].lstrip('.') if not input_format else input_format
                temp_output_file = os.path.join(temp_dir, f"output_{int(time.time())}.{output_format.lower()}")
            except Exception as e:
                import shutil
                shutil.rmtree(temp_dir)
                for f in temp_files:
                    os.remove(f)
                logger.error(f"查找输入图片文件失败: {str(e)}")
                return {"success": False, "error": f"Error finding input image file: {str(e)}"}
        try:
            from PIL import Image
            img = Image.open(actual_file_path)
            if output_format.lower() in ['jpg', 'jpeg']:
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                    img = background
            img.save(temp_output_file)
        except Exception as e:
            import shutil
            shutil.rmtree(temp_dir)
            for f in temp_files:
                os.remove(f)
            logger.error(f"图片转换异常: {str(e)}")
            return {"success": False, "error": f"Error during image conversion: {str(e)}"}
        import shutil
        output_file = f"{OUTPUT_DIR}/output_{int(time.time())}.{output_format.lower()}"
        logger.info(f"准备保存输出文件到: {output_file}")
        try:
            shutil.move(temp_output_file, output_file)
            logger.info(f"已成功保存输出文件到: {output_file}")
        except Exception as e:
            logger.error(f"移动输出文件失败: {str(e)}")
            shutil.rmtree(temp_dir)
            for f in temp_files:
                os.remove(f)
            return {"success": False, "error": f"Error moving output file: {str(e)}"}
        shutil.rmtree(temp_dir)
        for f in temp_files:
            os.remove(f)
        return {"success": True, "output_file": output_file, "download_url": get_download_url(os.path.basename(output_file))}
    except Exception as e:
        logger.error(f"Unexpected error in convert_image: {str(e)}")
        return debug_json_response(format_error_response(f"Error converting image: {str(e)}"))

# Excel to CSV conversion tool
@mcp.tool("excel2csv")
def convert_excel_to_csv(input_file: str) -> dict:
    try:
        temp_files = []
        if input_file and (input_file.startswith("http://") or input_file.startswith("https://")):
            try:
                input_file = download_url_to_tempfile(input_file, ".xlsx")
                temp_files.append(input_file)
                logger.info(f"已下载Excel到临时文件: {input_file}, 大小: {os.path.getsize(input_file) if os.path.exists(input_file) else '不存在'} 字节")
            except Exception as e:
                logger.error(f"下载Excel失败: {str(e)}")
                return {"success": False, "error": f"Error downloading excel from URL: {str(e)}"}
        if not input_file.lower().endswith((".xls", ".xlsx")):
            return {"success": False, "error": f"File must be an Excel file (.xls or .xlsx), got: {input_file}"}
        actual_file_path = input_file
        output_file = f"{OUTPUT_DIR}/output_{int(time.time())}.csv"
        import pandas as pd
        df = pd.read_excel(actual_file_path)
        df.to_csv(output_file, index=False)
        for f in temp_files:
            os.remove(f)
        return {"success": True, "output_file": output_file, "download_url": get_download_url(os.path.basename(output_file))}
    except Exception as e:
        logger.error(f"下载Excel失败: {str(e)}")
        return {"success": False, "error": f"Error converting Excel to CSV: {str(e)}"}

# HTML to PDF conversion tool
@mcp.tool("html2pdf")
def convert_html_to_pdf(input_file: str) -> dict:
    try:
        temp_files = []
        if input_file and (input_file.startswith("http://") or input_file.startswith("https://")):
            try:
                # 默认按.html后缀下载
                input_file = download_url_to_tempfile(input_file, ".html")
                temp_files.append(input_file)
                logger.info(f"已下载HTML到临时文件: {input_file}, 大小: {os.path.getsize(input_file) if os.path.exists(input_file) else '不存在'} 字节")
            except Exception as e:
                logger.error(f"下载HTML失败: {str(e)}")
                return {"success": False, "error": f"Error downloading html from URL: {str(e)}"}
        actual_file_path = input_file
        output_file = f"{OUTPUT_DIR}/output_{int(time.time())}.pdf"
        if actual_file_path.lower().endswith((".md", ".markdown")):
            import markdown
            with open(actual_file_path, 'r', encoding='utf-8') as md_file:
                md_content = md_file.read()
            html_content = markdown.markdown(md_content)
            html_temp = os.path.splitext(actual_file_path)[0] + '.temp.html'
            with open(html_temp, 'w', encoding='utf-8') as f:
                f.write(f"""
                <html><head><meta charset='utf-8'></head><body>{html_content}</body></html>
                """)
            actual_file_path = html_temp
        import pdfkit
        pdfkit.from_file(actual_file_path, output_file)
        if actual_file_path.endswith('.temp.html'):
            try: os.remove(actual_file_path)
            except: pass
        for f in temp_files:
            os.remove(f)
        return {"success": True, "output_file": output_file, "download_url": get_download_url(os.path.basename(output_file))}
    except Exception as e:
        logger.error(f"下载HTML失败: {str(e)}")
        return {"success": False, "error": f"Error converting HTML/Markdown to PDF: {str(e)}"}

# HTML to DOCX conversion tool (基于 Pandoc)
@mcp.tool("html2docx")
def convert_html_to_docx(input_file: str = None, file_content_base64: str = None) -> dict:
    """
    Convert an HTML file to DOCX format using Pandoc. Supports file path, URL, and base64 content input.
    """
    import shutil
    import subprocess
    try:
        logger.info(f"Starting HTML to DOCX conversion")
        temp_files = []
        # 如果input_file是URL，自动下载到临时文件
        if input_file and (input_file.startswith("http://") or input_file.startswith("https://")):
            try:
                input_file = download_url_to_tempfile(input_file, ".html")
                temp_files.append(input_file)
                logger.info(f"已下载HTML到临时文件: {input_file}, 大小: {os.path.getsize(input_file) if os.path.exists(input_file) else '不存在'} 字节")
            except Exception as e:
                logger.error(f"下载HTML失败: {str(e)}")
                return {"success": False, "error": f"Error downloading HTML from URL: {str(e)}"}
        if input_file is None and file_content_base64 is None:
            logger.error("No input provided: both input_file and file_content_base64 are None")
            return {"success": False, "error": "You must provide either input_file or file_content_base64"}
        # 检查 input_file、file_content_base64 类型
        if input_file is not None and not isinstance(input_file, str):
            logger.error(f"input_file 类型错误: {type(input_file)}")
            return {"success": False, "error": "input_file must be a string or None"}
        if file_content_base64 is not None and not isinstance(file_content_base64, str):
            logger.error(f"file_content_base64 类型错误: {type(file_content_base64)}")
            return {"success": False, "error": "file_content_base64 must be a string or None"}
        temp_dir = tempfile.mkdtemp()
        temp_input_file = os.path.join(temp_dir, f"input_{int(time.time())}.html")
        temp_output_file = os.path.join(temp_dir, f"output_{int(time.time())}.docx")
        # Handle direct content mode
        if file_content_base64:
            try:
                file_content = base64.b64decode(file_content_base64)
                with open(temp_input_file, "wb") as f:
                    f.write(file_content)
                actual_file_path = temp_input_file
                logger.info(f"已写入base64 HTML到临时文件: {temp_input_file}, 大小: {os.path.getsize(temp_input_file)} 字节")
            except Exception as e:
                shutil.rmtree(temp_dir)
                logger.error(f"写入base64 HTML失败: {str(e)}")
                return {"success": False, "error": f"Error processing input file content: {str(e)}"}
        else:
            try:
                actual_file_path = input_file
            except Exception as e:
                shutil.rmtree(temp_dir)
                for f in temp_files:
                    os.remove(f)
                logger.error(f"查找HTML文件失败: {str(e)}")
                return {"success": False, "error": f"Error finding HTML file: {str(e)}"}
        # 执行 Pandoc 转换
        try:
            # 检查 pandoc 是否可用
            try:
                subprocess.run(["pandoc", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception as e:
                logger.error(f"Pandoc 未安装或不可用: {str(e)}")
                shutil.rmtree(temp_dir)
                for f in temp_files:
                    os.remove(f)
                return {"success": False, "error": "Pandoc 未安装或不可用，请先在服务器安装 pandoc。"}
            logger.info(f"开始转换: {actual_file_path} -> {temp_output_file}")
            result = subprocess.run([
                "pandoc", actual_file_path, "-o", temp_output_file
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                logger.error(f"Pandoc 转换失败: {result.stderr.decode('utf-8')}")
                shutil.rmtree(temp_dir)
                for f in temp_files:
                    os.remove(f)
                return {"success": False, "error": f"Pandoc 转换失败: {result.stderr.decode('utf-8')}"}
            logger.info(f"Pandoc 转换完成，检查临时输出文件是否存在: {temp_output_file}, 存在: {os.path.exists(temp_output_file)}")
            if not os.path.exists(temp_output_file):
                logger.error(f"转换失败，未生成临时输出文件: {temp_output_file}")
                shutil.rmtree(temp_dir)
                for f in temp_files:
                    os.remove(f)
                return {"success": False, "error": f"HTML转换未生成输出文件，可能源文件损坏或格式不支持。"}
        except Exception as e:
            shutil.rmtree(temp_dir)
            for f in temp_files:
                os.remove(f)
            logger.error(f"HTML转换异常: {str(e)}")
            return {"success": False, "error": f"Error converting HTML to DOCX: {str(e)}"}
        output_file = f"{OUTPUT_DIR}/output_{int(time.time())}.docx"
        logger.info(f"准备保存输出文件到: {output_file}")
        # 自动创建输出文件目录
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)
        # 判断临时输出文件是否存在
        if not os.path.exists(temp_output_file):
            logger.error(f"临时输出文件未生成: {temp_output_file}")
            shutil.rmtree(temp_dir)
            for f in temp_files:
                os.remove(f)
            return {"success": False, "error": f"临时输出文件未生成: {temp_output_file}"}
        try:
            shutil.move(temp_output_file, output_file)
            logger.info(f"已成功保存输出文件到: {output_file}")
            # === 集成自动上传到静态服务器 ===
            try:
                from upload_to_server import upload_to_static_server
                remote_file = f"/root/files/{os.path.basename(output_file)}"
                hostname = "8.156.74.79"
                username = "root"
                password = "zfsZBC123."
                upload_success = upload_to_static_server(output_file, remote_file, hostname, username, password)
                if not upload_success:
                    logger.error(f"自动上传到静态服务器失败: {remote_file}")
                    return {"success": False, "error": f"自动上传到静态服务器失败: {remote_file}"}
                logger.info(f"自动上传到静态服务器成功: {remote_file}")
            except Exception as e:
                logger.error(f"自动上传到静态服务器异常: {str(e)}")
                return {"success": False, "error": f"自动上传到静态服务器异常: {str(e)}"}
            # === END ===
        except Exception as e:
            logger.error(f"移动输出文件失败: {str(e)}")
            shutil.rmtree(temp_dir)
            for f in temp_files:
                os.remove(f)
            return {"success": False, "error": f"Error moving output file: {str(e)}"}
        shutil.rmtree(temp_dir)
        for f in temp_files:
            os.remove(f)
        return {"success": True, "output_file": output_file, "download_url": get_download_url(os.path.basename(output_file))}
    except Exception as e:
        logger.error(f"Unexpected error in convert_html_to_docx: {str(e)}")
        return {"success": False, "error": f"Error converting HTML to DOCX: {str(e)}"}

# Generic file conversion tool using file paths
@mcp.tool("convert_file")
def convert_file(input_file: str = None, file_content_base64: str = None, input_format: str = None, output_format: str = None, ctx: Context = None) -> dict:
    try:
        if ctx:
            ctx.info(f"Converting from {input_format} to {output_format}")
        if input_file is None and file_content_base64 is None:
            return {"success": False, "error": "You must provide either input_file or file_content_base64"}
        if not input_format or not output_format:
            return {"success": False, "error": "You must specify both input_format and output_format"}
        conversion_map = {
            ("docx", "pdf"): convert_docx_to_pdf,
            ("pdf", "docx"): convert_pdf_to_docx,
            ("markdown", "pdf"): convert_html_to_pdf,
            ("md", "pdf"): convert_html_to_pdf,
        }
        conversion_key = (input_format.lower(), output_format.lower())
        if conversion_key in conversion_map:
            conversion_func = conversion_map[conversion_key]
            if file_content_base64:
                return conversion_func(file_content_base64=file_content_base64)
            else:
                return conversion_func(input_file=input_file)
        else:
            if input_format.lower() in ["jpg", "jpeg", "png", "webp", "gif", "bmp", "tiff"]:
                if file_content_base64:
                    return convert_image(
                        file_content_base64=file_content_base64,
                        input_format=input_format,
                        output_format=output_format
                    )
                else:
                    return convert_image(
                        input_file=input_file,
                        output_format=output_format
                    )
            return {"success": False, "error": f"Unsupported conversion: {input_format} to {output_format}"}
    except Exception as e:
        logger.error(f"下载文件失败: {str(e)}")
        return {"success": False, "error": f"Error converting file: {str(e)}"}

# Function to handle direct file content input
@mcp.tool("convert_content")
def convert_content(file_content_base64: str, input_format: str, output_format: str) -> dict:
    """
    Convert a file directly from its base64 content, without needing a file path.
    This is useful when the file path approach fails or when working with content
    directly from the chat.
    
    Args:
        file_content_base64: Base64 encoded content of the input file
        input_format: Source format (e.g., "docx", "pdf", "md")
        output_format: Target format (e.g., "pdf", "docx")
        
    Returns:
        Dictionary containing success status and either base64 encoded file or error message.
    """
    try:
        logger.info(f"Starting direct content conversion from {input_format} to {output_format}")
        
        # We can now directly use convert_file with file_content_base64
        return convert_file(
            file_content_base64=file_content_base64,
            input_format=input_format,
            output_format=output_format
        )
    
    except Exception as e:
        logger.error(f"下载内容失败: {str(e)}")
        return debug_json_response(format_error_response(f"Error converting content: {str(e)}"))

# Direct DOCX to PDF conversion with content
@mcp.tool("docx2pdf_content")
def convert_docx_to_pdf_content(file_content_base64: str) -> dict:
    """
    Convert a DOCX file directly from its base64 content to PDF format.
    
    Args:
        file_content_base64: Base64 encoded content of the DOCX file
        
    Returns:
        Dictionary containing success status and either base64 encoded PDF or error message.
    """
    result = convert_docx_to_pdf(file_content_base64=file_content_base64)
    return debug_json_response(result)

# Direct PDF to DOCX conversion with content
@mcp.tool("pdf2docx_content")
def convert_pdf_to_docx_content(file_content_base64: str = None, input_file: str = None) -> dict:
    """
    Convert a PDF file directly from its base64 content or URL to DOCX format.
    """
    # 新增：如果input_file是URL，自动下载并转base64
    if input_file and (input_file.startswith("http://") or input_file.startswith("https://")):
        try:
            response = requests.get(input_file)
            response.raise_for_status()
            file_content_base64 = base64.b64encode(response.content).decode('utf-8')
        except Exception as e:
            logger.error(f"下载PDF内容失败: {str(e)}")
            return debug_json_response({"success": False, "error": f"Error downloading file from URL: {str(e)}"})
    if not file_content_base64:
        return debug_json_response({"success": False, "error": "No base64 content provided."})
    result = convert_pdf_to_docx(file_content_base64=file_content_base64)
    return debug_json_response(result)

# Direct Markdown to PDF conversion with content
@mcp.tool("markdown2pdf_content")
def convert_markdown_to_pdf_content(file_content_base64: str) -> dict:
    """
    Convert a Markdown file directly from its base64 content to PDF format.
    
    Args:
        file_content_base64: Base64 encoded content of the Markdown file
        
    Returns:
        Dictionary containing success status and either base64 encoded PDF or error message.
    """
    result = convert_file(file_content_base64=file_content_base64, input_format="md", output_format="pdf")
    return debug_json_response(result)

if __name__ == "__main__":
    mcp.run() 
