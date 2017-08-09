## Ansible-OVM ##
This module can be used in an Ansible playbook to create VMs. 

## Example ##

---
 - hosts: <OVM_MANAGER>
   name: deploy an oracle vm
   gather_facts: no
   tasks:
    - name: create VM
      ovm_vm:
       name: 'myVM'
       ovm_user: 'username'
       ovm_pass: 'password'
       server_pool: 'pool1'
       repository: 'repo1'
       memory: 4096
       vcpu_cores: 1
       boot_order:
        - Disk
        
If you are not fanilair with Ansible, the host must be in your inventory file. Replace <OVM_MANAGER> with what you have in the inventory.
