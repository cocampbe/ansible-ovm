## Ansible-OVM Modules ##
Various modules to manage OVM via Ansible

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

### Stop VMs ###

```
---
 - hosts: <OVM_MANAGER>
   name: stop VMs
   gather_facts: no
   tasks:
     - name: clone VM
       ovm_vm_state:
         name: "{{item}}"
         ovm_user: 'username'
         ovm_pass: 'password'
         state: 'stopped'
       with_items:
           - "vm1"
           - "vm2"
```

### unpresent a repo ###

```
---
 - hosts: <OVM_MANAGER>
   gather_facts: no
   tasks:
     - name: unpresent repo 'Repo1'
       ovm_repo_present:
         ovm_user: 'username'
         ovm_pass: 'password'
         ovm_manager: "<OVM_MANAGER>"
         repository: "Repo1"
         server: "{{item}}"
       with_items:
           - "server1"
           - "server2"
```
        
If you are not familair with Ansible, the host must be in your inventory file. Replace <OVM_MANAGER> with what you have in the inventory.

## NOTES ##

- Each module has an example section.
- I need to review the code and make changes. I was in a rush to get these modules working.


## TODO ##

Modules are working. I am working on adding better results. I would like to add rc output so that you can use until to retry a task until it completes successfully.
