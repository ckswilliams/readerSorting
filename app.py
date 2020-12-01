from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy


from wtforms.ext.sqlalchemy.orm import model_form

from flask_wtf import FlaskForm
from wtforms import SelectField, TextField
import json
import argparse


app = Flask(__name__, static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SECRET_KEY'] = 'whydoineedthis'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
db = SQLAlchemy(app)



import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DisplaySet(db.Model):
    __tablename__ = 'displayset'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    def __init__(self):
        pass

class DisplayItem(db.Model):
    __tablename__ = 'displayitem'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    display_set_id = db.Column(db.Integer,db.ForeignKey('displayset.id'))
    fn = db.Column(db.String)
    
    def __init__(self, display_set_id, fn):
        self.display_set_id = display_set_id
        self.fn = fn


class Ranking(db.Model):
    __tablename__ = 'ranking'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    display_set_id = db.Column(db.Integer,db.ForeignKey('displayset.id'))
    display_item_id = db.Column(db.Integer,db.ForeignKey('displayitem.id'))
    user_id = db.Column(db.Integer,db.ForeignKey('user.id'))
    datetime = db.Column(db.DateTime,  default=db.func.current_timestamp())
    rank = db.Column(db.Integer)

    def __init__(self, user_id, display_set_id, display_item_id, rank):
        self.user_id = user_id
        self.display_set_id = display_set_id
        self.display_item_id = display_item_id
        self.rank = rank
        

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    def __init__(self, name):
        self.name = name
    
db.drop_all()
db.create_all()


def add_dummy_data():
    
    u = User('Chris')
    u2 = User('Jimothy')
    db.session.add(u)
    db.session.add(u2)
    db.session.commit()
    
    
    #Make 3 display_sets
    for i in range(1,4):
        ds = DisplaySet()        
        db.session.add(ds)
        db.session.commit()
        
        #Add 5 dispaly items to each display set
        for j in range(1,6):
            di = DisplayItem(ds.id, f'{i}_{j}.png')
            db.session.add(di)  
        db.session.commit()
    

    
    for i in range(5):
        rank = (i+2) % 5
        r = Ranking(user_id=1, display_set_id=1, display_item_id=i, rank=rank)
        db.session.add(r)
    db.session.commit()
    
    
add_dummy_data()


def export_data():
    data = db.session.query(Ranking, User, DisplayItem, DisplaySet).join(User).join(DisplayItem).join(DisplaySet).all()
    
    for r, u, di, ds in data:
        pass
    

@app.route('/')
def main():
    try:
        session['user_id']
    except KeyError:
        redirect('/user')
        
    ranked = Ranking.query.filter_by(user_id=session['user_id']).all()
    
    display_sets = DisplaySet.query.all()
    display_sets = set([ds.id for ds in display_sets])
    
    ranked_sets = set([r.display_set_id for r in ranked])
    outstanding_sets = list((display_sets - ranked_sets))
    if len(outstanding_sets) == 0:
        return '<h1>ALL DONE!</h1><br><p>If this is incorrect, you may need to change user or add a new user<a href="/adduser">Add user</a> <a href="/user">Change user</a>'
    
    display_set_id = outstanding_sets[0]
    session['display_set_id'] = display_set_id
    
    image_info = db.session.query(DisplaySet, DisplayItem).filter_by(id=display_set_id).join(DisplayItem)
    enum_info = [(di.id, di.fn) for ds, di in image_info]
    
    
    print(session['user_name'])
    print(session['user_id'])
 
    
    return render_template('sort.html',
                           image_info=enum_info,
                           user=session['user_name'],
                           display_set_id=display_set_id,
                           outstanding_sets=len(outstanding_sets))


@app.route('/submitrank', methods=['GET', 'POST'])
def submitrank():

    json_postdata = request.json
    logger.debug(f'Received POST - {json_postdata}')
    ranks = [s.replace('&','') for s in json_postdata.split('item[]=')[1:]]
    
    display_set_id = session['display_set_id']
    user_id = session['user_id']
    
    display_sets = db.session.query(DisplaySet, DisplayItem).filter_by(id=display_set_id).join(DisplayItem).all()
    
    display_item_ids = [di.id for ds, di in display_sets]
    
    for rank, display_item_id in enumerate(ranks):
        r = Ranking(user_id, display_set_id, display_item_id, rank)
        db.session.add(r)
    db.session.commit()

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


class UserForm(FlaskForm):
    name = SelectField('Choose name', choices = [(user.id, user.name) for user in User.query.all()])
    
class NewUserForm(FlaskForm):
    name = TextField('Choose name')



@app.route('/user', methods=['GET', 'POST'])
def login():
    form = UserForm()
    form.name.choices = [(user.id, user.name) for user in User.query.all()]
    
    if request.method == 'POST':
        print('test begin')
        print(form.name.data)
        print('test end')
        session['user_id'] = form.name.data
        session['user_name'] = User.query.filter_by(id=form.name.data).first().name

        return redirect('/')
        
    return render_template('user.html',
                           form=form)
    
@app.route('/adduser', methods=['GET', 'POST'])
def adduser():
    form = NewUserForm()
    
    if request.method == 'POST':
        
        u = User(form.name.data)
        db.session.add(u)
        db.session.commit()
        session['user_id'] = u.id
        session['user_name'] = u.name
        return redirect('/')
        
    return render_template('user.html',
                           form=form,
                           form_title='Add a new user')





if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='Webapp for easy sorting of medical images')
    parser.add_argument("-p", "--port", type=int,
                        action="store", default=5000)
    parser.add_argument("-d", "--debug", action='store_true')
    parser.add_argument('-l', '--loadcsv', action='store')
    parser.add_argument('-e', '--export', action='store')
    
    args = parser.parse_args()
    
    if args.debug:
        logger.info('Dropping database')
        db.drop_all()
        db.create_all()
        logger.info('Populating DB with dummy data')
        add_dummy_data()
    
    if args.loadcsv != '':
        db.drop_all()
        db.create_all()
        load_csv_data(args.loadcsv)
        
    print(args.loadcsv)
    
    
    port = args.port
    
    
    app.run(debug=True, port=port)
