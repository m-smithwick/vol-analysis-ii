#run screener to create the screened list which then is pasted in manually to screened.txt thede are candidates
# that must now pass vol_analysis


python populate_cache.py  -d 5 -f ticker_lists/indices.txt
python populate_cache.py  -d 5 -f ticker_lists/sector_etfs.txt
python populate_cache.py  -d 5 -f ticker_lists/screened.txt


python vol_analysis.py  --period 12mo --chart-backend plotly --save-charts --file ticker_lists/screened.txt   
python vol_analysis.py  --period 12mo --chart-backend plotly --save-charts --file ticker_lists/ibd50-nov-29.txt 


python batch_backtest.py  -p 12mo  --no-individual-reports -f ticker_lists/passed.txt

python analyze_professional_metrics.py --csv backtest_results/LOG_FILE_passed_12mo_conservative_20251211_215934.csv
