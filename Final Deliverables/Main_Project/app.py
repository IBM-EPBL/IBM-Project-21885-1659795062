import joblib
from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import InputRequired, Email, Length
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from cloudant.client import Cloudant
import pandas as pd
import pickle
import os
import requests
import numpy as np
from gevent.pywsgi import WSGIServer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split




app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://bhxyguombkphfd:98bbaa159dd23d7fa9e2529542f11aee235014f5c03ea8c9917dba674585859c@ec2-3-227-68-43.compute-1.amazonaws.com:5432/dapiu2e2ie5hs3'
bootstrap = Bootstrap(app)
client=Cloudant.iam('3dc145e8-61b5-46ca-b368-b3a1aee03600-bluemix','7UNHm-m8TbQt5ATtK5uikIGDkfYnysBbJRmdmaGq9Hr2',connect=True)
db = client.create_database('balu_data')
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


API_KEY = "4xUsYulwPd5YdaEUVvhcseOQXvizaGreTVk4mNFFl4YO"
token_response = requests.post('https://iam.cloud.ibm.com/identity/token', data={"apikey":
 API_KEY, "grant_type": 'urn:ibm:params:oauth:grant-type:apikey'})
mltoken = token_response.json()["access_token"]

header = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + mltoken}


#class User(UserMixin, db.Model):
#    id = db.Column(db.Integer, primary_key=True)
#    username = db.Column(db.String(15), unique=True)
#    email = db.Column(db.String(50), unique=True)
#    password = db.Column(db.String(80))



#def load_user(user_id):
#    return User.query.get(int(user_id))

@login_manager.user_loader
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=15)])
    email = StringField('Email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=80)])


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=15)])
    email = StringField('Email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=80)])


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/help')
def help():
    return render_template("help.html")





@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        name = form.username.data
        email = form.email.data
        password = form.password.data

        print(name, password)

        data = {
            '_id': email,
            'name': name,
            'psw': password,
        }

        print(data)

        query = {'_id': {'$eq': data['_id']}}

        docs = db.get_query_result(query)

        print(docs)

        print(len(docs.all()))

        if (len(docs.all()) != 0):
            db.create_document(data)
            return render_template("dashboard.html", form=form)

        return redirect("/signup")
    return render_template("login.html", form=form)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.username.data
        email = form.email.data
        password = form.password.data

        print(name, email, password)

        data = {
            '_id': email,
            'name': name,
            'psw': password,
        }

        print(data)

        query = {'_id': {'$eq': data['_id']}}

        docs = db.get_query_result(query)

        print(docs)

        print(len(docs.all()))

        if (len(docs.all()) == 0):
            db.create_document(data)
            return render_template("login.html", form=form)

        return redirect("/login")
    return render_template('signup.html', form=form)


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/disindex")

def disindex():
    return render_template("disindex.html")





@app.route("/liver")

def liver():
    return render_template("liver.html")


def ValuePred(to_predict_list, size):
    to_predict = np.array(to_predict_list).reshape(1,size)
    if(size==7):
        loaded_model = joblib.load('liver_model.pkl')
        result = loaded_model.predict(to_predict)

    return result[0]


@app.route('/predictliver', methods=["POST"])
def predictliver():
    if request.method == "POST":
        to_predict_list = request.form.to_dict()
        to_predict_list = list(to_predict_list.values())
        to_predict_list = list(map(float, to_predict_list))
        if len(to_predict_list) == 7:
            t = [[float(to_predict_list[0]), float(to_predict_list[1]), int(to_predict_list[2]), int(to_predict_list[3]),
                 float(to_predict_list[4]), float(to_predict_list[5]), float(to_predict_list[6])]]
            payload_scoring = {"input_data": [{"field": [["Total_Bilirubin","Direct_Bilirubin","Alkaline_Phosphotase","Alamine_Aminotransferase","Total_Protiens","Albumin","Albumin_and_Globulin_Ratio"]], "values":t}]}

            response_scoring = requests.post('https://us-south.ml.cloud.ibm.com/ml/v4/deployments/b13eb819-cb3b-4969-a6fe-45d00208ef11/predictions?version=2022-11-13',json=payload_scoring,headers={'Authorization': 'Bearer ' + mltoken})
            #        print("Scoring response")
            predictions = response_scoring.json()
            #res=predictions['predictions'][0]['values'][0][0]
            result = ValuePred(to_predict_list, 7)


    if int(result) == 1:
        prediction = "Patient has a high risk of Liver Disease, please consult your doctor immediately"
    else:
        prediction = "Patient has a low risk of Liver Disease"
    return render_template("liver_result.html", prediction_text=prediction,li=to_predict_list)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

port =os.getenv('VCAP_APP_PORT','8080')


if __name__ == "__main__":
    #app.run(debug=True) # To run the app in local host
    app.secret_key=os.urandom(12) # To run the app in IBM Cloud
    app.run(debug=True,host='0.0.0.0',port=port)

