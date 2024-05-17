import os

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from PsychTest import db, app


class User(db.Model, UserMixin):
    """用户模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    avatar = db.Column(db.String(120))

    records = db.relationship('Record', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def save(self):
        db.session.add(self)
        db.session.commit()


class PsychometricScale(db.Model):
    """心理量表模型"""
    __tablename__ = 'psychometric_scale'  # 指定表名
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(20), nullable=False)
    introduction = db.Column(db.Text)
    score_info = db.Column(db.Text)
    # 添加限制条件，将 dbsql.CheckConstraint 检查约束放置在 __table_args__ 元组中
    __table_args__ = (db.CheckConstraint(
        "category IN ('抑郁症','智商','情商','强迫症','焦虑症','躁狂症','躁郁症','恐惧症','心理综合','其它')"),)
    # 添加属性，通过relationship和backref实现双向访问
    questions = db.relationship('Question', backref='scale', lazy=True)


class Question(db.Model):
    """题目模型"""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    is_reverse = db.Column(db.Boolean, default=False)
    scale_id = db.Column(db.Integer, db.ForeignKey('psychometric_scale.id'), nullable=False)
    question_index = db.Column(db.Integer, nullable=False)
    # scale = db.relationship('PsychometricScale', backref='questions')
    options = db.relationship('Option', backref='question', lazy='dynamic')
    records = db.relationship('Record', backref='question', lazy=True)


class Option(db.Model):
    """选项模型"""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)


class Record(db.Model):
    """填写记录模型"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    scale_id = db.Column(db.Integer, db.ForeignKey('psychometric_scale.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    # option_id = db.Column(db.Integer, db.ForeignKey('option.id'), nullable=False)
    selected_option_score = db.Column(db.Integer, nullable=False)
    # 精确到分钟的时间戳，在插入数据时使用 datetime.datetime.now() 获取当前时间
    # index=True 为该列创建索引，提高查询效率
    update_time = db.Column(db.DateTime, index=True, default=db.func.now(), nullable=False)
