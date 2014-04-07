GlusterFS Regression Tester for Rackspace
=========================================

The "create_servers.py" script does most of the work here.

It has been written for Python 2.7, and was developed on OSX 10.7.

In theory it should work "out of the box" on any *nix-like system with Python
2.7.  Haven't yet confirmed it though, so please email me (justin@gluster.org)
if you do.

Status
------

Working when run against GlusterFS master branch.  Haven't yet tried other
branches.  There will likely be some small fixes needed on other branches for
this to pass 100%.

To Do
-----

* Add code to test specific GlusterFS branches and proposed patches, instead
  of just testing upstream master

* Add cloud-config files for other OS's.  eg Fedora, Ubuntu, NetBSD (where
  feasible)

* Add code to test further filesystem types, such as ext4, btrfs, and FFS (on
  NetBSD)

Setup
-----

__1. Create your Rackspace credentials file__

If you don't have a Rackspace username and API key yet, you'll need to create
them.  The API key can be generated (there's a button for it), after logging
in to the Rackspace UI (https://mycloud.rackspace.com).

Create a file called ".rackspace_cloud_credentials" in your home directory,
with the following contents:

    [rackspace_cloud]
    username = _your_rackspace_username_
    api_key = _your_rackspace_api-key_

eg:

    [rackspace_cloud]
    username = joe.bloggs
    api_key = 3a2bd72ab349ba43ce4954f0s36bf721

__2. Upload your public SSH key to Rackspace__

There is an "SSH Keys" tab in the Rackspace UI.  Upload your public SSH key
there.  You'll need to assign it a name, such as "MySSHKey", for use in the
next step.

__3. Update the "config" file with your SSH key details__

Update the "ssh_key_name" and "ssh_key_file" fields in the "config" file, in
this same git repo as the README.md you're reading now.

* The "ssh_key_name" field needs the name for your public SSH key. eg
  "MySSHKey" from the step above.
* The "ssh_key_file" field needs the path to the __private__ SSH key file
  matching the public one you uploaded.

__4. Install the Python "pyrax" module and it's dependencies__

    $ pip install pyrax

__5. Verify it works__

Try kicking off a new Rackspace regression testing instance using the basic
settings:

    $ ./create_servers.py -c remote_centos6.cfg

It should come back after a few minutes with a message like this:

    Waiting for yourname0
    Success, yourname0 built correctly

... with SSH login details for the VM after it.  Feel free to login to the VM
to see if it's working.  It should run an OS update process (potentially
rebooting), install all needed GlusterFS build dependencies, then build and
test GlusterFS.

Unfortunately, creating Rackspace VMs isn't completely reliable.  Sometimes it
will fail to create the requested VM for no apparent reason.  When this
happens, the script will automatically delete the failed VM, and notify you.

If this happens, and there is no obvious Python error onscreen (eg something
went wrong in the script), then just rerun the ./create_servers.py command to
try again.  It'll probably work.

Usage
-----

For just doing straightforward regression testing on CentOS 6.5 with a single
VM, use:

    $ ./create_servers.py -c remote_centos6.cfg

There are many more possibilities and options though.  Running
"./create_servers.py --help should display the full list of options available.
