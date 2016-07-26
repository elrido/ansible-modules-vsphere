ansible-modules-vsphere
=======================

The first Ansible module for VMware, [vsphere_guest](http://docs.ansible.com/ansible/vsphere_guest_module.html) was based on the pysphere vSphere API implementation. With Ansible 2.0 many additional modules for vSphere were added, all based on PyVmomi, the official vSphere API implementation provided by VMware. These provide additional functionality not covered by vsphere_guest.

The modules in this repository were created to fill some gaps in the vsphere_guest module. Namely the impossibility to create a new VM from a template, change the number of its CPUs, amount of RAM, put it in the correct datastore, resource pool *and* folder. This is a requirement to be able to properly handle multiple VM protection groups and support complex datastore structures (e.g. HP EVA and 3Par) accross multiple data centers.

- vsphere_template creates a new VM based on a template, optionally changing certain parameters of the VM compared to the template. It can also change these parameters (all except for the datastore) on an existing VM.
- vsphere_migrate_pool controls resource pools of VMs, (online) migrating them there if necessary.
- vsphere_tools checks the VMware tools status in a guest VM, optionally upgrading them.
- win_veeam_job creates or disables a VMware Veeam backup job and changes its settings. There is currently no Powershell commandlet to remove jobs, so setting the state to absent disables the schedule of an already existing job.

License
=======

As with Ansible, these modules are GPLv3 licensed. User generated modules not part of this project can be of any license.

Installation
============

Add a folder `library` to your Ansible project repository and put the modules you wish to use in there. You can now use these modules in the same way as any other modules shipped with Ansible.

