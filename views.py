from cloudant.client import Cloudant
from flask import Flask, render_template, request, flash, redirect, session, url_for, jsonify, json
from watson_developer_cloud import DiscoveryV1
from werkzeug.utils import secure_filename
import atexit
import os
import json
import time

from flask_wtf import FlaskForm 

from forms import LoginForm, MyForm
from flask_socketio import SocketIO
from flask_socketio import emit, join_room, leave_room

import watson_developer_cloud
from watson_developer_cloud import AssistantV2
from ibm_watson import ToneAnalyzerV3

lang_skills = ['java', 'python', 'c++', 'c#', 'html', 'jquery', 'mysql', 'php']
db_skills = ['management', 'leadership', 'product development', 'testing', 'agile', 'communication', 'creative', 'problem solving', 'design', 'software development', 'writing']
ALLOWED_EXTENSIONS = set(['pdf'])
UPLOAD_FOLDER = "static/tmp/"
app = Flask(__name__, static_url_path='')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config.update(dict(
    SECRET_KEY="powerful secretkey",
    WTF_CSRF_SECRET_KEY="a csrf secret key"
))

socketio = SocketIO(app)
# , async_mode='gevent'

client = Cloudant("7b997c14-00b2-4ebb-8386-b772c09062ba-bluemix", "2cc8e2229f55011a58b8b92d713061c606c8d91e190515442027519824fd4e9f", account="7b997c14-00b2-4ebb-8386-b772c09062ba-bluemix", connect=True)
headers = {"Accept": "application/json",
           "Content-Type": "application/json",
           "Content-Encoding": "gzip"}

db_name = 'mydb'
applications_db = 'applications'
client = None
db = None
appi_db = None

if 'VCAP_SERVICES' in os.environ:
    vcap = json.loads(os.getenv('VCAP_SERVICES'))
    print('Found VCAP_SERVICES')
    if 'cloudantNoSQLDB' in vcap:
        creds = vcap['cloudantNoSQLDB'][0]['credentials']
        user = creds['username']
        password = creds['password']
        url = 'https://' + creds['host']
        client = Cloudant(user, password, url=url, connect=True)
        db = client.create_database(db_name, throw_on_exists=False)
        appi_db = client.create_database(applications_db, throw_on_exists=False)
elif "CLOUDANT_URL" in os.environ:
    client = Cloudant(os.environ['CLOUDANT_USERNAME'], os.environ['CLOUDANT_PASSWORD'], url=os.environ['CLOUDANT_URL'], connect=True)
    db = client.create_database(db_name, throw_on_exists=False)
    appi_db = client.create_database(applications_db, throw_on_exists=False)

elif os.path.isfile('vcap-local.json'):
    with open('vcap-local.json') as f:
        vcap = json.load(f)
        print('Found local VCAP_SERVICES')
        creds = vcap['services']['cloudantNoSQLDB'][0]['credentials']
        user = creds['username']
        password = creds['password']
        url = 'https://' + creds['host']
        client = Cloudant(user, password, url=url, connect=True)
        db = client.create_database(db_name, throw_on_exists=False)
        appi_db = client.create_database(applications_db, throw_on_exists=False)

# On IBM Cloud Cloud Foundry, get the port number from the environment variable PORT
# When running this app on the local machine, default the port to 8000
port = int(os.getenv('PORT', 8000))

# Initialising IBM Services 

service=watson_developer_cloud.AssistantV2(
    iam_apikey='4ZTQ5aq-73YVWgTe2LMOlnMD_U580-6EnJZQKjAw9q6j',
    version='2018-11-08',
    url='https://gateway-lon.watsonplatform.net/assistant/api'
    )

discovery = DiscoveryV1(
        version="2019-01-01",
        iam_apikey='Kw54FJSoj89aoZePeYMKusCWHE9phIRtJF1OQ64JTYmm',
        url="https://gateway-lon.watsonplatform.net/discovery/api"
)

# tone_analyzer = ToneAnalyzerV3(
#     version='2017-09-21',
#     iam_apikey='nmaZeOH66dY03tb8ctOIalQW9q1oylEIxC1XzbkC8wUj',
#     url='https://gateway-lon.watsonplatform.net/tone-analyzer/api'
# )

# checking issue affecting the functionality on the cloud
tone_analyzer = ToneAnalyzerV3(
    version='2017-09-21',
    iam_apikey='RtCfNugR9fGsa0NHtjzEmXhoZ3o3Q-dubbt1Gl3Imn5J',
    url='https://gateway-syd.watsonplatform.net/tone-analyzer/api'
)

@app.route('/')
def root():
    return render_template('/index.html',title='Home page')

# Home Page
@app.route('/jobs_list', methods=['GET', 'POST'])
def home_page():

    db = client['jobs']

    if request.method == 'POST':
        data = request.get_json()
        job_id = ""

        for item in data:
            if item == "id":
                job_id = data['id']

        for job in db:
            if job["_id"] == job_id:
                session['job_title'] = job["title"]
                return jsonify({"title": job["title"], "description": job["description"],
                                "dop": job["dop"], "company": job["company"],
                                "industry": job["industry"],
                                "employment_type": job["employment_type"], "job_functions": job["job_functions"],
                                "skills": job["skills"], "education": job["education"]})

    return render_template('/jobs.html',title='Jobs List', jobs=db)

@app.route('/applicants', methods=['GET', 'POST'])
def put_applicant():

    global job_id

    if request.method == 'POST':
        if request.get_json():
           
            job_data = request.get_json()
            job_id = job_data['id']
            
            return jsonify({"message": "success"})

    form = MyForm()

    form.validate_on_submit()
    for key, value in form.errors.items():
        flash(value, 'error')

        # if action is POST and form is valid 
    if form.validate_on_submit():

            result = request.form.to_dict()
            data = {'firstname': result['firstname'], 'surname':result['surname'], 'email':result['email'], 'dob':result['dob'], 'phone':result['phone'], 'job_ref':job_id[3:]}
            if client:
                # for reading the job_ref
                job_data = request.get_json()
                flag = False
                # check whether in the database there is no user with these credentials
                # an user CANNOT apply for the same job once but CAN apply two different jobs
                for document in appi_db:
                    if (document['email'] == data['email']) and (job_id[3:] == document['job_ref']):
                        flag = True
                
                if flag == False:
                    # create a document and add the data to it
                    my_document = appi_db.create_document(data)

                    flash('You have been added to the database', 'success')
                    # use sessions to share the document info to the other routes
                    session['document'] = my_document
                else:
                    flash('Sorry you cannot apply for the same job twice', 'validation')

                return render_template('applicant.html', form=form)
            else:
                print('No database')
                return jsonify(data)

    return render_template('applicant.html', form=form)

@app.route('/upload', methods=['GET', 'POST'])
def upload():

    if request.method == 'POST':
        
        if 'inputFile' not in request.files:
            flash('Please upload your CV', 'error')

        else:
            f = request.files['inputFile']

            # Uploads file to static/tmp
            if f and allowed_file(f.filename):
                filename = secure_filename(f.filename)
                f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # query document
            for doc in appi_db:
                if doc['_id'] == session['document']['_id']:
                    file = open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'rb')
                    local_document = doc
                    # add filename to session
                    session['document']['filename'] = f.filename
            # attach the file to the document
            local_document.put_attachment(f.filename, 'application/pdf', file.read(), headers=None)

            doc_id = add_doc_to_watson(filename)
            doc_status = get_document_details(doc_id)
            if doc_status:
                result_data = query_watson(doc_id)
                if result_data:
                    filter_query_result(result_data)
                    # remove_doc_from_watson(doc_id)

                    flash('Thank you for uploading your CV', 'success')
    return render_template('upload.html')

# Check the format of the file
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Add document to Watson Discovery Collection
def add_doc_to_watson(file):
    with open(os.path.join(app.config['UPLOAD_FOLDER'], file), 'rb') as fileinfo:
        add_doc = discovery.add_document('377dab60-0f6e-41d0-a301-e524fba93bed', '3cfe57e2-9f65-42ca-912a-d96833d8795f', file=fileinfo).get_result()

    obj = add_doc.get("document_id")
    return obj

# Check the status of the document
def get_document_details(doc_id):
    status = ""
    while "available" not in status:
        oc_info = discovery.get_document_status('377dab60-0f6e-41d0-a301-e524fba93bed', '3cfe57e2-9f65-42ca-912a-d96833d8795f', doc_id).get_result()
        status = oc_info['status']
    return status

# Remove document from Discovery Collection
def remove_doc_from_watson(doc_id):
    delete_doc = discovery.delete_document('377dab60-0f6e-41d0-a301-e524fba93bed', '3cfe57e2-9f65-42ca-912a-d96833d8795f', doc_id).get_result()

# Query Discovery Collection for specific document
def query_watson(doc_id):
    q = discovery.query('377dab60-0f6e-41d0-a301-e524fba93bed', '3cfe57e2-9f65-42ca-912a-d96833d8795f',filter="id::" + format(doc_id),passages=True,highlight=True, passages_count=5, deduplicate=False).get_result()
    obj = q['results']
    return json.dumps(obj)

# Return the enriched text and save it to Cloudant
def filter_query_result(q):
    for doc in appi_db:
        if doc['_id'] == session['document']['_id']:
            local_document = doc
            new_obj = json.loads(q)

            for element in new_obj:
                if element['enriched_text']:
                    filtered_obj = element['enriched_text']
                    local_document['discovery'] = filtered_obj
                    local_document.save()


@app.route('/view_pdf', methods=['GET'])
def view_pdf():
    # get info needed to share to the html page
    data = {}
    data['id'] = session['document']['_id']  
    data['filename'] = session['document']['filename']  
    return render_template('view_pdf.html', data=data)

### Iteration 2 work
current_session = ''
### Integrate watson assistant into the app
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login form to enter a room."""
    #form = LoginForm()

    # create a session for the assisstant
    response = service.create_session(
        # assistant_id='e6a81a18-c7d0-4a3f-9f3d-da8ea20ed9ed'
        assistant_id='bbfcb3fd-6703-4bd5-8b6b-5ecefc71086e'
    ).get_result()

    session['current_session'] = response['session_id']

    #initialising the jump_to_core in session
    session['jump_to_core'] = False
    #initialising the first_mood in session
    session['first_mood'] = 'null'

    # core stage variables
    session['inside_core'] = 'null'

    # final stage variables
    session['inside_final'] = False
    session['jump_to_final'] = False
    session['finish_interview'] = False
    session['final_questions'] = False
    session['exit_interview'] = False

    # script
    # session['applicant_script'] = ''
    # session['interview_script'] = ''


    disco_data = get_discovery_data()
    skill_data = get_job_skills()
    entities = get_disco_entites()

    org = get_org_val(entities)
    comp = get_comp_val(entities)
    fac = get_fac_val(entities)

    in_skills = compare_skill_disco(skill_data,disco_data)

    language = filter_prog_lang(in_skills)
    # language = ""
    skill = filter_skill(in_skills)
    extract_emotion()

    if language == "":
        filter_job_lang(skill_data)
    else:
        session['job_lang_1'] = ""
        session['job_lang_2'] = ""
        session['job_lang_3'] = ""
        session['job_lang_4'] = ""

    session['organization'] = org
    session['company'] = comp
    session['facility'] = fac
    session['lang_skill'] = language
    session['found_skill'] = skill
    session['name'] = session['document']['firstname']
    session['room'] = session['document']['_id']


    session['logical_question'] = 'False'
    session['options_question'] = 'False'

    if session['name'] != '':
        return redirect(url_for('.chat'))

    return render_template('chat_index.html')

# Get applicant's data
def get_applic_data():
    # Connect to the applicant's discovery data
    for doc in appi_db:
        if doc['_id'] == session['document']['_id']:
            local_document = doc
    s = json.dumps(local_document)
    loc_document = json.loads(s)

    return loc_document

# Get keywords and concepts from applicant's discovery data
def get_discovery_data():

    disco_skills = []
    loc_document = get_applic_data()
    # Extract concepts and add them to disco_skills
    for element in loc_document['discovery']['concepts']:
        if float(element['relevance']) > 0.6:
            disco_skills.append(element['text'])

    # Extract keywords and add them to disco_skills
    for element in loc_document['discovery']['keywords']:
        if float(element['relevance']) > 0.57:
            disco_skills.append(element['text'])

    return disco_skills

# Get the skills from the applied job
def get_job_skills():

    skill_list = []
    loc_document = get_applic_data()
    job_ref = loc_document['job_ref']
    db = client['jobs']

    for job in db:
        if job['_id'] == job_ref:
            for skill in job['skills']:
                skill_list.append(skill['name'])

    return skill_list

# Look what languages are required by the job and add them to session
def filter_job_lang(skill_list):
    lang_list = []
    for lang in lang_skills:
        for skill in skill_list:
            if str(lang) == str(skill.lower()):
                lang_list.append(lang)
    for i,lang in enumerate(lang_list):
        session['job_lang_' + format(i+1)] = lang


# Identify the programming language from the found skills
def filter_prog_lang(in_skills):
    language = ""
    for lang in lang_skills:
        for skill in in_skills:
            if str(lang) == str(skill):
                language = lang
                return language
            else:
                language = ""
    return language

# Identify the software skills that are found in the applicant data
def filter_skill(in_skills):
    found_skill = ""
    for skill in db_skills:
        for in_skill in in_skills:
            if str(skill) == str(in_skill):
                found_skill = in_skill.lower()
                return found_skill
            else:
                found_skill = ""
    return found_skill

# Compare job skills and discovery skills
def compare_skill_disco(skills,disco):
    in_list = []

    for skill in skills:
        for disco_skill in disco:
            if skill.lower() in disco_skill.lower():
                in_list.append(skill.lower())

    return in_list

# Get discovery entities from the applicant's data
def get_disco_entites():
    disco_entities = {}
    loc_document = get_applic_data()

    # Extract entities and add them to disco_entities
    for element in loc_document['discovery']['entities']:
        if float(element['relevance']) > 0.47:
            disco_entities[element['type']] = element['text']

    return disco_entities

def extract_emotion():
    loc_document = get_applic_data()

    session['disgust'] = loc_document['discovery']['emotion']['document']['emotion']['disgust']
    session['joy'] = loc_document['discovery']['emotion']['document']['emotion']['joy']
    session['anger'] = loc_document['discovery']['emotion']['document']['emotion']['anger']
    session['fear'] = loc_document['discovery']['emotion']['document']['emotion']['fear']
    session['sadness'] = loc_document['discovery']['emotion']['document']['emotion']['sadness']

def get_org_val(entities):
    org_val = ""
    for k,v in entities.items():
        if k == "Organization":
            org_val = v
            return org_val

    return org_val

def get_comp_val(entities):
    comp_val = ""
    for k,v in entities.items():
        if k == "Company":
            comp_val = v
            return comp_val

    return comp_val

def get_fac_val(entities):
    fac_val = ""
    for k,v in entities.items():
        if k == "Facility":
            fac_val = v
            return fac_val

    return fac_val

@app.route('/chat')
def chat():
    """Chat room. The user's name and room must be stored in
    the session."""
    name = session.get('name', '')

    if name == '':
        return redirect(url_for('.login'))

    
    return render_template('chat.html', name=name)



# Events
@socketio.on('joined', namespace='/chat')
def joined(message):
    """Sent by clients when they enter a room.
    A status message is broadcast to the applicant in the room."""
    room = session.get('room')
    join_room(room)

    # Welcoming the user with a personalised message **issue_17**
    response = service.message(
        assistant_id='bbfcb3fd-6703-4bd5-8b6b-5ecefc71086e',
        session_id=session['current_session'],
        context= { 'skills': {
                                'main skill': {
                                    'user_defined': {
                                        'applicant_name': session['name'],
                                        'job_position': session['job_title'],
                                        'lang_skill': str(session['lang_skill']),
                                        'soft_skill': str(session['found_skill']),
                                        'org_val': str(session['organization']),
                                        'comp_val': str(session['company']),
                                        'fac_val': str(session['facility']),
                                        'job_lang_1': str(session['job_lang_1']),
                                        'job_lang_2': str(session['job_lang_2']),
                                        'job_lang_3': str(session['job_lang_3']),
                                        'job_lang_4': str(session['job_lang_4'])
                                    }
                                }
                            }
                }
    ).get_result()
    # Welcoming message
    emit('message', {'msg': str(response['output']['generic'][0]['text'])}, room=room)
    session['interview_script'] = str(response['output']['generic'][0]['text']) + '\n'

# Function that deals with one step process
def tone_assistant(message):
    # If interview is finished then redirect

    # Use Tone Analyser on applicant's first response and send the result via context in the next request
    tone_analysis = tone_analyzer.tone(
        {'text': message['msg']},
        content_type='application/json'
    ).get_result()

    # This should be done only for the first question 
    # Until is reaching the core of the interview
    detect_sad = False
    # # If I am in the core part of the interview then stop analysing the sentiment
    if session['jump_to_core'] == False:
        for tone in tone_analysis['document_tone']['tones']:
            if (tone['tone_id'] == 'sadness' or tone['tone_id'] == 'anger' or tone['tone_id'] == 'fear'):
                detect_sad  = True
 

    if session['jump_to_core'] == False and detect_sad == False:
        session['jump_to_core'] = True
    else:
        if (session['jump_to_core'] == True):
            session['jump_to_core'] = True


        else:
            session['jump_to_core'] = False

            if session['first_mood'] == 'null':
                session['first_mood'] = True
            else:
                session['first_mood'] = False

    # Send the tone analyser variable with the next request
    response = service.message(
        assistant_id='bbfcb3fd-6703-4bd5-8b6b-5ecefc71086e',
        session_id=session['current_session'],
        input={
            'message_type': 'text',
            'text': message['msg']
        },
        context= { 'skills': {
                                'main skill': {
                                    'user_defined': {
                                        'jump_to_core': str(session['jump_to_core']),
                                        'first_mood': str(session['first_mood']),
                                        'inside_core': str(session['inside_core']),
                                        'jump_to_final': str(session['jump_to_final']),
                                        'inside_final': str(session['inside_final'])
                                    }
                                }
                            }
                }
    ).get_result()


    # Here I check for consent to get to core


    
    try:
        if (session['jump_to_core'] == True and response['output']['intents'][0]['intent'] == 'Consent'): 
            session['inside_core'] = True
            session['jump_to_core'] = False
    except:
        print("Intent not found")

  

    # Preparing to got final THIS NEEDS TO CHANGE
    try:
    
        if (session['inside_final'] == True and session['final_questions'] == 'True'):
         
            # make another request
            response = service.message(
                assistant_id='bbfcb3fd-6703-4bd5-8b6b-5ecefc71086e',
                session_id=session['current_session'],
                input={
                    'message_type': 'text',
                    'text': message['msg']
                },
                context= { 'skills': {
                                        'main skill': {
                                            'user_defined': {
                                                'jump_to_core': str(session['jump_to_core']),
                                                'first_mood': str(session['first_mood']),
                                                'inside_core': str(session['inside_core']),
                                                'jump_to_final': str(session['jump_to_final']),
                                                'inside_final': str(session['inside_final']),
                                                'finish_interview': str(session['finish_interview'])
                                            }
                                        }
                                    }
                        }
            ).get_result()
         
        #Isolating for now the final part of the interview
        if (session['jump_to_final'] == True and response['output']['intents'][0]['intent'] == 'Consent'):
            session['jump_to_final'] = False
            session['inside_final'] = True
            session['inside_core'] = False  

        if(session['inside_final'] == True):
            session['jump_to_final'] = False

        if(session['inside_core'] == True):
            session['jump_to_core'] = False

        # The applicant wants to finish the interview
        if (session['inside_final'] == True and session['exit_interview'] == 'True'):
            session['finish_interview'] = True
               
        # questions for salaries not detected + the above rolue dos not seem correct

    except:
        print("Not ready to try")


    return response


@socketio.on('text', namespace='/chat')
def text(message):    
    room = session.get('room')
    #global jump_to_core
    jump_to_core = session['jump_to_core']

    if message != '':
        response = tone_assistant(message)

    # try unpacking image question
    try:
        session['logical_question'] = response['output']['user_defined']['context']['logical_question']
    except:
        print("Logical question not found")

    # try to find final questions
    try:
        session['final_questions'] = response['output']['user_defined']['context']['final_questions']
    except:
        print("final q not f found")

    # try to find exit 
    try:
        session['exit_interview'] = response['output']['user_defined']['context']['exit_interview']

    except:
        print("EXIT NOT FOUND")

    # try to get the moment when to jump to the final stage of the interview
    try:
        session['jump_to_final'] = response['output']['user_defined']['context']['jump_to_final']
        session['inside_final'] = True
    except:
        print("Final question not found")

    number_of_replies = 0
    if(session['finish_interview'] == False):
        number_of_replies = len(response['output']['generic'])

    if(session['logical_question'] == 'False'): 
        # add to general script
        session['interview_script'] += 'Applicant: ' + str(message['msg']) + '\n'
        # add to applicant script

        emit('message1', {'msg': message['msg'], 'name': session.get('name')}, room=room)
        i = 0
        while i != number_of_replies:
            chat_response = response['output']['generic'][i]['text']
            session['interview_script'] += 'Bot: ' + str(chat_response ) + '\n'
            emit('message', {'msg': str(chat_response)}, room=room)
            i += 1

    else:
            emit('message1', {'msg': message['msg'], 'name': session.get('name')}, room=room)
            session['interview_script'] += 'Applicant: ' + str(message['msg']) + '\n'

            emit('image_message', {'msg': response['output']['generic'][0]['description'], 'source': response['output']['generic'][0]['source']}, room=room)
            session['interview_script'] += 'Bot: ' + str(response['output']['generic'][0]['description']) + '\n'

    session['logical_question'] = 'False'

       
    if (session['finish_interview'] == True):

        # stop the interview here 10.43 25/04
    
        emit('disconnect', {'script':str(session['interview_script'])})

@app.route('/hr_view', methods=['GET', 'POST'])
def hr_view():
    labels = ['disgust', 'joy', 'anger', 'fear', 'sadness']
    sent = []
    total = 0
    total = total + session['disgust']
    total = total + session['joy']
    total = total + session['anger']
    total = total + session['fear']
    total = total + session['sadness']

    sent.append(round(session['disgust']/total*100))
    sent.append(round(session['joy']/total*100))
    sent.append(round(session['anger']/total*100))
    sent.append(round(session['fear']/total*100))
    sent.append(round(session['sadness']/total*100))

    if request.method == 'GET':
            print("GET")
            
    if request.method == 'POST':
        if(str(request.get_json()) != 'None'):
            session['a'] = request.get_json().split('\n')
        else:
            session['a'] = ""

    
   
    return render_template('hr_view.html', data=session['a'], sent=sent, labels=labels)

    
@atexit.register
def shutdown():
    if client:
        client.disconnect()

if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=port, debug=True)
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
