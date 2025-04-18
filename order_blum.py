import asyncio
import json
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.async_api import async_playwright
import fake_useragent
import time
import re

# Генерация случайного User-Agent
user_agent = fake_useragent.UserAgent().random

# Заголовки для запросов
headers = {
    'User-Agent': user_agent,
    'Referer': 'https://nois.su/',
    'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
    'Connection': 'keep-alive'
}

# URL страницы
url = 'https://nois.su/catalog/blum/'
base_url = 'https://nois.su'


# Функция для получения ссылок на группы с использованием aiohttp
async def groups_link(session):
    print("[LOG] Старт получения ссылок на группы...")  # [LOG]
    try:
        async with session.get(url, headers=headers, timeout=15) as response:
            print(f"[LOG] Запрос к {url} выполнен.")  # [LOG]
            response.raise_for_status()


            soup = BeautifulSoup(await response.text(), 'lxml')
            groups = soup.find_all('div', class_='item item--lg')
            groups_link_list = [urljoin(base_url, group.find('a')['href']) for group in groups if group.find('a')]

            print(f"[LOG] Найдено {len(groups_link_list)} ссылок на группы.")  # [LOG]
            with open('groups_link_list.txt', 'w', encoding='utf-8') as file:
                for link in groups_link_list:
                    file.write(f'{link}\n')

            return groups_link_list

    except aiohttp.ClientError as e:
        print(f"[ERROR] Ошибка при получении групп: {e}")  # [LOG]
        return []


# Функция для получения ссылок на подгруппы с использованием aiohttp
async def subgroups_link(session, groups_link_list):
    subgroups_link_list = []
    browser = None  # Инициализация переменной browser
    try:
        for group_link in groups_link_list:
            try:
                async with session.get(group_link, headers=headers, timeout=15) as response:
                    response.raise_for_status()

                    if group_link.endswith('/podyemnye-mekhanizmy/'):
                        print(f"[LOG] AVENTOS-группа найдена: {group_link}")
                        nested_links = [
                            urljoin(base_url, '/catalog/blum/podyemnye-mekhanizmy/aventos/'),
                            urljoin(base_url, '/catalog/blum/podyemnye-mekhanizmy/aventos-top_2/')
                        ]

                        for nested_url in nested_links:
                            print(f"[LOG] Переход на вложенную подгруппу: {nested_url}")
                            try:
                                async with session.get(nested_url, headers=headers, timeout=15) as nested_resp:
                                    nested_resp.raise_for_status()
                                    nested_soup = BeautifulSoup(await nested_resp.text(), 'lxml')
                                    nested_items = nested_soup.find_all('div', class_='item item--lg')
                                    for nested_item in nested_items:
                                        href = nested_item.find('a', class_='item-img')['href']
                                        if href:
                                            full_link = urljoin(base_url, href)
                                            subgroups_link_list.append(full_link)
                            except Exception as ex:
                                print(f"[ERROR] Ошибка при переходе к подгруппе AVENTOS: {nested_url}\n{ex}")

                    soup = BeautifulSoup(await response.text(), 'lxml')
                    item_subgroup = soup.find('div', class_='item-list item-list--full')
                    item_subgroup_1 = soup.find('div', class_='item-list item-list--lg js__goods_list')

                    if item_subgroup:
                        subgroups = item_subgroup.find_all('div', class_='item item--lg')
                        subgroups_link_list.extend(
                            [urljoin(base_url, subgroup.find('a')['href']) for subgroup in subgroups if
                             subgroup.find('a')])

                    elif item_subgroup_1:
                        items_contents_link = []
                        async with async_playwright() as p:
                            browser = await p.chromium.launch(headless=True)  # Запуск браузера в headless-режиме
                            page = await browser.new_page()
                            await page.goto(group_link)
                            # Ждём появления формы с кнопками
                            await page.wait_for_selector('.location-list')
                            # Нажимаем на кнопку "Москва и МО" по тексту
                            moscow_button = page.locator("button:has-text('Москва и МО')")
                            if await moscow_button.is_visible():
                                await moscow_button.click()
                                print("Клик по кнопке 'Москва и МО' выполнен.")
                            else:
                                print("Кнопка 'Москва и МО' не найдена.")


                            # Ищем элемент Blum
                            chapter = await page.query_selector('div.bx-breadcrumb-item a[href="/catalog/blum/"] span[itemprop="name"]')
                            blum = await chapter.inner_text()
                            # Извлекаем группу
                            text_1 = await page.query_selector('div.bx-breadcrumb-item div.bread__el#last_bread_el')
                            name_group = await text_1.inner_text()

                            comment = "НОИС"
                            units_of_measurement = "шт."



                            while True:
                                try:
                                    # Прокручиваем вниз перед поиском кнопки
                                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                                    await page.wait_for_timeout(500)  # Пауза для загрузки контента

                                    # Проверяем наличие кнопки "Показать еще"
                                    show_more_button = page.locator("button:has-text('Показать ещё')")
                                    if await show_more_button.is_visible():
                                        await show_more_button.scroll_into_view_if_needed()
                                        await show_more_button.click()
                                        await page.wait_for_timeout(2000)
                                    else:
                                        break
                                except Exception as ex:
                                    print(f"Error while clicking 'Показать еще': {ex}")
                                    break

                            items_playwright = await page.query_selector_all('div.item.item--lg')

                            for element in items_playwright:
                                # Ищем элементы внутри текущего элемента, где есть div с классом 'item-props_el'
                                item_props_elements = await element.query_selector_all('div.item-props_el')
                                # article = 'Не найден'
                                # factory_code = 'Не найден'
                                for prop_element in item_props_elements:
                                    # Получаем текст из элемента
                                    text_content = await prop_element.inner_text()
                                    # Проверяем, содержит ли текст "Артикул" или "Заводской код"
                                    if 'Артикул' in text_content:
                                        # Извлекаем артикул (текст после "Артикул:")
                                        article = text_content.split('Артикул:')[1].strip()
                                    elif 'Заводской код' in text_content:
                                        # Извлекаем заводской код (текст после "Заводской код:")
                                        factory_code = text_content.split('Заводской код:')[1].strip()
                                # Находим название товара по ссылке с классом 'item-title'
                                item_title_element = await element.query_selector('a.item-title')
                                if item_title_element:
                                    item_title = await item_title_element.inner_text()
                                # Ищем цену в блоке с классом 'order__price'
                                price_element = await element.query_selector('div.order__price span[id*="price"]')
                                if price_element:
                                    price = await price_element.inner_text()
                                    # Очищаем от лишних символов и пробелов
                                    price = price.replace(" ₽", "").strip()
                                items_contents_link.append(
                                    {'Артикул': article, 'Наименование материала': item_title, 'Наименование группы': f'{blum}/{name_group}', 'Единица измерения': units_of_measurement, 'Стоимость': price, 'Идентификатор для синхронизации': factory_code,
                                     'Комментарий': comment})

                            if items_contents_link:
                                with open('items_2.json', 'w', encoding='utf-8') as json_file:
                                    json.dump(items_contents_link, json_file, ensure_ascii=False, indent=4)
                                print("Данные сохранены в items_2.json.")
                            else:
                                print("No items to save.")

                        if not item_subgroup and not item_subgroup_1:
                            print(f"No item-list found for {group_link}. Saving HTML for debugging.")
                            with open(f'debug_subgroup_{time.time()}.html', 'w', encoding='utf-8') as file:
                                file.write(await response.text())
                                continue

            except aiohttp.ClientError as e:
                print(f"Error fetching subgroups for {group_link}: {e}")
                with open(f'debug_subgroup_error_{time.time()}.html', 'w', encoding='utf-8') as file:
                    file.write(str(e))

    finally:
        if browser:  # Проверяем, был ли инициализирован браузер перед его закрытием
            await browser.close()

    subgroups_link_list = [
        link for link in subgroups_link_list
        if not re.match(r'.*/aventos(-top_2)?/?$', link)
    ]

    print(f"Total subgroups links found: {len(subgroups_link_list)}")
    with open('subgroups_link_list.txt', 'w', encoding='utf-8') as file:
        for link in subgroups_link_list:
            file.write(f'{link}\n')

    return subgroups_link_list


# Функция для получения HTML данных с использованием Playwright
async def get_source_html(subgroups_link_list):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Запуск браузера в headless-режиме
        page = await browser.new_page()

        items_groups_link = []
        moscow_button_clicked = False  # Флаг для отслеживания, нажата ли кнопка

        try:
            for link in subgroups_link_list:
                try:
                    await page.goto(link, timeout=180000)  # Увеличиваем таймаут до 180 секунд
                    # Нажимаем на кнопку "Москва и МО" только один раз

                    if not moscow_button_clicked:
                        # Ждем появления формы с кнопками (с увеличенным таймаутом)
                        await page.wait_for_selector('.location-list', state='visible', timeout=60000)
                        moscow_button = page.locator("button:has-text('Москва и МО')")

                        # Проверяем, видна ли кнопка
                        if await moscow_button.is_visible():
                            await moscow_button.scroll_into_view_if_needed()  # Прокручиваем кнопку в видимую область
                            await moscow_button.click()
                            print("Клик по кнопке 'Москва и МО' выполнен.")
                            moscow_button_clicked = True  # Устанавливаем флаг, что кнопка была нажата
                        else:
                            print("Кнопка 'Москва и МО' не найдена.")
                    else:
                        print("Кнопка 'Москва и МО' уже была нажата.")

                    # Ищем элемент Blum
                    chapters = await page.query_selector_all('div.bx-breadcrumb-item span[itemprop="name"]')
                    text_list = []
                    for chapter in chapters:
                        text = await chapter.inner_text()
                        text_list.append(text)
                    blum = text_list[2]
                    print(blum)
                    name_group = text_list[3]
                    print(name_group)
                    # Извлекаем подгруппу
                    text_1 = await page.query_selector('div.bx-breadcrumb-item div.bread__el#last_bread_el')
                    name_subgroup = await text_1.inner_text()
                    print(name_subgroup)

                    comment = "НОИС"
                    units_of_measurement = "шт."

                    await page.wait_for_selector('.order__el-wrap, .item-list.item-list--lg.js__goods_list',
                                                 timeout=60000)
                    await page.wait_for_timeout(2000)  # Пауза для загрузки контента

                    # Прокрутка до кнопки "Показать еще" и клик по ней
                    while True:
                        try:
                            # Прокручиваем вниз перед поиском кнопки
                            await page.evaluate("window.scrollBy(0, window.innerHeight)")
                            await page.wait_for_timeout(500)  # Пауза для загрузки контента

                            # Проверяем наличие кнопки "Показать еще"
                            show_more_button = page.locator("button:has-text('Показать ещё')")
                            if await show_more_button.is_visible():
                                await show_more_button.scroll_into_view_if_needed()
                                await show_more_button.click()
                                await page.wait_for_timeout(2000)
                            else:
                                break
                        except Exception as ex:
                            print(f"Error while clicking 'Показать еще': {ex}")
                            break


                    items_container = await page.query_selector('div.order__el-wrap')
                    items_container_1 = await page.query_selector('div.item-list.item-list--lg.js__goods_list')

                    # Печать отладочной информации
                    if not items_container and not items_container_1:
                        print(f"No items found on page: {link}")
                        continue

                    # Извлечение наименования и цены
                    if items_container:
                        items_playwright = await items_container.query_selector_all('div[class*="js_p_group"]')
                        for element in items_playwright:
                            # Ищем элементы внутри текущего элемента, где есть div с классом 'order__art'
                            item_props_elements = await element.query_selector_all('.order__art')
                            # article = 'Не найден'
                            # factory_code = 'Не найден'
                            for prop_element in item_props_elements:
                                # Получаем текст из элемента
                                text_content = await prop_element.inner_text()
                                # Проверяем, содержит ли текст "Артикул" или "Заводской код"
                                if 'Артикул' in text_content:
                                    # Извлекаем артикул (текст после "Артикул:")
                                    article = text_content.split('Артикул:')[1].strip()

                                elif 'Заводской код' in text_content:
                                    # Извлекаем заводской код (текст после "Заводской код:")
                                    factory_code = text_content.split('Заводской код:')[1].strip()

                                    # Находим название товара по ссылке с классом 'item-title'
                            item_title_element = await element.query_selector('a.order__name-text')
                            if item_title_element:
                                item_title = await item_title_element.inner_text()

                                # Ищем цену в блоке с классом 'order__price'
                            price_element = await element.query_selector('div.order__price.card-cost-with-hint span[id*="price"]')
                            if price_element:
                                price = await price_element.inner_text()
                                # Очищаем от лишних символов и пробелов
                                price = price.replace(" ₽", "").strip()

                            items_groups_link.append(
                                    {'Артикул': article, 'Наименование материала': item_title, 'Наименование группы': f'{blum}/{name_group}/{name_subgroup}', 'Единица измерения': units_of_measurement, 'Стоимость': price, 'Идентификатор для синхронизации': factory_code,
                                     'Комментарий': comment})


                    elif items_container_1:
                        items_playwright_1 = await items_container_1.query_selector_all('div.item.item--lg')
                        for element in items_playwright_1:
                            # Ищем элементы внутри текущего элемента, где есть div с классом 'item-props_el'
                            item_props_elements = await element.query_selector_all('div.item-props_el')
                            # article = 'Не найден'
                            # factory_code = 'Не найден'
                            for prop_element in item_props_elements:
                                # Получаем текст из элемента
                                text_content = await prop_element.inner_text()
                                # Проверяем, содержит ли текст "Артикул" или "Заводской код"
                                if 'Артикул' in text_content:
                                    # Извлекаем артикул (текст после "Артикул:")
                                    article = text_content.split('Артикул:')[1].strip()

                                elif 'Заводской код' in text_content:
                                    # Извлекаем заводской код (текст после "Заводской код:")
                                    factory_code = text_content.split('Заводской код:')[1].strip()

                                    # Находим название товара по ссылке с классом 'item-title'
                            item_title_element = await element.query_selector('a.item-title')
                            if item_title_element:
                                item_title = await item_title_element.inner_text()
                            # Ищем цену в блоке с классом 'order__price'
                            price_element = await element.query_selector('div.order__price span[id*="price"]')
                            if price_element:
                                price = await price_element.inner_text()
                                # Очищаем от лишних символов и пробелов
                                price = price.replace(" ₽", "").strip()
                            items_groups_link.append(
                                    {'Артикул': article, 'Наименование материала': item_title, 'Наименование группы': f'{blum}/{name_group}/{name_subgroup}', 'Единица измерения': units_of_measurement, 'Стоимость': price, 'Идентификатор для синхронизации': factory_code,
                                     'Комментарий': comment})

                    # Выводим информацию о количестве найденных товаров
                    print(f"Processed {link} successfully. Found {len(items_groups_link)} items.")

                except Exception as ex:
                    print(f"Error processing {link}: {ex}")
                    with open(f'error_page_{time.time()}.html', 'w', encoding='utf-8') as file:
                        file.write(await page.content())

            # Проверяем, сколько данных найдено
            print(f"Total items extracted: {len(items_groups_link)}")

            # Сохранение данных в JSON файл
            if items_groups_link:
                with open('items.json', 'w', encoding='utf-8') as json_file:
                    json.dump(items_groups_link, json_file, ensure_ascii=False, indent=4)
                print("Данные сохранены в items.json.")
            else:
                print("No items to save.")

        finally:
            await browser.close()


# Основная функция
async def main():
    async with aiohttp.ClientSession() as session:
        groups = await groups_link(session)
        if groups:
            subgroups = await subgroups_link(session, groups)
            if subgroups:
                await get_source_html(subgroups)


if __name__ == '__main__':
    asyncio.run(main())
