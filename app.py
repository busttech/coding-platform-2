from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import subprocess
import sys
import os
import tempfile

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:tarun@localhost/co12'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Database Models
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    function_name = db.Column(db.String(100), nullable=False)
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
    result = db.Column(db.Text, nullable=False)

@app.route("/")
def home():
    return render_template('index.html')
# Teacher Page - Add Questions
@app.route('/teacher', methods=['GET', 'POST'])
def teacher():
    if request.method == 'POST':
        data = request.json
        question = Question(
            title=data['title'],
            description=data['description'],
            function_name=data['function_name']
        )
        db.session.add(question)
        db.session.commit()

        # Save test cases
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


# Student Page - List Questions
@app.route('/student')
def student():
    questions = Question.query.all()
    return render_template('student.html', questions=questions)


# Code Editor Page
@app.route('/editor/<int:question_id>')
def editor(question_id):
    question = Question.query.get_or_404(question_id)
    return render_template('editor.html', question=question)


# Run Code
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


# Submit Code
@app.route('/submit_code/<int:question_id>', methods=['POST'])
def submit_code(question_id):
    code = request.json.get('code')
    question = Question.query.get_or_404(question_id)
    test_cases = TestCase.query.filter_by(question_id=question.id).all()

    results = []
    for case in test_cases:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.py')
        temp_file.write(code.encode())
        temp_file.close()

        # Modify test case to call the function
        with open(temp_file.name, 'a') as f:
            f.write(f'\nprint({question.function_name}({case.input_data}))')

        try:
            result = subprocess.run([sys.executable, temp_file.name], capture_output=True, text=True)
            output = result.stdout.strip()
            passed = output == case.expected_output
            results.append({'input': case.input_data, 'expected': case.expected_output, 'output': output, 'passed': passed})
            os.remove(temp_file.name)
        except Exception as e:
            results.append({'error': str(e)})

    all_passed = all(r.get('passed', False) for r in results)
    submission = Submission(student_code=code, question_id=question_id, result="Passed" if all_passed else "Failed")
    db.session.add(submission)
    db.session.commit()
    return jsonify({'results': results, 'status': 'success' if all_passed else 'failure'})


# View Submissions (Teacher)
@app.route('/submissions/<int:question_id>')
def view_submissions(question_id):
    question = Question.query.get_or_404(question_id)
    submissions = Submission.query.filter_by(question_id=question_id).all()
    return render_template('submissions.html', question=question, submissions=submissions)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)


