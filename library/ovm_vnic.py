

DOCUMENTATION = '''
---
module: ovm_vnic
short_description: Module to delete/create a VNIC on a VM
description:
  - Module to to delete/create a VNIC on a VM
Author: "Court Campbell"
notes:
    - This module works with OVM 3.3 and 3.4
    - Set hosts in your playbook to the OVM Manager server
requirements:
    - requests package
options:
    name:
        description:
            - The VM with the VNIC you want to modify
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
    state:
      description:
            - State is either present or absent
'''

EXAMPLES = '''
- name: Delete a VNIC from a VM guest
  ovm_repo_ownership:
    name: 'vm_guest1'
    ovm_user: 'admin'
    ovm_pass: 'password'
    state: 'absent'

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


    def create_vnic(self, vmId, data):
        response = self.session.post(
            self.base_uri+'/Vm/'+vmId['value']+'/VirtualNic',
            data=json.dumps(data)
        )
        job = response.json()
        self.monitor_job(job['id']['value'])


    def delete_vnic(self, vmId, vnicId):
        response = self.session.delete(
            self.base_uri+'/Vm/'+vmId['value']+'/VirtualNic/'+vnicId['value']
        )
        job = response.json()
        self.monitor_job(job['id']['value'])


    def get_vm_vnic(self,vmName):
        for vnic in self.session.get(self.base_uri+'/VirtualNic').json():
          if vmName in vnic['vmId']['name']:
            return vnic

 
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
            state=dict(choices=['present', 'absent'],required=True),
            ovm_user=dict(required=True),
            ovm_pass=dict(required=True, no_log=True),
            ovm_host=dict(
                default='https://127.0.0.1:7002'),
        )
    )
    if HAS_REQUESTS is False:
        module.fail_json(
            msg="ovm_cmnds module requires the 'requests' package")

    base_uri = module.params['ovm_host']+'/ovm/core/wsapi/rest'
    session = auth(module.params['ovm_user'], module.params['ovm_pass'])
    client = OVMRestClient(base_uri, session)

    vmId = client.get_id_for_name(
        'Vm',
        module.params['name'])
    
    vnic = client.get_vm_vnic(
        module.params['name'])

    if module.params['state'] == 'absent':
      if vnic is None:
        changed = False
      else:
        client.delete_vnic(vmId, vnic['id'])
        changed = True
    if module.params['state'] == 'present':
      if vnic is not None:
        changed = False
      else:
        if vmId is not None:
          client.create_vnic(vmId, data = { 'name': module.params['name']+'_VNIC' })
          changed = True
        else:
          module.fail_json(msg="Could not get VM ID. Check that you are using the correct VM name.")

    module.exit_json(changed=changed)

# pylint: disable=wrong-import-position
from ansible.module_utils.basic import AnsibleModule
import json
if __name__ == '__main__':
    main()
