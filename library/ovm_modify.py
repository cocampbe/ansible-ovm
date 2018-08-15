#!/usr/bin/env python

DOCUMENTATION = '''
---
module: ovm_modify
short_description: Module to modify the properties of a VM
description:
  - Module to modify the properties of a VM
  - Not all properties can be modified
Author: "Court Campbell"
notes:
    - This module works with OVM 3.3 and 3.4
requirements:
    - requests package
options:
    name:
        description:
            - The VM you want to modify
            - case sensitive
        required: True
    ovm_user:
        description:
            - The OVM admin-user used to connect to the OVM-Manager.
        required: True
    ovm_pass:
        description:
            - The password of the OVM admin-user.
        required: True
    properties:
        description:
            - list of properties to modify. Please check the OvmSDK put
              for endpoint /rest/Vm/{vmId} for a list of valid properties.
              Properties names must match API names.
        required: False
        type: dict
'''

EXAMPLES = '''
- name: Change CPU and Memory on guest
  ovm_modify:
    name: 'TEST_VM'
    ovm_user: 'admin'
    ovm_pass: 'password'
    properties:
      cpuCount: 4
      memory: 8192
'''

RETURN = '''
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


    def modify_vm(self, vm):
        response = self.session.put(
            self.base_uri+'/Vm/'+vm['id']['value'],
            data=json.dumps(vm)
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
            name=dict(required=True),
            ovm_user=dict(required=True),
            ovm_pass=dict(required=True, no_log=True),
            ovm_host=dict(
                default='https://127.0.0.1:7002'),
            properties=dict(required=True,type=dict),
        )
    )
    if HAS_REQUESTS is False:
        module.fail_json(
            msg="ovm_cmnds module requires the 'requests' package")

    base_uri = module.params['ovm_host']+'/ovm/core/wsapi/rest'
    session = auth(module.params['ovm_user'], module.params['ovm_pass'])
    client = OVMRestClient(base_uri, session)

    result = {}
    result['name'] = module.params['name'].upper()
    result['properties'] = module.params['properties']
    result['modified'] = []

    vmId = client.get_id_for_name('Vm',
        module.params['name'])
    
    vm = client.get('Vm',
        vmId['value'])
    
    if vm is None:
      result['changed'] =  False
      module.fail_json(msg="Error getting VM object.")
    else:
      try:
        modified = 0
        for property in module.params['properties'].keys():
          if vm[property] !=  module.params['properties'][property]:
            vm[property] =  module.params['properties'][property] 
            modified += 1
            result['modified'].append(property)
        client.modify_vm(vm)
        if modified > 0:
          result['changed'] =  True
        else:
          result['changed'] =  False
      except:
        module.fail_json(msg="Error modifying VM.")

    module.exit_json(**result)

# pylint: disable=wrong-import-position
from ansible.module_utils.basic import AnsibleModule
import json
if __name__ == '__main__':
    main()
