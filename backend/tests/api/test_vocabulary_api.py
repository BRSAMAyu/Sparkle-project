"""
词汇 API 测试
Vocabulary API Tests
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


@pytest.fixture
def vocab_client(client):
    """获取测试客户端"""
    return client


@pytest.fixture
def mock_user():
    """模拟用户"""
    return {
        "id": str(uuid4()),
        "email": "test@example.com",
    }


@pytest.fixture
def auth_headers(mock_user):
    """获取认证头"""
    return {"Authorization": f"Bearer {mock_user['id']}"}


class TestVocabularyAPI:
    """词汇 API 测试"""

    def test_lookup_word_local_db(self, vocab_client, auth_headers):
        """测试查词（本地数据库）"""
        word = "hello"

        with patch('app.api.v1.vocabulary.vocabulary_service') as mock_service:
            mock_entry = AsyncMock()
            mock_entry.word = word
            mock_entry.phonetic = "/həˈloʊ/"
            mock_entry.pos = "interjection"
            mock_entry.definitions = ["Used as a greeting"]
            mock_entry.examples = ["Hello, world!"]
            mock_entry.source = "test"

            mock_service.lookup = AsyncMock(return_value=mock_entry)

            response = vocab_client.get(
                "/vocabulary/lookup",
                params={"word": word},
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["word"] == word
            assert data["phonetic"] == "/həˈloʊ/"
            assert data["source"] == "test"

    def test_lookup_word_not_found(self, vocab_client, auth_headers):
        """测试查词（未找到）"""
        word = "nonexistentword12345"

        with patch('app.api.v1.vocabulary.vocabulary_service') as mock_service, \
             patch('app.api.v1.vocabulary.get_mdx_service') as mock_mdx:
            mock_service.lookup = AsyncMock(return_value=None)
            mock_mdx.return_value = None

            response = vocab_client.get(
                "/vocabulary/lookup",
                params={"word": word},
                headers=auth_headers
            )

            assert response.status_code == 404

    def test_add_to_wordbook(self, vocab_client, auth_headers, mock_user):
        """测试添加生词到生词本"""
        word_data = {
            "word": "test",
            "definition": "A procedure for evaluation",
            "importance": 4,
            "part_of_speech": "noun",
        }

        with patch('app.api.v1.vocabulary.vocabulary_service') as mock_service, \
             patch('app.api.v1.vocabulary.get_current_user', return_value=mock_user):
            mock_word = AsyncMock()
            mock_word.id = uuid4()
            mock_word.word = "test"
            mock_word.phonetic = "/test/"
            mock_word.definition = "A procedure for evaluation"
            mock_word.importance = 4
            mock_word.consecutive_correct = 0
            mock_word.correct_review_count = 0
            mock_word.review_count = 0
            mock_word.next_review_at = "2024-01-01T00:00:00"
            mock_word.last_review_at = None
            mock_word.part_of_speech = "noun"
            mock_word.source_translation_id = None
            mock_word.context_sentence = None

            mock_service.add_to_wordbook = AsyncMock(return_value=mock_word)

            response = vocab_client.post(
                "/vocabulary/wordbook",
                json=word_data,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["word"] == "test"
            assert data["importance"] == 4
            assert data["part_of_speech"] == "noun"

    def test_add_to_wordbook_invalid_importance(self, vocab_client, auth_headers):
        """测试添加生词（无效的重要度）"""
        word_data = {
            "word": "test",
            "definition": "A procedure for evaluation",
            "importance": 6,  # 无效：超过 5
        }

        response = vocab_client.post(
            "/vocabulary/wordbook",
            json=word_data,
            headers=auth_headers
        )

        assert response.status_code == 422  # Validation error

    def test_update_importance(self, vocab_client, auth_headers, mock_user):
        """测试更新重要度"""
        word_id = str(uuid4())
        update_data = {"importance": 5}

        with patch('app.api.v1.vocabulary.vocabulary_service') as mock_service, \
             patch('app.api.v1.vocabulary.get_current_user', return_value=mock_user):
            mock_word = AsyncMock()
            mock_word.id = uuid4()
            mock_word.word = "test"
            mock_word.phonetic = "/test/"
            mock_word.definition = "A procedure"
            mock_word.importance = 5
            mock_word.consecutive_correct = 2
            mock_word.correct_review_count = 5
            mock_word.review_count = 7
            mock_word.next_review_at = "2024-01-01T00:00:00"
            mock_word.last_review_at = "2024-01-01T00:00:00"
            mock_word.part_of_speech = None
            mock_word.source_translation_id = None
            mock_word.context_sentence = None

            mock_service.update_importance = AsyncMock(return_value=mock_word)

            response = vocab_client.patch(
                f"/vocabulary/wordbook/{word_id}/importance",
                json=update_data,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["importance"] == 5

    def test_get_review_list(self, vocab_client, auth_headers, mock_user):
        """测试获取复习列表"""
        with patch('app.api.v1.vocabulary.vocabulary_service') as mock_service, \
             patch('app.api.v1.vocabulary.get_current_user', return_value=mock_user):
            mock_word = AsyncMock()
            mock_word.id = uuid4()
            mock_word.word = "test"
            mock_word.phonetic = "/test/"
            mock_word.definition = "A procedure"
            mock_word.importance = 3
            mock_word.consecutive_correct = 1
            mock_word.correct_review_count = 3
            mock_word.review_count = 5
            mock_word.next_review_at = "2024-01-01T00:00:00"
            mock_word.last_review_at = "2024-01-01T00:00:00"
            mock_word.part_of_speech = None
            mock_word.source_translation_id = None
            mock_word.context_sentence = None

            mock_service.get_review_list = AsyncMock(return_value=[mock_word])

            response = vocab_client.get(
                "/vocabulary/wordbook/review",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) >= 0

    def test_get_stats(self, vocab_client, auth_headers, mock_user):
        """测试获取统计"""
        with patch('app.api.v1.vocabulary.vocabulary_service') as mock_service, \
             patch('app.api.v1.vocabulary.get_current_user', return_value=mock_user):
            mock_service.get_statistics = AsyncMock(return_value={
                "total_words": 100,
                "due_for_review": 15,
                "accuracy_rate": 0.75,
                "by_importance": {
                    "1": 10, "2": 20, "3": 30, "4": 25, "5": 15
                }
            })

            response = vocab_client.get(
                "/vocabulary/wordbook/stats",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_words"] == 100
            assert data["due_for_review"] == 15
            assert data["accuracy_rate"] == 0.75

    def test_record_review(self, vocab_client, auth_headers, mock_user):
        """测试记录复习结果"""
        word_id = str(uuid4())
        review_data = {
            "word_id": word_id,
            "remembered": True
        }

        with patch('app.api.v1.vocabulary.vocabulary_service') as mock_service, \
             patch('app.api.v1.vocabulary.get_current_user', return_value=mock_user):
            mock_word = AsyncMock()
            mock_word.id = uuid4()
            mock_word.word = "test"
            mock_word.phonetic = "/test/"
            mock_word.definition = "A procedure"
            mock_word.importance = 3
            mock_word.consecutive_correct = 3
            mock_word.correct_review_count = 6
            mock_word.review_count = 8
            mock_word.next_review_at = "2024-01-01T00:00:00"
            mock_word.last_review_at = "2024-01-01T00:00:00"
            mock_word.part_of_speech = None
            mock_word.source_translation_id = None
            mock_word.context_sentence = None

            mock_service.record_review = AsyncMock(return_value=mock_word)

            response = vocab_client.post(
                "/vocabulary/wordbook/review",
                json=review_data,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["consecutive_correct"] == 3
