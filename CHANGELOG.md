# 更新日志

## [2024-12-19] - 添加通用文件上传功能

### 新增功能
- ✅ **新增 `upload_file_to_server` 工具**
  - 支持上传任意格式文件到服务器（Word、PDF、图片等）
  - 支持本地文件路径和URL输入
  - 支持Base64编码内容输入
  - 自动检测文件格式
  - 返回公网下载链接

### 改进功能
- ✅ **重命名文件避免冲突**
  - 将 `upload_to_server.py` 重命名为 `sftp_upload_helper.py`
  - 避免与MCP工具名称产生混淆
  - 更新所有相关引用

- ✅ **更新系统提示词**
  - 添加新工具的使用说明
  - 更新工作流程示例
  - 明确推荐使用 `upload_file_to_server` 工具

- ✅ **更新启动脚本**
  - 在 `start_mcp_server.py` 中添加新工具描述
  - 确保工具正确暴露给大模型

- ✅ **更新依赖配置**
  - 在 `pyproject.toml` 中添加缺失的依赖
  - 确保所有必需包都已包含

### 技术细节
- **工具名称**: `upload_file_to_server`
- **支持格式**: 任意文件格式（docx, pdf, jpg, png等）
- **输入方式**: 
  - `input_file`: 文件路径或URL
  - `file_content_base64`: Base64编码内容
  - `file_format`: 文件格式（可选，自动检测）
- **输出**: 包含下载链接的成功响应

### 使用示例
```python
# 上传本地Word文档
@File Converter
upload_file_to_server
input_file: document.docx
file_format: docx

# 上传Base64编码的PDF
@File Converter
upload_file_to_server
file_content_base64: [base64内容]
file_format: pdf
```

### 解决的问题
- ❌ **原问题**: 上传功能只支持PDF格式
- ✅ **解决方案**: 新增通用文件上传工具，支持Word文档和其他格式
- ✅ **兼容性**: 保留原有的 `upload_pdf_to_server` 工具，确保向后兼容

### 测试验证
- ✅ 创建测试脚本 `test_upload_tools.py`
- ✅ 验证工具正确注册到MCP服务器
- ✅ 验证参数定义正确
- ✅ 验证文件操作功能正常

### 文件变更列表
- `file_converter_server.py` - 添加新工具
- `sftp_upload_helper.py` - 重命名文件
- `system_prompt.md` - 更新系统提示词
- `start_mcp_server.py` - 更新工具描述
- `pyproject.toml` - 更新依赖
- `test_upload_tools.py` - 新增测试脚本
- `CHANGELOG.md` - 新增更新日志 