#!/usr/bin/env python3
"""
JSON格式验证和修复工具

用于检测和修复MCP工具调用中的JSON格式错误，特别是API错误(23700)问题。

🚨 重要：API错误(23700)的根本原因
====================================
错误信息：Agent节点执行失败(模型返回的推理内容格式不正确,无效的插件参数JSON格式)

根本原因：模型返回了嵌套的JSON对象，而不是直接传递字符串参数

❌ 错误格式示例：
{"markdown_text": "# 标题\n内容"}  # 嵌套JSON对象

✅ 正确格式示例：
markdown_text: "# 标题\n内容"  # 直接字符串

关键修复原则：
1. 参数值必须是字符串类型，不能是对象
2. 不要将字符串内容包装在额外的JSON对象中
3. 直接传递markdown/HTML字符串内容
4. 使用正确的参数名称（markdown_text 或 html_content）
"""

import json
import re
import logging
from typing import Dict, Any, Tuple, Optional

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPFormatValidator:
    """
    MCP工具调用格式验证和修复器
    
    专门用于解决API错误(23700)问题，确保MCP工具调用的JSON格式正确。
    
    主要功能：
    1. 检测嵌套JSON对象错误
    2. 验证参数名称正确性
    3. 检查工具调用格式完整性
    4. 提供自动修复建议
    
    修复的核心问题：
    - 嵌套JSON对象：{"markdown_text": "内容"} -> markdown_text: "内容"
    - 参数名错误：markdown: "内容" -> markdown_text: "内容"
    - 格式不完整：缺少@File Converter前缀
    """
    
    def __init__(self):
        # 定义正确的参数名称映射表
        # 这是解决API错误(23700)的关键：确保使用正确的参数名
        self.correct_param_names = {
            'markdown2docx': 'markdown_text',  # ✅ 正确参数名
            'html2docx': 'html_content',       # ✅ 正确参数名
            'markdown2pdf': 'markdown_text',    # ✅ 正确参数名
            'html2pdf': 'html_content',         # ✅ 正确参数名
            'docx2pdf': 'input_file',           # ✅ 正确参数名
            'pdf2docx': 'input_file',           # ✅ 正确参数名
            'convert_image': 'input_file',       # ✅ 正确参数名
            'excel2csv': 'input_file',          # ✅ 正确参数名
            'upload_file_to_server': 'input_file', # ✅ 正确参数名
            'upload_pdf_to_server': 'input_file'   # ✅ 正确参数名
        }
    
    def detect_json_format_error(self, tool_call: str) -> Tuple[bool, str, Optional[str]]:
        """
        检测JSON格式错误
        
        Args:
            tool_call: 工具调用字符串
            
        Returns:
            (has_error, error_type, suggested_fix)
        """
        try:
            # 检测嵌套JSON对象错误
            if self._has_nested_json_error(tool_call):
                return True, "nested_json", self._fix_nested_json_error(tool_call)
            
            # 检测参数名称错误
            if self._has_param_name_error(tool_call):
                return True, "param_name", self._fix_param_name_error(tool_call)
            
            # 检测格式错误
            if self._has_format_error(tool_call):
                return True, "format", self._fix_format_error(tool_call)
            
            return False, "", None
            
        except Exception as e:
            logger.error(f"检测JSON格式错误时发生异常: {e}")
            return True, "unknown", None
    
    def _has_nested_json_error(self, tool_call: str) -> bool:
        """
        检测嵌套JSON对象错误
        
        这是API错误(23700)的主要检测方法，识别以下错误模式：
        ❌ 错误：markdown_text: {"markdown_text": "内容"}
        ✅ 正确：markdown_text: "内容"
        
        Args:
            tool_call (str): 工具调用字符串
            
        Returns:
            bool: 是否存在嵌套JSON错误
        """
        # 查找嵌套JSON对象模式：markdown_text: {"markdown_text": "内容"}
        # 这是导致API错误(23700)的典型错误格式
        pattern = r'markdown_text:\s*\{[^}]*"markdown_text"[^}]*\}'
        return bool(re.search(pattern, tool_call))
    
    def _has_param_name_error(self, tool_call: str) -> bool:
        """检测参数名称错误"""
        # 查找错误的参数名称
        wrong_params = ['markdown:', 'html:', 'content:']
        return any(param in tool_call for param in wrong_params)
    
    def _has_format_error(self, tool_call: str) -> bool:
        """检测格式错误"""
        # 检查是否缺少必要的格式元素
        if '@File Converter' not in tool_call:
            return True
        if 'markdown2docx' in tool_call and 'markdown_text:' not in tool_call:
            return True
        if 'html2docx' in tool_call and 'html_content:' not in tool_call:
            return True
        return False
    
    def _fix_nested_json_error(self, tool_call: str) -> str:
        """
        修复嵌套JSON对象错误
        
        这是解决API错误(23700)的核心修复方法：
        
        修复前：markdown_text: {"markdown_text": "内容"}
        修复后：markdown_text: "内容"
        
        修复原理：
        1. 提取嵌套JSON对象中的实际内容
        2. 将内容直接作为字符串参数传递
        3. 避免额外的JSON包装层
        
        Args:
            tool_call (str): 包含嵌套JSON错误的工具调用字符串
            
        Returns:
            str: 修复后的工具调用字符串
        """
        # 提取嵌套JSON对象中的实际内容
        # 模式：markdown_text: {"markdown_text": "实际内容"}
        pattern = r'markdown_text:\s*\{[^}]*"markdown_text":\s*"([^"]*)"[^}]*\}'
        match = re.search(pattern, tool_call)
        if match:
            content = match.group(1)  # 提取实际内容
            # 替换为正确的直接字符串格式
            fixed_call = re.sub(pattern, f'markdown_text: "{content}"', tool_call)
            return fixed_call
        
        return tool_call
    
    def _fix_param_name_error(self, tool_call: str) -> str:
        """修复参数名称错误"""
        # 修复常见的参数名称错误
        fixes = {
            'markdown:': 'markdown_text:',
            'html:': 'html_content:',
            'content:': 'markdown_text:'
        }
        
        fixed_call = tool_call
        for wrong, correct in fixes.items():
            fixed_call = fixed_call.replace(wrong, correct)
        
        return fixed_call
    
    def _fix_format_error(self, tool_call: str) -> str:
        """修复格式错误"""
        # 确保有正确的工具调用格式
        if '@File Converter' not in tool_call:
            tool_call = '@File Converter\n' + tool_call
        
        return tool_call
    
    def validate_and_fix(self, tool_call: str) -> Tuple[bool, str, str]:
        """
        验证并修复工具调用格式
        
        Args:
            tool_call: 原始工具调用字符串
            
        Returns:
            (is_valid, original_call, fixed_call)
        """
        has_error, error_type, fix = self.detect_json_format_error(tool_call)
        
        if has_error:
            logger.warning(f"检测到{error_type}错误")
            if fix:
                logger.info("已生成修复建议")
                return False, tool_call, fix
            else:
                logger.error("无法自动修复，需要手动检查")
                return False, tool_call, tool_call
        else:
            logger.info("工具调用格式正确")
            return True, tool_call, tool_call

def main():
    """主函数 - 用于测试和演示"""
    validator = MCPFormatValidator()
    
    # 测试用例
    test_cases = [
        # 错误格式示例
        {
            "name": "嵌套JSON错误",
            "input": '''@File Converter
markdown2docx
markdown_text: {"markdown_text": "# 标题\n内容"}''',
            "expected_error": "nested_json"
        },
        {
            "name": "参数名称错误",
            "input": '''@File Converter
markdown2docx
markdown: "# 标题\n内容"''',
            "expected_error": "param_name"
        },
        # 正确格式示例
        {
            "name": "正确格式",
            "input": '''@File Converter
markdown2docx
markdown_text: |
  # 标题
  
  ## 章节
  内容''',
            "expected_error": None
        }
    ]
    
    print("=== MCP工具调用格式验证测试 ===\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"测试 {i}: {test_case['name']}")
        print(f"输入: {test_case['input']}")
        
        is_valid, original, fixed = validator.validate_and_fix(test_case['input'])
        
        if is_valid:
            print("✅ 格式正确")
        else:
            print("❌ 格式错误")
            print(f"修复建议: {fixed}")
        
        print("-" * 50)

if __name__ == "__main__":
    main() 