## 25/5/26 
created the folder and files structure
setup git
and all setup of fastapi backend, react frontend and postgresql with pgvector database 


## 26/5/26
implemented backend health endpoint, for fastapi
and database health endpoint with pydantic, psycopg

learn the database connetion in postgresql with docker with fastapi

## 28/5/26
output in cmu inspection, 

movie metadata rows:81741
plot summary rows: 42306
coreNlp files:42306

movie metadata inspection
{'rows': 81741, 'unique_wikipedia_ids': 81741, 'column_counts': {9: 81741}, 'missing_fields': {'box_office_revenue': 73340, 'runtime': 20450, 'release_date': 6902}}

- join the data

join inspection
joined ids: 42207
plot ids without metadata: 99
metadata ids without plot: 39534
first unmatched plot ids: ['10083650', '10153756', '10873999', '12651534', '13255982', '133671', '14481527', '14851642', '16758721', '16803295']