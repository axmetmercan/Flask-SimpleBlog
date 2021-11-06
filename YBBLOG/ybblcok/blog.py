from typing import MutableSet
from MySQLdb import cursors
from flask import Flask, config, render_template, redirect,flash,url_for,session,logging,request
import flask
from flask_mysqldb import MySQL
import passlib
from wtforms import Form, StringField, TextAreaField, PasswordField, form, validators
from passlib.hash import sha256_crypt
from functools import wraps
 
#Kullanıcı girişini kontrol eden decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' in session:  
            return f(*args, **kwargs)
        else:
            flash('Bu sayfayi görüntülemek için izniniz yok.', 'danger')
            return redirect(url_for('login'))
    return decorated_function



#Kullanıcı kayıt formu

class ResgisterForm(Form):
    name = StringField('İsim soyisim', validators=[validators.length(min=3, max=25)])
    username = StringField('Kullanıcı adı', validators=[validators.length(min=5, max=35) ])
    email = StringField('Email adı', validators=[validators.length(min=10, max=35), validators.Email(message='Lütfen Geçerli Bir email giriniz.')])
    password = PasswordField('Parola', validators = [
        validators.DataRequired(message='Lütfen Parolanızı Giriniz'),
        validators.EqualTo(fieldname='confirm', message='Parolalarınız eşleşmiyor')
        ])
    confirm = PasswordField('Parola Doğrulama')


class LoginForm(Form):
    username = StringField('Kullanıcı Adınız')
    password = PasswordField('Parola')


app = Flask(__name__)
app.secret_key = 'ybblog'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'ybblog'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)



@app.route('/')
def index():
    
    return render_template('index.html', answer = 'edvet')


@app.route('/register', methods = ['GET', 'POST'])
def register():
    form = ResgisterForm(request.form)

    if request.method == 'POST' and form.validate():
        #Formdan verileri aliyor
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        
        # Veri tabanına bagliyor
        cursor = mysql.connection.cursor()
        sorgu = 'Insert into users(name, email, username,password) VALUES(%s, %s, %s, %s)'
        cursor.execute(sorgu, (name, email, username, password))
        mysql.connection.commit()
        cursor.close()
        flash('Kayıt Başarılı','success')

        return redirect(url_for('login'))
    else:
        return render_template('register.html', form = form)



@app.route('/login', methods = ['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST':
        username = form.username.data
        password_entered = form.password.data
        cursor =mysql.connection.cursor()
        sorgu = 'SELECT * FROM users WHERE username = %s'

        result = cursor.execute(sorgu, (username,))

        if result != 0:  
            data = cursor.fetchone()
            real_password = data['password']
            if sha256_crypt.verify(password_entered, real_password):
                flash('Başarıyla Giriş Yapıldı', 'success')
                
                session['logged_in'] = True
                session['username'] = username

                return redirect(url_for('index'))
            else:
                flash('Yanlış Şifre Girdiniz.', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Böyle Bir Kullanıcı Adı Bulunmuyor', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html', form = form)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():

    cursor = mysql.connection.cursor()
    sorgu = 'Select * From articles Where author = %s'
    result = cursor.execute(sorgu,(session['username'],))

    if result != 0:
        articles = cursor.fetchall()
        return render_template('dashboard.html', articles = articles)
    else:
        return render_template('dashboard.html')

## MAKALE FORM:
class ArticleForm(Form):
    title = StringField('Makale Başlıgı', validators=[validators.length(min=5, max=65)])
    content = TextAreaField('Makale İçeriğiniz', validators = [validators.length(min=10)])



@app.route('/addarticle', methods=['GET','POST'])
def addarticle():
    form = ArticleForm(request.form)

    if request.method == 'POST' and form.validate():
        title = form.title.data
        content = form.content.data
        cursor = mysql.connection.cursor()
        sorgu = 'Insert Into articles(title, author, content) VALUES(%s,%s,%s)'
        cursor.execute(sorgu, (title,session['username'], content))
        mysql.connection.commit()
        cursor.close()
        flash('Makale Başarıyla Kaydedildi', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('addarticle.html', form = form)

@app.route('/articles')
def articles():
    cursor = mysql.connection.cursor()
    sorgu = 'Select * From articles'
    result = cursor.execute(sorgu)
    if result != 0:
        articles = cursor.fetchall()
        return render_template('articles.html', articles = articles)
    else:
        return render_template('articles.html')

#Article Sayfası
@app.route("/article/<string:id>")
def article(id):

    cursor = mysql.connection.cursor()
    sorgu = 'Select * From articles where id = %s'
    result = cursor.execute(sorgu,(id,))
    if result != 0:
        article = cursor.fetchone()
        return render_template('article.html', article = article)
    else:
        return render_template('article.html')


# Makale Silme
@app.route('/delete/<string:id>')
@login_required
def makalesil(id):
    cursor = mysql.connection.cursor()
    sorgu = 'Select * from articles where author = %s and id = %s'
    result = cursor.execute(sorgu, (session['username'], id))
    if result != 0:
        flash('{} id nolu makale başarıyla silindi. '.format(id),'success')
        sorgu2 = 'Delete  from articles where id = %s'
        cursor.execute(sorgu2, (id,))
        mysql.connection.commit()
        return redirect(url_for('dashboard'))
    else:
        flash('Bu makale yok veya bu makaleyi silmeye yetkiniz yok', 'danger')
        return redirect(url_for('index'))


#MakaleGüncelleme
@app.route('/edit/<string:id>', methods = ('GET', 'POST'))
@login_required
def edit(id):
    if request.method == 'GET':
        cursor = mysql.connection.cursor()
        sorgu = 'Select * From articles where id = %s and author = %s'
        result = cursor.execute(sorgu, (id, session['username']))
        if result != 0:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article['title']
            form.content.data = article['content']
            return render_template('update.html', form = form)
        else:
            flash('Böyle bir makale bulunmamaktadir veya yetkiniz bulunmamaktadır', 'danger')
            return redirect(url_for('index'))
            """  
            form = ArticleForm(request.form)

            new_title = form.title.data
            new_content = form.content.data
            sorgu2 = 'Update articles Set title = %s and content = %s where id = %s'
            cursor = mysql.connection.cursor()
            cursor.execute(sorgu,(new_title,new_content, id))
            mysql.connection.commit()
            """
            
                   
    else:
        form = ArticleForm(request.form)

        new_title = form.title.data
        new_content = form.content.data
        sorgu2 = 'Update articles Set title = %s, content = %s where id = %s'
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(new_title,new_content, id))
        mysql.connection.commit()
        flash('Makale Güncellendi', 'success')
        return redirect(url_for('dashboard'))

@app.route('/about')
def about():
    return render_template('about.html',form = form)

if __name__ == '__main__':
    app.run(debug=True)