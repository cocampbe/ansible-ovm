

DOCUMENTATION = '''
---
module: ovm_repo_ownership
short_description: This module will take/release ownership of an OVM repo to the OVM Manager
description:
  - Module to manage OVMM repository ownership 
Author: "Court Campbell"
notes:
    - This module works with OVM 3.3 and 3.4
    - Set hosts in your playbook to the OVM Manager server
requirements:
    - requests package
options:
    serverpool:
        description:
            - The serverpool of which the Repository's OCFS2 FileSystem is associated.
            - You will need to run mounted.ocfs2 -d and fsck.ocfs2 -y on the device assocaited with the repo
              before you can take ownership
    ovm_manager:
        description:
            - The ovm manager that will take/release ownership
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
            - The OVM repository you want to take/release ownership of
        required: True
'''

EXAMPLES = '''
- name: Release ownership of 'Repo1' to OVMM
  ovm_repo_ownership:
    ovm_user: 'admin'
    ovm_pass: 'password'
    repository: 'Repo1'
    state: 'released'

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

    def get_repo_owner(self, repositoryId):
        response = self.session.get(
            self.base_uri+'/Repository/'+repositoryId['value']
        )
        return response.json()['managerUuid']


    def releaseownership_repo(self, repositoryId):
        response = self.session.put(
            self.base_uri+'/Repository/'+repositoryId['value']+'/releaseOwnership'
        )
        job = response.json()
        self.monitor_job(job['id']['value'])

 
    def takeownership_repo(self, repositoryId, serverpoolId):
        response = self.session.put(
            self.base_uri+'/Repository/'+repositoryId['value']+'/takeOwnership?serverPoolId='+serverpoolId['value']
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
            serverpool=dict(required=False),
            ovm_manager=dict(required=True),
            state=dict(
                choices=['owned', 'released'],required=True),
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

    repositoryId = client.get_id_for_name(
        'Repository',
        module.params['repository'])
    
    ovm_manager = client.get_id_for_name(
        'Manager',
        'OVM Manager')
     
    if repositoryId is not None and ovm_manager is not None:
      repo_owner = client.get_repo_owner(repositoryId)
      if module.params['state'] == 'owned':
        if ovm_manager['value'] == repo_owner:
          changed = False
        else:
          if module.params['serverpool'] is not None:
            serverpoolId = client.get_id_for_name(
              'ServerPool',
              module.params['serverpool'])
          client.takeownership_repo(repositoryId, serverpoolId)
          changed = True
      if module.params['state'] == 'released':
        if repo_owner is None:
          changed = False
        else:
          client.releaseownership_repo(repositoryId)  
          changed = True

    module.exit_json(changed=changed)

# pylint: disable=wrong-import-position
from ansible.module_utils.basic import AnsibleModule
import json
if __name__ == '__main__':
    main()
