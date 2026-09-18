"""
Guest Seed Empty-Shell Content Fix — unit tests

多端实测发现官方种子库 10 条中 4 条 content 为空（空壳卡片）：
数学示例×3 + Python 列表推导式闪卡，均为"只定义 content_data、无 content"的条目。
本测试覆盖：
1. derive_item_content：从 content_data 推导可读正文
2. initialize_seed_libraries：播种时回填 content、纯空壳条目拒绝落库
3. repair_empty_seed_item_content：存量空壳启动修复（幂等）
4. SeedLibraryService.add_item：增量空壳防护（推导回填 / 双空拒绝）
5. SeedLibraryService.get_item / get_items：惰性补偿（访问时回填）
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.seed_content_initial import (
    OFFICIAL_LIBRARIES,
    _ensure_item_content,
    derive_item_content,
    initialize_seed_libraries,
    repair_empty_seed_item_content,
)
from app.models.seed_content import ItemType, SeedItem
from app.schemas.seed_content import ItemCreate, ItemListParams
from app.services.seed_library_service import SeedLibraryService

# ============ 1. derive_item_content ============


class TestDeriveItemContent:
    def test_example_derives_input_and_output(self):
        content = derive_item_content(
            ItemType.EXAMPLE,
            {"input": "求解 x²-5x+6=0", "output": "x₁=2, x₂=3", "explanation": "因式分解"},
        )
        assert content is not None
        assert "求解 x²-5x+6=0" in content
        assert "x₁=2, x₂=3" in content

    def test_flashcard_derives_front_and_back(self):
        content = derive_item_content(
            ItemType.FLASHCARD,
            {"front": "如何平方？", "back": "[x**2 for x in numbers]"},
        )
        assert content is not None
        assert "如何平方？" in content
        assert "[x**2 for x in numbers]" in content

    def test_exercise_prefers_solution(self):
        content = derive_item_content(
            ItemType.EXERCISE,
            {"solution": "sum(numbers)", "explanation": "用 sum()"},
        )
        assert content is not None
        assert "sum(numbers)" in content

    def test_knowledge_derives_definition_and_points(self):
        content = derive_item_content(
            ItemType.KNOWLEDGE,
            {"definition": "字典是键值映射", "key_points": ["keys()", "values()"]},
        )
        assert content is not None
        assert "字典是键值映射" in content
        assert "- keys()" in content

    def test_generic_fallback_joins_string_values(self):
        content = derive_item_content(ItemType.TEMPLATE, {"body": "模板正文", "note": 123})
        assert content is not None
        assert "模板正文" in content
        assert "123" not in content

    def test_non_dict_content_data_returns_none(self):
        assert derive_item_content(ItemType.EXAMPLE, None) is None
        assert derive_item_content(ItemType.EXAMPLE, "text") is None

    def test_blank_values_are_ignored(self):
        assert derive_item_content(ItemType.FLASHCARD, {"front": "  ", "back": None}) is None

    def test_item_type_accepts_string_value(self):
        content = derive_item_content("example", {"input": "q", "output": "a"})
        assert content is not None


# ============ 2. 官方种子数据 + initialize_seed_libraries ============


class TestOfficialSeedDataIntegrity:
    def test_all_10_official_items_normalize_to_non_empty_content(self):
        """实测缺陷回归：官方库 10 条（含 4 条仅 content_data 的空壳）规范化后 content 全部非空。"""
        total = 0
        for lib in OFFICIAL_LIBRARIES:
            for item in lib["items"]:
                normalized = _ensure_item_content(dict(item))
                assert normalized is not None, f"item '{item.get('title')}' must not be an empty shell"
                assert normalized["content"] and normalized["content"].strip()
                total += 1
        assert total == 10

    def test_known_blank_entries_get_derived_content(self):
        """当初 content 为空的 4 条：数学示例×3 + 列表推导式闪卡，回填后含实质内容。"""
        known_blank_titles = {
            "一元二次方程求解示例",
            "几何证明示例 - 三角形内角和",
            "函数图像分析示例",
            "Python 列表推导式闪卡",
        }
        matched = 0
        for lib in OFFICIAL_LIBRARIES:
            for item in lib["items"]:
                if item["title"] not in known_blank_titles:
                    continue
                matched += 1
                assert "content" not in item  # 原始数据确无 content（缺陷本体）
                normalized = _ensure_item_content(dict(item))
                content = normalized["content"]
                assert len(content) >= 50  # 推导出的正文有实质内容
        assert matched == 4


def _official_lib_item(title: str, *, with_content: bool, content_data: dict | None) -> dict:
    item: dict = {
        "item_type": ItemType.EXAMPLE,
        "title": title,
        "order_index": 1,
    }
    if with_content:
        item["content"] = "已有正文"
    if content_data is not None:
        item["content_data"] = content_data
    return item


class TestInitializeSeedLibraries:
    def _mock_db(self) -> AsyncMock:
        db = AsyncMock()
        db.add = MagicMock()  # add 为同步调用
        first_result = MagicMock()
        first_result.scalars.return_value.first.return_value = None  # 未初始化
        db.execute.return_value = first_result
        return db

    def _insert_statements(self, db: AsyncMock) -> list:
        return [call.args[0] for call in db.execute.call_args_list if call.args and "INSERT" in str(call.args[0])]

    async def test_real_official_data_seeds_10_items_with_derived_content(self):
        db = self._mock_db()

        created = await initialize_seed_libraries(db)

        assert created == 10
        inserts = self._insert_statements(db)
        assert len(inserts) == 10
        for stmt in inserts:
            params = stmt.compile().params
            assert params["content"] and str(params["content"]).strip()

    async def test_pure_empty_shell_item_is_skipped(self):
        """content 与 content_data 双空的条目拒绝落库（空壳不播种）。"""
        lib_data = {
            "name": "测试库",
            "description": "d",
            "category": "few_shot",
            "visibility": "official",
            "language": "zh",
            "is_official": True,
            "items": [
                _official_lib_item("好条目", with_content=True, content_data=None),
                _official_lib_item("空壳条目", with_content=False, content_data=None),
            ],
        }
        db = self._mock_db()

        with patch("app.data.seed_content_initial.OFFICIAL_LIBRARIES", [lib_data]):
            created = await initialize_seed_libraries(db)

        assert created == 1
        assert len(self._insert_statements(db)) == 1


# ============ 3. repair_empty_seed_item_content（存量补偿） ============


class TestRepairEmptySeedItemContent:
    def _make_item(self, content=None, content_data=None, item_type=ItemType.FLASHCARD):
        item = MagicMock(spec=SeedItem)
        item.id = uuid.uuid4()
        item.content = content
        item.content_data = content_data
        item.item_type = item_type
        return item

    def _mock_db(self, items: list) -> AsyncMock:
        db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = items
        db.execute.return_value = result
        return db

    async def test_repairs_blank_content_items(self):
        items = [
            self._make_item(content=None, content_data={"front": "F", "back": "B"}),
            self._make_item(content="  ", content_data={"input": "q", "output": "a"}, item_type=ItemType.EXAMPLE),
        ]
        db = self._mock_db(items)

        repaired = await repair_empty_seed_item_content(db)

        assert repaired == 2
        assert "F" in items[0].content
        assert "q" in items[1].content
        db.flush.assert_awaited_once()

    async def test_undecorable_items_are_not_repaired(self):
        items = [self._make_item(content=None, content_data={"n": 123})]
        db = self._mock_db(items)

        repaired = await repair_empty_seed_item_content(db)

        assert repaired == 0
        assert items[0].content is None
        db.flush.assert_not_awaited()

    async def test_idempotent_when_no_blank_items(self):
        db = self._mock_db([])

        assert await repair_empty_seed_item_content(db) == 0


# ============ 4. SeedLibraryService.add_item 增量防护 ============


class TestAddItemEmptyShellGuard:
    def setup_method(self):
        self.service = SeedLibraryService()
        self.db = AsyncMock()
        self.library = MagicMock()
        self.owner_id = uuid.uuid4()
        self.library.owner_id = self.owner_id
        self.db.add = MagicMock()
        self.db.flush = AsyncMock()
        self.db.refresh = AsyncMock()

    def _item_data(self, **kwargs) -> ItemCreate:
        return ItemCreate(item_type=ItemType.FLASHCARD, title="t", **kwargs)

    async def test_blank_content_derived_from_content_data(self):
        with (
            patch.object(self.service, "get_library", new_callable=AsyncMock, return_value=self.library),
            patch("app.services.seed_library_service._SEED_VECTOR_RUNTIME_ENABLED", False),
        ):
            item = await self.service.add_item(
                self.db,
                uuid.uuid4(),
                self._item_data(content=None, content_data={"front": "F", "back": "B"}),
                self.owner_id,
            )

        assert item is not None
        assert "F" in item.content and "B" in item.content

    async def test_whitespace_only_content_is_derived(self):
        with (
            patch.object(self.service, "get_library", new_callable=AsyncMock, return_value=self.library),
            patch("app.services.seed_library_service._SEED_VECTOR_RUNTIME_ENABLED", False),
        ):
            item = await self.service.add_item(
                self.db,
                uuid.uuid4(),
                self._item_data(content="   ", content_data={"front": "F", "back": "B"}),
                self.owner_id,
            )

        assert item.content == "F\n\nB"

    async def test_double_empty_item_rejected(self):
        with patch.object(self.service, "get_library", new_callable=AsyncMock, return_value=self.library):
            with pytest.raises(ValueError, match="empty shell"):
                await self.service.add_item(
                    self.db,
                    uuid.uuid4(),
                    self._item_data(content=None, content_data=None),
                    self.owner_id,
                )
        self.db.add.assert_not_called()


# ============ 5. SeedLibraryService.get_item / get_items 惰性补偿 ============


class TestLazyHeal:
    def setup_method(self):
        self.service = SeedLibraryService()
        self.db = AsyncMock()

    def _shell_item(self) -> MagicMock:
        item = MagicMock(spec=SeedItem)
        item.id = uuid.uuid4()
        item.content = None
        item.content_data = {"front": "F", "back": "B"}
        item.item_type = "flashcard"
        return item

    async def test_get_item_blank_content_healed_and_persisted(self):
        item = self._shell_item()
        result = MagicMock()
        result.scalar_one_or_none.return_value = item
        self.db.execute.return_value = result

        loaded = await self.service.get_item(self.db, item.id)

        assert loaded is item
        assert "F" in loaded.content
        assert self.db.execute.await_count == 2  # select + 补偿写

    async def test_get_item_heal_failure_does_not_break_read(self):
        item = self._shell_item()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = item
        state = {"calls": 0}

        async def execute_side_effect(*_args, **_kwargs):
            state["calls"] += 1
            if state["calls"] == 1:
                return select_result
            raise RuntimeError("db write failed")

        self.db.execute = AsyncMock(side_effect=execute_side_effect)

        loaded = await self.service.get_item(self.db, item.id)

        assert loaded is item
        assert "F" in loaded.content  # 内存中已回填，落库失败不影响读取

    async def test_get_item_undecorable_left_untouched(self):
        item = self._shell_item()
        item.content_data = {"n": 123}
        result = MagicMock()
        result.scalar_one_or_none.return_value = item
        self.db.execute.return_value = result

        loaded = await self.service.get_item(self.db, item.id)

        assert loaded.content is None
        assert self.db.execute.await_count == 1  # 仅 select，无补偿写

    async def test_get_items_in_memory_backfill_without_write(self):
        shell = self._shell_item()
        total_result = MagicMock()
        total_result.scalar.return_value = 1
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [shell]
        self.db.execute = AsyncMock(side_effect=[total_result, items_result])

        items, total = await self.service.get_items(self.db, ItemListParams(library_id=uuid.uuid4()), user_id=None)

        assert total == 1
        assert len(items) == 1
        assert "F" in items[0].content  # 展示兜底
        assert self.db.execute.await_count == 2  # 仅原有两条查询，无落库写
