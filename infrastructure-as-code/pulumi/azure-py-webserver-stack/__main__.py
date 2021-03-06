import pulumi
from pulumi_azure import core, compute, network

config = pulumi.Config()
username = config.require("username")
password = config.require_secret("password")
location = config.require("location")

resource_group = core.ResourceGroup("server", location=location)

net = network.VirtualNetwork(
    "server-network",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    address_spaces=["10.0.0.0/16"],
    subnets=[network.VirtualNetworkSubnetArgs(
        name="default",
        address_prefix="10.0.1.0/24",
    )])

subnet = network.Subnet(
    "server-subnet",
    resource_group_name=resource_group.name,
    virtual_network_name=net.name,
    address_prefixes=["10.0.2.0/24"],
    enforce_private_link_endpoint_network_policies=False)

public_ip = network.PublicIp(
    "server-ip",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    allocation_method="Dynamic")

network_iface = network.NetworkInterface(
    "server-nic",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    ip_configurations=[network.NetworkInterfaceIpConfigurationArgs(
        name="webserveripcfg",
        subnet_id=subnet.id,
        private_ip_address_allocation="Dynamic",
        public_ip_address_id=public_ip.id,
    )])

userdata = """#!/bin/bash

echo "Hello, World!" > index.html
nohup python -m SimpleHTTPServer 80 &"""

vm = compute.VirtualMachine(
    "server-vm",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    network_interface_ids=[network_iface.id],
    vm_size="Standard_A0",
    delete_data_disks_on_termination=True,
    delete_os_disk_on_termination=True,
    os_profile=compute.VirtualMachineOsProfileArgs(
        computer_name="hostname",
        admin_username=username,
        admin_password=password,
        custom_data=userdata,
    ),
    os_profile_linux_config=compute.VirtualMachineOsProfileLinuxConfigArgs(
        disable_password_authentication=False,
    ),
    storage_os_disk=compute.VirtualMachineStorageOsDiskArgs(
        create_option="FromImage",
        name="myosdisk1",
    ),
    storage_image_reference=compute.VirtualMachineStorageImageReferenceArgs(
        publisher="canonical",
        offer="UbuntuServer",
        sku="16.04-LTS",
        version="latest",
    ))

combined_output = pulumi.Output.all(vm.id, public_ip.name, public_ip.resource_group_name)
public_ip_addr = combined_output.apply(
    lambda lst: network.get_public_ip(name=lst[1], resource_group_name=lst[2]))

pulumi.export("public_ip", public_ip_addr.ip_address)