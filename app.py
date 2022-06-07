
from flask import Flask, redirect, render_template, g, request, session, redirect, url_for
from database import connect_db, get_db
from werkzeug.security import generate_password_hash,check_password_hash   # for hashing user passwords in Flask
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# --------------------------------------------------------------------------
# Closing DB

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        # it will close this object(sqlite_db) at the end of every request, 
        # so that there won't be any leaks after the route finishes response to the user
        g.sqlite_db.close()
# --------------------------------------------------------------------------

def get_current_user():
    user_result = None
    if 'user' in session:
        user = session['user']

        db = get_db()
        user_cur = db.execute('select id, name, password, expert, admin from user where name=?', [user])
        user_result = user_cur.fetchone()

    return user_result

@app.route('/')
def index():
    user = get_current_user()
    db = get_db()

    questions_cur = db.execute('select questions.id as question_id, questions.question_text, askers.name as asker_name, experts.name as expert_name from questions \
                                join user as askers on askers.id=questions.asked_by_id \
                                join user as experts on experts.id=questions.expert_id \
                                where questions.answer_text is not null')
                    # 2 different joins bcoz 1 is for asker user and other is for expert user 
                    # There are 2 diff users in our app
    questions_result = questions_cur.fetchall()

    return render_template('home.html', user=user, questions=questions_result)

@app.route('/register', methods=['GET', 'POST'])
def register():
    user = get_current_user()

    if request.method == 'POST':
        db = get_db()

# -----------------------------------------------------------------------------------------------------------------------
        # Check if user is already there in db or not
        existing_user_cur = db.execute('select id from user where name=?', [request.form['name']])
        existing_user = existing_user_cur.fetchone()

        if existing_user:
            return render_template('register.html', user=user, error='User Already Exists')
# -----------------------------------------------------------------------------------------------------------------------
        hashed_password = generate_password_hash(request.form['password'], method='sha256')
                        # hashing the password using this new method sha256, search once online
        db.execute('insert into user (name, password, expert, admin) values (?,?,?,?) ', [request.form['name'], hashed_password, '0', '0'])
                        # '0' for expert and admin, it means they will be 0
        db.commit()
        
        session['user'] = request.form['name']
        return redirect(url_for('index'))

    return render_template('register.html', user=user)


@app.route('/login', methods=['POST', 'GET'])
def login():
    user = get_current_user()
    error = None

    if request.method == 'POST':
        db = get_db()

        name = request.form['name']
        password = request.form['password']

        user_cur = db.execute('select id, name, password from user where name=?', [name])
        user_results = user_cur.fetchone()

        if user_results:
            if check_password_hash(user_results['password'], password):         # Checking pass from db whether it matches or no
                session['user'] = user_results['name']
                return redirect(url_for('index'))
            else:
                error = 'The Password is Incorrect'
        else:
            error = 'The Username is Incorrect'

    return render_template('login.html', user=user, error=error)


@app.route('/question/<question_id>')
def question(question_id):
    user = get_current_user()
    db = get_db()

    questions_cur = db.execute('select questions.question_text, questions.answer_text, askers.name as asker_name, experts.name as expert_name from questions \
                                join user as askers on askers.id=questions.asked_by_id \
                                join user as experts on experts.id=questions.expert_id \
                                where questions.id=?', [question_id])
    question = questions_cur.fetchone()

    return render_template('question.html', user=user, question=question)


@app.route('/answer/<question_id>', methods=['POST', 'GET'])
def answer(question_id):
    user = get_current_user()

    # Protecting data from not-logged in users
    if not user:
        return redirect(url_for('login'))
    
    if user['expert'] == 0:
        return redirect(url_for('index'))

    db = get_db()

    if request.method == 'POST':
        db.execute('update questions set answer_text=? where id=?', [request.form['answer'], question_id])
        db.commit()
        return redirect(url_for('unanswered'))

    question_cur = db.execute('select id, question_text from questions where id=?', [question_id])
    question = question_cur.fetchone()

    return render_template('answer.html', user=user, question=question)


@app.route('/ask', methods=['POST', 'GET'])
def ask():
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))

    db = get_db()

    if request.method == 'POST':
        db.execute('insert into questions (question_text, asked_by_id, expert_id) values (?,?,?)', [request.form['question'], user['id'], request.form['expert']])
        db.commit()

        return redirect(url_for('index'))
    
    expert_cur = db.execute('select id, name from user where expert=1')
    expert_results = expert_cur.fetchall()

    return render_template('ask.html', user=user, experts=expert_results)


@app.route('/unanswered')
def unanswered():
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))

    if user['expert'] == 0:
        return redirect(url_for('index'))

    db = get_db()
    questions_cur = db.execute('select questions.id, questions.question_text, user.name from questions \
        join user on user.id=questions.asked_by_id \
            where questions.answer_text is null and questions.expert_id=?', [user['id']])
    questions = questions_cur.fetchall()
    return render_template('unanswered.html', user=user, questions=questions)


@app.route('/users')
def users():
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))

    # Protecting user list from all diff users, except admin
    if user['admin'] == 0:
        return redirect(url_for('index'))

    db = get_db()
    users_cur = db.execute('select id, name, expert, admin from user')
    users_results = users_cur.fetchall()

    return render_template('users.html', user=user, users=users_results)


@app.route('/promote/<user_id>')
def promote(user_id):
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))
        
    if user['admin'] == 0:
        return redirect(url_for('index'))

    db = get_db()
    db.execute('update user set expert=1 where id=?', [user_id])
    db.commit()
    return redirect(url_for('users'))


@app.route('/logout')
def logout():
    session.pop('user', None)
            # To logout the user from session
    return redirect(url_for('index'))



if __name__ == '__main__':
    app.run(debug=True)






