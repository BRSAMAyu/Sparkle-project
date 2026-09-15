# WeasyPrint 依赖安装指南

## 概述

WeasyPrint 用于生成学习周报的 PDF 文件。它依赖于系统的 GTK+ 库（Pango, Cairo, GLib）。

## 当前状态

- **版本**: WeasyPrint 67.0
- **用途**: `weekly_synthesis_service.py` - 周报 PDF 生成
- **容错**: ✅ 已实现，导入失败时不影响应用启动

## 依赖声明

已在 `requirements.txt` 中添加：
```
weasyprint>=60.0
jinja2>=3.1.0
```

## 系统依赖

### macOS (本地开发)

使用 Homebrew 安装 GTK+ 库：
```bash
brew install cairo pango glib gdk-pixbuf libffi
```

### Linux (Docker)

已在 `backend/Dockerfile` 中配置：
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libglib2.0-0 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libfreetype6 \
    shared-mime-info \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*
```

## 环境配置

### macOS 本地开发

问题：WeasyPrint 找不到 Homebrew 安装的动态库。

**方案 1**: 使用启动脚本（推荐）
```bash
make grpc-server  # 自动设置 DYLD_LIBRARY_PATH
```

**方案 2**: 手动设置环境变量
```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH
cd backend && python grpc_server.py
```

### Docker 环境

无需额外配置，Docker 容器内已正确配置。

## 使用方式

```python
from app.services.analytics.weekly_synthesis_service import WeeklySynthesisService

# 生成周报数据
report = await service.generate_report(user_id="user-123")

# 生成 PDF（需要 WeasyPrint 和 Jinja2）
pdf_path = await service.generate_pdf(
    report_data=report,
    output_path="/path/to/report.pdf"
)
```

## 故障排查

### 错误: `OSError: cannot load library 'libgobject-2.0-0'`

**原因**: cffi 找不到 GTK+ 动态库

**解决**:
```bash
# 检查库是否存在
brew list pango | grep libgobject

# 设置环境变量
export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH

# 重新安装 cffi
pip install --force-reinstall --no-cache-dir cffi
```

### 错误: `PDF generation requires jinja2 and weasyprint`

**原因**: 依赖未安装

**解决**:
```bash
pip install -r requirements.txt
```

## 测试

验证 WeasyPrint 是否正常工作：
```bash
cd backend
DYLD_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python -c \
  "import weasyprint; print('WeasyPrint version:', weasyprint.__version__)"
```

预期输出：
```
WeasyPrint version: 67.0
```

## 替代方案

如果 WeasyPrint 持续出现问题，可以考虑：

1. **ReportLab**: 纯 Python PDF 库，无系统依赖
2. **pdfkit**: 使用 wkhtmltopdf（需要系统依赖）
3. **xhtml2pdf**: 基于 ReportLab 的 HTML 转 PDF

当前代码已实现容错，在 WeasyPrint 不可用时优雅降级。
