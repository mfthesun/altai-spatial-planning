# Завершение этапа концепции — 13.11.2026

Денис явно поручил закрыть все открытые Issues, опубликовать PR и принять его в main. Отчет фиксирует основание закрытия задач №1–8 за текущий учебный этап. Это решение не означает выполнения оставшихся исследований, согласования всеми соавторами или готовности проектной документации. Неподтвержденные критерии сохранены ниже, исходные чек-листы не переписаны.

Проверены актуальные тела всех восьми открытых Issues и все доступные комментарии. Историческая матрица 04.11 обновляется этим отчетом, включая выполненную 07.11 обработку адресных реестров.

Рабочая [презентация Figma Slides](https://www.figma.com/slides/YU7UHNRFIcDRq8dqVq1Qso), [состав и ID](presentation_manifest_2026-11-13.json), [проверка 20 карт](map_visual_audit_2026-11-13.md).

<a id="issue-1"></a>
## #1 — Расселение и социокультурные факторы

**Результат:** Собраны агломерация, демография и этнокультурные ареалы; проектная сеть — 9 официальных сельских ОНП и 6 предложенных центров. Для базового прогноза принята трендовая оценка, верхние 122–123 тыс. не выданы за наблюдаемый рост. Подготовлены отраслевые SWOT и пространственная модель.

**Границы приемки:** Адресные реестры школ и медицины обработаны и пересчитаны 07.11; это обновляет старый запрос в Issue. Часть координат остается привязкой к центру села, 14 школьных страниц были недоступны, полное подтверждение лицензий и ключей ФРМО отсутствует. Значения разных наборов точек не взаимозаменяемы; старые 59 ФАПов по № 543н не являются действующим перечнем строительства.

**Материалы:** [docs/access_registers_2026-11-07.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/access_registers_2026-11-07.md); [data/onp_candidates.csv](https://github.com/mfthesun/altai-spatial-planning/blob/main/data/onp_candidates.csv); [docs/decisions_2026-11-03.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/decisions_2026-11-03.md); [docs/swot_evidence_2026-11-04.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/swot_evidence_2026-11-04.md).

<a id="issue-2"></a>
## #2 — Экономика и специализация

**Результат:** Собраны география формальной экономики, структура ВРП, туризм, специализация пяти ТЭЗ и отраслевые SWOT. На основном слайде 6 оставлено пространственное объяснение, подробные экономические диаграммы сохранены в резерве. НДФЛ учитывается по месту налогового агента; административный турпоток, КСР и телеком-наблюдения не объединены в одну серию.

**Границы приемки:** Карта МСП по отраслям как отдельный итоговый слайд не предъявлена. Самостоятельное подтверждение соавтором экономических целевых ориентиров в комментариях отсутствует. Не заявляются рассчитанные экономические эффекты предварительного маршрута.

**Материалы:** [docs/validation_ndfl.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/validation_ndfl.md); [docs/swot_evidence_2026-11-04.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/swot_evidence_2026-11-04.md); [data/slides/map_05_economy.png](https://github.com/mfthesun/altai-spatial-planning/blob/main/data/slides/map_05_economy.png); [docs/final_presentation_2026-11-13.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/final_presentation_2026-11-13.md).

<a id="issue-3"></a>
## #3 — Транспорт и доступность

**Результат:** В репозитории сохранены расчеты, изохроны, карты ближайшей и Республиканской больниц. Дорожная карта показывает Р-256, региональные связи, узлы и международное продолжение A0306 в Монголии. Медицинская пара в Figma разделяет базу 56,8 % и сценарий 81,1 % в 120 мин; три точки помощи относятся к отдельному сценарию 92,2 → 95,3 % в 60 мин. Подписи и легенды согласованы.

**Границы приемки:** Это географическая модель, без учета кадров, мощности и временных закрытий дорог. Расхождение фактического и юридического адресов Усть-Коксинской РБ сохраняется в описании данных. OD-матрица локально отсутствует; текущий проход не является новым расчетом медицинского сценария.

**Материалы:** [docs/access_results.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/access_results.md); [docs/access_inputs.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/access_inputs.md); [data/access_results/time_to_hospital.csv](https://github.com/mfthesun/altai-spatial-planning/blob/main/data/access_results/time_to_hospital.csv); [data/slides/map_roads_course.png](https://github.com/mfthesun/altai-spatial-planning/blob/main/data/slides/map_roads_course.png); [docs/map_visual_audit_2026-11-13.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/map_visual_audit_2026-11-13.md).

<a id="issue-4"></a>
## #4 — Природный каркас и ограничения

**Результат:** Собрана карта ООПТ и рисков, отраслевые SWOT и связь с моделью. Показаны реальные полигоны соседних ООПТ, границы регионов/стран, подписи соседей. Площадь 24,7 % по объединению контуров не смешана с 25,6 % СТП. На карте отражена неполнота привязки списков подтопления и разрыва связи.

**Границы приемки:** Количественная емкость Катунской долины и юридический лимит застройки не рассчитаны; показатель нагрузки КСР не выдан за такую емкость. Точная геометрия лавинных/сейсмических зон отсутствует. Часть НП из списков рисков не привязана. Для этих выводов нужен источник и дальнейшее обоснование.

**Материалы:** [docs/ooppt_2026.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/ooppt_2026.md); [data/oopt/oopt_oczk_2026-10-28.geojson](https://github.com/mfthesun/altai-spatial-planning/blob/main/data/oopt/oopt_oczk_2026-10-28.geojson); [data/slides/map_07_constraints.png](https://github.com/mfthesun/altai-spatial-planning/blob/main/data/slides/map_07_constraints.png); [docs/swot_evidence_2026-11-04.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/swot_evidence_2026-11-04.md).

<a id="issue-5"></a>
## #5 — Жилье, ЖКХ и комфортная среда

**Результат:** Сохранены пять отдельных отраслевых слайдов 10–14 и связанные доктрина/мероприятия 17 и 20: все семь исходно защищенных слайдов остались отдельными. Исправлены компоновка инженерного слайда, обрезка текста и МВт, легенды и размеры Inter. Природный газ отделен от баллонного; оценки мастер-плана не представлены бюджетом концепции.

**Границы приемки:** Автоматическая проверка 102/102 охватывает только показатели скрипта, не все числа авторских объектов Figma. Полная независимая научная проверка всех авторских диаграмм и наличие воспроизводимых исходников каждой векторной карты не подтверждены. Последующее подтверждение автора не выдумывается.

**Материалы:** [docs/final_presentation_2026-11-13.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/final_presentation_2026-11-13.md); [docs/map_visual_audit_2026-11-13.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/map_visual_audit_2026-11-13.md); [docs/presentation_manifest_2026-11-13.json](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/presentation_manifest_2026-11-13.json); [docs/numbers_check.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/numbers_check.md).

<a id="issue-6"></a>
## #6 — Историко-культурное наследие

**Результат:** Собраны районная картограмма, историко-культурный каркас, SWOT и предварительный маршрут Анос → Калбак-Таш → Кокоря по действующим точкам показа. Для ЕГРОКН используется 288 объектов: 117 федеральных, 170 региональных и 1 местный. На карте выделена концентрация, а 71 из 117 федеральных ОКН относится к южному ядру. Отсутствующие координаты не выданы за точные места памятников.

**Границы приемки:** У 121 объекта нет точки, у трех не определен район; привязка к центру НП не заменяет границы территории памятника. Отдельная полная карта выявленных ОКН, юридические охранные зоны и проверенные площадочные кейсы конфликтов не завершены. Маршрут остается предварительным, без обещанного прироста турпотока или доходов.

**Материалы:** [data/okn/okn_by_mo_egrokn.csv](https://github.com/mfthesun/altai-spatial-planning/blob/main/data/okn/okn_by_mo_egrokn.csv); [data/slides/map_09_heritage.png](https://github.com/mfthesun/altai-spatial-planning/blob/main/data/slides/map_09_heritage.png); [docs/heritage_route_decisions.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/heritage_route_decisions.md); [docs/final_presentation_2026-11-13.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/final_presentation_2026-11-13.md).

<a id="issue-7"></a>
## #7 — Сборка презентации

**Результат:** Собран основной показ из 22 слайдов; 15 резервных скрыты, всего 37 объектов слайдов. Исходные номера сопоставлены с устойчивыми ID Figma. Согласованы разделы, страницы, навигация, подписи и типографика; проверены 20 карт, обновлены 13 растровых вставок и семь редактируемых легенд. Презентация принята Денисом для завершения текущего этапа.

**Границы приемки:** Figma — отдельный редактируемый документ: merge Git не воспроизводит автоматически изменения его холста. Командная сессия и полная содержательная приемка от имени всех соавторов не подтверждаются. Старые номера слайдов в телах Issues относятся к прежнему плану.

**Материалы:** [docs/final_presentation_2026-11-13.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/final_presentation_2026-11-13.md); [docs/presentation_manifest_2026-11-13.json](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/presentation_manifest_2026-11-13.json); [docs/map_visual_audit_2026-11-13.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/map_visual_audit_2026-11-13.md); [docs/evidence/2026-11-13/map-consistency-verification.json](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/evidence/2026-11-13/map-consistency-verification.json).

<a id="issue-8"></a>
## #8 — Доктрина, модель, мероприятия и флагманы

**Результат:** Собраны доктрина с горизонтами 2035/2050, пять ТЭЗ, узлы и три каркаса, межотраслевой план и связка флагманов «Чуйский путь + наследие + доступный юг». На модели сохранены реальные полигоны ООПТ и дорожные оси. Связь с Тывой и Хакасией обозначена как предложение сотрудничества; Шорский нацпарк отнесен к Кузбассу. Предварительный маршрут опирается на действующие музеи и точки показа.

**Границы приемки:** Полные паспорта мероприятий с ответственными, стоимостью, мощностями и операторами не разработаны. Межрегиональное согласование с командами соседей не подтверждено. Не заявляются новые бюджеты, сроки и гарантированные эффекты маршрута; медицинские охваты остаются сценарными.

**Материалы:** [docs/decisions_2026-11-03.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/decisions_2026-11-03.md); [docs/heritage_route_decisions.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/heritage_route_decisions.md); [docs/doctrine_draft.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/doctrine_draft.md); [data/model/map_model_draft.png](https://github.com/mfthesun/altai-spatial-planning/blob/main/data/model/map_model_draft.png); [docs/final_presentation_2026-11-13.md](https://github.com/mfthesun/altai-spatial-planning/blob/main/docs/final_presentation_2026-11-13.md).

## Проверки публикации

- `scripts/check_numbers.py`: 102/102 в охвате скрипта; контрольная подстановка дает ожидаемую ошибку (101/102, код 1).
- `scripts/check_map_context.py`: общие границы, стыковка дороги, порядок подписей, переносы и обработка дефекта тайла.
- Карты отрендерены и просмотрены; Figma-проверка и обзоры хранятся в `docs/evidence/2026-11-13/`. На этапе публикации повторный рендер всех карт и новый расчет OD не требуются: генераторы не менялись.
- Inter включен с OFL и контрольными суммами, без системной установки.
- Закрытие в GitHub сопровождается отдельным комментарием к каждой задаче после доступности отчета в main. Статус PR, merge и Issues подтверждается GitHub API; этот текст не заменяет проверку удаленного состояния.
