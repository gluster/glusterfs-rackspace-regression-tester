#!/usr/bin/env python
"""Simple snippet of code for retrieving metadata elements passed
to a VM using pyrax.  eg, if you created a new VM with this:

  meta = {'script_url': some_url}
  cs.servers.create(vm_name, os.id, size.id, meta=meta))

This code shows how to retrieve the 'script_url' data from inside
the VM.
"""

import os
import sys
import cPickle as pickle
from cloudinit import stages

if len(sys.argv) != 2:
    print '''ERROR: Wrong number of arguments.
Usage: {0} <metadata element name>

  eg: {0} script_url
'''.format(sys.argv[0], sys.argv[0])
    sys.exit(1)

element_name = sys.argv[1]

# Load the cloud-util cache
ci_config = stages.fetch_base_config()
ci_cache_dir = ci_config['system_info']['paths']['cloud_dir']
ci_cache_file = stages.util.load_file(
    os.path.join(ci_cache_dir, 'instance', 'obj.pkl'))
ci_cache = pickle.loads(ci_cache_file)

# If the metadata element doesn't exist, inform the user
if element_name not in ci_cache.metadata['meta']:
    print 'ERROR: No metadata element by that name'
    sys.exit(2)

# Display the metadata element
print ci_cache.metadata['meta'][element_name]