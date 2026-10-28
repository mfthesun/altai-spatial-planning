#!/usr/bin/env bash
# Подготовка облачной среды Claude Code для проекта (вызывается из Setup script среды).
# Ставит библиотеки из requirements.txt в системный Python и регистрирует ядро Jupyter.
# Рельеф (Copernicus DEM, 1,3 ГБ) и граф OSM здесь не качаются: блокнот докачает их сам в results/.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install -q --disable-pip-version-check -r requirements.txt
python3 -m ipykernel install --user --name python3 >/dev/null
python3 -c "import geopandas, rasterio, iduedu, objectnat; print('altai: среда готова, iduedu', iduedu.__version__, 'objectnat', objectnat.__version__)"
