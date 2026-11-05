"""Generate Power BI PBIP, TMSL semantic model, PBIR report and DAX reference."""
from pathlib import Path
import argparse
import json
import hashlib

ROOT = Path(__file__).resolve().parent
SCHEMA = 'https://developer.microsoft.com/json-schemas/fabric/'


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding='utf-8')


def build(data_folder='CHANGE_ME'):
    types = {
        'FactSales': {'series_key':'string','dt':'dateTime','split':'string','stockout_key':'int64','sale_amount':'double','stock_hour6_22_cnt':'double','records':'int64','stockout_records':'int64'},
        'FactForecast': {'series_key':'string','dt':'dateTime','split':'string','stockout_key':'int64','model_key':'string','sale_amount':'double','prediction':'double','error':'double','abs_error':'double'},
        'DimDate': {'dt':'dateTime','weekday':'int64','weekday_name':'string','month':'string'},
        'DimProduct': {'series_key':'string','store_id':'int64','product_id':'int64','product_label':'string'},
        'DimModel': {'model_key':'string','model_name':'string'},
        'DimSplit': {'split':'string'}, 'DimStockout': {'stockout_key':'int64','stockout_label':'string'},
    }
    measures = {
        'Observed Sales': ('SUM(FactSales[sale_amount])','#,0.00'),
        'Observed Records': ('SUM(FactSales[records])','#,0'),
        'Stockout Share': ('DIVIDE(SUM(FactSales[stockout_records]), SUM(FactSales[records]))','0.0%'),
        'Model WAPE': ('IF(HASONEVALUE(DimModel[model_key]), DIVIDE(SUM(FactForecast[abs_error]), SUM(FactForecast[sale_amount])))','0.0%'),
        'Model Bias': ('IF(HASONEVALUE(DimModel[model_key]), DIVIDE(SUM(FactForecast[error]), SUM(FactForecast[sale_amount])))','0.0%'),
        'Adjusted WAPE': ('CALCULATE([Model WAPE], DimModel[model_key] = "mean_7_weekday")','0.0%'),
        'Baseline WAPE': ('CALCULATE([Model WAPE], DimModel[model_key] = "mean_7")','0.0%'),
        'WAPE Improvement pp': ('([Baseline WAPE] - [Adjusted WAPE]) * 100','0.00'),
        'Evaluation Actual Sales': ('CALCULATE(SUM(FactForecast[sale_amount]), DimModel[model_key] = "mean_7")','#,0.00'),
        'Baseline Forecast': ('CALCULATE(SUM(FactForecast[prediction]), DimModel[model_key] = "mean_7")','#,0.00'),
        'Adjusted Forecast': ('CALCULATE(SUM(FactForecast[prediction]), DimModel[model_key] = "mean_7_weekday")','#,0.00'),
    }
    model = {'name':'RetailAnalytics','compatibilityLevel':1567,'model':{
        'culture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3',
        'dataAccessOptions':{'legacyRedirects':True,'returnErrorValuesAsNull':True},
        'expressions':[],
        'tables':[], 'relationships':[]}}
    for table, columns in types.items():
        mtypes = {'string':'type text','int64':'Int64.Type','double':'type number','dateTime':'type date'}
        typed = ', '.join('{"'+c+'", '+mtypes[t]+'}' for c,t in columns.items())
        file_path = (data_folder.rstrip('/\\') + '/' + table + '.csv').replace('"', '""')
        query = f'let\n Source = Csv.Document(File.Contents("{file_path}"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),\n Typed = Table.TransformColumnTypes(Headers, {{{typed}}}, "en-US")\nin Typed'
        definition = {'name':table,'columns':[{'name':c,'dataType':t,'sourceColumn':c,'summarizeBy':'none',**({'formatString':'yyyy-MM-dd'} if t=='dateTime' else {})} for c,t in columns.items()],
                      'partitions':[{'name':table,'mode':'import','source':{'type':'m','expression':query.splitlines()}}]}
        if table == 'FactForecast':
            definition['measures'] = [{'name':n,'expression':e,'formatString':f} for n,(e,f) in measures.items()]
        model['model']['tables'].append(definition)
    for fact in ['FactSales','FactForecast']:
        for dim, key in [('DimDate','dt'),('DimProduct','series_key'),('DimSplit','split'),('DimStockout','stockout_key')]:
            model['model']['relationships'].append({'name':fact+'_'+dim,'fromTable':fact,'fromColumn':key,'toTable':dim,'toColumn':key,'fromCardinality':'many','toCardinality':'one','crossFilteringBehavior':'oneDirection'})
    model['model']['relationships'].append({'name':'Forecast_Model','fromTable':'FactForecast','fromColumn':'model_key','toTable':'DimModel','toColumn':'model_key','fromCardinality':'many','toCardinality':'one','crossFilteringBehavior':'oneDirection'})
    semantic = ROOT / 'Retail.SemanticModel'
    report = ROOT / 'Retail.Report'
    write(semantic / 'definition.pbism', {'$schema':SCHEMA+'item/semanticModel/definitionProperties/1.0.0/schema.json','version':'1.0','settings':{}})
    write(semantic / 'model.bim',model)
    write(ROOT / 'Retail.pbip',{'$schema':SCHEMA+'pbip/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':'Retail.Report'}}],'settings':{'enableAutoRecovery':True}})
    write(report / 'definition.pbir',{'$schema':SCHEMA+'item/report/definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':'../Retail.SemanticModel'}}})
    definition = report / 'definition'
    write(definition/'version.json',{'$schema':SCHEMA+'item/report/definition/versionMetadata/1.0.0/schema.json','version':'2.0.0'})
    write(definition/'report.json',{'$schema':SCHEMA+'item/report/definition/report/3.1.0/schema.json','themeCollection':{}})
    pages = []
    def page(name):
        pid=hashlib.sha1(name.encode()).hexdigest()[:20]; pages.append(pid)
        path=definition/'pages'/pid
        write(path/'page.json',{'$schema':SCHEMA+'item/report/definition/page/2.0.0/schema.json','name':pid,'displayName':name,'displayOption':'FitToPage','height':720,'width':1280})
        return path
    def field(table, property, measure=False):
        return {('Measure' if measure else 'Column'):{'Expression':{'SourceRef':{'Entity':table}},'Property':property}}
    def col(table,name):return (table,name,False)
    def met(name):return ('FactForecast',name,True)
    def visual(path,title,kind,roles,x,y,w,h):
        vid=hashlib.sha1((path.name+title).encode()).hexdigest()[:20]
        query={role:{'projections':[{'field':field(*item),'queryRef':item[0]+'.'+item[1],'nativeQueryRef':item[1]} for item in items]} for role,items in roles.items()}
        config={'visualType':kind,'query':{'queryState':query},'drillFilterOtherVisuals':True,
                'visualContainerObjects':{'title':[{'properties':{'show':{'expr':{'Literal':{'Value':'true'}}},'text':{'expr':{'Literal':{'Value':"'"+title+"'"}}}}}]}}
        write(path/'visuals'/vid/'visual.json',{'$schema':SCHEMA+'item/report/definition/visualContainer/2.7.0/schema.json','name':vid,'position':{'x':x,'y':y,'width':w,'height':h,'z':0,'tabOrder':0},'visual':config})
    def slicers(path):
        for i,(title,table,column) in enumerate([('Period — choose validation or test','DimSplit','split'),('Product','DimProduct','product_label'),('Date','DimDate','dt'),('Daytime stockout status','DimStockout','stockout_label')]):
            visual(path,title,'slicer',{'Values':[col(table,column)]},20+i*315,10,305,105)
    overview=page('Sales and forecast overview');slicers(overview)
    for i,(title,name) in enumerate([('Observed sales (normalized)','Observed Sales'),('Daytime stockout share','Stockout Share'),('Adjusted WAPE','Adjusted WAPE'),('Baseline WAPE','Baseline WAPE')]):
        visual(overview,title,'card',{'Values':[met(name)]},20+i*315,125,305,100)
    visual(overview,'Observed daily sales — normalized','lineChart',{'Category':[col('DimDate','dt')],'Y':[met('Observed Sales')]},20,240,610,450)
    visual(overview,'Evaluation only — daily updated one-day forecasts','lineChart',{'Category':[col('DimDate','dt')],'Y':[met('Evaluation Actual Sales'),met('Baseline Forecast'),met('Adjusted Forecast')]},650,240,610,450)
    performance=page('Forecast performance');slicers(performance)
    visual(performance,'WAPE by model — lower is better','clusteredBarChart',{'Category':[col('DimModel','model_name')],'Y':[met('Model WAPE')]},20,130,600,250)
    visual(performance,'Signed bias by model','clusteredBarChart',{'Category':[col('DimModel','model_name')],'Y':[met('Model Bias')]},650,130,610,250)
    visual(performance,'Product-level evaluation and stockout profile','tableEx',{'Values':[col('DimProduct','product_label'),met('Observed Sales'),met('Stockout Share'),met('Baseline WAPE'),met('Adjusted WAPE'),met('WAPE Improvement pp')]},20,400,1240,290)
    write(definition/'pages'/'pages.json',{'$schema':SCHEMA+'item/report/definition/pagesMetadata/1.0.0/schema.json','pageOrder':pages,'activePageName':pages[0]})
    (ROOT/'measures.dax').write_text('\n\n'.join(n+' =\n'+e for n,(e,_) in measures.items()),encoding='utf-8')
    print('Generated Power BI project:',ROOT/'Retail.pbip')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--data-folder',default='CHANGE_ME')
    args=parser.parse_args();build(args.data_folder)
