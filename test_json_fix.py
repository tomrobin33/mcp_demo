#!/usr/bin/env python3
"""
测试JSON修复功能的脚本
"""

import json
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from file_converter_server import enhanced_parse_json, validate_and_fix_mcp_parameters, MARKDOWN2DOCX_PARAMS

def test_json_fixing():
    """测试JSON修复功能"""
    
    # 测试用例1: 正常的JSON
    print("测试1: 正常JSON")
    normal_json = '{"markdown_text": "# 测试标题\n\n这是测试内容"}'
    try:
        result = enhanced_parse_json(normal_json)
        print(f"✓ 成功解析: {result}")
    except Exception as e:
        print(f"✗ 解析失败: {e}")
    
    # 测试用例2: 包含前缀的JSON
    print("\n测试2: 包含前缀的JSON")
    prefixed_json = 'Agent节点执行失败(模型返回的推理内容格式不正确,无效的插件参数JSON格式: {"markdown_text": "# 近期人工智能领域重大事件总结\n\n## 一、政策与战略部署..."}'
    try:
        result = enhanced_parse_json(prefixed_json)
        print(f"✓ 成功解析: {result}")
    except Exception as e:
        print(f"✗ 解析失败: {e}")
    
    # 测试用例3: 包含尾随字符的JSON
    print("\n测试3: 包含尾随字符的JSON")
    trailing_json = '{"markdown_text": "# 测试内容"} ,sag00017744@dx19866c2c836a44d182'
    try:
        result = enhanced_parse_json(trailing_json)
        print(f"✓ 成功解析: {result}")
    except Exception as e:
        print(f"✗ 解析失败: {e}")
    
    # 测试用例4: 纯markdown内容
    print("\n测试4: 纯markdown内容")
    pure_markdown = "# 测试标题\n\n这是测试内容\n\n## 子标题\n\n更多内容"
    try:
        result = enhanced_parse_json(pure_markdown)
        print(f"✓ 成功解析: {result}")
    except Exception as e:
        print(f"✗ 解析失败: {e}")
    
    # 测试用例5: 参数验证
    print("\n测试5: 参数验证")
    test_params = {"markdown_text": "# 测试内容"}
    try:
        result = validate_and_fix_mcp_parameters(test_params, MARKDOWN2DOCX_PARAMS)
        print(f"✓ 参数验证成功: {result}")
    except Exception as e:
        print(f"✗ 参数验证失败: {e}")

if __name__ == "__main__":
    test_json_fixing() 