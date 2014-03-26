#!/usr/bin/env python
"""Times how long the GlusterFS regression test takes for each instance type
in Rackspace"""

import os
import getpass
import time
import ConfigParser
import pyrax

# How many servers to start?
# TODO: Having a command line option could be useful
max_servers = 1

# Read config file
config_file_path = os.path.join('config')
config = ConfigParser.ConfigParser()
config.read(config_file_path)
creds_file = os.path.expanduser(config.get('credentials', 'rackspace'))
ssh_key_name = config.get('credentials', 'ssh_key_name')

# Set the credentials for using Rackspace
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

# Start creating the servers
building_servers = []
building_passwords = []
username = getpass.getuser()
for counter in range(max_servers):
    node_name = '{0}-api-test-node{1}'.format(username, str(counter))
    print 'Creating {0}'.format(node_name)
    building_servers.append(
        cs.servers.create(node_name, centos.id, instance.id,
                          key_name=ssh_key_name))
    building_passwords.append(building_servers[counter].adminPass)

# Wait 20 seconds
time.sleep(20)

# Wait until all of the servers are running
server_list = []
admin_passwords = []
for server in range(len(building_servers)):
    print 'Waiting for {0} to become active'.format(
        building_servers[server].name)
    finished_build = pyrax.utils.wait_until(building_servers[server],
                                            'status', ['ACTIVE', 'ERROR'],
                                            interval=30, attempts=5)
    if finished_build.status == 'ACTIVE':
        print 'Adding {0} to the server list'.format(finished_build.name)
        server_list.append(finished_build)
        admin_passwords.append(building_passwords[server])
    else:
        print 'Server {0} errored during creation, so deleting'.format(
            finished_build.name)
        finished_build.delete()

# Print out info for the servers
for counter in range(len(server_list)):
    server_list[counter] = cs.servers.get(server_list[counter].id)
    print 'Name: {0}'.format(server_list[counter].name)
    print 'Server status: {0}'.format(server_list[counter].status)
    print 'ID: {0}'.format(server_list[counter].id)
    print 'Admin Password: {0}'.format(admin_passwords[counter])
    print 'Networks: {0}'.format(server_list[counter].networks)
    print 'IPv4 address: {0}\n'.format(server_list[counter].accessIPv4)

# Wait 1 minute
#print 'Waiting 1 minute...'
#time.sleep(60)

# Now kill all of the remaining servers
for counter in range(0, len(server_list)):
    print 'Deleting {0}'.format(server_list[counter].name)
    server_list[counter].delete()
