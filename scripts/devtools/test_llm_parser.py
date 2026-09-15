import pytest
from unittest.mock import Mock, patch
from app.services.llm.parser import LLMResponseParser
from app.schemas.llm import LLMResponse

class TestLLMResponseParser:
    @pytest.fixture
    def parser(self):
        return LLMResponseParser()

    def test_parse_valid_json(self, parser):
        """Level 1: Test direct JSON parsing"""
        raw_response = '{"assistant_message": "Hello", "actions": []}'
        result = parser.parse(raw_response)
        
        assert isinstance(result, LLMResponse)
        assert result.assistant_message == "Hello"
        assert result.actions == []
        assert not result.parse_degraded

    def test_parse_json_repair(self, parser):
        """Level 2: Test JSON repair for malformed JSON"""
        # Missing closing brace
        raw_response = '{"assistant_message": "Hello", "actions": []'
        
        # Mock json_repair to simulate successful repair
        with patch('json_repair.repair_json') as mock_repair:
            mock_repair.return_value = '{"assistant_message": "Hello", "actions": []}'
            
            result = parser.parse(raw_response)
            
            mock_repair.assert_called_once()
            assert result.assistant_message == "Hello"

    def test_parse_regex_extraction(self, parser):
        """Level 3: Test extracting JSON from markdown text"""
        raw_response = '''
        Here is your response:
        ```json
        {"assistant_message": "Extracted", "actions": []}
        ```
        '''
        result = parser.parse(raw_response)
        assert result.assistant_message == "Extracted"

    def test_parse_fallback_degraded(self, parser):
        """Level 4: Test fallback to text-only mode"""
        raw_response = "I cannot generate JSON format today."
        
        result = parser.parse(raw_response)
        
        assert result.parse_degraded is True
        assert result.assistant_message == "I cannot generate JSON format today."
        assert result.actions == []
        assert result.degraded_reason is None

    def test_detect_action_intent_in_fallback(self, parser):
        """Test detection of 'fake success' in degraded mode"""
        # Text implies an action was taken, but no JSON action was parsed
        raw_response = "已为您创建任务：复习数学"
        
        result = parser.parse(raw_response)
        
        assert result.parse_degraded is True
        assert result.degraded_reason is not None
        assert "AI 可能尝试执行了操作" in result.degraded_reason
        assert "创建" in result.degraded_reason