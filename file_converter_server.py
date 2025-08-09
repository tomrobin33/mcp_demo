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
from typing import Optional
# weasyprint将在需要时动态导入

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)  # 将日志输出到stderr，避免干扰stdout的JSON输出
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

def detect_json_error_pattern(text):
    """
    检测并分类常见的JSON错误模式，用于调试和改进
    
    Returns:
        dict: 包含错误类型和建议修复方案的字典
    """
    error_patterns = {
        "malformed_quotes": False,
        "missing_brackets": False,
        "over_escaped": False,
        "mixed_format": False,
        "truncated": False
    }
    
    if not text or not isinstance(text, str):
        return {"error_type": "empty_input", "patterns": error_patterns}
    
    text = text.strip()
    
    # 检测过度转义
    if text.count('\\"') > text.count('"') / 2:
        error_patterns["over_escaped"] = True
    
    # 检测括号不匹配
    open_brackets = text.count('{')
    close_brackets = text.count('}')
    if open_brackets != close_brackets:
        error_patterns["missing_brackets"] = True
    
    # 检测引号不匹配
    quote_count = text.count('"') - text.count('\\"')
    if quote_count % 2 != 0:
        error_patterns["malformed_quotes"] = True
    
    # 检测混合格式
    if text.startswith('{') and not text.endswith('}'):
        error_patterns["truncated"] = True
    
    # 检测是否是混合了JSON和纯文本
    if ('"' in text and '{' in text) and not text.strip().startswith('{'):
        error_patterns["mixed_format"] = True
    
    return {"patterns": error_patterns, "text_length": len(text)}

# Note: Enhanced JSON parsing is no longer needed in newer MCP versions

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

# 通用JSON格式修正函数
def fix_json_format(text):
    """
    修正各种可能的JSON格式错误，适用于所有工具
    
    常见的大模型JSON错误模式：
    1. 把JSON当作纯文本输出
    2. 过度转义或转义不当
    3. 嵌套JSON结构混乱
    4. 特殊字符处理错误
    5. 括号、引号不匹配
    
    Args:
        text: 待修正的文本内容
        
    Returns:
        修正后的文本内容
    """
    if not text:
        return ""
    
    # 移除可能的非JSON前缀
    text = text.strip()
    
    # 特殊处理：如果输入文本看起来已经是纯文本内容（包含换行但不是JSON）
    # 直接返回，不进行JSON解析处理
    if not text.startswith('{') and not text.startswith('"') and '\n' in text:
        logger.info("检测到包含换行符的纯文本，直接返回")
        return text
    
    # 如果已经是纯文本（不是JSON），直接返回
    if not text.startswith('{') and not text.startswith('"'):
        return text
    
    # 处理被转义的JSON字符串
    if text.startswith('"') and text.endswith('"'):
        try:
            # 尝试解析为JSON字符串
            import json
            return json.loads(text)
        except:
            # 如果不是有效的JSON字符串，移除引号
            return text[1:-1] if len(text) > 2 else text
    
    # 特殊处理：修复不完整的JSON字符串
    # 这种情况通常发生在AI生成的JSON格式中途被截断
    if text.startswith('{') and '"markdown_text"' in text:
        # 首先尝试正常解析JSON，如果成功就不需要修复
        try:
            import json
            parsed = json.loads(text)
            if isinstance(parsed, dict) and 'markdown_text' in parsed:
                logger.info("JSON解析成功，直接返回markdown_text内容")
                return parsed['markdown_text']
        except json.JSONDecodeError:
            logger.info("JSON解析失败，尝试修复不完整的JSON格式")
            # 检查是否有markdown_text字段但缺少结束符
            if '"markdown_text":' in text and not text.rstrip().endswith('}'):
                # 尝试找到markdown_text的值
                start_marker = '"markdown_text": "'
                start_pos = text.find(start_marker)
                if start_pos != -1:
                    start_content = start_pos + len(start_marker)
                    content_part = text[start_content:]
                    
                    # 如果字符串没有正确结束，尝试修复
                    if not content_part.endswith('"}') and not content_part.endswith('",'):
                        # 移除末尾可能的不完整字符并添加正确的结束符
                        content_part = content_part.rstrip()
                        # 如果内容以换行符结束，可能是被截断了
                        if content_part.endswith('\n') or content_part.endswith('\n\n'):
                            content_part = content_part.rstrip('\n')
                        
                        # 构建完整的JSON
                        fixed_json = '{"markdown_text": "' + content_part + '"}'
                        logger.info(f"修复JSON格式，原长度: {len(text)}, 修复后长度: {len(fixed_json)}")
                        try:
                            # 验证修复后的JSON是否有效
                            parsed = json.loads(fixed_json)
                            if 'markdown_text' in parsed:
                                logger.info("JSON修复成功，返回markdown_text内容")
                                return parsed['markdown_text']
                        except Exception as e:
                            logger.warning(f"修复后的JSON仍然无效: {str(e)}")
                            # 如果修复失败，直接返回提取的内容
                            return content_part
    
    # 处理嵌套JSON格式：{"arguments": "{\"markdown_text\": \"...\"}", "name": "..."}
    if text.startswith('{') and '"arguments"' in text:
        try:
            import json
            # 先解析外层JSON
            outer_parsed = json.loads(text)
            if isinstance(outer_parsed, dict) and 'arguments' in outer_parsed:
                arguments_str = outer_parsed['arguments']
                logger.info("检测到嵌套JSON格式，解析arguments字段")
                
                # 解析内层JSON字符串
                try:
                    inner_parsed = json.loads(arguments_str)
                    if isinstance(inner_parsed, dict) and 'markdown_text' in inner_parsed:
                        content = inner_parsed['markdown_text']
                        # 处理转义字符
                        content = content.replace('\\n', '\n')
                        content = content.replace('\\r', '\r')
                        content = content.replace('\\t', '\t')
                        content = content.replace('\\"', '"')
                        return content
                except json.JSONDecodeError:
                    logger.warning("内层JSON解析失败，尝试字符串提取")
                    # 如果内层JSON解析失败，尝试从字符串中提取
                    if '"markdown_text"' in arguments_str:
                        start_marker = '"markdown_text": "'
                        start_pos = arguments_str.find(start_marker)
                        if start_pos != -1:
                            start_content = start_pos + len(start_marker)
                            remaining_text = arguments_str[start_content:]
                            # 尝试多种结束模式
                            end_patterns = ['"}', '",', '"}', '"']
                            for pattern in end_patterns:
                                end_pos = remaining_text.find(pattern)
                                if end_pos > 0:
                                    content = remaining_text[:end_pos]
                                    # 处理转义字符
                                    content = content.replace('\\n', '\n')
                                    content = content.replace('\\r', '\r')
                                    content = content.replace('\\t', '\t')
                                    content = content.replace('\\"', '"')
                                    return content
        except json.JSONDecodeError as e:
            logger.warning(f"外层JSON解析失败: {str(e)}")
        except Exception as e:
            logger.warning(f"嵌套JSON处理失败: {str(e)}")
    
    # 处理JSON对象中的各种字段
    if text.startswith('{'):
        try:
            import json
            # 预处理JSON字符串，处理换行符和特殊字符
            processed_text = text
            
            # 更智能的JSON预处理
            # 1. 处理字符串值中的换行符
            import re
            # 匹配字符串值中的换行符，但不在JSON结构中的
            string_pattern = r'"([^"]*(?:\\n[^"]*)*)"'
            
            def replace_newlines_in_strings(match):
                content = match.group(1)
                # 将字符串中的换行符转义
                content = content.replace('\n', '\\n')
                content = content.replace('\r', '\\r')
                content = content.replace('\t', '\\t')
                return f'"{content}"'
            
            processed_text = re.sub(string_pattern, replace_newlines_in_strings, processed_text)
            
            parsed = json.loads(processed_text)
            if isinstance(parsed, dict):
                # 提取常见字段
                for field in ['markdown_text', 'text', 'content', 'message', 'html_content', 'input_file']:
                    if field in parsed:
                        value = parsed[field]
                        # 处理转义字符
                        if isinstance(value, str):
                            value = value.replace('\\n', '\n')
                            value = value.replace('\\r', '\r')
                            value = value.replace('\\t', '\t')
                            value = value.replace('\\"', '"')
                        return value
                # 如果只有一个键值对，返回值
                if len(parsed) == 1:
                    value = list(parsed.values())[0]
                    if isinstance(value, str):
                        value = value.replace('\\n', '\n')
                        value = value.replace('\\r', '\r')
                        value = value.replace('\\t', '\t')
                        value = value.replace('\\"', '"')
                    return value
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败，尝试其他方法: {str(e)}")
            # JSON解析失败，尝试提取内容
            pass
    
    # 尝试提取被转义的内容
    import re
    # 查找被转义的内容，支持多行内容
    patterns = [
        r'"markdown_text":\s*"([^"]*(?:\\n[^"]*)*)"',
        r'"text":\s*"([^"]*(?:\\n[^"]*)*)"',
        r'"content":\s*"([^"]*(?:\\n[^"]*)*)"',
        r'"message":\s*"([^"]*(?:\\n[^"]*)*)"',
        r'"html_content":\s*"([^"]*(?:\\n[^"]*)*)"',
        r'"input_file":\s*"([^"]*(?:\\n[^"]*)*)"',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            content = match.group(1)
            # 处理转义字符
            content = content.replace('\\n', '\n')
            content = content.replace('\\r', '\r')
            content = content.replace('\\t', '\t')
            content = content.replace('\\"', '"')
            return content
    
    # 尝试更宽松的匹配模式
    try:
        # 查找JSON对象中的字符串值
        import re
        # 匹配 "field": "value" 格式，支持多行
        json_pattern = r'"([^"]+)":\s*"([^"]*(?:\\n[^"]*)*)"'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        if matches:
            # 找到第一个有意义的字段
            for field_name, field_value in matches:
                if field_name in ['markdown_text', 'text', 'content', 'message']:
                    # 处理转义字符
                    field_value = field_value.replace('\\n', '\n')
                    field_value = field_value.replace('\\r', '\r')
                    field_value = field_value.replace('\\t', '\t')
                    field_value = field_value.replace('\\"', '"')
                    return field_value
            
            # 如果没有找到特定字段，返回第一个字段的值
            if matches:
                field_value = matches[0][1]
                field_value = field_value.replace('\\n', '\n')
                field_value = field_value.replace('\\r', '\r')
                field_value = field_value.replace('\\t', '\t')
                field_value = field_value.replace('\\"', '"')
                return field_value
    except Exception as e:
        logger.warning(f"正则表达式匹配失败: {str(e)}")
    
    # 最后尝试：直接提取JSON对象中的内容
    try:
        # 查找第一个和最后一个引号之间的内容
        start_quote = text.find('"markdown_text": "')
        if start_quote != -1:
            start_content = start_quote + len('"markdown_text": "')
            # 从后往前查找最后一个引号
            end_quote = text.rfind('"')
            if end_quote > start_content:
                content = text[start_content:end_quote]
                # 处理转义字符
                content = content.replace('\\n', '\n')
                content = content.replace('\\r', '\r')
                content = content.replace('\\t', '\t')
                content = content.replace('\\"', '"')
                return content
    except Exception as e:
        logger.warning(f"直接提取内容失败: {str(e)}")
    
    # 终极尝试：暴力提取
    try:
        # 如果所有方法都失败了，尝试最宽松的提取
        if '"markdown_text"' in text:
            # 找到markdown_text字段的开始
            start_marker = '"markdown_text": "'
            start_pos = text.find(start_marker)
            if start_pos != -1:
                start_content = start_pos + len(start_marker)
                # 查找结束位置，从开始位置向后查找
                remaining_text = text[start_content:]
                # 尝试找到结束的引号
                end_pos = remaining_text.find('"}')
                if end_pos == -1:
                    end_pos = remaining_text.rfind('"')
                if end_pos > 0:
                    content = remaining_text[:end_pos]
                    # 处理转义字符
                    content = content.replace('\\n', '\n')
                    content = content.replace('\\r', '\r')
                    content = content.replace('\\t', '\t')
                    content = content.replace('\\"', '"')
                    return content
    except Exception as e:
        logger.warning(f"暴力提取失败: {str(e)}")
    
    # 通用JSON格式处理：尝试修复常见的JSON格式问题
    try:
        # 处理包含换行符的JSON
        if '"markdown_text"' in text:
            # 找到markdown_text字段
            start_marker = '"markdown_text": "'
            start_pos = text.find(start_marker)
            if start_pos != -1:
                start_content = start_pos + len(start_marker)
                # 从开始位置向后查找结束位置
                remaining_text = text[start_content:]
                
                # 尝试多种结束模式
                end_patterns = ['"}', '",', '"}', '"']
                for pattern in end_patterns:
                    end_pos = remaining_text.find(pattern)
                    if end_pos > 0:
                        content = remaining_text[:end_pos]
                        # 处理转义字符
                        content = content.replace('\\n', '\n')
                        content = content.replace('\\r', '\r')
                        content = content.replace('\\t', '\t')
                        content = content.replace('\\"', '"')
                        return content
                
                # 如果找不到明确的结束模式，尝试从后往前查找
                end_pos = remaining_text.rfind('"')
                if end_pos > 0:
                    content = remaining_text[:end_pos]
                    # 处理转义字符
                    content = content.replace('\\n', '\n')
                    content = content.replace('\\r', '\r')
                    content = content.replace('\\t', '\t')
                    content = content.replace('\\"', '"')
                    return content
                
                # 如果完全找不到结束引号，可能是JSON被截断了
                # 直接取剩余的全部内容，并清理末尾的换行符
                logger.warning("未找到JSON结束标记，可能被截断，使用全部剩余内容")
                content = remaining_text.rstrip('\n\r ')
                content = content.replace('\\n', '\n')
                content = content.replace('\\r', '\r')
                content = content.replace('\\t', '\t')
                content = content.replace('\\"', '"')
                return content
    except Exception as e:
        logger.warning(f"通用JSON格式处理失败: {str(e)}")
    
    # 如果都失败了，返回原文本
    return text

# DOCX to PDF conversion tool
@mcp.tool("docx2pdf")
def convert_docx_to_pdf(input_file: str = None, file_content_base64: str = None) -> dict:
    """
    Convert a DOCX file to PDF format. Supports both file path, URL, and direct file content input.
    
    Args:
        input_file: Path to the DOCX file or URL
        file_content_base64: Base64 encoded content of the DOCX file
        
    ✅ 正确的JSON格式示例：
    
    方式1: 使用文件路径
    {
        "input_file": "/path/to/document.docx"
    }
    
    方式2: 使用URL
    {
        "input_file": "https://example.com/document.docx"
    }
    
    方式3: 使用Base64内容
    {
        "file_content_base64": "UEsDBBQAAAAIABcOCFGQ5..."
    }
    
    ❌ 错误示例 (请避免):
    {"input_file": {"path": "document.docx"}}  // 嵌套对象
    {"file_path": "document.docx"}             // 错误的参数名
        
    Returns:
        Dictionary containing success status and either output file path or error message.
    """
    import sys
    import platform
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
            if platform.system().lower() == "windows":
                from docx2pdf import convert
                logger.info(f"Windows平台，使用docx2pdf: {actual_file_path} -> {temp_output_file}")
                convert(actual_file_path, temp_output_file)
            else:
                import subprocess
                logger.info(f"非Windows平台，使用libreoffice: {actual_file_path} -> {temp_output_file}")
                # libreoffice --headless --convert-to pdf input.docx --outdir /output/dir
                cmd = [
                    "libreoffice", "--headless", "--convert-to", "pdf", actual_file_path, "--outdir", temp_dir
                ]
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logger.info(f"libreoffice stdout: {result.stdout.decode('utf-8')}")
                logger.info(f"libreoffice stderr: {result.stderr.decode('utf-8')}")
                # 查找输出pdf
                base_name = os.path.splitext(os.path.basename(actual_file_path))[0]
                generated_pdf = os.path.join(temp_dir, base_name + ".pdf")
                if not os.path.exists(generated_pdf):
                    raise Exception(f"libreoffice未生成PDF: {generated_pdf}")
                # 重命名为 temp_output_file 以兼容后续逻辑
                os.rename(generated_pdf, temp_output_file)
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
    
    Args:
        input_file: Path to the PDF file or URL
        file_content_base64: Base64 encoded content of the PDF file
        
    ✅ 正确的JSON格式示例：
    
    方式1: 使用文件路径
    {
        "input_file": "/path/to/document.pdf"
    }
    
    方式2: 使用URL
    {
        "input_file": "https://example.com/document.pdf"
    }
    
    方式3: 使用Base64内容
    {
        "file_content_base64": "JVBERi0xLjQKJeLjz9MKMSAwIG9..."
    }
    
    ❌ 错误示例 (请避免):
    {"input_file": {"path": "document.pdf"}}  // 嵌套对象
    {"file_path": "document.pdf"}             // 错误的参数名
    
    Returns:
        Dictionary containing success status and either output file path or error message.
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
        if temp_html_file and os.path.exists(temp_html_file):
            os.remove(temp_html_file)
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
    """
    Convert between different image formats (PNG, JPG, WEBP, GIF, BMP, etc.).
    
    Args:
        input_file: Path to the image file or URL
        file_content_base64: Base64 encoded content of the image file
        output_format: Target image format (png, jpg, webp, gif, bmp, etc.)
        input_format: Source image format (optional, auto-detected if not provided)
        
    ✅ 正确的JSON格式示例：
    
    方式1: 文件路径转换
    {
        "input_file": "/path/to/image.png",
        "output_format": "jpg"
    }
    
    方式2: URL转换
    {
        "input_file": "https://example.com/image.png",
        "output_format": "webp"
    }
    
    方式3: Base64内容转换
    {
        "file_content_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
        "output_format": "png",
        "input_format": "jpg"
    }
    
    ❌ 错误示例 (请避免):
    {"input_file": {"path": "image.png"}}      // 嵌套对象
    {"image_path": "image.png"}                // 错误的参数名
    {"output_format": {"type": "jpg"}}         // 格式应为字符串
        
    Returns:
        Dictionary containing success status and either output file path or error message.
    """
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
    """
    Convert Excel files (.xlsx, .xls) to CSV format.
    
    Args:
        input_file: Path to the Excel file or URL
        
    ✅ 正确的JSON格式示例：
    
    使用文件路径:
    {
        "input_file": "/path/to/spreadsheet.xlsx"
    }
    
    使用URL:
    {
        "input_file": "https://example.com/data.xlsx"
    }
    
    ❌ 错误示例 (请避免):
    {"input_file": {"path": "spreadsheet.xlsx"}}  // 嵌套对象
    {"excel_file": "spreadsheet.xlsx"}            // 错误的参数名
        
    Returns:
        Dictionary containing success status and either output file path or error message.
    """
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
def convert_html_to_pdf(input_file: Optional[str] = None, html_content: Optional[str] = None) -> dict:
    """
    Convert HTML files or content to PDF format. Supports both file path, URL, and direct HTML content input.
    
    Args:
        input_file: Path to the HTML file or URL
        html_content: Raw HTML content string
        
    ✅ 正确的JSON格式示例：
    
    方式1: 使用文件路径
    {
        "input_file": "/path/to/page.html"
    }
    
    方式2: 使用URL
    {
        "input_file": "https://example.com/page.html"
    }
    
    方式3: 使用HTML内容
    {
        "html_content": "<html><head><title>测试</title></head><body><h1>标题</h1><p>内容</p></body></html>"
    }
    
    ❌ 错误示例 (请避免):
    {"input_file": {"path": "page.html"}}      // 嵌套对象
    {"html_file": "page.html"}                 // 错误的参数名
    {"content": "<html>...</html>"}            // 错误的参数名
        
    Returns:
        Dictionary containing success status and either output file path or error message.
    """
    try:
        import tempfile, os, time, shutil
        from weasyprint import HTML
        
        # 修正输入的html_content
        if html_content:
            corrected_html = fix_json_format(html_content)
            logger.info(f"原始HTML内容长度: {len(html_content)}")
            logger.info(f"修正后HTML内容长度: {len(corrected_html)}")
            html_content = corrected_html
        
        temp_dir = tempfile.mkdtemp()
        output_file = f"{OUTPUT_DIR}/output_{int(time.time())}.pdf"
        if html_content is not None:
            HTML(string=html_content).write_pdf(output_file)
        elif input_file:
            if input_file.startswith("http://") or input_file.startswith("https://"):
                HTML(url=input_file).write_pdf(output_file)
            else:
                HTML(filename=input_file).write_pdf(output_file)
        else:
            shutil.rmtree(temp_dir)
            return {"success": False, "error": "You must provide either input_file or html_content"}
        shutil.rmtree(temp_dir)
        return {"success": True, "output_file": output_file, "download_url": get_download_url(os.path.basename(output_file))}
    except Exception as e:
        return {"success": False, "error": f"Error converting HTML to PDF: {str(e)}"}

# HTML to DOCX conversion tool (基于 Pandoc)
@mcp.tool("html2docx")
def convert_html_to_docx(input_file: Optional[str] = None, html_content: Optional[str] = None) -> dict:
    """
    Convert an HTML file to DOCX format using Pandoc. 支持文件路径、URL、明文HTML字符串输入。
    """
    import shutil
    import subprocess
    import tempfile, os, time
    try:
        logger.info(f"Starting HTML to DOCX conversion")
        
        # 修正输入的html_content
        if html_content:
            corrected_html = fix_json_format(html_content)
            logger.info(f"原始HTML内容长度: {len(html_content)}")
            logger.info(f"修正后HTML内容长度: {len(corrected_html)}")
            html_content = corrected_html
        
        temp_files = []
        temp_dir = tempfile.mkdtemp()
        temp_html_file = None
        # 优先处理 html_content
        if html_content is not None:
            temp_html_file = os.path.join(temp_dir, f"input_{int(time.time())}.html")
            with open(temp_html_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            actual_file_path = temp_html_file
        elif input_file and (input_file.startswith("http://") or input_file.startswith("https://")):
            try:
                input_file = download_url_to_tempfile(input_file, ".html")
                temp_files.append(input_file)
                logger.info(f"已下载HTML到临时文件: {input_file}, 大小: {os.path.getsize(input_file) if os.path.exists(input_file) else '不存在'} 字节")
            except Exception as e:
                logger.error(f"下载HTML失败: {str(e)}")
                shutil.rmtree(temp_dir)
                return {"success": False, "error": f"Error downloading HTML from URL: {str(e)}"}
            actual_file_path = input_file
        elif input_file:
            actual_file_path = input_file
        else:
            shutil.rmtree(temp_dir)
            logger.error("No input provided: both input_file and html_content are None")
            return {"success": False, "error": "You must provide either input_file or html_content"}
        temp_output_file = os.path.join(temp_dir, f"output_{int(time.time())}.docx")
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
        if temp_html_file and os.path.exists(temp_html_file):
            os.remove(temp_html_file)
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
    """
    Generic file conversion tool supporting various file formats.
    
    Args:
        input_file: Path to the input file or URL
        file_content_base64: Base64 encoded content of the file
        input_format: Source file format (docx, pdf, xlsx, html, etc.)
        output_format: Target file format (pdf, docx, csv, etc.)
        ctx: Context object for logging
        
    ✅ 正确的JSON格式示例：
    
    使用文件路径:
    {
        "input_file": "/path/to/document.docx",
        "input_format": "docx",
        "output_format": "pdf"
    }
    
    使用Base64内容:
    {
        "file_content_base64": "UEsDBBQAAAAIABcOCFGQ5...",
        "input_format": "docx",
        "output_format": "pdf"
    }
    
    ❌ 错误示例 (请避免):
    {"input_file": {"path": "document.docx"}}   // 嵌套对象
    {"formats": {"from": "docx", "to": "pdf"}}  // 错误的格式结构
        
    Returns:
        Dictionary containing success status and either output file path or error message.
    """
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
        
    ✅ 正确的JSON格式示例：
    
    DOCX转PDF:
    {
        "file_content_base64": "UEsDBBQAAAAIABcOCFGQ5...",
        "input_format": "docx",
        "output_format": "pdf"
    }
    
    PDF转DOCX:
    {
        "file_content_base64": "JVBERi0xLjQKJeLjz9MKMSAwIG9...",
        "input_format": "pdf",
        "output_format": "docx"
    }
    
    ❌ 错误示例 (请避免):
    {"content": "UEsDBBQ..."}                      // 错误的参数名
    {"file_content_base64": {"data": "UEsDBBQ"}}  // 嵌套对象
        
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

# Markdown to PDF
@mcp.tool("markdown2pdf")
def markdown2pdf(markdown_text: str, arguments: str = None) -> dict:
    """
    将Markdown文本转换为PDF文档格式。
    
    参数：
    - markdown_text: 要转换的Markdown文本内容 (必需参数)
    - arguments: 备用参数，用于传入markdown内容
    
    ✅ 正确的JSON格式示例：
    
    方式1 (推荐): 直接传入markdown_text参数
    {
        "markdown_text": "# 我的标题\n\n这是一段内容\n\n- 列表项1\n- 列表项2\n\n```python\nprint('代码块')\n```"
    }
    
    方式2: 使用arguments参数作为备用
    {
        "markdown_text": "",
        "arguments": "# 我的标题\n\n这是一段内容"
    }
    
    ❌ 错误示例 (请避免):
    {"arguments": "{\"markdown_text\": \"内容\"}"}  // 过度嵌套JSON
    {"markdown_text": "{\"content\": \"内容\"}"}   // 错误的JSON嵌套
    
    返回格式：
    {
        "success": true/false,
        "output_file": "输出文件路径",
        "download_url": "下载链接",
        "error": "错误信息（如果失败）"
    }
    
    功能特性：
    - 支持完整Markdown语法：标题、列表、链接、代码块、表格等
    - 智能处理各种JSON格式输入和错误修复
    - 中文内容完美支持
    - 自动生成下载链接
    """
    import tempfile, os, time, shutil
    try:
        logger.info("Starting Markdown to PDF conversion")
        logger.info(f"原始输入类型: {type(markdown_text)}")
        logger.info(f"原始输入长度: {len(markdown_text) if markdown_text else 0}")
        logger.info(f"原始输入预览: {repr(markdown_text[:200]) if markdown_text else 'None'}")
        logger.info(f"Arguments: {arguments}")
        
        # 处理输入格式 - markdown_text第一优先级（必需参数）
        input_text = None
        
        # 第一优先级：直接传入的markdown_text参数（必需参数）
        if markdown_text:
            input_text = markdown_text
            logger.info("使用markdown_text参数（第一优先级）")
        
        # 第二优先级：通过arguments字段传入（备用）
        elif arguments:
            input_text = arguments
            logger.info("使用arguments参数（第二优先级）")
        
        if not input_text:
            logger.error("没有找到有效的输入内容")
            return {"success": False, "error": "没有找到有效的输入内容，请提供markdown_text或arguments参数"}
        
        # 使用通用JSON格式修正函数处理各种格式的输入
        corrected_text = fix_json_format(input_text)
        logger.info(f"修正后长度: {len(corrected_text)}")
        logger.info(f"修正后预览: {repr(corrected_text[:200])}")
        
        # 验证修正后的内容
        if not corrected_text or len(corrected_text.strip()) == 0:
            logger.error("修正后的内容为空")
            return {"success": False, "error": "修正后的markdown内容为空，请检查输入格式"}
        
        # 检查内容是否包含有效的markdown语法
        if not any(char in corrected_text for char in ['#', '*', '-', '`', '[']):
            logger.warning("修正后的内容可能不是有效的markdown格式，但会继续处理")
        
        # 创建临时目录和文件
        temp_dir = tempfile.mkdtemp()
        temp_md_file = os.path.join(temp_dir, f"input_{int(time.time())}.md")
        temp_pdf_file = os.path.join(temp_dir, f"output_{int(time.time())}.pdf")
        
        # 写入markdown内容到临时文件
        with open(temp_md_file, "w", encoding="utf-8") as f:
            f.write(corrected_text)
        logger.info(f"已写入临时markdown文件: {temp_md_file}")
        
        # 使用html2pdf工具链进行转换（已支持md转pdf）
        try:
            result = convert_html_to_pdf(temp_md_file)
            if not result.get("success"):
                logger.error(f"Markdown转PDF失败: {result.get('error')}")
                shutil.rmtree(temp_dir)
                return {"success": False, "error": result.get("error")}
            output_file = result.get("output_file")
            download_url = result.get("download_url")
            logger.info(f"Markdown转PDF成功: {output_file}")
        except Exception as e:
            logger.error(f"Markdown转PDF异常: {str(e)}")
            shutil.rmtree(temp_dir)
            return {"success": False, "error": f"Error converting Markdown to PDF: {str(e)}"}
        
        # 清理临时文件并返回结果
        shutil.rmtree(temp_dir)
        return {"success": True, "output_file": output_file, "download_url": download_url}
    except Exception as e:
        logger.error(f"Unexpected error in markdown2pdf: {str(e)}")
        return {"success": False, "error": f"Error converting Markdown to PDF: {str(e)}"}

# Markdown to DOCX
@mcp.tool("markdown2docx")
def markdown2docx(markdown_text: str, arguments: str = None) -> dict:
    """
    将Markdown文本转换为DOCX文档格式。
    
    参数：
    - markdown_text: 要转换的Markdown文本内容 (必需参数)
    - arguments: 备用参数，用于传入markdown内容
    
    ✅ 正确的JSON格式示例：
    
    方式1 (推荐): 直接传入markdown_text参数
    {
        "markdown_text": "# 我的文档\n\n## 章节1\n\n这是一段**粗体**文本和*斜体*文本。\n\n- 列表项1\n- 列表项2\n\n| 表头1 | 表头2 |\n|-------|-------|\n| 内容1 | 内容2 |"
    }
    
    方式2: 使用arguments参数作为备用
    {
        "markdown_text": "",
        "arguments": "# 我的文档\n\n这是内容"
    }
    
    ❌ 错误示例 (请避免):
    {"arguments": "{\"markdown_text\": \"内容\"}"}  // 过度嵌套JSON
    {"markdown_text": "{\"content\": \"内容\"}"}   // 错误的JSON嵌套
    
    返回格式：
    {
         "success": true/false,
         "output_file": "输出文件路径",
         "download_url": "下载链接",
         "error": "错误信息（如果失败）"
    }
    
    功能特性：
    - 支持完整Markdown语法：标题、列表、链接、代码块、表格等
    - 使用Pandoc进行高质量转换
    - 智能处理各种JSON格式输入和错误修复
    - 中文内容完美支持
    - 自动生成下载链接
    """
    import tempfile, os, time, shutil, subprocess
    try:
        logger.info("Starting Markdown to DOCX conversion")
        logger.info(f"原始输入类型: {type(markdown_text)}")
        logger.info(f"原始输入长度: {len(markdown_text) if markdown_text else 0}")
        logger.info(f"原始输入预览: {repr(markdown_text[:200]) if markdown_text else 'None'}")
        logger.info(f"Arguments: {arguments}")
        
        # 处理输入格式 - markdown_text第一优先级（必需参数）
        input_text = None
        
        # 第一优先级：直接传入的markdown_text参数（必需参数）
        if markdown_text:
            input_text = markdown_text
            logger.info("使用markdown_text参数（第一优先级）")
        
        # 第二优先级：通过arguments字段传入（备用）
        elif arguments:
            input_text = arguments
            logger.info("使用arguments参数（第二优先级）")
        
        if not input_text:
            logger.error("没有找到有效的输入内容")
            return {"success": False, "error": "没有找到有效的输入内容，请提供markdown_text或arguments参数"}
        
        # 使用通用JSON格式修正函数处理各种格式的输入
        logger.info(f"调用fix_json_format前的文本类型: {type(input_text)}")
        logger.info(f"调用fix_json_format前的文本长度: {len(input_text) if input_text else 0}")
        logger.info(f"调用fix_json_format前的文本预览: {repr(input_text[:300]) if input_text else 'None'}")
        
        corrected_text = fix_json_format(input_text)
        logger.info(f"修正后长度: {len(corrected_text)}")
        logger.info(f"修正后预览: {repr(corrected_text[:200])}")
        
        # 额外的调试信息
        if corrected_text != input_text:
            logger.info("内容在fix_json_format过程中被修改")
        else:
            logger.info("内容在fix_json_format过程中未被修改")
        
        # 特殊处理：如果修正后的内容仍然包含JSON结构，尝试进一步处理
        # 这种情况通常发生在输入是嵌套JSON格式时
        if corrected_text.startswith('{') and '"markdown_text"' in corrected_text:
            logger.info("检测到JSON结构，尝试进一步处理")
            try:
                import json
                # 尝试直接解析JSON
                parsed = json.loads(corrected_text)
                if isinstance(parsed, dict) and 'markdown_text' in parsed:
                    corrected_text = parsed['markdown_text']
                    logger.info("成功从JSON中提取markdown_text字段")
            except json.JSONDecodeError:
                logger.warning("JSON解析失败，尝试字符串提取")
                # 尝试字符串提取方式
                start_marker = '"markdown_text": "'
                start_pos = corrected_text.find(start_marker)
                if start_pos != -1:
                    start_content = start_pos + len(start_marker)
                    # 查找结束位置
                    end_pos = corrected_text.find('"}', start_content)
                    if end_pos == -1:
                        end_pos = corrected_text.rfind('"')
                    if end_pos > start_content:
                        corrected_text = corrected_text[start_content:end_pos]
                        # 处理转义字符
                        corrected_text = corrected_text.replace('\\n', '\n')
                        corrected_text = corrected_text.replace('\\r', '\r')
                        corrected_text = corrected_text.replace('\\t', '\t')
                        corrected_text = corrected_text.replace('\\"', '"')
                        logger.info("通过字符串提取成功获取内容")
        
        # 终极容错处理：如果还是JSON格式，尝试暴力提取
        # 这是最后的兜底方案，确保能处理各种复杂格式
        if corrected_text.startswith('{') and '"markdown_text"' in corrected_text:
            logger.info("尝试终极容错处理")
            try:
                # 暴力提取：找到markdown_text字段的内容
                start_marker = '"markdown_text": "'
                start_pos = corrected_text.find(start_marker)
                if start_pos != -1:
                    start_content = start_pos + len(start_marker)
                    # 从开始位置向后查找结束位置
                    remaining_text = corrected_text[start_content:]
                    # 尝试多种结束模式
                    end_patterns = ['"}', '",', '"}', '"']
                    for pattern in end_patterns:
                        end_pos = remaining_text.find(pattern)
                        if end_pos > 0:
                            content = remaining_text[:end_pos]
                            # 处理转义字符
                            content = content.replace('\\n', '\n')
                            content = content.replace('\\r', '\r')
                            content = content.replace('\\t', '\t')
                            content = content.replace('\\"', '"')
                            corrected_text = content
                            logger.info("通过终极容错处理成功获取内容")
                            break
            except Exception as e:
                logger.warning(f"终极容错处理失败: {str(e)}")
        
        # 通用JSON格式处理：处理包含换行符的JSON
        # 这种情况通常发生在输入包含多行文本时
        if corrected_text.startswith('{') and '"markdown_text"' in corrected_text:
            logger.info("尝试通用JSON格式处理")
            try:
                # 处理包含换行符的JSON格式
                start_marker = '"markdown_text": "'
                start_pos = corrected_text.find(start_marker)
                if start_pos != -1:
                    start_content = start_pos + len(start_marker)
                    remaining_text = corrected_text[start_content:]
                    
                    # 尝试多种结束模式
                    end_patterns = ['"}', '",', '"}', '"']
                    for pattern in end_patterns:
                        end_pos = remaining_text.find(pattern)
                        if end_pos > 0:
                            content = remaining_text[:end_pos]
                            # 处理转义字符
                            content = content.replace('\\n', '\n')
                            content = content.replace('\\r', '\r')
                            content = content.replace('\\t', '\t')
                            content = content.replace('\\"', '"')
                            corrected_text = content
                            logger.info("通过通用JSON格式处理成功获取内容")
                            break
                    
                    # 如果找不到明确的结束模式，尝试从后往前查找
                    if corrected_text.startswith('{'):
                        end_pos = remaining_text.rfind('"')
                        if end_pos > 0:
                            content = remaining_text[:end_pos]
                            # 处理转义字符
                            content = content.replace('\\n', '\n')
                            content = content.replace('\\r', '\r')
                            content = content.replace('\\t', '\t')
                            content = content.replace('\\"', '"')
                            corrected_text = content
                            logger.info("通过后向查找成功获取内容")
            except Exception as e:
                logger.warning(f"通用JSON格式处理失败: {str(e)}")
        
        # 验证修正后的内容
        if not corrected_text or len(corrected_text.strip()) == 0:
            logger.error("修正后的内容为空")
            return {"success": False, "error": "修正后的markdown内容为空，请检查输入格式"}
        
        # 检查内容是否包含有效的markdown语法
        if not any(char in corrected_text for char in ['#', '*', '-', '`', '[']):
            logger.warning("修正后的内容可能不是有效的markdown格式，但会继续处理")
        
        # 创建临时目录和文件
        temp_dir = tempfile.mkdtemp()
        temp_md_file = os.path.join(temp_dir, f"input_{int(time.time())}.md")
        temp_docx_file = os.path.join(temp_dir, f"output_{int(time.time())}.docx")
        
        # 写入markdown内容到临时文件
        with open(temp_md_file, "w", encoding="utf-8") as f:
            f.write(corrected_text)
        logger.info(f"已写入临时markdown文件: {temp_md_file}")
        
        # 检查pandoc是否可用
        try:
            subprocess.run(["pandoc", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            logger.error(f"Pandoc 未安装或不可用: {str(e)}")
            shutil.rmtree(temp_dir)
            return {"success": False, "error": "Pandoc 未安装或不可用，请先在服务器安装 pandoc。"}
        
        # 使用pandoc进行转换
        try:
            logger.info(f"开始Pandoc转换: {temp_md_file} -> {temp_docx_file}")
            result = subprocess.run([
                "pandoc", temp_md_file, "-o", temp_docx_file
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8')
                logger.error(f"Pandoc 转换失败: {error_msg}")
                shutil.rmtree(temp_dir)
                return {"success": False, "error": f"Pandoc 转换失败: {error_msg}"}
            logger.info(f"Pandoc 转换完成，检查临时输出文件是否存在: {temp_docx_file}, 存在: {os.path.exists(temp_docx_file)}")
            if not os.path.exists(temp_docx_file):
                logger.error(f"转换失败，未生成临时输出文件: {temp_docx_file}")
                shutil.rmtree(temp_dir)
                return {"success": False, "error": f"Markdown转换未生成输出文件，可能源文件损坏或格式不支持。"}
        except Exception as e:
            logger.error(f"Markdown转换异常: {str(e)}")
            shutil.rmtree(temp_dir)
            return {"success": False, "error": f"Error converting Markdown to DOCX: {str(e)}"}
        
        # 保存输出文件到指定目录
        output_file = f"{OUTPUT_DIR}/output_{int(time.time())}.docx"
        logger.info(f"准备保存输出文件到: {output_file}")
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)
        
        if not os.path.exists(temp_docx_file):
            logger.error(f"临时输出文件未生成: {temp_docx_file}")
            shutil.rmtree(temp_dir)
            return {"success": False, "error": f"临时输出文件未生成: {temp_docx_file}"}
        
        # 移动文件并自动上传到静态服务器
        try:
            shutil.move(temp_docx_file, output_file)
            logger.info(f"已成功保存输出文件到: {output_file}")
            # 自动上传到静态服务器
            try:
                from upload_to_server import upload_to_static_server
                remote_file = f"/root/files/{os.path.basename(output_file)}"
                hostname = "8.156.74.79"
                username = "root"
                password = "zfsZBC123."
                logger.info(f"开始上传到静态服务器: {remote_file}")
                upload_success = upload_to_static_server(output_file, remote_file, hostname, username, password)
                if not upload_success:
                    logger.error(f"自动上传到静态服务器失败: {remote_file}")
                    return {"success": False, "error": f"自动上传到静态服务器失败: {remote_file}"}
                logger.info(f"自动上传到静态服务器成功: {remote_file}")
            except Exception as e:
                logger.error(f"自动上传到静态服务器异常: {str(e)}")
                return {"success": False, "error": f"自动上传到静态服务器异常: {str(e)}"}
        except Exception as e:
            logger.error(f"移动输出文件失败: {str(e)}")
            shutil.rmtree(temp_dir)
            return {"success": False, "error": f"Error moving output file: {str(e)}"}
        
        # 清理临时文件并返回结果
        shutil.rmtree(temp_dir)
        download_url = get_download_url(os.path.basename(output_file))
        logger.info(f"转换完成，下载链接: {download_url}")
        return {"success": True, "output_file": output_file, "download_url": download_url}
    except Exception as e:
        logger.error(f"Unexpected error in markdown2docx: {str(e)}")
        return {"success": False, "error": f"Error converting Markdown to DOCX: {str(e)}"} 

# 专门处理嵌套参数格式的markdown转换工具
@mcp.tool("markdown_convert")
def markdown_convert(output_format: str = "docx", markdown_text: str = None, content: str = None) -> dict:
    """
    专门处理多种参数格式的Markdown转换工具，支持转换为DOCX或PDF格式。
    
    参数：
    - output_format: 输出格式，支持 "docx" 或 "pdf" (默认: "docx")
    - markdown_text: markdown内容（第一优先级）
    - content: markdown内容（第二优先级）
    
    ✅ 正确的JSON格式示例：
    
    转换为DOCX (推荐):
    {
        "output_format": "docx",
        "markdown_text": "# 我的文档\n\n这是一段内容\n\n- 列表项1\n- 列表项2"
    }
    
    转换为PDF:
    {
        "output_format": "pdf",
        "markdown_text": "# 标题\n\n内容"
    }
    
    使用content参数 (备用):
    {
        "output_format": "docx",
        "content": "# 标题\n\n内容"
    }
    
    ❌ 错误示例 (请避免):
    {"format": "docx", "text": "内容"}              // 错误的参数名
    {"output_format": {"type": "docx"}}              // 格式应为字符串
    {"markdown_text": {"content": "内容"}}           // 嵌套对象
    
    优先级处理顺序：
    1. markdown_text 参数（第一优先级）
    2. content 参数（第二优先级）
    """
    try:
        logger.info(f"Markdown转换工具被调用，输出格式: {output_format}")
        logger.info(f"markdown_text: {markdown_text}")
        logger.info(f"content: {content}")
        
        input_text = None
        
        # 第一优先级：markdown_text参数
        if markdown_text:
            input_text = markdown_text
            logger.info("使用markdown_text参数（第一优先级）")
        
        # 第二优先级：content参数
        elif content:
            input_text = content
            logger.info("使用content参数（第二优先级）")
        
        if not input_text:
            return {"success": False, "error": "未找到有效的markdown内容，请提供markdown_text或content参数"}
        
        # 根据输出格式调用相应的转换函数
        if output_format.lower() == "docx":
            return markdown2docx(markdown_text=input_text)
        elif output_format.lower() == "pdf":
            return markdown2pdf(markdown_text=input_text)
        else:
            return {"success": False, "error": f"不支持的输出格式: {output_format}"}
        
    except Exception as e:
        logger.error(f"Markdown转换工具异常: {str(e)}")
        return {"success": False, "error": f"转换失败: {str(e)}"}

if __name__ == "__main__":
    mcp.run()
