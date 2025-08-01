#!/usr/bin/env python3
"""
测试推理格式修复功能的脚本
"""

import json
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from file_converter_server import fix_reasoning_format, enhanced_parse_json

def test_reasoning_format_fixing():
    """测试推理格式修复功能"""
    
    # 测试用例1: 推理格式错误
    print("测试1: 推理格式错误")
    reasoning_error = 'Agent节点执行失败(模型返回的推理内容格式不正确,无效的推理格式，缺少必要的标识字段,sag00017544@dx19866d281e5a4f3182)'
    try:
        result = fix_reasoning_format(reasoning_error)
        print(f"✓ 推理格式修复成功: {result}")
    except Exception as e:
        print(f"✗ 推理格式修复失败: {e}")
    
    # 测试用例2: 推理格式错误包含JSON内容
    print("\n测试2: 推理格式错误包含JSON内容")
    reasoning_with_json = 'Agent节点执行失败(模型返回的推理内容格式不正确,无效的推理格式，缺少必要的标识字段,sag00017544@dx19866d281e5a4f3182) {"markdown_text": "# 测试标题\\n\\n这是测试内容"}'
    try:
        result = fix_reasoning_format(reasoning_with_json)
        print(f"✓ 推理格式修复成功: {result}")
    except Exception as e:
        print(f"✗ 推理格式修复失败: {e}")
    
    # 测试用例3: 推理格式错误包含markdown内容
    print("\n测试3: 推理格式错误包含markdown内容")
    reasoning_with_markdown = 'Agent节点执行失败(模型返回的推理内容格式不正确,无效的推理格式，缺少必要的标识字段,sag00017544@dx19866d281e5a4f3182) # 测试标题\\n\\n这是测试内容\\n\\n## 子标题\\n\\n更多内容'
    try:
        result = fix_reasoning_format(reasoning_with_markdown)
        print(f"✓ 推理格式修复成功: {result}")
    except Exception as e:
        print(f"✗ 推理格式修复失败: {e}")
    
    # 测试用例4: 正常的markdown内容
    print("\n测试4: 正常的markdown内容")
    normal_markdown = "# 测试标题\\n\\n这是测试内容\\n\\n## 子标题\\n\\n更多内容"
    try:
        result = fix_reasoning_format(normal_markdown)
        print(f"✓ 正常内容处理成功: {result}")
    except Exception as e:
        print(f"✗ 正常内容处理失败: {e}")
    
    # 测试用例5: 复杂的推理格式错误
    print("\n测试5: 复杂的推理格式错误")
    complex_reasoning = 'Agent节点执行失败(模型返回的推理内容格式不正确,无效的推理格式，缺少必要的标识字段,sag00017544@dx19866d281e5a4f3182) 请帮我生成一份关于人工智能在医疗领域应用的研究报告'
    try:
        result = fix_reasoning_format(complex_reasoning)
        print(f"✓ 复杂推理格式修复成功: {result}")
    except Exception as e:
        print(f"✗ 复杂推理格式修复失败: {e}")

def test_json_parsing_with_reasoning():
    """测试JSON解析与推理格式修复的结合"""
    
    print("\n=== 测试JSON解析与推理格式修复的结合 ===")
    
    # 测试用例1: 推理格式错误中的JSON
    print("\n测试1: 推理格式错误中的JSON")
    reasoning_json = 'Agent节点执行失败(模型返回的推理内容格式不正确,无效的推理格式，缺少必要的标识字段,sag00017544@dx19866d281e5a4f3182) {"markdown_text": "# 人工智能研究报告\\n\\n## 摘要\\n\\n本文探讨了人工智能的发展现状..."}'
    try:
        # 先尝试JSON解析
        result = enhanced_parse_json(reasoning_json)
        print(f"✓ JSON解析成功: {result}")
    except Exception as e:
        print(f"✗ JSON解析失败: {e}")
        # 如果JSON解析失败，尝试推理格式修复
        try:
            fixed = fix_reasoning_format(reasoning_json)
            print(f"✓ 推理格式修复成功: {fixed}")
        except Exception as e2:
            print(f"✗ 推理格式修复也失败: {e2}")

if __name__ == "__main__":
    test_reasoning_format_fixing()
    test_json_parsing_with_reasoning() 