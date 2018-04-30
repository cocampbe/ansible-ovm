#!/usr/bin/env python
#

DOCUMENTATION = '''
---
module: ovm_vm_state
short_description: This module will start/stop/suspend/resume a VM on OVM
description:
  - Module to  start/stop/suspend/resume VMs
Author: "Court Campbell"
notes:
    - This module works with OVM 3.3 and 3.4
    - Set hosts in your playbook to the OVM Manager server
requirements:
    - requests package
options:
    name:
        description:
            - The VM name
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
            - the state of the VM
        options:
            - started
            - stopped
            - suspended
            - resumed
        required: True
'''

EXAMPLES = '''
- name: Stop a Virtual Machine
  ovm_vm:
    name: 'example_host'
    ovm_user: 'admin'
    ovm_pass: 'password'
    state: 'stopped'
'''

RETURN = '''
name:
  description:
    - The virtual-machine name, inside oracle-vm the vm-name is
    - not unique. It uses the vm-id as the unique identifier.
    - However, since this is not very useful for us mortals,
    - this module treats the vm-name as a unique identifier and
    - will return an error if two VMs have the same name.
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


    def start_vm(self, vmId):
        response = self.session.put(
            self.base_uri+'/Vm/'+vmId['value']+'/start'
        )
        job = response.json()
        self.monitor_job(job['id']['value'])

    
    def stop_vm(self, vmId):
        response = self.session.put(
            self.base_uri+'/Vm/'+vmId['value']+'/stop'
        )
        job = response.json()
        self.monitor_job(job['id']['value'])
    

    def suspend_vm(self, vmId):
        response = self.session.put(
            self.base_uri+'/Vm/'+vmId['value']+'/suspend'
        )
        job = response.json()
        self.monitor_job(job['id']['value'])
    

    def resume_vm(self, vmId):
        response = self.session.put(
            self.base_uri+'/Vm/'+vmId['value']+'/resume'
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
                choices=['stopped', 'started', 'suspended', 'resumed'],required=True),
            name=dict(required=True),
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

    vm_id = client.get_id_for_name(
        'Vm',
        module.params['name'])

    # Check if VM exists 
    if vm_id is not None:
      if module.params['state'] == 'started':
        vm = client.get('Vm',vm_id['value'])
        if vm['vmRunState'] == 'RUNNING':
          changed = False
        else:
          client.start_vm(vm_id)
          changed = True
      if module.params['state'] == 'stopped':
        vm = client.get('Vm',vm_id['value'])
        if vm['vmRunState'] == 'STOPPED':
          changed = False
        else:
          client.stop_vm(vm_id)  
          changed = True
      if module.params['state'] == 'suspended':
        vm = client.get('Vm',vm_id['value'])
        if vm['vmRunState'] == 'SUSPENDED':
          changed = False
        else:
          client.suspend_vm(vm_id)  
          changed = True
      if module.params['state'] == 'resumed':
        vm = client.get('Vm',vm_id['value'])
        if vm['vmRunState'] == 'RUNNING':
          changed = False
        else:
          client.resume_vm(vm_id)  
          changed = True

    module.exit_json(changed=changed)

# pylint: disable=wrong-import-position
from ansible.module_utils.basic import AnsibleModule
import json
if __name__ == '__main__':
    main()
