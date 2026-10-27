"""
build_ndfl.py — налоговая отчётность ФНС по НДФЛ (формы 5-НДФЛ и 7-НДФЛ) для Республики Алтай
и сравнения с Тывой и Хакасией. Источник: «Если быть точным», набор ndfl v20260722,
региональные архивы by_regions/data_ndfl_155_{04,17,19}_v20260722.zip.

Правила отбора (по итогам разведки):
  * годовые значения: indicator_period = 'Значение показателя за год';
  * итоговые разрезы: income/individual_type/tax_rate/deduction ∈ {'Всего','CD'};
  * tax_authority = 'Всего';
  * у одного (объект, форма, показатель, год, источник) бывает несколько версий отчёта →
    берётся последняя по report_date;
  * для 5-НДФЛ источники «Приложение № 2 к декларации по налогу на прибыль» и «2-НДФЛ с признаком «2»»
    (доходы, с которых налог не удержан) — не основной ряд, исключаются;
  * 7-НДФЛ по районам (по месту учёта налогового агента): полный охват МО только с 2022 г.;
    до 2022 г. опубликованы почти одни нули (данные скрыты) → не используются;
  * 2025 г.: Турочак и Чоя идут под новыми ОКТМО 84525000 / 84545000 → переназначаются на старые;
  * Чемальский район 2024: 2 налоговых агента и 0 руб. дохода — явный сбой публикации → пропуск (NaN).
"""
import os
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd

RAW = Path(os.environ.get('ALTAI_RAW', str(Path(__file__).resolve().parents[2] / 'data' / 'raw')))
OUT = Path(os.environ.get('ALTAI_OUT', str(Path(__file__).resolve().parents[2] / 'data' / 'dataset_v3')))
NDFL = RAW / 'ndfl'
NEWCODE = {'84525000': '84625000', '84545000': '84645000'}

c = duckdb.connect()
c.sql(f"""create view a as select * from read_parquet(['{NDFL}/r04/*.parquet','{NDFL}/r17/*.parquet','{NDFL}/r19/*.parquet'], union_by_name=true)""")

BASE = """indicator_period='Значение показателя за год'
 and income in ('Всего','CD') and individual_type in ('Всего','CD')
 and coalesce(tax_rate,'CD') in ('Всего','CD') and coalesce(deduction,'CD') in ('Всего','CD')
 and tax_authority='Всего'
 and source not like 'Приложение%' and source <> '2-НДФЛ с признаком «2»'"""


def pick(where, codes):
    q = f"""select index_form form, indicator_code code, any_value(indicator_name) name, object_level lvl, report_type rt,
               object_oktmo oktmo, any_value(object_name) obj, report_region_name region, year, source,
               arg_max(indicator_value, report_date) value, max(report_date) report_date
            from a where {BASE} and ({where}) and indicator_code in ({','.join("'" + x + "'" for x in codes)})
            group by all"""
    return c.sql(q).df()


LOG = []

# ---------- регионы: 2016–2025 ----------
R7 = pick("object_level='Субъект РФ' and report_type='Свод' and index_form='7-НДФЛ'",
          ['Y777000001', 'Y777000006', 'Y777000013', 'Y777000020'])
R5 = pick("object_level='Субъект РФ' and report_type='Свод' and index_form='5-НДФЛ'", ['Y777000028', 'Y777000006'])
for nm, d in [('7-НДФЛ', R7), ('5-НДФЛ', R5)]:
    dup = d.duplicated(['code', 'region', 'year']).sum()
    LOG.append(f'регионы {nm}: строк {len(d)}, дублей после отбора {dup}')
    assert dup == 0, d[d.duplicated(['code', 'region', 'year'], keep=False)]

reg = (pd.concat([R7.assign(k='7_' + R7.code), R5.assign(k='5_' + R5.code)])
       .pivot_table(index=['region', 'year'], columns='k', values='value').reset_index())
reg = reg.rename(columns={'7_Y777000001': 'agents', '7_Y777000006': 'income_7', '7_Y777000013': 'tax_7',
                          '7_Y777000020': 'records_7', '5_Y777000028': 'earners_5', '5_Y777000006': 'income_5'})
pop = c.sql(f"""select object_name region, year, avg(indicator_value)*1000 pop from '{RAW}/rc.parquet'
                where indicator_code='Y477110461' and object_name in ('Республика Алтай','Республика Тыва','Республика Хакасия')
                group by all""").df()
# население на 1 января года t = оценка на конец года t-1 (rc есть до конца 2023 г. → покрывает 2017–2024);
# для РА на 1.01.2025 — 210 095 чел. (Росстат, сводный датасет v3); для Тывы и Хакасии 2025 — нет данных
pop['year'] = pop.year + 1
pop = pd.concat([pop, pd.DataFrame([{'region': 'Республика Алтай', 'year': 2025, 'pop': 210095}])])
pop = pop.rename(columns={'pop': 'pop_avg'})
reg = reg.merge(pop[['region', 'year', 'pop_avg']], on=['region', 'year'], how='left')
reg['income_7_per_cap_month'] = reg.income_7 / reg.pop_avg / 12
reg['tax_7_per_cap'] = reg.tax_7 / reg.pop_avg
reg['earners_share'] = reg.earners_5 / reg.pop_avg
reg['income_per_earner_month'] = reg.income_5 / reg.earners_5 / 12
reg['agents_per_1000'] = reg.agents / reg.pop_avg * 1000
# Тыва 2018: доход по 7-НДФЛ 18,3 млрд против 27,4 (2017) и 36,7 (2019) — сбой публикации
bad = (reg.region == 'Республика Тыва') & (reg.year == 2018)
reg.loc[bad, ['income_7', 'tax_7', 'income_7_per_cap_month', 'tax_7_per_cap']] = np.nan
LOG.append('Тыва 2018, 7-НДФЛ: доход и налог исключены (выброс: 18,3 млрд при 27,4 в 2017 и 36,7 в 2019)')
reg = reg.sort_values(['region', 'year'])

# ---------- районы РА ----------
M7 = pick("report_region_name='Республика Алтай' and report_type='МО' and index_form='7-НДФЛ' and year>=2022 and object_level<>'Субъект РФ'",
          ['Y777000001', 'Y777000006', 'Y777000013', 'Y777000020'])
M7['oktmo'] = M7.oktmo.replace(NEWCODE)
M7 = M7[M7.oktmo.str.match(r'^846\d{2}000$|^84701000$')]
dup = M7.duplicated(['code', 'oktmo', 'year']).sum(); LOG.append(f'МО 7-НДФЛ 2022+: строк {len(M7)}, дублей {dup}'); assert dup == 0
mo = M7.pivot_table(index=['oktmo', 'year'], columns='code', values='value').reset_index().rename(columns={
    'Y777000001': 'agents', 'Y777000006': 'income_7', 'Y777000013': 'tax_7', 'Y777000020': 'records_7'})
chem = (mo.oktmo == '84643000') & (mo.year == 2024)
mo.loc[chem, ['agents', 'income_7', 'tax_7', 'records_7']] = np.nan
LOG.append('Чемальский район 2024: 2 агента и 0 руб. — сбой публикации, значения исключены')

M5 = pick("report_region_name='Республика Алтай' and report_type='МО' and index_form='5-НДФЛ' and year=2024 and object_level like 'Муниц%'",
          ['Y777000028'])
e5 = M5.set_index('oktmo').value.rename('earners_5_2024')
# разрезы 5-НДФЛ 2024 по типу получателя
seg = c.sql("""select object_oktmo oktmo, individual_type it, arg_max(indicator_value, report_date) v from a
   where report_region_name='Республика Алтай' and report_type='МО' and index_form='5-НДФЛ' and year=2024 and indicator_code='Y777000028'
   and object_level like 'Муниц%' and indicator_period='Значение показателя за год' and income in ('Всего','CD')
   and coalesce(tax_rate,'CD') in ('Всего','CD') and tax_authority='Всего' group by all""").df()
seg = seg.pivot_table(index='oktmo', columns='it', values='v')
foreign = seg[[x for x in seg.columns if x.startswith('Иностранные')][0]].rename('foreign_2024')
ip = seg[[x for x in seg.columns if x.startswith('ИП')][0]].rename('ip_2024')

# население и ФОТ из сводного датасета
P = pd.read_csv(OUT / 'mo_panel_long.csv', sep=';', dtype={'oktmo': str})
popm = P[P.indicator == 'Численность постоянного населения на 1 января'][['oktmo', 'year', 'value']].rename(columns={'value': 'pop_jan'})
fot = P[P.indicator == 'Фонд заработной платы работников организаций'][['oktmo', 'year', 'value', 'unit']]
LOG.append(f"ФОТ: единица {fot.unit.unique().tolist()}")
fot = fot[['oktmo', 'year', 'value']].rename(columns={'value': 'fot_rosstat'})
names = P.drop_duplicates('oktmo').set_index('oktmo').mo
mo = mo.merge(popm, on=['oktmo', 'year'], how='left').merge(fot, on=['oktmo', 'year'], how='left')
mo['mo'] = mo.oktmo.map(names)
mo['income_7_per_cap_month'] = mo.income_7 / mo.pop_jan / 12
mo['tax_7_per_cap'] = mo.tax_7 / mo.pop_jan
mo['agents_per_1000'] = mo.agents / mo.pop_jan * 1000
mo['fot_to_ndfl'] = (mo.fot_rosstat * 1000) / mo.income_7   # ФОТ в тыс. руб.
mo = mo.sort_values(['oktmo', 'year'])

# проверка: сумма МО против свода по региону
chk = mo.groupby('year')[['income_7', 'tax_7', 'agents']].sum(min_count=1)
regA = reg[reg.region == 'Республика Алтай'].set_index('year')[['income_7', 'tax_7', 'agents']]
cmp = (chk / regA.loc[chk.index]).round(3)
LOG.append('Доля суммы МО в своде по РА (7-НДФЛ):\n' + cmp.to_string())

# сводка по МО
last = mo[mo.year == 2025].set_index('oktmo'); y22 = mo[mo.year == 2022].set_index('oktmo')
summ = pd.DataFrame({
    'mo': last.mo,
    'Доходы, выплаченные агентами МО, 2025, млн руб.': (last.income_7 / 1e6).round(1),
    'То же на жителя в месяц, 2025, руб.': last.income_7_per_cap_month.round(0),
    'Рост доходов агентов МО 2022→2025, %': ((last.income_7 / y22.income_7 - 1) * 100).round(1),
    'НДФЛ исчисленный агентами МО, 2025, млн руб.': (last.tax_7 / 1e6).round(1),
    'НДФЛ на жителя, 2025, руб.': last.tax_7_per_cap.round(0),
    'Налоговых агентов на 1000 жит., 2025': last.agents_per_1000.round(1),
    'ФОТ Росстата / доходы по 7-НДФЛ, 2025': last.fot_to_ndfl.round(2),
    'Получателей доходов (5-НДФЛ), 2024': e5,
    'Иностранцев среди получателей, 2024': foreign,
    'ИП и главы КФХ среди получателей, 2024': ip,
})
p24 = popm[popm.year == 2024].set_index('oktmo').pop_jan
summ['Получатели доходов на 100 жит. (по месту учёта агента), 2024'] = (summ['Получателей доходов (5-НДФЛ), 2024'] / p24 * 100).round(1)
summ = summ.reset_index().rename(columns={'index': 'oktmo'})

OUT.mkdir(exist_ok=True, parents=True)
mo.to_csv(OUT / 'ndfl_mo_2022_2025.csv', sep=';', index=False, encoding='utf-8-sig')
reg.to_csv(OUT / 'ndfl_regions_2016_2025.csv', sep=';', index=False, encoding='utf-8-sig')
summ.to_csv(OUT / 'ndfl_mo_summary.csv', sep=';', index=False, encoding='utf-8-sig')
(OUT / 'ndfl_build_log.txt').write_text('\n'.join(LOG), encoding='utf-8')
print('\n'.join(LOG))
pd.set_option('display.width', 250)
print(summ.to_string())
print(reg[['region', 'year', 'income_7_per_cap_month', 'tax_7_per_cap', 'earners_share', 'income_per_earner_month', 'agents_per_1000']].round(3).to_string())
