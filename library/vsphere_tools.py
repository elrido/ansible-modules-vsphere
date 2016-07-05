#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Checks the VMware tools status in a guest VM

This module checks the VMware tools status in a guest VM, optionally upgrading them.
"""

DOCUMENTATION = '''
---
module: vsphere_tools
short_description: Checks the VMware tools status in a guest VM
description:
    - This module checks the VMware tools status in a guest VM, optionally upgrading them.
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
  installer_options:
    description:
      - Command line options passed to the installer to modify the installation procedure for tools.
    required: true
  port:
    description:
        - The port number under which the API is accessible on the vCenter server, defaults to port 443 (HTTPS).
    required: false
    default: 443
  state:
    description:
      - Indicates the desired tools state. `latest` ensures that the latest version is installed, upgrading the tools if necessary, while `present` only checks if they are installed.
    required: false
    default: present
    choices: ['present', 'latest', 'absent']
author:
    - Simon Rupf, based on examples by Dann Bohn
'''
EXAMPLES = '''
# example upgrading the VMware tools if necessary
- vsphere_tools:
    vcenter_hostname: vcenter.mydomain.local
    username: myuser
    password: mypass
    guest: myvm001
    state: latest
'''

# import module snippets
from ansible.module_utils.basic import *
from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
import atexit

def main():
    """Sets up the module parameters, validates them and perform the task"""
    # enforce parameters and types
    module = AnsibleModule(
        argument_spec=dict(
            vcenter_hostname=dict(required=True, type='str'),
            username=dict(required=True, type='str'),
            password=dict(required=True, type='str'),
            guest=dict(required=True, type='str'),
            state=dict(required=True, type='str'),
            installer_options=dict(required=False, type='str', default=''),
            port=dict(required=False, type='int', default=443)
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
    guest = get_obj(content, [vim.VirtualMachine], module.params['guest'])
    if not guest:
        module.fail_json(msg='guest VM "%s" not found on vCenter server at %s' %
            (module.params['guest'], module.params['vcenter_hostname']))

    state = module.params['state']
    if state not in ['present', 'latest', 'absent']:
        module.fail_json(msg='invalid state "%s" recieved, state must be one of: present, latest, absent' % state)

    # get current status of VMware tools
    status = guest.guest.toolsVersionStatus2

    # check if status requires an action
    if state == 'present' and status == 'guestToolsNotInstalled':
        module.fail_json(msg='guest VM "%s" has the tools state "present", but the current status if the tools is "%s"' %
            (module.params['guest'], status))

    elif state == 'absent' and status <> 'guestToolsNotInstalled':
        module.fail_json(msg='guest VM "%s" has the tools state "absent", but the current status if the tools is "%s"' %
            (module.params['guest'], status))

    elif state == 'latest' and status in ['guestToolsBlacklisted',
        'guestToolsNeedUpgrade', 'guestToolsNotInstalled',
        'guestToolsSupportedOld', 'guestToolsTooOld']:
        if module.check_mode:
            changes = [
                'tools on guest VM %s would have been upgraded, if not running in check mode' %
                module.params['guest']]
        else:
            task = guest.UpgradeTools(
                installerOptions=module.params['installer_options'])
            wait_for_task(module, task)
            changes = ['tools on guest VM %s have been upgraded' %
                module.params['guest']]
        module.exit_json(
            changed=True,
            changes=changes,
            ansible_facts={'vm_tools_status': status})

    module.exit_json(
            changed=False,
            ansible_facts={'vm_tools_status': status})

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

main()
