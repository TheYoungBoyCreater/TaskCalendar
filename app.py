from flask import Flask, render_template, request, redirect, url_for, session, flash  
from flask_mysqldb import MySQL
import MySQLdb.cursors
import MySQLdb.cursors, re, hashlib
import json
from datetime import datetime

app = Flask(__name__)

app.secret_key = 'your secret key' # 秘密鍵

app.config['MYSQL_HOST'] = 'host' # MySQLのホスト名
app.config['MYSQL_USER'] = 'username' # MySQLのユーザ名
app.config['MYSQL_PASSWORD'] = 'yourpassword' # MySQLのパスワード
app.config['MYSQL_DB'] = 'yourdb' # 用いるMySQL内のデータベース

mysql = MySQL(app)

# ログイン機能

@app.route('/')
def home_redirect():
    return redirect('/taskcalendar/login')

@app.route('/taskcalendar/login', methods=['GET','POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']

        hash = password + app.secret_key
        hash = hashlib.sha1(hash.encode())
        password = hash.hexdigest()

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password,))
        account = cursor.fetchone()

        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']

            return redirect(url_for('home'))
        else:
            msg = 'ユーザIDかパスワードが違います。'
    return render_template('index.html', msg = msg)

# ログアウト機能

@app.route('/taskcalendar/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)

    return redirect(url_for('login'))

# ユーザ登録機能

@app.route('/taskcalendar/register', methods=['GET','POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password'in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()

        if account:
            msg = 'そのアカウントは既に存在します。'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = '無効なメールアドレスです。'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'ユーザIDは, 文字と数字以外使用できません。'
        elif not username or not password or not email:
            msg = '必要事項を入力してください。'
        else:
            hash = password + app.secret_key
            hash = hashlib.sha1(hash.encode())
            password = hash.hexdigest()
            cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s)', (username, password, email,))
            mysql.connection.commit()
            msg = '登録に成功しました。'
    elif request.method == 'POST':
        msg = '必要事項を入力してください。'
    return render_template('register.html', msg = msg)

# ホーム画面

@app.route('/taskcalendar/home')     
def home():
    if 'loggedin' in session: 
        current_year = datetime.now().year
        current_month = datetime.now().month

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM shifts WHERE username = %s", (session['username'],))
        data = cursor.fetchall()

        salaries = []
        tcosts = []
        start_dates = []
        start_hours = []
        start_minutes = []
        end_dates = []
        end_hours = []
        end_minutes = []

        for row in data:
            salaries.append(row[1])
            tcosts.append(row[2])
            start_dates.append(row[3])
            start_hours.append(row[4])
            start_minutes.append(row[5])
            end_dates.append(row[6])
            end_hours.append(row[7])
            end_minutes.append(row[8])

        m_salaly=0
        for i in range(len(data)):
            if int(start_dates[i][0:4]) == current_year and (int(start_dates[i][5:7]) == current_month or int(start_dates[i][6] == current_month)):
                wtime_h = int(end_hours[i]) - int(start_hours[i])
                wtime_m = int(end_minutes[i]) - int(start_minutes[i])
                m_salaly += int(salaries[i]*wtime_h + salaries[i]*wtime_m/60 + tcosts[i])
        return render_template('home.html', username = session['username'], m_salaly=m_salaly)
    return redirect(url_for('login'))

# 予定追加機能

@app.route('/taskcalendar/addevent', methods=['GET','POST'])
def addevent():
    msg = ''
    if request.method == 'POST' and 'title' in request.form and 'start' in request.form and 'end' in request.form and 'allday' in request.form:
        title = request.form['title']
        start = request.form['start']
        end = request.form['end']
        allday = request.form['allday']
        if allday == 'allday':
            start = start[:10]
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('INSERT INTO events VALUES (NULL, %s, %s, %s, NULL, NULL, NULL, NULL, %s)', (session['username'], title, start, allday,))
            mysql.connection.commit()
            msg = '終日として登録に成功しました。'
        elif allday == 'notallday':
            if not end:
                msg = 'endに値を入れてください。' 
                return render_template('addevent.html', msg = msg)
            else:
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute('INSERT INTO events VALUES (NULL, %s, %s, %s, %s, NULL, NULL, NULL, %s)', (session['username'], title, start, end, allday,))
                mysql.connection.commit()
                msg = '登録に成功しました。'
        else:
            msg = 'error'
            return render_template('addevent.html', msg = msg)

        
    return render_template('addevent.html', msg = msg)

# ホーム画面のカレンダーに予定を表示する機能

@app.route('/taskcalendar/data')
def getevent():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM events WHERE username = %s', (session['username'],))
    result = cursor.fetchall()
    events = []
    for row in result:
        if row['allday'] == 'allday':
                event = {
                    'title': row['title'],
                    'start': row['start'],
                    'allday': 'true'
                }
        elif row['allday'] == 'notallday':
                event = {
                    'title': row['title'],
                    'start': row['start'],
                    'end': row['end'],
                }
        events.append(event)
    with open("events.json", "w") as f:
        json.dump(events, f, indent=4)

    with open("events.json", "r") as f:
        return f.read()

# 削除するイベントの選択肢を表示する機能
@app.route('/taskcalendar/showeventfordelete', methods=['GET', 'POST'])
def showeventfordelete():
    msg = ''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM events WHERE username = %s", (session['username'],))
    events = cursor.fetchall()
    return render_template('showeventfordelete.html', events=events, msg=msg)

# イベント削除機能
@app.route('/taskcalendar/delete', methods=['POST'])
def deleteevent():
    eventids = request.form.getlist('event_ids[]')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    delete_query = "DELETE FROM events WHERE id IN ({})".format(",".join(["%s"] * len(eventids)))
    cursor.execute(delete_query, eventids)
    mysql.connection.commit()
    msg = '削除が完了しました。'
    return render_template('showeventfordelete.html', msg=msg)

# 更新するイベントを選択肢を表示する機能
@app.route('/taskcalendar/showeventforupdate', methods=['GET', 'POST'])
def showeventforupdate():
    msg = ''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM events WHERE username = %s", (session['username'],))
    events = cursor.fetchall()
    return render_template('showeventforupdate.html', events=events, msg=msg)

# イベント更新機能
@app.route('/taskcalendar/update', methods=['POST'])
def updateevent():
    if request.method == 'POST' and 'title' in request.form and 'start' in request.form and 'end' in request.form and 'allday' in request.form:
        eventids = request.form['event_ids[]']
        title = request.form['title']
        start = request.form['start']
        end = request.form['end']
        allday = request.form['allday']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("UPDATE events SET title = %s, start = %s, end = %s, allday = %s WHERE id = %s", (title, start, end, allday, eventids,))
        mysql.connection.commit()
        msg = '更新が完了しました。'
    return render_template('showeventforupdate.html', msg = msg)

# メモ機能
@app.route('/taskcalendar/memo', methods=['GET', 'POST'])
def memo():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM posts WHERE username=%s", (session['username'],))
    posts = cursor.fetchall()
    return render_template('memo.html', posts=posts)

# メモ投稿機能
@app.route('/taskcalendar/post', methods=['POST'])
def post():
    msg = ''
    if request.method == 'POST' and 'content' in request.form:
        content = request.form['content']
        timestamp = datetime.now()
        username = session['username']
        if (len(content) <= 250):
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('INSERT INTO posts VALUES (NULL, %s, %s, %s)', (content, timestamp, username))
            mysql.connection.commit()
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("SELECT * FROM posts WHERE username=%s", (session['username'],))
            posts = cursor.fetchall()
            msg = '投稿完了'
        else:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("SELECT * FROM posts WHERE username=%s", (session['username'],))
            posts = cursor.fetchall()
            msg = '文字数は250文字以内に収めてください。'
        return render_template('memo.html', msg=msg, posts=posts)

# メモ編集機能
@app.route('/taskcalendar/memoedit/<int:id>', methods=['GET', 'POST'])
def memoedit(id):
    if request.method == 'POST':
        content = request.form['content']
        timestamp = datetime.now()
        username = session['username']
        if len(content) <= 250:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('UPDATE posts SET content = %s, timestamp = %s WHERE id = %s AND username = %s', (content, timestamp, id, username))
            mysql.connection.commit()
            flash('投稿を編集しました。', 'success')
            return redirect(url_for('memo'))
        elif len(content) > 250:
            msg = '文字数は250文字以内に収めてください。'
            return render_template('memoedit.html', id=id, msg=msg, content=content)
        else:
            msg = 'error'
            return render_template('memoedit.html', id=id, msg=msg, content=content)
    else:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM posts WHERE id = %s AND username=%s", (id, session['username']))
        memo = cursor.fetchone()
        return render_template('memoedit.html', id=id, content=memo['content'])

# メモ削除機能
@app.route('/taskcalendar/memodelete/<int:id>', methods=['GET'])
def memodelete(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM posts WHERE id = %s AND username = %s', (id, session['username']))
    mysql.connection.commit()
    flash('投稿を削除しました。', 'success')
    return redirect(url_for('memo'))

# バイトの時給情報を追加する機能
@app.route('/taskcalendar/add_template', methods=['GET','POST']) 
def add_template():
    msg = ''
    if request.method == 'POST':
        byte_name = request.form['byte_name']
        byte_salaly = request.form['byte_salaly']
        byte_tcost = request.form['byte_tcost']

        if not byte_name:
            flash('バイト名を入力してください')
        elif not byte_salaly:
            flash('時給を入力してください')
        elif not byte_tcost:
            flash('交通費を入力してください')
        else:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('INSERT INTO templates VALUES (NULL, %s, %s, %s, %s, NULL, NULL)', (session['username'], byte_name, byte_salaly, byte_tcost,))
            mysql.connection.commit()
            msg = 'テンプレートの登録に登録に成功しました。'
            return render_template('add_template.html', msg = msg) 
        
    return render_template('add_template.html', msg = msg)

# バイト一覧を表示する機能
@app.route('/taskcalendar/view_template', methods=['GET', 'POST'])
def view_template(): 
    msg = ''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM templates WHERE username = %s", (session['username'],))
    templates = cursor.fetchall()
    return render_template('view_template.html', templates=templates, msg=msg)

# バイト情報の削除を行う機能
@app.route('/taskcalendar/del_template', methods=['POST']) #こっちで削除の処理
def del_template():
    templateids = request.form.getlist('template_ids[]')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    delete_query = "DELETE FROM templates WHERE id IN ({})".format(",".join(["%s"] * len(templateids)))
    cursor.execute(delete_query, templateids)
    mysql.connection.commit()
    msg = '削除が完了しました。'
    return render_template('view_template.html', msg=msg)

# カレンダーにバイトのシフトを追加する機能
@app.route('/taskcalendar/addshift', methods=['GET','POST'])
def addshift():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  
    cursor.execute("SELECT * FROM templates WHERE username = %s", (session['username'],))
    templates = cursor.fetchall() 

    msg = ''
    if request.method == 'POST': #and 'start' in request.form and 'end' in request.form and 'template' in request.form:    

        template_ids = request.form.getlist('template_ids[]')
        selected_template = None
        if template_ids:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("SELECT * FROM templates WHERE id = %s", (template_ids[0],))
            selected_template = cursor.fetchone()
        title = selected_template['byte_name'] if selected_template else ''
        
        template_ids = request.form.getlist('template_ids[]') 
        selected_template = None
        if template_ids:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("SELECT * FROM templates WHERE id = %s", (template_ids[0],))
            selected_template = cursor.fetchone()
        salaly = selected_template['byte_salaly']

        template_ids = request.form.getlist('template_ids[]')
        selected_template = None
        if template_ids:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("SELECT * FROM templates WHERE id = %s", (template_ids[0],))
            selected_template = cursor.fetchone()
        tcost = selected_template['byte_tcost']

        start = request.form['start']
        end = request.form['end']
        allday = 'notallday'

        start_ymd = str(start[0:10])           #月給計算に仕様
        start_hour = str(start[11:13])
        start_minutes = str(start[14:16])
        end_ymd = str(end[0:10])
        end_hour = str(end[11:13])
        end_minutes = str(end[14:16])           

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO shifts VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s)', (salaly, tcost, start_ymd, start_hour, start_minutes, end_ymd, end_hour, end_minutes, session['username']))
        mysql.connection.commit()

 
        if not title:
            msg = 'error'
            return render_template('add_shift.html', templates=templates, msg = msg) ###
        elif allday == 'notallday':
            if not end:
                msg = 'endに値を入れてください。' 
                return render_template('addshift.html', templates=templates, msg = msg) ###
            else:
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute('INSERT INTO events VALUES (NULL, %s, %s, %s, %s, NULL, NULL, NULL, %s)', (session['username'], title, start, end, allday,))
                mysql.connection.commit()
                msg = '登録に成功しました。'
        
    return render_template('add_shift.html', templates=templates, msg = msg) ###

if __name__ == '__main__':
    app.run()

