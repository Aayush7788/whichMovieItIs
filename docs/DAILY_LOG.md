## 25/5/26 
created the folder and files structure
setup git
and all setup of fastapi backend, react frontend and postgresql with pgvector database 


## 26/5/26
implemented backend health endpoint, for fastapi
and database health endpoint with pydantic, psycopg

learn the database connetion in postgresql with docker with fastapi

## 28-29/5/26
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

- cmu_data_processing
metadata records loaded: 81741
metadata path exits: True
plot path exits: True
limit: 500
output: data\processed\cmu_movies_sample.jsonl

- join cmu metadata with plots for processing
metadata records loaded: 81741
plot record loaded: 42306
joined records: 42207

- filter cmu movie for english sample

records built: 500
first title: The Hunger Games

## 30/5/26
- make sure that all ports and password are consistent
- created movie table
movies table ready
- loaded cmu sample data into database
movies loaded: 500
- added basic movie database search on sample
(.venv) D:\WhichMovieItIs> python.exe -c "from backend.app.services.search import search_movies; print([m['title'] for m in search_movies('Hunger Games', 3)])"
['The Hunger Games']
- added the search (/search) api endpoint

## 1/6/26
- make the frontend 
- connected the search api to the frontend
(![bacis frontend for the checking search api](image.png))