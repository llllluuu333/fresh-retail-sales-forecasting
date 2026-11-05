"""全量报告：按门店、日期、缺货状态预聚合，保留逐商品误差总和。"""
from pathlib import Path
import pandas as pd
from common import output_dir

folder = output_dir()
data = pd.read_csv(folder/'powerbi_full'/'full_store_day_model.csv', parse_dates=['day'])
data['series_key'] = data['store_id'].astype(str)
data = data.rename(columns={'day':'dt','observed_sales':'sale_amount','predicted_sales':'prediction',
                            'signed_error':'error','absolute_error':'abs_error'})
data['model_key'] = data['model'].map({'7-day mean':'mean_7', '7-day mean + weekday':'mean_7_weekday'})
keys = ['series_key','dt','split','stockout_key']
if data['model_key'].isna().any() or data.duplicated(keys + ['model_key']).any():
    raise ValueError('模型标识缺失或重复。')
actual = data.loc[data['model_key']=='mean_7'].copy()
if data.groupby(keys).size().ne(2).any():
    raise ValueError('每个门店日期缺货组都应有两个模型。')
actual['stock_hour6_22_cnt'] = actual['stockout_hours']  # 当前门店日期缺货组的小时总和。
sales = actual[keys+['sale_amount','stock_hour6_22_cnt','records','stockout_records']]
forecast = data[keys+['model_key','sale_amount','prediction','error','abs_error']]
products = actual[['series_key','store_id']].drop_duplicates().copy()
products['product_id'] = -1
products['product_label'] = 'Store ' + products['store_id'].astype(str) + ' / all products'
dates = pd.DataFrame({'dt':pd.date_range(data.dt.min(), data.dt.max())})
dates['weekday'] = dates.dt.dt.day_of_week
dates['weekday_name'] = dates.dt.dt.day_name()
dates['month'] = dates.dt.dt.strftime('%Y-%m')
frames = {'FactSales':sales,'FactForecast':forecast,'DimProduct':products,'DimDate':dates,
          'DimSplit':pd.DataFrame({'split':['validation','test']}),
          'DimModel':pd.DataFrame({'model_key':['mean_7','mean_7_weekday'], 'model_name':['7-day mean','7-day mean + weekday']}),
          'DimStockout':pd.DataFrame({'stockout_key':[0,1],'stockout_label':['No daytime stockout','Daytime stockout']})}
target=folder/'powerbi_full_model';target.mkdir(parents=True,exist_ok=True)
for name, frame in frames.items(): frame.to_csv(target/(name+'.csv'),index=False,encoding='utf-8-sig',date_format='%Y-%m-%d')
print('全量看板表：', {name:len(frame) for name,frame in frames.items()})
print('目录：',target)
