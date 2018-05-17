__author__ = 'Oleg Butovich'
__copyright__ = '(c) Oleg Butovich 2013-2017'
__licence__ = 'MIT'


from itertools import chain
import json
import re
import logging
import sys

logger = logging.getLogger(__name__)

class Response(object):
    def __init__(self, content, status_code):
        self.status_code = status_code
        self.content = content
        self.headers = {"content-type": "application/json"}


class ProxmoxBaseSSHSession(object):

    def _exec(self, cmd):
        raise NotImplementedError()

    # noinspection PyUnusedLocal
    def request(self, method, url, data=None, params=None, headers=None):
        method = method.lower()
        data = data or {}
        params = params or {}
        url = url.strip()

        cmd = {'post': 'create',
               'put': 'set'}.get(method, method)

        #for 'upload' call some workaround
        tmp_filename = ''
        if url.endswith('upload'):
            #copy file to temporary location on proxmox host
            tmp_filename, _ = self._exec(
                "python -c 'import tempfile; import sys; tf = tempfile.NamedTemporaryFile(); sys.stdout.write(tf.name)'")
            self.upload_file_obj(data['filename'], tmp_filename)
            data['filename'] = data['filename'].name
            data['tmpfilename'] = tmp_filename

        translated_data = ' '.join(["-{0} {1}".format(k, v) for k, v in chain(data.items(), params.items())])
        full_cmd = 'pvesh {0}'.format(' '.join(filter(None, (cmd, url, translated_data))))
        logger.info('BASE_SSH_COMMAND: %s', full_cmd)

        stdout, stderr = self._exec(full_cmd)
        match = lambda s: re.match('\d\d\d [a-zA-Z]', s)
        # sometimes contains extra text like 'trying to acquire lock...OK'
        status_code = next(
            (int(s.split()[0]) for s in stderr.splitlines() if match(s)),
            500)

        # more verbose error messages
        if status_code == 500:
            return Response(stderr, status_code)
        else:
            return Response(stdout, status_code)



    def format_lvm(self, lvm_name, filesystem = 'ext4'):
        #TODO: make this format safely, check that no vms are using this disk
        full_cmd = '/sbin/mkfs.{1} /dev/pve/{0}'.format(lvm_name, filesystem)
        logger.info('BASE_SSH_FORMAT_DISK_COMMAND: %s', full_cmd)

        stdout, stderr = self._exec(full_cmd)
        match = lambda s: re.match('\d\d\d [a-zA-Z]', s)
        # sometimes contains extra text like 'trying to acquire lock...OK'
        status_code = next(
            (int(s.split()[0]) for s in stderr.splitlines() if match(s)),
            500)

        # more verbose error messages
        if status_code == 500:
            return Response(stderr, status_code)
        else:
            return Response(stdout, status_code)

    def upload_file_obj(self, file_obj, remote_path):
        raise NotImplementedError()


class JsonSimpleSerializer(object):

    def loads(self, response):
        try:
            return json.loads(response.content)
        except ValueError:
            return response.content


class BaseBackend(object):

    def get_session(self):
        return self.session

    def get_base_url(self):
        return ''

    def get_serializer(self):
        return JsonSimpleSerializer()
