import pandas as pd
import json
import os

# Указание пути для сохранения Excel-файла
folder_path = r'E:\pythonProjectsForUniversity\pythonProject\Exsel_table\Blum.xlsx'

# Установите текущий курс рубля к евро
exchange_rate = 0.012  # Пример: 1 рубль = 0.012 евро

# Функция для загрузки данных из JSON файла
def load_json(filename):
    """
    Загружает данные из JSON файла.

    :param filename: Имя или путь к JSON файлу
    :return: Данные, загруженные из файла в виде Python объекта
    """
    with open(filename, 'r', encoding='utf-8') as file:
        return json.load(file)

# Функция для перевода цены в евро
def convert_prices_to_euro(data, rate):
    """
    Переводит цены из рублей в евро и перезаписывает их в поле "Стоимость".

    :param data: Список словарей с ценами в рублях (в поле "Стоимость")
    :param rate: Курс рубля к евро
    :return: Обновленные данные с ценами в евро в поле "Стоимость"
    """
    for item in data:
        if 'Стоимость' in item and item['Стоимость']:  # Проверка, что поле "Стоимость" не пустое
            # Убираем неразрывные пробелы \xa0
            price_rub = item['Стоимость'].replace('\xa0', '').replace(' ', '')  # Убираем все пробелы
            try:
                price_rub = float(price_rub)  # Преобразуем в число с плавающей точкой
                item['Стоимость'] = round(price_rub * rate, 2)  # Перезаписываем стоимость в евро
            except ValueError:
                print(f"Ошибка при преобразовании стоимости для товара: {item}")
                item['Стоимость'] = None  # Если ошибка, указываем None
        else:
            item['Стоимость'] = None  # Если стоимость отсутствует, присваиваем None
    return data


# Загрузка данных из двух JSON файлов
data1 = load_json('items.json')  # Первый JSON файл
data2 = load_json('items_2.json')  # Второй JSON файл

# Перевод цен в евро
data1 = convert_prices_to_euro(data1, exchange_rate)
data2 = convert_prices_to_euro(data2, exchange_rate)

# Преобразование данных в pandas DataFrame
df1 = pd.DataFrame(data1)
df2 = pd.DataFrame(data2)

# Объединяем два DataFrame в один
combined_df = pd.concat([df1, df2], ignore_index=True)

# Создаем папку, если она не существует
os.makedirs(os.path.dirname(folder_path), exist_ok=True)

# Сохранение объединенного DataFrame в Excel файл
combined_df.to_excel(folder_path, index=False, engine='openpyxl')

# Сохранение обновленных JSON-файлов (по желанию)
with open('items_converted.json', 'w', encoding='utf-8') as file:
    json.dump(data1, file, ensure_ascii=False, indent=4)

with open('items_2_converted.json', 'w', encoding='utf-8') as file:
    json.dump(data2, file, ensure_ascii=False, indent=4)

print("Цены успешно преобразованы и сохранены в файл 'Blum.xlsx'")
