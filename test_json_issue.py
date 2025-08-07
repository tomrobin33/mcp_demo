#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re

def fix_json_format(text):
    """修正各种可能的JSON格式错误，适用于所有工具"""
    if not text:
        return ""
    
    # 移除可能的非JSON前缀
    text = text.strip()
    
    # 特殊处理：如果输入文本看起来已经是纯文本内容（包含换行但不是JSON）
    # 直接返回，不进行JSON解析处理
    if not text.startswith('{') and not text.startswith('"') and '\n' in text:
        print("检测到包含换行符的纯文本，直接返回")
        return text
    
    # 如果已经是纯文本（不是JSON），直接返回
    if not text.startswith('{') and not text.startswith('"'):
        return text
    
    # 处理被转义的JSON字符串
    if text.startswith('"') and text.endswith('"'):
        try:
            # 尝试解析为JSON字符串
            return json.loads(text)
        except:
            # 如果不是有效的JSON字符串，移除引号
            return text[1:-1] if len(text) > 2 else text
    
    # 特殊处理：修复不完整的JSON字符串
    # 这种情况通常发生在AI生成的JSON格式中途被截断
    if text.startswith('{') and '"markdown_text"' in text:
        # 首先尝试正常解析JSON，如果成功就不需要修复
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and 'markdown_text' in parsed:
                print("JSON解析成功，直接返回markdown_text内容")
                return parsed['markdown_text']
        except json.JSONDecodeError:
            print("JSON解析失败，尝试修复不完整的JSON格式")
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
                        print(f"修复JSON格式，原长度: {len(text)}, 修复后长度: {len(fixed_json)}")
                        try:
                            # 验证修复后的JSON是否有效
                            parsed = json.loads(fixed_json)
                            if 'markdown_text' in parsed:
                                print("JSON修复成功，返回markdown_text内容")
                                return parsed['markdown_text']
                        except Exception as e:
                            print(f"修复后的JSON仍然无效: {str(e)}")
                            # 如果修复失败，直接返回提取的内容
                            return content_part
    
    # 处理嵌套JSON格式：{"arguments": "{\"markdown_text\": \"...\"}", "name": "..."}
    if text.startswith('{') and '"arguments"' in text:
        try:
            # 先解析外层JSON
            outer_parsed = json.loads(text)
            if isinstance(outer_parsed, dict) and 'arguments' in outer_parsed:
                arguments_str = outer_parsed['arguments']
                print("检测到嵌套JSON格式，解析arguments字段")
                
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
                    print("内层JSON解析失败，尝试字符串提取")
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
            print(f"外层JSON解析失败: {str(e)}")
        except Exception as e:
            print(f"嵌套JSON处理失败: {str(e)}")
    
    # 处理JSON对象中的各种字段
    if text.startswith('{'):
        try:
            # 预处理JSON字符串，处理换行符和特殊字符
            processed_text = text
            
            # 更智能的JSON预处理
            # 1. 处理字符串值中的换行符
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
            print(f"JSON解析失败，尝试其他方法: {str(e)}")
            # JSON解析失败，尝试提取内容
            pass
    
    # 如果所有方法都失败，返回原始文本
    return text

# 测试用例
test_cases = [
    # 问题案例：包含换行符的JSON
    '{"markdown_text": "# 关于人工智能产业发展现状及战略方向的报告\n\n## 一、发展现状\n\n人工智能技术正在快速发展..."}',
    
    # 正常案例
    '{"markdown_text": "# 标题\\n这是内容"}',
    
    # 纯文本案例
    "# 关于人工智能产业发展现状及战略方向的报告\n\n## 一、发展现状\n\n人工智能技术正在快速发展...",
    
    # 不完整JSON案例
    '{"markdown_text": "# 关于人工智能产业发展现状及战略方向的报告',
]

print("=== 测试JSON解析问题 ===")
for i, test_case in enumerate(test_cases, 1):
    print(f"\n--- 测试案例 {i} ---")
    print(f"输入: {repr(test_case[:100])}...")
    try:
        result = fix_json_format(test_case)
        print(f"输出: {repr(result[:100])}...")
        print(f"成功: {len(result)} 字符")
    except Exception as e:
        print(f"错误: {str(e)}")
