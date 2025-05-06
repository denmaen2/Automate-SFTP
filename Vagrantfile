# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Use a well-established box
  config.vm.box = "generic/ubuntu2004"
  
  # Increase boot timeout to 600 seconds (10 minutes)
  config.vm.boot_timeout = 600
  
  # Force insecure key usage
  config.ssh.insert_key = false
  
  # Define server names and port offsets
  servers = {
    "ubuntu-server-1" => 1,
    "ubuntu-server-2" => 2,
    "ubuntu-server-3" => 3
  }
  
  # Create three Ubuntu servers
  servers.each do |server_name, index|
    config.vm.define server_name do |node|
      # Set hostname
      node.vm.hostname = server_name
      
      # Use a different SSH port for each VM to avoid collision
      node.vm.network "forwarded_port", guest: 22, host: 2221 + index, id: "ssh"
      
      # Set up network adapter with static IP
      node.vm.network "private_network", ip: "192.168.56.#{100+index}"
      
      # Provider-specific configurations
      node.vm.provider "virtualbox" do |vb|
        # VM name in VirtualBox with timestamp to ensure uniqueness
        vb.name = "#{server_name}-#{Time.now.to_i}"
        
        # Hardware settings
        vb.memory = 2048
        vb.cpus = 1
        
        # Enable GUI to see installation progress
        vb.gui = true
        
        # Force network cable to be connected
        vb.customize ["modifyvm", :id, "--cableconnected1", "on"]
      end
      
      # Basic installation script for all VMs
      node.vm.provision "shell", inline: <<-SCRIPT
#!/bin/bash
echo "===== Setting up SSH insecure key authentication on #{server_name} ====="

# Update package lists
apt-get update

# Install required packages
apt-get install -y openssh-server rsync avahi-daemon libnss-mdns sshpass wget

# Setup vagrant user with insecure key
mkdir -p /home/vagrant/.ssh
wget --no-check-certificate https://raw.githubusercontent.com/hashicorp/vagrant/master/keys/vagrant.pub -O /home/vagrant/.ssh/authorized_keys
chmod 0700 /home/vagrant/.ssh
chmod 0600 /home/vagrant/.ssh/authorized_keys
chown -R vagrant:vagrant /home/vagrant/.ssh

# Modify SSH config for both key and password authentication
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak

# Update sshd_config to enable both password and key authentication
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config
sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/g' /etc/ssh/sshd_config
sed -i 's/#AuthorizedKeysFile/AuthorizedKeysFile/g' /etc/ssh/sshd_config

# Ensure password for vagrant user is set to 'vagrant'
echo "vagrant:vagrant" | chpasswd

# Create SFTP user group
groupadd -f sftpusers

# Create dedicated SFTP user if it doesn't exist
if ! id "sftptransfer" &>/dev/null; then
    useradd -m -g sftpusers -s /bin/bash sftptransfer
    # Set a simple password for SSH key exchange
    echo "sftptransfer:sftp123" | chpasswd
    
    # Allow user to use sudo without password (for setup only)
    echo "sftptransfer ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/sftptransfer
    
    # Set up SSH directory for SFTP user
    mkdir -p /home/sftptransfer/.ssh
    chmod 700 /home/sftptransfer/.ssh
    touch /home/sftptransfer/.ssh/authorized_keys
    chmod 600 /home/sftptransfer/.ssh/authorized_keys
    chown -R sftptransfer:sftpusers /home/sftptransfer/.ssh
    
    # Create SFTP directories
    mkdir -p /home/sftptransfer/sftp/incoming
    mkdir -p /home/sftptransfer/sftp/outgoing
    chown -R sftptransfer:sftpusers /home/sftptransfer/sftp
    chmod 775 /home/sftptransfer/sftp/incoming
    chmod 775 /home/sftptransfer/sftp/outgoing
    
    # Generate SSH key pair
    sudo -u sftptransfer ssh-keygen -t ed25519 -N "" -f /home/sftptransfer/.ssh/id_ed25519
fi

# Set up SFTP configuration in SSH config if not already configured
if ! grep -q "Match Group sftpusers" /etc/ssh/sshd_config; then
    tee -a /etc/ssh/sshd_config > /dev/null << EOF

# SFTP Server Configuration
Match Group sftpusers
    ChrootDirectory /home/%u
    X11Forwarding no
    AllowTcpForwarding no
    ForceCommand internal-sftp
EOF
fi

# Update hosts file with all server entries
cat > /etc/hosts << EOF
127.0.0.1 localhost #{server_name}
# The following lines are for the Vagrant multi-VM setup
192.168.56.101 ubuntu-server-1
192.168.56.102 ubuntu-server-2
192.168.56.103 ubuntu-server-3
EOF

# Restart SSH service
systemctl restart ssh
systemctl enable ssh

# Ensure avahi is running for hostname resolution
systemctl restart avahi-daemon
systemctl enable avahi-daemon

echo "===== Basic installation complete on #{server_name} ====="
SCRIPT
    end
  end
  
  # After all VMs are up, run key exchange script on ubuntu-server-3
  config.vm.define "ubuntu-server-3" do |node|
    node.vm.provision "shell", run: "always", inline: <<-SCRIPT
#!/bin/bash
echo "===== Starting key exchange process after all VMs are ready ====="

# Wait longer for all services to fully start
echo "Waiting 30 seconds for all SSH services to fully initialize..."
sleep 30

# Check SSH service status on the current machine
echo "Checking SSH service status..."
systemctl status ssh

# Function to get IP address of the eth1 interface
get_vm_ip() {
  ip addr show eth1 | grep -oP 'inet \\K[\\d.]+'
}

# Get the IP address of this VM
MY_IP=$(get_vm_ip)
echo "My IP address: $MY_IP"

# Check if sftptransfer user exists
if ! id "sftptransfer" &>/dev/null; then
  echo "Creating sftptransfer user..."
  useradd -m -g sftpusers -s /bin/bash sftptransfer
  echo "sftptransfer:sftp123" | chpasswd
  
  # Create SSH directory and key
  mkdir -p /home/sftptransfer/.ssh
  chmod 700 /home/sftptransfer/.ssh
  ssh-keygen -t ed25519 -N "" -f /home/sftptransfer/.ssh/id_ed25519
  chmod 600 /home/sftptransfer/.ssh/id_ed25519
  chown -R sftptransfer:sftpusers /home/sftptransfer/.ssh
fi

# Configure sftptransfer keys
SFTP_USER="sftptransfer"
SFTP_PASS="sftp123"
MY_PUBKEY=$(cat /home/$SFTP_USER/.ssh/id_ed25519.pub)

# First ping test to make sure network is up
echo "Testing network connectivity to other servers..."
for server in ubuntu-server-1 ubuntu-server-2; do
  echo "Trying to ping $server..."
  ping -c 3 $server || echo "Ping failed, but continuing..."
done

# Wait again to ensure SSH is fully up on all machines
sleep 10

# Simplified approach: directly copy keys rather than using ssh
# This creates local files with the keys to be copied
echo "Preparing key exchange files..."
for server in ubuntu-server-1 ubuntu-server-2; do
  echo "Preparing key for $server..."
  
  # Creating a script to be run on the destination server
  cat > /tmp/setup_key_$server.sh << EOF
#!/bin/bash
mkdir -p /home/sftptransfer/.ssh
echo "$MY_PUBKEY" >> /home/sftptransfer/.ssh/authorized_keys
chmod 700 /home/sftptransfer/.ssh
chmod 600 /home/sftptransfer/.ssh/authorized_keys
chown -R sftptransfer:sftpusers /home/sftptransfer/.ssh
EOF
  chmod +x /tmp/setup_key_$server.sh
done

# Try SCP transfer of the setup script
for server in ubuntu-server-1 ubuntu-server-2; do
  echo "Copying setup script to $server..."
  
  # Using sshpass with scp
  sshpass -p "vagrant" scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 /tmp/setup_key_$server.sh vagrant@$server:/tmp/ || {
    echo "SCP to $server failed, trying alternative approach..."
    
    # Alternative: Try direct ssh with the script content
    sshpass -p "vagrant" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 vagrant@$server "sudo bash -c 'mkdir -p /home/sftptransfer/.ssh && echo \"$MY_PUBKEY\" >> /home/sftptransfer/.ssh/authorized_keys && chmod 700 /home/sftptransfer/.ssh && chmod 600 /home/sftptransfer/.ssh/authorized_keys && chown -R sftptransfer:sftpusers /home/sftptransfer/.ssh'" || echo "SSH key setup on $server failed, but continuing..."
    continue
  }
  
  # Run the script with sudo on the remote server
  echo "Running setup script on $server..."
  sshpass -p "vagrant" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 vagrant@$server "sudo bash /tmp/setup_key_$server.sh" || echo "SSH key setup on $server failed, but continuing..."
done

# Test file transfers using the primary vagrant user
echo "Creating test files for transfer..."
echo "Test file from ubuntu-server-3" > /tmp/test_file.txt

for server in ubuntu-server-1 ubuntu-server-2; do
  echo "Attempting file transfer to $server as vagrant user..."
  sshpass -p "vagrant" scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 /tmp/test_file.txt vagrant@$server:/tmp/ || echo "File transfer to $server failed, but continuing..."
  
  # Verify the file was transferred
  sshpass -p "vagrant" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 vagrant@$server "ls -la /tmp/test_file.txt" || echo "File verification on $server failed, but continuing..."
done

echo "===== Key exchange process complete ====="
SCRIPT
  end
end
