import os
import base64
import socket
from django.db.models import F, Q
from xos.config import Config
from xos.settings import RESTAPI_HOSTNAME, RESTAPI_PORT
from observer.openstacksyncstep import OpenStackSyncStep
from core.models.sliver import Sliver
from core.models.slice import Slice, SlicePrivilege, ControllerSlice
from core.models.network import Network, NetworkSlice, ControllerNetwork
from observer.ansible import *
from observer.syncstep import *
from util.logger import observer_logger as logger

def escape(s):
    s = s.replace('\n',r'\n').replace('"',r'\"')
    return s

class SyncSlivers(OpenStackSyncStep):
    provides=[Sliver]
    requested_interval=0
    observes=Sliver
    playbook='sync_slivers.yaml'

    def get_userdata(self, sliver, pubkeys):
        userdata = '#cloud-config\n\nopencloud:\n   slicename: "%s"\n   hostname: "%s"\n   restapi_hostname: "%s"\n   restapi_port: "%s"\n' % (sliver.slice.name, sliver.node.name, RESTAPI_HOSTNAME, str(RESTAPI_PORT))
        userdata += 'ssh_authorized_keys:\n'
        for key in pubkeys:
            userdata += '  - %s\n' % key
        return userdata

    def map_sync_inputs(self, sliver):
        inputs = {}
	metadata_update = {}
        if (sliver.numberCores):
            metadata_update["cpu_cores"] = str(sliver.numberCores)

        for tag in sliver.slice.tags.all():
            if tag.name.startswith("sysctl-"):
                metadata_update[tag.name] = tag.value

	slice_memberships = SlicePrivilege.objects.filter(slice=sliver.slice)
        pubkeys = set([sm.user.public_key for sm in slice_memberships if sm.user.public_key])
        if sliver.creator.public_key:
            pubkeys.add(sliver.creator.public_key)

        if sliver.slice.creator.public_key:
            pubkeys.add(sliver.slice.creator.public_key)

        if sliver.slice.service and sliver.slice.service.public_key:
            pubkeys.add(sliver.slice.service.public_key)

        nics = []
        networks = [ns.network for ns in NetworkSlice.objects.filter(slice=sliver.slice)]
        controller_networks = ControllerNetwork.objects.filter(network__in=networks,
                                                                controller=sliver.node.site_deployment.controller)

        for controller_network in controller_networks:
            if controller_network.network.template.visibility == 'private' and \
               controller_network.network.template.translation == 'none':
                   if not controller_network.net_id:
                        raise Exception("Private Network %s has no id; Try again later" % controller_network.network.name)
                   nics.append(controller_network.net_id)

        # now include network template
        network_templates = [network.template.shared_network_name for network in networks \
                             if network.template.shared_network_name]

        #driver = self.driver.client_driver(caller=sliver.creator, tenant=sliver.slice.name, controller=sliver.controllerNetwork)
        driver = self.driver.admin_driver(tenant='admin', controller=sliver.node.site_deployment.controller)
        nets = driver.shell.quantum.list_networks()['networks']
        for net in nets:
            if net['name'] in network_templates:
                nics.append(net['id'])

        if (not nics):
            for net in nets:
                if net['name']=='public':
                    nics.append(net['id'])

        image_name = None
        controller_images = sliver.image.controllerimages.filter(controller=sliver.node.site_deployment.controller)
        if controller_images:
            image_name = controller_images[0].image.name
            logger.info("using image from ControllerImage object: " + str(image_name))

        if image_name is None:
            controller_driver = self.driver.admin_driver(controller=sliver.node.site_deployment.controller)
            images = controller_driver.shell.glanceclient.images.list()
            for image in images:
                if image.name == sliver.image.name or not image_name:
                    image_name = image.name
                    logger.info("using image from glance: " + str(image_name))

	try:
            legacy = Config().observer_legacy
        except:
            legacy = False

        if (legacy):
            host_filter = sliver.node.name.split('.',1)[0]
        else:
            host_filter = sliver.node.name.strip()

        availability_zone_filter = 'nova:%s'%host_filter
        sliver_name = '%s-%d'%(sliver.slice.name,sliver.id)

        userData = self.get_userdata(sliver, pubkeys)
        if sliver.userData:
            userData = sliver.userData

        controller = sliver.node.site_deployment.controller
        fields = {'endpoint':controller.auth_url,
                     'admin_user': sliver.creator.email,
                     'admin_password': sliver.creator.remote_password,
                     'admin_tenant': sliver.slice.name,
                     'tenant': sliver.slice.name,
                     'tenant_description': sliver.slice.description,
                     'name':sliver_name,
                     'ansible_tag':sliver_name,
                     'availability_zone': availability_zone_filter,
                     'image_name':image_name,
                     'flavor_name':sliver.flavor.name,
                     'nics':nics,
                     'meta':metadata_update,
                     'user_data':r'%s'%escape(userData)}
        return fields


    def map_sync_outputs(self, sliver, res):
	sliver_id = res[0]['info']['OS-EXT-SRV-ATTR:instance_name']
        sliver_uuid = res[0]['id']

	try:
            hostname = res[0]['info']['OS-EXT-SRV-ATTR:hypervisor_hostname']
            ip = socket.gethostbyname(hostname)
            sliver.ip = ip
        except:
            pass

        sliver.instance_id = sliver_id
        sliver.instance_uuid = sliver_uuid
        sliver.instance_name = sliver_name
        sliver.save()
	
	
    def map_delete_inputs(self, sliver):
        controller_register = json.loads(sliver.node.site_deployment.controller.backend_register)

        if (controller_register.get('disabled',False)):
            raise InnocuousException('Controller %s is disabled'%sliver.node.site_deployment.controller.name)

        sliver_name = '%s-%d'%(sliver.slice.name,sliver.id)
        controller = sliver.node.site_deployment.controller
        input = {'endpoint':controller.auth_url,
                     'admin_user': sliver.creator.email,
                     'admin_password': sliver.creator.remote_password,
                     'admin_tenant': sliver.slice.name,
                     'tenant': sliver.slice.name,
                     'tenant_description': sliver.slice.description,
                     'name':sliver_name,
                     'ansible_tag':sliver_name,
                     'delete': True}
        return input
