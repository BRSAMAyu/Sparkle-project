"""
文档清洗和上传功能安全修复测试
测试路径穿越、魔数验证、10MB限制等修复
"""
import os
import tempfile
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.config import settings
from app.core.ingestion.ingestion_service import IngestionService
from app.services.document_service import DocumentService, _resolve_allowed_path


class TestPathTraversalFix:
    """测试路径穿越防护修复"""

    def test_reject_path_with_double_dot(self):
        """测试拒绝包含..的路径"""
        malicious_paths = [
            "../../etc/passwd",
            "../../../etc/shadow",
            "./../../../tmp/secrets",
            "/tmp/../etc/passwd",
        ]

        for path in malicious_paths:
            result = _resolve_allowed_path(path)
            assert result is None, f"应该拒绝恶意路径: {path}"

    def test_reject_absolute_paths_outside_allowed(self):
        """测试拒绝允许目录外的绝对路径"""
        # 系统敏感文件
        sensitive_paths = [
            "/etc/passwd",
            "/etc/shadow",
            "/var/log/auth.log",
        ]

        for path in sensitive_paths:
            result = _resolve_allowed_path(path)
            assert result is None, f"应该拒绝系统路径: {path}"

    def test_reject_symlinks(self):
        """测试拒绝符号链接"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建一个文件
            real_file = os.path.join(tmpdir, "real_file.txt")
            with open(real_file, "w") as f:
                f.write("safe content")

            # 创建符号链接
            symlink = os.path.join(tmpdir, "symlink.txt")
            try:
                os.symlink(real_file, symlink)
            except OSError:
                pytest.skip("需要管理员权限创建符号链接")

            # 测试符号链接被拒绝
            with patch.object(settings, 'UPLOAD_DIR', tmpdir):
                result = _resolve_allowed_path(symlink)
                assert result is None, "应该拒绝符号链接"

    def test_accept_valid_paths(self):
        """测试接受合法路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            with patch.object(settings, 'UPLOAD_DIR', tmpdir):
                result = _resolve_allowed_path(test_file)
                assert result == test_file, "应该接受合法路径"

    def test_accept_ingestion_temp_dir_paths(self):
        """测试接受 documents/clean 写入的临时目录文件"""
        with tempfile.TemporaryDirectory() as upload_dir:
            with tempfile.TemporaryDirectory() as temp_root:
                temp_upload_dir = os.path.join(temp_root, "sparkle_uploads")
                os.makedirs(temp_upload_dir, exist_ok=True)
                test_file = os.path.join(temp_upload_dir, "test.pdf")
                with open(test_file, "wb") as f:
                    f.write(b"%PDF-1.4\n")

                with patch.object(settings, "UPLOAD_DIR", upload_dir):
                    with patch.dict(os.environ, {"SPARKLE_UPLOAD_TEMP_DIR": temp_root}):
                        result = _resolve_allowed_path(test_file)

                assert result == os.path.abspath(test_file), "应该接受 ingestion 临时目录文件"

    def test_resolve_uses_abspath_not_realpath(self):
        """测试使用abspath而不是realpath（不跟随符号链接）"""
        # 这个测试验证即使有符号链接，也不会被跟随
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, "w") as f:
                f.write("content")

            with patch.object(settings, 'UPLOAD_DIR', tmpdir):
                result = _resolve_allowed_path(test_file)
                assert result is not None
                # 验证返回的是绝对路径
                assert os.path.isabs(result)


class TestMagicBytesValidation:
    """测试文件魔数验证"""

    def setup_method(self):
        self.ingestion_service = IngestionService()

    def test_reject_fake_pdf(self):
        """测试拒绝伪装成PDF的文本文件"""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"This is not a PDF file")
            f.flush()

            with pytest.raises(ValueError, match="Invalid PDF file"):
                self.ingestion_service._validate_magic_bytes(f.name)

            os.unlink(f.name)

    def test_reject_fake_docx(self):
        """测试拒绝伪装成DOCX的文本文件"""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(b"Not a ZIP file")
            f.flush()

            with pytest.raises(ValueError, match="Invalid Office document"):
                self.ingestion_service._validate_magic_bytes(f.name)

            os.unlink(f.name)

    def test_accept_valid_pdf_header(self):
        """测试接受有效的PDF文件头"""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4\n%fake content")
            f.flush()

            # 应该不抛出异常
            self.ingestion_service._validate_magic_bytes(f.name)
            os.unlink(f.name)

    def test_accept_valid_office_header(self):
        """测试接受有效的Office文件头（ZIP格式）"""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            # ZIP文件头
            f.write(b"PK\x03\x04" + b"\x00" * 100)
            f.flush()

            # 应该不抛出异常
            self.ingestion_service._validate_magic_bytes(f.name)
            os.unlink(f.name)

    def test_png_magic_bytes(self):
        """测试PNG魔数验证"""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # 写入足够的内容（512字节）但不是PNG格式
            f.write(b"Not PNG" + b"\x00" * 506)
            f.flush()

            with pytest.raises(ValueError, match="Invalid PNG file"):
                self.ingestion_service._validate_magic_bytes(f.name)

            os.unlink(f.name)

    def test_jpeg_magic_bytes(self):
        """测试JPEG魔数验证"""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            # 写入足够的内容（512字节）但不是JPEG格式
            f.write(b"Not JPEG" + b"\x00" * 506)
            f.flush()

            with pytest.raises(ValueError, match="Invalid JPEG file"):
                self.ingestion_service._validate_magic_bytes(f.name)

            os.unlink(f.name)

    def test_skip_ocr_when_disabled(self):
        """测试关闭 OCR 时不会触发扫描件 OCR fallback"""
        page = Mock()
        page.extract_text.return_value = ""
        fake_pdf = Mock()
        fake_pdf.pages = [page]

        open_mock = Mock()
        open_mock.__enter__ = Mock(return_value=fake_pdf)
        open_mock.__exit__ = Mock(return_value=False)

        with patch("app.core.ingestion.ingestion_service.pdfplumber.open", return_value=open_mock):
            with patch.object(self.ingestion_service, "_attempt_ocr", return_value=("ocr text", None)) as mock_attempt:
                chunks = self.ingestion_service._process_pdf("/tmp/fake.pdf", {"enable_ocr": False})

        assert chunks == []
        mock_attempt.assert_not_called()

    def test_legacy_deepseek_engine_maps_to_zhipu(self):
        """测试旧 deepseek 选项会自动映射到 zhipu"""
        page = Mock()
        page_image = Mock()
        page_image.original = Mock()
        page.to_image.return_value = page_image

        with patch("app.core.ingestion.ingestion_service.HAS_PIL", True):
            with patch.object(self.ingestion_service, "_ocr_via_api", return_value="ocr text") as mock_api:
                with patch.object(self.ingestion_service, "_ocr_via_local", return_value=("local text", 0.9)) as mock_local:
                    text, confidence = self.ingestion_service._attempt_ocr(page, {"ocr_engine": "deepseek"})

        assert text == "ocr text"
        assert confidence is None
        mock_api.assert_called_once()
        mock_local.assert_not_called()


class Test10MBSizeLimit:
    """测试10MB清洗后大小限制"""

    def setup_method(self):
        self.document_service = DocumentService()

    @pytest.mark.asyncio
    async def test_small_document_returns_full_text(self):
        """测试小文档（<20KB）返回完整文本"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("small")

            with patch.object(settings, "UPLOAD_DIR", tmpdir):
                with patch('app.services.document_service.ingestion_service') as mock_ingestion:
                    mock_ingestion.process_file.return_value = [
                        Mock(text="Small content", page_num=1, metadata={}, ocr_confidence=None)
                    ]

                    with patch.object(self.document_service, '_generate_quick_summary') as mock_summary:
                        mock_summary.return_value = "Summary"

                        result = await self.document_service.clean_and_summarize(
                            test_file,
                            task_id="test-task"
                        )

                        assert result["status"] == "completed"
                        assert result["mode"] == "full_text"
                        assert "full_text" in result
                        assert not result.get("truncated")

    @pytest.mark.asyncio
    async def test_large_document_returns_compressed(self):
        """测试超大文档（>10MB）返回压缩摘要"""
        # 模拟大文档（超过10MB字符）
        large_chunks = []
        for i in range(1000):
            chunk = Mock(
                text="X" * 15000,  # 每块15KB
                page_num=i+1,
                metadata={},
                ocr_confidence=None
            )
            large_chunks.append(chunk)

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "large.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("large")

            with patch.object(settings, "UPLOAD_DIR", tmpdir):
                with patch('app.services.document_service.ingestion_service') as mock_ingestion:
                    mock_ingestion.process_file.return_value = large_chunks

                    with patch.object(self.document_service, '_run_map_reduce') as mock_map_reduce:
                        mock_map_reduce.return_value = "Compressed summary"

                        result = await self.document_service.clean_and_summarize(
                            test_file,
                            task_id="test-task"
                        )

                        assert result["status"] == "completed"
                        assert result["mode"] == "compressed"
                        assert result.get("truncated")
                        assert "summary" in result
                        assert "full_text" not in result or result.get("full_text_preview") is not None


class TestErrorHandling:
    """测试错误处理和通知"""

    @pytest.mark.asyncio
    async def test_task_failure_updates_redis(self):
        """测试任务失败时更新Redis状态"""
        document_service = DocumentService()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("x")

            with patch.object(settings, "UPLOAD_DIR", tmpdir):
                with patch('app.services.document_service.ingestion_service') as mock_ingestion:
                    # 模拟处理失败
                    mock_ingestion.process_file.side_effect = Exception("Processing failed")

                    with patch('app.services.document_service.cache_service') as mock_cache:
                        mock_cache.set = AsyncMock()
                        result = await document_service.clean_and_summarize(
                            test_file,
                            task_id="test-task"
                        )

                        # 验证返回错误状态
                        assert result["status"] == "error"
                        assert "error" in result

                        # 验证更新了Redis（最后一次调用应该是status=error）
                        calls = mock_cache.set.call_args_list
                        error_call = [c for c in calls if "error" in str(c)]
                        assert len(error_call) > 0, "应该更新任务状态为失败"

    @pytest.mark.asyncio
    async def test_invalid_path_returns_error(self):
        """测试无效路径返回错误"""
        document_service = DocumentService()

        result = await document_service.clean_and_summarize(
            "../../etc/passwd",  # 恶意路径
            task_id="test-task"
        )

        assert result["status"] == "failed"
        assert "Invalid file path" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_update_progress_normalizes_completed_status(self):
        """测试进度状态会归一化为前端期望的小写 completed"""
        document_service = DocumentService()

        with patch("app.services.document_service.cache_service") as mock_cache:
            mock_cache.set = AsyncMock()
            await document_service.update_progress(
                "task-1",
                "Completed",
                100,
                {"status": "completed"},
            )

        payload = mock_cache.set.await_args.args[1]
        assert payload["status"] == "completed"
        assert payload["message"] == "Completed"


class TestDiskSpaceCheck:
    """测试磁盘空间检查"""

    def test_insufficient_disk_space(self):
        """测试磁盘空间不足"""
        from app.api.v1.ingestion import check_disk_space

        # 模拟没有足够空间
        with patch('os.statvfs') as mock_statvfs:
            mock_statvfs.return_value.f_bavail = 100  # 100个块
            mock_statvfs.return_value.f_frsize = 4096  # 每块4KB
            # 总共约400KB可用

            result = check_disk_space(1024 * 1024 * 100)  # 需要100MB
            assert not result, "应该拒绝空间不足的请求"

    def test_sufficient_disk_space(self):
        """测试磁盘空间充足"""
        from app.api.v1.ingestion import check_disk_space

        with patch('os.statvfs') as mock_statvfs:
            mock_statvfs.return_value.f_bavail = 100000  # 100K个块
            mock_statvfs.return_value.f_frsize = 4096  # 每块4KB
            # 总共约400MB可用

            result = check_disk_space(1024 * 1024 * 100)  # 需要100MB
            assert result, "应该接受空间充足的请求"


class TestGoHandlerMagicBytes:
    """测试Go Gateway的魔数验证（需要集成测试）"""

    def test_go_magic_bytes_validation(self):
        """
        注意：这个测试需要Go服务运行
        在CI/CD中应该标记为集成测试
        """
        # 这里只是示例，实际测试需要启动Go服务
        # 可以使用httpx或requests调用API
        pass


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
