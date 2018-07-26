import os
import tornado.web
import tornado.ioloop

BASE_DIR = os.path.dirname(__file__)


class HomeHandler(tornado.web.RequestHandler):
    def get(self, *args, **kwargs):
        self.write('home')


if __name__ == '__main__':
    handlers = [(r'/', HomeHandler)]
    settings = dict(
        debug=True, autoreload=False,
        template_path=os.path.join(BASE_DIR, 'templates'),
        static_path=os.path.join(BASE_DIR, 'static'),
    )
    application = tornado.web.Application(handlers=handlers, **settings)
    application.listen(8080)
    tornado.ioloop.IOLoop.instance().start()
