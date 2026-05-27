import psycopg
from .config import settings

def get_connection():
    return psycopg.connect(settings.build_database_url())
