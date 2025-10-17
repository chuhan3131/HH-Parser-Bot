
import json
import os

CONFIG_FILE = 'config.json'


DEFAULT_CONFIG = {
    "min_similarity": 70,
    "interval": 10,
    "bot_token": "",
    "chat_id": "",
    "search_text": "Middle Python Backend Developer",
    "excluded_text": "",
    "area_ids": [],
    "experience": ""
}

REGIONS = {
    "россия": 113,
    "украина": 5,
    "казахстан": 40,
    "азербайджан": 9,
    "беларусь": 16,
    "грузия": 28,
    "другие": 1001,
    "кыргызстан": 48,
    "узбекистан": 97
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for key in DEFAULT_CONFIG:
                    if key not in config:
                        config[key] = DEFAULT_CONFIG[key]
                return config
        except Exception as e:
            print(f"Ошибка загрузки конфига: {e}")
            return DEFAULT_CONFIG.copy()
    else:
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Сохраняет конфигурацию в JSON файл"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print("Конфигурация сохранена в config.json")
    except Exception as e:
        print(f"Ошибка сохранения конфига: {e}")

def build_url(search_text, excluded_text, area_ids, experience, page=0):
    base_url = "https://hh.ru/search/vacancy?"
    search_text_encoded = search_text.replace(' ', '+')
    excluded_param = f"excluded_text={excluded_text}" if excluded_text else ""
    area_params = "&".join(area_ids)
    
    params = [
        f"text={search_text_encoded}",
        excluded_param,
        area_params,
        f"experience={experience}",
        "order_by=relevance",
        "search_period=0",
        "items_on_page=50",
        "L_save_area=true",
        f"page={page}"
    ]
    params = [p for p in params if p]
    return base_url + "&".join(params)

def get_regions():
    while True:
        area_input = input("Введите регионы через запятую: ").strip()
        region_names = [r.strip().lower() for r in area_input.split(',')]
        area_ids = []
        invalid_regions = []
        
        for name in region_names:
            region_id = REGIONS.get(name)
            if region_id:
                area_ids.append(f"area={region_id}")
            else:
                invalid_regions.append(name)
        
        if invalid_regions:
            print(f"Неизвестные регионы: {', '.join(invalid_regions)}. Попробуйте снова.\n")
        else:
            return area_ids

def get_search_text():
    text = input("Введите поисковый запрос (пустой = дефолтный): ").strip()
    return text if text else "Middle Python Backend Developer"

def get_excluded_words():
    excluded = input("Введите исключённые слова (через запятую, можно пусто): ").strip()
    return excluded.replace(',', '+').replace(' ', '+') if excluded else ""

def get_experience():
    while True:
        exp_input = input("\nВведите опыт работы (например: 0, 1-3, 6+):").strip()
        
        if exp_input == "0":
            return "noExperience"
        
        if exp_input.endswith('+'):
            try:
                val = int(exp_input[:-1])
                return "moreThan6"
            except ValueError:
                print("Неверный формат!")
                continue
        
        if '-' in exp_input:
            parts = exp_input.split('-')
            if len(parts) == 2:
                try:
                    start = int(parts[0])
                    end = int(parts[1])
                    if start > end or start < 0 or end < 0:
                        print("Неверный диапазон!")
                        continue
                    
                    if end < 1:
                        return "noExperience"
                    elif start >= 6:
                        return "moreThan6"
                    elif start >= 3:
                        return "between3And6"
                    elif start >= 1:
                        return "between1And3"
                    elif start >= 0:
                        return "between0And1"
                except ValueError:
                    print("Неверный формат диапазона!")
                    continue
        
        try:
            val = int(exp_input)
            if val == 0:
                return "noExperience"
            elif 1 <= val < 3:
                return "between1And3"
            elif 3 <= val < 6:
                return "between3And6"
            elif val >= 6:
                return "moreThan6"
            elif 0 < val < 1:
                return "between0And1"
        except ValueError:
            print("Неверный формат ввода опыта!")
            continue

def setup_config():
    """Настройка конфигурации и сохранение в JSON"""
    config = load_config()
    
    config["bot_token"] = input("Введите Token: ").strip()
    config["chat_id"] = input("Введите Chat ID: ").strip()
    
    try:
        config["interval"] = int(input("Введите интервал проверки в минутах: ").strip())
    except ValueError:
        print("Неверный интервал. Используем 10 минут.")
        config["interval"] = 10
    
    config["area_ids"] = get_regions()
    config["search_text"] = get_search_text()
    config["excluded_text"] = get_excluded_words()
    config["experience"] = get_experience()

    save_config(config)

    url = build_url(config["search_text"], config["excluded_text"], config["area_ids"], config["experience"], 0)
    
    return config

def get_config():
    return load_config()

if __name__ == "__main__":
    setup_config()