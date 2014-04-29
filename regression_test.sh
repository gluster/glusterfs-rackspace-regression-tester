#!/bin/bash

# Prepares the server environment, builds Gluster, then runs the smoke and
# regression tests

# Set the locations we'll be using
ARCHIVED_BUILDS="/d/archived_builds"
BASE="/build/install"
LOG_DIR=/tmp
COMMAND_LOG="$LOG_DIR/commands.log"
PROGRESS_LOG="$LOG_DIR/progress.log"
BUILD_LOG="$LOG_DIR/build.log"
SMOKE_LOG="$LOG_DIR/smoke.log"
REGRESSION_LOG="$LOG_DIR/regression.log"

# Retrieve the Python version
PY_VER=`python -c "import sys; print sys.version[:3]"`

# Grab the rest of our scripts
REGRESSION_TESTER_BRANCH="master"
git clone -b "$REGRESSION_TESTER_BRANCH" git://forge.gluster.org/glusterfs-rackspace-regression-tester/glusterfs-rackspace-regression-tester.git /root/glusterfs-rackspace-regression-tester >> ${COMMAND_LOG} 2>&1
export PATH="/root/glusterfs-rackspace-regression-tester:${BASE}/sbin:${PATH}"

# Ensure Python finds the Gluster we're testing
export PYTHONPATH="${BASE}/lib/python${PY_VER}/site-packages:${PYTHONPATH}"

# Set HOME, which some tests seem to need
export HOME='/root'

# Set the hostname of the server
ip addr show dev eth0 |grep 'inet '|cut -d ' ' -f 6|sed "s/\/24/   `hostname`/"|sed "s/.novalocal/.cloud.gluster.org/" >> /etc/hosts 2> ${COMMAND_LOG}
hostname `hostname|sed "s/.novalocal/.cloud.gluster.org/"` >> ${COMMAND_LOG} 2>&1

# Turn off requiretty for sudo, needed for rpm.t to succeed
sed -i "s/Defaults    requiretty/#Defaults    requiretty/" /etc/sudoers

# Create the mock user, needed for the regression tests
useradd -g mock mock >> ${COMMAND_LOG} 2>&1

# Create the testing filesystem mount point
mkdir /d >> ${COMMAND_LOG} 2>&1

# If needed, creates a 10GB backing store
if [ -b /dev/xvde ]; then
    FS_DEVICE="/dev/xvde"
    FS_MOUNT_OPTIONS=""
else
    # We don't have a separate disk, so need to create a loopback backing store
    dd if=/dev/zero of=/backingstore bs=1024 count=1 seek=10M >> ${COMMAND_LOG} 2>&1
    FS_DEVICE="/backingstore"
    FS_MOUNT_OPTIONS="-o loop"
fi

# Create the filesystem we run the regression tests on
mkfs.xfs -i size=512 -f ${FS_DEVICE} >> ${COMMAND_LOG} 2>&1
mount ${FS_MOUNT_OPTIONS} ${FS_DEVICE} /d >> ${COMMAND_LOG} 2>&1

# Is there a specific branch of GlusterFS we should use?
GLUSTERFS_BRANCH=`metadata_retriever.py glusterfs_branch 2>/dev/null`
if [ x"$GLUSTERFS_BRANCH" = x'' ]; then
    export GLUSTERFS_BRANCH='master'
fi

# TODO: Remove this once http://review.gluster.org/#/c/7564/ is merged
# Workaround for GlusterFS release-3.x branch not compiling EPEL-7 yet
if [ x"$GLUSTERFS_BRANCH" = x'release-3.4' -o x"$GLUSTERFS_BRANCH" = x'release-3.5' ]; then
    rm -f /etc/mock/epel-7-x86_64.cfg
fi

# Prepare for building Gluster and running the tests
mkdir -p /d/archived_builds >> ${COMMAND_LOG} 2>&1
mkdir -p /d/build >> ${COMMAND_LOG} 2>&1
ln -s /d/build /build >> ${COMMAND_LOG} 2>&1
git clone -b ${GLUSTERFS_BRANCH} git://git.gluster.org/glusterfs.git /root/glusterfs >> ${COMMAND_LOG} 2>&1
git clone git://forge.gluster.org/gluster-patch-acceptance-tests/gluster-patch-acceptance-tests.git /opt/ >> ${COMMAND_LOG} 2>&1
cd /root/glusterfs >> ${COMMAND_LOG} 2>&1
chmod 755 /root >> ${COMMAND_LOG} 2>&1

# Build Gluster, install it under /d/build/install
echo "build - using GlusterFS '${GLUSTERFS_BRANCH}' branch" >> ${PROGRESS_LOG}
time /opt/qa/build.sh >> ${BUILD_LOG} 2>&1

# Run the smoke tests
echo 'smoke' >> ${PROGRESS_LOG}
time /opt/qa/smoke.sh >> ${SMOKE_LOG} 2>&1

# Should we set DEBUG mode for the tests?
DEBUG_CHECK=`metadata_retriever.py debug_tests 2>/dev/null`
if [ x"$DEBUG_CHECK" = x'True' ]; then
    export DEBUG=1
fi

# Should we run just one test, or all of the regression tests?
TEST_PATH=`metadata_retriever.py test_path 2>/dev/null`
if [ x"$TEST_PATH" = x'' ]; then
    # Run the full regression tests
    echo 'regression' >> ${PROGRESS_LOG}
    time /opt/qa/regression.sh >> ${REGRESSION_LOG} 2>&1
else
    # Run just the requested regression test
    echo "specific test: ${TEST_PATH}" >> ${PROGRESS_LOG}
    time ${TEST_PATH} >> ${REGRESSION_LOG} 2>&1
fi

# TODO: Send the results back to the collection server

# Indicate we've completed the script
echo 'complete' >> ${PROGRESS_LOG}
