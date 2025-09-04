#application.py
import statistics
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_file
from datetime import datetime, timedelta
from flask import request, redirect, url_for, render_template
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import JSON, JSONB, ARRAY, VARCHAR
import random, time, datetime
from datetime import datetime, date, timezone, timedelta
from dateutil.relativedelta import relativedelta
import random
import string
import pandas as pd
import io
from sqlalchemy.orm import aliased
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError
from collections import defaultdict
from sqlalchemy import Enum, text, Sequence, TIMESTAMP, Date, select, func,bindparam,or_, and_
from sqlalchemy.dialects.postgresql import ENUM
from functools import wraps
import MockTestQuestionsGenerator, CustomModulesQuestionsGenerator, DailyPracticeQuestionsGenerator
import json
import re
import boto3
import razorpay
import uuid
import hmac
import hashlib
import requests

# region Variables
application = Flask(__name__)
application.config['SECRET_KEY'] = 'your_secret_key'
application.config['MAIL_SERVER'] = 'smtp.hostinger.com'
application.config['MAIL_PORT'] = 587
application.config['MAIL_USE_TLS'] = True
application.config['MAIL_USERNAME'] = 'notifications@thinktests.com'
application.config['MAIL_PASSWORD'] = 'Thinktests@2025'

application.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://Thinktest:Thinktest2025@thinktestsdb.c3sk8iamux7s.ap-south-1.rds.amazonaws.com:5432/thinktestdb'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

application.config['TWOFACTOR_API_KEY'] = '5847b1a6-63c2-11f0-a562-0200cd936042'
application.config['TWOFACTOR_OTP_TEMPLATE'] = 'OTP+Verification'

application.config['RAZORPAY_ACCESS_KEY_ID'] = 'rzp_live_eWopTzOpSzZK6y'
application.config['RAZORPAY_SECRET_ACCESS_KEY'] = 'bMj92jaHjr9Tx4EQlbhG319U'

mail = Mail(application)
otp_storage = {}
verified_emails = {}
verified_phoneNumbers = {}
db = SQLAlchemy(application)

s3 = boto3.client('s3')

BUCKET_NAME = 'thinktestsimages'

razorpay_client = razorpay.Client(auth=(
    application.config['RAZORPAY_ACCESS_KEY_ID'],
    application.config['RAZORPAY_SECRET_ACCESS_KEY']
))

# endregion

# region Models

class Login(db.Model):
    __tablename__ = 'Login'
    __table_args__ = {'schema': 'registration'}

    student_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)

class Student(db.Model):
    __tablename__ = 'Student'
    __table_args__ = {'schema': 'registration'}

    student_id = db.Column(db.Integer, db.ForeignKey('registration.Login.student_id', ondelete='CASCADE'), primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(1), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    email = db.Column(db.String(255), db.ForeignKey('registration.Login.email', ondelete='CASCADE'), nullable=False, unique=True)
    contact_no = db.Column(db.String(10), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    subject_interests = db.Column(db.String(255))
    exam_interests = db.Column(db.String(255))
    last_subscription = db.Column(db.Integer, db.ForeignKey('registration.subscription.subscription_id', ondelete='SET NULL'), nullable=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('registration.Institution.institution_id', ondelete='SET NULL'), nullable=True)
    enrolment_date = db.Column(db.Date, nullable=False)

    # Relationships
    # subscriptions = db.relationship('Subscription', backref='student', passive_deletes=True)
    # Relationship to the last_subscription if needed:
    # last_sub = db.relationship('Subscription', foreign_keys=[last_subscription], post_update=True)

class Subscription(db.Model):
    __tablename__ = 'subscription'
    __table_args__ = {'schema': 'registration'}

    subscription_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('registration.Student.student_id', ondelete='CASCADE'))
    status = db.Column(db.Boolean, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('paymentplans.paymentplandetails.plan_id', ondelete='SET NULL'), nullable=True)

    # Relationships
    # plan = db.relationship('PaymentPlanDetail', backref='subscriptions')

class PaymentPlanDetail(db.Model):
    __tablename__ = 'paymentplandetails'
    __table_args__ = {'schema': 'paymentplans'}

    plan_id = db.Column(db.Integer, primary_key=True)
    plan_name = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.Interval, nullable=False)
    cost = db.Column(db.Numeric(10, 2), nullable=False)

    # Define relationships
    # subscriptions = db.relationship('Subscription', backref='plan')

class InstitutionLogin(db.Model):
    __tablename__ = 'InstitutionLogin'
    __table_args__ = {'schema': 'registration'}

    institution_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)

class Institution(db.Model):
    __tablename__ = 'Institution'
    __table_args__ = {'schema': 'registration'}

    institution_id = db.Column(db.Integer, db.ForeignKey('registration.InstitutionLogin.institution_id', ondelete='CASCADE'), primary_key=True)
    institution_name = db.Column(db.String(255), nullable=False)
    enrolment_date = db.Column(db.Date, nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    contact_no = db.Column(db.String(15), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    last_subscription = db.Column(db.Integer, db.ForeignKey('registration.InstitutionSubscription.subscription_id'))
    address = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    no_of_students = db.Column(db.Integer, nullable=False, default=0)

    # Explicitly define relationships to avoid ambiguity
    subscriptions = db.relationship('InstitutionSubscription', 
                                    foreign_keys='InstitutionSubscription.institution_id', 
                                    backref='institution', lazy=True)
    last_subscription_ref = db.relationship('InstitutionSubscription', 
                                            foreign_keys=[last_subscription], 
                                            backref='last_institution', lazy=True)
    
    students = db.relationship('Student', backref='institution', lazy=True)

class InstitutionSubscription(db.Model):
    __tablename__ = 'InstitutionSubscription'
    __table_args__ = {'schema': 'registration'}

    subscription_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('registration.Institution.institution_id'), nullable=False)
    status = db.Column(db.Boolean, nullable=False, default=True)  # True = Active, False = Inactive
    # start_date = db.Column(db.Date, nullable=False)
    # end_date = db.Column(db.Date, nullable=False)
    # plan_id = db.Column(db.Integer, db.ForeignKey('paymentplans.paymentplandetails.plan_id'), nullable=False)

    # # Relationship
    # plan = db.relationship('PaymentPlanDetail', backref='institution_subscriptions', lazy=True)

class Direction(db.Model):
    __tablename__ = 'direction'
    __table_args__ = {'schema': 'meta'}

    direction_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    direction_description = db.Column(db.Text, nullable=False)
    
class MockExam(db.Model):
    __tablename__ = 'mockexam'
    __table_args__ = {'schema': 'mocktest'}

    exam_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exam_name = db.Column(db.String(100), nullable=False)
    exam_duration = db.Column(db.Interval, nullable=False)
    general_instructions = db.Column(db.Text, nullable=False)
    exam_difficulty = db.Column(db.Enum('Easy', 'Medium', 'Difficult', name='exam_difficulty_enum'))
    
class Module(db.Model):
    __tablename__ = 'module'
    __table_args__ = {'schema': 'meta'}

    module_id = db.Column(db.Integer, Sequence('module_module_id_seq', schema='meta'), primary_key=True, autoincrement=True)
    module_name = db.Column(VARCHAR(100), nullable=False)
    # subject_id = db.Column(db.Integer, db.ForeignKey('meta.subject.subject_id'), nullable=False)

class SubjectModuleMapping(db.Model):
    __tablename__ = 'subject_module_mapping'
    __table_args__ = {'schema': 'meta'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('meta.subject.subject_id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('meta.module.module_id'), nullable=False)

    # Relationships (optional, not mandatory but good)
    subject = db.relationship('Subject', backref='module_mappings')
    module = db.relationship('Module', backref='subject_mappings')

class Question(db.Model):
    __tablename__ = 'question'
    __table_args__ = {'schema': 'meta'}

    q_id = db.Column(db.Integer, Sequence('question_q_id_seq', schema='meta'), primary_key=True, autoincrement=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('meta.subject.subject_id'), nullable=False)
    direction_id = db.Column(db.Integer, db.ForeignKey('meta.direction.direction_id'), nullable=False)
    question_description = db.Column(db.Text, nullable=False)
    answer_options = db.Column(JSONB, nullable=False)
    choice_type = db.Column(ENUM('text', 'image', name='choice_type_enum', schema='meta'), nullable=True)
    max_score = db.Column(db.Integer, nullable=False)
    solution_explanation = db.Column(db.Text, nullable=True)
    difficulty_level = db.Column(db.Integer, db.CheckConstraint('difficulty_level >= 1 AND difficulty_level <= 5'), nullable=True)
    multi_select = db.Column(db.Boolean, nullable=True)
    correct_option = db.Column(ARRAY(db.Text), nullable=True)
    module_id = db.Column(db.Integer, db.ForeignKey('meta.module.module_id'), nullable=True)    

class Subject(db.Model):
    __tablename__ = 'subject'
    __table_args__ = {'schema': 'meta'}

    subject_id = db.Column(db.Integer, Sequence('subject_subject_id_seq', schema='meta'), primary_key=True, autoincrement=True)
    subject_name = db.Column(db.String(100), nullable=False)

class UserResponse(db.Model):
    __tablename__ = 'userresponse'
    __table_args__ = {'schema': 'mocktest'}

    response_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    q_id = db.Column(db.Integer, db.ForeignKey('meta.question.q_id'), nullable=False)
    # time_spent = db.Column(db.Interval, nullable=False)
    response = db.Column(db.String(20), db.CheckConstraint("response IN ('correct', 'incorrect', 'skipped')"), nullable=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('mocktest.attempt.attempt_id'), nullable=True)
    q_order = db.Column(db.Integer, nullable=True)
    selected_option = db.Column(ARRAY(db.Text), nullable=True)
    question_status = db.Column(
        Enum('answered', 'not_answered', 'marked_for_review', 'not_attempted', name='question_status_enum'),
        nullable=False,
        default='not_answered'
    )

    def __repr__(self) -> str:
        return f'{self.response_id} - {self.response}'
    
class MockTestAttempt(db.Model):
    __tablename__ = 'attempt'
    __table_args__ = {'schema': 'mocktest'}

    attempt_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('registration.Login.student_id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('mocktest.mockexam.exam_id'), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    resume_time = db.Column(db.Interval, nullable=False)
    resume_test = db.Column(db.String(10), nullable=True)

class MockExamConfig(db.Model):
    __tablename__ = 'config'
    __table_args__ = {'schema': 'mocktest'}

    exam_id = db.Column(db.Integer, db.ForeignKey('mocktest.mockexam.exam_id'), primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('meta.subject.subject_id'), primary_key=True)
    q_diff = db.Column(JSON, nullable=False)

class CustomModuleAttempt(db.Model):
    __tablename__ = 'attempt'
    __table_args__ = {'schema': 'custommodules'}

    attempt_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('registration.Student.student_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    resume_test = db.Column(db.String, nullable=False)

class CustomModuleConfig(db.Model):
    __tablename__ = 'config'
    __table_args__ = {'schema': 'custommodules'}
    
    config_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('registration.Student.student_id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('meta.subject.subject_id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('meta.module.module_id'), nullable=False)
    difficulty_level = db.Column(db.Integer, db.CheckConstraint('difficulty_level >= 1 AND difficulty_level <= 5'), nullable=True)
    question_count = db.Column(db.Integer, nullable=False)
    attempt_id = db.Column(db.Integer,db.ForeignKey('custommodules.attempt.attempt_id'),nullable=False) 

class CustomModuleUserResponse(db.Model):
    __tablename__ = 'userresponse'
    __table_args__ = (
        db.CheckConstraint("response = ANY (ARRAY['correct', 'incorrect', 'skipped'])"),
        {'schema': 'custommodules', 'extend_existing': True}
    )
    
    response_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    q_id = db.Column(db.Integer, db.ForeignKey('meta.question.q_id'), nullable=False)
    response = db.Column(VARCHAR(20), nullable=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('custommodules.attempt.attempt_id'), nullable=True)
    q_order = db.Column(db.Integer, nullable=True)
    selected_option = db.Column(ARRAY(db.Text), nullable=True)
    question_status = db.Column(
        Enum('answered', 'not_answered', 'marked_for_review', 'not_attempted', name='question_status_enum'),
        nullable=False,
        default='not_answered'
    )

class DailyPracticeAttempt(db.Model):
    __tablename__ = 'attempt'
    __table_args__ = {'schema': 'dailypractice'}

    attempt_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('registration.Student.student_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    resume_test = db.Column(db.String, nullable=False)

class DailyPracticeConfig(db.Model):
    __tablename__ = 'config'
    __table_args__ = {'schema': 'dailypractice'}
    
    config_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('registration.Student.student_id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('meta.subject.subject_id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('meta.module.module_id'), nullable=False)
    difficulty_level = db.Column(db.Integer, db.CheckConstraint('difficulty_level >= 1 AND difficulty_level <= 5'), nullable=True)
    question_count = db.Column(db.Integer, nullable=False)
    attempt_id = db.Column(db.Integer,db.ForeignKey('dailypractice.attempt.attempt_id'),nullable=False) 

class DailyPracticeUserResponse(db.Model):
    __tablename__ = 'userresponse'
    __table_args__ = (
        db.CheckConstraint("response = ANY (ARRAY['correct', 'incorrect', 'skipped'])"),
        {'schema': 'dailypractice', 'extend_existing': True}
    )
    
    response_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    q_id = db.Column(db.Integer, db.ForeignKey('meta.question.q_id'), nullable=False)
    response = db.Column(VARCHAR(20), nullable=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('dailypractice.attempt.attempt_id'), nullable=True)
    q_order = db.Column(db.Integer, nullable=True)
    selected_option = db.Column(ARRAY(db.Text), nullable=True)
    question_status = db.Column(
        Enum('answered', 'not_answered', 'marked_for_review', 'not_attempted', name='question_status_enum'),
        nullable=False,
        default='not_answered'
    )

class Exam(db.Model):
    __tablename__ = 'exam'
    __table_args__ = {'schema': 'competitiveexams'}

    exam_id = db.Column(db.Integer, primary_key=True)
    exam_name = db.Column(db.String(255), nullable=False)
    category_id = db.Column(db.Integer)
    exam_description = db.Column(db.String(500))
    updatedon = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    year = db.Column(db.Integer, default=datetime.today().year)
    prepares  = db.relationship('ExamPrepare',  passive_deletes=True)
    patterns  = db.relationship('ExamPattern',  passive_deletes=True)
    calendars = db.relationship('ExamCalendar', passive_deletes=True)

class ExamCategory(db.Model):
    __tablename__ = 'examcategory'
    __table_args__ = {'schema': 'competitiveexams'}

    category_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category_name = db.Column(db.String(255), nullable=False, unique=True)

    def __repr__(self):
        return f"<ExamCategory(category_id={self.category_id}, category_name='{self.category_name}')>"

class ExamPrepare(db.Model):
    __tablename__ = 'examprepare'
    __table_args__ = {'schema': 'competitiveexams'}

    exam_id = db.Column(db.Integer, db.ForeignKey('competitiveexams.exam.exam_id', ondelete='CASCADE'), primary_key=True)
    mockdesc = db.Column(db.Text)
    dailydesc = db.Column(db.Text)
    customdesc = db.Column(db.Text)
    additionalinf = db.Column(db.Text)

class ExamPattern(db.Model):
    __tablename__ = 'exampattern'
    __table_args__ = {'schema': 'competitiveexams'}

    pattern_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('competitiveexams.exam.exam_id', ondelete='CASCADE'), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    no_questions = db.Column(db.Integer, nullable=False)
    marks = db.Column(db.Integer, nullable=False)
    time_alloted = db.Column(db.Interval, nullable=False)

class ExamCalendar(db.Model):
    __tablename__ = 'examcalendar'
    __table_args__ = {'schema': 'competitiveexams'}

    calendar_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    schedule_of_events = db.Column(db.String(255), nullable=False)
    important_dates = db.Column(db.Date)
    exam_id = db.Column(db.Integer, db.ForeignKey('competitiveexams.exam.exam_id', ondelete='CASCADE'), nullable=False)

class AdminLogin(db.Model):
    __tablename__ = 'AdminLogin'
    __table_args__ = {'schema': 'registration'}

    admin_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)

 # endregion

# region Registration

@application.route('/create_order', methods=['POST'])
def create_order():
    data = request.get_json()
    amount = int(data.get('amount'))  # in paise
    receipt_id = f"order_rcptid_{data['email'].split('@')[0]}_{uuid.uuid4().hex[:8]}"

    try:
        razorpay_order = razorpay_client.order.create({
        "amount": amount,
        "currency": "INR",
        "receipt": receipt_id,
        "payment_capture": 1
        })

        return jsonify({"order_id": razorpay_order['id']})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@application.route('/verify_payment', methods=['POST'])
def verify_payment():
    data = request.get_json()
    payment_id = data['razorpay_payment_id']
    order_id = data['razorpay_order_id']
    signature = data['razorpay_signature']

    generated_signature = hmac.new(
        application.config['RAZORPAY_SECRET_ACCESS_KEY'].encode('utf-8'),
        f"{order_id}|{payment_id}".encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    if generated_signature == signature:
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'failure'}), 400

@application.route('/Registration')
def registration():
    current_date = datetime.now()
    ten_years_ago = current_date - timedelta(days=365 * 10)  # Note that you should also import timedelta
    max_date = ten_years_ago.strftime('%Y-%m-%d')

    # Fetch subjects and exams from the database
    subjects = Subject.query.all()
    exams = MockExam.query.all()

    # Process the exam names to remove the difficulty suffix and ensure uniqueness
    unique_exams = {}
    for exam in exams:
        name_parts = exam.exam_name.split('_')
        processed_exam_name = name_parts[0]
        if processed_exam_name not in unique_exams:
            unique_exams[processed_exam_name] = exam.exam_id

    # Convert the unique exams dictionary to a list of dictionaries for rendering
    processed_exams = [{'exam_id': exam_id, 'exam_name': exam_name} for exam_name, exam_id in unique_exams.items()]

    # Pass subjects and processed exams to the template
    message = request.args.get('message')
    
    plans = [
    {'id': p.plan_id, 'name': p.plan_name, 'cost': p.cost}
    for p in db.session.query(PaymentPlanDetail).all()
    ]
    
    return render_template('Registration.html', max_date=max_date, message=message, subjects=subjects, exams=processed_exams, plans=plans, razorpaykey = application.config['RAZORPAY_ACCESS_KEY_ID'])

@application.route('/proceed', methods=['POST'])
def proceed_to_login():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    gender = request.form['gender'][0]
    date_of_birth = request.form['date_of_birth']
    phone_number = request.form['phone']
    email_id = request.form['email']
    password = request.form['password']
    
    # Collect selected subject and exam interests
    selected_subjects = request.form.getlist('subject_interest')
    selected_exam_ids = request.form.getlist('exam_interest')

    # Convert selected exam IDs to names
    selected_exam_names = []
    for exam_id in selected_exam_ids:
        exam_id = exam_id + "_"
        exams = MockExam.query.filter(MockExam.exam_name.like(f"{exam_id}%")).all()
        for exam in exams:
            selected_exam_names.append(exam.exam_name)

    # Join the selected interests into comma-separated strings
    subject_interests = ','.join(selected_subjects)
    exam_interests = ','.join(selected_exam_names)

    if email_id not in verified_emails or not verified_emails[email_id]:
        return redirect(url_for('registration', message='Email not verified'))
    
    if phone_number not in verified_phoneNumbers or not verified_phoneNumbers[phone_number]:
        return redirect(url_for('registration', message='Phone Number not verified'))

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    new_login = Login(email=email_id, password=hashed_password)
    db.session.add(new_login)
    db.session.commit()

    current_utc_time = datetime.now(timezone.utc)
    today = current_utc_time.date()
    
    new_student = Student(
        student_id=new_login.student_id,
        first_name=first_name,
        last_name=last_name,
        gender=gender,
        dob=date_of_birth,
        email=email_id,
        contact_no=phone_number,
        password=hashed_password,
        subject_interests=subject_interests,
        exam_interests=exam_interests,
        institution_id = None,        
        enrolment_date = today
    )

    db.session.add(new_student)
    db.session.flush()  # get student_id

    # Create subscription
    plan_id = request.form.get('plan_id') or 1
    plan = PaymentPlanDetail.query.filter_by(plan_id=plan_id).first()

    if plan:
        start_date = today
        if plan.duration.days < 30:
            end_date = start_date + relativedelta(days=plan.duration.days)
        else:
            end_date = start_date + relativedelta(months=int(plan.duration.days / 30))
        new_subscription = Subscription(
            student_id=new_student.student_id,
            plan_id=plan_id,
            start_date=start_date,
            end_date=end_date,
            status=True
        )
        db.session.add(new_subscription)
        db.session.flush()
        new_student.last_subscription = new_subscription.subscription_id

    db.session.commit()
    return redirect(url_for('loginPage'))

# region Phone    
def check_phone_internal(phone):
    if not phone:
        return {'success': False, 'message': 'Enter the phone number'}

    student = Student.query.filter_by(contact_no=phone).first()
    if student:
        return {'success': False, 'message': 'Phone number already registered as student'}
    
    institution = Institution.query.filter_by(contact_no=phone).first()
    if institution:
        return {'success': False, 'message': 'Phone number already registered as institution'}
    
    return {'success': True}

@application.route('/check_phone', methods=['POST'])
def check_phone():
    data = request.json
    phone = data.get('phone')
    if not phone:
        return jsonify({'success': False, 'message': 'Enter the phone number'}), 400

    result = check_phone_internal(phone)  # Reuse the internal function
    return jsonify(result), 200

# def generate_sms_otp_order_id(prefix='v', length=3):
#     characters = string.ascii_lowercase + string.digits
#     random_string = ''.join(random.choice(characters) for _ in range(length))
#     timestamp = str(int(time.time() * 1000))  # Current time in milliseconds
#     return prefix + random_string + timestamp

@application.route('/sendMobileOTP', methods=['POST'])
def sendMobileOTP():
    data = request.get_json()
    phoneNumber = "+91" + data.get('phone')
    API_KEY = application.config['TWOFACTOR_API_KEY']
    OTP_TEMPLATE = application.config['TWOFACTOR_OTP_TEMPLATE']

    # Check if phone number is registered
    response = check_phone_internal(phoneNumber)
    # print(response)
    if not response['success']:
        return jsonify({'status': 'phone_registered'}), 400

    # Proceed to send OTP
    # channel = "SMS"
    # otpLength = "6"
    # orderId = generate_sms_otp_order_id()
    # session['orderId'] = orderId
    # hash = "hash"
    # expiry = "120"
    # client_id = application.config['SMS_CLIENT_ID']
    # client_secret = application.config['SMS_CLIENT_SECRET']

    try:
        # otp_details = OTPLessAuthSDK.OTP.send_otp(email=None, phoneNumber=phoneNumber, channel=channel, hash=hash, orderId=orderId, expiry=expiry, otpLength=otpLength, client_id=client_id, client_secret=client_secret)
        # print(f"details: {otp_details}")
        url = f"https://2factor.in/API/V1/{API_KEY}/SMS/{phoneNumber}/AUTOGEN/{OTP_TEMPLATE}"
        response = requests.get(url)
        return jsonify({'status': 'success'})
    except Exception as e:
        # print(f"An error occurred: {e}")
        return jsonify({'status': 'failure'})

@application.route('/verifyMobileOTP', methods=['GET' ,'POST'])
def verifyMobileOTP():
    # orderId = session['orderId']
    # client_id = application.config['SMS_CLIENT_ID']
    # client_secret = application.config['SMS_CLIENT_SECRET']
    API_KEY = application.config['TWOFACTOR_API_KEY']
    data = request.get_json()
    phoneNumber = data.get('phone')
    phoneNumberwCode = "+91" + phoneNumber
    otp = data.get('otp')
    # try:    
    #     otp_details = OTPLessAuthSDK.OTP.veriy_otp(orderId=orderId,email=None, otp=otp, phoneNumber=phoneNumberwCode, client_id=client_id, client_secret=client_secret)        
    #     isverified = otp_details['isOTPVerified']
    #     # if True:
    #     if isverified:
    #         verified_phoneNumbers[phoneNumber] = True
    #         return jsonify(status='success')
    #     else:
    #         return jsonify(status='failure')
    # except Exception as e:
    #     print(e)
    #     return jsonify(status='failure')
    url = f"https://2factor.in/API/V1/{API_KEY}/SMS/VERIFY3/{phoneNumberwCode}/{otp}"

    try:
        response = requests.get(url)
        data = response.json()
        if data.get("Status") == "Success":
            verified_phoneNumbers[phoneNumber] = True
            return jsonify(status='success')
        else:
            return jsonify(status='failure')
    except Exception as e:
        return jsonify({"status": "failure", "error": str(e)}), 500    
    
@application.route('/check_phone_verification_status', methods=['POST'])
def check_phone_verification_status():
    data = request.json
    phone = data.get('phone')
    if phone in verified_phoneNumbers and verified_phoneNumbers[phone]:
        return jsonify({'verified': True}), 200
    else:
        return jsonify({'verified': False}), 200

# endregion

# region Email

@application.route('/send_otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')
    if not email:
        return jsonify({'success': False, 'message': 'Enter the email'}), 400

    otp = random.randint(100000, 999999)
    otp_storage[email] = {'otp': otp, 'timestamp': time.time()}

    msg = Message('Your OTP Code', sender=application.config['MAIL_USERNAME'], recipients=[email])
    msg.body = f'Your OTP code is {otp}'
    mail.send(msg)

    return jsonify({'success': True}), 200

@application.route('/resend_otp', methods=['POST'])
def resend_otp():
    data = request.json
    email = data.get('email')
    if not email:
        return jsonify({'success': False, 'message': 'Enter the email'}), 400

    if email not in verified_emails or verified_emails[email]:
        return jsonify({'success': False, 'message': 'Email already verified or not registered'}), 400

    otp = random.randint(100000, 999999)
    otp_storage[email] = {'otp': otp, 'timestamp': time.time()}

    msg = Message('Your OTP Code', sender=application.config['MAIL_USERNAME'], recipients=[email])
    msg.body = f'Your OTP code is {otp}'
    mail.send(msg)

    return jsonify({'success': True}), 200

@application.route('/verify_otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')

    stored_otp = otp_storage.get(email)
    if not stored_otp:
        return jsonify({'success': False, 'message': 'Invalid OTP'}), 400

    current_time = time.time()
    if current_time - stored_otp['timestamp'] > 120:  # OTP expires in 2 minutes (120 seconds)
        del otp_storage[email]  # OTP expired, delete it
        return jsonify({'success': False, 'message': 'OTP expired'}), 400

    # if True:
    if stored_otp['otp'] == int(otp):
        del otp_storage[email]  # OTP is used, so delete it
        verified_emails[email] = True
        return jsonify({'success': True}), 200
    else:
        return jsonify({'success': False, 'message': 'Invalid OTP'}), 400
    
@application.route('/check_email', methods=['POST'])
def check_email():
    data = request.json
    email = data.get('email')

    if not email:
        return jsonify({'success': False, 'message': 'Enter the email'}), 400

    user = Login.query.filter_by(email=email).first()
    if user:
        return jsonify({'success': True}), 200
    
    
    institution = Institution.query.filter_by(email=email).first()
    if institution:
        return jsonify({'success': True}), 200
    
    return jsonify({'success': False, 'message': 'Email ID not registered'}), 400
    
@application.route('/check_verification_status', methods=['POST'])
def check_verification_status():
    data = request.json
    email = data.get('email')
    if email in verified_emails and verified_emails[email]:
        return jsonify({'verified': True}), 200
    else:
        return jsonify({'verified': False}), 200

# endregion

# endregion

# region Login

@application.route('/createSubscription', methods=['POST'])
def createSubscription():
    data = request.get_json()
    student_id = data.get('student_id')
    plan_id = data.get('plan_id')

    student = Student.query.filter_by(student_id=student_id).first()  
    start_date = datetime.utcnow().date()

    # Get plan duration
    plan = PaymentPlanDetail.query.filter_by(plan_id=plan_id).first()
    if not plan:
        return jsonify({'status': 'failed', 'reason': 'Invalid plan'}), 400

    # Calculate end date    
    if plan.duration.days < 30:
        end_date = start_date + relativedelta(days=plan.duration.days)
    else:
        end_date = start_date + relativedelta(months=int(plan.duration.days / 30))

    # Insert new subscription
    new_subscription = Subscription(
        student_id=student_id,
        plan_id=plan_id,
        start_date=start_date,
        end_date=end_date,
        status=True
    )

    db.session.add(new_subscription)
    db.session.flush()
    student.last_subscription = new_subscription.subscription_id
    db.session.commit()

    return jsonify({'status': 'success'})

def deactivate_expired_subscriptions(student_id):
    today = date.today()
    expired_subscriptions = Subscription.query.filter(
        Subscription.student_id == student_id,
        Subscription.status == True,
        Subscription.end_date.isnot(None),
        Subscription.end_date < today
    ).all()

    for sub in expired_subscriptions:
        sub.status = False

    db.session.commit()

@application.route('/', methods=['GET', 'POST'])
def loginPage():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password'] 
        login = Login.query.filter_by(email=email).first()
        student = Student.query.filter_by(email=email).first()
        institution = InstitutionLogin.query.filter_by(email=email).first()
        admin=AdminLogin.query.filter_by(email=email).first()
        current_utc_time = datetime.now(timezone.utc)
        today = current_utc_time.date()

        if login:
            deactivate_expired_subscriptions(login.student_id)
            plans = [
                    {'id': p.plan_id, 'name': p.plan_name, 'cost': p.cost}
                    for p in db.session.query(PaymentPlanDetail).all()
                    ]
            if check_password_hash(login.password, password):
                # Check subscription status
                # First, try to get the one with the latest non-null end_date
                subscription = Subscription.query.filter(
                    Subscription.student_id == login.student_id,
                    Subscription.end_date.isnot(None)
                ).order_by(Subscription.end_date.desc()).first()

                # If none found, fallback to one with end_date = None
                if not subscription:
                    subscription = Subscription.query.filter(
                        Subscription.student_id == login.student_id,
                        Subscription.end_date.is_(None)
                    ).first()

                if subscription and subscription.status and (subscription.end_date>=today or subscription.end_date==None):
                    session['user_id'] = login.student_id                    
                    verified_emails[email] = True
                    return redirect(url_for('dashboard'))
                elif (not(subscription.status) and subscription.end_date>=today) or (subscription.end_date<today and student.institution_id):
                    return render_template('Login.html', user="student", plans=plans, student=login, 
                    razorpaykey = application.config['RAZORPAY_ACCESS_KEY_ID'], show_subscription_expired_modal=False, show_subscription_inactive_modal = True, 
                    show_incorrect_password_modal=False, show_email_not_registered_modal=False)
                elif (subscription.end_date<today and student.institution_id is None):
                    expiry_date = (
                        subscription.end_date.strftime('%d %B %Y')
                        if subscription and subscription.end_date is not None
                        else 'N/A'
                    )                    
                    return render_template('Login.html', user="student", plans=plans, student=login, 
                    razorpaykey = application.config['RAZORPAY_ACCESS_KEY_ID'], show_subscription_expired_modal=True, 
                    show_subscription_inactive_modal = False , expiry_date=expiry_date, show_incorrect_password_modal=False, show_email_not_registered_modal=False)
            else:
                return render_template('Login.html', user="student", plans=[], student={}, show_subscription_expired_modal=False, show_incorrect_password_modal=True, show_email_not_registered_modal=False)
        elif institution:
            if check_password_hash(institution.password, password):
                # Check subscription status
                subscription = InstitutionSubscription.query.filter_by(institution_id=institution.institution_id).first()
                if subscription and subscription.status:
                    session['user_id'] = institution.institution_id                    
                    verified_emails[email] = True
                    return redirect(url_for('institutionDashboard'))
                else:
                    return render_template('Login.html', user="institution", plans=[], student={}, show_subscription_expired_modal=False, show_subscription_inactive_modal = True, show_incorrect_password_modal=False, show_email_not_registered_modal=False)
            else:
                return render_template('Login.html', user="institution", plans=[], student={}, show_subscription_expired_modal=False, show_incorrect_password_modal=True, show_email_not_registered_modal=False)
        elif admin:
            if check_password_hash(admin.password, password):                
                session['user_id'] = admin.admin_id                    
                verified_emails[email] = True
                return redirect(url_for('adminDashboard'))
            else:
                return render_template('Login.html', user="admin", plans=[], student={}, show_subscription_expired_modal=False, show_incorrect_password_modal=True, show_email_not_registered_modal=False)            
        else:
            return render_template('Login.html', user="admin", plans=[], student={}, show_subscription_expired_modal=False, show_incorrect_password_modal=False, show_email_not_registered_modal=True)        
    
    return render_template('Login.html', user="", plans=[], student={}, show_subscription_expired_modal=False, show_incorrect_password_modal=False, show_email_not_registered_modal=False)

@application.route('/logout', methods=['GET'])
def logout():
    session.pop('user_id', None)
    session.clear()
    # flash('You have been logged out.', 'success')
    return redirect(url_for('loginPage'))

def is_valid_password(password):
    # At least one upper case letter
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    # At least one lower case letter
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    # At least one digit
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number."
    # At least one special character
    if not re.search(r'[^A-Za-z0-9]', password):
        return False, "Password must contain at least one special character."
    # Length constraints
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 18:
        return False, "Password must not exceed 18 characters."

    return True, ""

@application.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400

    if email not in verified_emails or not verified_emails[email]:
        return jsonify({'success': False, 'message': 'Login again to update password'}), 400
    
    validation_result, error_message = is_valid_password(password)
    
    if not validation_result:
        return jsonify({'success': False, 'message': 'Password does not meet criteria. ' + error_message}), 400

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    student = Login.query.filter_by(email=email).first()
    institution = InstitutionLogin.query.filter_by(email=email).first()
    
    if student:
        student.password = hashed_password
        db.session.commit()
    elif institution:
        institution.password = hashed_password
        db.session.commit()  
    else:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    return jsonify({'success': True}), 200

def generate_hash(data):
    return generate_password_hash(data, method='pbkdf2:sha256')

def check_hash(data, hash_value):
    return check_password_hash(hash_value, data)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # print("USER NOT LOGGED IN!")
            return redirect(url_for('loginPage'))  
        return f(*args, **kwargs)
    return decorated_function

# endregion

# region Dashboard

@application.context_processor
def inject_profile_pic_url():
    if 'user_id' in session:
        student_id = session['user_id']
        try:
            profile_pic_url = get_profile_pic_url(student_id)
        except:
            profile_pic_url = url_for('static', filename='images/staticprofile.png')
        return {'profile_pic_url': profile_pic_url}
    return {'profile_pic_url': url_for('static', filename='images/staticprofile.png')}

@application.route('/Dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('loginPage'))
    
    student_id = session['user_id']
    student = Student.query.filter_by(student_id=student_id).first()
    
    if student:
        mock_count_query = text(
        """
        SELECT count(*) 
        FROM mocktest.attempt 
        WHERE student_id = :student_id
        and resume_test = 'completed'
        """
        )

        mock_tests_total_count = db.session.execute(mock_count_query, {'student_id': student_id}).scalar()

        daily_count_query = text(
        """
        SELECT count(*) 
        FROM dailypractice.attempt 
        WHERE student_id = :student_id
        and resume_test = 'completed'
        """
        )

        daily_practice_total_count = db.session.execute(daily_count_query, {'student_id': student_id}).scalar()
        
        current_utc_time = datetime.now(timezone.utc)
        today = current_utc_time.date()
        
        daily_today_count_query = text(
        """
        SELECT count(*) 
        FROM dailypractice.attempt 
        WHERE student_id = :student_id
        and resume_test = 'incomplete'
        and date = :today
        """
        )

        daily_practice_today_total_count = db.session.execute(daily_today_count_query, {'student_id': student_id, 'today':today}).scalar()
        daily_practice_scheduled_today = daily_practice_today_total_count>0
        
        daily_schedule_dates_query = text(
        """
        SELECT distinct TO_CHAR(date, 'YYYY-MM-DD') 
        FROM dailypractice.attempt 
        WHERE student_id = :student_id
        and resume_test = 'incomplete'
        """
        )
        
        daily_schedule_dates = db.session.execute(daily_schedule_dates_query, {'student_id': student_id}).fetchall()
        dailyScheduleDates = json.dumps([item[0] for item in daily_schedule_dates])
        
        custom_count_query = text(
        """
        SELECT count(*) 
        FROM custommodules.attempt 
        WHERE student_id = :student_id
        and resume_test = 'completed'
        """
        )

        custom_modules_total_count = db.session.execute(custom_count_query, {'student_id': student_id}).scalar()   
        # profile_pic_url = get_profile_pic_url(student_id)
        
        # Fetch filtered exams for the student
        year =  datetime.today().year
        categories = 'all'
        your_exams, other_exams = filter_exams_logic(student_id, year, categories)

    return render_template('Dashboard.html',mock_tests_total_count=mock_tests_total_count,
                           daily_practice_total_count=daily_practice_total_count,custom_modules_total_count=custom_modules_total_count,
                           daily_practice_scheduled_today=daily_practice_scheduled_today,daily_schedule_dates=dailyScheduleDates, exams = your_exams)

@application.route('/DashboardPieChartMockData', methods=['GET'])
def get_mock_PieChartData(): 
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('loginPage'))
    
    student_id = session['user_id']
    
    mock_pie_query = text(
        """
        SELECT count(*),resume_test 
        FROM mocktest.attempt 
        WHERE student_id = :student_id
        group by resume_test
        """
        )

    mock_count_results = db.session.execute(mock_pie_query, {'student_id': student_id}).fetchall()
    
    labels = []
    series = []
    status_mapping = {
    'completed': 'Completed',
    'incomplete': 'Partially Completed'
    }

    for count, status in mock_count_results:
        labels.append(status_mapping.get(status, status)) 
        series.append(count)
    
    pieChartData = {
        "labels": labels,
        "series": series,
    }
    return jsonify(pieChartData)

@application.route('/DashboardPieChartDailyData', methods=['GET'])
def get_daily_PieChartData(): 
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('loginPage'))
    
    student_id = session['user_id']
    
    daily_pie_query = text(
        """
        SELECT 
        COUNT(*) AS count,
        CASE
        WHEN resume_test = 'incomplete' AND attempt.date > now() THEN 'lapsed'
        ELSE resume_test
        END AS status
        FROM dailypractice.attempt
        WHERE student_id = :student_id
        GROUP BY status
        """
        )

    daily_count_results = db.session.execute(daily_pie_query, {'student_id': student_id}).fetchall()
          
    labels = []
    series = []
    status_mapping = {
    'completed': 'Completed',
    'incomplete': 'Partially Completed',
    'lapsed': 'Lapsed'
    }

    for count, status in daily_count_results:
        labels.append(status_mapping.get(status, status)) 
        series.append(count)
    
    pieChartData = {
        "labels": labels,
        "series": series,
    }
    return jsonify(pieChartData)

@application.route('/DashboardPieChartCustomData', methods=['GET'])
def get_custom_PieChartData(): 
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('loginPage'))
    
    student_id = session['user_id']
    
    custom_pie_query = text(
        """
        SELECT count(*),resume_test 
        FROM custommodules.attempt 
        WHERE student_id = :student_id
        group by resume_test
        """
        )

    custom_count_results = db.session.execute(custom_pie_query, {'student_id': student_id}).fetchall()
          
    labels = []
    series = []
    status_mapping = {
    'completed': 'Completed',
    'incomplete': 'Partially Completed'
    }

    for count, status in custom_count_results:
        labels.append(status_mapping.get(status, status)) 
        series.append(count)
    
    pieChartData = {
        "labels": labels,
        "series": series,
    }
    return jsonify(pieChartData)

def getBarChartData(table,student_id):
    # Fetch exam attempt details from session or database
    subquery = text(
        """
        SELECT attempt_id 
        FROM """+table+""".attempt 
        WHERE student_id = :student_id
        """
    )
    
    barChart_query = text(
        """
        SELECT 
        meta.subject.subject_name,
        COUNT(CASE WHEN """+table+""".userresponse.response = 'correct' THEN 1 END) * 100.0 / COUNT(*) AS avg_score
        FROM """+table+""".userresponse
        JOIN meta.question
        ON """+table+""".userresponse.q_id = meta.question.q_id
        JOIN meta.subject
        ON meta.question.subject_id = meta.subject.subject_id
        WHERE 
        """+table+""".userresponse.attempt_id IN (""" + subquery.text + """)
        GROUP BY meta.subject.subject_name;
        """
    )
    
    params = {"student_id": student_id}
    
    barChart_responses = db.session.execute(barChart_query, params).fetchall()
    return barChart_responses

@application.route('/DashboardBarChartData', methods=['GET'])
def get_dash_BarChartData():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('loginPage'))
    
    student_id = session['user_id']    
    student = Student.query.filter_by(student_id=student_id).first()
    
    if student:
        barChart_responses_mock = getBarChartData("mocktest",student_id)
        barChart_responses_daily = getBarChartData("dailypractice",student_id)        
        barChart_responses_custom = getBarChartData("custommodules",student_id)
        
        # aggregation
        
        barChart_responses = barChart_responses_mock+barChart_responses_daily+barChart_responses_custom
        
        subject_scores = defaultdict(list)

        for subject_name, average_score in barChart_responses:
            subject_scores[subject_name].append(average_score)
        
        series_data = []
        for subject_name, scores in subject_scores.items():
            overall_average = sum(scores) / len(scores)
            series_data.append({"x": subject_name, "y": overall_average})

        # Prepare series for the bar chart
        series = [{"name": "Average Score by Subjects", "data": series_data}]

        # Return JSON response
        return jsonify({"series": series})
    
    else:
        series = [{"name": "Average Score by Subjects", "data": []}]
        return jsonify({"series": series})

# endregion

# region MockTestDashboard

@application.route('/MockTestDashboard', methods=['GET', 'POST'])
def mockTestDashboard():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('loginPage'))
    
    student_id = session['user_id']
    student = Student.query.filter_by(student_id=student_id).first()
    
    if student:
        #region take test modal
        exams = MockExam.query.all()
        exam_names = {}
        difficulty_levels = set()

        for exam in exams:
            # name_parts = exam.exam_name.split('_')
            # exam_name = name_parts[0]
            # difficulty = name_parts[1] if len(name_parts) > 1 else None

            exam_name = exam.exam_name
            difficulty = exam.exam_difficulty
            
            if exam_name not in exam_names:
                exam_names[exam_name] = exam.exam_id
                
            if difficulty:
                difficulty_levels.add(difficulty)

        if request.method == 'POST':
            exam_name = request.form.get('exam_name')
            difficulty = request.form.get('difficulty')
            
            if not exam_name or not difficulty:
                flash('Please select both an exam and a difficulty level.', 'error')
                return redirect(url_for('dashboard'))
            
            combined_exam_name = f"{exam_name}_{difficulty}"
            exam = MockExam.query.filter_by(exam_name=combined_exam_name).first()
            
            if not exam:
                flash('Selected exam not found.', 'error')
                return redirect(url_for('dashboard'))

            exam_id = exam.exam_id
            today = date.today()
            start_time = datetime.now().time()

            new_attempt = MockTestAttempt(
                date=today,
                student_id=session['user_id'],
                exam_id=exam_id,
                start_time=start_time
            )

            db.session.add(new_attempt)
            db.session.commit()

            attempt_id = new_attempt.attempt_id

            hash_value = generate_hash(f"{exam_id}:{attempt_id}")
            session['exam_hash'] = hash_value

            return redirect(url_for('MockTestInstruction', exam_id=exam_id, attempt_id=attempt_id, hash=hash_value))

        #endregion

        average_accuracy, average_score = get_student_metrics(student_id=student_id)
        filtered_completed_attempts,filtered_incomplete_attempts = get_attempt_details(student_id=student_id)
        mocks_completed = sum(len(attempts) for attempts in filtered_completed_attempts.values())
        # Create a dictionary to store unique exam_id and exam_name
        unique_exams = {}

        # Add items from exam_attempt_details_completed
        for exam_id, attempts in filtered_completed_attempts.items():
            if exam_id not in unique_exams:
                unique_exams[exam_id] = attempts[0]['exam_name']+"_"+attempts[0]['exam_difficulty']

        # Add items from exam_attempt_details_incomplete
        for exam_id, attempts in filtered_incomplete_attempts.items():
            if exam_id not in unique_exams:
                unique_exams[exam_id] = attempts[0]['exam_name']+"_"+attempts[0]['exam_difficulty']

        student_name = f"{student.first_name} {student.last_name}"
        distinct_exams_count = len(unique_exams)
        session['exam_attempt_details'] = filtered_completed_attempts        
        return render_template('MockTestDashboard.html', exams=exam_names.keys(), difficulty_levels=difficulty_levels,
                            mocks_completed=mocks_completed, average_accuracy=average_accuracy,
                            average_score=average_score,unique_exams=unique_exams,
                            exam_attempt_details_completed=filtered_completed_attempts,exam_attempt_details_incomplete=filtered_incomplete_attempts,
                            student_name=student_name,exams_targeted=distinct_exams_count)
    else:
        flash('Student not logged in.', 'error')
        return redirect(url_for('loginPage'))

@application.route('/PieChartData', methods=['GET'])
def get_PieChartData(): 
    exam_attempt_details = session.get('exam_attempt_details', {})      
    labels = [attempts[0]['exam_name'] for exam_id, attempts in exam_attempt_details.items()]
    series = [len(attempts) for exam_id, attempts in exam_attempt_details.items()]
    pieChartData = {
        "labels": labels,
        "series": series,
    }
    return jsonify(pieChartData)

@application.route('/BarChartData', methods=['GET'])
def get_BarChartData():
    # Fetch exam attempt details from session or database
    exam_attempt_details = session.get('exam_attempt_details', {})

    attempt_ids=[]
    
    for exam_id, attempts in exam_attempt_details.items():
        for attempt in attempts:
            attempt_ids.append(attempt['attempt_id'])
    
    barChart_query = text(
        """
        SELECT 
        meta.subject.subject_name,
        COUNT(CASE WHEN mocktest.userresponse.response = 'correct' THEN 1 END) * 100.0 / COUNT(*) AS avg_score
        FROM mocktest.userresponse
        JOIN meta.question
        ON mocktest.userresponse.q_id = meta.question.q_id
        JOIN meta.subject
        ON meta.question.subject_id = meta.subject.subject_id
        WHERE 
        mocktest.userresponse.attempt_id IN :attempt_ids
        GROUP BY meta.subject.subject_name;
        """
    )
    
    params = {"attempt_ids": tuple(attempt_ids)}
    
    lineChart_responses = db.session.execute(barChart_query, params).fetchall()
    
    series_data = []
    for subject_name, average_score in lineChart_responses:
        # Append data in the required format
        series_data.append({"x": subject_name, "y": average_score})

    # Prepare series for the bar chart
    series = [{"name": "Average Score by Subjects", "data": series_data}]

    # Return JSON response
    return jsonify({"series": series})
    
@application.route('/LineChartData', methods=['GET'])
def get_LineChartData():
    # Fetch exam attempt details from session or database
    exam_attempt_details = session.get('exam_attempt_details', {})
    attempt_ids=[]
    
    for exam_id, attempts in exam_attempt_details.items():
        for attempt in attempts:
            attempt_ids.append(attempt['attempt_id'])
    
    lineChart_query = text(
        """
        SELECT 
        meta.subject.subject_name,
        meta.question.difficulty_level,
        COUNT(CASE WHEN mocktest.userresponse.response = 'correct' THEN 1 END) * 100.0 / COUNT(*) AS avg_score
        FROM mocktest.userresponse
        JOIN meta.question
        ON mocktest.userresponse.q_id = meta.question.q_id
        JOIN meta.subject
        ON meta.question.subject_id = meta.subject.subject_id
        WHERE 
        mocktest.userresponse.attempt_id IN :attempt_ids
        GROUP BY meta.subject.subject_name, meta.question.difficulty_level;
        """
    )
    
    params = {"attempt_ids": tuple(attempt_ids)}
    
    lineChart_responses = db.session.execute(lineChart_query, params).fetchall()

    # Extract unique subject names for labels
    labels = list(set(row[0] for row in lineChart_responses))
    # Map labels to indices for easier assignment
    label_indices = {label: idx for idx, label in enumerate(labels)}    
    
    subjects_placeholder = [0] * len(labels)
    
    # Prepare series for the bar chart
    series = [{"name": "Beginner", "data": subjects_placeholder.copy(), "color": '#F2BC2A'},
              {"name": "Intermediate", "data": subjects_placeholder.copy(), "color": '#4b5563'},
              {"name": "Proficient", "data": subjects_placeholder.copy(), "color": '#0ABDDB'},
              {"name": "Advanced", "data": subjects_placeholder.copy(), "color": '#90EE90'},
              {"name": "Expert", "data": subjects_placeholder.copy(), "color": '#FB9251'}]
    
    for subject_name,difficulty_level,avg_score in lineChart_responses:
        series[difficulty_level-1]["data"][label_indices[subject_name]] = avg_score
        
    lineChartData = {
        "labels": labels,
        "series": series,
    }
    
    # Return JSON response
    return jsonify(lineChartData)

def get_student_metrics(student_id):
    # Get total scores and total possible scores for each attempt
    subquery = text(
        """
        SELECT attempt_id 
        FROM mocktest.attempt 
        WHERE student_id = :student_id
        """
    )

    # Query to count correct responses
    correct_responses_query = text(
        """
        SELECT COUNT(response) AS correct_count
        FROM mocktest.userresponse
        WHERE response = 'correct' AND attempt_id IN (""" + subquery.text + """)
        """
    )
    correct_responses = db.session.execute(correct_responses_query, {'student_id': student_id}).scalar()

    # Query to count attempted options (correct + incorrect)
    attempted_options_query = text(
        """
        SELECT COUNT(response) AS attempted_count
        FROM mocktest.userresponse
        WHERE (response = 'correct' OR response = 'incorrect') AND attempt_id IN (""" + subquery.text + """)
        """
    )
    attempted_options = db.session.execute(attempted_options_query, {'student_id': student_id}).scalar()

    # Query to count total questions attempted
    total_questions_attempted_query = text(
        """
        SELECT COUNT(*) AS total_attempted
        FROM mocktest.userresponse
        WHERE attempt_id IN (""" + subquery.text + """)
        """
    )
    total_questions_attempted = db.session.execute(total_questions_attempted_query, {'student_id': student_id}).scalar()

    # Calculate accuracy and average
    accuracy = correct_responses / attempted_options if attempted_options > 0 else 0
    average = correct_responses / total_questions_attempted if total_questions_attempted > 0 else 0
    # print(accuracy,average)
    
    return int(accuracy*100), int(average*100)

def get_attempt_details(student_id):
    exams_completed,exams_incomplete = filter_mocktest_logic(
            student_id, 'all', 'all', 'all', 'all', 'all')
    
    return exams_completed,exams_incomplete

def filter_mocktest_logic(student_id, status, exam_id, from_date, to_date, difficulty):

    query = db.session.query(
        MockTestAttempt.exam_id,
        MockTestAttempt.attempt_id,
        MockTestAttempt.date,
        MockTestAttempt.resume_test,
        MockExam.exam_name,
        MockExam.exam_difficulty
    ).filter_by(student_id=student_id).join(MockExam, MockTestAttempt.exam_id == MockExam.exam_id)   
    
    #Difficulty Filter
    
    if difficulty and difficulty != 'all':
        query = query.filter(MockExam.exam_difficulty == difficulty)
    
    #Exam Filter

    if exam_id and exam_id != 'all':
        query = query.filter(MockExam.exam_id == exam_id)
    
    #Date Filter
    
    from_date_parsed=''
    to_date_parsed =''
    if from_date and from_date!='all':
        from_date_parsed = datetime.strptime(from_date, '%Y-%m-%d')
    if to_date and to_date!='all':
        to_date_parsed = datetime.strptime(to_date, '%Y-%m-%d')
    
    if from_date_parsed!='' and to_date_parsed!='':
        query = query.filter(MockTestAttempt.date.between(from_date_parsed, to_date_parsed))
    elif from_date_parsed!='':
        query = query.filter(MockTestAttempt.date >= from_date_parsed)
    elif to_date_parsed!='':
        query = query.filter(MockTestAttempt.date <= to_date_parsed)

    #Status Filter
    if status and status != 'all':
        if status == 'completed':
            query = query.filter(MockTestAttempt.resume_test == 'completed')  # Completed: resume_test is NULL
        elif status == 'partially_completed':
            query = query.filter(MockTestAttempt.resume_test == 'incomplete')  # Partially Completed
       
    query = query.order_by(MockTestAttempt.attempt_id.desc())    
    results = query.all()

    # filtered_attempts = defaultdict(list)
    filtered_completed_attempts = defaultdict(list)
    filtered_incomplete_attempts = defaultdict(list)
    
    for result in results:        
        if result.resume_test == 'completed':        
            score = db.session.query(
                db.func.count(UserResponse.response)
            ).filter_by(attempt_id=result.attempt_id, response='correct').scalar() or 0

            max_score = db.session.query(
                db.func.count(UserResponse.response)
            ).filter_by(attempt_id=result.attempt_id).scalar() or 0

            data={
                'exam_name': result.exam_name ,
                'exam_difficulty': result.exam_difficulty,
                'attempt_id': result.attempt_id,
                'date': result.date,
                'score': score,
                'max_score': max_score
            }
            filtered_completed_attempts[result.exam_id].append(data)
        else:
            total_count = db.session.query(
                db.func.count(UserResponse.response)
            ).filter_by(attempt_id=result.attempt_id).scalar() or 0

            attempted_count = db.session.query(
                db.func.count(UserResponse.response)
            ).filter(UserResponse.attempt_id==result.attempt_id, UserResponse.question_status!='not_attempted').scalar() or 0

            data={
                'exam_name': result.exam_name ,
                'exam_difficulty': result.exam_difficulty,
                'attempt_id': result.attempt_id,
                'date': result.date,
                'total_count': total_count,
                'attempted_count': attempted_count
            }
            
            filtered_incomplete_attempts[result.exam_id].append(data)
            
    # Convert defaultdict to normal dict before returning
    filtered_completed_attempts = dict(filtered_completed_attempts)
    filtered_incomplete_attempts = dict(filtered_incomplete_attempts)
    
    return filtered_completed_attempts,filtered_incomplete_attempts

@application.route('/filter_mocktest', methods=['POST'])
def filter_mocktest():
    student_id = session['user_id'] # Get student ID from session
    status = request.form.get('status')
    exam_id = request.form.get('exam')
    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')
    difficulty = request.form.get('difficulty')

    filtered_completed_attempts,filtered_incomplete_attempts = filter_mocktest_logic(
        student_id, status, exam_id, from_date, to_date, difficulty
    )

    return render_template('MockTestAccordion.html', exam_attempt_details_completed=filtered_completed_attempts,exam_attempt_details_incomplete=filtered_incomplete_attempts)

# endregion

# region MockTest

def get_presigned_image_url(filename):
    key = f"question_pictures/{filename}"
    try:
        s3.head_object(Bucket=BUCKET_NAME, Key=key)
        return s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': key},
            ExpiresIn=3600
        )
    except Exception as e:
        # print(f"Could not generate URL for {key}: {e}")
        return None

@application.route('/MockTestInstruction', methods=['POST'])
def mockTestInstruction():
    try:
        if 'user_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('loginPage'))

        student_id = session['user_id']
        student = Login.query.filter_by(student_id=student_id).first()

        if student:
            exam_name = request.form['exam_name']
            difficulty_level = request.form['difficulty']
            exam = MockExam.query.filter_by(exam_name=exam_name,exam_difficulty=difficulty_level).first()
            if not exam:
                flash('Exam does not exist for this difficulty level.', 'error')
                return redirect('/MockTestDashboard')
            
            exam_id = exam.exam_id

            config_entries = MockExamConfig.query.filter_by(exam_id=exam_id).all()

            subjects = {}
            total_questions = 0
            total_marks = 0

            for entry in config_entries:
                subject = Subject.query.filter_by(subject_id=entry.subject_id).first()
                if subject:
                    subject_name = subject.subject_name
                    q_diff = entry.q_diff

                    num_questions = 0
                    max_marks = 0

                    for difficulty, count in q_diff.items():
                        questions = Question.query.filter_by(subject_id=entry.subject_id, difficulty_level=int(difficulty)).limit(count).all()
                        num_questions += len(questions)
                        max_marks += sum(question.max_score for question in questions)

                    subjects[subject_name] = {
                        'num_questions': num_questions,
                        'max_marks': max_marks,
                    }

                    total_questions += num_questions
                    total_marks += max_marks

            total_seconds = exam.exam_duration.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)

            return render_template('MockTestInstruction.html', 
                                exam=exam, 
                                subjects=subjects, 
                                total_questions=total_questions, 
                                total_marks=total_marks,
                                exam_id=exam_id, 
                                hours=hours,
                                minutes=minutes)
        else:
            flash('Student not logged in.', 'error')
            return redirect(url_for('/'))
    except Exception as e:
        # Log errors for debugging
        # print(f"Error: {e}")
        return f"An error occurred: {e}", 500

def create_attempt(student_id, exam_id):
    current_utc_time = datetime.now(timezone.utc)
    new_attempt = MockTestAttempt(
        date=current_utc_time.date(),  # Set current date
        student_id=student_id,
        exam_id=exam_id,
        start_time=current_utc_time,
        resume_test='incomplete'
    )

    # Add to the database session and commit
    db.session.add(new_attempt)
    db.session.commit()

    # Return the generated attempt_id
    return new_attempt.attempt_id
 
@application.route('/MockCreateTest', methods=['POST'])
@login_required
def mockCreateTest():
    if request.method == 'POST':
        exam_id = request.form.get('exam_id')
    if 'user_id' not in session:
        flash('Student not logged in.', 'error')
        return redirect('/')

    student_id = session['user_id']

    exam = MockExam.query.get(exam_id)
    if not exam:
        flash('Exam not found.', 'error')
        return redirect('/MockTestDashboard')
    
    attempt_id = create_attempt(student_id, exam_id)
    # new_hash_value = generate_hash(f"{exam_id}:{student_id}")

    selected_questions = MockTestQuestionsGenerator.fetchMockTestQuestions(exam.exam_name,exam.exam_id)
    
    q_order=1

    for question in selected_questions:  
        user_response = UserResponse(q_id=question[0],
            response='skipped',
            attempt_id=attempt_id,
            q_order=q_order,
            selected_option={},
            question_status='not_attempted',
            # time_spent = timedelta(seconds=0)
        )
        db.session.add(user_response) 
        q_order+=1
    db.session.commit()

    return redirect(url_for('mockTest', attempt_id=attempt_id))

@application.route('/MockTest', methods=['GET', 'POST'])
def mockTest():
    # Log request method and parameters for debugging
        
    if request.method == 'GET':
        attempt_id = request.args.get('attempt_id')
        # hash_value = request.args.get('hash')
    elif request.method == 'POST':
        attempt_id = request.form.get('attempt_id')
        # hash_value = request.args.get('hash')
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('loginPage'))

    student_id = session['user_id']
    student = Login.query.filter_by(student_id=student_id).first()

    if student:
        
        # Check if attempt exists in the table
        attempt = MockTestAttempt.query.filter_by(attempt_id = attempt_id, student_id = student_id).first()
    
        exam_id = attempt.exam_id
        
        # if 'exam_hash' not in session or not hash_value or not check_hash(f"{exam_id}:{student_id}", hash_value):
        #     flash('Invalid or missing hash value.', 'error')
        #     return redirect(url_for('dashboard'))
        
        if not attempt:
            flash('Invalid attempt. Please try again.', 'error')
            return redirect('/MockTestDashboard')

        if attempt.resume_test!='incomplete':
            flash('Cannot attempt this test.', 'error')
            return redirect('/MockTestDashboard')
        
        exam = MockExam.query.get(exam_id)
        
        exam_duration = exam.exam_duration
        exam_duration_seconds = int(exam_duration.total_seconds())
        
        resume_seconds = 0
        if attempt.resume_time:
            resume_seconds = int(attempt.resume_time.total_seconds())
        else:
            resume_seconds = exam_duration_seconds
        
        mockResumeQuery = text("""
        SELECT 
            question.q_id,
            direction.direction_description,
            question.question_description,
            question.answer_options,
            question.choice_type,
            question.max_score,
            question.correct_option,
            question.solution_explanation,
            question.multi_select,
            userresponse.selected_option,
            userresponse.question_status
        FROM mocktest.userresponse
        JOIN meta.question ON userresponse.q_id = question.q_id
        JOIN meta.direction ON question.direction_id = direction.direction_id
        WHERE userresponse.attempt_id = :attempt_id
        order by userresponse.q_order
        """)
        
        params = {"attempt_id": attempt_id}    
        responses = db.session.execute(mockResumeQuery, params).fetchall()
        
        questions = []
    
        for response in responses:
            question_data = {
                'q_id': response.q_id,
                'direction_description': response.direction_description,
                'question_description': response.question_description,
                'answer_options': response.answer_options,
                'choice_type' : response.choice_type,
                'max_score': response.max_score,
                'correct_option': response.correct_option,
                'solution_explanation': response.solution_explanation,
                'multi_select': response.multi_select,
                'selected_option_list': response.selected_option if response.selected_option else [], 
                'question_status': response.question_status if response.question_status else 'not_attempted'
            }
            
            if question_data['choice_type'] == 'image':
                new_options = {}
                for k, v in question_data['answer_options'].items():
                    signed_url = get_presigned_image_url(v)
                    new_options[k] = signed_url if signed_url else v
                question_data['answer_options'] = new_options
        
            questions.append(question_data)
        
        return render_template('MockTest.html', exam_id=exam_id, questions=questions, exam_duration=exam_duration_seconds, attempt_id=attempt_id, resume_seconds=resume_seconds)
    else:
        flash('Student not logged in.', 'error')
        return redirect('/')

@application.route('/SubmitMockTest', methods=['GET', 'POST'])
def submit_MockTest():
    try:
        data = request.json
        if not data:
            return "Unsupported Media Type NO JSON", 415
        
        if 'user_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('loginPage'))

        student_id = session['user_id']
        student = Login.query.filter_by(student_id=student_id).first()

        if not student:
            flash('Student not logged in.', 'error')
            return redirect(url_for('loginPage'))


        attempt_id = data.get('attempt_id')
        selected_options = data.get('selectedOptions')
        selected_options_for_q_id = data.get('selectedOptionsForq_id')
        question_status = data.get('questionStatus')
        question_status_map = json.loads(question_status)
        q_id_to_q_order = data.get('qIdToQOrder')
        time_left = data.get('timeLeft')
        partial_complete = data.get('partial_complete')
        
        # Print received localStorage data to the server console
        # print(f"Selected Options: {selected_options}")
        # print(f"Selected Options for Q_id: {selected_options_for_q_id}")
        # print(f"Question Status: {question_status_map}")
        # print(f"Q Id to Q Order: {q_id_to_q_order}")
        # print(f"Time Left: {time_left}")
        
        if partial_complete:
            seconds = int(time_left)
            td = timedelta(seconds=seconds)
            interval_str = str(td)
            updateResumeTimeQuery = text("""
                UPDATE mocktest.attempt
                SET resume_time = :resume_time
                WHERE attempt_id = :attempt_id
            """)
            params = {
                "resume_time": interval_str,
                "attempt_id": attempt_id
            }
            db.session.execute(updateResumeTimeQuery, params)
            db.session.commit()
        else:
            setTestCompletedQuery = text("""update mocktest.attempt
                                    set resume_test = 'completed'
                                    where attempt_id = :attempt_id
                                        """)
        
            params = {"attempt_id": attempt_id}    
            db.session.execute(setTestCompletedQuery, params)
            db.session.commit()
        
        # delete from userresponse if it already has any
        
        deletePrevResponseQuery = text("""delete from mocktest.userresponse
                                where attempt_id = :attempt_id
                                    """)
     
        params = {"attempt_id": attempt_id}    
        db.session.execute(deletePrevResponseQuery, params)
        db.session.commit()
        
        answer_status = {}
        questions = Question.query.all()
        
        # Create a dictionary to easily access correct options by q_id
        correct_options_dict = {q.q_id: q.correct_option for q in questions}
        
        # Evaluate each question
        for q_id, options in selected_options_for_q_id.items():
            correct_options = correct_options_dict.get(int(q_id), [])
            if not options:
                answer_status[q_id] = 'skipped'
            elif set(options) == set(correct_options):
                answer_status[q_id] = 'correct'
            else:
                answer_status[q_id] = 'incorrect'
        # print(f"Answer Status: {answer_status}")

        # Save the data to userresponse table
        for q_id, options in selected_options_for_q_id.items():
            response = answer_status.get(q_id, 'skipped')
            q_order = q_id_to_q_order.get(q_id) 
            selected_option = options
            user_response = UserResponse(
                q_id=q_id,
                # time_spent=time_left,
                response=response,
                attempt_id=attempt_id,
                q_order=q_order,
                selected_option=selected_option,
                question_status=question_status_map.get(str(q_order), "not_attempted")
            )
            db.session.add(user_response) 
        db.session.commit()
        
        return jsonify({"Success":"Successfully submitted Mock Test","attempt_id":attempt_id})
    except Exception as e:
        # Log errors for debugging
        return jsonify({"Error": "An error occurred Details: {e}"})

# endregion

# region Mocktest Report

def get_report_attempt_details(attempt_id):
    # student_id = session['user_id']
    attempt = MockTestAttempt.query.filter_by(attempt_id=attempt_id).first()

    # print(attempt)
    if attempt:
        return {
            'attempt_id': attempt.attempt_id,
            'date': attempt.date,
            'student_id': attempt.student_id,
            'exam_id': attempt.exam_id,
            'start_time': attempt.start_time
        }
    else:
        return None

def get_report_responses(attempt_id):
    query = text("""
    SELECT * 
    FROM mocktest.userresponse
    JOIN meta.question ON mocktest.userresponse.q_id = meta.question.q_id
    JOIN meta.subject ON meta.subject.subject_id = meta.question.subject_id
    WHERE attempt_id = :attempt_id
    """)

    responses = db.session.execute(query, {"attempt_id": attempt_id}).fetchall()
    return responses

def get_report_table_details(responses):     
    
    subject_details = {}
    
    for response in responses:
        
        #Subject consolidation section for table
        
        subject_name = response.subject_name
        
        if subject_name not in subject_details:
            subject_details[subject_name] = {
                'subject_name': subject_name,
                'question_count': 0,
                'attempted': 0,
                'correct': 0,
                'incorrect': 0,
                'skipped': 0,
                'score': 0,
                'percentage': 0
            }
        
        # subject_details[subject_name]['total_time_spent'] += response.time_spent.total_seconds()
        if response.response == 'correct':
            subject_details[subject_name]['correct'] += 1
        elif response.response == 'incorrect':
            subject_details[subject_name]['incorrect'] += 1
        elif response.response == 'skipped':
            subject_details[subject_name]['skipped'] += 1
        # subject_details[subject_name]['total_time_spent'] += response.time_spent.total_seconds() 
        

    subject_details_flattened = []
    all_sections_totals = {
        'Total_Questions': 0,
        'Total_Attempted': 0,
        'Correct': 0,
        'Incorrect': 0,
        'Skipped': 0,
        'Score': 0,
        'Percentage': 0
    }

    for subject_name,details in subject_details.items():
        details['question_count'] = details['correct'] + details['incorrect'] + details['skipped']
        details['attempted'] = details['correct'] + details['incorrect']
        details['score'] = details['correct']
        if details['question_count'] > 0:
            details['percentage'] =  int((details['correct'] / details['question_count']) * 100)
        
        # all_sections_summary
        all_sections_totals['Total_Questions']+=details['question_count']
        all_sections_totals['Total_Attempted']+=details['attempted']
        all_sections_totals['Correct']+=details['correct']
        all_sections_totals['Incorrect']+=details['incorrect']
        all_sections_totals['Skipped']+=details['skipped']
        all_sections_totals['Score']+=details['score']
        # all_sections_totals['Total_Time_Spent']+=details['total_time_spent']
        
        # total_time_spent = details['total_time_spent']
        # hours = int(total_time_spent // 3600)
        # minutes = int((total_time_spent % 3600) // 60)
        # seconds = total_time_spent % 60    
        # details['total_time_spent'] =  str(hours) + " h " + str(minutes) + " m " + str(seconds) + " s"
        
        subject_details_flattened.append(details)
    
    # all_sections_totals['Percentage'] = int((all_sections_totals['Correct'] / all_sections_totals['Total_Questions']) * 100)  
    if all_sections_totals['Total_Questions'] > 0:
        all_sections_totals['Percentage'] = int((all_sections_totals['Correct'] / all_sections_totals['Total_Questions']) * 100)
    else:
        all_sections_totals['Percentage'] = 0    
    
    # allsec_total_time_spent = all_sections_totals['Total_Time_Spent']
    # hours = int(allsec_total_time_spent // 3600)
    # minutes = int((allsec_total_time_spent % 3600) // 60)
    # seconds = allsec_total_time_spent % 60    
    # all_sections_totals['Total_Time_Spent'] =  str(hours) + " h " + str(minutes) + " m " + str(seconds) + " s"
    
    return subject_details_flattened,all_sections_totals

def get_report_qa_details(attempt_id,subject='all',response_type='all'):
    base_query = """
    SELECT q_order,response,selected_option, correct_option, question_description, solution_explanation, answer_options , choice_type
    FROM mocktest.userresponse
    JOIN meta.question ON mocktest.userresponse.q_id = meta.question.q_id
    JOIN meta.subject ON meta.subject.subject_id = meta.question.subject_id
    WHERE attempt_id = :attempt_id
    """
    params = {"attempt_id": attempt_id}
    
    if subject != 'all':
        base_query += " AND subject_name = :subject"
        params.update({"subject": subject})
    if response_type != 'all':
        base_query += " AND response = :response_type"
        params.update({"response_type": response_type})
        
    base_query+= " order by q_order"

    query= text(base_query)
    solutions = db.session.execute(query, params).fetchall()
    return solutions

@application.route('/Report', methods=['POST'])
def generateReport():
    attempt_id = request.form.get('attempt_id')
    attempt_details = get_report_attempt_details(attempt_id)
    
    if attempt_details:
        attempt_id = attempt_details['attempt_id']
        date = attempt_details['date']
        student_id = attempt_details['student_id']
        exam_id = attempt_details['exam_id']
        start_time = attempt_details['start_time']
        
    student_name = f"{student.first_name} {student.last_name}" if (student := Student.query.filter_by(student_id=student_id).first()) else None
    exam_name = MockExam.query.filter_by(exam_id = exam_id).first().exam_name
    responses = get_report_responses(attempt_id)
    subjects, all_sections= get_report_table_details(responses)
    solutions_raw  = get_report_qa_details(attempt_id)
    
    # Convert to dicts for mutation
    solutions = [dict(row._mapping) for row in solutions_raw]

    # Replace image filenames with presigned URLs if choice_type is image
    for solution in solutions:
        if solution.get("choice_type") == "image":
            new_options = {}
            for key, val in solution["answer_options"].items():
                signed_url = get_presigned_image_url(val)
                new_options[key] = signed_url if signed_url else val
            solution["answer_options"] = new_options

        else:
            # For text options, still load as JSON
            try:
                solution["answer_options"] = json.loads(solution["answer_options"])
            except:
                pass
            
    return render_template('Report.html',
                           subjects=subjects,all_sections=all_sections,
                           solutions = solutions, exam_id = exam_id, exam_name=exam_name,
                           student_id = student_id, student_name=student_name ,date=date, time=start_time, attempt_id=attempt_id)

@application.route('/filter_report', methods=['POST'])
def filter_report():    
    attempt_id = request.form.get('attempt_id')
    total_questions = request.form.get('total_questions')
    selected_subject = request.form.get('subjects')
    selected_responsetype = request.form.get('responsetype')
    solutions_raw  = get_report_qa_details(attempt_id,subject=selected_subject,response_type=selected_responsetype)
    
    # Convert to dicts for mutation
    solutions = [dict(row._mapping) for row in solutions_raw]

    # Replace image filenames with presigned URLs if choice_type is image
    for solution in solutions:
        if solution.get("choice_type") == "image":
            options = json.loads(solution["answer_options"])
            new_options = {}
            for key, val in options.items():
                signed_url = get_presigned_image_url(val)
                new_options[key] = signed_url if signed_url else val
            solution["answer_options"] = new_options

        else:
            # For text options, still load as JSON
            try:
                solution["answer_options"] = json.loads(solution["answer_options"])
            except:
                pass

    return render_template('ReportSolution.html',
                           solutions = solutions, total_questions = total_questions)

# endregion

# region CustomModule Dashboard

def get_custom_student_metrics(student_id):
    # Step 1: Get all attempt IDs
    attempt_ids_query = text("""
        SELECT attempt_id 
        FROM custommodules.attempt 
        WHERE student_id = :student_id
    """)
    attempt_ids = db.session.execute(attempt_ids_query, {'student_id': student_id}).fetchall()

    if not attempt_ids:
        return 0, 0, [], [], 0, []

    attempt_ids_list = [str(row[0]) for row in attempt_ids]
    attempt_ids_str = ", ".join(attempt_ids_list)

    # Step 2: Get correct response count
    correct_responses_query = text(f"""
        SELECT COUNT(response)
        FROM custommodules.userresponse
        WHERE response = 'correct' AND attempt_id IN ({attempt_ids_str})
    """)
    correct_responses = db.session.execute(correct_responses_query).scalar()

    # Step 3: Get attempted options count
    attempted_options_query = text(f"""
        SELECT COUNT(response)
        FROM custommodules.userresponse
        WHERE (response = 'correct' OR response = 'incorrect') AND attempt_id IN ({attempt_ids_str})
    """)
    attempted_options = db.session.execute(attempted_options_query).scalar()

    # Step 4: Get total questions attempted
    total_questions_attempted_query = text(f"""
        SELECT COUNT(*)
        FROM custommodules.userresponse
        WHERE attempt_id IN ({attempt_ids_str})
    """)
    total_questions_attempted = db.session.execute(total_questions_attempted_query).scalar()

    # Step 5: Calculate accuracy and average
    accuracy = correct_responses / attempted_options if attempted_options > 0 else 0
    average = correct_responses / total_questions_attempted if total_questions_attempted > 0 else 0

    # Step 6: Get subjects attempted (through config → subject)
    subject_query = text("""
        SELECT DISTINCT s.subject_id, s.subject_name
        FROM meta.subject AS s
        JOIN meta.subject_module_mapping AS smm ON s.subject_id = smm.subject_id
        JOIN meta.module AS m ON smm.module_id = m.module_id
        JOIN custommodules.config AS c ON c.module_id = m.module_id
        WHERE c.student_id = :student_id
    """)
    subjects_attempted = db.session.execute(subject_query, {'student_id': student_id}).fetchall()
    subject_list = [{'subject_id': row.subject_id, 'subject_name': row.subject_name} for row in subjects_attempted]

    # Step 7: Get modules attempted (through config → module)
    module_query = text("""
        SELECT DISTINCT m.module_id, m.module_name, smm.subject_id
        FROM meta.module AS m
        JOIN meta.subject_module_mapping AS smm ON m.module_id = smm.module_id
        JOIN custommodules.config AS c ON c.module_id = m.module_id
        WHERE c.student_id = :student_id
    """)
    modules_attempted = db.session.execute(module_query, {'student_id': student_id}).fetchall()
    module_list = [{'module_id': row.module_id, 'module_name': row.module_name, 'subject_id': row.subject_id} for row in modules_attempted]

    return int(accuracy * 100), int(average * 100), attempt_ids_list, subject_list, len(module_list), module_list

def get_custom_attempt_details(student_id):
    tests_completed,incomplete_tests = filter_custommodule_logic(
        student_id, 'all', 'all', 'all', 'all', 'all')
    
    return tests_completed,incomplete_tests

def getAllSubjects():
    getSubjectQuery = text("""select * from meta.subject""")
    all_subjects = db.session.execute(getSubjectQuery).fetchall()
    all_subject_list = [{'subject_id':row.subject_id, 'subject_name': row.subject_name} for row in all_subjects]
    return all_subject_list
    
# def getAllModules():
#     getModuleQuery = text("""select * from meta.module""")
#     all_modules = db.session.execute(getModuleQuery).fetchall()
#     all_module_list = [{"module_id": row.module_id, "module_name": row.module_name, "subject_id":row.subject_id} for row in all_modules]
#     return all_module_list

def getAllModules():
    result = db.session.query(
        Module.module_id,
        Module.module_name,
        SubjectModuleMapping.subject_id
    ).join(SubjectModuleMapping, Module.module_id == SubjectModuleMapping.module_id).all()

    all_module_list = [
        {"module_id": row.module_id, "module_name": row.module_name, "subject_id": row.subject_id}
        for row in result
    ]
    return all_module_list

@application.route('/CustomModuleDashboard')
@login_required
def customModuleDashboard():
    student_id = session['user_id']
    student = Student.query.filter_by(student_id=student_id).first()
    student_name = f"{student.first_name} {student.last_name}"
    accuracy,average,attempt_ids,subjects,modules_attempted_count, modules  = get_custom_student_metrics(student_id=student_id)
    tests_completed,incomplete_tests = get_custom_attempt_details(student_id)
    all_subjects = getAllSubjects()
    all_modules = getAllModules()
    session['custommodule_attempt_ids'] = attempt_ids         
    
    difficulty_map = {
    1: "Beginner",
    2: "Intermediate",
    3: "Proficient",
    4: "Advanced",
    5: "Expert",
    }
    
    return render_template('CustomModuleDashboard.html',custom_attempt_details_completed=tests_completed,custom_attempt_details_incomplete=incomplete_tests,
                           accuracy=accuracy,average=average, student_name=student_name, modules_attempted_count=modules_attempted_count, subjects=subjects, 
                           difficulty_map = difficulty_map, modules=modules, all_subjects= all_subjects,all_modules=all_modules)
    
def get_custommodule_attempt_score(attempt_id):        
    score = db.session.query(
        db.func.count(CustomModuleUserResponse.response)
    ).filter_by(attempt_id=attempt_id, response='correct').scalar() or 0
    return score

def get_custommodule_attempt_maxscore(attempt_id):
    max_score = db.session.query(
        db.func.count(CustomModuleUserResponse.response)
    ).filter_by(attempt_id=attempt_id).scalar() or 0
    return max_score
    
def filter_custommodule_logic(student_id, status, subject_name, from_date, to_date, difficulty):
 
    query = db.session.query(
        CustomModuleAttempt.attempt_id,
        CustomModuleAttempt.date,
        CustomModuleAttempt.resume_test,
        CustomModuleConfig.config_id,
        CustomModuleConfig.subject_id,
        Subject.subject_name,
        CustomModuleConfig.module_id,
        Module.module_name,
        CustomModuleConfig.difficulty_level,
        CustomModuleConfig.question_count
    ).filter_by(student_id=student_id
                ).join(CustomModuleConfig, CustomModuleAttempt.attempt_id == CustomModuleConfig.attempt_id
                       ).join(Subject, Subject.subject_id == CustomModuleConfig.subject_id
                              ).join(Module, CustomModuleConfig.module_id == Module.module_id)    
    
    #Difficulty Filter
    
    if difficulty and difficulty != 'all':
        query = query.filter(CustomModuleConfig.difficulty_level == difficulty)
    
    #Exam Filter

    if subject_name and subject_name != 'all':
        query = query.filter(Subject.subject_name == subject_name)
    
    #Date Filter
    
    from_date_parsed=''
    to_date_parsed =''
    if from_date and from_date!='all':
        from_date_parsed = datetime.strptime(from_date, '%Y-%m-%d')
    if to_date and to_date!='all':
        to_date_parsed = datetime.strptime(to_date, '%Y-%m-%d')
    
    if from_date_parsed!='' and to_date_parsed!='':
        query = query.filter(CustomModuleAttempt.date.between(from_date_parsed, to_date_parsed))
    elif from_date_parsed!='':
        query = query.filter(CustomModuleAttempt.date >= from_date_parsed)
    elif to_date_parsed!='':
        query = query.filter(CustomModuleAttempt.date <= to_date_parsed)

    #Status Filter
    if status and status != 'all':
        if status == 'completed':
            query = query.filter(CustomModuleAttempt.resume_test == 'completed') 
        elif status == 'partially_completed':
            query = query.filter(CustomModuleAttempt.resume_test == 'incomplete')
            
    attempt_results = query.all()

    filtered_completed_attempts = defaultdict(list)
    filtered_incomplete_attempts = defaultdict(list)
    
    for attempt in attempt_results:
        config_data = {
                        'subject_name': attempt.subject_name ,
                        'subject_id': attempt.subject_id,
                        'module_name': attempt.module_name,
                        'module_id': attempt.module_id,
                        'difficulty_level': attempt.difficulty_level,
                        'question_count':attempt.question_count
                        }
        if attempt.resume_test == 'completed':
            if attempt.attempt_id not in filtered_completed_attempts:
                filtered_completed_attempts[attempt.attempt_id] = {
                    'status': 'completed',
                    'date': attempt.date,
                    'score': get_custommodule_attempt_score(attempt.attempt_id),
                    'max_score': get_custommodule_attempt_maxscore(attempt.attempt_id),
                    'configs': [config_data]
                }
            else:
                filtered_completed_attempts[attempt.attempt_id]['configs'].append(config_data)
        else:
            if attempt.attempt_id not in filtered_incomplete_attempts:
                filtered_incomplete_attempts[attempt.attempt_id] = {
                    'status': 'incomplete',
                    'date': attempt.date,
                    'score': get_custommodule_attempt_score(attempt.attempt_id),
                    'max_score': get_custommodule_attempt_maxscore(attempt.attempt_id),
                    'configs': [config_data]
                }
            else:
                filtered_incomplete_attempts[attempt.attempt_id]['configs'].append(config_data) 
        
    return filtered_completed_attempts,filtered_incomplete_attempts

@application.route('/delete_custom_attempt', methods=['POST'])
@login_required
def delete_custom_attempt():
    attempt_id = request.form.get('attempt_id')
    sub_query=" where attempt_id = :attempt_id"
    params = {"attempt_id": attempt_id}
    deleteConfigQuery = "delete from custommodules.config" + sub_query  
    db.session.execute(text(deleteConfigQuery),params)
    deleteUserResponseQuery = "delete from custommodules.userresponse" + sub_query     
    db.session.execute(text(deleteUserResponseQuery),params)
    deleteAttemptQuery = "delete from custommodules.attempt" + sub_query   
    db.session.execute(text(deleteAttemptQuery),params)
    db.session.commit()
    return redirect('/CustomModuleDashboard')

@application.route('/filter_custommodule', methods=['POST'])
def filter_custommodule():
    student_id = session['user_id']
    status = request.form.get('status')
    subject_name = request.form.get('subject')
    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')
    difficulty = request.form.get('difficulty')

    filtered_completed_attempts,filtered_incomplete_attempts = filter_custommodule_logic(
        student_id, status, subject_name, from_date, to_date, difficulty
    )
    
    difficulty_map = {
    1: "Beginner",
    2: "Intermediate",
    3: "Proficient",
    4: "Advanced",
    5: "Expert",
    }

    return render_template('CustomModuleAccordion.html', custom_attempt_details_completed=filtered_completed_attempts,custom_attempt_details_incomplete=filtered_incomplete_attempts, difficulty_map = difficulty_map)

@application.route('/CustomModulePieChartData', methods=['GET'])
def get_CMPieChartData():
    attempt_ids = session.get('custommodule_attempt_ids', {})
    
    if not attempt_ids:
        return jsonify({'error': 'attempt_ids is required'})

    # Convert attempt_ids to a tuple for the query
    attempt_ids_tuple = tuple(attempt_ids)
         
    if len(attempt_ids):
        query = text("""
            SELECT subject_name, COUNT(config.attempt_id) AS attempt_count
            FROM meta.subject
            JOIN custommodules.config ON config.subject_id = subject.subject_id
            WHERE config.attempt_id IN :attempt_ids
            GROUP BY subject_name
        """)

        # Execute the query with the parameter
        result = db.session.execute(query, {'attempt_ids': attempt_ids_tuple})

        # Process the result into labels and series
        labels = []
        series = []
        for row in result:
            subject_name, attempt_count = row  # Unpack the tuple
            labels.append(subject_name)
            series.append(attempt_count)
            
        pieChartData = {
            "labels": labels,
            "series": series,
        }
        return jsonify(pieChartData)
    else:
        pieChartData = {
            "labels": [],
            "series": [],
        }
        
        return jsonify(pieChartData)

@application.route('/CustomModuleBarChartData', methods=['GET'])
def get_CMBarChartData():
    # Fetch exam attempt details from session or database
    attempt_ids = session.get('custommodule_attempt_ids')
    
    if len(attempt_ids):
        barChart_query = text(
            """
            SELECT 
            meta.subject.subject_name,
            COUNT(CASE WHEN custommodules.userresponse.response = 'correct' THEN 1 END) * 100.0 / COUNT(*) AS avg_score
            FROM custommodules.userresponse
            JOIN meta.question
            ON custommodules.userresponse.q_id = meta.question.q_id
            JOIN meta.subject
            ON meta.question.subject_id = meta.subject.subject_id
            WHERE 
            custommodules.userresponse.attempt_id IN :attempt_ids
            GROUP BY meta.subject.subject_name;
            """
        )
        
        params = {"attempt_ids": tuple(attempt_ids)}
        
        lineChart_responses = db.session.execute(barChart_query, params).fetchall()
        
        series_data = []
        for subject_name, average_score in lineChart_responses:
            # Append data in the required format
            series_data.append({"x": subject_name, "y": average_score})

        # Prepare series for the bar chart
        series = [{"name": "Average Score by Subjects", "data": series_data}]

        # Return JSON response
        return jsonify({"series": series})
    
    else:
        series = [{"name": "Average Score by Subjects", "data": []}]
        return jsonify({"series": series})
    
@application.route('/CustomModuleLineChartData', methods=['GET'])
def get_CMLineChartData():
    # Fetch exam attempt details from session or database
    attempt_ids = session.get('custommodule_attempt_ids', {})
    
    if len(attempt_ids):
    
        lineChart_query = text(
            """
            SELECT 
            meta.subject.subject_name,
            meta.question.difficulty_level,
            COUNT(CASE WHEN custommodules.userresponse.response = 'correct' THEN 1 END) * 100.0 / COUNT(*) AS avg_score
            FROM custommodules.userresponse
            JOIN meta.question
            ON custommodules.userresponse.q_id = meta.question.q_id
            JOIN meta.subject
            ON meta.question.subject_id = meta.subject.subject_id
            WHERE 
            custommodules.userresponse.attempt_id IN :attempt_ids
            GROUP BY meta.subject.subject_name, meta.question.difficulty_level;
            """
        )
        
        params = {"attempt_ids": tuple(attempt_ids)}
        
        lineChart_responses = db.session.execute(lineChart_query, params).fetchall()

        # Extract unique subject names for labels
        labels = list(set(row[0] for row in lineChart_responses))
        # Map labels to indices for easier assignment
        label_indices = {label: idx for idx, label in enumerate(labels)}    
        
        subjects_placeholder = [0] * len(labels)
        
        # Prepare series for the bar chart
        series = [{"name": "Beginner", "data": subjects_placeholder.copy(), "color": '#F2BC2A'},
                {"name": "Intermediate", "data": subjects_placeholder.copy(), "color": '#4b5563'},
                {"name": "Proficient", "data": subjects_placeholder.copy(), "color": '#0ABDDB'},
                {"name": "Advanced", "data": subjects_placeholder.copy(), "color": '#90EE90'},
                {"name": "Expert", "data": subjects_placeholder.copy(), "color": '#FB9251'}]
        
        for subject_name,difficulty_level,avg_score in lineChart_responses:
            series[difficulty_level-1]["data"][label_indices[subject_name]] = avg_score
            
        lineChartData = {
            "labels": labels,
            "series": series,
        }
        
        # Return JSON response
        return jsonify(lineChartData)
    
    else:
        lineChartData = {
            "labels": [],
            "series": [],
        }
        
        # Return JSON response
        return jsonify(lineChartData)

# endregion

# region CustomModule Test

@application.route('/CustomModuleInstruction', methods=['POST'])
@login_required
def customModuleInstruction():
    data = request.form.get('data')
    data = json.loads(data) if data else []
    custom_configs = []

    for item in data:
        config_dict = {}
        config_dict['subject_id'] = item.get('subject_id')
        config_dict['subject_name'] = item.get('subject_name')
        config_dict['module_id'] = item.get('module_id')
        config_dict['module_name'] = item.get('module_name')
        config_dict['difficulty_level'] = item.get('difficulty_level')
        config_dict['difficulty_name'] = item.get('difficulty_name')
        config_dict['question_count'] = item.get('question_count')
        custom_configs.append(config_dict)
    return render_template('CustomModuleInstruction.html', configs=custom_configs)    

def create_attempt_custommodule(custom_configs):    
    
    student_id = session['user_id']
    
    # Generate a new config_id (use a sequence or the maximum current config_id + 1)
    new_attempt_id = db.session.query(db.func.max(CustomModuleAttempt.attempt_id)).scalar() or 0
    new_attempt_id += 1
    
    current_utc_time = datetime.now(timezone.utc)
    new_attempt = CustomModuleAttempt(
        attempt_id = new_attempt_id,
        date=current_utc_time.date(),
        student_id=student_id,
        resume_test='incomplete'
    )

    # Add to the database session and commit
    db.session.add(new_attempt)
    db.session.commit()

    # Convert the string to a Python list of dictionaries
    custom_configs = custom_configs.replace("'", '"')  # Replace single quotes with double quotes
    custom_configs = json.loads(custom_configs)

    for item in custom_configs:
        subject_id = item['subject_id']
        module_id = item['module_id']
        difficulty_level = item['difficulty_level']
        question_count = item['question_count']
        new_config_id = db.session.query(db.func.max(CustomModuleConfig.config_id)).scalar() or 0
        new_config_id+=1
        # Create a new CustomModuleConfig entry
        new_config = CustomModuleConfig(
            config_id=new_config_id,
            student_id=student_id,
            subject_id=subject_id,
            module_id=module_id,
            difficulty_level=difficulty_level,
            question_count=question_count,
            attempt_id=new_attempt_id
        )

        # Add to session and commit
        db.session.add(new_config)

    db.session.commit()   
    
    # Generate a hash to protect the test link
    # hash_value = generate_hash(f"{student_id}:{new_attempt_id}")
    
    return new_attempt_id

@application.route('/CustomModuleCreateTest', methods=['POST'])
@login_required
def customModuleCreateTest():
    if request.method == 'POST':
        custom_configs = request.form.get('configs')
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('loginPage'))

    student_id = session['user_id']
    student = Login.query.filter_by(student_id=student_id).first()

    if student:
        attempt_id = create_attempt_custommodule(custom_configs)
        # if not hash_value or not check_hash(f"{student_id}:{attempt_id}", hash_value):
        #     flash('Invalid or missing hash value.', 'error')
        #     return redirect('/CustomModuleDashboard')       

        # Fetch total number of questions
        selected_questions = CustomModulesQuestionsGenerator.fetchCustomModuleQuestions_for_attempt(attempt_id)
        q_order=1

        for question in selected_questions:  
            custom_modules_user_response = CustomModuleUserResponse(q_id=question['q_id'],
                response='skipped',
                attempt_id=attempt_id,
                q_order=q_order,
                selected_option={},
                question_status='not_attempted'
            )
            db.session.add(custom_modules_user_response) 
            q_order+=1
        db.session.commit()

        return redirect(url_for('customModuleTest', attempt_id=attempt_id))
    else:
        flash('Student not logged in.', 'error')
        return redirect('/')

@application.route('/CustomModuleTest', methods=['GET','POST'])
@login_required
def customModuleTest():
    student_id = session['user_id']    
    
    # If from custommodulecreatetest redirect
    if request.method == 'GET':
        attempt_id = request.args.get('attempt_id')
    # If from custommoduleresumeetest redirect
    else:
        attempt_id = request.form.get('attempt_id')
    
    # Check if attempt exists in the table
    attempt = CustomModuleAttempt.query.filter_by(attempt_id = attempt_id, student_id = student_id).first()

    if not attempt:
        flash('Invalid attempt. Please try again.', 'error')
        return redirect('/CustomModuleDashboard')

    if attempt.resume_test!='incomplete':
        flash('Cannot attempt this test.', 'error')
        return redirect('/CustomModuleDashboard')
    
    customModResumeQuery = text("""
        SELECT 
            question.q_id,
            direction.direction_description,
            question.question_description,
            question.answer_options,
            question.max_score,
            question.correct_option,
            question.solution_explanation,
            question.multi_select,
            userresponse.selected_option,
            userresponse.question_status
        FROM custommodules.userresponse
        JOIN meta.question ON userresponse.q_id = question.q_id
        JOIN meta.direction ON question.direction_id = direction.direction_id
        WHERE userresponse.attempt_id = :attempt_id
        order by userresponse.q_order
    """)
     
    params = {"attempt_id": attempt_id}    
    responses = db.session.execute(customModResumeQuery, params).fetchall()
    
    questions = []
    
    for response in responses:
        question_data = {
            'q_id': response.q_id,
            'direction_description': response.direction_description,
            'question_description': response.question_description,
            'answer_options': response.answer_options,
            'choice_type' : response.choice_type,
            'max_score': response.max_score,
            'correct_option': response.correct_option,
            'solution_explanation': response.solution_explanation,
            'multi_select': response.multi_select,
            'selected_option_list': response.selected_option if response.selected_option else [], 
            'question_status': response.question_status if response.question_status else 'not_attempted'
        }
        
        if question_data['choice_type'] == 'image':
            new_options = {}
            for k, v in question_data['answer_options'].items():
                signed_url = get_presigned_image_url(v)
                new_options[k] = signed_url if signed_url else v
            question_data['answer_options'] = new_options
        
        questions.append(question_data)

    return render_template('CustomModuleTest.html', questions=questions, attempt_id=attempt_id)

@application.route('/SubmitCustomModule', methods=['GET', 'POST'])
def submitCustomModule():
    try:
        data = request.json
        if not data:
            return "Unsupported Media Type NO JSON", 415
        
        if 'user_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('loginPage'))

        student_id = session['user_id']
        student = Login.query.filter_by(student_id=student_id).first()

        if not student:
            flash('Student not logged in.', 'error')
            return redirect(url_for('loginPage'))

        attempt_id = data.get('attempt_id')
        selected_options = data.get('selectedOptions')
        selected_options_for_q_id = data.get('selectedOptionsForq_id')
        q_id_to_q_order = data.get('qIdToQOrder')
        question_status = data.get('questionStatus')
        question_status_dict = json.loads(question_status)
        
        partial_complete = data.get('partial_complete')
        
        # Print received localStorage data to the server console
        # print(f"Selected Options: {selected_options}")
        # print(f"Selected Options for Q_id: {selected_options_for_q_id}")
        # print(f"Question Status: {question_status}")
        # print(f"Q Id to Q Order: {q_id_to_q_order}")
        
        if not partial_complete:
            setTestCompletedQuery = text("""update custommodules.attempt
                                    set resume_test = 'completed'
                                    where attempt_id = :attempt_id
                                        """)
        
            params = {"attempt_id": attempt_id}    
            db.session.execute(setTestCompletedQuery, params)
            db.session.commit()
        
        # delete from userresponse if it already has any
        
        deletePrevResponseQuery = text("""delete from custommodules.userresponse
                                where attempt_id = :attempt_id
                                    """)
     
        params = {"attempt_id": attempt_id}    
        db.session.execute(deletePrevResponseQuery, params)
        db.session.commit()
        
        answer_status = {}
        questions = Question.query.all()
        
        # Create a dictionary to easily access correct options by q_id
        correct_options_dict = {q.q_id: q.correct_option for q in questions}
        
        # Evaluate each question
        for q_id, options in selected_options_for_q_id.items():
            correct_options = correct_options_dict.get(int(q_id), [])
            if not options:
                answer_status[q_id] = 'skipped'
            elif set(options) == set(correct_options):
                answer_status[q_id] = 'correct'
            else:
                answer_status[q_id] = 'incorrect'
        # print(f"Answer Status: {answer_status}")

        # Save the data to userresponse table
        for q_id, options in selected_options_for_q_id.items():
            response = answer_status.get(q_id, 'skipped')
            q_order = q_id_to_q_order.get(q_id) 
            question_status = question_status_dict.get(str(q_order),'not_answered')
            selected_option = options
            custom_modules_user_response = CustomModuleUserResponse(q_id=q_id,
                response=response,
                attempt_id=attempt_id,
                q_order=q_order,
                selected_option=selected_option,
                question_status=question_status
            )
            db.session.add(custom_modules_user_response) 
        db.session.commit()
        
        return jsonify({"Success":"Successfully submitted CustomModule","attempt_id":attempt_id})
    
    except Exception as e:
        return jsonify({"Error": "An error occurred Details: {e}"})
    
# endregion

# region CustomModule Report

def cm_get_report_attempt_details(attempt_id):
    # student_id = session['user_id']
    attempt = CustomModuleAttempt.query.filter_by(attempt_id=attempt_id).first()

    # print(attempt)
    if attempt:
        return {
            'attempt_id': attempt.attempt_id,
            'date': attempt.date,
            'student_id': attempt.student_id
        }
    else:
        return None

def cm_get_report_responses(attempt_id):
    query = text("""
    SELECT * 
    FROM custommodules.userresponse
    JOIN meta.question ON custommodules.userresponse.q_id = meta.question.q_id
    JOIN meta.subject ON meta.subject.subject_id = meta.question.subject_id
    JOIN meta.module ON meta.module.module_id = meta.question.module_id
    WHERE attempt_id = :attempt_id
    """)

    responses = db.session.execute(query, {"attempt_id": attempt_id}).fetchall()
    return responses

def cm_get_report_table_details(responses):     
    
    subject_details = {}
    module_details = []
    
    for response in responses:
        
        #Subject consolidation section for table
        
        subject_name = response.subject_name
        module_name = response.module_name
        
        if subject_name not in subject_details:
            subject_details[subject_name] = {
                'subject_name': subject_name,
                'question_count': 0,
                'attempted': 0,
                'correct': 0,
                'incorrect': 0,
                'skipped': 0,
                'score': 0,
                'percentage': 0
            }
            
        if module_name not in module_details:
            module_details.append(module_name)
        
        if response.response == 'correct':
            subject_details[subject_name]['correct'] += 1
        elif response.response == 'incorrect':
            subject_details[subject_name]['incorrect'] += 1
        elif response.response == 'skipped':
            subject_details[subject_name]['skipped'] += 1    
        

    subject_details_flattened = []
    all_sections_totals = {
        'Total_Questions': 0,
        'Total_Attempted': 0,
        'Correct': 0,
        'Incorrect': 0,
        'Skipped': 0,
        'Score': 0,
        'Percentage': 0
    }

    for subject_name,details in subject_details.items():
        details['question_count'] = details['correct'] + details['incorrect'] + details['skipped']
        details['attempted'] = details['correct'] + details['incorrect']
        details['score'] = details['correct']
        if details['question_count'] > 0:
            details['percentage'] =  int((details['correct'] / details['question_count']) * 100)
        
        # all_sections_summary
        all_sections_totals['Total_Questions']+=details['question_count']
        all_sections_totals['Total_Attempted']+=details['attempted']
        all_sections_totals['Correct']+=details['correct']
        all_sections_totals['Incorrect']+=details['incorrect']
        all_sections_totals['Skipped']+=details['skipped']
        all_sections_totals['Score']+=details['score']
        
        subject_details_flattened.append(details)
    
    all_sections_totals['Percentage'] = int((all_sections_totals['Correct'] / all_sections_totals['Total_Questions']) * 100)
    
    return subject_details_flattened,module_details,all_sections_totals,

def cm_get_report_qa_details(attempt_id,subject='all',module='all',response_type='all'):
    base_query = """
    SELECT q_order,response,selected_option, correct_option, question_description, solution_explanation, answer_options , choice_type
    FROM custommodules.userresponse
    JOIN meta.question ON custommodules.userresponse.q_id = meta.question.q_id
    JOIN meta.subject ON meta.subject.subject_id = meta.question.subject_id
    JOIN meta.module ON meta.module.module_id = meta.question.module_id
    WHERE attempt_id = :attempt_id
    """
    params = {"attempt_id": attempt_id}
    
    if subject != 'all':
        base_query += " AND subject_name = :subject"
        params.update({"subject": subject})
    if module != 'all':
        base_query += " AND module_name = :module"
        params.update({"module": module})
    if response_type != 'all':
        base_query += " AND response = :response_type"
        params.update({"response_type": response_type})
        
    base_query+= " order by q_order"

    query= text(base_query)
    solutions = db.session.execute(query, params).fetchall()
    return solutions

@application.route('/CustomModuleReport', methods=['POST'])
def cmGenerateReport():
    attempt_id = request.form.get('attempt_id')
    attempt_details = cm_get_report_attempt_details(attempt_id)
    
    if attempt_details:
        attempt_id = attempt_details['attempt_id']
        date = attempt_details['date']
        student_id = attempt_details['student_id']
        
    student_name = f"{student.first_name} {student.last_name}" if (student := Student.query.filter_by(student_id=student_id).first()) else None
    responses = cm_get_report_responses(attempt_id)
    subjects,modules,all_sections= cm_get_report_table_details(responses)
    solutions = cm_get_report_qa_details(attempt_id)
    return render_template('CustomModuleReport.html',
                           subjects=subjects, modules=modules, all_sections=all_sections,
                           solutions = solutions, student_id = student_id, student_name=student_name ,date=date, attempt_id=attempt_id)

@application.route('/cm_filter_report', methods=['POST'])
def cm_filter_report():    
    attempt_id = request.form.get('attempt_id')
    total_questions = request.form.get('total_questions')
    selected_subject = request.form.get('subjects')
    selected_module = request.form.get('modules')
    selected_responsetype = request.form.get('responsetype')
    # print(selected_subject)
    # print(selected_responsetype)
    filtered_solutions = cm_get_report_qa_details(attempt_id,subject=selected_subject,module=selected_module,response_type=selected_responsetype)

    return render_template('ReportSolution.html',
                           solutions = filtered_solutions, total_questions = total_questions)

# endregion

# region Daily Practice Dashboard
    
def get_dp_student_metrics(student_id):
    # Step 1: Get all attempt IDs from dailypractice.attempt
    attempt_ids_query = text("""
        SELECT attempt_id 
        FROM dailypractice.attempt 
        WHERE student_id = :student_id
    """)
    attempt_ids = db.session.execute(attempt_ids_query, {'student_id': student_id}).fetchall()

    if not attempt_ids:
        return 0, 0, [], [], 0, []

    attempt_ids_list = [str(row[0]) for row in attempt_ids]
    attempt_ids_str = ", ".join(attempt_ids_list)

    # Step 2: Get correct response count
    correct_responses_query = text(f"""
        SELECT COUNT(response)
        FROM dailypractice.userresponse
        WHERE response = 'correct' AND attempt_id IN ({attempt_ids_str})
    """)
    correct_responses = db.session.execute(correct_responses_query).scalar()

    # Step 3: Get attempted options count
    attempted_options_query = text(f"""
        SELECT COUNT(response)
        FROM dailypractice.userresponse
        WHERE (response = 'correct' OR response = 'incorrect') AND attempt_id IN ({attempt_ids_str})
    """)
    attempted_options = db.session.execute(attempted_options_query).scalar()

    # Step 4: Get total questions attempted
    total_questions_attempted_query = text(f"""
        SELECT COUNT(*)
        FROM dailypractice.userresponse
        WHERE attempt_id IN ({attempt_ids_str})
    """)
    total_questions_attempted = db.session.execute(total_questions_attempted_query).scalar()

    # Step 5: Calculate accuracy and average
    accuracy = correct_responses / attempted_options if attempted_options > 0 else 0
    average = correct_responses / total_questions_attempted if total_questions_attempted > 0 else 0

    # Step 6: Get subjects attempted through dailypractice.config
    subject_query = text("""
        SELECT DISTINCT s.subject_id, s.subject_name
        FROM meta.subject AS s
        JOIN meta.subject_module_mapping AS smm ON s.subject_id = smm.subject_id
        JOIN meta.module AS m ON smm.module_id = m.module_id
        JOIN dailypractice.config AS c ON c.module_id = m.module_id
        WHERE c.student_id = :student_id
    """)
    subjects_attempted = db.session.execute(subject_query, {'student_id': student_id}).fetchall()
    subject_list = [{'subject_id': row.subject_id, 'subject_name': row.subject_name} for row in subjects_attempted]

    # Step 7: Get modules attempted
    module_query = text("""
        SELECT DISTINCT m.module_id, m.module_name, smm.subject_id
        FROM meta.module AS m
        JOIN meta.subject_module_mapping AS smm ON m.module_id = smm.module_id
        JOIN dailypractice.config AS c ON c.module_id = m.module_id
        WHERE c.student_id = :student_id
    """)
    modules_attempted = db.session.execute(module_query, {'student_id': student_id}).fetchall()
    module_list = [{'module_id': row.module_id, 'module_name': row.module_name, 'subject_id': row.subject_id} for row in modules_attempted]

    return int(accuracy * 100), int(average * 100), attempt_ids_list, subject_list, len(module_list), module_list

def get_dp_attempt_details(student_id):
    tests_completed,incomplete_tests,lapsed_tests = filter_dp_logic(
        student_id, 'all', 'all', 'all', 'all', 'all')
    
    return tests_completed,incomplete_tests,lapsed_tests

@application.route('/DailyPracticeDashboard')
@login_required
def dailyPracticeDashboard():
    student_id = session['user_id']
    student = Student.query.filter_by(student_id=student_id).first()
    student_name = f"{student.first_name} {student.last_name}"
    accuracy,average,attempt_ids,subjects,modules_attempted_count, modules  = get_dp_student_metrics(student_id=student_id)
    tests_completed,incomplete_tests,lapsed_tests = get_dp_attempt_details(student_id)
    all_subjects = getAllSubjects()
    all_modules = getAllModules()
    session['dp_attempt_ids'] = attempt_ids         
    
    difficulty_map = {
    1: "Beginner",
    2: "Intermediate",
    3: "Proficient",
    4: "Advanced",
    5: "Expert",
    }
    
    return render_template('DailyPracticeDashboard.html',dp_attempt_details_completed=tests_completed,dp_attempt_details_incomplete=incomplete_tests,dp_attempt_details_lapsed=lapsed_tests,
                           accuracy=accuracy,average=average, student_name=student_name, modules_attempted_count=modules_attempted_count, subjects=subjects, 
                           difficulty_map = difficulty_map, modules=modules, all_subjects= all_subjects,all_modules=all_modules)
    
def get_dp_attempt_score(attempt_id):        
    score = db.session.query(
        db.func.count(DailyPracticeUserResponse.response)
    ).filter_by(attempt_id=attempt_id, response='correct').scalar() or 0
    return score

def get_dp_attempt_maxscore(attempt_id):
    max_score = db.session.query(
        db.func.count(DailyPracticeUserResponse.response)
    ).filter_by(attempt_id=attempt_id).scalar() or 0
    return max_score
    
def filter_dp_logic(student_id, status, subject_name, from_date, to_date, difficulty):
    query = db.session.query(
        DailyPracticeAttempt.attempt_id,
        DailyPracticeAttempt.date,
        DailyPracticeAttempt.resume_test,
        DailyPracticeConfig.config_id,
        DailyPracticeConfig.subject_id,
        Subject.subject_name,
        DailyPracticeConfig.module_id,
        Module.module_name,
        DailyPracticeConfig.difficulty_level,
        DailyPracticeConfig.question_count
    ).filter_by(student_id=student_id
                ).join(DailyPracticeConfig, DailyPracticeAttempt.attempt_id == DailyPracticeConfig.attempt_id
                       ).join(Subject, Subject.subject_id == DailyPracticeConfig.subject_id
                              ).join(Module, DailyPracticeConfig.module_id == Module.module_id)    
    
    #Difficulty Filter
    
    if difficulty and difficulty != 'all':
        query = query.filter(DailyPracticeConfig.difficulty_level == difficulty)
    
    #Exam Filter

    if subject_name and subject_name != 'all':
        query = query.filter(Subject.subject_name == subject_name)
    
    #Date Filter
    
    from_date_parsed=''
    to_date_parsed =''
    if from_date and from_date!='all':
        from_date_parsed = datetime.strptime(from_date, '%Y-%m-%d')
    if to_date and to_date!='all':
        to_date_parsed = datetime.strptime(to_date, '%Y-%m-%d')
    
    if from_date_parsed!='' and to_date_parsed!='':
        query = query.filter(DailyPracticeAttempt.date.between(from_date_parsed, to_date_parsed))
    elif from_date_parsed!='':
        query = query.filter(DailyPracticeAttempt.date >= from_date_parsed)
    elif to_date_parsed!='':
        query = query.filter(DailyPracticeAttempt.date <= to_date_parsed)

    
    current_utc_time = datetime.now(timezone.utc).date() 
    #Status Filter
    if status and status != 'all':
        if status == 'completed':
            query = query.filter(DailyPracticeAttempt.resume_test == 'completed') 
        elif status == 'partially_completed':
            query = query.filter(DailyPracticeAttempt.resume_test == 'incomplete', DailyPracticeAttempt.date > current_utc_time)
        elif status == 'lapsed':
            query = query.filter(DailyPracticeAttempt.resume_test == 'incomplete', DailyPracticeAttempt.date < current_utc_time)
            
    attempt_results = query.all()

    filtered_completed_attempts = defaultdict(list)
    filtered_incomplete_attempts = defaultdict(list)
    filtered_lapsed_attempts = defaultdict(list)
    
    for attempt in attempt_results:
        config_data = {
                        'subject_name': attempt.subject_name ,
                        'subject_id': attempt.subject_id,
                        'module_name': attempt.module_name,
                        'module_id': attempt.module_id,
                        'difficulty_level': attempt.difficulty_level,
                        'question_count':attempt.question_count
                        }
        if attempt.resume_test == 'completed':
            if attempt.attempt_id not in filtered_completed_attempts:
                filtered_completed_attempts[attempt.attempt_id] = {
                    'status': 'completed',
                    'date': attempt.date,
                    'score': get_dp_attempt_score(attempt.attempt_id),
                    'max_score': get_dp_attempt_maxscore(attempt.attempt_id),
                    'configs': [config_data]
                }
            else:
                filtered_completed_attempts[attempt.attempt_id]['configs'].append(config_data)
        elif attempt.date < current_utc_time:
            if attempt.attempt_id not in filtered_lapsed_attempts:                
                filtered_lapsed_attempts[attempt.attempt_id] = {
                    'status': 'incomplete',
                    'date': attempt.date,
                    'score': get_dp_attempt_score(attempt.attempt_id),
                    'max_score': get_dp_attempt_maxscore(attempt.attempt_id),
                    'configs': [config_data]
                }
            else:
                filtered_lapsed_attempts[attempt.attempt_id]['configs'].append(config_data)
        else:                        
            if attempt.attempt_id not in filtered_incomplete_attempts:                
                filtered_incomplete_attempts[attempt.attempt_id] = {
                    'status': 'incomplete',
                    'date': attempt.date,
                    'score': get_dp_attempt_score(attempt.attempt_id),
                    'max_score': get_dp_attempt_maxscore(attempt.attempt_id),
                    'configs': [config_data]
                }
            else:
                filtered_incomplete_attempts[attempt.attempt_id]['configs'].append(config_data) 
        
    return filtered_completed_attempts,filtered_incomplete_attempts,filtered_lapsed_attempts

@application.route('/delete_dp_attempt', methods=['POST'])
@login_required
def delete_dp_attempt():
    attempt_id = request.form.get('attempt_id')
    sub_query=" where attempt_id = :attempt_id"
    params = {"attempt_id": attempt_id}
    deleteConfigQuery = "delete from dailypractice.config" + sub_query  
    db.session.execute(text(deleteConfigQuery),params)
    deleteUserResponseQuery = "delete from dailypractice.userresponse" + sub_query     
    db.session.execute(text(deleteUserResponseQuery),params)
    deleteAttemptQuery = "delete from dailypractice.attempt" + sub_query   
    db.session.execute(text(deleteAttemptQuery),params)
    db.session.commit()
    return redirect('/DailyPracticeDashboard')

@application.route('/dp_edit_attempt_date', methods=['POST'])
@login_required
def dp_edit_attempt_date():    
    attempt_id = request.form.get('attempt_id')
    date = request.form.get('change_attempt_date')
    editAttemptDateQuery = text("""update dailypractice.attempt
                                    set date = :date
                                    where attempt_id = :attempt_id
                                        """)
        
    params = {"attempt_id": attempt_id, "date": date}    
    db.session.execute(editAttemptDateQuery, params)
    db.session.commit()
    return redirect('/DailyPracticeDashboard')

@application.route('/filter_dp', methods=['POST'])
def filter_dp():
    student_id = session['user_id']
    status = request.form.get('status')
    subject_name = request.form.get('subject')
    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')
    difficulty = request.form.get('difficulty')

    filtered_completed_attempts,filtered_incomplete_attempts,filtered_lapsed_attempts = filter_dp_logic(
        student_id, status, subject_name, from_date, to_date, difficulty
    )
    
    difficulty_map = {
    1: "Beginner",
    2: "Intermediate",
    3: "Proficient",
    4: "Advanced",
    5: "Expert",
    }

    return render_template('DailyPracticeAccordion.html', dp_attempt_details_completed=filtered_completed_attempts,dp_attempt_details_incomplete=filtered_incomplete_attempts,dp_attempt_details_lapsed=filtered_lapsed_attempts, difficulty_map = difficulty_map)

@application.route('/DailyPracticePieChartData', methods=['GET'])
def get_DPPieChartData():
    attempt_ids = session.get('dp_attempt_ids', {})
    
    if not attempt_ids:
        return jsonify({'error': 'attempt_ids is required'})

    # Convert attempt_ids to a tuple for the query
    attempt_ids_tuple = tuple(attempt_ids)
         
    if len(attempt_ids):
        query = text("""
            SELECT subject_name, COUNT(config.attempt_id) AS attempt_count
            FROM meta.subject
            JOIN dailypractice.config ON config.subject_id = subject.subject_id
            WHERE config.attempt_id IN :attempt_ids
            GROUP BY subject_name
        """)

        # Execute the query with the parameter
        result = db.session.execute(query, {'attempt_ids': attempt_ids_tuple})

        # Process the result into labels and series
        labels = []
        series = []
        for row in result:
            subject_name, attempt_count = row  # Unpack the tuple
            labels.append(subject_name)
            series.append(attempt_count)
            
        pieChartData = {
            "labels": labels,
            "series": series,
        }
        return jsonify(pieChartData)
    else:
        pieChartData = {
            "labels": [],
            "series": [],
        }
        
        return jsonify(pieChartData)

@application.route('/DailyPracticeBarChartData', methods=['GET'])
def get_DPBarChartData():
    # Fetch exam attempt details from session or database
    attempt_ids = session.get('dp_attempt_ids')
    
    if len(attempt_ids):
        barChart_query = text(
            """
            SELECT 
            meta.subject.subject_name,
            COUNT(CASE WHEN dailypractice.userresponse.response = 'correct' THEN 1 END) * 100.0 / COUNT(*) AS avg_score
            FROM dailypractice.userresponse
            JOIN meta.question
            ON dailypractice.userresponse.q_id = meta.question.q_id
            JOIN meta.subject
            ON meta.question.subject_id = meta.subject.subject_id
            WHERE 
            dailypractice.userresponse.attempt_id IN :attempt_ids
            GROUP BY meta.subject.subject_name;
            """
        )
        
        params = {"attempt_ids": tuple(attempt_ids)}
        
        lineChart_responses = db.session.execute(barChart_query, params).fetchall()
        
        series_data = []
        for subject_name, average_score in lineChart_responses:
            # Append data in the required format
            series_data.append({"x": subject_name, "y": average_score})

        # Prepare series for the bar chart
        series = [{"name": "Average Score by Subjects", "data": series_data}]

        # Return JSON response
        return jsonify({"series": series})
    
    else:
        series = [{"name": "Average Score by Subjects", "data": []}]
        return jsonify({"series": series})
    
@application.route('/DailyPracticeLineChartData', methods=['GET'])
def get_DPLineChartData():
    # Fetch exam attempt details from session or database
    attempt_ids = session.get('dp_attempt_ids', {})
    
    if len(attempt_ids):
    
        lineChart_query = text(
            """
            SELECT 
            meta.subject.subject_name,
            meta.question.difficulty_level,
            COUNT(CASE WHEN dailypractice.userresponse.response = 'correct' THEN 1 END) * 100.0 / COUNT(*) AS avg_score
            FROM dailypractice.userresponse
            JOIN meta.question
            ON dailypractice.userresponse.q_id = meta.question.q_id
            JOIN meta.subject
            ON meta.question.subject_id = meta.subject.subject_id
            WHERE 
            dailypractice.userresponse.attempt_id IN :attempt_ids
            GROUP BY meta.subject.subject_name, meta.question.difficulty_level;
            """
        )
        
        params = {"attempt_ids": tuple(attempt_ids)}
        
        lineChart_responses = db.session.execute(lineChart_query, params).fetchall()

        # Extract unique subject names for labels
        labels = list(set(row[0] for row in lineChart_responses))
        # Map labels to indices for easier assignment
        label_indices = {label: idx for idx, label in enumerate(labels)}    
        
        subjects_placeholder = [0] * len(labels)
        
        # Prepare series for the bar chart
        series = [{"name": "Beginner", "data": subjects_placeholder.copy(), "color": '#F2BC2A'},
                {"name": "Intermediate", "data": subjects_placeholder.copy(), "color": '#4b5563'},
                {"name": "Proficient", "data": subjects_placeholder.copy(), "color": '#0ABDDB'},
                {"name": "Advanced", "data": subjects_placeholder.copy(), "color": '#90EE90'},
                {"name": "Expert", "data": subjects_placeholder.copy(), "color": '#FB9251'}]
        
        for subject_name,difficulty_level,avg_score in lineChart_responses:
            series[difficulty_level-1]["data"][label_indices[subject_name]] = avg_score
            
        lineChartData = {
            "labels": labels,
            "series": series,
        }
        
        # Return JSON response
        return jsonify(lineChartData)
    
    else:
        lineChartData = {
            "labels": [],
            "series": [],
        }
        
        # Return JSON response
        return jsonify(lineChartData)

@application.route('/DailyPracticeCalendar', methods=['POST'])
def view_schedule_calendar():
    return render_template('DailyPracticeCalendar.html')

@application.route('/dc_fetch_attempts')
def dc_fetch_attempts():
    student_id = session['user_id']
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    # Ensure dates are in the correct format
    # if from_date:
    #     from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
    # if to_date:
    #     to_date = datetime.strptime(to_date, "%Y-%m-%d").date()

    # Call `filter_dp_logic` with extracted dates
    tests_completed, incomplete_tests, lapsed_tests = filter_dp_logic(
        student_id, 'all', 'all', from_date, to_date, 'all'
    )

    # Convert results to JSON and return
    return jsonify([tests_completed, incomplete_tests, lapsed_tests])

# endregion

# region Daily Practice Test

@application.route('/DailyPracticeInstruction', methods=['POST'])
@login_required
def dailyPracticeInstruction():
    dp_configs = request.form.get('configs')
    return render_template('DailyPracticeInstruction.html', configs=dp_configs)

def create_attempt_dp(dp_configs,scheduled_date):    
    
    student_id = session['user_id']
    
    # Generate a new config_id (use a sequence or the maximum current config_id + 1)
    new_attempt_id = db.session.query(db.func.max(DailyPracticeAttempt.attempt_id)).scalar() or 0
    new_attempt_id += 1
    
    # current_utc_time = datetime.now(timezone.utc)
    new_attempt = DailyPracticeAttempt(
        attempt_id = new_attempt_id,
        # date=current_utc_time.date(),
        date = datetime.strptime(scheduled_date, '%Y-%m-%d').date(),
        student_id=student_id,
        resume_test='incomplete'
    )

    # Add to the database session and commit
    db.session.add(new_attempt)
    db.session.commit()

    # Convert the string to a Python list of dictionaries
    # dp_configs = dp_configs.replace("'", '"')  # Replace single quotes with double quotes
    # dp_configs = json.loads(dp_configs)

    for item in dp_configs:
        subject_id = item['subject_id']
        module_id = item['module_id']
        difficulty_level = item['difficulty_level']
        question_count = item['question_count']
        new_config_id = db.session.query(db.func.max(DailyPracticeConfig.config_id)).scalar() or 0
        new_config_id+=1
        # Create a new DailyPracticeConfig entry
        new_config = DailyPracticeConfig(
            config_id=new_config_id,
            student_id=student_id,
            subject_id=subject_id,
            module_id=module_id,
            difficulty_level=difficulty_level,
            question_count=question_count,
            attempt_id=new_attempt_id
        )

        # Add to session and commit
        db.session.add(new_config)

    db.session.commit()   
    
    return new_attempt_id

def get_dates_between(start_date, end_date, frequency):
    """
    Generate all dates between start_date and end_date based on the specified frequency.
    
    :param start_date: Start date as a string in 'YYYY-MM-DD' format.
    :param end_date: End date as a string in 'YYYY-MM-DD' format.
    :param frequency: Frequency ('daily', 'weekly', 'monthly').
    :return: List of dates in 'YYYY-MM-DD' format.
    """
    # Parse the input strings into datetime objects
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Initialize the result list
    dates = []
    current_date = start_date

    # Generate dates based on the frequency
    while current_date <= end_date:
        dates.append(current_date.strftime("%Y-%m-%d"))
        if frequency == "daily":
            current_date += timedelta(days=1)
        elif frequency == "weekly":
            current_date += timedelta(weeks=1)
        elif frequency == "monthly":
            current_date += relativedelta(months=1)
        else:
            raise ValueError("Invalid frequency. Choose 'daily', 'weekly', or 'monthly'.")
    
    return dates

@application.route('/DailyPracticeCreateTest', methods=['POST'])
@login_required
def dailyPracticeCreateTest():
    if request.method == 'POST':        
        # dp_configs = request.form.get('configs')
            
        scheduler_data = request.form.get('schedulerdata')        
        scheduler_data = json.loads(scheduler_data) if scheduler_data else []
        frequency = scheduler_data[0].get('frequency')
        start_date = scheduler_data[0].get('start_date')
        end_date = scheduler_data[0].get('end_date')
        scheduled_dates = get_dates_between(start_date, end_date, frequency)
        
        data = request.form.get('data')
        data = json.loads(data) if data else []
        dp_configs = []

        for item in data:
            config_dict = {}
            config_dict['subject_id'] = item.get('subject_id')
            config_dict['subject_name'] = item.get('subject_name')
            config_dict['module_id'] = item.get('module_id')
            config_dict['module_name'] = item.get('module_name')
            config_dict['difficulty_level'] = item.get('difficulty_level')
            config_dict['difficulty_name'] = item.get('difficulty_name')
            config_dict['question_count'] = item.get('question_count')
            dp_configs.append(config_dict)        
        
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('loginPage'))

    student_id = session['user_id']
    student = Login.query.filter_by(student_id=student_id).first()

    if student:
        for scheduled_date in scheduled_dates:
            attempt_id = create_attempt_dp(dp_configs,scheduled_date)
            # Fetch total number of questions
            selected_questions = DailyPracticeQuestionsGenerator.fetchDailyPracticeQuestions_for_attempt(attempt_id)
            q_order=1

            for question in selected_questions:  
                dp_modules_user_response = DailyPracticeUserResponse(q_id=question['q_id'],
                    response='skipped',
                    attempt_id=attempt_id,
                    q_order=q_order,
                    selected_option={},
                    question_status='not_attempted'
                )
                db.session.add(dp_modules_user_response) 
                q_order+=1
            db.session.commit()

        # return redirect(url_for('dailyPracticeTest', attempt_id=attempt_id))
        return redirect('/DailyPracticeDashboard')
    else:
        flash('Student not logged in.', 'error')
        return redirect('/')

@application.route('/DailyPracticeTest', methods=['GET','POST'])
@login_required
def dailyPracticeTest():
    student_id = session['user_id']    
    
    # If from DailyPracticecreatetest redirect
    if request.method == 'GET':
        attempt_id = request.args.get('attempt_id')
    # If from DailyPracticeresumeetest redirect
    else:
        attempt_id = request.form.get('attempt_id')
    
    # Check if attempt exists in the table
    attempt = DailyPracticeAttempt.query.filter_by(attempt_id = attempt_id, student_id = student_id).first()

    if not attempt:
        flash('Invalid attempt. Please try again.', 'error')
        return redirect('/DailyPracticeDashboard')

    if attempt.resume_test!='incomplete':
        flash('Cannot attempt this test.', 'error')
        return redirect('/DailyPracticeDashboard')
    
    dpModResumeQuery = text("""
        SELECT 
            question.q_id,
            direction.direction_description,
            question.question_description,
            question.answer_options,
            question.max_score,
            question.correct_option,
            question.solution_explanation,
            question.multi_select,
            userresponse.selected_option,
            userresponse.question_status
        FROM dailypractice.userresponse
        JOIN meta.question ON userresponse.q_id = question.q_id
        JOIN meta.direction ON question.direction_id = direction.direction_id
        WHERE userresponse.attempt_id = :attempt_id
        order by userresponse.q_order
    """)
     
    params = {"attempt_id": attempt_id}    
    responses = db.session.execute(dpModResumeQuery, params).fetchall()
    
    questions = []
    
    for response in responses:
        question_data = {
            'q_id': response.q_id,
            'direction_description': response.direction_description,
            'question_description': response.question_description,
            'answer_options': response.answer_options,
            'choice_type' : response.choice_type,
            'max_score': response.max_score,
            'correct_option': response.correct_option,
            'solution_explanation': response.solution_explanation,
            'multi_select': response.multi_select,
            'selected_option_list': response.selected_option if response.selected_option else [], 
            'question_status': response.question_status if response.question_status else 'not_attempted'
        }
        
        if question_data['choice_type'] == 'image':
            new_options = {}
            for k, v in question_data['answer_options'].items():
                signed_url = get_presigned_image_url(v)
                new_options[k] = signed_url if signed_url else v
            question_data['answer_options'] = new_options
        
        questions.append(question_data)

    return render_template('DailyPracticeTest.html', questions=questions, attempt_id=attempt_id)

@application.route('/SubmitDailyPractice', methods=['GET', 'POST'])
def submitDailyPracticeModule():
    try:
        data = request.json
        if not data:
            return "Unsupported Media Type NO JSON", 415
        
        if 'user_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('loginPage'))

        student_id = session['user_id']
        student = Login.query.filter_by(student_id=student_id).first()

        if not student:
            flash('Student not logged in.', 'error')
            return redirect(url_for('loginPage'))

        attempt_id = data.get('attempt_id')
        selected_options = data.get('selectedOptions')
        selected_options_for_q_id = data.get('selectedOptionsForq_id')
        q_id_to_q_order = data.get('qIdToQOrder')
        question_status = data.get('questionStatus')
        question_status_dict = json.loads(question_status)
        
        partial_complete = data.get('partial_complete')
        
        # Print received localStorage data to the server console
        # print(f"Selected Options: {selected_options}")
        # print(f"Selected Options for Q_id: {selected_options_for_q_id}")
        # print(f"Question Status: {question_status}")
        # print(f"Q Id to Q Order: {q_id_to_q_order}")
        
        if not partial_complete:
            setTestCompletedQuery = text("""update dailypractice.attempt
                                    set resume_test = 'completed'
                                    where attempt_id = :attempt_id
                                        """)
        
            params = {"attempt_id": attempt_id}    
            db.session.execute(setTestCompletedQuery, params)
            db.session.commit()
        
        # delete from userresponse if it already has any
        
        deletePrevResponseQuery = text("""delete from dailypractice.userresponse
                                where attempt_id = :attempt_id
                                    """)
     
        params = {"attempt_id": attempt_id}    
        db.session.execute(deletePrevResponseQuery, params)
        db.session.commit()
        
        answer_status = {}
        questions = Question.query.all()
        
        # Create a dictionary to easily access correct options by q_id
        correct_options_dict = {q.q_id: q.correct_option for q in questions}
        
        # Evaluate each question
        for q_id, options in selected_options_for_q_id.items():
            correct_options = correct_options_dict.get(int(q_id), [])
            if not options:
                answer_status[q_id] = 'skipped'
            elif set(options) == set(correct_options):
                answer_status[q_id] = 'correct'
            else:
                answer_status[q_id] = 'incorrect'
        # print(f"Answer Status: {answer_status}")

        # Save the data to userresponse table
        for q_id, options in selected_options_for_q_id.items():
            response = answer_status.get(q_id, 'skipped')
            q_order = q_id_to_q_order.get(q_id) 
            question_status = question_status_dict.get(str(q_order),'not_answered')
            selected_option = options
            dp_modules_user_response = DailyPracticeUserResponse(q_id=q_id,
                response=response,
                attempt_id=attempt_id,
                q_order=q_order,
                selected_option=selected_option,
                question_status=question_status
            )
            db.session.add(dp_modules_user_response) 
        db.session.commit()
        
        return jsonify({"Success":"Successfully submitted DailyPractice","attempt_id":attempt_id})
    
    except Exception as e:
        return jsonify({"Error": "An error occurred Details: {e}"})
    
# endregion

# region Daily Practice Report

def dp_get_report_attempt_details(attempt_id):
    # student_id = session['user_id']
    attempt = DailyPracticeAttempt.query.filter_by(attempt_id=attempt_id).first()

    # print(attempt)
    if attempt:
        return {
            'attempt_id': attempt.attempt_id,
            'date': attempt.date,
            'student_id': attempt.student_id
        }
    else:
        return None

def dp_get_report_responses(attempt_id):
    query = text("""
    SELECT * 
    FROM dailypractice.userresponse
    JOIN meta.question ON dailypractice.userresponse.q_id = meta.question.q_id
    JOIN meta.subject ON meta.subject.subject_id = meta.question.subject_id
    JOIN meta.module ON meta.module.module_id = meta.question.module_id
    WHERE attempt_id = :attempt_id
    """)

    responses = db.session.execute(query, {"attempt_id": attempt_id}).fetchall()
    return responses

def dp_get_report_table_details(responses):     
    
    subject_details = {}
    module_details = []
    
    for response in responses:
        
        #Subject consolidation section for table
        
        subject_name = response.subject_name
        module_name = response.module_name
        
        if subject_name not in subject_details:
            subject_details[subject_name] = {
                'subject_name': subject_name,
                'question_count': 0,
                'attempted': 0,
                'correct': 0,
                'incorrect': 0,
                'skipped': 0,
                'score': 0,
                'percentage': 0
            }
            
        if module_name not in module_details:
            module_details.append(module_name)
        
        if response.response == 'correct':
            subject_details[subject_name]['correct'] += 1
        elif response.response == 'incorrect':
            subject_details[subject_name]['incorrect'] += 1
        elif response.response == 'skipped':
            subject_details[subject_name]['skipped'] += 1    
        

    subject_details_flattened = []
    all_sections_totals = {
        'Total_Questions': 0,
        'Total_Attempted': 0,
        'Correct': 0,
        'Incorrect': 0,
        'Skipped': 0,
        'Score': 0,
        'Percentage': 0
    }

    for subject_name,details in subject_details.items():
        details['question_count'] = details['correct'] + details['incorrect'] + details['skipped']
        details['attempted'] = details['correct'] + details['incorrect']
        details['score'] = details['correct']
        if details['question_count'] > 0:
            details['percentage'] =  int((details['correct'] / details['question_count']) * 100)
        
        # all_sections_summary
        all_sections_totals['Total_Questions']+=details['question_count']
        all_sections_totals['Total_Attempted']+=details['attempted']
        all_sections_totals['Correct']+=details['correct']
        all_sections_totals['Incorrect']+=details['incorrect']
        all_sections_totals['Skipped']+=details['skipped']
        all_sections_totals['Score']+=details['score']
        
        subject_details_flattened.append(details)
    
    all_sections_totals['Percentage'] = int((all_sections_totals['Correct'] / all_sections_totals['Total_Questions']) * 100)
    
    return subject_details_flattened,module_details,all_sections_totals,

def dp_get_report_qa_details(attempt_id,subject='all',module='all',response_type='all'):
    base_query = """
    SELECT q_order,response,selected_option, correct_option, question_description, solution_explanation, answer_options, choice_type 
    FROM dailypractice.userresponse
    JOIN meta.question ON dailypractice.userresponse.q_id = meta.question.q_id
    JOIN meta.subject ON meta.subject.subject_id = meta.question.subject_id
    JOIN meta.module ON meta.module.module_id = meta.question.module_id
    WHERE attempt_id = :attempt_id
    """
    params = {"attempt_id": attempt_id}
    
    if subject != 'all':
        base_query += " AND subject_name = :subject"
        params.update({"subject": subject})
    if module != 'all':
        base_query += " AND module_name = :module"
        params.update({"module": module})
    if response_type != 'all':
        base_query += " AND response = :response_type"
        params.update({"response_type": response_type})
        
    base_query+= " order by q_order"

    query= text(base_query)
    solutions = db.session.execute(query, params).fetchall()
    return solutions

@application.route('/DailyPracticeReport', methods=['POST'])
def dpGenerateReport():
    attempt_id = request.form.get('attempt_id')
    attempt_details = dp_get_report_attempt_details(attempt_id)
    
    if attempt_details:
        attempt_id = attempt_details['attempt_id']
        date = attempt_details['date']
        student_id = attempt_details['student_id']
        
    student_name = f"{student.first_name} {student.last_name}" if (student := Student.query.filter_by(student_id=student_id).first()) else None
    responses = dp_get_report_responses(attempt_id)
    subjects,modules,all_sections= dp_get_report_table_details(responses)
    solutions = dp_get_report_qa_details(attempt_id)
    return render_template('DailyPracticeReport.html',
                           subjects=subjects, modules=modules, all_sections=all_sections,
                           solutions = solutions, student_id = student_id, student_name=student_name ,date=date, attempt_id=attempt_id)

@application.route('/dp_filter_report', methods=['POST'])
def dp_filter_report():    
    attempt_id = request.form.get('attempt_id')
    total_questions = request.form.get('total_questions')
    selected_subject = request.form.get('subjects')
    selected_module = request.form.get('modules')
    selected_responsetype = request.form.get('responsetype')
    # print(selected_subject)
    # print(selected_responsetype)
    filtered_solutions = dp_get_report_qa_details(attempt_id,subject=selected_subject,module=selected_module,response_type=selected_responsetype)

    return render_template('ReportSolution.html',
                           solutions = filtered_solutions, total_questions = total_questions)

# endregion

# region Exam Info

def get_exam_categories():
    query = text("""
    SELECT * 
    FROM competitiveexams.examcategory
    """)

    responses = db.session.execute(query).fetchall()
    return responses

@application.route('/ExamInfoDashboard')
@login_required
def examInfoDashboard():
    student_id = session['user_id'] 
    categories_data = get_exam_categories()
    year = 'all'  # Default year selection
    categories = 'all'  # Default category selection
    
    # Get distinct years from the exam table
    query_years = text("""
        SELECT DISTINCT year 
        FROM competitiveexams.exam 
        ORDER BY year DESC
    """)
    year_options = [row[0] for row in db.session.execute(query_years).fetchall()]

    # Fetch filtered exams for the student
    your_exams, other_exams = filter_exams_logic(student_id, year, categories)

    return render_template('ExamInfoDashboard.html', year_options=year_options, categories=categories_data,your_exams=your_exams,other_exams=other_exams)

# def filter_exams_logic(student_id, year, categories):
#     filters = []
#     params = {}

#     # Add year filter only if it's not 'all'
#     if year != 'all':
#         filters.append("year = :year")
#         try:
#             params['year'] = int(year)
#         except ValueError:
#             raise ValueError("Invalid year format")

#     # Add category filter only if it's not 'all'
#     if categories and categories != 'all':
#         category_ids = tuple(map(int, categories.split(',')))
#         filters.append("category_id IN :categories")
#         params['categories'] = category_ids

#     # Build base query with dynamic WHERE clause
#     base_query = "SELECT exam_id, exam_name FROM competitiveexams.exam"
#     if filters:
#         base_query += " WHERE " + " AND ".join(filters)

#     query_all_exams = text(base_query)

#     all_filtered_exams = {
#         row[0]: row[1]
#         for row in db.session.execute(query_all_exams, params).fetchall()
#     }

#     # Fetch student's exam interests
#     query_student_interests = text("""
#         SELECT exam_interests 
#         FROM registration."Student"
#         WHERE student_id = :student_id
#     """)
#     student_exam_interests = db.session.execute(
#         query_student_interests, {"student_id": student_id}
#     ).fetchone()

#     if student_exam_interests and student_exam_interests[0]:
#         student_exam_interests = set(student_exam_interests[0].split(','))
#     else:
#         student_exam_interests = set()

#     # Separate exams into 'your_exams' and 'other_exams' based on interest match
#     your_exams = {
#         exam_id: name for exam_id, name in all_filtered_exams.items()
#         if name in student_exam_interests
#     }
#     other_exams = {
#         exam_id: name for exam_id, name in all_filtered_exams.items()
#         if name not in student_exam_interests
#     }

#     return your_exams, other_exams

def filter_exams_logic(student_id, year, categories):
    filters = []
    params = {}

    # Add year filter
    if year != 'all':
        filters.append("e.year = :year")
        try:
            params['year'] = int(year)
        except ValueError:
            raise ValueError("Invalid year format")

    # Add category filter
    if categories and categories != 'all':
        category_ids = tuple(map(int, categories.split(',')))
        filters.append("e.category_id IN :categories")
        params['categories'] = category_ids

    # Base query with JOIN to examcategory
    base_query = """
        SELECT e.exam_id, e.exam_name, e.exam_description, c.category_name
        FROM competitiveexams.exam e
        JOIN competitiveexams.examcategory c ON e.category_id = c.category_id
    """
    if filters:
        base_query += " WHERE " + " AND ".join(filters)

    query_all_exams = text(base_query)

    # exam_id → {exam_name, exam_description, category_name}
    all_filtered_exams = {
        row[0]: {
            "exam_name": row[1],
            "exam_description": row[2],
            "category_name": row[3]
        }
        for row in db.session.execute(query_all_exams, params).fetchall()
    }

    # Get student's exam interests
    query_student_interests = text("""
        SELECT exam_interests 
        FROM registration."Student"
        WHERE student_id = :student_id
    """)
    student_exam_interests = db.session.execute(
        query_student_interests, {"student_id": student_id}
    ).fetchone()

    if student_exam_interests and student_exam_interests[0]:
        student_exam_interests = set(student_exam_interests[0].split(','))
    else:
        student_exam_interests = set()

    # Separate into your_exams and other_exams based on interest
    your_exams = {
        exam_id: data
        for exam_id, data in all_filtered_exams.items()
        if data["exam_name"] in student_exam_interests
    }

    other_exams = {
        exam_id: data
        for exam_id, data in all_filtered_exams.items()
        if data["exam_name"] not in student_exam_interests
    }

    return your_exams, other_exams

@application.route('/filter_exams', methods=['POST'])
def filter_exams():
    student_id = session['user_id']
    year = request.form.get('year')
    categories = request.form.get('categories')

    your_exams,other_exams = filter_exams_logic(student_id, year, categories)  
    
    return render_template('ExamFiltered.html', your_exams=your_exams,other_exams=other_exams)

def get_exam_details(exam_id):
    if not exam_id:
        return "Exam ID is required in the JSON payload", 400
    
    # Fetch exam details
    query_exam = text("""
        SELECT e.exam_name, ec.category_name, e.exam_description
        FROM competitiveexams.exam e
        JOIN competitiveexams.examcategory ec ON e.category_id = ec.category_id
        WHERE e.exam_id = :exam_id
    """)
    exam = db.session.execute(query_exam, {"exam_id": exam_id}).fetchone()

    if not exam:
        return "Exam not found", 404

    # Fetch exam pattern
    query_pattern = text("""
        SELECT subject, no_questions, marks, time_alloted
        FROM competitiveexams.exampattern
        WHERE exam_id = :exam_id
    """)
    exam_pattern = db.session.execute(query_pattern, {"exam_id": exam_id}).fetchall()

    # Fetch exam calendar
    query_calendar = text("""
        SELECT schedule_of_events, important_dates
        FROM competitiveexams.examcalendar
        WHERE exam_id = :exam_id
    """)
    exam_calendar = db.session.execute(query_calendar, {"exam_id": exam_id}).fetchall()
    
    #Fetch exam prepare details
    query_prepare = text("""
        SELECT mockdesc, dailydesc, customdesc, additionalinf
        FROM competitiveexams.examprepare
        WHERE exam_id = :exam_id
    """)
    exam_prepare = db.session.execute(query_prepare, {"exam_id": exam_id}).fetchall()    
    
    return exam,exam_pattern,exam_calendar,exam_prepare[0]

@application.route('/ExamDetails', methods=['POST'])
def exam_details():
    data = request.get_json()  # Get JSON payload from the request
    exam_id = data.get('exam_id') if data else None
    exam,exam_pattern,exam_calendar,exam_prepare=get_exam_details(exam_id)
    return render_template('ExamDetails.html', exam=exam, exam_pattern=exam_pattern, exam_calendar=exam_calendar,exam_prepare=exam_prepare)
#endregion

# region Profile

@application.route('/renewSubscription', methods=['POST'])
def renew_subscription():
    data = request.get_json()
    student_id = data.get('student_id')
    plan_id = data.get('plan_id')

    student = Student.query.filter_by(student_id=student_id).first()    
    
    # Get latest subscription
    subscription = (
        db.session.query(Subscription, PaymentPlanDetail)
        .join(PaymentPlanDetail, Subscription.plan_id == PaymentPlanDetail.plan_id)
        .filter(Subscription.student_id == student_id)
        .order_by(Subscription.end_date.desc())
        .first()
    )

    subscription_data = subscription[0] if subscription else None

    # Determine new start date
    if subscription_data:
        start_date = subscription_data.end_date
    else:
        start_date = datetime.utcnow().date()

    # Get plan duration
    plan = PaymentPlanDetail.query.filter_by(plan_id=plan_id).first()
    if not plan:
        return jsonify({'status': 'failed', 'reason': 'Invalid plan'}), 400

    # Calculate end date
    if plan.duration.days < 30:
        end_date = start_date + relativedelta(days=plan.duration.days)
    else:
        end_date = start_date + relativedelta(months=int(plan.duration.days / 30))

    # Insert new subscription
    new_subscription = Subscription(
        student_id=student_id,
        plan_id=plan_id,
        start_date=start_date,
        end_date=end_date,
        status=True
    )

    db.session.add(new_subscription)
    db.session.flush()
    student.last_subscription = new_subscription.subscription_id
    db.session.commit()

    return jsonify({'status': 'success'})

@application.route('/Profile')
@login_required
def profile():
    if 'user_id' not in session:
        return redirect('/login')

    student_id = session['user_id']
    user = Student.query.filter_by(student_id=student_id).first()
    if not user:
        return "User not found", 404

    institution_name = None
    if user.institution_id:
        institution = Institution.query.filter_by(institution_id=user.institution_id).first()
        institution_name = institution.institution_name if institution else "N/A"

    subscription = (
        db.session.query(Subscription, PaymentPlanDetail)
        .join(PaymentPlanDetail, Subscription.plan_id == PaymentPlanDetail.plan_id)
        .filter(Subscription.student_id == student_id)
        .order_by(Subscription.end_date.desc())
        .first()
    )

    subscription_data = subscription[0] if subscription else None
    plan_data = subscription[1] if subscription else None

    all_exams = Exam.query.with_entities(Exam.exam_name).all()
    all_subjects = Subject.query.with_entities(Subject.subject_name).all()
    exam_list = [exam[0] for exam in all_exams]
    subject_list = [subject[0] for subject in all_subjects]
    selected_exam_interests = user.exam_interests.split(", ") if user.exam_interests else []
    selected_subject_interests = user.subject_interests.split(", ") if user.subject_interests else []
    current_date = datetime.today().date()   
    profile_pic_url = get_profile_pic_url(student_id)
    last_subscription_id = user.last_subscription
    last_subscription = Subscription.query.filter_by(subscription_id=last_subscription_id).first()
    
    plans = [
    {'id': p.plan_id, 'name': p.plan_name, 'cost': p.cost}
    for p in db.session.query(PaymentPlanDetail).all()
    ]

    return render_template(
        'Profile.html',
        user=user,
        subscription=subscription_data,
        plan=plan_data,
        exam_list=exam_list,
        subject_list=subject_list,
        selected_exam_interests=selected_exam_interests,
        selected_subject_interests=selected_subject_interests,
        institution_name=institution_name,
        current_date=current_date,
        profile_pic_url=profile_pic_url,
        razorpaykey = application.config['RAZORPAY_ACCESS_KEY_ID'],
        plans=plans,
        last_subscription_date = last_subscription.end_date
    )

@application.route('/saveprofile', methods=['POST'])
def saveprofile():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "User not authenticated"}), 401

    student_id = session['user_id']
    user = Student.query.filter_by(student_id=student_id).first()

    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    try:
        data = request.json
        user.first_name = data.get("first_name", user.first_name)
        user.last_name = data.get("last_name", user.last_name)
        user.gender = data.get("gender", user.gender)
        user.dob = data.get("dob") if data.get("dob") else user.dob
        user.institution_id = int(data.get("institution_id", user.institution_id)) if data.get("institution_id") else user.institution_id
        user.contact_no = data.get("phone", user.contact_no)
        user.exam_interests = data.get("exam_interests", user.exam_interests)
        user.subject_interests = data.get("subject_interests", user.subject_interests)

        db.session.commit()
        return jsonify({"success": True, "message": "Profile updated successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@application.route('/uploadProfilePic', methods=['POST'])
def upload_profile_pic_dashboard():
    upload_profile_pic()    
    return redirect(url_for('profile'))

def upload_profile_pic():
    try:
        student_id = request.form['student_id']
        file = request.files['image']
        key = f"profile_pictures/{student_id}.jpg"
        s3.upload_fileobj(file, BUCKET_NAME, key)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@application.route('/deleteProfilePic/<student_id>', methods=['DELETE'])
def delete_profile_pic(student_id):
    try:
        key = f"profile_pictures/{student_id}.jpg"
        s3.delete_object(Bucket=BUCKET_NAME, Key=key)
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def get_profile_pic_url(student_id):
    key = f"profile_pictures/{student_id}.jpg"
    try:
        s3.head_object(Bucket=BUCKET_NAME, Key=key)
        return s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': key},
            ExpiresIn=3600
        )
    except:
        return None

# endregion

# region InstitutionRegistration

@application.route('/InstitutionRegistration')
def institutionregistration():    
    return render_template('InstitutionRegistration.html')

@application.route('/proceedInstitutionRegistration', methods=['POST'])
def proceed_institution_registration():
    institution_name = request.form['institution_name']
    phone_number = request.form['phone']
    email_id = request.form['email']
    password = request.form['password']

    if email_id not in verified_emails or not verified_emails[email_id]:
        return redirect(url_for('institutionregistration', message='Email not verified'))
    
    if phone_number not in verified_phoneNumbers or not verified_phoneNumbers[phone_number]:
        return redirect(url_for('institutionregistration', message='Phone Number not verified'))

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    new_login = InstitutionLogin(email=email_id, password=hashed_password)
    db.session.add(new_login)
    db.session.commit()
    
    current_utc_time = datetime.now(timezone.utc)
    today = current_utc_time.date()

    new_institution = Institution(
        institution_id =new_login.institution_id,
        institution_name =institution_name,
        enrolment_date =today,
        email=email_id,
        contact_no=phone_number,
        password=hashed_password
        # last_subscription = 
    )

    db.session.add(new_institution)
    db.session.commit()

    return redirect(url_for('loginPage'))
# endregion

# region InstitutionDashboard

@application.route('/InstitutionDashboard', methods=['GET', 'POST'])
def institutionDashboard():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('loginPage'))

    institution_id = session['user_id']
    institution = Institution.query.filter_by(institution_id=institution_id).first()

    if not institution:
        flash('Institution not found.', 'error')
        return redirect(url_for('loginPage'))

    student_ids = db.session.query(Student.student_id).filter_by(institution_id=institution_id).all()
    student_ids = [s[0] for s in student_ids]

    if not student_ids:
        return render_template('InstitutionDashboard.html',
                               mock_tests_total_count=0,
                               daily_practice_total_count=0,
                               custom_modules_total_count=0)

    id_tuple = tuple(student_ids)

    mock_tests_total_count,mock_avg = inst_mocktest_details(id_tuple)
    daily_practice_total_count,daily_avg = inst_daily_details(id_tuple)
    custom_module_total_count,custom_avg = inst_custom_details(id_tuple)

    retPieChartMockData = inst_mock_PieChartData(id_tuple)
    retPieChartDailyData = inst_daily_PieChartData(id_tuple)
    retPieChartCustomData = inst_custom_PieChartData(id_tuple)
    retBarChartData = inst_dash_BarChartData(id_tuple)
    
    # query_all_exams = text("""
    #         SELECT exam_id, exam_name 
    #         FROM competitiveexams.exam
    #     """)
    # all_filtered_exams = {row[0]: row[1] for row in db.session.execute(query_all_exams).fetchall()}
    
    all_filtered_exams = filter_exams_inst_logic(date.today().year, "all")
    
    top_students, low_students = inst_get_average_scores(id_tuple)

    return render_template('InstitutionDashboard.html',
                           mock_tests_total_count=mock_tests_total_count,
                           daily_practice_total_count=daily_practice_total_count,
                           custom_modules_total_count=custom_module_total_count,
                           mock_avg = mock_avg,
                           daily_avg= daily_avg,
                           custom_avg = custom_avg,
                           retPieChartMockData=retPieChartMockData.get_json(),
                           retPieChartDailyData=retPieChartDailyData.get_json(),
                           retPieChartCustomData=retPieChartCustomData.get_json(),
                           retBarChartData=retBarChartData.get_json(),
                           exams=all_filtered_exams,
                           top_students=top_students, 
                           low_students=low_students)

def inst_mocktest_details(id_tuple):
    # === MOCK TESTS ===
    mock_tests_attempts = db.session.execute(
        text("""
            SELECT attempt_id FROM mocktest.attempt
            WHERE student_id IN :ids AND resume_test = 'completed'
        """).bindparams(bindparam("ids", expanding=True)),
        {'ids': id_tuple}
    ).fetchall()

    mock_attempt_id_list = [row[0] for row in mock_tests_attempts]
    mock_tests_total_count = len(mock_attempt_id_list)

    if mock_tests_total_count:
        mock_correct_count = db.session.execute(
            text("""
                SELECT count(response) FROM mocktest.userresponse
                WHERE attempt_id IN :attempt_ids AND response = 'correct'
            """).bindparams(bindparam("attempt_ids", expanding=True)),
            {'attempt_ids': mock_attempt_id_list}
        ).scalar()

        mock_total_count = db.session.execute(
            text("""
                SELECT count(response) FROM mocktest.userresponse
                WHERE attempt_id IN :attempt_ids
            """).bindparams(bindparam("attempt_ids", expanding=True)),
            {'attempt_ids': mock_attempt_id_list}
        ).scalar()

        mock_avg = round(mock_correct_count / mock_total_count, 2) if mock_total_count else 0
    else:
        mock_avg = 0
    return mock_tests_total_count,mock_avg

def inst_daily_details(id_tuple):
    # === DAILY PRACTICE ===
    daily_practice_attempts = db.session.execute(
        text("""
            SELECT attempt_id FROM dailypractice.attempt
            WHERE student_id IN :ids AND resume_test = 'completed'
        """).bindparams(bindparam("ids", expanding=True)),
        {'ids': id_tuple}
    ).fetchall()

    daily_attempt_id_list = [row[0] for row in daily_practice_attempts]
    daily_practice_total_count = len(daily_attempt_id_list)

    if daily_practice_total_count:
        daily_correct_count = db.session.execute(
            text("""
                SELECT count(response) FROM dailypractice.userresponse
                WHERE attempt_id IN :attempt_ids AND response = 'correct'
            """).bindparams(bindparam("attempt_ids", expanding=True)),
            {'attempt_ids': daily_attempt_id_list}
        ).scalar()

        daily_total_count = db.session.execute(
            text("""
                SELECT count(response) FROM dailypractice.userresponse
                WHERE attempt_id IN :attempt_ids
            """).bindparams(bindparam("attempt_ids", expanding=True)),
            {'attempt_ids': daily_attempt_id_list}
        ).scalar()

        daily_avg = round(daily_correct_count / daily_total_count, 2) if daily_total_count else 0
    else:
        daily_avg = 0
    return daily_practice_total_count,daily_avg

def inst_custom_details(id_tuple):
     # === CUSTOM MODULES ===
    custom_module_attempts = db.session.execute(
        text("""
            SELECT attempt_id FROM custommodules.attempt
            WHERE student_id IN :ids AND resume_test = 'completed'
        """).bindparams(bindparam("ids", expanding=True)),
        {'ids': id_tuple}
    ).fetchall()

    custom_attempt_id_list = [row[0] for row in custom_module_attempts]
    custom_module_total_count = len(custom_attempt_id_list)

    if custom_module_total_count:
        custom_correct_count = db.session.execute(
            text("""
                SELECT count(response) FROM custommodules.userresponse
                WHERE attempt_id IN :attempt_ids AND response = 'correct'
            """).bindparams(bindparam("attempt_ids", expanding=True)),
            {'attempt_ids': custom_attempt_id_list}
        ).scalar()

        custom_total_count = db.session.execute(
            text("""
                SELECT count(response) FROM custommodules.userresponse
                WHERE attempt_id IN :attempt_ids
            """).bindparams(bindparam("attempt_ids", expanding=True)),
            {'attempt_ids': custom_attempt_id_list}
        ).scalar()

        custom_avg = round(custom_correct_count / custom_total_count, 2) if custom_total_count else 0
    else:
        custom_avg = 0
    return custom_module_total_count,custom_avg

def inst_mock_PieChartData(student_ids):
    query = text("""
        SELECT count(*), resume_test 
        FROM mocktest.attempt 
        WHERE student_id IN :ids 
        GROUP BY resume_test
    """)
    results = db.session.execute(query, {'ids': student_ids}).fetchall()

    labels, series = [], []
    mapping = {'completed': 'Completed', 'incomplete': 'Partially Completed'}
    for count, status in results:
        labels.append(mapping.get(status, status))
        series.append(count)

    return jsonify({"labels": labels, "series": series})

def inst_daily_PieChartData(student_ids):
    query = text("""
        SELECT 
        COUNT(*) AS count,
        CASE
            WHEN resume_test = 'incomplete' AND attempt.date > now() THEN 'lapsed'
            ELSE resume_test
        END AS status
        FROM dailypractice.attempt
        WHERE student_id IN :ids
        GROUP BY status
    """)
    results = db.session.execute(query, {'ids': student_ids}).fetchall()

    labels, series = [], []
    mapping = {'completed': 'Completed', 'incomplete': 'Partially Completed', 'lapsed': 'Lapsed'}
    for count, status in results:
        labels.append(mapping.get(status, status))
        series.append(count)

    return jsonify({"labels": labels, "series": series})

def inst_custom_PieChartData(student_ids):
    query = text("""
        SELECT count(*), resume_test 
        FROM custommodules.attempt 
        WHERE student_id IN :ids 
        GROUP BY resume_test
    """)
    results = db.session.execute(query, {'ids': student_ids}).fetchall()

    labels, series = [], []
    mapping = {'completed': 'Completed', 'incomplete': 'Partially Completed'}
    for count, status in results:
        labels.append(mapping.get(status, status))
        series.append(count)

    return jsonify({"labels": labels, "series": series})

def inst_BarChartData(table, student_ids):
    subquery = f"""
        SELECT attempt_id FROM {table}.attempt 
        WHERE student_id IN :ids
    """
    query = f"""
        SELECT meta.subject.subject_name,
               COUNT(CASE WHEN {table}.userresponse.response = 'correct' THEN 1 END) * 100.0 / COUNT(*) AS avg_score
        FROM {table}.userresponse
        JOIN meta.question ON {table}.userresponse.q_id = meta.question.q_id
        JOIN meta.subject ON meta.question.subject_id = meta.subject.subject_id
        WHERE {table}.userresponse.attempt_id IN ({subquery})
        GROUP BY meta.subject.subject_name
    """
    return db.session.execute(text(query), {'ids': student_ids}).fetchall()

def inst_dash_BarChartData(student_ids):
    all_scores = inst_BarChartData("mocktest", student_ids) + \
                 inst_BarChartData("dailypractice", student_ids) + \
                 inst_BarChartData("custommodules", student_ids)

    subject_scores = defaultdict(list)
    for subject, score in all_scores:
        subject_scores[subject].append(score)

    series_data = [{"x": subject, "y": sum(scores)/len(scores)} for subject, scores in subject_scores.items()]
    return jsonify({"series": [{"name": "Average Score by Subjects", "data": series_data}]})

def inst_get_average_scores(id_tuple):
    student_scores = []
    all_schemas = ['mocktest', 'dailypractice', 'custommodules']

    for student_id in id_tuple:
        attempts = {}
        averages = []

        # Step 1: Fetch attempt IDs from each schema
        for schema in all_schemas:
            query = text(f"SELECT attempt_id FROM {schema}.attempt WHERE student_id = :sid")
            result = db.session.execute(query, {'sid': student_id}).fetchall()
            attempts[schema] = [row[0] for row in result]

        # Step 2: Compute average score for each schema
        for schema in all_schemas:
            if attempts[schema]:
                placeholders = ','.join([f':id{i}' for i in range(len(attempts[schema]))])
                param_dict = {f'id{i}': val for i, val in enumerate(attempts[schema])}

                query = text(f"""
                    SELECT 
                        COUNT(*) FILTER (WHERE response = 'correct')::float / NULLIF(COUNT(*), 0) 
                    FROM {schema}.userresponse
                    WHERE attempt_id IN ({placeholders})
                """)
                accuracy = db.session.execute(query, param_dict).scalar()
                if accuracy is not None:
                    averages.append(accuracy * 100)  # Convert to percentage

        # Step 3: Compute final average (or 0.0 if no data)
        overall_avg = round(statistics.mean(averages), 2) if averages else 0.0

        # Step 4: Fetch name from registration."Student"
        name_query = text("""
            SELECT first_name, last_name FROM registration."Student"
            WHERE student_id = :sid
        """)
        name_result = db.session.execute(name_query, {'sid': student_id}).fetchone()
        firstname = name_result[0] if name_result else 'First'
        lastname = name_result[1] if name_result else 'Last'

        student_scores.append({
            'student_id': student_id,
            'firstname': firstname,
            'secondname': lastname,
            'avg': overall_avg
        })

    # Step 5: Sort all students by avg ascending (low to high)
    sorted_students = sorted(student_scores, key=lambda x: x['avg'])

    low_students = []
    top_students = []
    used_ids = set()

    # Fill bottom 5 first
    for student in sorted_students:
        if len(low_students) < 5:
            low_students.append(student)
            used_ids.add(student['student_id'])

    # Then fill top 5 without overlap
    for student in reversed(sorted_students):  # Highest avg first
        if len(top_students) < 5 and student['student_id'] not in used_ids:
            top_students.append(student)

    return top_students, low_students

# endregion

# region InstitutionExamInfo

@application.route('/ExamInfoInstitutionDashboard')
@login_required
def examInfoInstitutionDashboard():
    categories_data = get_exam_categories()
    year = 'all'  # Default year selection
    categories = 'all'  # Default category selection

    # Fetch filtered exams for the student
    exams = filter_exams_inst_logic(year, categories)
    
    # Get distinct years from the exam table
    query_years = text("""
        SELECT DISTINCT year 
        FROM competitiveexams.exam 
        ORDER BY year DESC
    """)
    year_options = [row[0] for row in db.session.execute(query_years).fetchall()]

    return render_template('ExamInfoInstitutionDashboard.html',year_options=year_options,categories=categories_data,exams=exams)

# def filter_exams_inst_logic(year, categories):
#     # Ensure categories are a valid list and avoid SQL injection risks
#     if not categories or categories == 'all':
#         query_all_exams = text("SELECT exam_id, exam_name FROM competitiveexams.exam")
#         all_filtered_exams = {row[0]: row[1] for row in db.session.execute(query_all_exams).fetchall()}
#     else:
#         query_all_exams = text("""
#             SELECT exam_id, exam_name 
#             FROM competitiveexams.exam 
#             WHERE category_id IN :categories
#         """)
#         all_filtered_exams = {row[0]: row[1] for row in db.session.execute(query_all_exams, {"categories": tuple(map(int, categories.split(',')))}).fetchall()}

#     return all_filtered_exams

def filter_exams_inst_logic(year, categories):
    filters = []
    params = {}

    # Add year filter
    if year != 'all':
        filters.append("e.year = :year")
        try:
            params['year'] = int(year)
        except ValueError:
            raise ValueError("Invalid year format")

    # Add category filter
    if categories and categories != 'all':
        category_ids = tuple(map(int, categories.split(',')))
        filters.append("e.category_id IN :categories")
        params['categories'] = category_ids

    # Base query with JOIN to examcategory
    base_query = """
        SELECT e.exam_id, e.exam_name, e.exam_description, c.category_name
        FROM competitiveexams.exam e
        JOIN competitiveexams.examcategory c ON e.category_id = c.category_id
    """
    if filters:
        base_query += " WHERE " + " AND ".join(filters)

    query_all_exams = text(base_query)

    # exam_id → {exam_name, exam_description, category_name}
    all_filtered_exams = {
        row[0]: {
            "exam_name": row[1],
            "exam_description": row[2],
            "category_name": row[3]
        }
        for row in db.session.execute(query_all_exams, params).fetchall()
    }

    return all_filtered_exams

@application.route('/filter_exams_inst', methods=['POST'])
def filter_exams_inst():
    year = request.form.get('year')
    categories = request.form.get('categories')

    exams = filter_exams_inst_logic(year, categories)  
    
    return render_template('ExamFilteredInstitution.html', exams=exams)

@application.route('/ExamInstitutionDetails', methods=['POST'])
def exam_institution_details():
    data = request.get_json()  # Get JSON payload from the request
    exam_id = data.get('exam_id') if data else None
    exam,exam_pattern,exam_calendar,exam_prepare=get_exam_details(exam_id)
    return render_template('ExamInstitutionDetails.html', exam=exam, exam_pattern=exam_pattern, exam_calendar=exam_calendar,exam_prepare=exam_prepare)

# endregion

# region InstitutionProfile

@application.route('/InstitutionProfile')
@login_required
def instprofile():
    # Ensure user is logged in
    if 'user_id' not in session:
        return redirect('/login')  # Redirect to login if not authenticated

    institution_id = session['user_id']

    # Fetch Institution details from database
    user = Institution.query.filter_by(institution_id=institution_id).first()

    if not user:
        return "Institution not found", 404  # Handle case where user doesn't exist
    
    # Fetch latest subscription details
    subscription = InstitutionSubscription.query.filter_by(institution_id=institution_id).first()
    inst_student_count = db.session.query(Student).filter_by(institution_id=institution_id).count()
    
    return render_template('InstitutionProfile.html', user=user,
        subscription=subscription,
        inst_student_count=inst_student_count)

@application.route('/saveinstprofile', methods=['POST'])
def saveinstprofile():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "User not authenticated"}), 401

    institution_id = session['user_id']
    user = Institution.query.filter_by(institution_id=institution_id).first()

    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    try:
        data = request.json
        user.institution_name = data.get("institution", user.institution_name)
        user.contact_no = data.get("phone", user.contact_no)
        user.address = data.get("address", user.address)

        db.session.commit()
        return jsonify({"success": True, "message": "Profile updated successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

# endregion

# region InstitutionPerformanceAnalysis

@application.route('/PerformanceAnalysis', methods=['GET', 'POST'])
def performanceAnalysis():
    institution_id = session['user_id']
    students = db.session.query(Student.student_id, Student.first_name, Student.last_name).filter_by(institution_id=institution_id).all()

    if not students:
        # print("students yet to be onboarded")
        return render_template('PerformanceAnalysis.html', students=[], student_name="")
    else: 
        # Default to the first student
        student_id = request.form.get('student_id') if request.method == 'POST' else students[0][0]   
        student = Student.query.filter_by(student_id=student_id).first()       
        #Mocktest
        average_accuracy, average_score = get_student_metrics(student_id=student_id)
        filtered_completed_attempts,filtered_incomplete_attempts = get_attempt_details(student_id=student_id)
        mocks_completed = sum(len(attempts) for attempts in filtered_completed_attempts.values())
        # Create a dictionary to store unique exam_id and exam_name
        unique_exams = {}

        # Add items from exam_attempt_details_completed
        for exam_id, attempts in filtered_completed_attempts.items():
            if exam_id not in unique_exams:
                unique_exams[exam_id] = attempts[0]['exam_name']

        # Add items from exam_attempt_details_incomplete
        for exam_id, attempts in filtered_incomplete_attempts.items():
            if exam_id not in unique_exams:
                unique_exams[exam_id] = attempts[0]['exam_name']
        student_name = f"{student.first_name} {student.last_name}"
        distinct_exams_count = len(unique_exams)
        session['exam_attempt_details'] = filtered_completed_attempts 
        
        #DailyPractice
        accuracy,average,attempt_ids,subjects,modules_attempted_count, modules  = get_dp_student_metrics(student_id=student_id)
        tests_completed,incomplete_tests,lapsed_tests = get_dp_attempt_details(student_id)
        all_subjects = getAllSubjects()
        all_modules = getAllModules()
        session['dp_attempt_ids'] = attempt_ids         
        
        difficulty_map = {
        1: "Beginner",
        2: "Intermediate",
        3: "Proficient",
        4: "Advanced",
        5: "Expert",
        }        
        
        #CustomModule
        custom_accuracy,custom_average,custom_attempt_ids,custom_subjects,custom_modules_attempted_count, custom_modules  = get_custom_student_metrics(student_id=student_id)
        custom_tests_completed,custom_incomplete_tests = get_custom_attempt_details(student_id)
        session['custommodule_attempt_ids'] = custom_attempt_ids
               
        return render_template('PerformanceAnalysis.html', 
                            students=students, selected_student_id = student_id,
                            mocks_completed=mocks_completed, average_accuracy=average_accuracy,
                            average_score=average_score,unique_exams=unique_exams,
                            exam_attempt_details_completed=filtered_completed_attempts,exam_attempt_details_incomplete=filtered_incomplete_attempts,
                            student_name=student_name,exams_targeted=distinct_exams_count,
                            dp_attempt_details_completed=tests_completed,dp_attempt_details_incomplete=incomplete_tests,dp_attempt_details_lapsed=lapsed_tests,
                            accuracy=accuracy,average=average, modules_attempted_count=modules_attempted_count, subjects=subjects, 
                            difficulty_map = difficulty_map, modules=modules, all_subjects= all_subjects,all_modules=all_modules,
                            custom_attempt_details_completed=custom_tests_completed,custom_attempt_details_incomplete=custom_incomplete_tests,
                            custom_accuracy=custom_accuracy,custom_average=custom_average, custom_modules_attempted_count=custom_modules_attempted_count, 
                            custom_subjects=custom_subjects, 
                            custom_modules=custom_modules)

@application.route('/pa_filter_mocktest', methods=['POST'])
def pa_filter_mocktest():
    student_id = request.form.get('student_id')
    status = request.form.get('status')
    exam_id = request.form.get('exam')
    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')
    difficulty = request.form.get('difficulty')

    filtered_completed_attempts,filtered_incomplete_attempts = filter_mocktest_logic(
        student_id, status, exam_id, from_date, to_date, difficulty
    )

    return render_template('PAMockAccordion.html', exam_attempt_details_completed=filtered_completed_attempts,exam_attempt_details_incomplete=filtered_incomplete_attempts)

@application.route('/pa_filter_dp', methods=['POST'])
def pa_filter_dp():
    student_id = request.form.get('student_id')
    status = request.form.get('status')
    subject_name = request.form.get('subject')
    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')
    difficulty = request.form.get('difficulty')

    filtered_completed_attempts,filtered_incomplete_attempts,filtered_lapsed_attempts = filter_dp_logic(
        student_id, status, subject_name, from_date, to_date, difficulty
    )
    
    difficulty_map = {
    1: "Beginner",
    2: "Intermediate",
    3: "Proficient",
    4: "Advanced",
    5: "Expert",
    }

    return render_template('PADailyAccordion.html', dp_attempt_details_completed=filtered_completed_attempts,dp_attempt_details_incomplete=filtered_incomplete_attempts,dp_attempt_details_lapsed=filtered_lapsed_attempts, difficulty_map = difficulty_map)

@application.route('/pa_filter_custommodule', methods=['POST'])
def pa_filter_custommodule():
    student_id = request.form.get('student_id')
    status = request.form.get('status')
    subject_name = request.form.get('subject')
    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')
    difficulty = request.form.get('difficulty')

    filtered_completed_attempts,filtered_incomplete_attempts = filter_custommodule_logic(
        student_id, status, subject_name, from_date, to_date, difficulty
    )
    
    difficulty_map = {
    1: "Beginner",
    2: "Intermediate",
    3: "Proficient",
    4: "Advanced",
    5: "Expert",
    }

    return render_template('PACustomAccordion.html', custom_attempt_details_completed=filtered_completed_attempts,custom_attempt_details_incomplete=filtered_incomplete_attempts, difficulty_map = difficulty_map)

# endregion

# region AdminDashboard
@application.route('/AdminDashboard', methods=['GET', 'POST'])
def adminDashboard():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('loginPage'))

    admin_id = session['user_id']
    admin = AdminLogin.query.filter_by(admin_id=admin_id).first()

    if not admin:
        flash('Admin not found.', 'error')
        return redirect(url_for('loginPage'))
    

    today = date.today()
    first_day_this_month = date(today.year, today.month, 1)
    last_day_this_month = date(today.year, today.month + 1, 1) - timedelta(days=1) if today.month < 12 else date(today.year, 12, 31)
    first_day_last_month = (first_day_this_month - timedelta(days=1)).replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    
    active_institutions = InstitutionSubscription.query.filter_by(status=True).count()
    inactive_institutions = InstitutionSubscription.query.filter_by(status=False).count()

    # last_month_active_institutions = InstitutionSubscription.query.filter(
    #     InstitutionSubscription.status == True,
    #     InstitutionSubscription.start_date <= last_day_last_month,
    #     InstitutionSubscription.end_date >= first_day_last_month
    # ).count()

    # last_month_inactive_institutions = InstitutionSubscription.query.filter(
    #     InstitutionSubscription.status == False,
    #     InstitutionSubscription.start_date <= last_day_last_month,
    #     InstitutionSubscription.end_date >= first_day_last_month
    # ).count()

    active_subscribers = Subscription.query.filter_by(status=True).count()
    inactive_subscribers = Subscription.query.filter_by(status=False).count()

    last_month_active_subscribers = Subscription.query.filter(
        Subscription.status == True,
        Subscription.start_date <= last_day_last_month,
        Subscription.end_date >= first_day_last_month
    ).count()
    
    last_month_inactive_subscribers = Subscription.query.filter(
        Subscription.status == True,
        Subscription.start_date <= last_day_last_month,
        Subscription.end_date >= first_day_last_month
    ).count()

    # upcoming_renewals = (
    #     Subscription.query.filter(Subscription.end_date <= last_day_this_month, Subscription.end_date >= first_day_last_month).count() +
    #     InstitutionSubscription.query.filter(InstitutionSubscription.end_date <= last_day_this_month, InstitutionSubscription.end_date >= first_day_last_month).count()
    # )

    upcoming_renewals = (
        Subscription.query.filter(Subscription.end_date <= last_day_this_month, Subscription.end_date >= first_day_last_month).count()
    )

    last_month_renewals = Subscription.query.filter(
        Subscription.end_date <= last_day_last_month,
        Subscription.end_date >= first_day_last_month
    ).count()

    return render_template(
        'AdminDashboard.html',
        active_institutions=active_institutions,
        inactive_institutions=inactive_institutions,
        active_subscribers=active_subscribers,
        inactive_subscribers=inactive_subscribers,
        upcoming_renewals=upcoming_renewals,
        delta_active_subscribers=active_subscribers-last_month_active_subscribers,
        delta_inactive_subscribers=inactive_subscribers-last_month_inactive_subscribers,
        delta_upcoming_renewals=upcoming_renewals-last_month_renewals
    )    

# Quarter, Month, Week enrollment count from Student + Institution
@application.route("/BarChartUsersQuarter")
def chart_users_quarter():
    return jsonify(fetch_users_enrollment("QUARTER"))

@application.route("/BarChartUsersMonth")
def chart_users_month():
    return jsonify(fetch_users_enrollment("MONTH"))

@application.route("/BarChartUsersWeek")
def chart_users_week():
    return jsonify(fetch_users_enrollment("WEEK"))

# def fetch_users_enrollment(granularity):
#     query = text(f"""
#         SELECT label, SUM(total) FROM (
#             SELECT EXTRACT({granularity} FROM enrolment_date) AS label, COUNT(*) AS total
#             FROM registration."Student"
#             WHERE EXTRACT(YEAR FROM enrolment_date) = EXTRACT(YEAR FROM CURRENT_DATE)
#             GROUP BY label
#             UNION ALL
#             SELECT EXTRACT({granularity} FROM enrolment_date) AS label, COUNT(*) AS total
#             FROM registration."Institution"
#             WHERE EXTRACT(YEAR FROM enrolment_date) = EXTRACT(YEAR FROM CURRENT_DATE)
#             GROUP BY label
#         ) AS combined
#         GROUP BY label ORDER BY label
#     """)
#     result = db.session.execute(query).fetchall()
#     data = [{"x": f"{granularity.title()} {int(r[0])}", "y": r[1]} for r in result]
#     return {"series": [{"name": "New Enrollments", "data": data}]}

def fetch_users_enrollment(granularity):
    query = text(f"""
        SELECT EXTRACT({granularity} FROM enrolment_date) AS label, COUNT(*) AS total
        FROM registration."Student"
        WHERE EXTRACT(YEAR FROM enrolment_date) = EXTRACT(YEAR FROM CURRENT_DATE)
        GROUP BY label
        ORDER BY label
    """)
    result = db.session.execute(query).fetchall()
    data = [{"x": f"{granularity.title()} {int(r[0])}", "y": r[1]} for r in result]
    return {"series": [{"name": "New Enrollments", "data": data}]}

# Billing from Student + Institution Subscription
@application.route("/BarChartBillingsQuarter")
def chart_billings_q():
    return jsonify(fetch_combined_billing("QUARTER"))

@application.route("/BarChartBillingsMonth")
def chart_billings_m():
    return jsonify(fetch_combined_billing("MONTH"))

@application.route("/BarChartBillingsWeek")
def chart_billings_w():
    return jsonify(fetch_combined_billing("WEEK"))

# def fetch_combined_billing(granularity):
#     query = text(f"""
#         SELECT label, SUM(total) FROM (
#             SELECT EXTRACT({granularity} FROM sub.end_date) AS label, COALESCE(SUM(p.cost), 0) AS total
#             FROM registration.subscription sub
#             LEFT JOIN paymentplans.paymentplandetails p ON p.plan_id = sub.plan_id
#             WHERE EXTRACT(YEAR FROM sub.end_date) = EXTRACT(YEAR FROM CURRENT_DATE)
#             GROUP BY label

#             UNION ALL

#             SELECT EXTRACT({granularity} FROM sub.end_date) AS label, COALESCE(SUM(p.cost), 0) AS total
#             FROM registration."InstitutionSubscription" sub
#             LEFT JOIN paymentplans.paymentplandetails p ON p.plan_id = sub.plan_id
#             WHERE EXTRACT(YEAR FROM sub.end_date) = EXTRACT(YEAR FROM CURRENT_DATE)
#             GROUP BY label
#         ) AS combined
#         GROUP BY label ORDER BY label
#     """)
#     result = db.session.execute(query).fetchall()
#     data = [{"x": f"{granularity.title()} {int(r[0])}", "y": r[1]} for r in result]
#     return {"series": [{"name": "Total Billing", "data": data}]}

def fetch_combined_billing(granularity):
    query = text(f"""
        SELECT EXTRACT({granularity} FROM sub.end_date) AS label, COALESCE(SUM(p.cost), 0) AS total
        FROM registration.subscription sub
        LEFT JOIN paymentplans.paymentplandetails p ON p.plan_id = sub.plan_id
        WHERE EXTRACT(YEAR FROM sub.end_date) = EXTRACT(YEAR FROM CURRENT_DATE)
        GROUP BY label
        ORDER BY label
    """)
    result = db.session.execute(query).fetchall()
    data = [{"x": f"{granularity.title()} {int(r[0])}", "y": r[1]} for r in result]
    return {"series": [{"name": "Total Billing", "data": data}]}

@application.route("/BarChartRevenueQuarter")
def chart_revenue_q():
    return jsonify(fetch_combined_revenue("QUARTER"))

@application.route("/BarChartRevenueMonth")
def chart_revenue_m():
    return jsonify(fetch_combined_revenue("MONTH"))

@application.route("/BarChartRevenueWeek")
def chart_revenue_w():
    return jsonify(fetch_combined_revenue("WEEK"))

# def fetch_combined_revenue(granularity):
#     query = text(f"""
#         SELECT label, SUM(total) FROM (
#             SELECT EXTRACT({granularity} FROM sub.start_date) AS label, COALESCE(SUM(p.cost), 0) AS total
#             FROM registration.subscription sub
#             LEFT JOIN paymentplans.paymentplandetails p ON p.plan_id = sub.plan_id
#             WHERE EXTRACT(YEAR FROM sub.start_date) = EXTRACT(YEAR FROM CURRENT_DATE)
#             GROUP BY label

#             UNION ALL

#             SELECT EXTRACT({granularity} FROM sub.start_date) AS label, COALESCE(SUM(p.cost), 0) AS total
#             FROM registration."InstitutionSubscription" sub
#             LEFT JOIN paymentplans.paymentplandetails p ON p.plan_id = sub.plan_id
#             WHERE EXTRACT(YEAR FROM sub.start_date) = EXTRACT(YEAR FROM CURRENT_DATE)
#             GROUP BY label
#         ) AS combined
#         GROUP BY label ORDER BY label
#     """)
#     result = db.session.execute(query).fetchall()
#     data = [{"x": f"{granularity.title()} {int(r[0])}", "y": r[1]} for r in result]
#     return {"series": [{"name": "Total Revenue", "data": data}]}

def fetch_combined_revenue(granularity):
    query = text(f"""
        SELECT EXTRACT({granularity} FROM sub.start_date) AS label, COALESCE(SUM(p.cost), 0) AS total
        FROM registration.subscription sub
        LEFT JOIN paymentplans.paymentplandetails p ON p.plan_id = sub.plan_id
        WHERE EXTRACT(YEAR FROM sub.start_date) = EXTRACT(YEAR FROM CURRENT_DATE)
        GROUP BY label
        ORDER BY label
    """)
    result = db.session.execute(query).fetchall()
    data = [{"x": f"{granularity.title()} {int(r[0])}", "y": r[1]} for r in result]
    return {"series": [{"name": "Total Revenue", "data": data}]}

# Pie Chart for Tests
@application.route("/PieChartTests")
def pie_chart_tests():
    queries = {
        "Mock Test": "SELECT COUNT(*) FROM mocktest.attempt",
        "Daily Practice": "SELECT COUNT(*) FROM dailypractice.attempt",
        "Custom Module": "SELECT COUNT(*) FROM custommodules.attempt"
    }
    labels = list(queries.keys())
    series = [db.session.execute(text(q)).scalar() for q in queries.values()]
    return jsonify({"labels": labels, "series": series})

@application.route("/PieChartUsers")
def pie_chart_users():
    queries = {
        "Mock Test": "SELECT COUNT(DISTINCT student_id) FROM mocktest.attempt",
        "Daily Practice": "SELECT COUNT(DISTINCT student_id) FROM dailypractice.attempt",
        "Custom Module": "SELECT COUNT(DISTINCT student_id) FROM custommodules.attempt"
    }
    labels = list(queries.keys())
    series = [db.session.execute(text(q)).scalar() for q in queries.values()]
    return jsonify({"labels": labels, "series": series})

# endregion

# region AdminSubscribers

@application.route('/AdminSubscriberList', methods=['GET', 'POST'])
def adminSubscriberList():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('loginPage'))

    admin_id = session['user_id']
    admin = AdminLogin.query.filter_by(admin_id=admin_id).first()
    if not admin:
        flash('Admin not found.', 'error')
        return redirect(url_for('loginPage'))

    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Filters
    search_name = request.args.get('search_name', '')
    search_institution = request.args.get('search_institution', '')
    selected_plan = request.args.get('plan', '')
    selected_status = request.args.get('status', '')
    enrol_from = request.args.get('enrol_from', '')
    enrol_to = request.args.get('enrol_to', '')
    today = datetime.today().date()

    query = (
    db.session.query(Student, Institution, Subscription, PaymentPlanDetail)
    .outerjoin(Institution, Student.institution_id == Institution.institution_id)
    .outerjoin(Subscription, Student.student_id == Subscription.student_id)
    .outerjoin(PaymentPlanDetail, Subscription.plan_id == PaymentPlanDetail.plan_id)
    .filter(Subscription.subscription_id == Student.last_subscription)
    .order_by(Student.student_id.desc())
    )

    if search_name:
        query = query.filter(Student.student_id == int(search_name))

    if search_institution:
        query = query.filter(Student.institution_id == int(search_institution))

    if selected_plan:
        query = query.filter(PaymentPlanDetail.plan_name == selected_plan)

    if selected_status:
        if selected_status == 'Active':
            query = query.filter(
                Subscription.status == True,
                or_(
                    Subscription.end_date >= today,
                    Subscription.end_date.is_(None)
                )
            )
        elif selected_status == 'Inactive':
            query = query.filter(
                or_(
                    Subscription.status == False,
                    and_(
                        Subscription.status == True,
                        Subscription.end_date.isnot(None),
                        Subscription.end_date < today
                    )
                )
            )

    if enrol_from:
        try:
            date_from = datetime.strptime(enrol_from, "%Y-%m-%d").date()
            query = query.filter(Subscription.start_date >= date_from)
        except:
            pass

    if enrol_to:
        try:
            date_to = datetime.strptime(enrol_to, "%Y-%m-%d").date()
            query = query.filter(Subscription.start_date <= date_to)
        except:
            pass

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    student_list = []
    for student, institution, subscription, plan in pagination.items:
        student_list.append({
            'student_id': student.student_id,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'institution_id': institution.institution_name if institution else 'N/A',
            'dob': student.dob,
            'plan': plan.plan_name if plan else 'N/A',
            'valid_until': subscription.end_date.strftime('%d/%m/%Y') if subscription and subscription.end_date else 'N/A',
            'status': 'Active' if subscription.status and (subscription.end_date is None or subscription.end_date >= today) else 'Inactive'
        })

    # Dropdown values
    plan_options = [p[0] for p in db.session.query(PaymentPlanDetail.plan_name).distinct()]
    subscribers = db.session.query(Student.student_id, Student.first_name, Student.last_name).all()
    institutions = db.session.query(Institution.institution_id, Institution.institution_name).all()
    
    BLOCK_SIZE = 10
    block_start = ((pagination.page - 1) // BLOCK_SIZE) * BLOCK_SIZE + 1
    block_end = min(block_start + BLOCK_SIZE - 1, pagination.pages)

    return render_template('AdminSubscriberList.html',
        students=student_list,
        page=page,
        total_pages=pagination.pages,
        has_prev=pagination.has_prev,
        has_next=pagination.has_next,
        prev_num=max(1, pagination.page - BLOCK_SIZE),
        next_num=min(pagination.pages, pagination.page + BLOCK_SIZE),
        block_start=block_start,
        block_end=block_end,
        plan_options=plan_options,
        subscribers=[{"id": s[0], "name": f"{s[1]} {s[2]}"} for s in subscribers],
        institutions=[{"id": i[0], "name": i[1]} for i in institutions],
        current_filters={
            'search_name': search_name,
            'search_institution': search_institution,
            'plan': selected_plan,
            'status': selected_status,
            'enrol_from': enrol_from,
            'enrol_to': enrol_to
        }
    )
    
@application.route('/AdminSubscriberPartial')
def adminSubscriberPartial():
    if 'user_id' not in session:
        return redirect(url_for('loginPage'))

    # Use the same filtering and pagination logic as in adminSubscriberList
    page = request.args.get('page', 1, type=int)
    per_page = 50

    search_name = request.args.get('search_name', '')
    search_institution = request.args.get('search_institution', '')
    selected_plan = request.args.get('plan', '')
    selected_status = request.args.get('status', '')
    enrol_from = request.args.get('enrol_from', '')
    enrol_to = request.args.get('enrol_to', '')
    today = datetime.today().date()

    query = (
    db.session.query(Student, Institution, Subscription, PaymentPlanDetail)
    .outerjoin(Institution, Student.institution_id == Institution.institution_id)
    .outerjoin(Subscription, Student.student_id == Subscription.student_id)
    .outerjoin(PaymentPlanDetail, Subscription.plan_id == PaymentPlanDetail.plan_id)
    .filter(Subscription.subscription_id == Student.last_subscription)
    )

    if search_name:
        query = query.filter(Student.student_id == int(search_name))
    if search_institution:
        query = query.filter(Student.institution_id == int(search_institution))
    if selected_plan:
        query = query.filter(PaymentPlanDetail.plan_name == selected_plan)
    if selected_status:
        if selected_status == 'Active':
            query = query.filter(
                Subscription.status == True,
                or_(
                    Subscription.end_date >= today,
                    Subscription.end_date.is_(None)
                )
            )
        elif selected_status == 'Inactive':
            query = query.filter(
                or_(
                    Subscription.status == False,
                    and_(
                        Subscription.status == True,
                        Subscription.end_date.isnot(None),
                        Subscription.end_date < today
                    )
                )
            )
    if enrol_from:
        date_from = datetime.strptime(enrol_from, "%Y-%m-%d").date()
        query = query.filter(Subscription.start_date >= date_from)
    if enrol_to:
        date_to = datetime.strptime(enrol_to, "%Y-%m-%d").date()
        query = query.filter(Subscription.start_date <= date_to)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    student_list = []
    for student, institution, subscription, plan in pagination.items:
        student_list.append({
            'student_id': student.student_id,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'institution_id': institution.institution_name if institution else 'N/A',
            'dob': student.dob,
            'plan': plan.plan_name if plan else 'N/A',
            'valid_until': subscription.end_date.strftime('%d/%m/%Y') if subscription and subscription.end_date else 'N/A',
            'status': 'Active' if subscription.status and (subscription.end_date is None or subscription.end_date >= today) else 'Inactive'
        })            
    
    BLOCK_SIZE = 10
    block_start = ((pagination.page - 1) // BLOCK_SIZE) * BLOCK_SIZE + 1
    block_end = min(block_start + BLOCK_SIZE - 1, pagination.pages)    

    return render_template('AdminSubscriberPartial.html',
                           students=student_list,
                           page=page,
                           total_pages=pagination.pages,
                           has_next=pagination.has_next,
                           has_prev=pagination.has_prev,
                           next_num=min(pagination.pages, pagination.page + BLOCK_SIZE),
                           prev_num=max(1, pagination.page - BLOCK_SIZE),
                            block_start=block_start,
                            block_end=block_end)

@application.route('/uploadProfilePicEditSubscriber', methods=['POST'])
def upload_profile_pic_editsubscriber():
    student_id = request.form.get('student_id')
    upload_profile_pic()
    return redirect(url_for('adminEditSubscriber', student_id=student_id))

@application.route('/AdminEditSubscriber', methods=['GET'])
def adminEditSubscriber():
    student_id = request.args.get('student_id', type=int)
    if not student_id:
        return "Missing student_id", 400

    student = Student.query.get_or_404(student_id)
    # institution_names = db.session.query(Institution.institution_id, Institution.institution_name).all()
    institution_name = db.session.query(Institution.institution_name).filter_by(institution_id=student.institution_id).scalar()
    plan_options = [
    {'id': p.plan_id, 'name': p.plan_name, 'cost': p.cost}
    for p in db.session.query(PaymentPlanDetail).all()
    ]
    subscription = (
    db.session.query(Subscription, PaymentPlanDetail.plan_name)
    .outerjoin(PaymentPlanDetail, Subscription.plan_id == PaymentPlanDetail.plan_id)
    .filter(Subscription.subscription_id == student.last_subscription)
    .first()
    )

    subscription_data = subscription[0] if subscription else None
    current_plan_name = subscription[1] if subscription else None
    
    today = datetime.today().date()
    subscription_status = 'Active' if subscription_data.status and (subscription_data.end_date is None or subscription_data.end_date >= today) else 'Inactive'  
    profile_pic_url = get_profile_pic_url(student_id)

    return render_template(
        'AdminEditSubscriber.html',
        student=student,
        subscription=subscription_data,
        current_plan=current_plan_name,
        subscription_status=subscription_status,
        institution_name=institution_name,
        plan_options=plan_options,
        profile_pic_url=profile_pic_url
    )

@application.route('/getSubscriber', methods=['GET'])
def getSubscriber():
    student_id = request.args.get('student_id', type=int)
    student = Student.query.get(student_id)
    subscription = Subscription.query.filter_by(student_id=student_id).first()
    if student and subscription:
        return jsonify({
            'student_id': student.student_id,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'institution_id': student.institution_id
        })
    return jsonify({'success': False, 'message': 'Subscriber not found'})

@application.route('/updateSubscriber', methods=['POST'])
def updateSubscriber():
    data = request.get_json()
    student_id = data.get('student_id')
    subscription_id = data.get('subscription_id')

    student = Student.query.get(student_id)
    subscription = Subscription.query.filter_by(subscription_id=subscription_id).first()

    if student and subscription:
        # Update only if values have changed
        if data.get('first_name') != student.first_name:
            student.first_name = data.get('first_name')

        if data.get('last_name') != student.last_name:
            student.last_name = data.get('last_name')

        new_dob = datetime.strptime(data.get('dob'), '%Y-%m-%d').date()
        if new_dob != student.dob:
            student.dob = new_dob

        # new_institution_id = int(data.get('institution_id'))
        # if new_institution_id != student.institution_id:
        #     student.institution_id = new_institution_id

        if data.get('contact_no') != student.contact_no:
            student.contact_no = data.get('contact_no')

        if data.get('gender') != student.gender:
            student.gender = data.get('gender')

        new_status = bool(int(data.get('status')))
        if new_status != subscription.status:
            subscription.status = new_status

        if data.get('plan') and data.get('plan') != 'None':
            new_plan_id = int(data.get('plan'))
            if new_plan_id != subscription.plan_id:
                plan = PaymentPlanDetail.query.get(new_plan_id)
                if plan:
                    subscription.plan_id = new_plan_id                    
                    if plan.duration.days < 30:
                        subscription.end_date = subscription.start_date + relativedelta(days=plan.duration.days)
                    else:
                        subscription.end_date = subscription.start_date + relativedelta(months=int(plan.duration.days / 30))

        db.session.commit()
        return jsonify({'success': True})

    return jsonify({'success': False, 'message': 'Update failed'})

@application.route('/deleteSubscriber', methods=['POST'])
def deleteSubscriber():
    data = request.get_json()
    student_id = data.get('student_id')
    student = Student.query.get(student_id)

    if student:        
        # --- CUSTOM MODULES ---
        cm_attempt_ids = [a.attempt_id for a in CustomModuleAttempt.query.filter_by(student_id=student_id).all()]
        if cm_attempt_ids:
            CustomModuleUserResponse.query.filter(CustomModuleUserResponse.attempt_id.in_(cm_attempt_ids)).delete(synchronize_session=False)
            CustomModuleConfig.query.filter_by(student_id=student_id).delete(synchronize_session=False)
            CustomModuleAttempt.query.filter_by(student_id=student_id).delete(synchronize_session=False)

        # --- DAILY PRACTICE ---
        dp_attempt_ids = [a.attempt_id for a in DailyPracticeAttempt.query.filter_by(student_id=student_id).all()]
        if dp_attempt_ids:
            DailyPracticeUserResponse.query.filter(DailyPracticeUserResponse.attempt_id.in_(dp_attempt_ids)).delete(synchronize_session=False)
            DailyPracticeConfig.query.filter_by(student_id=student_id).delete(synchronize_session=False)
            DailyPracticeAttempt.query.filter_by(student_id=student_id).delete(synchronize_session=False)

        # --- MOCK TEST ---
        mt_attempt_ids = [a.attempt_id for a in MockTestAttempt.query.filter_by(student_id=student_id).all()]
        if mt_attempt_ids:
            UserResponse.query.filter(UserResponse.attempt_id.in_(mt_attempt_ids)).delete(synchronize_session=False)
            MockTestAttempt.query.filter_by(student_id=student_id).delete(synchronize_session=False)
        
        # --- SUBSCRIPTIONS ---
        student.last_subscription = None  # replace with actual FK column if different
        db.session.commit()
        
        Subscription.query.filter_by(student_id=student_id).delete()

        # Delete student record (which depends on Login)
        db.session.delete(student)
        db.session.flush()  # Ensure deletion is staged before Login

        # Now safely delete login
        Login.query.filter_by(student_id=student_id).delete()

        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Subscriber not found'})
 
@application.route('/exportSubscribers')
def exportSubscribers():
    # Filters
    search_name = request.args.get('search_name', '')
    search_institution = request.args.get('search_institution', '')
    selected_plan = request.args.get('plan', '')
    selected_status = request.args.get('status', '')
    enrol_from = request.args.get('enrol_from', '')
    enrol_to = request.args.get('enrol_to', '')
    today = date.today()

    # # Subquery to get the latest subscription per student
    # latest_subq = (
    #     db.session.query(
    #         Subscription.student_id.label("student_id"),
    #         db.func.max(Subscription.subscription_id).label("max_sub_id")
    #     )
    #     .group_by(Subscription.student_id)
    #     .subquery()
    # )

    # # Alias Subscription table to join correctly
    # Sub = aliased(Subscription)

    # # Main query
    # query = (
    #     db.session.query(Student, Institution, Sub, PaymentPlanDetail)
    #     .outerjoin(Institution, Student.institution_id == Institution.institution_id)
    #     .join(latest_subq, Student.student_id == latest_subq.c.student_id)
    #     .join(Sub, Sub.subscription_id == latest_subq.c.max_sub_id)
    #     .outerjoin(PaymentPlanDetail, Sub.plan_id == PaymentPlanDetail.plan_id)
    # )

    query = (
        db.session.query(Student, Institution, Subscription, PaymentPlanDetail)
        .outerjoin(Institution, Student.institution_id == Institution.institution_id)
        .join(Subscription, Student.student_id == Subscription.student_id)
        .outerjoin(PaymentPlanDetail, Subscription.plan_id == PaymentPlanDetail.plan_id)
    )

    # Apply filters
    if search_name:
        query = query.filter(Student.student_id == int(search_name))

    if search_institution:
        query = query.filter(Student.institution_id == int(search_institution))

    if selected_plan:
        query = query.filter(PaymentPlanDetail.plan_name == selected_plan)

    if selected_status:
        if selected_status == 'Active':
            query = query.filter(
                Subscription.status == True,
                or_(
                    Subscription.end_date >= today,
                    Subscription.end_date.is_(None)
                )
            )
        elif selected_status == 'Inactive':
            query = query.filter(
                or_(
                    Subscription.status == False,
                    and_(
                        Subscription.status == True,
                        Subscription.end_date.isnot(None),
                        Subscription.end_date < today
                    )
                )
            )

    if enrol_from:
        try:
            date_from = datetime.strptime(enrol_from, "%Y-%m-%d").date()
            query = query.filter(Subscription.start_date >= date_from)
        except ValueError:
            pass

    if enrol_to:
        try:
            date_to = datetime.strptime(enrol_to, "%Y-%m-%d").date()
            query = query.filter(Subscription.start_date <= date_to)
        except ValueError:
            pass

    results = query.all()

    # Prepare data for Excel
    data = []
    for student, institution, subscription, plan in results:
        data.append({
            'ID': student.student_id,
            'Subscriber Name': f"{student.first_name} {student.last_name}",
            'Institution Name': institution.institution_name if institution else 'N/A',
            'Enrolment Date': student.dob.strftime('%d/%m/%Y') if student.dob else '',
            'Plan': plan.plan_name if plan else 'N/A',
            'Valid Until': subscription.end_date.strftime('%d/%m/%Y') if subscription and subscription.end_date else 'N/A',
            'Status': 'Active' if subscription and (subscription.end_date is None or subscription.end_date >= today) else 'Inactive'
        })

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Subscribers')

    output.seek(0)
    return send_file(output, download_name="Subscribers.xlsx", as_attachment=True)
 
# endregion

# region AdminInstitutions

def get_institution_results(request):
    page = int(request.args.get("page", 1))
    per_page = 50

    # Filters from request
    search_institution = request.args.get("search_institution", "")
    no_of_students = request.args.get("no_of_students", "")
    status_filter = request.args.get("status", "")
    enrol_from = request.args.get('enrol_from', '')
    enrol_to = request.args.get('enrol_to', '')

    # Base query
    query = db.session.query(Institution, InstitutionSubscription).join(InstitutionSubscription, Institution.institution_id == InstitutionSubscription.institution_id)

    # Apply filters
    if search_institution:
        query = query.filter(Institution.institution_id == int(search_institution))
    if no_of_students:
        if no_of_students == "1-10":
            query = query.filter(Institution.no_of_students.between(1, 10))
        elif no_of_students == "11-50":
            query = query.filter(Institution.no_of_students.between(11, 50))
        elif no_of_students == "51+":
            query = query.filter(Institution.no_of_students > 50)
    if status_filter:
        query = query.filter(InstitutionSubscription.status == (status_filter == "Active")) 
        
    if enrol_from:
        date_from = datetime.strptime(enrol_from, "%Y-%m-%d").date()
        query = query.filter(Institution.enrolment_date >= date_from)
    if enrol_to:
        date_to = datetime.strptime(enrol_to, "%Y-%m-%d").date()
        query = query.filter(Institution.enrolment_date <= date_to)   

    # Pagination
    pagination = query.order_by(Institution.institution_id).paginate(page=page, per_page=per_page, error_out=False)

    # Result list
    institution_list = []
    for inst, sub in pagination.items:
        institution_list.append(({
            'id': inst.institution_id,
            'name': inst.institution_name,
            'status': "Active" if sub.status else "Inactive",
            'created_on': inst.enrolment_date
        }, inst.no_of_students))
    
    BLOCK_SIZE = 10
    block_start = ((pagination.page - 1) // BLOCK_SIZE) * BLOCK_SIZE + 1
    block_end = min(block_start + BLOCK_SIZE - 1, pagination.pages)
    
    return {
        "institutions": institution_list,
        "page": pagination.page,
        "total_pages": pagination.pages,
        "prev_num": max(1, pagination.page - BLOCK_SIZE),
        "next_num": min(pagination.pages, pagination.page + BLOCK_SIZE),
        "has_prev": pagination.has_prev,
        "has_next": pagination.has_next,
        "block_start": block_start,
        "block_end": block_end
    }

@application.route("/AdminInstitutionList")
def adminInstitutionList():
    institution_names = Institution.query.with_entities(
        Institution.institution_id.label('id'),
        Institution.institution_name.label('name')
    ).all()
    plan_options = [p.plan_name for p in PaymentPlanDetail.query.all()]

    result = get_institution_results(request)

    return render_template("AdminInstitutionList.html",
                           institution_names=institution_names,
                           plan_options=plan_options,
                           current_filters={
                               'search_institution': request.args.get('search_institution', ''),
                               'plan': request.args.get('plan', ''),
                               'no_of_students': request.args.get('no_of_students', ''),
                               'status': request.args.get('status', ''),
                               'enrol_from': request.args.get('enrol_from', ''),
                               'enrol_to': request.args.get('enrol_to', '')
                           },
                           **result)

@application.route("/AdminInstitutionPartial")
def adminInstitutionPartial():
    result = get_institution_results(request)
    return render_template("AdminInstitutionPartial.html", **result) 

def is_valid_phone(phone):
    return re.fullmatch(r'[6-9][0-9]{9}', phone) is not None

# def is_valid_email(email):
#     return re.fullmatch(r'[a-zA-Z0-9._%+-]+@(gmail\.com|outlook\.com)', email) is not None

def is_valid_email(email):
    return re.fullmatch(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', email) is not None

@application.route('/addInstitution', methods=["GET", "POST"])
def addInstitution():
    if request.method == "POST":
        try:
            name = request.form.get('name')
            contact_no = request.form.get('contact_no')
            email = request.form.get('email')
            no_of_students = int(request.form.get('no_of_students', 0))
            address = request.form.get('address')
            description = request.form.get('description')
            # plan_id = int(request.form.get('plan'))
            is_active = request.form.get('status') == 'true'
            file = request.files.get('file')

            # Validate formats
            if not is_valid_phone(contact_no):
                return jsonify({'success': False, 'message': 'Phone number must start with 6-9 and be 10 digits long'}), 400
            if not is_valid_email(email):
                return jsonify({'success': False, 'message': 'Email must end with @gmail.com or @outlook.com'}), 400

            # Duplicate check
            if Login.query.filter_by(email=email).first() or Institution.query.filter_by(email=email).first():
                return jsonify({'success': False, 'message': 'Email already registered'}), 400
            phone_check = check_phone_internal(contact_no)
            if not phone_check['success']:
                return jsonify(phone_check), 400
            
            hashed_password = generate_password_hash("helloinstitutionadmin", method='pbkdf2:sha256')

            institutionLogin = InstitutionLogin(email=email, password=hashed_password)
            db.session.add(institutionLogin)
            db.session.flush()
            
            # Create institution
            institution = Institution(
                institution_id = institutionLogin.institution_id,
                institution_name=name,
                no_of_students=no_of_students,
                contact_no=contact_no,
                email=email,
                address=address,
                description=description,
                password=hashed_password,
                enrolment_date=datetime.today()
            )
            db.session.add(institution)
            db.session.flush()  # to get institution_id
            
            # plan = PaymentPlanDetail.query.get(plan_id)
            # if not plan:
            #     return jsonify({'success': False, 'message': 'Selected plan not found'}), 400
            
            # Create subscription
            subscription = InstitutionSubscription(
                institution_id=institution.institution_id,
                status=is_active
            )
            
            db.session.add(subscription)

            skipped_students = []
            if file:
                # result = importStudentsToInstitution(file, institution.institution_id,plan_id)
                result = importStudentsToInstitution(file, institution.institution_id)
                if not result['success']:
                    db.session.rollback()
                    return jsonify(result), 400
                skipped_students = result.get('skipped_students', [])

            db.session.commit()
            return jsonify({'success': True, 'skipped_students': skipped_students})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)})
    if request.method == "GET":
        # plan_options = PaymentPlanDetail.query.with_entities(
        #     PaymentPlanDetail.plan_id.label("id"),
        #     PaymentPlanDetail.plan_name.label("name"),
        #     PaymentPlanDetail.cost
        # ).all()

        return render_template("AdminAddInstitution.html")

@application.route('/updateInstitution', methods=["GET", "POST"])
def updateInstitution():
    if request.method == "POST":
        try:
            institution_id = request.form.get('institution_id')
            institution = Institution.query.get(institution_id)
            subscription = InstitutionSubscription.query.filter_by(institution_id=institution_id).first()

            if not institution or not subscription:
                return jsonify({'success': False, 'message': 'Institution or subscription not found'})

            # Track changes
            updated = False

            # Update institution fields only if changed
            new_name = request.form.get('name')
            if new_name and institution.institution_name != new_name:
                institution.institution_name = new_name
                updated = True

            new_no_students = int(request.form.get('no_of_students', 0))
            current_mapped_count = Student.query.filter_by(institution_id=institution_id).count()
            # if institution.no_of_students != new_no_students:
            #     institution.no_of_students = new_no_students
            #     updated = True
            if new_no_students > institution.no_of_students:
                institution.no_of_students = new_no_students
                updated = True
            elif new_no_students < institution.no_of_students:
                if new_no_students >= current_mapped_count:
                    institution.no_of_students = new_no_students
                    updated = True
                else:
                    raise Exception(f'Cannot reduce student limit to {new_no_students} — {current_mapped_count} students already mapped.')

            new_contact = request.form.get('contact_no')
            if new_contact and institution.contact_no != new_contact:
                institution.contact_no = new_contact
                updated = True

            new_address = request.form.get('address')
            if new_address and institution.address != new_address:
                institution.address = new_address
                updated = True

            new_description = request.form.get('description')
            if new_description and institution.description != new_description:
                institution.description = new_description
                updated = True

            new_status = request.form.get('status') == 'true'
            if subscription.status != new_status:
                subscription.status = new_status
                updated = True

                # Update status for all students under the institution
                students = Student.query.filter_by(institution_id=institution_id).all()
                for student in students:
                    student_subscription = Subscription.query.filter_by(subscription_id=student.last_subscription).first()
                    if student_subscription:
                        student_subscription.status = new_status           

            # Commit all field updates first, including no_of_students, before import
            if updated:
                db.session.commit()
                updated = False  # reset for changes from import            
            
            # Handle student import
            skipped_students = []
            file = request.files.get("file")
            if file and file.filename.endswith('.xlsx'):
                result = importStudentsToInstitution(file, institution.institution_id)
                if not result['success']:
                    db.session.rollback()
                    return jsonify(result), 400
                skipped_students = result.get('skipped_students', [])
                updated = True

            if updated:
                db.session.commit()

            return jsonify({'success': True, 'skipped_students': skipped_students})

        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
        
    elif request.method == "GET":
        institution_id = request.args.get("institution_id")
        if not institution_id or not institution_id.isdigit():
            return "Invalid or missing institution_id", 400

        institution = Institution.query.get(int(institution_id))
        subscription = InstitutionSubscription.query.filter_by(institution_id=institution_id).first()

        if not institution or not subscription:
            return "Institution or subscription not found", 404

        subscription_status = "Active" if subscription.status else "Inactive"

        return render_template(
            "AdminEditInstitution.html",
            institution=institution,
            subscription=subscription,
            subscription_status=subscription_status
        )
        
# Delete institution
@application.route('/deleteInstitution/<int:institution_id>', methods=['POST'])
def deleteInstitution(institution_id):
    try:
        # Delete all students, their subscriptions, and their logins
        students = Student.query.filter_by(institution_id=institution_id).all()
        for student in students:
            # 1. Set FK references to None
            student.last_subscription = None
            db.session.commit()

            # 2. Delete all subscriptions linked to this student
            Subscription.query.filter_by(student_id=student.student_id).delete()

            # 3. Delete the student
            db.session.delete(student)

            # 4. Then delete the login if needed
            Login.query.filter_by(student_id=student.student_id).delete()

            # 5. Commit once at the end
            db.session.commit()


        # Delete all institution subscriptions
        InstitutionSubscription.query.filter_by(institution_id=institution_id).delete()

        # Delete institution login
        InstitutionLogin.query.filter_by(institution_id=institution_id).delete()

        # Delete the institution
        institution = Institution.query.get(institution_id)
        if institution:
            db.session.delete(institution)

        db.session.commit()
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

def importStudentsToInstitution(file, institution_id):
    if not file or not file.filename.endswith('.xlsx'):
        return {'success': False, 'message': 'Invalid file format', 'skipped_students': []}
    
    # Count currently registered students
    existing_students_count = Student.query.filter_by(institution_id=institution_id).count()
    institution = Institution.query.get(institution_id)
    inst_subscription = InstitutionSubscription.query.filter_by(institution_id=institution_id).first()

    skipped_students = []

    try:
        df = pd.read_excel(file)
        excel_row_count = len(df)

        if existing_students_count + excel_row_count > institution.no_of_students:
            return {
                'success': False,
                'message': f'Cannot import {excel_row_count} students. Limit exceeded. Allowed: {institution.no_of_students}, Existing: {existing_students_count}',
                'skipped_students': []
            }
        
        for index, row in df.iterrows():
            student_email = row.get("Email")
            student_phone = str(row.get("Contact No"))

            # Validate required fields
            if not student_email or not student_phone:
                skipped_students.append({'row': index + 2, 'reason': 'Missing email or phone'})
                continue

            # Format checks
            if not is_valid_email(student_email):
                skipped_students.append({'row': index + 2, 'reason': 'Invalid email format'})
                continue

            if not is_valid_phone(student_phone):
                skipped_students.append({'row': index + 2, 'reason': 'Invalid phone format'})
                continue

            # Check duplicates
            if Login.query.filter_by(email=student_email).first() or Student.query.filter_by(email=student_email).first():
                skipped_students.append({'row': index + 2, 'reason': 'Email already exists'})
                continue

            if Student.query.filter_by(contact_no=student_phone).first():
                skipped_students.append({'row': index + 2, 'reason': 'Phone number already exists'})
                continue            
              
            # Hash and insert
            intended_password = "hello" + row["First Name"] + row["Last Name"]
            hashed_password = generate_password_hash(intended_password, method='pbkdf2:sha256')
            
            new_login = Login(email=student_email, password=hashed_password)
            db.session.add(new_login)
            db.session.commit()
            
            current_utc_time = datetime.now(timezone.utc)
            today = current_utc_time.date()
            
            try:
                student = Student(
                    student_id=new_login.student_id,
                    first_name=row["First Name"],
                    last_name=row["Last Name"],
                    gender=row["Gender"],
                    dob=pd.to_datetime(row["DOB"]).date(),
                    email=student_email,
                    contact_no=student_phone,
                    password=hashed_password,
                    subject_interests=row.get("Subject Interests", ""),
                    exam_interests=row.get("Exam Interests", ""),
                    institution_id=institution_id,        
                    enrolment_date = today
                )
                db.session.add(student)
                db.session.flush()    
                
                student_subscription = Subscription(
                    student_id=new_login.student_id,
                    status=inst_subscription.status,
                    plan_id = None,
                    start_date = None,
                    end_date = None
                )
                
                db.session.add(student_subscription)
                db.session.flush()
                student.last_subscription = student_subscription.subscription_id
                db.session.commit()
            except Exception as insert_error:
                skipped_students.append({'row': index + 2, 'reason': f'Insertion error: {str(insert_error)}'})
                continue

        return {
            'success': True,
            'skipped_students': skipped_students
        }

    except Exception as e:
        return {'success': False, 'message': str(e), 'skipped_students': skipped_students}

@application.route('/exportStudents/<int:institution_id>')
def exportStudents(institution_id):
    students = db.session.query(
        Student,
        Subscription
    ).join(
        Subscription, Subscription.student_id == Student.student_id
    ).filter(
        Student.institution_id == institution_id
    ).all()

    if not students:
        return "No students found for this institution", 404

    data = []
    for student, sub in students:
        data.append({
            "Student ID": student.student_id,
            "First Name": student.first_name,
            "Last Name": student.last_name,
            "Gender": student.gender,
            "DOB": student.dob.strftime('%Y-%m-%d') if student.dob else "",
            "Email": student.email,
            "Contact No": student.contact_no,
            "Subject Interests": student.subject_interests,
            "Exam Interests": student.exam_interests,
            "Enrolment Date":student.enrolment_date,
            "Status": "Active" if sub.status else "Inactive"
        })

    df = pd.DataFrame(data)
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    return send_file(output, download_name=f'students_institution_{institution_id}.xlsx', as_attachment=True)

# endregion
 
# region AdminQuestions

def get_filtered_questions():
    search_question = request.args.get('search_question', '').strip()
    subject = request.args.get('subject', '').strip()
    module = request.args.get('module', '').strip()
    page = request.args.get('page', 1, type=int)

    query = db.session.query(
        Question.q_id,
        Question.question_description,
        Subject.subject_name,
        Module.module_name
    ).join(Subject, Subject.subject_id == Question.subject_id)\
     .outerjoin(Module, Module.module_id == Question.module_id)

    if search_question:
        query = query.filter(Question.question_description.ilike(f"%{search_question}%"))
    if subject:
        query = query.filter(Subject.subject_name == subject)
    if module:
        query = query.filter(Module.module_name == module)
    
    query = query.order_by(Question.q_id.desc())
    pagination = query.paginate(page=page, per_page = 50, error_out=False)

    questions = [{
        'q_id': q.q_id,
        'question_description': q.question_description,
        'subject_name': q.subject_name,
        'module_name': q.module_name or 'N/A'
    } for q in pagination.items]

    return questions, pagination

@application.route('/AdminQuestionList')
def adminQuestionList():
    questions, pagination = get_filtered_questions()

    subjects = [s.subject_name for s in Subject.query.all()]
    modules = [m.module_name for m in Module.query.all()]
    BLOCK_SIZE = 10
    block_start = ((pagination.page - 1) // BLOCK_SIZE) * BLOCK_SIZE + 1
    block_end = min(block_start + BLOCK_SIZE - 1, pagination.pages)

    return render_template('AdminQuestionList.html',
                           questions=questions,
                           subjects=subjects,
                           modules=modules,
                           current_filters={'subject': request.args.get('subject', ''), 'module': request.args.get('module', '')},
                           page=pagination.page,
                           total_pages=pagination.pages,
                           has_prev=pagination.has_prev,
                           has_next=pagination.has_next,
                           prev_num=max(1, pagination.page - BLOCK_SIZE),
                           next_num=min(pagination.pages, pagination.page + BLOCK_SIZE),
                            block_start=block_start,
                            block_end=block_end)

@application.route('/AdminQuestionPartial')
def adminQuestionPartial():
    questions, pagination = get_filtered_questions()
    BLOCK_SIZE = 10
    block_start = ((pagination.page - 1) // BLOCK_SIZE) * BLOCK_SIZE + 1
    block_end = min(block_start + BLOCK_SIZE - 1, pagination.pages)

    return render_template('AdminQuestionPartial.html',
                           questions=questions,
                           page=pagination.page,
                           total_pages=pagination.pages,
                           has_prev=pagination.has_prev,
                           has_next=pagination.has_next,
                           prev_num=max(1, pagination.page - BLOCK_SIZE),
                           next_num=min(pagination.pages, pagination.page + BLOCK_SIZE),
                           block_start=block_start,
                           block_end=block_end)

@application.route('/adminAddQuestion', methods=['GET', 'POST'])
def adminAddQuestion():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            subject_id = request.form.get('subject')
            module_id = request.form.get('module')
            direction_id = request.form.get('direction')
            difficulty_level = request.form.get('difficulty')
            answer_options = request.form.get('answer_options')  # JSON string
            choice_type = request.form.get('type')
            multi_select = request.form.get('multi_select') == 'true'
            correct_option = request.form.get('correct_option')  # Already formatted like "{A,C}"
            solution = request.form.get('solution')

            # Validate required fields
            if not (name and subject_id and direction_id and answer_options and correct_option):
                return jsonify({'success': False, 'message': 'Missing required fields.'})

            try:
                answer_options = json.loads(answer_options)
            except json.JSONDecodeError:
                return jsonify({'success': False, 'message': 'Error parsing answer_options.'})
            
            # Create new Question
            new_question = Question(
                subject_id=int(subject_id),
                module_id=int(module_id) if module_id else None,
                direction_id=int(direction_id),
                question_description=name,
                answer_options=answer_options,  # JSON format string
                choice_type=choice_type,
                correct_option=[correct_option],  # PostgreSQL ARRAY(Text) expects list
                max_score=1,  # Assuming 1 mark per question
                solution_explanation=solution,
                multi_select=multi_select,
                difficulty_level=int(difficulty_level) if difficulty_level else 1
            )

            # Add to database
            db.session.add(new_question)
            db.session.commit()

            return jsonify({'success': True})

        except Exception as e:
            # print(f"Error while adding question: {e}")
            db.session.rollback()
            return jsonify({'success': False, 'message': 'An error occurred while adding the question.'})

    else:
        # GET request: Load Add Question page
        subjects = Subject.query.all()
        modules = Module.query.all()
        directions = Direction.query.all()
        subject_module_mappings = db.session.query(
            SubjectModuleMapping.subject_id,
            Module.module_id,
            Module.module_name
        ).join(Module).all()

        return render_template('AdminAddQuestion.html',
                               subjects=subjects,
                               modules=modules,
                               directions=directions,
                               subject_module_mappings = subject_module_mappings
                               )

@application.route('/adminEditQuestion', methods=['GET', 'POST'])
def adminEditQuestion():
    if request.method == 'POST':
        data = request.form

        q_id = data.get('q_id')
        question = Question.query.get(q_id)

        if not question:
            return jsonify({'success': False, 'message': 'Question not found'})

        # Update fields
        question.question_description = data.get('name')
        question.subject_id = int(data.get('subject')) if data.get('subject') else None
        question.module_id = int(data.get('module')) if data.get('module') else None
        question.direction_id = int(data.get('direction')) if data.get('direction') else None
        question.difficulty_level = int(data.get('difficulty')) if data.get('difficulty') else 1
        question.solution_explanation = data.get('solution')
        question.choice_type = data.get('type')

        # Update answer options
        answer_options_raw = data.get('answer_options')
        question.answer_options = json.loads(answer_options_raw) if answer_options_raw else {}

        # Update correct options
        correct_option_raw = data.get('correct_option')  # e.g., "{B}"
        if correct_option_raw:
            # Remove the curly braces and split
            selected_options = correct_option_raw.strip('{}').split(',')
            selected_options = [opt.strip() for opt in selected_options if opt.strip()]
            question.correct_option = selected_options  # ← This is a real list for Postgres TEXT[]
            question.multi_select = len(selected_options) > 1
        else:
            question.correct_option = []
            question.multi_select = False

        db.session.commit()

        return jsonify({'success': True})

    else:
        # GET request
        q_id = request.args.get('q_id')

        question = Question.query.get(q_id)
        if not question:
            return "Question not found", 404

        subjects = Subject.query.all()
        modules = Module.query.all()
        directions = Direction.query.all()
        subject_module_mappings = db.session.query(
            SubjectModuleMapping.subject_id,
            Module.module_id,
            Module.module_name
        ).join(Module).all()

        return render_template('AdminEditQuestion.html',
                               question=question,
                               subjects=subjects,
                               modules=modules,
                               directions=directions,
                               subject_module_mappings = subject_module_mappings)

@application.route('/deleteQuestion', methods=['POST'])
def deleteQuestion():
    try:
        data = request.get_json()
        question_id = data.get('question_id')

        if not question_id:
            return jsonify({'success': False, 'message': 'Missing question ID.'})

        question = Question.query.get(question_id)
        if not question:
            return jsonify({'success': False, 'message': 'Question not found.'})

        db.session.delete(question)
        db.session.commit()

        return jsonify({'success': True})

    except IntegrityError as e:
        db.session.rollback()
        if 'foreign key constraint' in str(e.orig).lower():
            return jsonify({
                'success': False,
                'message': 'Cannot delete question as it is linked to user responses.'
            })
        return jsonify({'success': False, 'message': 'Database integrity error.'})

    except Exception as e:
        db.session.rollback()
        # print(f"Unexpected error while deleting question: {e}")
        return jsonify({'success': False, 'message': 'An unexpected error occurred while deleting the question.'})

@application.route('/importQuestions', methods=['POST'])
def importQuestions():
    file = request.files.get('file')

    if not file:
        return jsonify({'success': False, 'message': 'No file uploaded'})

    try:
        df = pd.read_excel(file)

        imported = 0
        skipped = 0

        for index, row in df.iterrows():
            q_description = row.get('Question Description')
            subject_id = row.get('Subject')
            module_id = row.get('Module')
            direction_id = row.get('Direction')
            difficulty = row.get('Difficulty')
            correct_option = row.get('Correct Option')
            solution_explanation = row.get('Solution Explanation')

            choice_A = row.get('Choice A')
            choice_B = row.get('Choice B')
            choice_C = row.get('Choice C')
            choice_D = row.get('Choice D')
            
            choice_type = row.get('Choice Type')  # Expected 'text' or 'image'

            if not (q_description and subject_id and module_id and direction_id and difficulty and correct_option):
                skipped += 1
                continue

            subject = Subject.query.filter_by(subject_id=subject_id).first()
            if not subject:
                skipped += 1
                continue

            direction = Direction.query.filter_by(direction_id=direction_id).first()
            if not direction:
                skipped += 1
                continue

            
            module = Module.query.filter_by(module_id=module_id).first()                
            if not module or not SubjectModuleMapping.query.filter_by(subject_id=subject.subject_id, module_id=module.module_id).first():
                skipped += 1
                continue

            # Build answer_options dictionary
            answer_options = {}
            if choice_A: answer_options["A"] = str(choice_A)
            if choice_B: answer_options["B"] = str(choice_B)
            if choice_C: answer_options["C"] = str(choice_C)
            if choice_D: answer_options["D"] = str(choice_D)

            # Decide multi_select
            multi_select = True if ',' in correct_option else False

            new_question = Question(
                question_description=q_description,
                subject_id=subject.subject_id,
                module_id=module.module_id,
                direction_id=direction.direction_id,
                answer_options=answer_options,
                choice_type=choice_type if choice_type in ['text', 'image'] else 'text',
                correct_option=[correct_option],  # store as list
                max_score=1,
                multi_select=multi_select,
                difficulty_level=int(difficulty) if difficulty else 3,
                solution_explanation=solution_explanation if solution_explanation else ''  # blank, optional
            )

            db.session.add(new_question)
            imported += 1

        db.session.commit()

        return jsonify({'success': True, 'imported': imported, 'skipped': skipped})

    except Exception as e:
        # print("Import error:", e)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@application.route('/exportQuestions')
def exportQuestions():
    questions = db.session.query(
        Question.q_id,
        Question.question_description,
        Question.answer_options,
        Question.choice_type,
        Question.max_score,
        Question.solution_explanation,
        Question.difficulty_level,
        Question.multi_select,
        Question.correct_option,
        Question.subject_id,
        Subject.subject_name,
        Question.module_id,
        Module.module_name,
        Question.direction_id,
        Direction.direction_description
    ).join(Subject, Subject.subject_id == Question.subject_id) \
     .outerjoin(Module, Module.module_id == Question.module_id) \
     .join(Direction, Direction.direction_id == Question.direction_id) \
     .all()

    # Build list of dicts
    data = []
    for q in questions:
        data.append({
            'Question ID': q.q_id,
            'Question Description': q.question_description,
            'Question Answer Options': q.answer_options,
            'Question Choice Type': q.choice_type,
            'Question Max Score': q.max_score,
            'Question Solution Explanation': q.solution_explanation,
            'Question Difficulty Level': q.difficulty_level,
            'Question Multi Select': q.multi_select,
            'Question Correct Option': q.correct_option,
            'Question Subject Id': q.subject_id,
            'Question Subject Name': q.subject_name,
            'Question Moduel Id': q.module_id,
            'Question Module Name': q.module_name,
            'Question Direction': q.direction_id,
            'Question Direction Description': q.direction_description
        })

    # Create DataFrame
    df = pd.DataFrame(data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Questions')

    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        download_name='questions.xlsx',
        as_attachment=True
    )
   
# endregion 
 
# region AdminSubject

# Load full Admin Subject List Page
@application.route('/AdminSubjectList')
def adminSubjectList():
    subject_filter = request.args.get('subject', '')
    page = request.args.get('page', 1, type=int)

    query = db.session.query(Subject)

    if subject_filter:
        query = query.filter(Subject.subject_name.ilike(f'%{subject_filter}%'))

    query = query.order_by(Subject.subject_id.desc())
    pagination = query.paginate(page=page, per_page = 50)

    subjects = pagination.items

    subject_data = []
    for subject in subjects:
        module_mappings = SubjectModuleMapping.query.filter_by(subject_id=subject.subject_id).all()
        module_names = []
        for mapping in module_mappings:
            module = Module.query.get(mapping.module_id)
            if module:
                module_names.append(module.module_name)
        module_names_str = ", ".join(module_names)

        subject_data.append({
            'subject_id': subject.subject_id,
            'subject_name': subject.subject_name,
            'modules': module_names_str
        })

    all_subjects = db.session.query(Subject.subject_name).distinct().all()
    all_subjects = [s[0] for s in all_subjects]

    all_modules = db.session.query(Module.module_id, Module.module_name).distinct().all()
    
    BLOCK_SIZE = 10
    block_start = ((pagination.page - 1) // BLOCK_SIZE) * BLOCK_SIZE + 1
    block_end = min(block_start + BLOCK_SIZE - 1, pagination.pages)
    
    return render_template('AdminSubjectList.html',
                           subjects=subject_data,
                           page=page,
                           total_pages=pagination.pages,
                           prev_num=max(1, pagination.page - BLOCK_SIZE),
                           next_num=min(pagination.pages, pagination.page + BLOCK_SIZE),
                           has_prev=pagination.has_prev,
                           has_next=pagination.has_next,
                           block_start=block_start,
                            block_end=block_end,
                           current_filters={'subject': subject_filter},
                           all_subjects=all_subjects,
                           all_modules=all_modules)

# Load only the Partial Table (for AJAX reloads)
@application.route('/AdminSubjectPartial')
def adminSubjectPartial():
    subject_filter = request.args.get('subject', '')
    page = request.args.get('page', 1, type=int)

    # Base query: get all subjects
    query = db.session.query(Subject)

    if subject_filter:
        query = query.filter(Subject.subject_name.ilike(f'%{subject_filter}%'))

    query = query.order_by(Subject.subject_id.desc())
    pagination = query.paginate(page=page, per_page = 50)

    subjects = pagination.items

    # Build subject data with associated module names
    subject_data = []
    for subject in subjects:
        mappings = SubjectModuleMapping.query.filter_by(subject_id=subject.subject_id).all()
        module_names = []
        for mapping in mappings:
            module = Module.query.get(mapping.module_id)
            if module:
                module_names.append(module.module_name)
        module_names_str = ", ".join(module_names)

        subject_data.append({
            'subject_id': subject.subject_id,
            'subject_name': subject.subject_name,
            'modules': module_names_str
        })        
        
    BLOCK_SIZE = 10
    block_start = ((pagination.page - 1) // BLOCK_SIZE) * BLOCK_SIZE + 1
    block_end = min(block_start + BLOCK_SIZE - 1, pagination.pages)

    return render_template('AdminSubjectPartial.html',
                           subjects=subject_data,
                           page=page,
                           total_pages=pagination.pages,
                           prev_num=max(1, pagination.page - BLOCK_SIZE),
                           next_num=min(pagination.pages, pagination.page + BLOCK_SIZE),
                           has_prev=pagination.has_prev,
                           has_next=pagination.has_next,
                           block_start=block_start,
                            block_end=block_end)

# Get subject details for editing
@application.route('/getSubject/<int:subject_id>')
def getSubject(subject_id):
    subject = Subject.query.get(subject_id)
    if not subject:
        return jsonify({'success': False, 'message': 'Subject not found'})

    # Fetch all modules linked to this subject
    mappings = SubjectModuleMapping.query.filter_by(subject_id=subject_id).all()
    module_data = []

    for mapping in mappings:
        module = Module.query.get(mapping.module_id)
        if module:
            module_data.append({
                'module_id': module.module_id,
                'module_name': module.module_name
            })

    return jsonify({
        'success': True,
        'subject': {
            'subject_id': subject.subject_id,
            'subject_name': subject.subject_name,
            'modules': module_data
        }
    })

@application.route('/addSubject', methods=['POST'])
def addSubject():
    data = request.get_json()
    subject_name = data.get('subject_name')
    module_ids = data.get('module_ids', [])

    if not subject_name or not module_ids:
        return jsonify({'success': False, 'message': 'Subject name and modules are required'})

    try:
        # Create subject
        subject = Subject(subject_name=subject_name)
        db.session.add(subject)
        db.session.flush()  # so that subject_id gets generated

        for module_id in module_ids:
            mapping = SubjectModuleMapping(subject_id=subject.subject_id, module_id=module_id)
            db.session.add(mapping)

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@application.route('/updateSubject', methods=['POST'])
def updateSubject():
    data = request.get_json()
    subject_id = data.get('subject_id')
    subject_name = data.get('subject_name')
    module_ids = data.get('module_ids', [])

    subject = Subject.query.get(subject_id)
    if not subject:
        return jsonify({'success': False, 'message': 'Subject not found'})

    try:
        subject.subject_name = subject_name

        # Clear existing mappings
        SubjectModuleMapping.query.filter_by(subject_id=subject_id).delete()

        # Add new mappings
        for module_id in module_ids:
            mapping = SubjectModuleMapping(subject_id=subject_id, module_id=module_id)
            db.session.add(mapping)

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@application.route('/deleteSubject', methods=['POST'])
def deleteSubject():
    data = request.get_json()
    subject_id = data.get('subject_id')

    subject = Subject.query.get(subject_id)
    if not subject:
        return jsonify({'success': False, 'message': 'Subject not found'})

    try:
        SubjectModuleMapping.query.filter_by(subject_id=subject_id).delete()
        db.session.delete(subject)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
    
@application.route('/exportSubjects')
def exportSubjects():
    try:
        # JOIN Subject → Mapping → Module
        results = db.session.query(
            Subject.subject_id,
            Subject.subject_name,
            Module.module_name
        ).join(SubjectModuleMapping, Subject.subject_id == SubjectModuleMapping.subject_id
        ).join(Module, Module.module_id == SubjectModuleMapping.module_id).all()

        data = [{
            'Subject Id': r.subject_id,
            'Subject Name': r.subject_name,
            'Module Name': r.module_name
        } for r in results]

        df = pd.DataFrame(data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Subjects')

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='Subjects.xlsx'
        )
    except Exception as e:
        return str(e), 500

@application.route('/importSubjects', methods=['POST'])
def importSubjects():
    file = request.files.get('file')
    if not file:
        return jsonify({'success': False, 'message': 'No file uploaded'})

    try:
        df = pd.read_excel(file)

        if not {'Subject Name', 'Module Id'}.issubset(df.columns):
            return jsonify({'success': False, 'message': 'Invalid Excel format. Required columns: Subject Name, Module Id'})

        inserted = 0
        skipped = 0

        for _, row in df.iterrows():
            subject_name = str(row['Subject Name']).strip()
            module_id = str(row['Module Id']).strip()

            if not subject_name or not module_id:
                continue

            # Find or create Subject
            subject = Subject.query.filter_by(subject_name=subject_name).first()
            if not subject:
                subject = Subject(subject_name=subject_name)
                db.session.add(subject)
                db.session.flush()  # To get subject_id before commit

            # Find Module
            module = Module.query.filter_by(module_id=module_id).first()
            if not module:
                skipped += 1
                continue

            # Check if mapping already exists
            existing = SubjectModuleMapping.query.filter_by(subject_id=subject.subject_id, module_id=module.module_id).first()
            if existing:
                skipped += 1
                continue

            # Create new mapping
            mapping = SubjectModuleMapping(subject_id=subject.subject_id, module_id=module.module_id)
            db.session.add(mapping)
            inserted += 1

        db.session.commit()
        return jsonify({'success': True, 'imported': inserted, 'skipped': skipped})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
    
# endregion
 
# region AdminModule
 
# Load full Admin Module List Page
@application.route('/AdminModuleList')
def adminModuleList():
    module_id = request.args.get('module_id', type=int)
    page = request.args.get('page', 1, type=int)

    query = Module.query.order_by(Module.module_id.desc())

    if module_id:
        query = query.filter(Module.module_id == module_id)

    pagination = query.paginate(page=page, per_page = 50)
    modules = pagination.items

    # For filter dropdown — always freshly fetch all
    # all_modules = Module.query.all()
    all_modules = Module.query.order_by(Module.module_id.desc()).all()    
    
    BLOCK_SIZE = 10
    block_start = ((pagination.page - 1) // BLOCK_SIZE) * BLOCK_SIZE + 1
    block_end = min(block_start + BLOCK_SIZE - 1, pagination.pages)

    return render_template('AdminModuleList.html',
                           modules=modules,
                           all_modules=all_modules,  # <- Use full updated list here
                           page=page,
                           total_pages=pagination.pages,
                           prev_num=max(1, pagination.page - BLOCK_SIZE),
                           next_num=min(pagination.pages, pagination.page + BLOCK_SIZE),
                           has_prev=pagination.has_prev,
                           has_next=pagination.has_next,
                           block_start=block_start,
                            block_end=block_end,
                           current_filters={'module_id': module_id})

# Load partial table for Module
@application.route('/AdminModulePartial')
def adminModulePartial():
    module_id = request.args.get('module_id', type=int)
    page = request.args.get('page', 1, type=int)

    query = Module.query

    if module_id:
        query = query.filter(Module.module_id == module_id)

    query = query.order_by(Module.module_id.desc())
    pagination = query.paginate(page=page, per_page = 50)
    modules = pagination.items
        
    BLOCK_SIZE = 10
    block_start = ((pagination.page - 1) // BLOCK_SIZE) * BLOCK_SIZE + 1
    block_end = min(block_start + BLOCK_SIZE - 1, pagination.pages)

    return render_template('AdminModulePartial.html',
                           modules=modules,
                           page=page,
                           total_pages=pagination.pages,
                           prev_num=max(1, pagination.page - BLOCK_SIZE),
                           next_num=min(pagination.pages, pagination.page + BLOCK_SIZE),
                           has_prev=pagination.has_prev,
                           has_next=pagination.has_next,
                           block_start=block_start,
                            block_end=block_end)

# Add Module
@application.route('/addModule', methods=['POST'])
def addModule():
    data = request.get_json()
    module_name = data.get('module_name')

    if not module_name:
        return jsonify({'success': False, 'message': 'Module name is required'})

    existing = Module.query.filter_by(module_name=module_name).first()
    if existing:
        return jsonify({'success': False, 'message': 'Module already exists'})

    try:
        new_module = Module(module_name=module_name)
        db.session.add(new_module)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# Get Single Module
@application.route('/getModule/<int:module_id>')
def getModule(module_id):
    module = Module.query.get(module_id)
    if not module:
        return jsonify({'success': False, 'message': 'Module not found'})

    return jsonify({
        'success': True,
        'module': {
            'module_id': module.module_id,
            'module_name': module.module_name
        }
    })

# Update Module
@application.route('/updateModule', methods=['POST'])
def updateModule():
    data = request.get_json()
    module_id = data.get('module_id')
    module_name = data.get('module_name')

    module = Module.query.get(module_id)
    if not module:
        return jsonify({'success': False, 'message': 'Module not found'})

    existing = Module.query.filter(
        Module.module_name == module_name,
        Module.module_id != module_id
    ).first()

    if existing:
        return jsonify({'success': False, 'message': 'Another module with the same name already exists'})

    try:
        module.module_name = module_name
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# Delete Module
@application.route('/deleteModule', methods=['POST'])
def deleteModule():
    data = request.get_json()
    module_id = data.get('module_id')

    module = Module.query.get(module_id)
    if not module:
        return jsonify({'success': False, 'message': 'Module not found'})

    try:
        SubjectModuleMapping.query.filter_by(module_id=module_id).delete()
        db.session.delete(module)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# Export Modules
@application.route('/exportmodules')
def exportmodules():
    try:
        modules = Module.query.all()

        data = [{
            'Module ID': c.module_id,
            'Module Name': c.module_name
        } for c in modules]

        df = pd.DataFrame(data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Modules')

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='Modules.xlsx'
        )
    except Exception as e:
        return str(e), 500

# Import Modules
@application.route('/importmodules', methods=['POST'])
def importmodules():
    file = request.files.get('file')
    if not file:
        return jsonify({'success': False, 'message': 'No file uploaded'})

    try:
        df = pd.read_excel(file)

        if 'Module Name' not in df.columns:
            return jsonify({'success': False, 'message': 'Invalid Excel format'})

        inserted = 0
        skipped = 0

        for _, row in df.iterrows():
            module_name = str(row['Module Name']).strip()

            if not module_name:
                continue

            existing = Module.query.filter_by(module_name=module_name).first()
            if existing:
                skipped += 1
                continue

            new_module = Module(module_name=module_name)
            db.session.add(new_module)
            inserted += 1

        db.session.commit()
        return jsonify({'success': True, 'imported': inserted, 'skipped': skipped})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
 
# endregion
 
# region AdminCategory
 
# Load full Admin Category List Page
@application.route('/AdminCategoryList')
def adminCategoryList():
    category_id = request.args.get('category_id', type=int)
    page = request.args.get('page', 1, type=int)

    query = ExamCategory.query

    if category_id:
        query = query.filter(ExamCategory.category_id == category_id)

    query = query.order_by(ExamCategory.category_id.desc())
    pagination = query.paginate(page=page, per_page = 50)
    categories = pagination.items

    # For filter dropdown — always freshly fetch all
    all_categories = ExamCategory.query.order_by(ExamCategory.category_id.desc()).all()    
    
    BLOCK_SIZE = 10
    block_start = ((pagination.page - 1) // BLOCK_SIZE) * BLOCK_SIZE + 1
    block_end = min(block_start + BLOCK_SIZE - 1, pagination.pages)

    return render_template('AdminCategoryList.html',
                           categories=categories,
                           all_categories=all_categories,  # <- Use full updated list here
                           page=page,
                           total_pages=pagination.pages,
                           prev_num=max(1, pagination.page - BLOCK_SIZE),
                           next_num=min(pagination.pages, pagination.page + BLOCK_SIZE),
                           has_prev=pagination.has_prev,
                           has_next=pagination.has_next,
                           block_start=block_start,
                            block_end=block_end,
                           current_filters={'category_id': category_id})

# Load partial table for Category
@application.route('/AdminCategoryPartial')
def adminCategoryPartial():
    category_id = request.args.get('category_id', type=int)
    page = request.args.get('page', 1, type=int)

    query = ExamCategory.query

    if category_id:
        query = query.filter(ExamCategory.category_id == category_id)

    query = query.order_by(ExamCategory.category_id.desc())
    pagination = query.paginate(page=page, per_page = 50)
    categories = pagination.items
    
    BLOCK_SIZE = 10
    block_start = ((pagination.page - 1) // BLOCK_SIZE) * BLOCK_SIZE + 1
    block_end = min(block_start + BLOCK_SIZE - 1, pagination.pages)

    return render_template('AdminCategoryPartial.html',
                           categories=categories,
                           page=page,
                           total_pages=pagination.pages,
                           prev_num=max(1, pagination.page - BLOCK_SIZE),
                           next_num=min(pagination.pages, pagination.page + BLOCK_SIZE),
                           has_prev=pagination.has_prev,
                           has_next=pagination.has_next,
                           block_start=block_start,
                            block_end=block_end)

# Add Category
@application.route('/addCategory', methods=['POST'])
def addCategory():
    data = request.get_json()
    category_name = data.get('category_name')

    if not category_name:
        return jsonify({'success': False, 'message': 'Category name is required'})

    existing = ExamCategory.query.filter_by(category_name=category_name).first()
    if existing:
        return jsonify({'success': False, 'message': 'Category already exists'})

    try:
        new_category = ExamCategory(category_name=category_name)
        db.session.add(new_category)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# Get Single Category
@application.route('/getCategory/<int:category_id>')
def getCategory(category_id):
    category = ExamCategory.query.get(category_id)
    if not category:
        return jsonify({'success': False, 'message': 'Category not found'})

    return jsonify({
        'success': True,
        'category': {
            'category_id': category.category_id,
            'category_name': category.category_name
        }
    })

# Update Category
@application.route('/updateCategory', methods=['POST'])
def updateCategory():
    data = request.get_json()
    category_id = data.get('category_id')
    category_name = data.get('category_name')

    category = ExamCategory.query.get(category_id)
    if not category:
        return jsonify({'success': False, 'message': 'Category not found'})

    existing = ExamCategory.query.filter(
        ExamCategory.category_name == category_name,
        ExamCategory.category_id != category_id
    ).first()

    if existing:
        return jsonify({'success': False, 'message': 'Another category with the same name already exists'})

    try:
        category.category_name = category_name
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# Delete Category
@application.route('/deleteCategory', methods=['POST'])
def deleteCategory():
    data = request.get_json()
    category_id = data.get('category_id')

    category = ExamCategory.query.get(category_id)
    if not category:
        return jsonify({'success': False, 'message': 'Category not found'})

    try:
        db.session.delete(category)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# Export Categories
@application.route('/exportcategories')
def exportcategories():
    try:
        categories = ExamCategory.query.all()

        data = [{
            'Category ID': c.category_id,
            'Category Name': c.category_name
        } for c in categories]

        df = pd.DataFrame(data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Categories')

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='Categories.xlsx'
        )
    except Exception as e:
        return str(e), 500

# Import Categories
@application.route('/importcategories', methods=['POST'])
def importcategories():
    file = request.files.get('file')
    if not file:
        return jsonify({'success': False, 'message': 'No file uploaded'})

    try:
        df = pd.read_excel(file)

        if 'Category Name' not in df.columns:
            return jsonify({'success': False, 'message': 'Invalid Excel format'})

        inserted = 0
        skipped = 0

        for _, row in df.iterrows():
            category_name = str(row['Category Name']).strip()

            if not category_name:
                continue

            existing = ExamCategory.query.filter_by(category_name=category_name).first()
            if existing:
                skipped += 1
                continue

            new_category = ExamCategory(category_name=category_name)
            db.session.add(new_category)
            inserted += 1

        db.session.commit()
        return jsonify({'success': True, 'imported': inserted, 'skipped': skipped})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
 
# endregion
     
# region AdminExam

# Load Exam List
@application.route('/AdminExamList')
def adminExamList():
    page = request.args.get('page', 1, type=int)
    search_category = request.args.get('search_category', '')

    # query = db.session.query(Exam, ExamCategory.category_name).join(ExamCategory, Exam.category_id == ExamCategory.category_id)
    query = db.session.query(Exam, ExamCategory.category_name) \
    .join(ExamCategory, Exam.category_id == ExamCategory.category_id)

    if search_category:
        query = query.filter(Exam.category_id == search_category)

    query = query.order_by(Exam.exam_id.desc())
    pagination = query.paginate(page=page, per_page = 50)

    exams = [
        {
            'exam_id': ex.Exam.exam_id,
            'exam_name': ex.Exam.exam_name,
            'examcategory_name': ex.category_name,
            'updatedon': ex.Exam.updatedon.strftime('%Y-%m-%d') if ex.Exam.updatedon else ''
        } for ex in pagination.items
    ]

    examcategories = ExamCategory.query.all()
    
    BLOCK_SIZE = 10
    block_start = ((pagination.page - 1) // BLOCK_SIZE) * BLOCK_SIZE + 1
    block_end = min(block_start + BLOCK_SIZE - 1, pagination.pages)

    return render_template('AdminExamList.html', exams=exams, examcategories=examcategories, 
                           page=page, total_pages=pagination.pages, prev_num=max(1, pagination.page - BLOCK_SIZE),
                           next_num=min(pagination.pages, pagination.page + BLOCK_SIZE), has_prev=pagination.has_prev, has_next=pagination.has_next,
                           block_start=block_start, block_end=block_end,
                           current_filters={'search_category': search_category})

# Partial for AJAX
@application.route('/AdminExamPartial')
def adminExamPartial():
    page = request.args.get('page', 1, type=int)
    search_category = request.args.get('search_category', '')

    query = db.session.query(Exam, ExamCategory.category_name).join(ExamCategory, Exam.category_id == ExamCategory.category_id)

    if search_category:
        query = query.filter(Exam.category_id == search_category)

    query = query.order_by(Exam.exam_id.desc())
    pagination = query.paginate(page=page, per_page = 50)

    exams = [
        {
            'exam_id': ex.Exam.exam_id,
            'exam_name': ex.Exam.exam_name,
            'examcategory_name': ex.category_name,
            'updatedon': ex.Exam.updatedon.strftime('%Y-%m-%d') if ex.Exam.updatedon else ''
        } for ex in pagination.items
    ]
    
    BLOCK_SIZE = 10
    block_start = ((pagination.page - 1) // BLOCK_SIZE) * BLOCK_SIZE + 1
    block_end = min(block_start + BLOCK_SIZE - 1, pagination.pages)
    
    return render_template('AdminExamPartial.html', exams=exams,
                           page=page, total_pages=pagination.pages, prev_num=max(1, pagination.page - BLOCK_SIZE),
                           block_start=block_start, block_end=block_end,
                           next_num=min(pagination.pages, pagination.page + BLOCK_SIZE), has_prev=pagination.has_prev, has_next=pagination.has_next)

@application.route('/AddExam', methods=['GET', 'POST'])
def addExam():
    if request.method == 'POST':
        data = request.form

        # --- Create Exam ---
        exam = Exam(
            exam_name=(data.get('exam_name') or '').strip(),
            category_id=int(data.get('category_id')) if data.get('category_id') else None,
            exam_description=(data.get('exam_description') or '').strip(),
            year=int(data.get('year')) if data.get('year') else datetime.today().year,
        )
        db.session.add(exam)
        db.session.flush()  # ensure exam.exam_id is available without an early commit

        # --- Prepare block ---
        db.session.add(ExamPrepare(
            exam_id=exam.exam_id,
            mockdesc=(data.get('mockdesc') or '').strip(),
            dailydesc=(data.get('dailydesc') or '').strip(),
            customdesc=(data.get('customdesc') or '').strip(),
            additionalinf=(data.get('additionalinf') or '').strip()
        ))

        # --- Exam Pattern (supports both naming styles just in case) ---
        subjects       = data.getlist('pattern_subjects[]') or data.getlist('subject[]')
        no_questions   = data.getlist('pattern_questions[]') or data.getlist('no_questions[]')
        marks          = data.getlist('pattern_marks[]')     or data.getlist('marks[]')
        time_minutes   = data.getlist('pattern_time[]')      or data.getlist('time_alloted[]')

        for i in range(max(len(subjects), len(no_questions), len(marks), len(time_minutes))):
            subj = (subjects[i] if i < len(subjects) else '').strip()
            if not subj:
                continue
            try:
                nq = int(no_questions[i]) if i < len(no_questions) and no_questions[i] else 0
                mk = int(marks[i]) if i < len(marks) and marks[i] else 0
                mins = int(time_minutes[i]) if i < len(time_minutes) and time_minutes[i] else 0
            except ValueError:
                continue

            db.session.add(ExamPattern(
                exam_id=exam.exam_id,
                subject=subj,
                no_questions=nq,
                marks=mk,
                time_alloted=timedelta(minutes=mins)  # store as interval/timedelta
            ))

        # --- Exam Calendar (multiple rows) ---
        events = data.getlist('calendar_events[]')
        dates  = data.getlist('calendar_dates[]')

        # Fallback to single-name inputs if present
        if not events and data.get('schedule_of_events'):
            events = [data.get('schedule_of_events')]
        if not dates and data.get('important_dates'):
            dates = [data.get('important_dates')]

        for i in range(max(len(events), len(dates))):
            ev = (events[i] if i < len(events) else '').strip()
            dt_raw = (dates[i] if i < len(dates) else '').strip()
            if not ev and not dt_raw:
                continue

            dt = None
            if dt_raw:
                try:
                    dt = datetime.strptime(dt_raw, '%Y-%m-%d')
                except ValueError:
                    dt = None

            db.session.add(ExamCalendar(
                exam_id=exam.exam_id,
                schedule_of_events=ev,
                important_dates=dt
            ))

        db.session.commit()
        return redirect(url_for('adminExamList'))

    categories = ExamCategory.query.all()
    return render_template('AdminAddExam.html', categories=categories)

# Update Exam
@application.route('/updateExam/<int:exam_id>', methods=['GET', 'POST'])
def updateExam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    prepare = ExamPrepare.query.filter_by(exam_id=exam_id).first()
    patterns = ExamPattern.query.filter_by(exam_id=exam_id).all()
    calendars = ExamCalendar.query.filter_by(exam_id=exam_id).all()

    if request.method == 'POST':
        data = request.form

        # ---------- helpers ----------
        def _to_int(val, default=0):
            if val is None:
                return default
            s = str(val).strip()
            if s == "":
                return default
            try:
                # accept "10", "10.0", "10.50"
                return int(float(s))
            except ValueError:
                return default

        def _to_date(yyyy_mm_dd):
            s = (yyyy_mm_dd or "").strip()
            if not s:
                return None
            try:
                return datetime.strptime(s, '%Y-%m-%d').date()
            except ValueError:
                return None

        # ---------- basic fields ----------
        exam.exam_name = (data.get('exam_name') or "").strip()
        category_raw = data.get('category_id')
        exam.category_id = _to_int(category_raw, None)
        exam.exam_description = (data.get('exam_description') or "").strip()

        year_raw = data.get('year')
        exam.year = _to_int(year_raw, datetime.today().year)

        # ---------- prepare section ----------
        if not prepare:
            prepare = ExamPrepare(exam_id=exam.exam_id)
            db.session.add(prepare)

        prepare.mockdesc = (data.get('mockdesc') or "").strip()
        prepare.dailydesc = (data.get('dailydesc') or "").strip()
        prepare.customdesc = (data.get('customdesc') or "").strip()
        prepare.additionalinf = (data.get('additionalinf') or "").strip()

        # ---------- PATTERNS: UPSERT BY ID + DELETE MISSING ----------
        p_ids   = data.getlist('pattern_ids[]')
        p_subj  = data.getlist('pattern_subjects[]')
        p_qs    = data.getlist('pattern_questions[]')
        p_marks = data.getlist('pattern_marks[]')
        p_time  = data.getlist('pattern_time[]')

        existing_patterns = {p.pattern_id: p for p in ExamPattern.query.filter_by(exam_id=exam_id).all()}
        seen_pattern_ids = set()

        rows = max(len(p_ids), len(p_subj), len(p_qs), len(p_marks), len(p_time))
        for i in range(rows):
            pid_raw = (p_ids[i] if i < len(p_ids) else "").strip()
            subj    = (p_subj[i] if i < len(p_subj) else "").strip()
            nq      = _to_int(p_qs[i]   if i < len(p_qs)   else "", 0)
            mk      = _to_int(p_marks[i]if i < len(p_marks)else "", 0)
            tm_raw = p_time[i] if i < len(p_time) else ""
            mins    = _to_int(tm_raw, 0)

            # Skip truly empty row
            if not (pid_raw or subj or nq or mk or mins):
                continue

            if pid_raw:  # UPDATE
                try:
                    pid = int(pid_raw)
                except ValueError:
                    pid = None
                if pid and pid in existing_patterns:
                    pat = existing_patterns[pid]
                    pat.subject      = subj or pat.subject
                    pat.no_questions = nq
                    pat.marks        = mk
                    if tm_raw.strip() != "":   # only if user gave a value
                        # mins = _to_int(tm_raw, 0)
                        pat.time_alloted = timedelta(minutes=mins)
                    seen_pattern_ids.add(pid)
            else:        # INSERT
                db.session.add(ExamPattern(
                    exam_id=exam.exam_id,
                    subject=subj,
                    no_questions=nq,
                    marks=mk,
                    time_alloted=timedelta(minutes=mins)
                ))

        # DELETE patterns not present anymore
        for pid, pat in list(existing_patterns.items()):
            if pid not in seen_pattern_ids:
                db.session.delete(pat)

        # ---------- CALENDAR: UPSERT BY ID + DELETE MISSING ----------
        c_ids   = data.getlist('calendar_ids[]')
        c_evts  = data.getlist('calendar_events[]')
        c_dates = data.getlist('calendar_dates[]')

        existing_cals = {c.calendar_id: c for c in ExamCalendar.query.filter_by(exam_id=exam_id).all()}
        seen_cal_ids = set()

        rows = max(len(c_ids), len(c_evts), len(c_dates))
        for i in range(rows):
            cid_raw = (c_ids[i] if i < len(c_ids) else "").strip()
            ev      = (c_evts[i] if i < len(c_evts) else "").strip()
            dt      = _to_date(c_dates[i] if i < len(c_dates) else "")

            # Skip truly empty row
            if not (cid_raw or ev or dt):
                continue

            if cid_raw:  # UPDATE
                try:
                    cid = int(cid_raw)
                except ValueError:
                    cid = None
                if cid and cid in existing_cals:
                    cal = existing_cals[cid]
                    cal.schedule_of_events = ev or cal.schedule_of_events
                    cal.important_dates    = dt
                    seen_cal_ids.add(cid)
            else:        # INSERT
                db.session.add(ExamCalendar(
                    exam_id=exam.exam_id,
                    schedule_of_events=ev,
                    important_dates=dt
                ))

        # DELETE calendars not present anymore
        for cid, cal in list(existing_cals.items()):
            if cid not in seen_cal_ids:
                db.session.delete(cal)

        # ---------- commit ----------
        db.session.commit()
        return redirect(url_for('adminExamList'))

    # GET
    categories = ExamCategory.query.all()
    return render_template(
        'AdminEditExam.html',
        exam=exam,
        prepare=prepare,
        patterns=patterns,
        calendars=calendars,
        categories=categories
    )

# Delete Exam
@application.route('/deleteExam', methods=['POST'])
def deleteExam():
    data = request.get_json()
    exam = Exam.query.get(data['exam_id'])

    if not exam:
        return jsonify({'success': False, 'message': 'Exam not found'})

    db.session.delete(exam)
    db.session.commit()
    return jsonify({'success': True})

# endregion

# region MockExam

@application.route('/AdminMockExamList')
def adminMockExamList():
    page = int(request.args.get('page', 1))
    per_page = 50
    search = request.args.get('search_mock_exams', '').strip()

    query = MockExam.query
    if search:
        query = query.filter(MockExam.exam_name.ilike(f"%{search}%"))

    pagination = query.order_by(MockExam.exam_id.desc()).paginate(page=page, per_page=per_page)
    
    BLOCK_SIZE = 10
    block_start = ((pagination.page - 1) // BLOCK_SIZE) * BLOCK_SIZE + 1
    block_end = min(block_start + BLOCK_SIZE - 1, pagination.pages)
    
    return render_template('AdminMockExamList.html', mockExams=pagination.items,
                           page=pagination.page, total_pages=pagination.pages,
                           has_next=pagination.has_next, has_prev=pagination.has_prev,
                           block_start=block_start, block_end=block_end,
                           next_num=min(pagination.pages, pagination.page + BLOCK_SIZE), prev_num=max(1, pagination.page - BLOCK_SIZE))

@application.route('/AdminMockExamPartial')
def adminMockExamPartial():
    page = int(request.args.get('page', 1))
    per_page = 50
    search = request.args.get('search_mock_exams', '').strip()

    query = MockExam.query
    if search:
        query = query.filter(MockExam.exam_name.ilike(f"%{search}%"))

    pagination = query.order_by(MockExam.exam_id.desc()).paginate(page=page, per_page=per_page)
    
    BLOCK_SIZE = 10
    block_start = ((pagination.page - 1) // BLOCK_SIZE) * BLOCK_SIZE + 1
    block_end = min(block_start + BLOCK_SIZE - 1, pagination.pages)
    
    return render_template('AdminMockExamPartial.html', mockExams=pagination.items,
                           page=pagination.page, total_pages=pagination.pages,
                           has_next=pagination.has_next, has_prev=pagination.has_prev,
                           block_start=block_start, block_end=block_end,
                           next_num=min(pagination.pages, pagination.page + BLOCK_SIZE), prev_num=max(1, pagination.page - BLOCK_SIZE))

@application.route('/adminAddMockExam', methods=['GET', 'POST'])
def adminAddMockExam():
    if request.method == 'GET':
        subjects = Subject.query.all()
        return render_template('AdminAddMockExam.html', subjects=subjects)

    try:
        name = request.form['name']
        difficulty_map = {"1": "Easy", "2": "Medium", "3": "Difficult"}
        difficulty = difficulty_map.get(request.form['difficulty'], 'Easy')
        duration_minutes = int(request.form['duration'])
        general_instructions = request.form['instructions']

        exam = MockExam(
            exam_name=name,
            exam_difficulty=difficulty,
            exam_duration=timedelta(minutes=duration_minutes),
            general_instructions=general_instructions
        )
        db.session.add(exam)
        db.session.flush()
        config_data = json.loads(request.form['config'])
        for subject_id, q_diff in config_data.items():
            db.session.add(MockExamConfig(
                exam_id=exam.exam_id,
                subject_id=int(subject_id),
                q_diff=q_diff
            ))
        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@application.route('/adminEditMockExam/<int:exam_id>', methods=['GET', 'POST'])
def adminEditMockExam(exam_id):
    exam = MockExam.query.get_or_404(exam_id)
    if request.method == 'GET':
        subjects = Subject.query.all()
        configs = MockExamConfig.query.filter_by(exam_id=exam_id).all()
        return render_template('AdminEditMockExam.html', exam=exam, configs=configs, subjects=subjects)

    try:
        changed = False
        name = request.form['name']
        difficulty_map = {"1": "Easy", "2": "Medium", "3": "Difficult"}
        difficulty = difficulty_map.get(request.form['difficulty'], 'Easy')
        duration = timedelta(minutes=int(request.form['duration']))
        instructions = request.form['instructions']
        config_data = json.loads(request.form['config'])

        if exam.exam_name != name:
            exam.exam_name = name
            changed = True
        if exam.exam_difficulty != difficulty:
            exam.exam_difficulty = difficulty
            changed = True
        if exam.exam_duration != duration:
            exam.exam_duration = duration
            changed = True
        if exam.general_instructions != instructions:
            exam.general_instructions = instructions
            changed = True

        existing_configs = {c.subject_id: c for c in MockExamConfig.query.filter_by(exam_id=exam_id).all()}
        for subject_id_str, q_diff in config_data.items():
            subject_id = int(subject_id_str)
            if subject_id in existing_configs:
                if existing_configs[subject_id].q_diff != q_diff:
                    existing_configs[subject_id].q_diff = q_diff
                    changed = True
            else:
                db.session.add(MockExamConfig(
                    exam_id=exam_id,
                    subject_id=subject_id,
                    q_diff=q_diff
                ))
                changed = True

        db.session.commit() if changed else None
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@application.route('/deleteMockExam', methods=['POST'])
def delete_mock_exam():
    exam_id = request.json.get('q_id')
    try:
        MockExamConfig.query.filter_by(exam_id=exam_id).delete()
        MockExam.query.filter_by(exam_id=exam_id).delete()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# @application.route('/exportMockExams')
# def exportMockExams():
#     exams = MockExam.query.all()
#     configs = MockExamConfig.query.all()
#     exam_data = []
#     for exam in exams:
#         exam_data.append({
#             'Exam ID': exam.exam_id,
#             'Name': exam.exam_name,
#             'Difficulty': exam.exam_difficulty,
#             'Duration': str(exam.exam_duration),
#             'Instructions': exam.general_instructions
#         })
#     config_data = [{
#         'Exam ID': c.exam_id,
#         'Subject ID': c.subject_id,
#         'Q_Diff': json.dumps(c.q_diff)
#     } for c in configs]

#     output = io.BytesIO()
#     with pd.ExcelWriter(output, engine='openpyxl') as writer:
#         pd.DataFrame(exam_data).to_excel(writer, sheet_name='Exams', index=False)
#         pd.DataFrame(config_data).to_excel(writer, sheet_name='Config', index=False)
#     output.seek(0)
#     return send_file(output, as_attachment=True, download_name='mock_exams_with_config.xlsx')

@application.route('/exportMockExams')
def exportMockExams():
    exams = MockExam.query.all()
    configs = MockExamConfig.query.all()

    # Prepare exam details
    exam_data = [{
        'Exam ID': exam.exam_id,
        'Name': exam.exam_name,
        'Difficulty': exam.exam_difficulty,
        'Duration': str(exam.exam_duration),
        'Instructions': exam.general_instructions
    } for exam in exams]

    # Prepare config details (shared sheet)
    config_data = [{
        'Exam ID': config.exam_id,
        'Subject ID': config.subject_id,
        'Q_Diff': json.dumps(config.q_diff)
    } for config in configs]

    # Write to Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(exam_data).to_excel(writer, sheet_name='Exams', index=False)
        pd.DataFrame(config_data).to_excel(writer, sheet_name='Config', index=False)

    output.seek(0)
    return send_file(output, as_attachment=True, download_name='mock_exams_with_config.xlsx')

@application.route('/importMockExams', methods=['POST'])
def import_mock_exams():
    file = request.files.get('file')
    if not file:
        return jsonify({'success': False, 'message': 'No file uploaded'})

    try:
        xls = pd.read_excel(file, sheet_name=None)
        exams_df = xls.get('Exams')
        config_df = xls.get('Config')
        imported, skipped = 0, 0
        name_to_id = {}

        # Insert exams and build mapping from name to generated ID
        for _, row in exams_df.iterrows():
            exam_name = row['Name']
            exam_difficulty=row['Difficulty']
            if MockExam.query.filter_by(exam_name=exam_name).first():
                skipped += 1
                continue
            exam = MockExam(
                exam_name=exam_name,
                exam_difficulty=exam_difficulty,
                exam_duration=pd.to_timedelta(row['Duration']),
                general_instructions=row['Instructions']
            )
            db.session.add(exam)
            db.session.flush()  # to get the generated exam_id
            name_to_id[(exam_name, exam_difficulty)] = exam.exam_id
            imported += 1

        db.session.commit()

        # Now insert configs using exam name
        for _, row in config_df.iterrows():
            exam_name = row.get('MockExam Name')
            exam_difficulty = row.get('MockExam Difficulty')
            exam_id = name_to_id.get((exam_name, exam_difficulty))
            if not exam_id:
                continue
            db.session.add(MockExamConfig(
                exam_id=exam_id,
                subject_id=int(row['Subject ID']),
                q_diff=json.loads(row['Q_Diff'])
            ))

        db.session.commit()
        return jsonify({'success': True, 'imported': imported, 'skipped': skipped})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# endregion
          
if __name__ == '__main__':
    with application.app_context():
        db.create_all()
