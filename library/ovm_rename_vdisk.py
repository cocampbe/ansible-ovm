

DOCUMENTATION = '''
---
module: ovm_rename_vdisk.
short_description: rename an vm virtual disk
description:
  - Module to modify the name of a virtualdisk presented to a vm
Author: "Court Campbell"
notes:
    - This module works with OVM 3.3 and 3.4
requirements:
    - requests package
options:
    vdisk_name:
        description:
            - current, or partial, vdisk name
        required: True
    rename:
        description:
            - new name of the vdisk
        required: True
    vm_name:
        description:
            - name of the vm with the vdisk to rename
        required: True
    ovm_host:
        description:
            - URL of OVMM
            - default, https://127.0.0.1:7002
    ovm_user:
        description:
            - The OVM admin-user used to connect to the OVM-Manager.
        required: True
    ovm_pass:
        description:
            - The password of the OVM admin-user.
        required: True
'''

EXAMPLES = '''
- name: rename vdisk "disk10"
  ovm_rename_vdisk:
    ovm_user: 'admin'
    ovm_pass: 'password'
    rename: 'test server disk 1'
    vdisk_name: "disk10"
    vm_name: "testvm1"

'''

RETURN = '''
name:
  description:
    - Changes VirtualDisk name.
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


    def get_vm_vdisk(self,vm,vdiskName):
        for diskmap in self.session.get(self.base_uri+'/Vm/'+vm['value']+'/VmDiskMapping').json():
          vdisk = self.session.get(self.base_uri+'/VirtualDisk/'+diskmap['virtualDiskId']['value']).json()
          if vdisk['diskType'] == "VIRTUAL_DISK":
            if vdiskName in vdisk['name']:
              return vdisk


    def rename_vdisk(self,vdisk,data):
        response = self.session.put(
            self.base_uri+'/VirtualDisk/'+vdisk['id']['value'],
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
            rename=dict(required=True),
            vdisk_name=dict(required=True),
            vm_name=dict(required=True),
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

    try: 
      vm = client.get_id_for_name('Vm',module.params['vm_name'])
    except:
      module.fail_json(msg="Error getting VM object. Try checking the vm_name, or ovm_host.")

    try:
      vdisk = client.get_vm_vdisk(vm,module.params['vdisk_name'])
    except:
      module.fail_json(msg="Error getting VM VirtualDisk.")
    
    result = {}
    result['vm_name'] = module.params['vm_name'].upper() 
    result['vdisk_name'] = module.params['vdisk_name']
    result['rename'] = module.params['rename']
    if vdisk is None:
      try:
        vdisk = client.get_vm_vdisk(vm,module.params['rename'])
      except:
        module.fail_json(msg="Error getting VM VirtualDisk "+module.params['rename']+".")
    if module.params['vdisk_name'] in vdisk['name']:
      vdisk['name'] = module.params['rename']
      client.rename_vdisk(vdisk,data=vdisk)
      result['changed'] = True
    elif module.params['rename'] == vdisk['name']:
      result['changed'] = False
    else:
      module.fail_json(msg="Error renaming VirtualDisk.")

    module.exit_json(**result)

# pylint: disable=wrong-import-position
from ansible.module_utils.basic import AnsibleModule
import json
if __name__ == '__main__':
    main()
