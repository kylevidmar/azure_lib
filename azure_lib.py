##########################################################
#  
#   Name:   AzureCLI
#
#   Purpose:  To create a class that contains functions
#             to support connections to supporting Linux
#             this is the base class.
#
#
###########################################################
import re
import logging
import time
import yaml
import os
import ast
from subprocess import check_output

log = logging.getLogger(__name__)

class AzureCLI():
    '''
    This is the base class for the Azure CLI. Allows you to login and do 
    Base manipulations of Azure. Can either login using Application-ID, 
    Directory-ID and Auth-Key, or by Username and Password. Make sure to 
    provide all the required parameters for chosen method.

    Initial Arguments:
            * self: is the container
            * appid: Azure Application ID to connect to, default None
            * dirid: Azure Directory ID to connect to, default None
            * key: Azure Secret Key used to connect, default None

            * username : Azure username, default None
            * pw : Azure Password, default None
    '''

    def __init__(self, appid=None, dirid=None, key=None, username=None, pw=None):
        '''Azure CLI base class __init__ will set global variables to use in object'''
        self.type       = 'azure'
        #Check which method using to login confirm all needed parameters included
        if (appid and dirid and key):
            self.appid = appid
            self.dirid = dirid
            self.key = key
        elif (username and pw):
            self.username = username
            self.pw = pw 
        else: 
            raise  ValueError("Either use Application-ID, Directory-ID and Auth-Key or Username and PW to login,"\
                             " make sure to provide all parameters of your chosen method")

        self.is_logged_in = False

    '''
    ************************************
    Azure Connectivity Functions
    ************************************
    '''

    def login_azure_cli(self):
        '''
        Purpose:
                Checks Azure CLI is installed on box then logs in with either 
                Username and Password or Application-ID, Directory-ID and Auth-Key
                depending on how azure object was initialized. If Azure-CLI not installed
                will attempt to install (this will only work on machines where logged in 
                as root or have admin permissions)
        Arguments:
                * self - Azure object
        '''

        # Confirm Azure CLI installed 
        try:
            output = check_output("which az", shell=True)
        except Exception as e:
            log.info("Azure CLI not installed on this machine : %s" %e)
            #Install Azure CLI 
            try:
                log.info("Attempting to install Azure-CLI, can take a few minutes")
                output = check_output("pip install azure-cli", shell=True)
                log.info("Azure CLI installed")
            except Exception as e:
                log.error("Unable to install Azure CLI: %s" %e)
                log.error(output)
                raise

        # Confirm able to login
        if self.appid:
            try:
                #Try to login with app-id, dir-id and auth-key
                check_output("az login -u %s --service-principal --tenant %s -p %s" %(self.appid, self.dirid, self.key), shell=True)
            except Exception as e:
                log.error("Unable to logon to Azure with App-ID, Dir-ID and Auth-Key %s" %e)
                raise

        elif self.username:
            try:
                #Try to login with username and pw
                check_output("az login -u %s -p %s" %(self.username, self.pw), shell=True)
            except Exception as e:
                log.error("Unable to logon to Azure with Username and Password %s" %e)
                raise

        log.info("Logged into Azure")
        self.is_logged_in = True

    def disconnect_azure(self):
        '''
        Purpose:
                Disconnects safely from Azure ClI
        Arguments:
                * self - Azure object
        '''

        try:
            #Try to logout
            check_output("az logout", shell=True)
        except Exception as e:
            log.error("Unable to logout %s" %(e))

    ''' 
    ************************************
    Azure Resource Group Functions
    ************************************
    '''
    def create_rg(self, rg_name, location="eastus"):
        '''
        Purpose:
                Creates new resource group
        Arguments:
                * self - Azure object
                * rg_name - Name of resource group to be created
                * location - Location for resource group, default = "eastus"
        '''

        try:
            #Try create resource group
            check_output("az group create --name %s --location %s" %(rg_name, location), shell=True)
        except Exception as e:
            log.error("Unable to create rg %s: %s" %(rg_name, e))
            raise

    def delete_rg(self, rg_name):
        '''
        Purpose:
                Deletes exisiting resource group
        Arguments:
                * self - Azure object
                * rg_name - Name of resource group to be deleted
        '''

        try:
            #Try to logout
            check_output("az group delete --name %s -y" %rg_name, shell=True)
        except Exception as e:
            log.error("Unable to delete rg %s: %s" %(rg_name, e))
            raise

    def list_rg(self, tags={'location':'eastus'}, json=False):
        '''
        Purpose:
                Gets list of Azure resource groups based on passed in tags
        Arguments:
                * self - Azure object
                * tags - dictionary containing tag id and tag value default = {'location':'eastus'}
                * json - If you want the data in json format, default False
        Returns:
                Azure resource groups as string or json depending on input
        '''

        # Concantinate all tags into a single string to pass to Azure ClI
        tag_str = ""
        for tag in tags:
            tag_str += "[?%s=='%s']" %(tag, tags[tag])

        if (json):
            out = check_output('az group list --query "%s"' %tag_str, shell=True)
        else: 
            out = check_output('az group list --query "%s" -o table' %tag_str, shell=True)

        #Check data isn't empty
        assert not out.isspace(), "No Resource Groups information collected"
        return out.decode('utf-8')

    def show_rg(self, rg_name, json=False):
        '''
        Purpose:
                Gets data about specific Azure resource group
        Arguments:
                * self - Azure object
                * rg_name - Name of Resource Group you want data about
                * json - If you want the data in json format, default False
        Returns:
                Azure resource group information as string or json depending on input
        '''

        if (json):
            out = check_output('az group show --name %s' %rg_name, shell=True)
        else:
            out = check_output('az group show --name %s -o table' %rg_name, shell=True)

         #Check data isn't empty
        assert not out.isspace(), "No information for Resource Group %s collected" %rg_name
        return out.decode('utf-8')

    ''' 
    ************************************
    Azure VNET Functions
    ************************************
    '''
    def create_vnet(self, name, rg_name, add_prefix=None, location="eastus", subnet_name=None, subnet_prefix=None):
        '''
        Purpose:
                Creates new Vnet - Either leave defaults for add_prefix, subnet_name and subnet_prefix\
                                   to use Azure's default prefix or define prefix and add subnet parameters\
                                   to define a vnet with a subnet
        Arguments:
                * self - Azure object
                * name - Azure vnet name
                * rg_name - Name of resource group to be created
                * add_prefix - Address prfix of vnet, optional defaults to Azure default (default = None)
                * location - Location for resource group, default = "eastus"
                * subnet_name -Optional name of subnet to add, default = None
                * subnet_prefix -Optional subnet prefix to add, default = None
        '''

        try:
            #Try to create vnet with or without subnet depending on parameters defined
            if add_prefix and subnet_prefix and subnet_name:
                check_output("az network vnet create -g %s -n %s --location %s --address-prefix %s"\
                    " --subnet-name %s --subnet-prefix %s" %(rg_name, name, location, add_prefix,\
                     subnet_name, subnet_prefix), shell=True)
            else:
                check_output("az network vnet create -g %s -n %s --location %s" %(rg_name, name, location), shell=True)
        except Exception as e:
            log.error("Unable to create vnet %s: %s" %(rg_name, e))
            raise

    def delete_vnet(self, name, rg_name):
        '''
        Purpose:
                Deletes exisiting vnet
        Arguments:
                * self - Azure object
                * name - Name of VNET you want to delete
                * rg_name - Name of resource group to be deleted
        '''

        try:
            #Try to logout
            check_output("az network vnet delete -n %s -g %s" %(name, rg_name), shell=True)
        except Exception as e:
            log.error("Unable to delete vnet %s: %s" %(name, e))
            raise

    def list_vnet(self, rg_name, json=False):
        '''
        Purpose:
                Gets list of Azure Vnets contained in resource group
        Arguments:
                * self - Azure object
                * rg _name - resource group you want to find VNETs associated with
                * json - If you want the data in json format, default False
        Returns:
                Azure vnets as string or json depending on input
        '''

        if (json):
            out = check_output('az network vnet list --resource-group %s' %rg_name, shell=True)
        else: 
            out = check_output('az network vnet list --resource-group %s -o table' %rg_name, shell=True)

        #Check data isn't empty
        assert not out.isspace(), "Unable to list VNET information"
        return out.decode('utf-8')

    def show_vnet(self, name, rg_name, json=False):
        '''
        Purpose:
                Gets data about specific Azure Vnet associated to a rg
        Arguments:
                * self - Azure object
                * name - Name of Vnet you want data about
                * rg_name - Name of Resource Group you want data about
                * json - If you want the data in json format, default False
        Returns:
                Azure vnet information as string or json depending on input
        '''

        if (json):
            out = check_output('az network vnet show -g %s -n %s' %(rg_name,name), shell=True)
        else: 
            out = check_output('az network vnet show -g %s -n %s -o table' %(rg_name,name), shell=True)

        #Check data isn't empty
        assert not out.isspace(), "Unable get information about VNET %s" %name
        return out.decode('utf-8')

    def add_vnet_subnet(self, name, rg_name, vnet_name, address_prefix, route_table=None):
        '''
        Purpose:
                Creates new subnet and attaches it to a vnet
        Arguments:
                * self - Azure object
                * name - Azure subnet name
                * rg_name - Name of resource group to be created unerder
                * vnet_name - Name of subnet
                * address_prefix - subnet Prefix to add
                * route_table - Optional Route-table you want to associate it with, default None
        '''

        try:
            #Try to create subnet and attach to a vnet
            if route_table:
                check_output("az network vnet subnet create -g %s -n %s --vnet-name %s --address-prefix %s --route-table %s"\
                             %(rg_name, name, vnet_name, address_prefix, route_table), shell=True)
            else:
                check_output("az network vnet subnet create -g %s -n %s --vnet-name %s --address-prefix %s"\
                             %(rg_name, name, vnet_name, address_prefix), shell=True)
        except Exception as e:
            log.error("Unable to create vnet subnet %s: %s" %(name, e))
            raise

    def delete_vnet_subnet(self, name, rg_name, vnet_name):
        '''
        Purpose:
                Delete subnet attached to a vnet
        Arguments:
                * self - Azure object
                * name - Azure subnet name to delete
                * rg_name - Name of resource group
                * vnet_name - Name of vnet subnet belongs to
        '''

        try:
            #Try to delete a subnet
            check_output("az network vnet subnet delete -g %s -n %s --vnet-name %s"\
                             %(rg_name, name, vnet_name), shell=True)
        except Exception as e:
            log.error("Unable to delete subnet %s: %s" %(name, e))
            raise

    def list_vnet_subnets(self, name, rg_name, json=False):
        '''
        Purpose:
                Gets data about Azure subnet
        Arguments:
                * self - Azure object
                * name - Name of Vnet you want subnet data about
                * rg_name - Name of Resource Group subnet is associated with
                * json - If you want the data in json format, default False
        Returns:
                List of Azure subnets associated with vnet in string or Json format
        '''

        if (json):
            out = check_output('az network vnet subnet list -g %s --vnet-name %s' %(rg_name,name), shell=True)
        else: 
            out = check_output('az network vnet subnet list -g %s --vnet-name %s -o table' %(rg_name,name), shell=True)

        #Check data isn't empty
        assert not out.isspace(), "Unable to list VNET Subnets information"
        return out.decode('utf-8')

    def show_vnet_subnet(self, name, rg_name, vnet_name, json=False):
        '''
        Purpose:
                Gets data about a specific Azure subnet associated to a vnet
        Arguments:
                * self - Azure object
                * name - Name of subnet you want data about
                * rg_name - Name of Resource Group vnet is associated with
                * vnet_name - Name of VNet subnet is associated with
                * json - If you want the data in json format, default False
        Returns:
                Azure subnet information as string or json depending on input
        '''

        if (json):
            out = check_output('az network vnet subnet show -g %s -n %s --vnet-name %s' %(rg_name,name, vnet_name), shell=True)
        else: 
            out = check_output('az network vnet subnet show -g %s -n %s --vnet-name %s -o table'\
                        %(rg_name,name,vnet_name), shell=True)

        #Check data isn't empty
        assert not out.isspace(), "Unable to get information about Subnet VNET %s" %name
        return out.decode('utf-8')
 
    ''' 
    ************************************
    Azure Deployment Functions
    ************************************
    '''
    def create_parameter_file(self, parameter_template, testbed_file, output_file_path, yaml_object= "azure"):
        '''
        Purpose:
                Method to create parameter file from information in testbed YAML file and parameter template
                file. Combines values from testbed YAML and places them in appropriate placeholders
                in parameter template file. This outputed parameter file can then be passed into the 
                deployment methods to be used with deployment templates 
        Arguments:
                * self - Azure object
                * parameter_template - Parameter template file to use
                * testbed_file - Testbed YAML file holding data for parameter template
                * output_file_path - Path of output file
                * yaml_object - Object in the YAML file the dictionary containing variable to be placed 
                                in the parameter_template live under ie testbed[azure] or testbed[asa]
                                default=Azure if the variables aren't under any object and be called by 
                                testbed[parameter]
        '''
        
        new_parameters = ""
        #Open files
        testbed = yaml.load(open(testbed_file, 'r'))
        parameters = open(parameter_template, 'r')
        new_param_file = open(output_file_path, 'w+')

        #Get specific object in testbed YAML file - Will usually be 'azure'
        if yaml_object:
            testbed = testbed[yaml_object]

        #Check each line in parameter template for place holder
        #if placeholder found update with relevant data from testbed file
        lines = parameters.readlines()
        for line in lines:
            if '[' and ']' in line:
                m = re.search(r'\[(\w*)\]', line)
                new_line = line.replace(m.group(0), '"'+ testbed[m.group(1)]+ '"')
                line = new_line
            #Write new parameter file
            new_parameters += (line)
            new_param_file.write(line)

        #Close all files
        new_param_file.close()
        parameters.close()

    def deploy_from_template_custom_image(self, resource_group, storage_name, image_path, template_file,
                                            parameter_file, location='eastus', storage_container_name="images"):
        '''
        Purpose:
                Creates new deployment using custom image - Have to create a resource group and storage container to 
                store custom image then copy over the custom image to the new storage container. Will then attempt to 
                deploy template passed in. Note if this fails please remember to delete resource group in any cleanup done
        Arguments:
                * self - Azure object
                * resource_group - Name of resource group to created
                * storage_name - Name of storage container to be created
                * image_path - Path to custom image to be copied to storage container and then deployed
                * template_file - path to file to use for deployment
                * parameter_file - Parameter file to be combined with Template file for deployment
                * location - Location of deployment default 'eastus'
                * storage_container_name - Name of storage container - defaults to 'images', which is what is defined 
                                           in template file - do not change to different value unless you know 
                                           what you are doing and have matching value in template file
        '''
        try:
            # Create Resource Group
            self.create_rg(resource_group, location)
            log.info("Resource Group %s Created" %resource_group)

            # Create Storage and Storage Container
            self.create_storage(storage_name, resource_group, location)
            log.info("Storage %s Created" %storage_name)

            self.create_storage_container(storage_container_name, resource_group, storage_name)
            log.info("Storage Container %s Created" %storage_container_name)

            # Copy custom image onto storage container 
            self.upload_vhd_to_container(storage_container_name, storage_name, resource_group, image_path)
            log.info("Image %s uploaded to Storage container %s" %(image_path, storage_container_name))

        except Exception as e:
            log.error("Unable to set up the resource group and storage to deploy template to: %s" %e)
            raise

        # Deploy template
        try:
            #Try create deployment
            log.info("Image on Azure, now deploying Template, can take a few minutes")
            check_output("az group deployment create -g %s --template-file %s --parameters %s" %(resource_group, template_file, parameter_file), shell=True)
            log.info("Template deployed")
        except Exception as e:
            log.error("Unable to deploy template %s" %e)
            raise

    def deploy_from_template_mp_image(self, rg_name, location, template_file, parameter_file):
        '''
        Purpose:
                Creates new deployment using Marketplace Image, will check if resource group is created
                if not will create one. If this fails please remember to delete resource group created
        Arguments:
                * self - Azure object
                * rg_name - Resource Group name
                * template_file - path to azure template file to use for deployment
                * parameter_file - path to file containing parameters needed for deployment
        Returns:
                Output from successful deployment
        '''
        #Check if resource group exists - If not create it
        try:
            # See if able to get resource group information
            self.show_rg(rg_name)
            log.info("Resource group %s already exists" %rg_name)
        except:
            # If unable to get rg information make new one then continue
            log.info("Creating Resoucre group %s" %rg_name)
            self.create_rg(rg_name, location)

        # Deploy template
        try:
            #Try create deployment
            out = check_output("az group deployment create -g %s --template-file %s --parameters %s" %(rg_name, template_file, parameter_file), shell=True)
        except Exception as e:
            log.error("Unable to deploy template: %s" %(e))
            raise

    '''
    ************************************
    Azure VM Functions
    ************************************
    '''

    def deploy_linux(self, name, rg_name, vnet_name, subnet_name, username="automation-admin", pw="Cisco-123123"):
        '''
        Purpose:
                Creates basic linux VM
        Arguments:
                * self - Azure object
                * name - Name of Linux VM
                * rg_name - Name of resource group associated with Linux VM
                * vnet_name - Name of Vnet 
                * subnet_name - Name of subnet in Vnet
                * username - Username of VM defaul = automation-admin
                * pw - Password of VM deault = Cisco-123123 
        Returns:
                Output from successful deployment - Includes public and private IP addreses in dictionary
        '''
        #Deploy Linux 
        try:
            #Try create deployment
            out = check_output("az vm create -n %s -g %s --admin-username %s --admin-password %s --image UbuntuLTS --vnet-name %s --subnet %s"\
                             %(name, rg_name, username, pw, vnet_name, subnet_name), shell=True)
            out = out.decode('utf-8')
        except Exception as e:
            log.error("Unable to deploy Linux: %s" %( e))
            raise

        #Confirm VM running is seen in output
        assert  "VM running" in out, "Linux Deployment not sucessful: %s" %out
        return out

    def delete_linux(self, name, rg_name):
        '''
        Purpose:
                Deletes existing linux VM
        Arguments:
                * self - Azure object
                * name - Name of Linux VM
                * rg_name - Name of resource group associated with Linux VM
        '''
        #Delete Linux VM and all things associated with it 
        log.info("Deleting Linux VM %s" %name)
        try:
            check_output("az vm delete -n %s -g %s --yes" %(name, rg_name), shell=True)
        except Exception as e:
            log.error("Unable to delete Linux: %s" %( e))
            raise

        log.info("Try to delete remaining resources associated with linux %s" %name)
        try:
            #delete associated disk
            self.delete_disk(rg_name, name)
            log.info("Deleted disk")

            #delete associated NIC
            self.delete_nic(rg_name, name)
            log.info("Deleted network interface")

            #delete associated NSG
            self.delete_nsg(rg_name, name)
            log.info("Deleted network security group")

            #delete associated Public IP
            self.delete_public_ip(rg_name, name)
            log.info("Deleted public IP")

            #Check all resources with name are deleted
            output= self.list_resources(rg_name)
            assert name not in output, "Some resources with name %s remaining: %s" %(name,output)
            log.info("All additional resources sucessfully deleted")

        except Exception as e:
            log.error("Unable to delete all resources associated with Linux %s : %s" %(name, e))
            raise

    def list_vm(self, rg_name, json=False):
        '''
        Purpose:
                Lists Azure VM associated with a resource_group
        Arguments:
                * self - Azure object
                * rg_name - Resource group VMs are associated with
                * json - If you want the data in json format, default False
        '''
        try:
            #Try to delete route table
            if(json):
                out = check_output("az vm list -g %s" %(rg_name), shell=True)
            else:
                out = check_output("az vm list -g %s -o table" %(rg_name), shell=True)
        except Exception as e:
            log.error("Unable to list vms %s" %(e))
            raise

        #Check data isn't empty
        assert not out.isspace(), "Unable to list VMs"
        return out.decode('utf-8')

    def list_resources(self, rg_name, json=False):
        '''
        Purpose:
                Lists Azure resources associated with resource_group
        Arguments:
                * self - Azure object
                * rg_name - Resource group resources are associated with
                * json - If you want the data in json format, default False
        '''
        try:
            #Try to delete route table
            if(json):
                out = check_output("az resource list -g %s" %(rg_name), shell=True)
            else:
                out = check_output("az resource list -g %s -o table" %(rg_name), shell=True)
        except Exception as e:
            log.error("Unable to list resources %s" %(e))

        #Check data isn't empty
        assert not out.isspace(), "Unable to list Resources associated with resource group %s" %rg_name
        return out.decode('utf-8')

    '''
    ************************************
    Azure Route-Table and Route Functions
    ************************************
    '''

    def show_all_route_tables(self, rg_name, json=False):
        '''
        Purpose:
                Gets data about Azure route tables associated with resource group
        Arguments:
                * self - Azure object
                * rg_name - Resource group you want route-tables in
                * json - If you want the data in json format, default False
        Returns:
                Azure route-table information as string or json depending on input
        '''

        if (json):
            out = check_output("az network route-table list -g %s" %rg_name, shell=True)
        else: 
            out = check_output("az network route-table list -g %s -o table" %rg_name, shell=True)

        #Check data isn't empty
        assert not out.isspace(), "Unable to list route tables associated with resource group %s" %rg_name
        return out.decode('utf-8')

    def show_route_table(self, rg_name, route_table, json=False):
        '''
        Purpose:
                Gets data about specific Azure route table, To see route information have json=True
        Arguments:
                * self - Azure object
                * rg_name - Resource group route-table is associated with
                * route_table - Route-table to collect info on
                * json - If you want the data in json format, default False
        Returns:
                Azure route-table information as string or json depending on input
        '''

        if (json):
               out = check_output("az network route-table show -g %s -n %s" %(rg_name, route_table), shell=True)
        else: 
               out = check_output("az network route-table show -g %s -n %s -o table" %(rg_name, route_table), shell=True)

        #Check data isn't empty
        assert not out.isspace(), "Unable get information about route-table %s" %route_table
        return out.decode('utf-8')

    def show_routes(self, rg_name, route_table, json=False):
        '''
        Purpose:
                Gets data about Azure routes in route table
        Arguments:
                * self - Azure object
                * rg_name - Resource group route-table is associated with
                * route_table - Route-table to collect route info on
                * json - If you want the data in json format, default False
        Returns:
                Azure route information as string or json depending on input
        '''

        if (json):
            out = check_output("az network route-table route list -g %s --route-table-name %s" %(rg_name, route_table), shell=True)
        else: 
            out = check_output("az network route-table route list -g %s --route-table-name %s -o table" %(rg_name, route_table), shell=True)

        #Check data isn't empty
        assert not out.isspace(), "Unable get information about routes in route-table %s" %route_table
        return out.decode('utf-8')

    def add_route_table(self, rg_name, route_table):
        '''
        Purpose:
                Adds Azure Route-Table
        Arguments:
                * self - Azure object
                * rg_name - Resource group route-table is associated with
                * route_table - Route-table to be added
        '''

        try:
            #Try to add route table
            check_output("az network route-table create -g %s -n %s" %(rg_name, route_table), shell=True)
        except Exception as e:
            log.error("Unable to add route-table %s: %s" %(route_table,e))
            raise

    def delete_route_table(self, rg_name, route_table):
        '''
        Purpose:
                Delete Azure Route-Table
        Arguments:
                * self - Azure object
                * rg_name - Resource group route-table is associated with
                * route_table - Route-table to be added
        '''

        try:
            #Try to delete route table
            check_output("az network route-table delete -g %s -n %s" %(rg_name, route_table), shell=True)
        except Exception as e:
            log.error("Unable to delete route-table %s: %s" %(route_table,e))
            raise

    def add_route(self, rg_name, route_table, route, prefix, next_hop_add, next_hop_type="VirtualAppliance"):
        '''
        Purpose:
                Adds Azure Route
        Arguments:
                * self - Azure object
                * rg_name - Resource group route-table is associated with
                * route_table - Route-table route to be added
                * route - Route to be added
                * prefix - Address prefix to which route applies
                * next_hop_type - The type of Azure hop the packet should be sent to.  Allowed\
                                 values: Internet, None, VirtualAppliance, VirtualNetworkGateway,\
                                 VnetLocal. Default to VirtualAppliance
                * next_hop_add - The IP address packets should be forwarded to when using the\
                                    VirtualAppliance hop type.
        '''

        try:
            #Try to create route
            check_output("az network route-table route create -g %s -n %s --address-prefix "\
            "%s --next-hop-type %s --route-table-name %s --next-hop-ip-address %s"\
            %(rg_name, route, prefix, next_hop_type, route_table, next_hop_add), shell=True)
        except Exception as e:
            log.error("Unable to add route %s: %s" %(route,e))
            raise

    def delete_route(self, rg_name, route_table, route):
        '''
        Purpose:
                Delete Azure Route
        Arguments:
                * self - Azure object
                * rg_name - Resource group route-table is associated with
                * route_table - Route-table route to be deleted on
                * route - Route to be deleted
        '''

        try:
            #Try to delete route
            check_output("az network route-table route delete -g %s -n %s --route-table-name %s"\
                         %(rg_name, route, route_table), shell=True)
        except Exception as e:
            log.error("Unable to delete route %s: %s" %(route,e))
            raise

    '''
    ************************************
    Azure Network Functions
    ************************************
    '''

    def delete_public_ip(self, rg_name, vm_name, pip_name=None):
        '''
        Purpose:
                Deletes Azure public IP
        Arguments:
                * self - Azure object
                * rg_name - Resource group PIP is associated with
                * vm_name - VM associated with PIP important to make sure deleted
                * pip_name - Name of Public IP to delete -Optional as will use VM name+PublicIP
                            as default - this is the format for azure generated public IPs 
        '''
        # Check vm Deleted 
        assert vm_name not in self.list_vm(rg_name), "VM is still present delete before deleting Public IP"

        #If disk name not given get disk name
        if not pip_name:
            pip_name = vm_name+"PublicIP"

        try:
            #Try to delete public IP
            check_output("az network public-ip delete -n %s -g %s" %(pip_name, rg_name), shell=True)
        except Exception as e:
            log.error("Unable to delete Public IP %s: %s" %(pip_name,e))
            raise

    def list_pip(self, rg_name, json=False):
        '''
        Purpose:
                Lists Azure Public IPs associated with a resource_group
        Arguments:
                * self - Azure object
                * rg_name - Resource group public-ip are associated with
                * json - If you want the data in json format, default False
        Returns: 
               Azure public Ips associated with a resource group in string or json
        '''
        try:
            #List public IP
            if(json):
                out = check_output("az network public-ip list-g %s" %(rg_name), shell=True)
            else:
                out = check_output("az network public-ip list -g %s -o table" %(rg_name), shell=True)
        except Exception as e:
            log.error("Unable to list public-ip %s" %(e))
            raise

        #Check data isn't empty
        assert not out.isspace(), "Unable to list public IPs"
        return out.decode('utf-8')

    def get_public_ip_from_vm(self, pip_name, rg_name):
        '''
        Purpose:
                Extract public IP from existing VM 
        Arguments:
                * self - Azure object
                * pip_name - Name of Public IP
                * rg_name - Name of resource group associated with VM
        Returns:
                Public IP in string format
        '''

        #Get all public IPs associated with resource group
        out = self.list_pip(rg_name)
        assert out, "Unable to get Public IP information: %s" %out.decode('utf-8')

        #Use regex to find public IP
        m = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) .* %s' %pip_name, out)
        assert m, "Unable to find public ip in output %s" %out
        return m.group(1).strip()

    def list_nsg(self, rg_name, json=False):
        '''
        Purpose:
                Lists Azure Network Security Groups associated with a resource_group
        Arguments:
                * self - Azure object
                * rg_name - Resource group nsg are associated with
                * json - If you want the data in json format, default False
        Returns: 
               Azure Network Security Groups associated with a resource group in string or json
        '''
        try:
            #Try to list nsg
            if(json):
                out = check_output("az network nsg list -g %s" %(rg_name), shell=True)
            else:
                out = check_output("az network nsg list -g %s -o table" %(rg_name), shell=True)
        except Exception as e:
            log.error("Unable to list nsg %s" %(e))
            raise

        #Check data isn't empty
        assert not out.isspace(), "Unable to list network securit groups associated with resource group %s" %rg_name
        return out.decode('utf-8')

    def delete_nsg(self, rg_name, vm_name, nsg_name=None):
        '''
        Purpose:
                Delete Azure Network Security Group
        Arguments:
                * self - Azure object
                * rg_name - Resource group NSG is associated with
                * vm_name - VM associated with NSG important to make sure deleted
                * nsg_name - Name of network security group to delete -Optional as will use VM name+NSG
                            as default - this is the format for azure generated NSGs
        '''
        # Check vm Deleted 
        assert vm_name not in self.list_vm(rg_name), "VM is still present delete before deleting NSG"

        #If nsg name not given get nsg name
        if not nsg_name:
            nsg_name = vm_name+"NSG"

        try:
            #Try to delete nsg
            check_output("az network nsg delete -n %s -g %s" %(nsg_name, rg_name), shell=True)
        except Exception as e:
            log.error("Unable to delete NSG %s: %s" %(nsg_name,e))
            raise
  
    def list_nic(self, rg_name, json=False):
        '''
        Purpose:
                Lists Azure Network Interface associated with a resource_group
        Arguments:
                * self - Azure object
                * rg_name - Resource group nics are associated with
                * json - If you want the data in json format, default False
        Returns: 
               Azure Network Interfaces associated with a resource group in string or json
        '''
        try:
            #List azure nics
            if(json):
                out = check_output("az network nic list -g %s" %(rg_name), shell=True)
            else:
                out = check_output("az network nic list -g %s -o table" %(rg_name), shell=True)
        except Exception as e:
            log.error("Unable to list nic %s" %(e))
            raise

        #Check data isn't empty
        assert not out.isspace(), "Unable to list network interfaces associated with resource group %s" %rg_name
        return out.decode('utf-8')

    def delete_nic(self, rg_name, vm_name, nic_name=None):
        '''
        Purpose:
                Delete Azure Network Interface
        Arguments:
                * self - Azure object
                * rg_name - Resource group NIC is associated with
                * vm_name - VM associated with NIC important to make sure deleted
                * nsg_name - Name of network interface to delete -Optional as will use VM name+VMNic
                            as default - this is the format for azure generated NSGs
        '''
        # Check vm Deleted 
        assert vm_name not in self.list_vm(rg_name), "VM is still present delete before deleting NIC"

        #If nic name not given get nsg name
        if not nic_name:
            nic_name = vm_name+"VMNic"

        try:
            #Try to delete nic
            check_output("az network nic delete -n %s -g %s" %(nic_name, rg_name), shell=True)
        except Exception as e:
            log.error("Unable to delete NIC %s: %s" %(nic_name,e))
            raise
  
    '''
    ************************************
    Azure Public IP Functions
    ************************************
    '''

    def delete_disk(self, rg_name, vm_name, disk_name=None):
        '''
        Purpose:
                Delete Azure Managed disk
        Arguments:
                * self - Azure object
                * rg_name - Resource group disk is associated with
                * vm_name - VM associated with Disk important to make sure deleted
                * disk_name - Name of disk to delete -Optional as will use VM name to 
                              find name of disk if not given
                
        '''

        # Check vm Deleted 
        assert vm_name not in self.list_vm(rg_name), "VM is still present delete before deleting disk"

        #If disk name not given get disk name
        if not disk_name:
            disk_name = self.get_disk_name(rg_name, vm_name)

        try:
            #Try to delete disk
            check_output("az disk delete -n %s -g %s --yes" %(disk_name, rg_name), shell=True)
        except Exception as e:
            log.error("Unable to delete disk %s: %s" %(disk_name,e))
            raise

    def list_disk(self, rg_name, json=False):
        '''
        Purpose:
                Lists Azure Managed disk associated with a resource_group
        Arguments:
                * self - Azure object
                * rg_name - Resource group disks are associated with
                * json - If you want the data in json format, default False
        Returns: 
               Azure disks associated with a resource group in string or json
        '''
        try:
            #Try to delete route table
            if(json):
                out = check_output("az disk list -g %s" %(rg_name), shell=True)
            else:
                out = check_output("az disk list -g %s -o table" %(rg_name), shell=True)
        except Exception as e:
            log.error("Unable to list disks %s" %(e))

        #Check data isn't empty
        assert not out.isspace(), "Unable to list disks associated with resource group %s" %rg_name
        return out.decode('utf-8')

    def get_disk_name(self, rg_name, vm_name):
        '''
        Purpose:
                Lists Azure Managed disk associated with a resource_group and 
                extracts the name of the disk based on the name of the VM the 
                disk is associated with. Disk name will usually be vm_name_OsDisk_1_...
        Arguments:
                * self - Azure object
                * rg_name - Resource group disks are associated with
                * vm_name - Name of the VM
        Returns: 
               Name of disk associated with VM name passed in, if potential diskname 
               is not found will return None
        '''
        disks = self.list_disk(rg_name)

        #Confirm vm we want is in Disk list
        assert vm_name in disks, "VM %s is not present in disks %s" %(vm_name, disks)

        #Extract disk name 
        m = re.search(r"(" + re.escape(vm_name)+ r"_\w*)", disks)
        try:
            disk_name = m.group(1).strip()
        except:
            #Do not raise exception just continue on
            log.error("Unable to find VM disk name in disks")
            disk_name = None

        return disk_name

    ''' 
    ************************************
    Azure Storage Functions
    ************************************
    '''

    def create_storage(self, name, rg_name, location="eastus", sku="Standard_LRS"):
        '''
        Purpose:
                Creates new Storage Account
        Arguments:
                * self - Azure object
                * name - Azure storage account name
                * rg_name - Name of resource group to be under
                * location - Location for resource group, default = "eastus"
                * sku - Storage Account SKU - defaul to Standard_LRS. accepted values: Premium_LRS,
                        Standard_GRS,Standard_LRS, Standard_RAGRS, Standard_ZRS
        '''

        try:
            #Try to create storage account
            check_output("az storage account create -g %s -n %s -l %s --sku %s"
                         %(rg_name, name, location, sku), shell=True)
        except Exception as e:
            log.error("Unable to create storage %s: %s" %(name, e))
            raise

    def delete_storage(self, name, rg_name):
        '''
        Purpose:
                Deletes exisiting Storage account
        Arguments:
                * self - Azure object
                * name - Name of Storage account you want to delete
                * rg_name - Name of resource group to be deleted
        '''

        try:
            #Try to logout
            check_output("az storage account delete -n %s -g %s --yes" %(name, rg_name), shell=True)
        except Exception as e:
            log.error("Unable to delete storage %s: %s" %(name, e))
            raise

    def list_storage(self, rg_name, json=False):
        '''
        Purpose:
                Gets list of Azure Storage Acounts based on passed in resource group
        Arguments:
                * self - Azure object
                * rg_name - resource group you want to find storage accounts associated with
                * json - If you want the data in json format, default False
        Returns:
                Azure storange accounts as string or json depending on input
        '''

        if (json):
            out = check_output('az storage account list -g %s' %rg_name, shell=True)
        else: 
            out = check_output('az storage account list -g %s -o table' %rg_name, shell=True)

        #Check data isn't empty
        assert not out.isspace(), "Unable to list storage_accounts associated with resource group %s" %rg_name
        return out.decode('utf-8')

    def show_storage(self, name, rg_name, json=False):
        '''
        Purpose:
                Gets data about Azure Storage account associated to a rg
        Arguments:
                * self - Azure object
                * name - Name of Storage account you want data about
                * rg_name - Name of Resource Group associated with
                * json - If you want the data in json format, default False
        Returns:
                Azure storage account information as string or json depending on input
        '''

        if (json):
            out = check_output('az storage account show -g %s -n %s' %(rg_name,name), shell=True)
        else: 
            out = check_output('az storage account show -g %s -n %s -o table' %(rg_name,name), shell=True)

        #Check data isn't empty
        assert not out.isspace(), "Unable to get information about Storage Account %s" %name
        return out.decode('utf-8')

    def get_storage_keys(self, storage_name, rg_name):
        '''
        Purpose:
                Gets data about Azure Storage Keys
        Arguments:
                * self - Azure object
                * storage_name - Name of Storage account you want data about
                * rg_name - Name of Resource Group associated with
        Returns:
                Dictionary of Azure storage keys in format {"keyname":"key",...}
        '''
        out = check_output('az storage account keys list -n %s -g %s' %(storage_name, rg_name),
                           shell=True)

        #Check data isn't empty
        assert not out.isspace(), "Unable to get Storage Account Key information"

        #Decode and format output so it is represented by a list instead of byte string
        out= out.decode('utf-8')
        out = ast.literal_eval(out)

        # Extract keyname and key value
        keys = {}
        for key in out:
            keys[key['keyName']] = key['value']

        return(keys)

    def create_storage_container(self, name, rg_name, storage_name):
        '''
        Purpose:
                Creates storage container in existing Azure storage. First 
                gets keys from storage to use in authenticating container
                will use first key found
        Arguments:
                * self - Azure object
                * name - Name of container to be created
                * storage_name - Name of Storage account 
                * rg_name - Name of Resource Group associated with storage
        '''
        #Get key information from storage
        keys = self.get_storage_keys(storage_name, rg_name)
        #Get abritray key from list
        key = list(keys.values())[0]

        try:
            #Try to create storage account
            check_output("az storage container create -n %s --account-name %s --account-key %s"
                         %(name, storage_name, key), shell=True)
        except Exception as e:
            log.error("Unable to create storage container %s: %s" %(name, e))

    def list_storage_container(self, rg_name, storage_name, json=False):
        '''
        Purpose:
                Creates storage container in existing Azure storage. First 
                gets keys from storage to use in authenticating container
                will use first key found
        Arguments:
                * self - Azure object
                * storage_name - Name of Storage account 
                * rg_name - Name of Resource Group associated with storage
                * json - If you want the data in json format, default False
        Returns:
                Azure storange accounts as string or json depending on input
        '''
        #Get key information from storage
        keys = self.get_storage_keys(storage_name, rg_name)
        #Get abritray key from list
        key = list(keys.values())[0]

        if (json):
            out = check_output('az storage container list --account-name %s --account-key %s'
                             %(storage_name, key), shell=True)
        else: 
            out = check_output('az storage container list --account-name %s --account-key %s -o table'
                             %(storage_name, key), shell=True)

        #Check data isn't empty
        assert not out.isspace(), "Unable to list Storage Account information"
        return out.decode('utf-8')
  
    def delete_storage_container(self, name, rg_name, storage_name):
        '''
        Purpose:
                Deletes storage container in existing Azure storage. First 
                gets keys from storage to use in authenticating container
                will use first key found
        Arguments:
                * self - Azure object
                * name - Name of container to be created
                * storage_name - Name of Storage account 
                * rg_name - Name of Resource Group associated with storage
        '''
        #Get key information from storage
        keys = self.get_storage_keys(storage_name, rg_name)
        #Get abritray key from list
        key = list(keys.values())[0]

        try:
            #Try to create storage account
            check_output("az storage container delete -n %s --account-name %s --account-key %s"
                         %(name, storage_name, key), shell=True)
        except Exception as e:
            log.error("Unable to delete storage container %s: %s" %(name, e))

    def upload_vhd_to_container(self, container_name, storage_name, rg_name, file_path):
        '''
        Purpose:
                Uploads VHD file to existing container, Checks container exists
                then gets storage key, will use first key found. Then creates a blob named 
                after file (or just blob.vhd if error) to be uploaded which then will contain the file.
        Arguments:
                * self - Azure object
                * container_name - Name of container for file to be uploaded to
                * storage_name - Name of Storage account 
                * rg_name - Name of Resource Group associated with storage
                * file_path - path of file to upload - has to be accesible by Kick
        '''

        #Check container exists
        assert container_name in self.list_storage_container(rg_name,storage_name), \
               "Container %s does not currently exist, please create first" %container_name

        #Get key information from storage
        keys = self.get_storage_keys(storage_name, rg_name)
        #Get abritray key from list
        key = list(keys.values())[0]

        #Extract blob name from path - will be file name 
        m = re.search(r'^.*[\/\\](.*)', file_path)
        if not m:
            #Unable to extract name - just call it blob.vhd
            blob_name = "blob.vhd"
        else:
            blob_name = m.group(1).strip()

        try:
            #Try to upload file
            check_output("az storage blob upload  -n %s -c %s --account-name %s --account-key %s -f %s -t page"
                         %(blob_name, container_name, storage_name, key, file_path), shell=True)
        except Exception as e:
            log.error("Unable to upload file %s: %s" %(file_path, e))
       
