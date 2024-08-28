##############################################################################
# COPYRIGHT Ericsson AB 2014
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

from litp.core.plugin import Plugin
from litp.core.validators import ValidationError
from litp.core.extension import ViewError
from lvm_driver.lvm_driver import LvmDriver
from vxvm_driver.vxvm_driver import VxvmDriver

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class VolMgrPlugin(Plugin):
    """
    LITP Volume Manager Plugin
    """

    def __init__(self):
        '''
        Constructor to instantiate Drivers
        '''

        super(VolMgrPlugin, self).__init__()
        self.lvm_driver = LvmDriver()
        self.vxvm_driver = VxvmDriver()

    def _validate_unique_fs_mountpoint(self, profile, rule_number):
        '''
        Validate that a File System Mount Point is unique
        for a given Storage Profile.
        '''

        preamble = '_validate_unique_fs_mountpoint: ' + rule_number + ': '

        errors = []

        for vg in profile.volume_groups:
            for fs in vg.file_systems:

                mounts = [fs1.mount_point for fs1 in \
                            [fs2 for vg1 in profile.volume_groups \
                                 for fs2 in vg1.file_systems]
                          if fs1 != fs]
                if fs.mount_point in mounts:
                    message = "File System mount_point in not " + \
                              "unique for this Storage profile"

                    log.trace.debug((preamble + "VG:%s FS:%s Error: %s") % \
                                    (vg.item_id, fs.item_id, message))

                    errors.append(ValidationError(item_path=fs.get_vpath(),
                                                  error_message=message))

        return errors

    def _validate_swap_fs_mountpoint(self, profile, rule_number):
        '''
        Validate that a File System with type 'swap' also
        has a mount_point of 'swap'
        '''

        preamble = '_validate_swap_fs_mountpoint: ' + rule_number + ': '

        errors = []

        for vg in profile.volume_groups:
            for fs in vg.file_systems:
                if fs.type == 'swap' and fs.mount_point != 'swap':
                    message = "A File System with type set to 'swap' " + \
                              "must also have a mount_point set to 'swap'"

                    log.trace.debug((preamble + "VG:%s FS:%s Error: %s") % \
                                    (vg.item_id, fs.item_id, message))

                    errors.append(ValidationError(item_path=fs.get_vpath(),
                                                  error_message=message))
        return errors

    def _validate_unique_vg_name(self, profile, rule_number):
        '''
        Validate that a Volume Group name is unique
        in a given Storage Profile
        '''

        preamble = '_validate_unique_vg_name: ' + rule_number + ': '

        errors = []

        for vg in profile.volume_groups:
            vg_names = [vg1.volume_group_name \
                        for vg1 in profile.volume_groups \
                        if vg1 != vg]
            if vg.volume_group_name in vg_names:
                message = "Volume Group name in not " + \
                          "unique for this Storage profile"

                log.trace.debug((preamble + "VG:%s Error: %s") % \
                                (vg.item_id, message))

                errors.append(ValidationError(item_path=vg.get_vpath(),
                                              error_message=message))

        return errors

    def _validate_bootable_disk(self, node, rule_number):
        '''
        Validate that only 1 System Disk has "bootable" set to True
        '''

        preamble = '_validate_bootable_disk: %s Rule:%s : ' % \
                   (node.item_id, rule_number)

        errors = []

        num_boot_disks = len([disk for disk in node.system.disks \
                                if disk.bootable == "true"])

        if num_boot_disks != 1:
            message = "One System Disk should have 'bootable' Property " + \
                      "set to 'true'"
            log.trace.debug(preamble + message)
            error = ValidationError(item_path=node.system.get_vpath(),
                                    error_message=message)
            errors.append(error)

        return errors

    def _validate_disk_exists(self, node, rule_number):
        '''
        Validate that the Physical Device exists as
        a System Disk
        '''

        preamble = '_validate_disk_exists: %s Rule:%s : ' % \
                   (node.item_id, rule_number)

        errors = []
        for vg in node.storage_profile.volume_groups:

            for pd in vg.physical_devices:

                system_disk_found = False

                for disk in node.system.disks:
                    if disk.name and (disk.name == pd.device_name):
                        system_disk_found = True
                        break

                if not system_disk_found:
                    message = "Failed to find System disk '%s'" % \
                              pd.device_name
                    log.trace.debug((preamble + "VG:%s PD:%s " + message) % \
                                    (vg.item_id, pd.item_id))
                    error = ValidationError(item_path=pd.get_vpath(),
                                            error_message=message)
                    errors.append(error)

                # At present only 1 Physical Device is supported
                break

        return errors

    def _validate_pd_disks(self, node, rule_number):
        '''
        Validate that each System Disk is referenced by
        at most 1 Physical Device.
        '''

        preamble = '_validate_pd_disks: %s Rule:%s : ' % \
                   (node.item_id, rule_number)

        errors = []
        for disk in node.system.disks:
            pd_refs = [pd for pd in \
                        [pd2 for vg in node.storage_profile.volume_groups \
                         for pd2 in vg.physical_devices] \
                       if pd.device_name == disk.name]

            if len(pd_refs) > 1:
                msg = "Disk '%s' referenced by multiple Physical Devices" % \
                      disk.name
                log.trace.debug(preamble + msg)

                error = ValidationError(item_path=disk.get_vpath(),
                                        error_message=msg)
                errors.append(error)

        return errors

    def validate_model(self, plugin_api_context):
        """
        This method can be used to validate the Model ...

          D=Done, H=HalfDone, N=NotDone
        1.1 D validate the PD device exists as a System Disk
        1.2 H validate size constraints between system.disk & VG items
              (see LVM Driver validation)
        2.  D validate that VG must contain 1-5 FSs and 1 PD
        3.  D validate that we can only create a 1-2 VGs
        4.  D validate VG name is unique in scope of storage-profile
        5.  D validate FS mount_point is unique in scope of storage-profile
        6.  N validate FS mount_point accepts only valid mount_point values
        7.  D validate FS size accepts only valid FS size values
        8.  D validate FS type property only accepts valid values
        9.  D validate FS of type swap must be mounted on mount_point='swap'
        10. N validate that root VG has root mount point ('/')
        11. N validate that specified FS sizes in root VG
              are enough for OS installation
        12. D validate only 1 PD references a System Disk
        13. D validate 1 System disk must have "bootable" property set to true
        14. D validate the FS size must be a multiple of the
              Logical Extent size, which defaults to 4 MB
              (see LVM Driver validation)

        """

        profiles = []
        nodes = plugin_api_context.query("node")

        for node in nodes:
            if node.storage_profile:
                profiles.append(node.storage_profile)

        # To avoid duplicate Profile errors, only validate once
        errors = []
        for profile in profiles:
            errors += self._validate_unique_vg_name(profile, '4')
            errors += self._validate_unique_fs_mountpoint(profile, '5')
            errors += self._validate_swap_fs_mountpoint(profile, '9')

        # Validate each Node (System against Profile)
        for node in nodes:
            if node.system:
                errors += self._validate_bootable_disk(node, '13')

                if node.storage_profile:
                    errors += self._validate_disk_exists(node, '1.1')
                    errors += self._validate_pd_disks(node, '12')

                    errors += self.lvm_driver.validate_node(node)
                    errors += self.vxvm_driver.validate_node(node)

        return errors

# ----------------------

    def _gen_tasks_for_node(self, node):
        '''
        Generate all Tasks for a given Managed Node.
        '''

        preamble = '._gen_tasks_for_node: %s : ' % node.item_id

        log.trace.debug((preamble + \
                         "Generating tasks for Node '%s'") % \
                         node.item_id)

        tasks = []
        try:
            the_root_vg = node.storage_profile.view_root_vg
        except ViewError as e:
            log.trace.debug(preamble + str(e))
            return tasks

        for vg in node.storage_profile.volume_groups:
            if vg.volume_group_name == the_root_vg:
                if vg.volume_driver == 'lvm':
                    tasks += self.lvm_driver.gen_tasks_for_volume_group(node,
                                                                        vg)
                elif vg.volume_driver == 'vxvm':
                    tasks += self.vxvm_driver.gen_tasks_for_volume_group(node,
                                                                         vg)

        return tasks

    def create_configuration(self, plugin_api_context):
        """
        Plugin can provide tasks based on the model ...

        *Example CLI for this plugin:*

        .. code-block:: bash

          # TODO Please provide an example CLI snippet for plugin lvm
          # here
        """
        tasks = []
        preamble = '.create_configuration: '

        nodes = plugin_api_context.query('node')
        for node in nodes:
            log.trace.debug((preamble + \
                            "Examining Node '%s'") % \
                            node.item_id)
            if node.storage_profile and node.system:
                log.trace.debug((preamble + \
                                "Processing Storage Profile on Node '%s'") % \
                                node.item_id)
                tasks += self._gen_tasks_for_node(node)
            else:
                log.trace.debug((preamble + \
                                 "Node '%s' does not have both a " + \
                                 "System and Storage Profile") % \
                                 node.item_id)

        for task in tasks:
            log.trace.debug(preamble + "Task: %s" % task)

        return tasks
