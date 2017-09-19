## Ansible-OVM ##
This module can be used in an Ansible playbook to create VMs. 

## Examples ##

### Create a new VM ###

```
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
       disks:
          - name: 'myOSDisk'
            description: '...'
            size: 50
            sparse: False
            repository: 'osdisk_repo'
          - name: 'myDataDisk'
            description: '...'
            size: 250
            sparse: False
            repository: 'datadisk_repo'
       networks:
         - name: 'myVnic1'
         - name: 'myVnic2'
       boot_order:
        - Disk
```

### Clone a VM ###

```
---
 - hosts: <OVM_MANAGER>
   name: clone an oracle vm from a template
   gather_facts: no
   tasks:
     - name: clone VM
       ovm_vm:
         name: 'myClonedVM'
         ovm_user: 'username'
         ovm_pass: 'password'
         serverpool: 'pool1'
         repository: 'repo1'
         clone_vm:
           template: 'myTemplate'
           vmCloneDefinition: 'myCloneCustomizer'
```
        
If you are not familair with Ansible, the host must be in your inventory file. Replace <OVM_MANAGER> with what you have in the inventory.

## TODO ##

I need to add code to create and map Networks.
