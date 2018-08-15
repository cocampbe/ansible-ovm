

DOCUMENTATION = '''
---
module: ovm_network
short_description: Module to modify the network of a VMs VNIC
description:
  - Module to modify the network of a VMs VNIC
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
    network:
        description:
            - The network you want to assign
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


    def add_vnic_to_network(self, networkId, data):
        response = self.session.put(
            self.base_uri+'/Network/'+networkId['value']+'/addVirtualNic',
            data=json.dumps(data)
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
            network=dict(required=True),
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

    vnic = client.get_vm_vnic(
        module.params['name'])
    
    networkId = client.get_id_for_name(
        'Network',
        module.params['network'])
     
    if vnic is not None and networkId is not None:
      if vnic['networkId'] is not None:
        if vnic['networkId']['name'] == module.params['network']:
          changed = False
      else:
        client.add_vnic_to_network(
            networkId,
            data = vnic['id'])
        changed = True
    else:
      module.fail_json(msg="Error getting VNIC or Network info. Check network and name in the playbook. They are case sensitive.")

    module.exit_json(changed=changed)

# pylint: disable=wrong-import-position
from ansible.module_utils.basic import AnsibleModule
import json
if __name__ == '__main__':
    main()
