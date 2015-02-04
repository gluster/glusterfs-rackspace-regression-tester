#!/usr/bin/env python
"""Run the GlusterFS regression test in Rackspace"""

import os
import sys
import getopt
import getpass
import time
import ConfigParser
import pyrax
from pygerrit.rest import GerritRestAPI

version = '0.0.6'
instance_type = '2 GB General Purpose v1'
os_requested = 'CentOS 6 (PVHVM)'
max_servers = 1
remove_servers = False
debug_tests = False


def usage(error_string=None):
    prog_name = sys.argv[0]
    if error_string:
        print 'ERROR: {0}'.format(error_string)
        print
    print 'Usage:'
    print
    print '{0}'.format(prog_name)
    print '{0} [options]'.format(prog_name)
    print
    print '  -b | --branch <string>    Uses git HEAD for the given branch'
    print '  -c | --cloud_init <file>  Provides the file to cloud-init'
    print '  -d | --debug              Sets the DEBUG variable for the tests'
    print '  -f | --flavour <string>   Flavour of server instance to create'
    print "                            Use 'list' to show available flavours"
    print '  -g | --gerrit <change #>  Gerrit change request number'
    print '  -h | --help               Display usage'
    print '  -n | --num_servers #      Create # number of servers'
    print '  -o | --os <string>        Which OS to use'
    print '  -r | --remove             Remove the servers after creating them'
    print '  -s | --script-url <URL>   Runs this script after server creation'
    print '  -t | --test <path>        Runs only a specific test'
    print
    print 'To create the default number of servers, use:'
    print
    print '  {0}'.format(prog_name)
    print
    print 'or to create a specific number of servers, use this:'
    print
    print '  {0} --num_servers #'.format(prog_name)
    print
    print 'To pass the servers a cloud-init configuration file, use:'
    print
    print '  {0} -c config_file'.format(prog_name)
    print
    print 'To show the available instance flavours, use:'
    print
    print '  {0} -f list'.format(prog_name)
    print
    print 'Examples:'
    print
    print '  {0} --num_servers 5'.format(prog_name)
    print
    print 'or'
    print
    print '  {0} --cloud_init configs/remote_centos6.cfg ' \
          '-n 10'.format(prog_name)
    print
    print 'or'
    print
    print '  {0} -c configs/remote_centos6.cfg ' \
          '-flavour "1 GB Performance"'.format(prog_name)
    print
    print 'or'
    print
    print '  {0} -c configs/remote_centos6.cfg ' \
          '-t tests/basic/rpm.t'.format(prog_name)
    print


# Display a startup banner
print 'Rackspace instance regression test launcher: v{0}\n'.format(version)

# Check the command line
try:
    opts, args = getopt.getopt(sys.argv[1:], 'b:c:df:g:hn:o:rs:t:',
                               ['branch=', 'cloud_init=', 'debug', 'flavour=',
                                'gerrit=', 'help', 'num_servers=', 'remove',
                                'script-url=', 'test='])

except getopt.GetoptError as err:
    # There was something wrong with the command line options
    usage(err)
    sys.exit(2)

# Parse any command line options and arguments
ci_config_path = 'configs/remote_centos6.cfg'
change_req = None
git_branch = 'master'
script_url = None
test_path = None
for o, a in opts:
    if o in ("-h", "--help"):
        usage()
        sys.exit()
    elif o in ("-b", "--branch"):
        git_branch = a
    elif o in ("-c", "--cloud_init"):
        ci_config_path = os.path.expanduser(a)
    elif o in ("-d", "--debug"):
        debug_tests = True
    elif o in ("-f", "--flavour"):
        instance_type = a
    elif o in ("-g", "--gerrit"):
        change_req = a
    elif o in ("-n", "--num_servers"):
        max_servers = int(a)
    elif o in ("-o", "--os"):
        os_requested = a
    elif o in ("-r", "--remove"):
        remove_servers = True
    elif o in ("-s", "--script-url"):
        script_url = a
    elif o in ("-t", "--test"):
        test_path = a
    else:
        assert False, "Unknown command line option"

# Read config file
config_file_path = os.path.join('config')
config = ConfigParser.ConfigParser()
config.read(config_file_path)
creds_file = os.path.expanduser(config.get('credentials', 'rackspace'))
ssh_key_file = os.path.expanduser(config.get('credentials', 'ssh_key_file'))
ssh_key_name = config.get('credentials', 'ssh_key_name')

# Set the credentials for using Rackspace
pyrax.set_setting('identity_type', 'rackspace')
pyrax.set_credential_file(creds_file)
cs = pyrax.cloudservers

# Select the Operating System
os_selected = None
os_list = cs.images.list()
if os_requested == 'list':
    print 'Available OSs'
    for os_option in os_list:
        print os_option.name
    print
    sys.exit(0)
for os_option in os_list:
    if os_option.name == os_requested:
        os_instance = os_option
if not os_instance:
    print('ERROR: The requested OS "{0}" '
          'does not exist'.format(os_requested))
    sys.exit(2)

# Select an instance type
instance = None
instance_list = cs.flavors.list()
if instance_type == 'list':
    print 'Available flavours:'
    for instance_option in instance_list:
        print instance_option.name
    print
    sys.exit(0)
for instance_option in instance_list:
    if instance_option.name == instance_type:
        instance = instance_option
if not instance:
    print('ERROR: The requested instance type "{0}" '
          'does not exist'.format(instance_type))
    sys.exit(2)

if instance_type != 'list':
    print "Creating {0} x {1} servers...".format(max_servers, instance_type)
    print

# Read the cloud-init configuration file
ci_config = open(ci_config_path, 'r').read()

# Add the script_url if one was given
meta = {'test_path': ''}
if script_url:
    meta['script_url'] = script_url
    ci_config += script_url + '\n'

# Add the test path if one was given
if test_path:
    meta['test_path'] = test_path

# If debug mode was requested, pass that via metadata
if debug_tests:
    meta['debug_tests'] = 'True'

# Pass the desired gerrit change request info via metadata
if change_req:
    # Retrieve the Gerrit ref info for the change request
    gerrit_server = GerritRestAPI(url='http://review.gluster.org')
    gerrit_request = '/changes/?q={0}&o=CURRENT_REVISION'.format(change_req)
    rev = gerrit_server.get(gerrit_request)
    ref = rev[0]['revisions'][rev[0]['revisions'].keys()[0]]['fetch']['http']['ref']

    # Pass the Gerrit Change Request # and the matching git reference
    meta['change_req'] = change_req
    meta['change_ref'] = ref

    # Ensure we have the matching git branch
    git_branch = rev[0]['branch']

# Pass the desired git branch name via metadata
meta['glusterfs_branch'] = git_branch

# Files to be injected info the new image
# * /var/run/reboot-required is to address a bug in cloud-utils 0.7.4,
#   which won't reboot the system unless this file is present when run.
#   It's just a flag file, so being empty is fine.
#   It can be removed when this bug is fixed in available cloud-utils.
files = {'/var/run/reboot-required': ''}

# Start creating the servers
building_servers = []
building_passwords = []
username = getpass.getuser()
for counter in range(max_servers):
    # Set the name of the VM in Rackspace
    if change_req:
        # Name the VM after the Gerrit change request
        node_name = 'gerrit{0}-{1}'.format(change_req, str(counter))
    else:
        # No change request, so name the VM after the user
        node_name = '{0}{1}'.format(username, str(counter))

    print 'Creating {0}'.format(node_name)
    building_servers.append(
            cs.servers.create(node_name, os_instance.id, instance.id,
                          key_name=ssh_key_name, files=files,
                          config_drive=True, userdata=ci_config,
                          meta=meta))
    building_passwords.append(building_servers[counter].adminPass)

# Wait 20 seconds (seems to help)
time.sleep(20)
print

# Wait until all of the servers are running
server_list = []
admin_passwords = []
for server in range(len(building_servers)):
    print 'Waiting for {0}'.format(building_servers[server].name)

    # Wait for the given server to become either ACTIVE or ERROR status
    finished_build = pyrax.utils.wait_until(building_servers[server],
                                            'status', ['ACTIVE', 'ERROR'],
                                            interval=60, attempts=10)

    # Check which status it changed to
    if finished_build.status == 'ACTIVE':
        print 'Success, {0} built correctly'.format(finished_build.name)

        # Add the server to the full list
        server_list.append(finished_build)
        admin_passwords.append(building_passwords[server])

    else:
        print 'Server {0} errored during creation, so deleting'.format(
            finished_build.name)
        finished_build.delete()

# Print out info for the servers
print
for counter in range(len(server_list)):
    server_list[counter] = cs.servers.get(server_list[counter].id)
    ip_addr = server_list[counter].accessIPv4
    print 'Server name: {0}'.format(server_list[counter].name)
    print 'Server ID: {0}'.format(server_list[counter].id)
    print 'IPv4 address: {0}'.format(ip_addr)
    print 'Root password: {0}'.format(admin_passwords[counter])
    print('SSH command: ssh -l root -i {0} -o UserKnownHostsFile=/dev/null '
          '-o StrictHostKeyChecking=no {1}'.format(ssh_key_file, ip_addr))
    print

# If requested, remove the servers (useful when testing)
if remove_servers:
    for counter in range(0, len(server_list)):
        print 'Deleting {0}'.format(server_list[counter].name)
        server_list[counter].delete()
