"""
MDX/MDD 词典查询服务
MDX/MDD Dictionary Query Service

依赖: pip install readmdict python-lzo beautifulsoup4 lxml
"""
import html
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
    from readmdict import MDD, MDX
    MDX_AVAILABLE = True
except ImportError:
    MDX_AVAILABLE = False
    MDX = None
    MDD = None
    BeautifulSoup = None
    logger.warning("readmdict or beautifulsoup4 not available. MDX dictionary service disabled.")


class MDXDictionaryService:
    """
    MDX/MDD 词典查询服务

    支持查询常见的 MDX 格式词典文件，如牛津、朗文等。
    使用 readmdict 库读取词典数据。
    """

    def __init__(self, mdx_path: str, mdd_path: str | None = None):
        """
        初始化 MDX 词典服务

        Args:
            mdx_path: MDX 词典文件路径
            mdd_path: MDD 资源文件路径（可选，用于音频、图片等）
        """
        if not MDX_AVAILABLE:
            raise RuntimeError("readmdict or beautifulsoup4 not installed")

        self.mdx_path = Path(mdx_path)
        self.mdd_path = Path(mdd_path) if mdd_path else None

        if not self.mdx_path.exists():
            raise FileNotFoundError(f"MDX file not found: {mdx_path}")

        try:
            self.mdx = MDX(str(self.mdx_path))
            self._dictionary_name = self.mdx_path.stem
            self._items_cache = None  # 延迟加载
            logger.info(f"MDX dictionary loaded: {self._dictionary_name} ({len(self.mdx)} entries)")
        except Exception as e:
            logger.error(f"Failed to load MDX dictionary: {e}")
            raise

    def _get_items(self):
        """获取词典条目（延迟加载并缓存）"""
        if self._items_cache is None:
            self._items_cache = {k.lower(): v for k, v in self.mdx.items()}
        return self._items_cache

    def lookup(self, word: str) -> dict[str, Any] | None:
        """
        查询单词

        Args:
            word: 要查询的单词

        Returns:
            包含单词信息的字典，如果未找到则返回 None
        """
        if not MDX_AVAILABLE:
            return None

        word_lower = word.lower().strip()
        if not word_lower:
            return None

        try:
            items = self._get_items()
            # key 可能是 bytes，需要转换
            for key, value in items.items():
                key_str = key.decode('utf-8', errors='ignore').lower() if isinstance(key, bytes) else str(key).lower()
                if key_str == word_lower:
                    return self._parse_result(value, word)
            return None
        except Exception as e:
            logger.error(f"MDX lookup error for '{word}': {e}")
            return None

    def _parse_result(self, raw: Any, word: str) -> dict[str, Any]:
        """
        解析 MDX 原始结果

        Args:
            raw: MDX 查询返回的原始 HTML (bytes 或 list)
            word: 查询的单词

        Returns:
            解析后的字典数据
        """
        # raw 可能是 bytes 或 list
        content_bytes = raw[0] if isinstance(raw, list) else raw

        if isinstance(content_bytes, bytes):
            html_content = content_bytes.decode('utf-8', errors='ignore')
        else:
            html_content = str(content_bytes)

        if not BeautifulSoup:
            # 如果没有 BeautifulSoup，返回简单解析
            return {
                "word": word,
                "phonetic": None,
                "pos": None,
                "definitions": [html.unescape(html_content)[:500]],
                "examples": [],
                "source": self._dictionary_name
            }

        soup = BeautifulSoup(html_content, 'html.parser')

        return {
            "word": word,
            "phonetic": self._extract_phonetic(soup),
            "pos": self._extract_pos(soup),
            "definitions": self._extract_definitions(soup),
            "examples": self._extract_examples(soup),
            "source": self._dictionary_name
        }

    def _extract_phonetic(self, soup) -> str | None:
        """提取音标"""
        if not soup:
            return None

        # 常见的音标类名（牛津词典特定）
        phonetic_selectors = [
            '.phon', '.phonetic', '.pr', '.pron', '.ipa',
            '.pronounce', 'span.pos-g', 'span.orth'
        ]

        for selector in phonetic_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text().strip()
                # 清理方括号和其他符号，只保留音标部分
                text = text.strip('[]ˈˌ()/\\ ')
                if text and len(text) < 50:  # 合理的音标长度
                    return text

        # 查找包含音标格式的文本
        full_text = soup.get_text()
        import re
        # 匹配 /.../ 或 [...] 格式的音标
        patterns = [r'/([^/]{3,30})/', r'\[([^\]]{3,30})\]']
        for pattern in patterns:
            match = re.search(pattern, full_text[:500])  # 只在前500字符中搜索
            if match:
                return match.group(1).strip()

        return None

    def _extract_pos(self, soup) -> str | None:
        """提取词性"""
        if not soup:
            return None

        # 常见的词性类名
        pos_selectors = [
            '.pos', '.gram', '.fl', '.posg',
            'span.part-of-speech', '.webtop'
        ]

        for selector in pos_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text().strip()
                # 限制词性长度
                if text and len(text) < 30:
                    # 清理常见的词性标记
                    text = text.split('\n')[0].strip()
                    if any(pos in text.lower() for pos in ['noun', 'verb', 'adj', 'adv', 'prep', 'conj', 'exclamation', 'pron']):
                        return text[:20]

        return None

    def _extract_definitions(self, soup) -> list[str]:
        """提取释义"""
        if not soup:
            return []

        definitions = []

        # 牛津词典特定的选择器
        def_selectors = [
            '.sn-g', '.sense', '.def', '.definition',
            '.shcut-g', '.entry'
        ]

        for selector in def_selectors:
            elements = soup.select(selector)
            for element in elements:
                # 获取释义文本
                text = element.get_text().strip()
                # 清理文本
                text = ' '.join(text.split())
                if text and 10 < len(text) < 500:
                    definitions.append(text[:300])
                    if len(definitions) >= 5:
                        break
            if definitions:
                break

        # 如果没找到特定的释义元素，使用整个内容
        if not definitions:
            # 移除 script 和 style 标签
            for script in soup(['script', 'style']):
                script.decompose()
            text = soup.get_text().strip()
            text = ' '.join(text.split())
            if text:
                definitions = [text[:500]]

        return definitions[:5] if definitions else ["No definition found"]

    def _extract_examples(self, soup) -> list[str]:
        """提取例句"""
        if not soup:
            return []

        examples = []

        # 常见的例句类名
        ex_selectors = [
            '.x-g', '.example', '.exg', '.eg', '.ex',
            '.sentence', '.example-sent', '.xh'
        ]

        for selector in ex_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text().strip()
                text = ' '.join(text.split())
                if text and 10 < len(text) < 300:
                    examples.append(text)
                    if len(examples) >= 3:
                        break
            if examples:
                break

        return examples


def create_mdx_service(
    mdx_path: str | None = None,
    mdd_path: str | None = None
) -> MDXDictionaryService | None:
    """
    创建 MDX 词典服务实例

    Args:
        mdx_path: MDX 词典文件路径
        mdd_path: MDD 资源文件路径

    Returns:
        MDXDictionaryService 实例，如果初始化失败则返回 None
    """
    if not MDX_AVAILABLE or not mdx_path:
        return None

    try:
        return MDXDictionaryService(mdx_path, mdd_path)
    except Exception as e:
        logger.warning(f"Failed to create MDX service: {e}")
        return None
