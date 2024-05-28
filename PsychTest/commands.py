import os

import click
import json

from PsychTest import app, db
from PsychTest.models import User, PsychometricScale, Record, Question, Option


@app.cli.command('init-db')
@click.option('--drop', is_flag=True, help='删除后重新创建数据库')
def init_db(drop):
    """初始化数据库"""
    if drop:
        db.drop_all()
    db.create_all()
    click.echo('初始化数据库完成！')


@app.cli.command('init-scale')
@click.option('--file-question', prompt='题目文件',
              help='包含量表题目的JSON文件')  # click.File('r')表示以只读方式打开文件
@click.option('--file-option', prompt='选项文件', help='包含量表选项的JSON文件')
def init_scale(file_question, file_option):
    """
    初始化心理量表
    :param file_question: 包含量表题目的JSON文件
    :param file_option: 包含量表选项的JSON文件
    """
    question_path = os.path.join(app.root_path, 'static', 'scale_data', f"{file_question}.json")
    option_path = os.path.join(app.root_path, 'static', 'scale_data', f"{file_option}.json")
    with open(question_path, 'r', encoding='utf-8') as file_question, open(option_path, 'r',
                                                                           encoding='utf-8') as file_option:
        questions = json.load(file_question)
        options = json.load(file_option)
        print(questions)
        print(options)

    title = questions['title']
    category = questions['category']
    introduction = questions['introduction']
    score_info = questions['score_info']
    scale = PsychometricScale(title=title, category=category, introduction=introduction, score_info=score_info)
    db.session.add(scale)
    db.session.commit()
    content = questions['content']
    for question_index, question_content in content.items():
        content = question_content['question']
        is_reverse = bool(json.loads(question_content['is_reverse']))
        question = Question(content=content, is_reverse=is_reverse, scale_id=scale.id,
                            question_index=int(question_index))
        db.session.add(question)
        db.session.commit()

        for option_score, option_content in options.items():
            option = Option(content=option_content, score=int(option_score), question_id=question.id)
            db.session.add(option)
    db.session.commit()
    click.echo('初始化心理量表数据完成！')
    # print(type(scale.questions[0]))


@app.cli.command('del-scale')
@click.option('--scale', prompt='量表名称', help='要删除的量表名称')
def del_scale(scale):
    """删除心理量表"""
    scale = PsychometricScale.query.filter_by(title=scale).first()
    if scale:
        title = scale.title
        # 删除对应的问题和选项
        questions = Question.query.filter_by(scale_id=scale.id).all()
        for question in questions:
            options = Option.query.filter_by(question_id=question.id).all()
            for option in options:
                db.session.delete(option)
            db.session.delete(question)
        db.session.delete(scale)
        db.session.commit()
        click.echo(f'删除{title}心理量表数据完成！')
    else:
        click.echo('未找到该心理量表！')
