

DOCUMENTATION = '''
---
module: ovm_repo_present
short_description: This module will present/unpresent an OVM repo to/from a OVM server
description:
  - Module to manage OVM repository presentation
Author: "Court Campbell"
notes:
    - This module works with OVM 3.3 and 3.4
    - Set hosts in your playbook to the OVM Manager server
requirements:
    - requests package
options:
    server:
        description:
            - The OVM server to which you want to present/unpresent the repo
        required: True
    ovm_user:
        description:
            - The OVM admin-user used to connect to the OVM-Manager.
        required: True
    ovm_pass:
        description:
            - The password of the OVM admin-user.
        required: True
    repository:
        description:
            - The OVM repository you want to present/unpresent
        required: True
'''

EXAMPLES = '''
- name: Present 'Repo1' to 'example_host'
  ovm_repo_present:
    server: 'example_host'
    ovm_user: 'admin'
    ovm_pass: 'password'
    repository: 'Repo1'
    state: 'presented'

- name: Present 'Repo1' to many hosts
  ovm_repo_present:
    server: {{ item }}
    ovm_user: 'admin'
    ovm_pass: 'password'
    repository: 'Repo1'
    state: 'presented'
  with_items:
    - "host 1"
    - "host 2"
    - "host 3"
'''

RETURN = '''
name:
  description:
    - The OVM Manager server you ran commands on
'''

WANT_JSON = ''

#==============================================================
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

#==============================================================
def auth(ovm_user, ovm_pass):
    """ Set authentication-credentials.

    Oracle-VM usually generates a self-signed certificate,
    this is why we disable certificate-validation.

    Set Accept and Content-Type headers to application/json to
    tell Oracle-VM we want json, not XML.
    """
    session = requests.Session()
    session.auth = (ovm_user, ovm_pass)
    session.verify = False
    session.headers.update({
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    })
    return session

#==============================================================
class OVMRestClient:

    def __init__(self, base_uri, session):
        self.session = session
        self.base_uri = base_uri


    def get_presented_servers(self, repositoryId):
        presented_servers = []
        response = self.session.get(
            self.base_uri+'/Repository/'+repositoryId['value']
        )
        for server in response.json()['presentedServerIds']:
            presented_servers.append(server['name'])
        return presented_servers

    
    def unpresent_repo(self, repositoryId, data):
        response = self.session.put(
            self.base_uri+'/Repository/'+repositoryId['value']+'/unpresent',
            data=json.dumps(data)
        )
        job = response.json()
        self.monitor_job(job['id']['value'])

 
    def present_repo(self, repositoryId, data):
        response = self.session.put(
            self.base_uri+'/Repository/'+repositoryId['value']+'/present',
            data=json.dumps(data)
        )
        job = response.json()
        self.monitor_job(job['id']['value'])

    
    def get(self, object_type, object_id):
        response = self.session.get(
            self.base_uri+'/'+object_type+'/'+object_id
        )
        return response.json()


    def get_id_for_name(self, object_type, object_name):
        response = self.session.get(
            self.base_uri+'/'+object_type+'/id'
        )
        for obj in response.json():
            if obj['name'] == object_name:
                return obj
        return None


    def monitor_job(self, job_id):
        while True:
            response = self.session.get(
                self.base_uri+'/Job/'+job_id)
            job = response.json()
            if job['summaryDone']:
                if job['jobRunState'] == 'FAILURE':
                    raise Exception('Job failed: %s' % job.error)
                elif job['jobRunState'] == 'SUCCESS':
                    if 'resultId' in job.keys():
                        return job['resultId']
                    break
                elif job['jobRunState'] == 'RUNNING':
                    continue
                else:
                    break


def main():
    changed = False
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(
                choices=['presented', 'unpresented'],required=True),
            server=dict(required=True),
            ovm_user=dict(required=True),
            ovm_pass=dict(required=True, no_log=True),
            ovm_host=dict(
                default='https://127.0.0.1:7002'),
            repository=dict(required=True),
        )
    )
    if HAS_REQUESTS is False:
        module.fail_json(
            msg="ovm_cmnds module requires the 'requests' package")

    base_uri = module.params['ovm_host']+'/ovm/core/wsapi/rest'
    session = auth(module.params['ovm_user'], module.params['ovm_pass'])
    client = OVMRestClient(base_uri, session)

    serverId = client.get_id_for_name(
        'Server',
        module.params['server'])

    repositoryId = client.get_id_for_name(
        'Repository',
        module.params['repository'])

    if serverId is not None and repositoryId is not None:
      presented_servers = client.get_presented_servers(repositoryId)
      if module.params['state'] == 'presented':
        if module.params['server'] in presented_servers:
          changed = False
        else:
          client.present_repo(repositoryId, data = serverId)
          changed = True
      if module.params['state'] == 'unpresented':
        if module.params['server'] not in presented_servers:
          changed = False
        else:
          client.unpresent_repo(repositoryId, data = serverId)  
          changed = True

    module.exit_json(changed=changed)

# pylint: disable=wrong-import-position
from ansible.module_utils.basic import AnsibleModule
import json
if __name__ == '__main__':
    main()
