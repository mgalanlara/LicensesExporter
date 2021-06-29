import pandas as pd

#url = "http://ucolic02.ctx.uco.es:5054/goforms/rlmstat"
url = "http://ucolic02.ctx.uco.es:5054"

features_to_include = ["Quadro-Virtual-DWS","GRID-Virtual-Apps"]
label_feature_name = "Nombre"
label_total = "Licencias"
label_in_use = "Estado.3"
table_index = 0

all_tables = pd.read_html(url)
print(all_tables)
table = all_tables[table_index]


for index,row in table.iterrows():
    print(row.dtype)
    print(row)
    pass