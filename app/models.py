from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from . import login_manager
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request, url_for
from datetime import datetime
import hashlib
import bleach
from markdown import markdown
from .exceptions import ValidationError


class Permission:
    # 权限常亮
    FOLLOW = 0x01   # 关注
    COMMENT = 0x02  # 评论
    WRITE_ARTICLES = 0x04   # 写文章
    MODERATE_COMMENTS = 0x08    # 管理评论
    ADMINISTER = 0x80   # 管理员


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(64),unique=True)
    # default 为 true 时表示为普通用户
    default = db.Column(db.Boolean,default=False,index=True)    # index 如果设置为true表示为这列创建缩影，提升查询效率
    # permissions 表示权限，当允许某个操作时，该数的某一位会被置一，比如0x01表示允许关注其他用户
    permissions = db.Column(db.Integer)
    # 定义关系，users 属性代表这个关系的面向对象视角。对于一个 Role 类的实例，其 users 属性将返回与角色相关联的用户组成的列表
    users = db.relationship('User',backref='role',lazy='dynamic')
    # dynamic 禁止执行自动查询

    # 将角色添加到数据库中
    @staticmethod
    def insert_roles():
        roles = {
            # 普通用户
            'User': (Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.WRITE_ARTICLES, True),
            # 协管员
            'Moderator': (Permission.FOLLOW |
                          Permission.COMMENT |
                          Permission.WRITE_ARTICLES |
                          Permission.MODERATE_COMMENTS, False),
            # 管理员
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()


    def __repr__(self):
        return '<Role %r>' % self.name


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True,default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    body_html = db.Column(db.Text)  # Markdown文本的HTML缓存
    comments = db.relationship('Comment', backref='post', lazy='dynamic')

    # 生成虚拟文章
    @staticmethod
    def generate_fake(count=100):
        from random import seed, randint
        import forgery_py
        seed()
        user_count = User.query.count()
        for i in range(count):
            u = User.query.offset(randint(0, user_count - 1)).first()
            p = Post(body=forgery_py.lorem_ipsum.sentences(randint(1, 5)),
                     timestamp=forgery_py.date.date(True),
                     author=u)
            db.session.add(p)
            db.session.commit()

    # 处理Markdown文本
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        # linkify 把纯文本中的URL转换成适当的<a>链接，由 bleach 提供
        # markdown将Markdown 转为 HTML
        # clean 清除不允许的标签
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    # 把文章转换成JSON格式的序列化字典
    def to_json(self):
        json_post={
            'url': url_for('api.get_post', id=self.id, _external=True),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author': url_for('api.get_user', id=self.author_id, _external=True),
            'comments': url_for('apt.get_post_comments', id=self.id, _external=True),
            'comment_count': self.comments.count()
        }
        return json_post

    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('post does not have a body')
        return Post(body=body)

# on_changed_body 函数注册在 body 字段上，是 SQLAlchemy“ set”事件的监听程序，
# 这意味着只要这个类实例的 body 字段设了新值，函数就会自动被调用
db.event.listen(Post.body, 'set', Post.on_changed_body)


class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer,db.ForeignKey('users.id'),   # 关注者
                            primary_key=True)
    followed_id = db.Column(db.Integer,db.ForeignKey('users.id'),   # 被关注者
                            primary_key=True)
    timestamp = db.Column(db.DateTime,default=datetime.utcnow)  # 关注日期


class User(UserMixin,db.Model):
    # FlaskLogin 提供了一个 UserMixin 类,实现了giant拓展要求的大部分函数
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64),unique=True,index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))  # 定义外键
    confirmed = db.Column(db.Boolean, default=False)    # 用户是否验证
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))     # 所在地
    about_me = db.Column(db.Text())     # 个人简介，Text类型不需要指定长度
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)    # 注册时间，utcnow是一个函数
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)    # 最后访问时间
    avatar_hash = db.Column(db.String(32))      # 用户Gravatar头像hash值
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    # 使用两个一对多关系实现的多对多关系
    # 注意，为了消除外键间的歧义， 定义关系时必须使用可选参数 foreign_keys 指定的外键。
    # 而且，db.backref()参数并不是指定这两个关系之间的引用关系，而是回引 Follow 模型。

    # 关注的人
    followed = db.relationship('Follow', foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic', cascade='all,delete-orphan')
    # 关注该用户的用户
    followers = db.relationship('Follow', foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic', cascade='all,delete-orphan')

    # 生成虚拟用户
    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(True),
                     password=forgery_py.lorem_ipsum.word(),
                     confirmed=True,
                     name=forgery_py.name.full_name(),
                     location=forgery_py.address.city(),
                     about_me=forgery_py.lorem_ipsum.sentence(),
                     member_since=forgery_py.date.date(True))
            db.session.add(u)
            try:
                db.session.commit()
                # 生成的用户重复，回滚
            except IntegrityError:
                db.session.rollback()

    # 添加测试数据
    @staticmethod
    def add_test_user():
        from sqlalchemy.exc import IntegrityError
        import forgery_py
        admin = User(email=current_app.config['FLASKY_ADMIN'],
                     username='admin',
                     password='admin',
                     confirmed=True,
                     name='root',
                     location=forgery_py.address.city(),
                     about_me=forgery_py.lorem_ipsum.sentence(),
                     member_since=forgery_py.date.date(True))
        test = User(email='605518519@qq.com',
                     username='test',
                     password='test',
                     confirmed=True,
                     name='test',
                     location=forgery_py.address.city(),
                     about_me=forgery_py.lorem_ipsum.sentence(),
                     member_since=forgery_py.date.date(True))

        moderator = User(email='moderator@qq.com',
                    username='moderaor',
                    password='test',
                    confirmed=True,
                    name='moderator',
                    location=forgery_py.address.city(),
                    about_me=forgery_py.lorem_ipsum.sentence(),
                    member_since=forgery_py.date.date(True))

        db.session.add(admin)
        db.session.add(test)
        db.session.add(moderator)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

    # 更新数据库使得用户自己关注自己
    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    def __init__(self, **kwargs):
        # 赋予角色
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:    # 判断是否是管理员
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.email == current_app.config['FLASKY_MODERATOR']:
                self.role = Role.query.filter_by(permissions=0x0f).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            # 计算用户头像的hash值并存入数据库
            self.avatar_hash = hashlib.md5(
                self.email.encode('utf-8')).hexdigest()
        self.followed.append(Follow(followed=self))

    # @property将password方法变成一个属性p
    @property
    def password(self):
        # password 是一个只读属性
        raise AttributeError('password is not a readable attribute')

    # @password.setter用于给password赋值
    @password.setter
    def password(self,password):
        # generate_password_hash将原始密码作为输入，以字符串形式输出密码的散列值， 输出的值可保存在用户数据库中
        self.password_hash = generate_password_hash(password)

    # check_password_hash的参数是从数据库中取回的密码散列值和用户输入的密码。返回值为 True 表明密码正确
    def verify_password(self,password):
        return check_password_hash(self.password_hash,password)

    # 用于生成令牌
    def generate_confirmation_token(self,expiration=3600):
        s= Serializer(current_app.config['SECRET_KEY'],expiration)
        #dumps() 方法为指定的数据生成一个加密签名，然后再对数据和签名进行序列化，生成令牌字符串。
        #expiration 参数设置令牌的过期时间，单位为秒
        return s.dumps({'confirm':self.id})

    # 验证注册令牌
    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            #loads用于解码令牌，参数是令牌字符串，如果正确且没有过期则通过
            data=s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return  False
        self.confirmed = True   #验证通过
        db.session.add(self)    #在数据库中添加用户
        return True

    # 生成重设密码的令牌，用于邮箱验证
    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    # 修改密码
    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    # 生成修改邮箱令牌
    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    # 修改邮箱
    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        return True

    # 检查用户是否有指定的权限
    def can(self, permissions):
        return self.role is not None and \
            (self.role.permissions & permissions) == permissions

    # 检查是否有管理员权限
    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    # 刷新用户最后的访问时间
    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    # 生成用户邮箱对应的gravatar头像地址hash值，size 为图片大小，rating 表示图片级别，可选值有 "g"、 "pg"、 "r" 和 "x"，
    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        # 如果数据库中没有 hash 则重新计算
        hash = self.avatar_hash or hashlib.md5(self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
                url=url, hash=hash, size=size, default=default, rating=rating)

    # 关注用户
    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    # 取消关注
    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    # 是否关注某个用户
    def is_following(self, user):
        return self.followed.filter_by(
            followed_id=user.id).first() is not None

    # 是否被某个用户关注
    def is_followed_by(self, user):
        return self.follower.filter_by(
            follower_id=user.id).first() is not None

    # 获取所关注用户的文章，先执行连结操作再过滤
    # @property表示将方法定义为属性，调用时不用加（）
    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id) \
            .filter(Follow.follower_id == self.id)

    # 用于基于令牌的认证
    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dump({'id': self.id})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.load(token)
        except:
            return None
        return User.query.get(data['id'])

    # 将用户转换为JSON字典
    def to_json(self):
        json_user = {
            'url': url_for('api.get_user', id=self.id, _external=True),
            'username': self.username,
            'member_since': self.member_since,
            'last_seen': self.last_seen,
            'posts': url_for('api.get_user_posts', id=self.id, _external=True),
            'followed_posts': url_for('api.get_user_followed_posts',
                                      id=self.id, _external=True),
            'post_count': self.posts.count()
        }
        return json_user

    def __repr__(self):
        return '<User %r>' % self.username


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
                        'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    @staticmethod
    def generate_fake(count=100):
        from random import seed, randint
        import forgery_py

        seed()
        user_count = User.query.count()
        for i in range(count):
            u = User.query.offset(randint(0, user_count - 1)).first()
            p = Post.query.offset(randint(0, user_count - 1)).first()
            comment = Comment(body=forgery_py.lorem_ipsum.sentences(randint(1, 5)),
                              timestamp=forgery_py.date.date(True),
                              author=u,
                              post=p)
            db.session.add(comment)
            db.session.commit()

db.event.listen(Comment.body, 'set', Comment.on_changed_body)


# 匿名用户，用户未登录时 current_user 的值，这样用户未登录的时候也可以调用 can 和 is_administrator
class AnonymousUser(AnonymousUserMixin):
    def can(self,permissions):
        return False

    def is_administrator(self):
        return False

# 设置程序的匿名用户
login_manager.anonymous_user = AnonymousUser


# Flask-Login 要求程序实现一个回调函数，使用指定的标识符加载用户
@login_manager.user_loader
def load_user(user_id):
    # 使用指定的标识符加载用户
    return User.query.get(int(user_id)) #加载用户的回调函数接收以 Unicode 字符串形式表示的用户标识符























