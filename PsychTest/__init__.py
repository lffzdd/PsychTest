import sys, os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# 兼容操作系统
WIN = sys.platform.startswith('win')
if WIN:  # 如果是Windows系统，使用三个斜杠
    prefix = 'sqlite:///'
else:
    prefix = 'sqlite:////'

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))
app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(os.path.dirname(app.root_path),
                                                              os.getenv('DATABASE_FILE', 'scale_data.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 取消数据库对对象修改的追踪，减少不必要的开销
# app.config['UPLOAD_AVATAR'] = os.path.join(app.static_folder, 'images', 'avatars')  # 上传头像路径
app.config['UPLOAD_FOLDER_AVATAR'] = os.path.join(app.static_folder, 'images', 'avatars')  # 上传头像路径
if not os.path.exists(app.config['UPLOAD_FOLDER_AVATAR']):
    os.makedirs(app.config['UPLOAD_FOLDER_AVATAR'])

os.makedirs(app.config['UPLOAD_FOLDER_AVATAR'], exist_ok=True)  # 确保1.文件夹存在 2.不会抛出异常
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # 添加@required装饰器后未登录用户访问页面重定向到 login 界面
login_manager.login_message = '请登录账号！'


@login_manager.user_loader
def load_user(user_id):
    from PsychTest.models import User
    return User.query.get(int(user_id))


@app.context_processor
def inject_user():  # 传入用户id
    """上下文处理器，返回当前登录用户对象"""
    from flask_login import current_user
    return dict(user=current_user)


from PsychTest import commands, errors, views
