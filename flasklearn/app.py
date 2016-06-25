import os
from flask import Flask, render_template, url_for, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from forms import BookmarkForm
#import models

#from logging import DEBUG
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
#app.logger.setLevel(DEBUG)
app.config['SECRET_KEY'] = b'\xe4\xd1\xec\xea\x14\xfb\xaf\x16y<\xe8q\xa2\x19Z\x8a\xb1k8\t\x14F\xa46'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
db = SQLAlchemy(app)

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')
    #return render_template('index.html', new_bookmarks=models.Bookmark.newest(5))

@app.route('/add', methods=['GET', 'POST'])
def add():
    form = BookmarkForm()
    if form.validate_on_submit():
        url = form.url.data
        description = form.description.data
        bm = models.Bookmark(url = url, description = description)
        db.session.add(bm)
        db.session.commit()
        flash("Store '{}'".format(description))
        return redirect(url_for('index'))
    return render_template('add.html', form=form)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)