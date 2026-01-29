#!/usr/bin/env python3
"""
WeasyPrint 依赖测试脚本
测试 WeasyPrint 和 Jinja2 是否正确安装和配置
"""
import sys
import os

# macOS: 自动设置 DYLD_LIBRARY_PATH 用于 WeasyPrint
if sys.platform == "darwin" and os.path.exists("/opt/homebrew/lib"):
    if "DYLD_LIBRARY_PATH" not in os.environ:
        os.environ["DYLD_LIBRARY_PATH"] = "/opt/homebrew/lib"
        print("✓ 自动设置 DYLD_LIBRARY_PATH=/opt/homebrew/lib\n")

def test_weasyprint_import():
    """测试 WeasyPrint 导入"""
    print("=" * 50)
    print("测试 WeasyPrint 导入...")
    print("=" * 50)

    try:
        import weasyprint
        print(f"✓ WeasyPrint 版本: {weasyprint.__version__}")
        print(f"✓ 安装路径: {weasyprint.__file__}")
        return True
    except ImportError as e:
        print(f"✗ WeasyPrint 导入失败: {e}")
        print("  请运行: pip install weasyprint")
        return False
    except OSError as e:
        print(f"✗ WeasyPrint 系统库加载失败: {e}")
        print("  这是 GTK+ 库问题，请参考 WEASYPRINT_SETUP.md")
        return False

def test_jinja2_import():
    """测试 Jinja2 导入"""
    print("\n" + "=" * 50)
    print("测试 Jinja2 导入...")
    print("=" * 50)

    try:
        import jinja2
        print(f"✓ Jinja2 版本: {jinja2.__version__}")
        print(f"✓ 安装路径: {jinja2.__file__}")
        return True
    except ImportError as e:
        print(f"✗ Jinja2 导入失败: {e}")
        print("  请运行: pip install jinja2")
        return False

def test_weekly_synthesis_service():
    """测试周报服务导入"""
    print("\n" + "=" * 50)
    print("测试 WeeklySynthesisService 导入...")
    print("=" * 50)

    # 切换到 backend 目录以正确导入 app 模块
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)

    # 添加 backend 目录到 Python 路径
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    try:
        from app.services.analytics.weekly_synthesis_service import HAS_WEASYPRINT, HAS_JINJA2

        if HAS_WEASYPRINT:
            print("✓ WeasyPrint 可用")
        else:
            print("⚠ WeasyPrint 不可用（容错模式）")

        if HAS_JINJA2:
            print("✓ Jinja2 可用")
        else:
            print("⚠ Jinja2 不可用（容错模式）")

        return HAS_WEASYPRINT and HAS_JINJA2
    except ImportError as e:
        print(f"✗ WeeklySynthesisService 导入失败: {e}")
        return False

def test_pdf_generation():
    """测试 PDF 生成功能"""
    print("\n" + "=" * 50)
    print("测试 PDF 生成...")
    print("=" * 50)

    try:
        import tempfile
        from weasyprint import HTML
        from jinja2 import Template

        # 创建简单的 HTML 模板
        template = Template('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>测试文档</title>
        </head>
        <body>
            <h1>WeasyPrint 测试</h1>
            <p>如果你看到这个 PDF，说明 WeasyPrint 工作正常！</p>
        </body>
        </html>
        ''')

        # 渲染 HTML
        html_content = template.render()

        # 创建临时 PDF 文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            pdf_path = f.name

        # 生成 PDF
        HTML(string=html_content).write_pdf(pdf_path)

        # 检查文件
        file_size = os.path.getsize(pdf_path)
        print(f"✓ PDF 生成成功: {pdf_path}")
        print(f"✓ 文件大小: {file_size} bytes")

        # 清理
        os.unlink(pdf_path)

        return True
    except Exception as e:
        print(f"✗ PDF 生成失败: {e}")
        return False

def check_environment():
    """检查环境变量"""
    print("\n" + "=" * 50)
    print("环境变量检查...")
    print("=" * 50)

    dyld_path = os.environ.get('DYLD_LIBRARY_PATH', '')
    if dyld_path:
        print(f"✓ DYLD_LIBRARY_PATH: {dyld_path}")
    else:
        print("⚠ DYLD_LIBRARY_PATH 未设置")
        print("  macOS 用户可能需要设置: export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH")

def main():
    """主测试函数"""
    print("\n" + "=" * 50)
    print("WeasyPrint 依赖测试")
    print("=" * 50)

    # 检查环境
    check_environment()

    # 运行测试
    results = {
        "WeasyPrint 导入": test_weasyprint_import(),
        "Jinja2 导入": test_jinja2_import(),
        "WeeklySynthesisService": test_weekly_synthesis_service(),
    }

    # 如果所有依赖都可用，测试 PDF 生成
    if all(results.values()):
        results["PDF 生成"] = test_pdf_generation()

    # 总结
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)

    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{test_name}: {status}")

    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 所有测试通过！WeasyPrint 配置正确。")
        return 0
    else:
        print("\n⚠ 部分测试失败，请参考 WEASYPRINT_SETUP.md 进行配置。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
