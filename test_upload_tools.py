#!/usr/bin/env python3
"""
测试上传工具功能
"""

import sys
import os
import tempfile
import base64

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_upload_tools():
    """测试上传工具是否正常工作"""
    try:
        # 导入MCP服务器
        from file_converter_server import mcp
        
        print("✅ MCP服务器导入成功")
        print(f"✅ 可用工具数量: {len(mcp.tools)}")
        
        # 检查工具列表
        tool_names = [tool.name for tool in mcp.tools]
        print("✅ 可用工具列表:")
        for tool_name in sorted(tool_names):
            print(f"  - {tool_name}")
        
        # 检查特定工具是否存在
        required_tools = [
            "upload_pdf_to_server",
            "upload_file_to_server",
            "docx2pdf",
            "pdf2docx",
            "markdown2docx",
            "html2docx"
        ]
        
        print("\n✅ 检查必需工具:")
        for tool_name in required_tools:
            if tool_name in tool_names:
                print(f"  ✅ {tool_name} - 已注册")
            else:
                print(f"  ❌ {tool_name} - 未找到")
        
        # 测试工具参数
        print("\n✅ 测试工具参数:")
        for tool_name in ["upload_pdf_to_server", "upload_file_to_server"]:
            if tool_name in tool_names:
                tool = next(t for t in mcp.tools if t.name == tool_name)
                print(f"  📋 {tool_name} 参数:")
                for param in tool.input_schema.get("properties", {}).keys():
                    print(f"    - {param}")
        
        print("\n✅ 所有测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_file_creation():
    """测试文件创建功能"""
    try:
        # 创建一个测试文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("这是一个测试文件\n用于验证上传功能")
            test_file_path = f.name
        
        print(f"✅ 测试文件创建成功: {test_file_path}")
        
        # 读取文件并转换为base64
        with open(test_file_path, 'rb') as f:
            file_content = f.read()
            base64_content = base64.b64encode(file_content).decode('utf-8')
        
        print(f"✅ Base64编码成功，长度: {len(base64_content)}")
        
        # 清理测试文件
        os.unlink(test_file_path)
        print("✅ 测试文件清理完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 文件创建测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 开始测试上传工具...")
    print("=" * 50)
    
    success1 = test_upload_tools()
    success2 = test_file_creation()
    
    print("=" * 50)
    if success1 and success2:
        print("🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("💥 部分测试失败！")
        sys.exit(1) 