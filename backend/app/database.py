import sqlite3

DATABASE_NAME = "agrogestor.db"

def get_db():
    """ Abre e fecha a conexão com o banco de dados a cada requisição """
    conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;") # Ativa integridade do banco
    try:
        yield conn
    finally:
        conn.close()