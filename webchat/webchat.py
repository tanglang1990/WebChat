import os
import logging

import bcrypt
import tornado.web
import tornado.ioloop
import tornado.gen
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


class BaseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        return self.get_secure_cookie(USER_COOKIE_KEY)

    @tornado.gen.coroutine
    def get_current_user_dict(self):
        if not self.current_user:
            return None
        else:
            user_dict = yield POOL.execute('select * from users where email = %s', self.current_user)
            return user_dict.fetchone()


class HomeHandler(BaseHandler):

    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self, *args, **kwargs):
        user_dict = yield self.get_current_user_dict()
        print(user_dict)
        self.write(user_dict)


class LoginHandler(BaseHandler):

    def initialize(self):
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
            self.render(self.template_name, error="Incorrect Password")


class RegisteHandler(BaseHandler):
    def get(self, *args, **kwargs):
        self.render('registe.html', error=None)

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
            self.render("registe.html", error='Error input infomation')
            return

        if await self.is_email_user_exists(email):
            is_existed = self.locale.translate('is existed')
            self.render("create_user.html",
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


if __name__ == '__main__':
    handlers = [
        (r'/', HomeHandler),
        (r'/login', LoginHandler),
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
    application = tornado.web.Application(handlers=handlers, **settings)
    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
