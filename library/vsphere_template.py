#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Create a VM based on a template

This module creates a new VMs based on a template, optionally changing certain
parameters of the VM compared to the template.
"""

DOCUMENTATION = '''
---
module: vsphere_template
short_description: Create/Change a VM based on a template
description:
    - This module creates a new VMs based on a template, optionally changing certain parameters of the VM compared to the template. It can also change these parameters (all except for the datastore) on an existing VM.
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
  datastore:
    description:
      - The name of the datastore to create the VM into. This parameter is not considered when changing an existing VM, as it may have unexpected and dangerous results, e.g. migrating contents of multiple datastores into a single one.
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
        - The number of CPUs the VM should have, defaults to 2 CPUs. When changing this on an existing VM, you need to shutdown the VM beforehand.
    required: false
    default: 2
  memory_mb:
    description:
        - The number of CPUs the VM should have, defaults to 4096 MiB. When changing this on an existing VM, you need to shutdown the VM beforehand.
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
# minimal example to create a new machine from a template
- vsphere_template:
    vcenter_hostname: vcenter.mydomain.local
    username: myuser
    password: mypass
    guest: myvm001
    template_src: mytemplate
    resource_pool: MyResourcePool
    datastore: MyDataStore
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
    except:
        module.fail_json(
            msg='failed to connect to vCenter server at %s with user %s' %
            (module.params['vcenter_hostname'], module.params['username']))
    # and don't forget to disconnect
    atexit.register(Disconnect, connection)
    content = connection.RetrieveContent()

    # validate parameters
    template = get_obj(
        content,
        [vim.VirtualMachine],
        module.params['template_src'])
    if not template:
        module.fail_json(msg='template "%s" not found on vCenter server at %s' %
            (module.params['template_src'], module.params['vcenter_hostname']))

    datastore = get_obj(content, [vim.Datastore], module.params['datastore'])
    if not datastore:
        module.fail_json(msg='datastore %s not found on vCenter server at %s' %
            (module.params['datastore'], module.params['vcenter_hostname']))

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

    # is this a change of an existing machine or a new creation operation?
    guest = get_obj(content, [vim.VirtualMachine], module.params['guest'])
    if guest:
        change_guest(guest, module, datastore, folder, resource_pool)

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
        changed=True,
        changes=changes,
        ansible_facts=gather_facts(new_vm))

def change_guest(
    guest,
    module,
    datastore,
    folder,
    resource_pool):
    """Reconfigures guest and exits with the result"""
    changes = []
    relocation_required = False
    reconfiguration_required = False
    requires_shutdown = False
    relocation_spec = vim.vm.RelocateSpec()
    virtualmachine_conf = vim.vm.ConfigSpec()

    # This works as long as there is only one datastore.
    # For VMDKs on multiple datastores or raw LUNs, this may cause
    # unexpected and dangerous results, therefore it is uncommented for now
    #if guest.datastore[0].name != datastore.name:
    #    changes.append('Relocate VM from datastore %s to %s' %
    #        (guest.datastore[0].name, datastore.name))
    #    relocation_spec.datastore = datastore
    #    relocation_required = True

    if guest.resourcePool.name != resource_pool.name:
        changes.append('Relocate VM from resource pool %s to %s' %
            (guest.resourcePool.name, resource_pool.name))
        relocation_spec.pool = resource_pool
        relocation_required = True

    if guest.parent.name != folder.name:
        changes.append('Relocate VM from folder %s to %s' %
            (guest.folder.name, folder.name))
        relocation_spec.folder = folder
        relocation_required = True

    if guest.config.annotation != module.params['notes']:
        changes.append('Change configured annotation of VM from "%s" to "%s"' %
            (guest.config.annotation, module.params['notes']))
        virtualmachine_conf.annotation = module.params['notes']
        reconfiguration_required = True

    if guest.config.hardware.numCPU != module.params['num_cpus']:
        changes.append('Change configured number of CPUs of VM from %d to %d' %
            (guest.config.hardware.numCPU, module.params['num_cpus']))
        virtualmachine_conf.numCPUs = module.params['num_cpus']
        reconfiguration_required = True
        requires_shutdown = True

    if guest.config.hardware.memoryMB != module.params['memory_mb']:
        changes.append('Change configured memory in MB of VM from %d to %d' %
            (guest.config.hardware.memoryMB, module.params['memory_mb']))
        virtualmachine_conf.memoryMB = module.params['memory_mb']
        reconfiguration_required = True
        requires_shutdown = True

    if len(changes) > 0:
        if  requires_shutdown and \
            guest.summary.runtime.powerState == 'poweredOn':
            module.fail_json(
                msg=('VM %s is powered on and virtual hardware changes have ' +
                'been detected. Please shutdown the VM and rerun this action ' +
                'to apply the following changes: %s') %
                (module.params['guest'], ', '.join(changes)))
        else:
            if module.check_mode:
                changes.append('These changes were detected, but not ' +
                'applied, due to running in check mode')
            else:
                if relocation_required:
                    task = guest.RelocateVM_Task(spec=relocation_spec)
                    wait_for_task(module, task)
                if reconfiguration_required:
                    task = guest.ReconfigVM_Task(spec=virtualmachine_conf)
                    wait_for_task(module, task)
            module.exit_json(
                changed=True,
                changes=changes,
                ansible_facts=gather_facts(guest))
    else:
        module.exit_json(
            changed=False,
            ansible_facts=gather_facts(guest))

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
