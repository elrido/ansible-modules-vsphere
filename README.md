ansible-modules-vsphere
=======================

The first Ansible module for VMware, [vsphere_guest](http://docs.ansible.com/ansible/vsphere_guest_module.html) was based on the pysphere vSphere API implementation. With Ansible 2.0 many additional modules for vSphere were added, all based on PyVmomi, the official vSphere API implementation provided by VMware. These provide additional functionality not covered by vsphere_guest.

The modules in this repository were created to fill some gaps in the vsphere_guest module. Namely the impossibility to create a new VM from a template, change the number of its CPUs, amount of RAM, put it in the correct datastore, resource pool *and* folder. This is a requirement to be able to properly handle multiple VM protection groups and support complex datastore structures (e.g. HP EVA and 3Par) accross multiple data centers.

License
=======

As with Ansible, these modules are GPLv3 licensed. User generated modules not part of this project can be of any license.

Installation
============

Add a folder `library` to your Ansible project repository and put the modules you wish to use in there. You can now use these modules in the same way like any other modules shipped with Ansible.

