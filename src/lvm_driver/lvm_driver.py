##############################################################################
# COPYRIGHT Ericsson AB 2014
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

from litp.core.validators import ValidationError
from litp.core.execution_manager import ConfigTask
from volmgr_plugin.volmgr_utils import VolMgrUtils
from litp.core.task import OrderedTaskList

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class LvmDriver(object):
    """
    LITP LVM Driver
    """

    SLASH_BOOT_SIZE = 500

    VG_OVERHEAD = 100

    LOGICAL_EXTENT_SIZE_MB = 4

    def _gen_file_system_device_name(self, vg, fs):
        '''
        Generate File-System identifier
        This *MUST* synchronize with the
        puppet/modules/lvm/manifests/volume.pp filesystem identifier
        '''
        return "/dev/%s/%s" % (vg.volume_group_name, fs.item_id)

    def _suitable_state(self, items):
        '''
        Check if any 1 of items is Initial or Updated
        '''

        return any((item.is_initial() or item.is_updated()) for item in items)

    def _gen_tasks_for_file_system(self, node, pd, vg, fs):
        '''
        Generate all Tasks for a File System in
        a given Volume Group on a given Node.
        '''

        preamble = '._gen_tasks_for_file_system: %s PD:%s, VG:%s, FS:%s : ' % \
                   (node.item_id, pd.item_id, vg.item_id, fs.item_id)

        log.trace.debug((preamble + \
                         "Generating tasks for File System '%s'") % \
                         fs.item_id)

        tasks = []
        tasks.append(self._gen_task_for_volume(node, pd, vg, fs))

        if fs.type == 'ext4':
            fs_mount_tasks = self._gen_tasks_for_fs_mount(node, pd, vg, fs)
            if fs_mount_tasks:
                tasks += fs_mount_tasks
                return [OrderedTaskList(node.storage_profile, tasks)]

        return tasks

    def _get_node_disk_for_pd(self, node, pd):
        '''
        Iterate the Node System disks and locate the exact Disk
        referenced by the Physical Device
        '''

        for disk in node.system.disks:
            if disk.name == pd.device_name:
                return disk

    def _gen_task_for_volume(self, node, pd, vg, fs):
        '''
        Generate a Task for a Volume in a given Volume Group
        on a given Physical Device on a given Node.
        '''

        preamble = '._gen_task_for_volume: %s PD:%s, VG:%s, FS:%s : ' % \
                   (node.item_id, pd.item_id, vg.item_id, fs.item_id)

        log.trace.debug(preamble + "Generating Volume task")

        disk = self._get_node_disk_for_pd(node, pd)

        disk_fact = '$::disk_scsi' + '_3' + disk.uuid
        if disk.bootable == 'true':
            # If the device is bootable then anaconda has already
            # partitioned the disk therfore put the VG on partition 2
            disk_fact += '_part2'
        disk_fact += '_dev'

        desc = "Volume: %s::%s::%s::%s" % \
               (fs.item_id, vg.item_id, pd.item_id, node.item_id)

        task = ConfigTask(node,
                          fs,
                          desc,
                          'lvm::volume',
                          fs.item_id,
                          ensure='present',
                          pv=disk_fact,
                          vg=vg.volume_group_name,
                          fstype=fs.type,
                          size=fs.size)
        return task

    def _gen_tasks_for_fs_mount(self, node, pd, vg, fs):
        '''
        Generate Tasks to Mount a File System
        '''

        # We skip over the / ext4 filesystem
        if fs.mount_point == "/":
            return []

        desc = "Mount Directory: %s::%s::%s::%s" % \
               (fs.item_id, vg.item_id, pd.item_id, node.item_id)
        file_task = ConfigTask(node,
                               fs,
                               desc,
                               'file',
                               fs.mount_point,
                               path=fs.mount_point,
                               ensure="directory",
                               owner="0",
                               group="0",
                               mode="0755",
                               backup='false')

        desc = "Mount: %s::%s::%s::%s" % \
               (fs.item_id, vg.item_id, pd.item_id, node.item_id)

        fs_device = self._gen_file_system_device_name(vg, fs)
        mount_task = ConfigTask(node,
                                fs,
                                desc,
                                'mount',
                                fs.mount_point,
                                fstype=fs.type,
                                device=fs_device,
                                ensure='mounted',
                                options="defaults",
                                atboot="true")
        return [file_task, mount_task]

    def gen_tasks_for_volume_group(self, node, vg):
        '''
        Generate all Tasks for a given Volume Group
        for a given Managed Node.
        '''
        preamble = '.gen_tasks_for_volume_group: %s VG:%s : ' % \
                   (node.item_id, vg.item_id)

        log.trace.debug((preamble + \
                         "Generating tasks for Volume Group '%s'") % \
                         vg.item_id)
        tasks = []
        the_pd = None

        for pd in vg.physical_devices:
            the_pd = pd   # Only 1 PD per VG allowed/expected
            break

        for fs in vg.file_systems:
            if self._suitable_state([the_pd, vg, fs]):
                tasks += self._gen_tasks_for_file_system(node, the_pd, vg, fs)

        return tasks

# -------------

    def _validate_vg_size_against_disk(self, node, vg, disk, rule_number):
        '''
        Validate the File System for a given Volume Group
        will fit on the nominated System Disk.
        '''

        preamble = '_validate_vg_size_against_disk: %s VG:%s, Rule:%s : ' % \
                   (node.item_id, vg.item_id, rule_number)

        sizes = [VolMgrUtils.get_size_megabytes(fs.size) \
                    for fs in vg.file_systems]
        vg_cumulative_size = sum(sizes)

        disk_size = VolMgrUtils.get_size_megabytes(disk.size)

        sundries = LvmDriver.VG_OVERHEAD

        if disk.bootable == 'true':
            sundries += LvmDriver.SLASH_BOOT_SIZE

        if (vg_cumulative_size + sundries) > disk_size:
            message = ("The System Disk (size = %s) does not have " + \
                       "sufficient space for all File Systems " + \
                       "(%d MBs) plus sundries (%d MBs)") % \
                       (disk.size, vg_cumulative_size, sundries)
            log.trace.debug(preamble + message)
            return ValidationError(item_path=vg.get_vpath(),
                                   error_message=message)
        return None

    def _validate_disk_sizes(self, node, rule_number):
        '''
        Validate that the Volume Groups can fit on the
        nominated System disks
        '''

        preamble = '_validate_disk_sizes: %s Rule:%s : ' % \
                   (node.item_id, rule_number)

        errors = []
        for vg in node.storage_profile.volume_groups:

            for pd in vg.physical_devices:

                for disk in node.system.disks:
                    if disk.name and (disk.name == pd.device_name):
                        log.trace.debug((preamble + \
                                         "Will validate %s against %s") % \
                                        (vg.item_id, disk.item_id))
                        error = self._validate_vg_size_against_disk(node,
                                                                   vg,
                                                                   disk,
                                                                   rule_number)
                        if error:
                            errors.append(error)
                        break

                # At present only 1 Physical Device is supported
                break

        return errors

    def _is_extent_multiple(self, size):
        '''
        Return boolean True if FS size is a multiple of Logical Extent
        '''

        size_mb = VolMgrUtils.get_size_megabytes(size)
        if (int(size_mb) % LvmDriver.LOGICAL_EXTENT_SIZE_MB) == 0:
            return True

        return False

    def _validate_fs_size(self, node, rule_number):
        '''
        Validate that FS size is multiple of Logical Extent
        '''

        preamble = '_validate_fs_size: %s Rule:%s : ' % \
                   (node.item_id, rule_number)

        errors = []
        for vg in node.storage_profile.volume_groups:
            for fs in vg.file_systems:
                if not self._is_extent_multiple(fs.size):
                    msg = ("File System size '%s' is not an exact " + \
                           "multiple of the LVM Logical Extent " + \
                           "size ('%d')") % \
                           (fs.size, LvmDriver.LOGICAL_EXTENT_SIZE_MB)
                    log.trace.debug(preamble + msg)
                    error = ValidationError(item_path=fs.get_vpath(),
                                            error_message=msg)
                    errors.append(error)

        return errors

    def validate_node(self, node):
        '''
        Public Driver method to validate LVM items per Node
        '''

        errors = []
        errors += self._validate_fs_size(node, '14')
        errors += self._validate_disk_sizes(node, '1.2')

        return errors
