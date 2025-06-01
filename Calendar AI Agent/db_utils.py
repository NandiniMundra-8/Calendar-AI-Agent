import sqlite3

def get_email_by_name(name, db_path="contacts.db"):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Use LIKE for partial match (case-insensitive)
        cursor.execute("SELECT email FROM contacts WHERE name LIKE ?", (f"%{name}%",))
        result = cursor.fetchone()
        
        conn.close()

        if result:
            return result[0]
        return None
    except Exception as e:
        print("Database error:", e)
        return None
