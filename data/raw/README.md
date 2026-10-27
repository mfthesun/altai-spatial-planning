# Сырые данные (в репозиторий не входят)

Архивы «Если быть точным» ([tochno.st/datasets](https://tochno.st/datasets)) нужно скачать и распаковать в `data/raw/` в такой раскладке, как ожидает `scripts/dataset/build_dataset.py`:

| Папка | Источник (архив) |
|---|---|
| `bdmo/` | БД ПМО, разделы 6, 7, 9, 13, 37, 60: `data_section<N>_112_v20260928_section_file.zip` (parquet/csv) |
| `reg84/` | Региональные архивы БД ПМО по Республике Алтай. Шаблон ссылки: `https://storage.yandexcloud.net/tochno-st-catalog/Rosstat/data_bdmo_118_v20260928/regions/data_<КОД>_region84_112_v20260928.zip` |
| `allsett/` | `data_allsettlements_anon_156_v20260925_csv.zip` |
| `mun_demo/` | `data_mun_demography_123_v20240612_csv.zip` |
| `sme/` | `data_sme_153_region_Республика_Алтай_v20260605_xlsx.zip` |
| `dtp/` | `data_traffic_accidents_126_csv.zip` |
| `fires/` | `data_fires_128_v20240912_csv.zip` |
| `gisgkh/` | `data_gisgkh_157_v20260917_xlsx.zip` |
| `budgets/` | `data_budgets_140_v20241118_csv.zip` |
| `housing/` | `data_housing_construction_161_csv.zip` |
| `air/` | `data_air_emissions_147_v20250515_csv.zip` |
| `ndfl/r04`, `ndfl/r17`, `ndfl/r19` | НДФЛ по регионам: `https://storage.yandexcloud.net/tochno-st-catalog/FNS/data_ndfl_155_v20260722/by_regions/data_ndfl_155_<04|17|19>_v20260722.zip` (Алтай, Тыва, Хакасия) |
| `rc.parquet` | `data_regions_collection_102_v20260313.parquet` |
| `ezh.txt`, `racif.txt`, `ser.txt` | Текстовый слой ежегодника, «Республика Алтай в цифрах» и Стратегии СЭР (pdftotext) |

Коды показателей БД ПМО — в справочнике проекта: [Google Sheet](https://docs.google.com/spreadsheets/d/1fain2iBHAJEkaXYk-8aAcjEA8tdR5GKF134AAk1UCSQ).
Разделы 31/32 и полный архив НДФЛ (несколько ГБ) в сборке не используются — вместо полного НДФЛ берутся региональные архивы.
