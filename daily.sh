python populate_cache.py  -d 5 -f ticker_lists/indices.txt
python populate_cache.py  -d 5 -f ticker_lists/sector_etfs.txt
python populate_cache.py  -d 5 -f ticker_lists/ibd50-nov-29.txt


python vol_analysis.py  --period 12mo --chart-backend plotly --save-charts --file ticker_lists/ibd50-nov-29.txt   
