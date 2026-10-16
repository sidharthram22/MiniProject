import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'nptel.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Create students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            accuracy TEXT DEFAULT '85.0%',
            tests_taken INTEGER DEFAULT 0,
            avg_rating TEXT DEFAULT '5.0/5',
            streak_days INTEGER DEFAULT 1,
            today_focus TEXT DEFAULT 'Data Structures • Easy',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create courses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE NOT NULL
        )
    ''')

    # Create enrollments table (many-to-many relationship)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            PRIMARY KEY (student_id, course_id),
            FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
        )
    ''')

    # Seed default courses
    default_courses = ["Data Structures", "DBMS", "Computer Networks", "Operating Systems"]
    for title in default_courses:
        cursor.execute("INSERT OR IGNORE INTO courses (title) VALUES (?)", (title,))

    # Seed sample enrolled students if table is empty
    cursor.execute("SELECT COUNT(*) as count FROM students")
    if cursor.fetchone()['count'] == 0:
        sample_students = [
            ("Asha Sharma", "asha@nptel.ac.in", "pass", "98.4%", 18, "4.9/5", 5, "Data Structures • Moderate", ["Data Structures", "DBMS"]),
            ("Rahul Verma", "rahul@nptel.ac.in", "pass", "95.1%", 14, "4.8/5", 4, "DBMS • Advanced", ["DBMS", "Operating Systems"]),
            ("Meera Patel", "meera@nptel.ac.in", "pass", "92.8%", 12, "4.7/5", 3, "Computer Networks • Easy", ["Computer Networks", "Data Structures"])
        ]

        for name, email, pwd, acc, tests, rating, streak, focus, courses in sample_students:
            cursor.execute('''
                INSERT INTO students (name, email, password, accuracy, tests_taken, avg_rating, streak_days, today_focus)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, email, pwd, acc, tests, rating, streak, focus))
            student_id = cursor.lastrowid

            for c_title in courses:
                cursor.execute("SELECT id FROM courses WHERE title = ?", (c_title,))
                c_row = cursor.fetchone()
                if c_row:
                    cursor.execute("INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)", (student_id, c_row['id']))

    conn.commit()
    conn.close()

def get_student_by_email(email):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE email = ?", (email.strip().lower(),))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    student = dict(row)

    # Fetch enrolled courses
    cursor.execute('''
        SELECT c.title FROM courses c
        JOIN enrollments e ON c.id = e.course_id
        WHERE e.student_id = ?
    ''', (student['id'],))
    courses = [r['title'] for r in cursor.fetchall()]
    student['enrolled_courses'] = courses

    conn.close()
    return student

def authenticate_student(email, password):
    student = get_student_by_email(email)
    if student and student['password'] == password:
        return student
    return None

def register_student(name, email, password, selected_courses):
    email = email.strip().lower()
    conn = get_db()
    cursor = conn.cursor()

    # Check if student exists
    cursor.execute("SELECT id FROM students WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        return False, "An account with this email already exists."

    try:
        cursor.execute('''
            INSERT INTO students (name, email, password, today_focus)
            VALUES (?, ?, ?, ?)
        ''', (name.strip(), email, password, f"{selected_courses[0] if selected_courses else 'General'} • Beginner"))
        student_id = cursor.lastrowid

        for c_title in selected_courses:
            cursor.execute("SELECT id FROM courses WHERE title = ?", (c_title,))
            c_row = cursor.fetchone()
            if c_row:
                cursor.execute("INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)", (student_id, c_row['id']))

        conn.commit()
        conn.close()
        return True, get_student_by_email(email)
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)

def get_all_courses():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM courses ORDER BY id ASC")
    courses = [r['title'] for r in cursor.fetchall()]
    conn.close()
    return courses
