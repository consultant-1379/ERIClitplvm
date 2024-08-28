##############################################################################
# COPYRIGHT Ericsson AB 2014
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# from litp.core.validators import ValidationError
# from litp.core.execution_manager import ConfigTask
# from volmgr_plugin.volmgr_utils import VolMgrUtils
# from litp.core.task import OrderedTaskList
# from litp.core.extension import ViewError

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class VxvmDriver(object):
    """
    LITP VxVm Driver
    """

    def gen_tasks_for_volume_group(self, node, vg):
        '''
        Generate all Tasks for a given Volume Group
        for a given Managed Node.
        '''

        preamble = '.gen_tasks_for_volume_group: %s VG:%s : ' % \
                   (node.item_id, vg.item_id)
        log.trace.debug(preamble + "Generating tasks for Volume Group")
        tasks = []

        return tasks

    def validate_node(self, node):
        '''
        Validate all VxVm Node items for a given Managed Node
        '''

        preamble = '.validate_node: %s : ' % node.item_id
        log.trace.debug(preamble + "Validating Node")
        errors = []

        return errors
