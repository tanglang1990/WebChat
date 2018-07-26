import os
import tornado.web
import tornado.ioloop

BASE_DIR = os.path.dirname(__file__)


class BaseHandler(tornado.web.RequestHandler):
    pass


class HomeHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self, *args, **kwargs):
        self.write('home')


class LoginHandler(BaseHandler):
    def get(self, *args, **kwargs):
        self.render('login.html')


class RegisteHandler(BaseHandler):
    def get(self, *args, **kwargs):
        self.render('registe.html')


if __name__ == '__main__':
    handlers = [
        (r'/', HomeHandler),
        (r'/login', LoginHandler),
        (r'/registe', RegisteHandler)
    ]
    settings = dict(
        debug=True, autoreload=False,
        template_path=os.path.join(BASE_DIR, 'templates'),
        static_path=os.path.join(BASE_DIR, 'static'),
        login_url='/login'
    )
    application = tornado.web.Application(handlers=handlers, **settings)
    application.listen(8000)
    tornado.ioloop.IOLoop.instance().start()
