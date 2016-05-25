#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Create a VM based on a template

This module creates a new VMs based on a template, optionally changing certain
parameters of the VM compared to the template.
"""

DOCUMENTATION = '''
---
module: vsphere_template
short_description: Create a VM based on a template
description:
    - This module creates a new VMs based on a template, optionally changing certain parameters of the VM compared to the template.
version_added: "not yet"
options:
  vcenter_hostname:
    description:
      - The hostname of the vCenter server the module will connect to, to control the guest.
    required: true
  guest:
    description:
      - The virtual machines name you wish to create or manage.
    required: true
  username:
    description:
      - Username to connect to vCenter as.
    required: true
  password:
    description:
      - Password of the user to connect to vcenter as.
    required: true
  template_src:
    description:
      - Name of the source template to deploy from
    required: true
  resource_pool:
    description:
      - The name of the resource pool to migrate the VM to.
    required: true
  datacenter:
    description:
      - The name of the datacenter to migrate the VM to.
    required: true
  datastore:
    description:
      - The name of the datastore to migrate the VM to.
    required: true
  folder:
    description:
      - The name of the folder to migrate the VM to.
    required: true
  notes:
    description:
        - The string to set as the annotation about the VM, defaults to an empty string.
    required: false
    default: none
  num_cpus:
    description:
        - The number of CPUs the VM should have, defaults to 2 CPUs.
    required: false
    default: 2
  memory_mb:
    description:
        - The number of CPUs the VM should have, defaults to 4096 MiB.
    required: false
    default: 4096
  port:
    description:
        - The port number under which the API is accessible on the vCenter server, defaults to port 443 (HTTPS).
    required: false
    default: 443
  power_on_after_clone:
    description:
      - Specifies if the VM should be powered on after the clone.
    required: false
    default: yes
    choices: ['yes', 'no']
author:
    - Simon Rupf, based on examples by Dann Bohn
'''
EXAMPLES = '''
# Create new machine from template
- vsphere_template:
    vcenter_hostname: vcenter.mydomain.local
    username: myuser
    password: mypass
    guest: myvm001
    template_src: mytemplate
    resource_pool: MyResourcePool
    datastore: MyDataStore
    datacenter: MyDataCenterName
    folder: MyFolder
'''

# import module snippets
from ansible.module_utils.basic import *
from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
import atexit

def main():
    """Sets up the module parameters, validates them and perform the change"""
    # enforce parameters and types
    module = AnsibleModule(
        argument_spec=dict(
            vcenter_hostname=dict(required=True, type='str'),
            username=dict(required=True, type='str'),
            password=dict(required=True, type='str'),
            guest=dict(required=True, type='str'),
            template_src=dict(required=True, type='str'),
            datastore=dict(required=True, type='str'),
            datacenter=dict(required=True, type='str'),
            folder=dict(required=True, type='str'),
            resource_pool=dict(required=True, type='str'),
            notes=dict(required=False, type='str', default=''),
            num_cpus=dict(required=False, type='int', default=2),
            memory_mb=dict(required=False, type='int', default=4096),
            port=dict(required=False, type='int', default=443),
            power_on_after_clone=dict(required=False, type='bool', default=True)
        ),
        supports_check_mode=True
    )

    # connect to the vCenter...
    try:
        connection = SmartConnect(
            host=module.params['vcenter_hostname'],
            user=module.params['username'],
            pwd=module.params['password'],
            port=module.params['port'])
        # and don't forget to disconnect
        atexit.register(Disconnect, connection)
    except:
        module.fail_json(
            msg='failed to connect to vCenter server at %s with user %s' %
            (module.params['vcenter_hostname'], module.params['username']))

    content = connection.RetrieveContent()

    # validate parameters
    guest = get_obj(content, [vim.VirtualMachine], module.params['guest'])
    if guest:
        module.exit_json(
            changed=False,
            ansible_facts=gather_facts(guest))

    template = get_obj(
        content,
        [vim.VirtualMachine],
        module.params['template_src'])
    if not template:
        module.fail_json(msg='template %s not found on vCenter server at %s' %
            (module.params['template'], module.params['vcenter_hostname']))

    datastore = get_obj(content, [vim.Datastore], module.params['datastore'])
    if not datastore:
        module.fail_json(msg='datastore %s not found on vCenter server at %s' %
            (module.params['datastore'], module.params['vcenter_hostname']))

    datacenter = get_obj(content, [vim.Datacenter], module.params['datacenter'])
    if not datacenter:
        module.fail_json(msg='datacenter %s not found on vCenter server at %s' %
            (module.params['datacenter'], module.params['vcenter_hostname']))

    folder = get_obj(content, [vim.Folder], module.params['folder'])
    if not folder:
        module.fail_json(msg='folder %s not found on vCenter server at %s' %
            (module.params['folder'], module.params['vcenter_hostname']))

    resource_pool = get_obj(
        content,
        [vim.ResourcePool],
        module.params['resource_pool'])
    if not resource_pool:
        module.fail_json(
            msg='resource_pool %s not found on vCenter server at %s' %
            (module.params['resource_pool'], module.params['vcenter_hostname']))

    # prepare relocation specification
    relospec = vim.vm.RelocateSpec()
    relospec.datastore = datastore
    relospec.pool = resource_pool

    # prepare VM configuration
    vmconf = vim.vm.ConfigSpec()
    vmconf.numCPUs = module.params['num_cpus']
    vmconf.memoryMB = module.params['memory_mb']
    vmconf.cpuHotAddEnabled = False
    vmconf.memoryHotAddEnabled = False
    vmconf.annotation = module.params['notes']

    # prepare the clones specification
    clonespec = vim.vm.CloneSpec()
    clonespec.location = relospec
    clonespec.config = vmconf
    clonespec.powerOn = module.params['power_on_after_clone']
    clonespec.template = False # the clone itself will not be a template

    if module.check_mode:
        changes = [
            'vm %s would have been created, if not running in check mode' %
            module.params['guest']]
    else:
        task = template.Clone(
            folder=folder,
            name=module.params['guest'],
            spec=clonespec)
        new_vm = wait_for_task(module, task)
        changes = ['vm %s has been created' % module.params['guest']]

    module.exit_json(
        changed=True, changes=changes,
        ansible_facts=gather_facts(new_vm))

def get_obj(content, vimtype, name):
    """Returns an object based on it's vimtype and name"""
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for element in container.view:
        if element.name == name:
            obj = element
            break
    return obj

def wait_for_task(module, task):
    """Wait for a task to complete"""
    # set generic message
    error_msg = 'an error occurred while waiting for the task to complete'
    task_done = False
    while not task_done:
        if task.info.state == 'success':
            return task.info.result

        if task.info.state == 'error':
            if isinstance(task.info.error, vim.fault.DuplicateName):
                error_msg = 'an object with the name %s already exists' % \
                    task.info.error.name
            module.fail_json(msg=error_msg)

def gather_facts(virtualmachine):
    """Set ansible_facts based on a VMs configuration"""
    memory_mb = virtualmachine.summary.config.memorySizeMB
    memory_gb = memory_mb / 1024

    facts = {}
    facts['vm_uuid'] = virtualmachine.config.uuid
    facts['vm_name'] = virtualmachine.config.name
    facts['instance_uuid'] = virtualmachine.config.instanceUuid
    facts['memory_mb'] = memory_mb
    facts['memory_gb'] = memory_gb
    facts['num_cpus'] = virtualmachine.summary.config.numCpu

    return facts

main()
