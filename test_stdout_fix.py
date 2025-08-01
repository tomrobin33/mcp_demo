#!/usr/bin/env python3
"""
测试stdout修复的脚本
验证MCP服务器不会向stdout输出非JSON内容
"""

import sys
import os
import subprocess
import json
import tempfile

def test_stdout_output():
    """测试MCP服务器的stdout输出"""
    print("测试MCP服务器的stdout输出...")
    
    # 创建一个简单的测试文件
    test_md_content = "# 测试标题\n\n这是测试内容。"
    test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
    test_file.write(test_md_content)
    test_file.close()
    
    try:
        # 启动MCP服务器进程
        process = subprocess.Popen(
            [sys.executable, "file_converter_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # 等待一下让服务器启动
        import time
        time.sleep(2)
        
        # 检查stdout是否有非JSON输出
        stdout_output = ""
        stderr_output = ""
        
        # 尝试读取一些输出
        try:
            stdout_output, stderr_output = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout_output, stderr_output = process.communicate()
        
        print(f"stdout输出长度: {len(stdout_output)}")
        print(f"stderr输出长度: {len(stderr_output)}")
        
        if stdout_output.strip():
            print("⚠️ 发现stdout输出:")
            print(stdout_output[:200] + "..." if len(stdout_output) > 200 else stdout_output)
            
            # 检查是否是有效的JSON
            try:
                json.loads(stdout_output.strip())
                print("✓ stdout输出是有效的JSON")
            except json.JSONDecodeError:
                print("✗ stdout输出不是有效的JSON")
                return False
        else:
            print("✓ stdout没有输出（这是正确的）")
        
        if stderr_output.strip():
            print("✓ stderr有日志输出（这是正确的）")
            print(stderr_output[:200] + "..." if len(stderr_output) > 200 else stderr_output)
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        return False
    finally:
        # 清理测试文件
        try:
            os.unlink(test_file.name)
        except:
            pass

def test_startup_script():
    """测试启动脚本的stdout输出"""
    print("\n测试启动脚本的stdout输出...")
    
    try:
        # 启动启动脚本进程
        process = subprocess.Popen(
            [sys.executable, "start_mcp_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # 等待一下让脚本启动
        import time
        time.sleep(3)
        
        # 检查输出
        try:
            stdout_output, stderr_output = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout_output, stderr_output = process.communicate()
        
        print(f"启动脚本stdout输出长度: {len(stdout_output)}")
        print(f"启动脚本stderr输出长度: {len(stderr_output)}")
        
        if stdout_output.strip():
            print("⚠️ 启动脚本发现stdout输出:")
            print(stdout_output[:200] + "..." if len(stdout_output) > 200 else stdout_output)
            return False
        else:
            print("✓ 启动脚本stdout没有输出（这是正确的）")
        
        if stderr_output.strip():
            print("✓ 启动脚本stderr有输出（这是正确的）")
            print(stderr_output[:200] + "..." if len(stderr_output) > 200 else stderr_output)
        
        return True
        
    except Exception as e:
        print(f"启动脚本测试失败: {e}")
        return False

if __name__ == "__main__":
    print("=== 测试stdout修复 ===")
    
    success1 = test_stdout_output()
    success2 = test_startup_script()
    
    if success1 and success2:
        print("\n✓ 所有测试通过！stdout修复成功。")
    else:
        print("\n✗ 部分测试失败，需要进一步修复。") 