import os
import logging

import bcrypt
import tornado.web
import tornado.ioloop
import tornado.gen
import tornado.websocket
from tornado.options import define, options
from tornado_mysql import pools
from tornado_mysql.cursors import DictCursor

from utils import save_flie_async

define("port", default=8000, help="run on the given port", type=int)
define("db_host", default="192.168.222.10", help="blog database host")
define("db_port", default=3306, help="blog database port")
define("db_database", default="testdb", help="blog database name")
define("db_user", default="root", help="blog database user")
define("db_password", default="Ten123456@", help="blog database password")
tornado.options.parse_command_line()

ConnParm = {'host': options.db_host, 'port': options.db_port,
            'user': options.db_user, 'password': options.db_password,
            'db': options.db_database, 'charset': 'utf8',
            'cursorclass': DictCursor}
POOL = pools.Pool(ConnParm, max_idle_connections=1, max_recycle_sec=3)
BASE_DIR = os.path.dirname(__file__)
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '\media'
USER_COOKIE_KEY = 'userkey'


class BaseHandler:
    def initialize(self):
        self.current_user_dict = None

    def get_current_user(self):
        return self.get_secure_cookie(USER_COOKIE_KEY)

    @tornado.gen.coroutine
    def get_current_user_dict(self, with_password=False):
        if self.current_user_dict:
            return self.current_user_dict
        elif not self.current_user:
            return None
        else:
            sql = 'select * from users where email = %s' if with_password else 'select id, nickname, email, head_img  from users where email = %s'
            cursor = yield POOL.execute(sql, self.current_user)
            self.current_user_dict = cursor.fetchone()
            return self.current_user_dict


class CommonBaseHandler(BaseHandler, tornado.web.RequestHandler):
    pass


class HomeHandler(CommonBaseHandler):

    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self, *args, **kwargs):
        user_dict = yield self.get_current_user_dict()
        self.render('home.html', error=None)


class LoginHandler(CommonBaseHandler):

    def initialize(self, *args, **kwargs):
        self.template_name = 'login.html'

    def get(self, *args, **kwargs):
        self.render(self.template_name, error=None)

    async def post(self, *args, **kwargs):
        email = self.get_argument('email')
        password = self.get_argument('password')

        # 数据校验
        if not email or not password:
            self.render(self.template_name, error='Error input infomation')
            return

        cursor = await POOL.execute(
            "SELECT id, nickname, email, password FROM users WHERE email = %s",
            email)
        if cursor.rowcount == 0:
            self.render(self.template_name, error="Email or password error")
            return

        # 验证密码
        user_dict = cursor.fetchone()
        user_password = user_dict.get('password')
        hashed_password = await tornado.ioloop.IOLoop.current().run_in_executor(
            None, bcrypt.hashpw, tornado.escape.utf8(password),
            tornado.escape.utf8(user_password))
        hashed_password = tornado.escape.to_unicode(hashed_password)
        if hashed_password == user_password:
            self.set_secure_cookie(USER_COOKIE_KEY, email)
            self.redirect(self.get_argument("next", "/"))
        else:
            self.render(self.template_name, error="Email or password error")


class LogoutHandler(CommonBaseHandler):
    def get(self):
        self.clear_cookie(USER_COOKIE_KEY)
        self.redirect('/')


class RegisteHandler(CommonBaseHandler):

    def initialize(self):
        self.template_name = 'registe.html'

    def get(self, *args, **kwargs):
        self.render(self.template_name, error=None)

    async def is_email_user_exists(self, email):
        cursor = await POOL.execute('SELECT * FROM users where email =%s',
                                    email)
        return cursor.rowcount > 0

    async def post(self, *args, **kwargs):
        email = self.get_argument('email')
        password = self.get_argument('password')
        nickname = self.get_argument('nickname')
        req_files = self.request.files.get('head_img', [])

        # 数据校验
        if not email or not password or len(req_files) == 0:
            self.render(self.template_name, error='Error input infomation')
            return

        if await self.is_email_user_exists(email):
            is_existed = self.locale.translate('is existed')
            self.render(self.template_name,
                        error="%s %s" % (email, is_existed))
            return

        head_img_meta = req_files[0]
        head_img = await save_flie_async(MEDIA_ROOT, head_img_meta)
        head_img_url = os.path.join(MEDIA_URL, head_img)

        hashed_password = await tornado.ioloop.IOLoop.current().run_in_executor(
            None, bcrypt.hashpw, tornado.escape.utf8(password),
            bcrypt.gensalt())

        await POOL.execute(
            "INSERT INTO users (email, password, nickname, head_img) VALUES (%s, %s, %s, %s)",
            (email, hashed_password, nickname, head_img_url))

        self.set_secure_cookie(USER_COOKIE_KEY, email)
        self.redirect(self.get_argument("next", "/"))


class ChatHandler(BaseHandler, tornado.websocket.WebSocketHandler):
    # 存放所有的socket连接
    waiters = set()
    # 存放消息
    cache = []
    # 存放最大的消息记录数
    cache_size = 200

    # 创建连接时触发
    async def open(self):
        ChatHandler.waiters.add(self)
        # 将用户id发给前端
        user_dict = await self.get_current_user_dict()
        self.write_message(str(user_dict.get('id')))
        # 将历史消息发给前端
        for msg in ChatHandler.cache:
            self.write_message(msg)

    # 收到消息是触发
    async def on_message(self, message):
        user_dict = await self.get_current_user_dict()
        msg = {'user': user_dict, 'content': message}
        ChatHandler.update_cache(msg)
        ChatHandler.send_updates(msg)

    # 更新消息记录
    @classmethod
    def update_cache(cls, chat):
        cls.cache.append(chat)
        if len(cls.cache) > cls.cache_size:
            cls.cache = cls.cache[-cls.cache_size:]

    # 发送消息给所有用户
    @classmethod
    def send_updates(cls, msg):
        logging.info("sending message to %d waiters", len(cls.waiters))
        for waiter in cls.waiters:
            try:
                waiter.write_message(msg)
            except:
                logging.error("Error sending message", exc_info=True)

    # 断开连接时触发
    def on_close(self):
        ChatHandler.waiters.remove(self)


if __name__ == '__main__':
    handlers = [
        (r'/', HomeHandler),
        (r'/chat', ChatHandler),
        (r'/login', LoginHandler),
        (r'/logout', LogoutHandler),
        (r'/registe', RegisteHandler),
        (r'/media/(.*)', tornado.web.StaticFileHandler, {'path': os.path.join(BASE_DIR, 'media')})
    ]
    settings = dict(
        debug=True,
        autoreload=False,
        template_path=os.path.join(BASE_DIR, 'templates'),
        static_path=os.path.join(BASE_DIR, 'static'),
        login_url='/login',
        cookie_secret='TODO random a cookie_secret'
    )

    tornado.locale.load_translations(os.path.join(BASE_DIR, 'locales'))
    tornado.locale.set_default_locale('en')

    application = tornado.web.Application(handlers=handlers, **settings)
    application.listen(options.port)
    logging.info(f'application port is {options.port}')
    tornado.ioloop.IOLoop.instance().start()
