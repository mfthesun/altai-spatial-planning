import duckdb, sys
con=duckdb.connect()
STD={'indicator_section_code','indicator_section','indicator_code','indicator_name','region_id','region_name','mun_level','mun_district','municipality','oktmo','mun_type','mun_type_oktmo','oktmo_stable','oktmo_history','oktmo_year_from','oktmo_year_to','year','indicator_value','indicator_unit','indicator_period','comment'}
for p in sys.argv[1:]:
    src = f"read_csv('{p}', delim=';', header=true, all_varchar=true)" if p.endswith('.csv') else f"'{p}'"
    cols=[r[0] for r in con.sql(f"describe select * from {src}").fetchall()]
    dims=[c for c in cols if c not in STD]
    dexpr = "concat_ws('|',"+",".join(f"coalesce({c}::varchar,'')" for c in dims)+")" if dims else "''"
    print('=====',p,'dims:',dims)
    print(con.sql(f"""select indicator_code, any_value(indicator_name)[:85] n, count(distinct {dexpr}) nd, min(year::int) y0, max(year::int) y1,
     count(distinct case when mun_level like '%верхнего%' then oktmo end) n_up, any_value(indicator_unit)[:25] u
     from {src} where region_name='Республика Алтай' group by 1 order by 1""").df().to_string())
