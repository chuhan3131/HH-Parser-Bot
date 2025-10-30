import pytest
import json
import os
import tempfile
import sys
from unittest.mock import patch, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from builder import load_config, save_config, build_url, get_experience, REGIONS

class TestBuilder:
    
    def test_load_config_existing_file(self):
        test_config = {
            "min_similarity": 80,
            "interval": 15,
            "bot_token": "test_token",
            "chat_id": "test_chat",
            "search_text": "test",
            "excluded_text": "",
            "area_ids": [],
            "experience": "",
            "daily_stats": True,
            "stats_time": "00:00"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f)
            temp_path = f.name
        
        try:
            with patch('builder.CONFIG_FILE', temp_path):
                config = load_config()
                assert config["min_similarity"] == 80
                assert config["interval"] == 15
                assert config["daily_stats"] == True
                assert config["stats_time"] == "00:00"
        finally:
            os.unlink(temp_path)
    
    def test_load_config_missing_file(self):
        with patch('builder.CONFIG_FILE', 'nonexistent.json'):
            config = load_config()
            assert config["min_similarity"] == 70
            assert config["interval"] == 10
            assert config["daily_stats"] == True  # default value
            assert config["stats_time"] == "00:00"  # default value
    
    def test_load_config_missing_new_fields(self):
        """Тест загрузки старого конфига без новых полей"""
        old_config = {
            "min_similarity": 80,
            "interval": 15,
            "bot_token": "test_token",
            "chat_id": "test_chat",
            "search_text": "test",
            "excluded_text": "",
            "area_ids": [],
            "experience": ""
            # Отсутствуют daily_stats и stats_time
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(old_config, f)
            temp_path = f.name
        
        try:
            with patch('builder.CONFIG_FILE', temp_path):
                config = load_config()
                assert config["min_similarity"] == 80
                assert config["daily_stats"] == True  # должно добавиться значение по умолчанию
                assert config["stats_time"] == "00:00"  # должно добавиться значение по умолчанию
        finally:
            os.unlink(temp_path)
    
    def test_save_config(self):
        test_config = {
            "min_similarity": 85,
            "interval": 20,
            "bot_token": "save_test",
            "chat_id": "chat_test",
            "search_text": "test",
            "excluded_text": "",
            "area_ids": [],
            "experience": "",
            "daily_stats": False,
            "stats_time": "09:00"
        }
        
        mock_file = mock_open()
        with patch('builtins.open', mock_file):
            with patch('json.dump') as mock_json:
                save_config(test_config)
                
        mock_file.assert_called_once_with('config.json', 'w', encoding='utf-8')
    
    def test_build_url_basic(self):
        url = build_url("python developer", "", ["area=113"], "between1And3", 0)
        assert "hh.ru/search/vacancy" in url
        assert "text=python+developer" in url
        assert "area=113" in url
        assert "experience=between1And3" in url
        assert "page=0" in url
    
    def test_build_url_with_excluded_text(self):
        url = build_url("python", "java php", ["area=113"], "noExperience", 1)
        assert "excluded_text=java+php" in url or "excluded_text=java php" in url
        assert "page=1" in url
    
    def test_build_url_empty_params(self):
        url = build_url("test", "", [], "", 0)
        assert "text=test" in url
        assert "excluded_text=" not in url
    
    @pytest.mark.parametrize("input_exp,expected", [
        ("0", "noExperience"),
        ("1-3", "between1And3"), 
        ("3-6", "between3And6"),
        ("6+", "moreThan6"),
        ("1", "between1And3"),
        ("5", "between3And6"),
        ("7", "moreThan6"),
    ])
    def test_get_experience_various_inputs(self, input_exp, expected):
        with patch('builtins.input', return_value=input_exp):
            result = get_experience()
            assert result == expected
    
    def test_regions_mapping(self):
        assert REGIONS["россия"] == 113
        assert REGIONS["украина"] == 5
        assert REGIONS["казахстан"] == 40
        assert REGIONS["беларусь"] == 16
        assert REGIONS["грузия"] == 28
    
    def test_get_experience_invalid_input_then_valid(self):
        """Тест неверного ввода, затем правильного"""
        inputs = ["invalid", "1-3"]
        with patch('builtins.input', side_effect=inputs):
            result = get_experience()
            assert result == "between1And3"