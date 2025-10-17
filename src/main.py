
import time
import schedule
from builder import build_url, get_config

from parser import (
    parse_vacancies_from_url, similarity_check, send_telegram_message,
    connect_db, is_vacancy_sent, mark_vacancy_sent, format_vacancy_message,
    create_table_if_not_exists 
)


def job(db_conn, config):
    print("Ищу вакансии...")
    page = 0
    new_found = False
    
    while True:
        url = build_url(
            config["search_text"], 
            config["excluded_text"], 
            config["area_ids"], 
            config["experience"], 
            page
        )

        
        vacancies = parse_vacancies_from_url(url)
        
        if not vacancies:
            print("Вакансии не найдены/ошибка парсинга")
            break
            
        print(f"Найдено {len(vacancies)} вакансий")
        
        for v in vacancies:
            is_similar, similarity_percent = similarity_check(config["search_text"], v, config["min_similarity"])
            
            if is_similar:
                if not is_vacancy_sent(db_conn, v['href']):
                    print(f"Найдена подходящая вакансия: {v['title']} (схожесть: {similarity_percent}%)")

                    success = send_telegram_message(config["bot_token"], config["chat_id"], v)
                    if success:
                        mark_vacancy_sent(db_conn, v['href'], v['title'], v['company'])
                        new_found = True
                    else:
                        print(f"Не удалось отправить сообщение в телеграм")
                else:
                    print(f"Уже отправлена: {v['title']} (схожесть: {similarity_percent}%)")
            else:
                print(f"Не подходит: {v['title']} (схожесть: {similarity_percent}%)")
        
        #если вакансий меньше 20 значит ласт страница
        if len(vacancies) < 20:
            print("Последняя страница достигнута")
            break
            
        page += 1
        time.sleep(1) 
        
    if not new_found:
        print("Новых подходящих вакансий не найдено.")
    else:
        print("Новые вакансии успешно отправлены!")


def main():
    config = get_config()

    if not config["bot_token"] or not config["chat_id"]:
        print("Ошибка: Сначала запустите builder.py для настройки конфигурации!")
        return
    
    print("Конфиг загружен из config.json")
    print(f"Поиск: {config['search_text']}")
    print(f"Интервал: {config['interval']} минут")

    
    db_conn = connect_db()

    if db_conn:
        create_table_if_not_exists(db_conn)
    else:
        print("Не удалось подключиться к БД, работаю без сохранения истории!")
    
    print("Запускаю мониторинг...")

    def scheduled_job():
        job(db_conn, config)

    scheduled_job()  #запуск сразу
    schedule.every(config["interval"]).minutes.do(scheduled_job)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("Завершаю работу...")
    finally:
        if db_conn:
            db_conn.close()

if __name__ == "__main__":
    main()