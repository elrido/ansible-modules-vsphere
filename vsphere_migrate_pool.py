#!/usr/bin/python
# -*- coding: utf-8 -*-

# Control resource pools of VMs
#
# This module controls resource pools of VMs,
# (online) migrating them there if necessary.
#
# (c) 2016, Simon Rupf <simon@rupf.net>
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: vsphere_migrate_pool
short_description: Control resource pools of VMs
description:
     - This module controls resource pools of VMs, (online) migrating them there if necessary.
version_added: "not yet"
notes:
    - This module should run from a system that can access vSphere directly.
      Either by using local_action, or using delegate_to.
    - Tested on vSphere 5.1 and 5.5
requirements:
    - "python >= 2.6"
    - PyVmomi
options:
  vcenter_hostname:
    description:
      - The hostname of the vcenter server the module will connect to, to control the guest.
    required: true
  guest:
    description:
      - The virtual server name you wish to manage.
    required: true
  username:
    description:
      - Username to connect to vcenter as.
    required: true
  password:
    description:
      - Password of the user to connect to vcenter as.
    required: true
  resource_pool:
    description:
      - The name of the resource_pool to migrate the VM to.
    required: true
  cluster:
    description:
      - The name of the cluster to migrate the VM to.
    required: true
  sync:
    description:
      - Specifies if the module should wait until the migration is completed. If no further changes on the VM are done during the current play, this can be set to 'no'.
    required: false
    default: yes
    choices: ['yes', 'no']
author:
    - Simon Rupf
'''
EXAMPLES = '''
# Set or change a resource pool
- vsphere_migrate_pool:
    vcenter_hostname: vcenter.mydomain.local
    username: myuser
    password: mypass
    guest: myvm001
    resource_pool: "/Resources"
    cluster: MyCluster
'''

# import module snippets
from ansible.module_utils.basic import *
from pysphere import VIServer
import re

def main():
    """Sets up the module parameters, validates them and perform the change"""
    module = AnsibleModule(
        argument_spec=dict(
            vcenter_hostname=dict(required=True),
            username=dict(required=True),
            password=dict(required=True),
            guest=dict(required=True),
            resource_pool=dict(required=True),
            cluster=dict(required=True),
            sync=dict(required=False, type='bool', default=True)
        ),
        supports_check_mode=True
    )

    server = VIServer()
    server.connect(
        module.params['vcenter_hostname'],
        module.params['username'],
        module.params['password'])
    virtualmachine = server.get_vm_by_name(module.params['guest'])

    old_name = virtualmachine.get_resource_pool_name()
    new_name = module.params['resource_pool']

    # find the clusters ManagedObjectReference
    cluster = None
    clusters = server.get_clusters()
    for mor, name in clusters.iteritems():
        if name == module.params['cluster']:
            cluster = mor
            break

    if cluster is None:
        module.fail_json(msg='Cluster %s not found on server %s' %
            (module.params['cluster'], module.params['vcenter_hostname']))

    # find the new resource pools Managed Object Reference and migrate the VM
    rps = server.get_resource_pools(from_mor=cluster)
    for mor, path in rps.iteritems():
        if re.match('.*%s$' % new_name, path):
            if not re.match('.*%s$' % old_name, path):
                if not module.check_mode:
                    virtualmachine.migrate(
                        resource_pool=mor,
                        host=virtualmachine.get_property('hostname'),
                        sync_run=module.params['sync'])
                module.exit_json(changed=True, changes=module.params)
            module.exit_json(changed=False, changes=module.params)
    module.fail_json(msg='Resource pool %s not found' %
        module.params['resource_pool'])

main()
