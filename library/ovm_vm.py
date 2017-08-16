#!/usr/bin/env python
#

DOCUMENTATION = '''
---
module: ovm_vm
short_description: This module manages Virtual Machines inside Oracle-VM
description:
  - Module to manage Virtual Machine definitions inside Oracle-VM
author: "Stephan Arts, @stephanarts"
update: "Court Campbell"
notes:
    - This module works with OVM 3.3 and 3.4
    - Set hosts n your playbook to the OVM Manager server
requirements:
    - requests package update: "Court Campbell"
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
            - definition.
        required: True
    vm_domain_type:
        description:
            - The domain type specifies the Virtual-Machine
            - virtualization mode.
        required: False
        default: "XEN_HVM"
        choices: [ XEN_HVM, XEN_HVM_PV_DRIVERS, XEN_PVM, LDOMS_PVM, UNKNOWN ]
'''

EXAMPLES = '''
- name: Create a Virtual Machine
  ovm_vm:
    name: 'example_host'
    ovm_user: 'admin'
    ovm_pass: 'password'
    serverpool: 'Madrid'
    repository: 'Repo1'
    memory: 4096
    vcpu_cores: 4
    network_interfaces:
      - name: eth0
        description: koffie
        mac: '00:00:00:00:00:00'
        network: 456787654
    disks:
      - name: example_host_system.1
        description: '...'
        size: 50G
        sparse: False
        repository: 'Repo1'
    boot_order:
      - PXE
'''

RETURN = '''
name:
  description:
    - The virtual-machine name, inside oracle-vm the vm-name is
    - not unique. It uses the vm-id as the unique identifier.
    - However, since this is not very useful for us mortals,
    - this module treats the vm-name as a unique identifier and
    - will return an error if two VMs have the same name.
id:
  description:
    - The virtual-machine id, inside oracle-vm the vm id is
    - the unique identifier. This is the Id used when referencing
    - the vm from other resources.
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

    def create_vm(self, object_type, data):
        response = self.session.post(
            self.base_uri+'/'+object_type,
            data=json.dumps(data)
        )
        job = response.json()
        self.monitor_job(job['id']['value'])
    
    def create_vdisk(self, repositoryId, sparse, data):
        response = self.session.post(
            self.base_uri+'/Repository/'+repositoryId['value']+'/VirtualDisk?sparse='+str(sparse),
            data=json.dumps(data)
        )
        job = response.json()
        self.monitor_job(job['id']['value'])
    
    def map_vdisk(self, vmId, data):
        response = self.session.post(
            self.base_uri+'/Vm/'+vmId['value']+'/VmDiskMapping',
            data=json.dumps(data)
        )
        job = response.json()
        self.monitor_job(job['id']['value'])

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
    changed = False
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(
                default='present',
                choices=['present', 'absent']),
            name=dict(required=True),
            ovm_user=dict(required=True),
            ovm_pass=dict(required=True),
            ovm_host=dict(
                default='https://127.0.0.1:7002'),
            clone_vm=dict(
                 required=False,
                 type='dict'),
            serverpool=dict(required=True),
            repository=dict(required=True),
            vm_domain_type=dict(
                default='XEN_HVM',
                choices=[
                    'XEN_HVM',
                    'XEN_HVM_PV_DRIVERS',
                    'XEN_PVM',
                    'LDOMS_PVM',
                    'UNKNOWN']),
            memory=dict(
                default=4096,
                type='int'),
            max_memory=dict(
                default=None,
                type='int'),
            vcpu_cores=dict(
                default=2,
                type='int'),
            max_vcpu_cores=dict(
                default=None,
                type='int'),
            networks=dict(
                type='list'),
            disks=dict(
                type='list'),
            boot_order=dict(
                required=False,
                type='list'),
        )
    )
    if HAS_REQUESTS is False:
        module.fail_json(
            msg="ovm_vm module requires the 'requests' package")

    memory = module.params['memory']
    max_memory = module.params['max_memory']
    vcpu_cores = module.params['vcpu_cores']
    max_vcpu_cores = module.params['max_vcpu_cores']

    # Check memory requirements
    if memory%1024 != 0:
        module.fail_json(
            msg="memory must be a multitude of 1024")
    if max_memory is None:
        max_memory = memory
    else:
        if max_memory < memory:
            module.fail_json(
                msg="max_memory < memory")
        if max_memory%1024 != 0:
            module.fail_json(
                msg="max_memory must be a multitude of 1024")
    if max_vcpu_cores is None:
        max_vcpu_cores = vcpu_cores

    base_uri = module.params['ovm_host']+'/ovm/core/wsapi/rest'
    session = auth(module.params['ovm_user'], module.params['ovm_pass'])
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
            client.clone_vm(
                client.get_id_for_name('Vm',module.params['clone_vm']['template']),
                    module.params['name'],
                    data = {
                        'repositoryId': repository_id,
                        'serverPoolId': serverpool_id,
                        'vmCloneDefinitionId': client.get_id_for_name('VmCloneDefinition',module.params['clone_vm']['vmCloneDefinition'])
                    })
            changed = True
            module.exit_json(changed=changed)
        
        client.create_vm(
            'Vm',
            data = {
                'repositoryId': repository_id,
                'serverPoolId': serverpool_id,
                'vmDomainType': module.params['vm_domain_type'],
                'name': module.params['name'],
                'cpuCount': vcpu_cores,
                'cpuCountLimit': max_vcpu_cores,
                'memory': memory,
                'memoryLimit': max_memory
            })
        changed = True
    # If dissks are defined, create them
    if module.params['disks']:
       for disk in module.params['disks']:
           if client.get_id_for_name('VirtualDisk',disk['name']) is None:
               client.create_vdisk(
                   client.get_id_for_name('Repository', disk['repository']),
                   disk['sparse'],
                   data = {
                       'name': disk['name'],
                       'size': disk['size'] * (2**30)
                   })
               client.map_vdisk(
                   client.get_id_for_name('Vm',module.params['name']),
                   data = {
                       'vmId': client.get_id_for_name('Vm',module.params['name']),
                       'virtualDiskId': client.get_id_for_name('VirtualDisk',disk['name']),
                       'diskTarget': len(client.get_disk_maps(client.get_id_for_name('Vm',module.params['name'])))
                   })
               changed = True
           else:
               changed = False

    module.exit_json(changed=changed)

# pylint: disable=wrong-import-position
from ansible.module_utils.basic import AnsibleModule
import json
if __name__ == '__main__':
    main()
