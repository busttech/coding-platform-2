from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
import subprocess
import sys
import os
import tempfile

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CA_CERT_PATH = os.path.join(BASE_DIR, 'certs/isrgrootx1.pem')
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f'mysql+pymysql://3QkyK3w5GoLuPjo.root:r8jhtPzQbNRtJaSF@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/tes1?ssl_ca={CA_CERT_PATH}'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.secret_key = os.urandom(24)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    function_name = db.Column(db.String(100), nullable=False)
    parameters = db.Column(db.String(16), nullable=False)
    test_cases = db.relationship('TestCase', backref='question', lazy=True)

class TestCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    input_data = db.Column(db.Text, nullable=False)
    expected_output = db.Column(db.Text, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_code = db.Column(db.Text, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    result = db.Column(db.String(16), nullable=False)
class SubmissionAll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_code = db.Column(db.Text, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    result = db.Column(db.String(16), nullable=False)


@app.route("/")
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'room330' and password == '329330':
            session['logged_in'] = True
            return redirect(url_for('teacher'))
        else:
            return render_template('login.html', error="Invalid credentials, please try again.")
    return render_template('login.html')

@app.route('/teacher', methods=['GET', 'POST'])
def teacher():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        data = request.json
        question = Question(
            title=data['title'],
            description=data['description'],
            parameters = data['parameters'],
            function_name=data['function_name']
        )
        db.session.add(question)
        db.session.commit()
        for case in data['test_cases']:
            test_case = TestCase(
                input_data=case['input'],
                expected_output=case['output'],
                question_id=question.id
            )
            db.session.add(test_case)
        db.session.commit()
        return jsonify({'message': 'Question added successfully!'}), 201
    return render_template('teacher.html')

@app.route('/student')
def student():
    questions = Question.query.all()
    return render_template('student.html', questions=questions)
@app.route('/Allquestions')
def showallquestions():
    questions = Question.query.all()
    return render_template('Allquestions.html', questions=questions)

@app.route('/editor/<int:question_id>')
def editor(question_id):
    question = Question.query.get_or_404(question_id)
    return render_template('editor.html', question=question)
@app.route('/editor')
def practiceditor():
    question = {
        "title": "Practice question",
        "description": "You can write code in code editor and then ",
        "function_name": "function",
        "parameters":"a"
    }
    return render_template('editor.html',question=question)
@app.route('/run_code', methods=['POST'])
def run_code():
    code = request.json.get('code')
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.py')
    temp_file.write(code.encode())
    temp_file.close()
    try:
        result = subprocess.run([sys.executable, temp_file.name], capture_output=True, text=True)
        os.remove(temp_file.name)
        output = result.stdout if result.returncode == 0 else result.stderr
        return jsonify({'output': output, 'status': 'success'})
    except Exception as e:
        return jsonify({'output': str(e), 'status': 'error'})

@app.route('/submit_code/<int:question_id>', methods=['POST'])
def submit_code(question_id):
    code = request.json.get('code')
    question = Question.query.get_or_404(question_id)
    test_cases = TestCase.query.filter_by(question_id=question.id).all()
    results = []
    all_passed = True
    for case in test_cases:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.py')
        temp_file.write(code.encode())
        temp_file.close()
        input_data = case.input_data
        try:
            with open(temp_file.name, 'a') as f:
                f.write(f'\nprint({question.function_name}({input_data}))')
            result = subprocess.run([sys.executable, temp_file.name], capture_output=True, text=True)
            output = result.stdout.strip()
            passed = output == case.expected_output
            if not passed:
                all_passed = False
            results.append({
                'input': input_data, 
                'expected': case.expected_output, 
                'output': output, 
                'passed': passed
            })
            os.remove(temp_file.name)
        except Exception as e:
            results.append({'error': str(e)})
    if all_passed:
        submission = Submission(student_code=code, question_id=question_id, result="Passed")
        db.session.add(submission)
        db.session.commit()
    elif not all_passed :
        submissiondsd = SubmissionAll(student_code=code, question_id=question_id, result="Passed" if all_passed else "Failed")
        db.session.add(submissiondsd)
        db.session.commit()
    return jsonify({'results': results, 'status': 'success' if all_passed else 'failure'})

@app.route('/passedsub/<int:question_id>')
def view_submissions(question_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    question = Question.query.get_or_404(question_id)
    submissions = Submission.query.filter_by(question_id=question_id).all()
    has_passed_submission = any(submission.result == 'Passed' for submission in submissions)
    return render_template('submission.html', question=question, submissions=submissions, has_passed_submission=has_passed_submission)
@app.route('/failedsub/<int:question_id>')
def view_failed_submissions(question_id):
    question = Question.query.get_or_404(question_id)
    submissions = SubmissionAll.query.filter_by(question_id=question_id).all()
    return render_template('submission.html', question=question, submissions=submissions)
@app.route('/logout')
def logout():
    session['logged_in'] = False
    return redirect(url_for("login"))
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)