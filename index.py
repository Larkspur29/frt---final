from flask import Flask, render_template, url_for,flash,redirect,request,session
# from flask_mail import Mail, Message
import pandas as pd
import sqlite3
import os
import Question_Maker
import run

from flask import Flask, Response, render_template, request, jsonify
from wtforms import StringField, Form
import pandas as pd
import json


app = Flask(__name__)

# Some Definitions
app.config['SECRET_KEY'] = '4f9a5c9c0b0e66722f11b04bbfb4949f'

# app.config.update(
# 	DEBUG=True,
# 	#EMAIL SETTINGS
# 	MAIL_SERVER='smtp.gmail.com',
# 	MAIL_PORT=465,
# 	MAIL_USE_SSL=True,
# 	MAIL_USERNAME = 'drbot.health@gmail.com',
# 	MAIL_PASSWORD = 'Drbothealth123'
# 	)
# mail=Mail(app)





@app.route('/info')
def info():
    return render_template('info.html')


@app.route('/symps', methods=['POST','GET'])
def get_symptoms():
    con = sqlite3.connect("mydatabase.db")
    cur = con.cursor()
    cur.execute("SELECT DISTINCT symptom FROM symptoms")
    symptom = cur.fetchall()

    if request.method == 'POST':
        session['visitor'] = 'visitor'
        session['sex'] = request.form.get('gender','udefined')
        if session['sex'] == "udefined":
            flash(f'Please select your gender!','danger')
            return redirect(url_for('home'))
        session['age'] = request.form['age']
        return render_template('symps.html', symptom = symptom)
    if request.method == 'GET' and 'email' in session:
        return render_template('symps.html', symptom = symptom)
    else:
        return redirect(url_for('info'))


Q1=Q2=[]
@app.route('/questions', methods=['POST','GET'])
def questions():
    if request.method == 'GET':
        return redirect(url_for('info'))
    symptoms = request.form.getlist('sym[]')
    if len(symptoms) <= 1:
        flash(f'Please select atleast 2 symptoms!','danger')
        return redirect(url_for('home'))
    myQuestions1,myQuestions2 = Question_Maker.fillter(symptoms)
    if len(myQuestions2) > 0:
        global Q1
        Q1=myQuestions1
        global Q2
        Q2=myQuestions2
        return render_template('choose-one.html',symptoms=symptoms,myQuestions1=myQuestions1,
                                                    myQuestions2=myQuestions2)
    else:
        return render_template('questions.html',symptoms=symptoms,myQuestions=myQuestions1)
    

@app.route('/choose', methods=['POST','GET'])
def chooseOne():
    if request.method == 'GET':
        return redirect(url_for('info'))
    symptoms = request.form.getlist('sym[]')
    choosen = request.form['ans']
    if choosen[0] == '1':
        symptoms.pop(1)
        choosen = choosen.replace('1','')
        symptoms.append(choosen)
    else:
        symptoms.pop(0)
        choosen = choosen.replace('2','')
        symptoms.append(choosen)
    
    myQuestions1,myQuestions2 = Question_Maker.fillter(symptoms)
    if len(myQuestions2) > 0:
        global Q1
        Q1=myQuestions1
        global Q2
        Q2=myQuestions2
        return render_template('choose-one.html',symptoms=symptoms,myQuestions1=myQuestions1,
                                                    myQuestions2=myQuestions2)
    else:
        return render_template('questions.html',symptoms=symptoms,myQuestions=myQuestions1)


@app.route('/diagnosis/<count>', methods=['POST','GET'])
def diagnosis(count):
    if request.method == 'GET':
        return redirect(url_for('info'))
    goodAnswer = []
    badAnswer = []
    ans = []
    for i in range(int(count)):
        ans = ans + request.form.getlist('ans['+str(i)+']')

    for x in range(len(ans)):
        if ans[x][-1] == '3' or ans[x][-1] == '2':
            badAnswer.append(ans[x])
        else:
            goodAnswer.append(ans[x])
    
    symptoms = request.form.getlist('sym[]')
    symptoms = list(set(symptoms+goodAnswer))
    diseases = run.run(symptoms)
    
    percent=[]
    diseasesSyms = []
    for i in range(len(diseases)):
        disSymps = getAllSyms(diseases[i])
        percent.append(getPercent(symptoms,disSymps))
        diseasesSyms.append(disSymps)


    for i in range(len(diseases)-1):
        for j in range(len(diseases)-i-1):
            if percent[j] < percent[j+1]:
                percent[j],percent[j+1] = percent[j+1],percent[j]
                diseases[j],diseases[j+1] = diseases[j+1],diseases[j]
                diseasesSyms[j],diseasesSyms[j+1] = diseasesSyms[j+1],diseasesSyms[j]
    
    if len(diseases) > 0:
        counter = 0
        finalDiseases = []
        finalPercent = []
        diseasesInfo = []
        finalDisSyms = []
        diseasesTips = []
        specialist = ""
        for i in range(len(diseases)):
            if percent[i] == 0:
                continue
            finalDiseases.append(diseases[i])
            finalPercent.append(percent[i])
            finalDisSyms.append(diseasesSyms[i])
            diseasesInfo.append(getDiseaseData(diseases[i]))
            specialist = getSpecialist(diseasesInfo[i][4])
            diseasesTips.append(getTips(diseases[i]))
            counter = counter + percent[i]
            if counter > 75.0:
                break
        return render_template('diagnosis.html',diseases=finalDiseases,percent=finalPercent,
                symptoms=symptoms,diseasesInfo=diseasesInfo,diseasesSyms=finalDisSyms,diseasesTips=diseasesTips,specialist=specialist)
    else:
        flash(f'Sorry your symptoms dosn\'t match any disease, try again!','danger')
        return redirect(url_for('home'))





def getDiseaseData(disease):
    con = sqlite3.connect("mydatabase.db")
    cur = con.cursor()
    query_string = """SELECT * FROM diseases WHERE disease=?"""
    cur.execute(query_string, (disease,))
    diseases = cur.fetchall()
    cur.close()
    if len(diseases) > 0:
        return diseases[0]
    return []

def getAllSyms(disease):
    con = sqlite3.connect("mydatabase.db")
    cur = con.cursor()
    query_string = """SELECT symptom FROM symptoms WHERE disease=?"""
    cur.execute(query_string, (disease,))
    symptoms = cur.fetchall()
    cur.close()
    result = []
    if len(symptoms) > 0:
        for s in symptoms:
            result.append(s[0])
        return result
    return []

def getTips(disease):
    con = sqlite3.connect("mydatabase.db")
    cur = con.cursor()
    query_string = """SELECT tips FROM tips WHERE disease=?"""
    cur.execute(query_string, (disease,))
    tips = cur.fetchall()
    cur.close()
    if len(tips) > 0:
        return tips[0][0]
    return []

def getPercent(mySymptoms,diseaseSymptoms):
    counter = 0
    for ms in mySymptoms:
        for ds in diseaseSymptoms:
            if ms == ds:
                counter +=1
    if len(diseaseSymptoms) == 0:
        return 0
    else :
        return int((counter * 100) / len(diseaseSymptoms))

def getSpecialist(organ):
    con = sqlite3.connect("mydatabase.db")
    cur = con.cursor()
    query_string = """SELECT specialist FROM specialist WHERE organ=?"""
    cur.execute(query_string, (organ,))
    specialist = cur.fetchall()
    cur.close()
    if len(specialist) > 0:
        return specialist[0][0]
    return ""


# Load data from the CSV file
csv_file_path = 'medicine_dataset.csv'
data = pd.read_csv(csv_file_path)
medicines = data['name'].tolist()

class SearchForm(Form):
    autocomp = StringField('Insert Medicine', id='city_autocomplete')

@app.route('/_autocomplete', methods=['GET'])
def autocomplete():
    return Response(json.dumps(medicines), mimetype='application/json')

@app.route('/search', methods=['GET', 'POST'])
def index():
    form = SearchForm(request.form)
    if request.method == 'POST':
        search_query = request.form['search_query']
        result = search_in_csv(search_query)
        if result:
            return render_template('result.html', result=result)
        else:
            return render_template('result.html', result=None)
    return render_template('medicine.html', form=form)

def search_in_csv(search_query):
    filtered_data = data[data['name'].str.contains(search_query, case=False, na=False)]
    if not filtered_data.empty:
        result = filtered_data.to_dict(orient='records')[0]
        filtered_result = {key: value for key, value in result.items() if pd.notna(value)}
        return filtered_result
    return None



@app.route('/map', methods=['GET', 'POST'])
def google_map():
    address = address_value = "Cairo"
    if request.method == 'POST':
        address = address_value = request.form['map-address']
        address = address.replace(' ', '+')
    return render_template('map.html', address=address, address_value=address_value)


@app.route('/')
@app.route('/')
def home():
    return render_template('intro.html')

if __name__ == '__main__':
    # app.run()
    app.run(debug=True)
