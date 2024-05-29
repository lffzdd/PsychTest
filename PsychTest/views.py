import os
from datetime import datetime

from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import logout_user, login_required, current_user, login_user
from werkzeug.exceptions import BadRequestKeyError
from werkzeug.utils import secure_filename

from PsychTest import app, db
from PsychTest.models import User, PsychometricScale, Record, Question


@app.route('/')
@app.route('/index')
def index():
    """主页"""
    # 获取所有心理测量量表
    scales = PsychometricScale.query.all()
    return render_template('index.html', scales=scales)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """注册页面"""
    if request.method == 'POST':
        if request.form['action'] == 'register':
            username = request.form['username']
            password = request.form['password']
            # 若数据库中已有该用户名，则返回错误
            if User.query.filter_by(username=username).first():
                flash('用户名已存在，请重新输入！', 'error')
                return redirect(url_for('register'))

            if not username or not password or len(username) > 20 or len(password) < 6 or len(password) > 20:
                flash('输入无效，请确保用户名不为空，密码在6到20个字符之间。', 'error')
                return redirect(url_for('register'))

            user = User(username=username)
            user.set_password(password)
            user.save()
            flash('注册成功！')
            return redirect(url_for('login'))
    return render_template('login_register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        if request.form['action'] == 'login':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                flash('登录成功！')
                return redirect(url_for('index'))

            flash('用户名或密码错误，请重新登录！')

    return render_template('login_register.html')


@app.route('/logout')
@login_required
def logout():
    """退出登录"""
    logout_user()
    flash('退出登录！')

    return redirect(url_for('index'))


@app.route('/<string:username>/settings', methods=['GET', 'POST'])
@login_required
def settings(username):
    """设置页面"""
    user = User.query.get(current_user.id)
    # 获得头像的url，若没有则使用默认头像
    avatar_url = user.avatar if user.avatar else url_for('static', filename='images/avatars/default.jpg')
    if request.method == 'POST':
        # 用户名和密码
        if 'action' not in request.form:
            username = request.form['username']
            password = request.form['password']
            if not username or len(username) > 20 or len(password) < 6 or len(password) > 20:
                flash('用户名不能为空，密码长度为6-20！')
                return redirect(url_for('settings', username=user.username))
            user.username = username
            user.set_password(password)
            user.save()
        # 头像
        if 'avatar' in request.files:
            file = request.files['avatar']
            # 如果头像大于5MB，返回错误
            if file.content_length > 5 * 1024 * 1024:
                flash('头像文件过大，请上传小于5MB的文件！', 'error')
                return redirect(url_for('settings', username=user.username))
            if file.filename != '':
                filename = secure_filename(f'{user.id}_{user.username}.jpg')
                file_path = os.path.join(app.config['UPLOAD_FOLDER_AVATAR'], filename)
                app.logger.debug(f'Saving file to: {file_path}')
                file.save(file_path)
                user.avatar = url_for('static', filename=f'images/avatars/{filename}')
                user.save()
                flash('头像上传成功！')
            # return redirect(url_for('settings', username=user.username, avatar_url=user.avatar))
            return render_template('settings.html', avatar_url=user.avatar)

        flash('修改成功！')

    return render_template('settings.html', avatar_url=avatar_url)


@app.route('/cancel', methods=['POST'])
@login_required
def cancel():
    """注销页面"""
    user = User.query.get(current_user.id)
    db.session.delete(user)
    db.session.commit()
    logout_user()
    flash('注销成功！')
    return redirect(url_for('index'))


@app.route('/index/psychometry/<int:scale_id>', methods=['GET', 'POST'])
def psychometry(scale_id):
    """心理测量页面"""
    scale = PsychometricScale.query.get_or_404(scale_id)
    # 将题目和选项提取出来，加上编号，方便在模板中使用
    question_table = scale.questions
    questions = [question.content for question in question_table]  # 获取题目内容
    print(f'question_table:{question_table}')
    questions = list(enumerate(questions, 1))  # 加上编号
    options = question_table[0].options  # 心理量表各个题目的选项都是一样的，所以只需要提取一个题目的选项即可
    options = list(enumerate(options, 1))  # 由于选项是一个对象，所以需要加上编号

    selected_options_score = {}  # 保存用户选择的选项
    scores = 0
    is_finished = False

    if request.method == 'POST':
        ans_num = 0
        max_score = max([option.score for option in question_table[0].options])
        for i in range(1, len(question_table) + 1):
            if str(i) in request.form:
                # 若答了题，计数
                value = int(request.form[str(i)])
                selected_options_score[i] = value

                if question_table[i - 1].is_reverse:  # 如果是反向题目，选项值越小，分数越高，最大score可查询选项表
                    value = max_score - value
                scores += value
                ans_num += 1
        # 若全部题目都已答完，计算结果
        if ans_num == len(questions):
            is_finished = True
            flash('您的得分为：' + str(scores))
        else:
            # 设置确认框，确认后flash消息消失
            flash('测试未完成！', 'error')
            # 若已登录，保存记录
        if current_user.is_authenticated:
            for question_index, question in enumerate(question_table, 1):
                value = selected_options_score.get(question_index)
                if value is not None:
                    record = Record.query.filter_by(user_id=current_user.id, scale_id=scale_id,
                                                    question_id=question.id).first()

                    if record:  # 若用户已经回答过该题目，则更新记录
                        record.selected_option_score = value
                        record.update_time = datetime.now().replace(microsecond=0)
                    else:  # 若用户未回答过该题目，则新建记录
                        record = Record(user_id=current_user.id, scale_id=scale_id, question_id=question.id,
                                        selected_option_score=value)
                        db.session.add(record)
            db.session.commit()
            flash('记录已保存！')

            # 不用redirect，因为需要保留用户的选择
        return render_template('psychometry.html', scale=scale, questions=questions, options=options,
                               selected_options_score=selected_options_score, is_finished=is_finished, score=scores)

    return render_template('psychometry.html', scale=scale, questions=questions, options=options,
                           selected_options_score=selected_options_score, is_finished=is_finished, scores=scores)


@app.route('/<string:username>/history')
@login_required
def history(username):
    """历史记录页面，显示当前用户填写过的心理量表，但不显示具体答题情况"""
    scales = db.session.query(Record.scale_id).filter(Record.user_id == current_user.id).distinct().all()
    scale_ids = [scale_id for scale_id, in scales]
    scales = PsychometricScale.query.filter(PsychometricScale.id.in_(scale_ids)).all()
    return render_template('index.html', scales=scales, is_history=True)


@app.route('/<string:username>/history/<int:scale_id>', methods=['GET', 'POST'])
@login_required
def history_scale(username, scale_id):
    """显示用户填写过的心理量表的具体答题情况"""
    scale = PsychometricScale.query.get_or_404(scale_id)
    questions = [question.content for question in scale.questions]
    options = scale.questions[0].options
    questions = list(enumerate(questions, 1))
    options = list(enumerate(options, 1))
    selected_options_score = {}
    scores = 0
    max_score = max([option.score for option in scale.questions[0].options])
    is_finished = False
    # 按照题目编号将用户选择的选项提取出来
    records = Record.query.filter_by(user_id=current_user.id, scale_id=scale_id).all()
    # 获取最近更新的时间，即update_time最大的记录
    updated_time = '尚未填写过'
    if records:
        updated_time = max(record.update_time for record in records)

    # selected_options_score[question_index] = record.selected_option
    # 如果答完了，即所有题目都有记录，selected_options_score中会有所有题目的选项
    if len(records) == len(questions):
        is_finished = True

    for record in records:
        question_index = record.question.question_index
        selected_options_score[question_index] = record.selected_option_score
        if is_finished:
            value = record.selected_option_score
            if record.question.is_reverse:
                value = max_score - value
            scores += value

    # 若用户点击保存按钮，更新记录并跳转到心理量表页面
    if request.method == 'POST':
        scores = 0
        for question_index in range(1, len(questions) + 1):
            # 通过question_index获取题目
            # question = scale.questions.filter_by(question_index=question_index).first()
            question = Question.query.filter_by(scale_id=scale_id, question_index=question_index).first()
            if str(question_index) in request.form:  # 如果表单中有该题目的选项值，从表单中获取选项值
                value = int(request.form[str(question_index)])
                selected_options_score[question_index] = value

                # 更新记录
                record = Record.query.filter_by(user_id=current_user.id, scale_id=scale_id,
                                                question_id=question.id).first()
                if record:
                    record.selected_option_score = value
                    record.update_time = datetime.now().replace(microsecond=0)
                else:
                    record = Record(user_id=current_user.id, scale_id=scale_id, question_id=question.id,
                                    selected_option_score=value)
                    db.session.add(record)
            else:  # 如果表单中没有该题目的选项值，从数据库中获取选项值
                value = selected_options_score.get(question_index)

            if value is None:  # 如果表单和数据库中都没有该题目的选项值，则跳过
                value = 0

            # 计算分数
            if value != 0 and question.is_reverse:
                value = max_score - int(value)
            scores += value

        db.session.commit()
        flash('记录已保存！')
        if len(selected_options_score) == len(questions):
            is_finished = True
            flash('您的得分为：' + str(scores))
        return render_template('psychometry.html', scale=scale, questions=questions, options=options,
                               selected_options_score=selected_options_score, is_finished=is_finished, scores=scores)

    return render_template('psychometry.html', scale=scale, questions=questions, options=options,
                           selected_options_score=selected_options_score, is_finished=is_finished, scores=scores,
                           is_history=True,
                           updated_time=updated_time)


@app.errorhandler(BadRequestKeyError)
def handle_bad_request_key_error(error):
    return jsonify({'error': 'Bad Request', 'message': str(error)}), 400


@app.route('/base')
def base():
    return render_template('base.html')
