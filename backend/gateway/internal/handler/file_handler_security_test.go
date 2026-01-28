package handler

import (
	"bytes"
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestValidateFileByMagicBytes 测试魔数验证函数
func TestValidateFileByMagicBytes(t *testing.T) {
	tests := []struct {
		name      string
		ext       string
		content   []byte
		wantValid bool
		wantErr   string
	}{
		{
			name:      "有效的PDF文件",
			ext:       ".pdf",
			content:   []byte("%PDF-1.4\n%%EOF"),
			wantValid: true,
		},
		{
			name:      "无效的PDF文件（伪装）",
			ext:       ".pdf",
			content:   []byte("This is not a PDF"),
			wantValid: false,
			wantErr:   "Invalid PDF file",
		},
		{
			name:      "有效的DOCX文件",
			ext:       ".docx",
			content:   append([]byte("PK\x03\x04"), make([]byte, 100)...),
			wantValid: true,
		},
		{
			name:      "无效的DOCX文件",
			ext:       ".docx",
			content:   []byte("Not a ZIP file"),
			wantValid: false,
			wantErr:   "Invalid Office document",
		},
		{
			name:      "有效的PNG文件",
			ext:       ".png",
			content:   append([]byte("\x89PNG\r\n\x1a\n"), make([]byte, 100)...),
			wantValid: true,
		},
		{
			name:      "无效的PNG文件",
			ext:       ".png",
			content:   []byte("Not PNG"),
			wantValid: false,
			wantErr:   "Invalid PNG file",
		},
		{
			name:      "有效的JPEG文件",
			ext:       ".jpg",
			content:   append([]byte("\xFF\xD8\xFF"), make([]byte, 100)...),
			wantValid: true,
		},
		{
			name:      "无效的JPEG文件",
			ext:       ".jpg",
			content:   []byte("Not JPEG"),
			wantValid: false,
			wantErr:   "Invalid JPEG file",
		},
		{
			name:      "有效的GIF文件",
			ext:       ".gif",
			content:   append([]byte("GIF89a"), make([]byte, 100)...),
			wantValid: true,
		},
		{
			name:      "无效的GIF文件",
			ext:       ".gif",
			content:   []byte("Not GIF"),
			wantValid: false,
			wantErr:   "Invalid GIF file",
		},
		{
			name:      "有效的WebP文件",
			ext:       ".webp",
			content:   []byte("RIFF\x00\x00\x00\x00WEBP"),
			wantValid: true,
		},
		{
			name:      "无效的WebP文件",
			ext:       ".webp",
			content:   []byte("Not WebP"),
			wantValid: false,
			wantErr:   "Invalid WebP file",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			valid, errMsg := validateFileByMagicBytes(bytes.NewReader(tt.content), tt.ext)

			if tt.wantValid {
				assert.True(t, valid, "文件应该有效")
				assert.Empty(t, errMsg, "不应该有错误信息")
			} else {
				assert.False(t, valid, "文件应该无效")
				assert.Contains(t, errMsg, tt.wantErr, "错误信息应该匹配")
			}
		})
	}
}

// TestSanitizeFilename 测试文件名清理
func TestSanitizeFilename(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "正常文件名",
			input:    "document.pdf",
			expected: "document.pdf",
		},
		{
			name:     "带路径的文件名",
			input:    "../../etc/passwd",
			expected: "passwd",
		},
		{
			name:     "带空格的文件名",
			input:    "  document.pdf  ",
			expected: "document.pdf",
		},
		{
			name:     "只有路径",
			input:    "../../",
			expected: "..",  // path.Base("../../")返回".."
		},
		{
			name:     "空字符串",
			input:    "",
			expected: "file",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := sanitizeFilename(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

// BenchmarkValidateFileByMagicBytes 性能测试
func BenchmarkValidateFileByMagicBytes(b *testing.B) {
	content := make([]byte, 512)
	copy(content, "%PDF-1.4\n")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		validateFileByMagicBytes(bytes.NewReader(content), ".pdf")
	}
}
