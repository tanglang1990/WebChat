import hashlib
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import tornado.ioloop
import tornado.gen

thread_pool = ThreadPoolExecutor(4)


def save_md5_file(upload_path, file_meta):
    '''
    通过文件的md5值保存文件，这样可以确保文件的唯一性，节省了空间
    '''
    os.makedirs(upload_path, exist_ok=True)
    filename, content_type, body = file_meta['filename'], \
                                   file_meta['content_type'], \
                                   file_meta['body']

    file_ext = filename.split('.')[-1]
    store_filename = os.path.join(upload_path,
                                  '{}.{}'.format(uuid.uuid1(), file_ext))
    m = hashlib.md5()
    with open(store_filename, 'wb') as f:
        f.write(body)
        m.update(body)
    fmd5 = m.hexdigest()
    md5_filename = f'{fmd5}.{file_ext}'
    store_md5_filename = os.path.join(upload_path, md5_filename)
    try:
        os.renames(store_filename, store_md5_filename)
    except FileExistsError:
        # 如果文件已存在说明文件重复了，可以将之前的文件删除掉
        os.remove(store_filename)
    return md5_filename


@tornado.gen.coroutine
def save_flie_async(uploda_path, img_meta):
    ret = yield thread_pool.submit(save_md5_file, uploda_path, img_meta)
    return ret


@tornado.gen.coroutine
def test_save_file():
    uploda_path = os.path.join(os.path.dirname(__file__), 'media')
    file_meta = {'filename': 'aa.txt', 'content_type': 'aa/text', 'body': b'3fe'}
    r = yield save_flie_async(uploda_path, file_meta)
    print(r)


if __name__ == '__main__':
    ## 测试同步保存
    # uploda_path = os.path.join(os.path.dirname(__file__), 'media')
    # file_meta = {'filename': 'aa.txt', 'content_type': 'aa/text', 'body': b'eee'}
    # # save_md5_img(uploda_path, file_meta)

    ## 测试异步保存
    tornado.ioloop.IOLoop.current().run_sync(test_save_file)
