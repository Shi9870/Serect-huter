import sqlite3
import os

class KeywordDB():
    
    def __init__(self, db_name = "Keyword.db"):

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(base_dir,db_name)


        self._create_table()

    def _get_connection(self):

        return sqlite3.connect(self.db_path)
        
    def _create_table(self):
            
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT UNIQUE NOT NULL,
        category TEXT DEFAULT 'General'
        );
        """
        with self._get_connection() as conn:
            conn.execute(create_table_sql)
    
    def add_keyword(self,word):
        clean_word = word.strip().lower()
        sql = "INSERT OR IGNORE INTO keywords (word) VALUES (?)"

        try:
            with self._get_connection() as conn:
                conn.execute(sql,(clean_word,))
            return True
        except Exception as e:
            print(f"Fail to insert:{e}")

            return False
    def delete_keyword(self,word):
        clean_word = word.strip().lower()
        sql = "DELETE FROM keywords WHERE word = ?"

        with self._get_connection() as conn:
            conn.execute(sql,(clean_word,))

    def get_all_keyword(self):

        sql = "SELECT word FROM keywords ORDER BY word ASC"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)

            return [row[0] for row in cursor.fetchall()]
        

if __name__ =="__main__":
    db = KeywordDB()
    db.add_keyword("password")
    db.add_keyword("api_key")
    db.delete_keyword("password")
    print("keyword list :", db.get_all_keyword())

        

