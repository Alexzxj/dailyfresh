from fdfs_client.client import Fdfs_client
from django.core.files.storage import Storage
from django.conf import settings
import os


class FDFSStorage(Storage):
    def __init__(self, FDFS_CONFIG=None, NGINX_URL=None):
        if FDFS_CONFIG == None:
            FDFS_CONFIG = settings.FDFS_CONFIG_PATH
        self.fdfs_config = FDFS_CONFIG

        if NGINX_URL == None:
            NGINX_URL = settings.NGINX_URL_PATH
        self.nginx_url = NGINX_URL

    def _open(self, name, mode='rb'):
        pass

    def _save(self, name, content):
        # 初始化创建ｃｌｉｅｎｔ对象
        client = Fdfs_client(self.fdfs_config)
        content = content.read()
        # {
        #     'Group name': group_name,
        #     'Remote file_id': remote_file_id,
        #     'Status': 'Upload successed.',
        #     'Local file name': '',
        #     'Uploaded size': upload_size,
        #     'Storage IP': storage_ip
        # }
        res = client.upload_by_buffer(content)

        if res.get('Status') != 'Upload successed.':
            # 上传文件失败
            raise Exception('上传文件失败')
        file_id = res.get('Remote file_id')
        return file_id

    def exists(self, name):
       return False

    def url(self, name):
        # 这里返回的一定是ｎｇｉｎｘ服务器的端口
        return self.nginx_url + name