"""check_numbers.py — пересчитывает числа из задач команды (.github/tasks) по файлам репозитория.

Запуск:  python3 scripts/check_numbers.py            # проверка
         python3 scripts/check_numbers.py --control  # контроль: подставляет заведомо неверное значение, проверка ОБЯЗАНА упасть
Код выхода: 0 — все числа совпали; 1 — есть расхождения.
Числа из внешних источников (веб, тексты СТП и мастер-плана вне репозитория) здесь не проверяются — см. docs/numbers_check.md.
"""
import sys
from pathlib import Path
import pandas as pd

R = Path(__file__).resolve().parents[1]
def csv(p):
    for sep in (';', ','):
        d = pd.read_csv(R / p, sep=sep, encoding='utf-8-sig')
        if d.shape[1] > 1:
            return d
    raise ValueError(p)
mo = csv('data/dataset_v4/mo_summary.csv').set_index('mo')
ndfl = csv('data/dataset_v4/ndfl_mo_summary.csv').set_index('mo')
onp = csv('data/onp_candidates.csv')
okn = csv('data/stp_extracted/okn/okn_by_mo.csv').set_index('МО')
f1 = csv('data/stp_extracted/chs/flood_zone_settlements_1.csv')
f2 = csv('data/stp_extracted/chs/flood_zone_settlements_2.csv')
fh = csv('data/stp_extracted/chs/flood_history.csv')
cal = csv('relief/calibration_pairs.csv')
rows = lambda d: d[pd.to_numeric(d.iloc[:, 0], errors='coerce').notna()]  # строки таблицы с порядковым номером

pop = mo['Население 1.01.2025, чел.']
ksr = mo['Размещено в КСР, чел. (2025)']
inc = ndfl['То же на жителя в месяц, 2025, руб.']
ga2014 = fh[fh.astype(str).apply(lambda r: 'Горно-Алтайск' in ' '.join(map(str, r)) and '2014' in ' '.join(map(str, r)), axis=1)].iloc[0]

# (задача, утверждение, пересчитанное значение, заявленное значение, допуск)
CHECKS = [
    ('01', 'кандидатов в ОНП', len(onp), 37, 0),
    ('01', 'доля населения в ОНП, %', 100 * onp.pop_2025_est.sum() / pop.sum(), 75, 1),
    ('01', 'населённых пунктов в settlements.csv', len(csv('data/dataset_v3/settlements.csv')), 247, 0),
    ('02', 'доля Маймы и Чемала в размещённых, %', 100 * ksr[['Майминский район', 'Чемальский район']].sum() / ksr.sum(), 61, 0.5),
    ('02', 'размещено в КСР 2025, тыс.', ksr.sum() / 1000, 634, 0.5),
    ('02', 'доход на жителя Майминский, тыс. руб./мес', inc['Майминский район'] / 1000, 37.4, 0.05),
    ('02', 'доход на жителя Усть-Канский, тыс. руб./мес', inc['Усть-Канский район'] / 1000, 8.9, 0.05),
    ('02', 'разрыв Майма / Усть-Кан, раз', inc['Майминский район'] / inc['Усть-Канский район'], 4.2, 0.05),
    ('03', 'маршрутов калибровки', len(cal), 11, 0),
    ('03', 'ГА → Кош-Агач, мин', cal.loc[0, 'ref_min'], 369, 0),
    ('03', 'ГА → Кош-Агач, км', cal.loc[0, 'ref_km'], 452, 0),
    ('03', 'сёл с разрывом связи (табл. 1.6), строк с номером', rows(f2).shape[0], 36, 0),
    ('03', 'население с разрывом связи, сумма строк', rows(f2)['Количество населения'].astype(float).sum(), 12061, 0),
    ('03', 'население с разрывом связи, строка «Итого»', float(f2.iloc[-1]['Количество населения']), 12061, 0),
    ('04', 'сёл в зоне подтопления (табл. 1.5)', int(str(f1.iloc[-1]['Населенный пункт']).split()[0]), 41, 0),
    ('04', 'население в зоне подтопления', float(f1.iloc[-1]['Количество населения']), 13475, 0),
    ('04', 'ГА 30.05.2014: домов', float(ga2014['Кол-во домов']), 3417, 0),
    ('04', 'ГА 30.05.2014: человек', float(ga2014['Кол-во человек в домах']), 17068, 0),
    ('04', 'Чемальский: размещено на 1 жителя', mo.loc['Чемальский район', 'Размещено в КСР на 1 жителя'], 15.4, 0.05),
    ('06', 'федеральных ОКН', okn.loc['Итого', 'федеральные'], 118, 0),
    ('06', 'региональных ОКН', okn.loc['Итого', 'региональные'], 170, 0),
    ('06', 'выявленных (приказы)', okn.loc['Итого', 'выявленные (приказы)'], 318, 0),
    ('06', 'выявленных (перечень 2018)', okn.loc['Итого', 'выявленные (перечень 2018)'], 2130, 0),
    ('06', 'федеральных ОКН в Онгудае и Кош-Агаче', okn.loc[['Онгудайский', 'Кош-Агачский'], 'федеральные'].sum(), 72, 0),
]

if '--control' in sys.argv:          # контроль: заявляем 38 кандидатов вместо 37 — проверка обязана упасть
    CHECKS[0] = CHECKS[0][:3] + (38, 0)

bad = 0
for task, what, got, claimed, tol in CHECKS:
    ok = abs(float(got) - claimed) <= tol
    bad += not ok
    print(f"{'OK  ' if ok else 'FAIL'} [{task}] {what}: в данных {float(got):.3f}, в тексте {claimed}")
print(f"\nИТОГ: {len(CHECKS) - bad} из {len(CHECKS)} совпали" + ("" if not bad else f", расхождений: {bad}"))
sys.exit(1 if bad else 0)
