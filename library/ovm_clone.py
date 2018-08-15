#!/usr/bin/env python

DOCUMENTATION = '''
---
module: ovm_clone
short_description: Clone a VM from a template with a clone definition
description:
  - Pass options to clone a VM using a template and VM clone definition.
    Template and clone defintion must already exist. 
author: "Court Campbell"
boilerplate: "Stephan Arts, @stephanarts"
notes:
    - This module works with OVM 3.3 and 3.4
requirements:
    - requests package
options:
    name:
        description:
            - The virtual-machine name, inside oracle-vm the vm-name is
            - not unique. It uses the vm-id as the unique identifier.
            - However, since this is not very useful for us mortals,
            - this module treats the vm-name and will return an error
            - if two virtual machines have the same name.
        required: True
    ovm_user:
        description:
            - The OVM admin-user used to connect to the OVM-Manager.
        required: True
    ovm_pass:
        description:
            - The password of the OVM admin-user.
        required: True
    ovm_host:
        description:
            - The base-url for Oracle-VM.
        default: https://127.0.0.1:7002
        required: False
    serverpool:
        description:
            - The Oracle-VM server-pool where to create/find the
            - Virtual Machine.
        required: True
    repository:
        description:
            - The Oracle-VM storage repository where to store the Oracle-VM
              definition.
        required: True
    clone_vm:
        description:
            - dictionary containing the template and clone defintion
            - type (dict)
              - template
              - vmCloneDefinition
        required: True
'''

EXAMPLES = '''
- name: clone VM
  ovm_create:
     name: 'my_cloned_vm'
     ovm_user: 'admin'
     ovm_pass: 'password'
     serverpool: 'Pool1'
     repository: 'Repo1'
     clone_vm:
       template: 'MyVmTempalte'
       vmCloneDefinition: 'MyCloneDefinition'
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


    def clone_vm(self, vmId, name, data):
	response = self.session.put(
            self.base_uri+'/Vm/'+vmId['value']+'/clone'+
                '?serverPoolId='+data['serverPoolId']['value']+
                '&repositoryId='+data['repositoryId']['value']+
                '&vmCloneDefinitionId='+data['vmCloneDefinitionId']['value']+
                '&createTemplate=false'
        )
        job = response.json()
        clone_id = self.monitor_job(job['id']['value'])
        vm = { 'id': self.get('Vm',clone_id['value'])['id'],
                 'name': name }
        response = self.session.put(
            self.base_uri+'/Vm/'+clone_id['value'],
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


    def get_ids(self, object_type):
        response = self.session.get(
            self.base_uri+'/'+object_type
        )
        return response.json()


    def get_disk_maps(self,vmId):
        response = self.session.get(
            self.base_uri+'/Vm/'+vmId['value']+'/VmDiskMapping/id'
        )
        return response.json()


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
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(required=True),
            ovm_user=dict(required=True),
            ovm_pass=dict(required=True,no_log=True),
            ovm_host=dict(
                default='https://127.0.0.1:7002'),
            clone_vm=dict(
                 required=True,
                 type='dict'),
            serverpool=dict(required=True),
            repository=dict(required=True),
        )
    )
    if HAS_REQUESTS is False:
        module.fail_json(
            msg="ovm_create module requires the 'requests' package")

    base_uri = module.params['ovm_host']+'/ovm/core/wsapi/rest'
    session = auth(module.params['ovm_user'], module.params['ovm_pass'])

    result = {}
    result['name'] = module.params['name']

    client = OVMRestClient(base_uri, session)

    repository_id = client.get_id_for_name(
        'Repository',
        module.params['repository'])

    serverpool_id = client.get_id_for_name(
        'ServerPool',
        module.params['serverpool'])

    vm_id = client.get_id_for_name(
        'Vm',
        module.params['name'])

    # Create a new vm if it does not exist
    if vm_id is None:
      # Code for cloning from a template
      if module.params['clone_vm']:
          try:
              client.clone_vm(
                  client.get_id_for_name('Vm',module.params['clone_vm']['template']),
                      module.params['name'],
                      data = {
                          'repositoryId': repository_id,
                          'serverPoolId': serverpool_id,
                          'vmCloneDefinitionId': client.get_id_for_name('VmCloneDefinition',module.params['clone_vm']['vmCloneDefinition'])
                      })
              result['changed'] = True
          except:
              module.fail_json(msg="Error cloning vm from template.")
    else:
      result['changed'] = False

    module.exit_json(**result)

# pylint: disable=wrong-import-position
from ansible.module_utils.basic import AnsibleModule
import json
if __name__ == '__main__':
    main()
