import pytest
import sys
import os
from unittest.mock import patch, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from main import job, main, schedule_stats

class TestMain:
    
    @patch('main.parse_vacancies_from_url')
    @patch('main.similarity_check')
    @patch('main.is_vacancy_sent')
    @patch('main.send_telegram_message')
    @patch('main.mark_vacancy_sent')
    def test_job_with_new_vacancies(self, mock_mark, mock_send, mock_is_sent, 
                                   mock_similarity, mock_parse):
        mock_db = Mock()
        config = {
            "search_text": "Python",
            "min_similarity": 70,
            "bot_token": "test_token", 
            "chat_id": "test_chat",
            "excluded_text": "",
            "area_ids": [],
            "experience": "",
            "daily_stats": True
        }
        
        test_vacancies = [{
            'title': 'Python Developer',
            'href': 'https://hh.ru/vacancy/123',
            'company': 'Test Co'
        }]
        
        mock_parse.return_value = test_vacancies
        mock_similarity.return_value = (True, 85)
        mock_is_sent.return_value = False
        mock_send.return_value = True
        
        job(mock_db, config)
        
        mock_send.assert_called_once()
        mock_mark.assert_called_once()
    
    @patch('main.parse_vacancies_from_url')
    @patch('main.similarity_check') 
    def test_job_no_suitable_vacancies(self, mock_similarity, mock_parse):
        mock_db = Mock()
        config = {
            "search_text": "Python",
            "min_similarity": 70,
            "excluded_text": "",
            "area_ids": [],
            "experience": "",
            "daily_stats": True
        }
        
        test_vacancies = [{
            'title': 'Java Developer', 
            'href': 'https://hh.ru/vacancy/456',
            'company': 'Test Co'
        }]
        
        mock_parse.return_value = test_vacancies
        mock_similarity.return_value = (False, 30)
        
        job(mock_db, config)
    
    @patch('main.parse_vacancies_from_url')
    def test_job_no_vacancies_found(self, mock_parse):
        mock_db = Mock()
        config = {
            "search_text": "Python",
            "excluded_text": "",
            "area_ids": [],
            "experience": "",
            "daily_stats": False
        }
        
        mock_parse.return_value = []
        
        job(mock_db, config)
    
    @patch('main.get_config')
    @patch('main.connect_db')
    @patch('main.create_table_if_not_exists')
    @patch('main.schedule')
    @patch('main.job')
    def test_main_success(self, mock_job, mock_schedule, mock_create_table, 
                         mock_connect_db, mock_get_config):
        mock_config = {
            "bot_token": "test",
            "chat_id": "test", 
            "search_text": "Python",
            "interval": 1,
            "excluded_text": "",
            "area_ids": [],
            "experience": "",
            "daily_stats": True
        }
        mock_get_config.return_value = mock_config
        
        mock_db = Mock()
        mock_connect_db.return_value = mock_db
        
        mock_schedule.run_pending.side_effect = KeyboardInterrupt
        
        try:
            main()
        except KeyboardInterrupt:
            pass
        
        mock_get_config.assert_called_once()
        mock_connect_db.assert_called_once()
        mock_create_table.assert_called_once_with(mock_db)
        mock_job.assert_called()
    
    @patch('main.get_config')
    def test_main_no_config(self, mock_get_config):
        mock_get_config.return_value = {
            "bot_token": "",
            "chat_id": "",
            "search_text": "Python", 
            "excluded_text": "",
            "area_ids": [],
            "experience": "",
            "daily_stats": True
        }
        
        # main() просто возвращается при ошибке, не вызывает sys.exit
        result = main()
        assert result is None  # Просто проверяем что функция завершилась
    
    @patch('main.schedule')
    def test_schedule_stats_enabled(self, mock_schedule):
        mock_db = Mock()
        config = {
            "daily_stats": True
        }
        
        schedule_stats(mock_db, config)
        
        mock_schedule.every.assert_called_once()
    
    @patch('main.schedule')
    def test_schedule_stats_disabled(self, mock_schedule):
        mock_db = Mock()
        config = {
            "daily_stats": False
        }
        
        schedule_stats(mock_db, config)
        
        mock_schedule.every.assert_not_called()
    
    @patch('main.get_config')
    @patch('main.connect_db')
    @patch('main.create_table_if_not_exists')
    @patch('main.schedule')
    @patch('main.job')
    def test_main_with_daily_stats_disabled(self, mock_job, mock_schedule, 
                                          mock_create_table, mock_connect_db, 
                                          mock_get_config):
        mock_config = {
            "bot_token": "test",
            "chat_id": "test", 
            "search_text": "Python",
            "interval": 1,
            "excluded_text": "",
            "area_ids": [],
            "experience": "",
            "daily_stats": False  # Статистика отключена
        }
        mock_get_config.return_value = mock_config
        
        mock_db = Mock()
        mock_connect_db.return_value = mock_db
        
        mock_schedule.run_pending.side_effect = KeyboardInterrupt
        
        try:
            main()
        except KeyboardInterrupt:
            pass
        
        # Проверяем что статистика не планируется
        mock_schedule.every().day.at.assert_not_called()