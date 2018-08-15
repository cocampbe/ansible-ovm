

DOCUMENTATION = '''
---
module: ovm_serverpool
short_description: This module will add/remove a VM from a server pool
description:
  - Module to add/remove a VM from a server pool
Author: "Court Campbell"
notes:
    - This module works with OVM 3.3 and 3.4
    - Set hosts in your playbook to the OVM Manager server
requirements:
    - requests package
options:
    name:
        description:
            - The name of the VM
        required: True
    serverpool:
        description:
            - The server pool you want to add/remove the VM from
        required: True
    ovm_user:
        description:
            - The OVM admin-user used to connect to the OVM-Manager.
        required: True
    ovm_pass:
        description:
            - The password of the OVM admin-user.
        required: True
    state: 
	description:
            - present or absent
        required: True
'''

EXAMPLES = '''
- name: Add VM to server pool
  ovm_serverpool:
    serverpool: 'pool1'
    ovm_user: 'admin'
    ovm_pass: 'password'
    name: 'MyVM'
    state: 'present'

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


    def add_vm(self, serverpoolId, data):
        response = self.session.put(
            self.base_uri+'/ServerPool/'+serverpoolId['value']+'/addVm',
            data=json.dumps(data)
        )
        job = response.json()
        self.monitor_job(job['id']['value'])

 
    def remove_vm(self, serverpoolId, data):
        response = self.session.put(
            self.base_uri+'/ServerPool/'+serverpoolId['value']+'/removeVm',
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
                choices=['present', 'absent'],required=True),
            serverpool=dict(required=True),
            ovm_user=dict(required=True),
            ovm_pass=dict(required=True, no_log=True),
            ovm_host=dict(
                default='https://127.0.0.1:7002'),
            name=dict(required=True),
        )
    )
    if HAS_REQUESTS is False:
        module.fail_json(
            msg="ovm_cmnds module requires the 'requests' package")

    base_uri = module.params['ovm_host']+'/ovm/core/wsapi/rest'
    session = auth(module.params['ovm_user'], module.params['ovm_pass'])
    client = OVMRestClient(base_uri, session)

    serverpoolId = client.get_id_for_name(
        'ServerPool',
        module.params['serverpool'])

    vmId = client.get_id_for_name(
        'Vm',
        module.params['name'])

    vm = client.get(
        'Vm',
        vmId['value'])

    if serverpoolId is not None and vm is not None:
      if module.params['state'] == 'present':
        if vm['serverPoolId'] is None:
          client.add_vm(serverpoolId, data = vm['id'])
          changed = True
          module.exit_json(changed=changed)
        if vm['serverPoolId']['name'] == module.params['serverpool']:
          changed = False
      if module.params['state'] == 'absent':
        if vm['serverPoolId'] is None:
          changed = False
        else:
          client.remove_vm(serverpoolId, data = vm['id'])  
          changed = True
    else:
      module.fail_json(msg="Invalid serverpool or VM name. Please check that your parameters")

    module.exit_json(changed=changed)

# pylint: disable=wrong-import-position
from ansible.module_utils.basic import AnsibleModule
import json
if __name__ == '__main__':
    main()
