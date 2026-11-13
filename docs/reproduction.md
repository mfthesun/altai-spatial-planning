# Проверка и воспроизведение

Все команды выполняются из корня репозитория в подготовленном Python-окружении
с `requirements.txt`. Карты, CSV и GeoJSON уже включены в Git.
Рабочая презентация хранится отдельно в Figma Slides; экспорт PNG не меняет ее автоматически.

## Без загрузки исходников

```bash
python scripts/check_numbers.py
python scripts/check_map_context.py
sha256sum -c assets/fonts/SHA256SUMS
```

`check_numbers.py --control` — намеренно неуспешный тест: ожидаются 101/102 и код 1.
Обычный запуск ожидает 102/102 и код 0. Эти проверки не пересчитывают маршрутизацию
и не заменяют сверку всех чисел Figma с первичными источниками.

## Экспорт из сохраненных данных

Следующие команды перезаписывают PNG. Для подложки нужен доступ к Esri;
координаты и тематические показатели читаются из сохраненных данных:

```bash
python scripts/slides/make_slides_01_03.py
python scripts/slides/make_course_feedback_maps.py
python scripts/slides/make_completion_maps.py
python scripts/slides/make_map_07_constraints.py
python scripts/slides/make_heritage_route_map.py
python scripts/model/make_model_map.py
```

Общий макет — `scripts/maptools.py`: UTM 45N, PNG 2000×1400, легенда справа,
север, масштаб и атрибуция. Inter загружается из `assets/fonts/` в процесс Python.
Легенда проверяется на выход за холст. Итоговый рендер также нужно просмотреть:
автоматическая проверка не выявляет все перекрытия.

`python scripts/access/make_access_maps.py` умеет перерисовывать карты больниц
из `data/access_results/`, когда результатов полного расчета нет. При наличии
полного `results/` он также обновляет сводные таблицы — перед запуском проверьте,
какой набор входных данных используете.

Медицинская пара «база / два центра» создается `scripts/access/scenario_south_center.py`.
Для нее недостаточно сохраненной итоговой CSV: нужна OD-матрица и граф из `results/`.
В текущем проходе эти карты не пересчитывались; их редактируемые легенды находятся в Figma.

## Полный пересчет

Исходные архивы и PDF перечислены в [data/raw/README.md](../data/raw/README.md)
и [каталоге данных](data_catalog.md). Графы, DEM и OD-матрицы в Git не хранятся.
Блокнот [altai_access_mountain.ipynb](../relief/altai_access_mountain.ipynb)
описывает полный расчет больниц; в Colab нужно указать `REPO`.

Скрипты отдельных этапов:

| Этап | Скрипт | Требования |
|---|---|---|
| Сводный датасет | `scripts/dataset/build_dataset.py`, затем `scripts/dataset/export.py` | Распакованные архивы и исходные документы |
| Входные слои больниц | `scripts/access/build_access_inputs.py` | Геоданные и источники из описания входов |
| Граф с поправкой на рельеф | `scripts/access/build_graph.py` | Сеть для OSM и DEM либо локальный кеш |
| Входы школ и ПМСП | `scripts/access/build_services_inputs.py` | OSM и перечни СТП; это отдельная версия сети объектов |
| Доступность услуг | `scripts/access/services_access.py` | Горный граф и входные слои; см. модуль и блокнот |
| Медицинские сценарии | `scripts/access/scenario_south_center.py` | `od_mountain_all_hospitals.parquet`, горный граф и входные слои |
| Карты услуг | `scripts/access/make_services_maps.py` | Результаты расчета услуг |
| Вторые оси модели | `scripts/model/build_axes.py` | Горный граф и входные геоданные |

Это перечень модулей, а не обещание полностью автономной сборки из чистого клона.
Новый запрос OSM или новые версии реестров могут изменить результаты. Сохраняйте
дату источника и не смешивайте новый расчет с прежними подписями слайдов.
Адресный пересчет отдельно описан в [отчете 07.11](access_registers_2026-11-07.md).

| Переменная | Назначение |
|---|---|
| `ALTAI_RAW` | Распакованные архивы для сборки датасета |
| `ALTAI_SOURCES` | Папка исходных документов сборки |
| `ALTAI_OUT` | Выходная папка сборки датасета |
| `ALTAI_RESULTS` | Графы, OD-матрицы и результаты расчета доступности; по умолчанию `results/` |
| `OVERPASS_URL` | Зеркало Overpass; задается до импорта IduEdu |

Подробности и оговорки: [входы](access_inputs.md), [метод рельефа](relief_method.md),
[результаты больниц](access_results.md), [школы и ПМСП](access_services.md).
