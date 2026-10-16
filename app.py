from flask import Flask, render_template, request, redirect, url_for, session
from db import init_db, authenticate_student, get_student_by_email, register_student, get_all_courses

app = Flask(__name__)
app.secret_key = 'nptel_secret_key_super_secure'

# Initialize SQLite database on startup
init_db()

@app.route('/')
def home():
    user_session = session.get('user')
    if not user_session:
        return redirect(url_for('login'))

    # Fetch live student profile & enrolled courses directly from SQLite DB
    student = get_student_by_email(user_session['email'])
    if not student:
        session.clear()
        return redirect(url_for('login'))

    return render_template('index.html', user=student)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user'):
        return redirect(url_for('home'))

    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        student = authenticate_student(email, password)
        if student:
            session['user'] = {'email': student['email'], 'name': student['name']}
            return redirect(url_for('home'))
        else:
            error = "Invalid email or password. Please try again or enroll as a new student."

    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user'):
        return redirect(url_for('home'))

    error = None
    all_courses = get_all_courses()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        selected_courses = request.form.getlist('courses')

        if not name or not email or not password:
            error = "Please fill in all required fields."
        elif not selected_courses:
            error = "Please select at least one course to enroll in."
        else:
            success, result = register_student(name, email, password, selected_courses)
            if success:
                session['user'] = {'email': result['email'], 'name': result['name']}
                return redirect(url_for('home'))
            else:
                error = result

    return render_template('register.html', error=error, courses=all_courses)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
