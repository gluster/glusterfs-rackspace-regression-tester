#!/usr/bin/env python
"""Times how long the GlusterFS regression test takes for each instance type
in Rackspace"""

import os
import pyrax

# Use my user level credentials
creds_file = os.path.expanduser("~/.rackspace_cloud_credentials")
pyrax.set_setting("identity_type", "rackspace")
pyrax.set_credential_file(creds_file)
cs = pyrax.cloudservers

# Select CentOS 6.5
centos = None
os_list = cs.images.list()
for os_option in os_list:
    if os_option.name == 'CentOS 6.5':
        centos = os_option

# Select a 512MB instance
instance = None
instance_list = cs.flavors.list()
for instance_option in instance_list:
    if instance_option.name == '512MB Standard Instance':
        instance = instance_option

#servers = []
counter = 1
node_name = 'jc-api-test-node' + str(counter)
print node_name
temp_server = cs.servers.create(node_name, centos.id, instance.id)
server = pyrax.utils.wait_until(temp_server, 'status', ['ACTIVE', 'ERROR'], interval = 15, attempts = 40, verbose = False, verbose_atts = 'progress')
if server:
    if server.status == 'ACTIVE':
        print 'Name: {0}'.format(server.name)
        print 'Server status: {0}'.format(server.status)
        print 'ID: {0}'.format(server.id)
        print 'Admin Password: {0}'.format(server.adminPass)
        print 'Networks: {0}'.format(server.networks)
        print 'IPv4 address: {0}'.format(server.accessIPv4)
    else:
        server.delete()
#servers.append(cs.servers.create(node_name, centos.id, instance.id))
