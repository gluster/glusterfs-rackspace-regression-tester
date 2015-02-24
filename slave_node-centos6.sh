#!/bin/bash

# Prepares a slave node
LOG_DIR=/tmp
COMMAND_LOG="$LOG_DIR/commands.log"

# Set the hostname of the server
ip addr show dev eth0 |grep 'inet '|cut -d ' ' -f 6|sed "s/\/24/   `hostname`/"|sed "s/.novalocal/.cloud.gluster.org/" >> /etc/hosts 2> ${COMMAND_LOG}
hostname `hostname|sed "s/.novalocal/.cloud.gluster.org/"` >> ${COMMAND_LOG} 2>&1

# Turn off requiretty for sudo, needed for rpm.t to succeed
sed -i "s/Defaults    requiretty/#Defaults    requiretty/" /etc/sudoers

# Create the mock user, needed for the regression tests
useradd -g mock mock >> ${COMMAND_LOG} 2>&1

# Disable eth1
sed -i 's/ONBOOT=yes/ONBOOT=no/' /etc/sysconfig/network-scripts/ifcfg-eth1

# Disable IPv6
sed -i 's/IPV6INIT=yes/IPV6INIT=no/' /etc/sysconfig/network-scripts/ifcfg-eth0
echo 'options ipv6 disable=1' > /etc/modprobe.d/ipv6.conf
chkconfig ip6tables off
sed -i 's/NETWORKING_IPV6=yes/NETWORKING_IPV6=no/' /etc/sysconfig/network
echo ' ' >> /etc/sysctl.conf
echo '# ipv6 support in the kernel, set to 0 by default' >> /etc/sysctl.conf
echo 'net.ipv6.conf.all.disable_ipv6 = 1' >> /etc/sysctl.conf
echo 'net.ipv6.conf.default.disable_ipv6 = 1' >> /etc/sysctl.conf
sed -i 's/v     inet6/-     inet6/' /etc/netconfig

# Remove IPv6 and eth1 interface from /etc/hosts
sed -i 's/^10\./#10\./' /etc/hosts
sed -i 's/^2001/#2001/' /etc/hosts

# Install ntpdate
yum -y install ntp
chkconfig ntpdate on
service ntpdate start

# Install OpenJDK, needed for Jenkins slaves
yum -y install java-1.7.0-openjdk

# Remove the OS provided GlusterFS packages, which conflicts with GlusterFS used in testing
yum remove -y glusterfs*

# Create the Jenkins user
useradd -G wheel jenkins
chmod 755 /home/jenkins

# Create the Jenkins .ssh directory
mkdir /home/jenkins/.ssh
chmod 700 /home/jenkins/.ssh
chown -R jenkins:jenkins /home/jenkins/.ssh

# Change the Python glusterfs site-packages directory to Jenkins ownership
chown jenkins:root /usr/lib/python2.6/site-packages/gluster/

# Install git from RPMForge
yum -y install http://pkgs.repoforge.org/rpmforge-release/rpmforge-release-0.5.3-1.el6.rf.x86_64.rpm
yum -y --enablerepo=rpmforge-extras update git

# Install the GlusterFS patch acceptance tests
git clone git://forge.gluster.org/gluster-patch-acceptance-tests/gluster-patch-acceptance-tests.git /opt/qa >> ${COMMAND_LOG} 2>&1

# Create the testing filesystem mount point
mkdir /d >> ${COMMAND_LOG} 2>&1

# If needed, creates a 10GB backing store
if [ -b /dev/xvde ]; then
    FS_DEVICE="/dev/xvde"
    FS_MOUNT_OPTIONS=""

    # Add the testing file system to /etc/fstab
    echo '/dev/xvde   /d   xfs   defaults   0 2' >> /etc/fstab
else
    # We don't have a separate disk, so need to create a loopback backing store
    dd if=/dev/zero of=/backingstore bs=1024 count=1 seek=10M >> ${COMMAND_LOG} 2>&1
    FS_DEVICE="/backingstore"
    FS_MOUNT_OPTIONS="-o loop"

    # Add the loopback file system to /etc/fstab
    echo '/backingstore           /d                      xfs     loop            0 2' >> /etc/fstab
fi

# Create the filesystem we run the regression tests on
mkfs.xfs -i size=512 -f ${FS_DEVICE} >> ${COMMAND_LOG} 2>&1
mount ${FS_MOUNT_OPTIONS} ${FS_DEVICE} /d >> ${COMMAND_LOG} 2>&1

# Create the directories needed for the regression testing
JDIRS="/var/log/glusterfs /var/lib/glusterd /var/run/gluster /d /d/archived_builds /d/backends /d/build /d/logs /home/jenkins/root"
mkdir -p $JDIRS
chown jenkins:jenkins $JDIRS
chmod 755 $JDIRS
ln -s /d/build /build

# Create the directories where regression logs are archived
ADIRS="/archives/archived_builds /archives/logs"
mkdir -p $ADIRS
chown jenkins:jenkins $ADIRS
chmod 755 $ADIRS

# Install Nginx
yum -y install http://nginx.org/packages/centos/6/noarch/RPMS/nginx-release-centos-6-0.el6.ngx.noarch.rpm
yum -y install nginx
sed -i 's/dport 22 -j ACCEPT/dport 22 -j ACCEPT\n-A INPUT -m conntrack --ctstate NEW -m tcp -p tcp --dport 80 -j ACCEPT/' /etc/sysconfig/iptables

# Copy the Nginx config file into place
cp -f /opt/qa/nginx/default.conf /etc/nginx/conf.d/default.conf

# Enable wheel group for sudo
sed -i 's/# %wheel\tALL=(ALL)\tNOPASSWD/%wheel\tALL=(ALL)\tNOPASSWD/' /etc/sudoers

# Remove qemu-img, which conflicts with glusterfs being built from source
yum -y remove qemu-img

# Enable yum-cron, so updates are automatically installed
chkconfig yum-cron on

# Indicate we've completed the script
echo 'complete' >> ${COMMAND_LOG}
