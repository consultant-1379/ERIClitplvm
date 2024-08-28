##############################################################################
# COPYRIGHT Ericsson AB 2014
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

from volmgr_plugin.volmgr_plugin import VolMgrPlugin

from litp.core.plugin_manager import PluginManager
from litp.core.model_manager import ModelManager
from litp.extensions.core_extension import CoreExtension
from litp.core.plugin_context_api import PluginApiContext
from litp.core.model_type import ItemType, Child
from lvm_extension.lvm_extension import LvmExtension
from volmgr_plugin.volmgr_utils import VolMgrUtils

import unittest


class TestVolMgrPlugin(unittest.TestCase):

    def setUp(self):
        """
        Construct a model manager, sufficient for test cases
        that you wish to implement in this suite.
        """
        self.model_manager = ModelManager()
        self.plugin_manager = PluginManager(self.model_manager)
        self.context = PluginApiContext(self.model_manager)

        core_ext = CoreExtension()
        lvm_ext = LvmExtension()

        for ext in [core_ext, lvm_ext]:
            self.plugin_manager.add_property_types(ext.define_property_types())
            self.plugin_manager.add_item_types(ext.define_item_types())

        # Add default minimal model (which creates '/' root item)
        self.plugin_manager.add_default_model()

        # Instantiate your plugin and register with PluginManager
        self.plugin = VolMgrPlugin()
        self.plugin_manager.add_plugin('TestPlugin',
                                       'some.test.plugin',
                                       '1.0.0',
                                       self.plugin)

    def _create_storage_profile_items(self, profile, system, data):

        if profile:
            profile_url = profile.get_vpath()
            for vg in data['VGs']:
                vg_url = profile_url + '/volume_groups/' + vg['id']
#               print "Creating VG " + vg_url
                if 'volume_driver' in vg:
                    driver = vg['volume_driver']
                else:
                    driver = 'lvm'

                self.model_manager.create_item('volume-group',
                                               vg_url,
                                               volume_group_name=vg['name'],
                                               volume_driver=driver)

                if 'FSs' in vg:
                    for fs in vg['FSs']:
                        fs_url = vg_url + '/file_systems/' + fs['id']
#                       print "Creating FS " + fs_url
                        self.model_manager.create_item('file-system',
                                                       fs_url,
                                                       type=fs['type'],
                                                       mount_point=fs['mp'],
                                                       size=fs['size'])
                if 'PDs' in vg:
                    for pd in vg['PDs']:
                        pd_url = vg_url + '/physical_devices/' + pd['id']
#                       print "Creating PD " + pd_url
                        self.model_manager.create_item('physical-device',
                                                       pd_url,
                                                       device_name=pd['device'])

        if system:
            sys_url = system.get_vpath()
            for disk in data['disks']:
                disk_url = sys_url + '/disks/' + disk['id']
#               print "Creating Disk " + disk_url
                self.model_manager.create_item('disk',
                                               disk_url,
                                               bootable=disk['bootable'],
                                               uuid=disk['uuid'],
                                               name=disk['name'],
                                               size=disk['size'])

    def setup_model(self, link_node_to_system=True):

        self.model_manager.create_item('deployment', '/deployments/d1')
        self.model_manager.create_item('cluster',
                                       '/deployments/d1/clusters/c1')

        n1_url = '/deployments/d1/clusters/c1/nodes/n1'

        node1 = self.model_manager.create_item('node',
                                               n1_url,
                                               hostname='node1')

        s1_url = '/infrastructure/systems/s1'
        sys_name = 'MN1SYS'
        self.system1 = self.model_manager.create_item('system',
                                                      s1_url,
                                                      system_name=sys_name)
        sps_url = '/infrastructure/storage/storage_profiles'

        sp1_url = sps_url + '/sp1'
        sp1_name = 'storage_profile_1'
        self.sp1 = self.model_manager.create_item('storage-profile',
                                                 sp1_url,
                                                 storage_profile_name=sp1_name)
        rsp = self.model_manager.create_link('storage-profile',
                                             n1_url + '/storage_profile',
                                             storage_profile_name=sp1_name)
        self.assertFalse(isinstance(rsp, list), rsp)

        if link_node_to_system == True:
            rsp = self.model_manager.create_link('system',
                                                 n1_url + '/system',
                                                 system_name=sys_name)
            self.assertFalse(isinstance(rsp, list), rsp)

    def _create_dataset1(self):

        disk1_name = 'primary'

        storage_data = \
        {'VGs': [{'id': 'vg1',
                  'name': 'root_vg',
                  'FSs': [{'id': 'fs1', 'type': 'ext4', 'mp': '/',     'size': '10G'},
                          {'id': 'fs2', 'type': 'swap', 'mp': 'swap',  'size': '2G' },
                          {'id': 'fs3', 'type': 'ext4', 'mp': '/home', 'size': '14G'}],
                  'PDs': [{'id': 'pd1', 'device': disk1_name}]
                 }
                ],
         'disks': [{'id': 'disk1', 'bootable': 'true', 'uuid': 'ABCD_1234',
                    'name': disk1_name, 'size': '28G'}
                  ]
        }

        self._create_storage_profile_items(self.sp1,
                                           self.system1,
                                           storage_data)

    def _create_dataset2(self):

        disk2_name = 'secondary'

        storage_data = \
        {'VGs': [{'id': 'vg2',
                  'name': 'app_vg',
                  'FSs': [{'id': 'fs1',  'type': 'ext4', 'mp': '/opt', 'size': '10G'},
                          {'id': 'fs2',  'type': 'ext4', 'mp': '/var', 'size': '20G'}],
                  'PDs': [{'id': 'pd1', 'device': disk2_name}]
                 }
                ],
         'disks': [{'id': 'disk2', 'bootable': 'false', 'uuid': 'ABCD_1235',
                    'name': disk2_name, 'size': '30G'}
                  ]
        }

        self._create_storage_profile_items(self.sp1,
                                           self.system1,
                                           storage_data)

    def test_megabyte_conversion(self):
        self.assertEquals(1024, VolMgrUtils.get_size_megabytes('1G'))
        self.assertEquals(1, VolMgrUtils.get_size_megabytes('1M'))
        self.assertEquals(1024 * 1024, VolMgrUtils.get_size_megabytes('1024G'))
        self.assertEquals(1024 * 1024, VolMgrUtils.get_size_megabytes('1T'))
        self.assertEquals(0, VolMgrUtils.get_size_megabytes('1F'))
        self.assertEquals(0, VolMgrUtils.get_size_megabytes('1'))
        self.assertEquals(0, VolMgrUtils.get_size_megabytes('G'))

    def test_validate_model_01(self):
        self.setup_model()
        self._create_dataset1()
        errors = self.plugin.validate_model(self.context)
        self.assertEqual(0, len(errors))

    def test_validate_model_02(self):
        self.setup_model()

        disk_name = 'primary'
        storage_data = \
        {'VGs': [{'id': 'vg1',
                  'name': 'app_vg',
                  'FSs': [{'id': 'fs1',  'type': 'ext4', 'mp': '/opt', 'size': '10G'},
                          {'id': 'fs2',  'type': 'ext4', 'mp': '/var', 'size': '20G'}],
                  'PDs': [{'id': 'pd1', 'device': disk_name}]
                 }
                ],
         'disks': [{'id': 'disk1', 'bootable': 'true', 'uuid': 'ABCD_1234',
                    'name': disk_name, 'size': '25G'} # Too small for the 2 FSs
                  ]
        }

        self._create_storage_profile_items(self.sp1,
                                           self.system1,
                                           storage_data)

        errors = self.plugin.validate_model(self.context)
        self.assertEqual(1, len(errors))

    def test_validate_model_03(self):
        self.setup_model()

        disk_name = 'primary'
        storage_data = \
        {'VGs': [{'id': 'vg1',
                  'name': 'root_vg',
                  'FSs': [{'id': 'fs1', 'type': 'ext4', 'mp': '/',     'size': '10G'},
                          {'id': 'fs2', 'type': 'ext4', 'mp': '/home', 'size': '20G'}],
                  'PDs': [{'id': 'pd1', 'device': disk_name}]
                 }
                ],
         'disks': [{'id': 'disk1', 'bootable': 'true', 'uuid': 'ABCD_1234',
                    'name': disk_name, 'size': '30G'}  # No space for sundries
                  ]
        }

        self._create_storage_profile_items(self.sp1,
                                           self.system1,
                                           storage_data)

        errors = self.plugin.validate_model(self.context)
        self.assertEqual(1, len(errors))

    def test_validate_model_04(self):
        self.setup_model()

        storage_data = \
        {'VGs': [{'id': 'vg1',
                  'name': 'root_vg',
                  'FSs': [{'id': 'fs1', 'type': 'ext4', 'mp': '/',   'size': '10G'}],
                  'PDs': [{'id': 'pd1', 'device': 'primary'}]
                 }
                ],
         'disks': []  # No Disk(s) for LVM items
        }

        self._create_storage_profile_items(self.sp1,
                                           self.system1,
                                           storage_data)

        errors = self.plugin.validate_model(self.context)
        self.assertEqual(2, len(errors))

    def test_validate_model_05(self):
        self.setup_model()

        disk1_name = 'primary'
        disk2_name = 'secondary'
        storage_data = \
        {'VGs': [{'id': 'vg1',
                  'name': 'root_vg',
                  'FSs': [{'id': 'fs1', 'type': 'ext4', 'mp': '/', 'size': '10G'}],
                  'PDs': [{'id': 'pd1', 'device': disk1_name}]
                 },
                 {'id': 'vg2',
                  'name': 'root_vg',    # Duplicate name
                  'FSs': [{'id': 'fs1', 'type': 'ext4', 'mp': '/home', 'size': '10G'}],
                  'PDs': [{'id': 'pd1', 'device': disk2_name}]
                 }
                ],
         'disks': [{'id': 'disk1', 'bootable': 'true',  'uuid': 'ABCD_1234',
                    'name': disk1_name, 'size': '15G'},
                   {'id': 'disk2', 'bootable': 'false', 'uuid': 'ABCD_1235',
                    'name': disk2_name, 'size': '15G'}
                  ]
        }

        self._create_storage_profile_items(self.sp1,
                                           self.system1,
                                           storage_data)

        errors = self.plugin.validate_model(self.context)
        self.assertEqual(2, len(errors))

    def test_validate_model_06(self):
        self.setup_model()

        disk_name = 'primary'
        storage_data = \
        {'VGs': [{'id': 'vg1',
                  'name': 'root_vg',
                  'FSs': [{'id': 'fs1', 'type': 'ext4', 'mp': '/home', 'size': '10G'},
                          # Duplicate Mount Point
                          {'id': 'fs2', 'type': 'ext4', 'mp': '/home', 'size': '20G'}],
                  'PDs': [{'id': 'pd1', 'device': disk_name}]
                 }
                ],
         'disks': [{'id': 'disk1', 'bootable': 'true', 'uuid': 'ABCD_1234',
                    'name': disk_name, 'size': '40G'}
                  ]
        }

        self._create_storage_profile_items(self.sp1,
                                           self.system1,
                                           storage_data)

        errors = self.plugin.validate_model(self.context)
        self.assertEqual(2, len(errors))

    def test_validate_model_07(self):
        self.setup_model()

        disk_name = 'primary'
        storage_data = \
        {'VGs': [{'id': 'vg1',
                  'name': 'root_vg',
                  # Mount for a FS of type swap should be just 'swap'
                  'FSs': [{'id': 'fs1', 'type': 'swap', 'mp': '/not_swap', 'size': '10G'}],
                  'PDs': [{'id': 'pd1', 'device': disk_name}]
                 }
                ],
         'disks': [{'id': 'disk1', 'bootable': 'true', 'uuid': 'ABCD_1234',
                    'name': disk_name, 'size': '40G'}
                  ]
        }

        self._create_storage_profile_items(self.sp1,
                                           self.system1,
                                           storage_data)

        errors = self.plugin.validate_model(self.context)
        self.assertEqual(1, len(errors))

    def test_validate_model_08(self):
        self.setup_model()

        disk_name = 'primary'
        storage_data = \
        {'VGs': [{'id': 'vg1',
                  'name': 'root_vg',
                  'PDs': [{'id': 'pd1', 'device': disk_name}]
                 },
                 {'id': 'vg2',
                  'name': 'app_vg',
                  'PDs': [{'id': 'pd1', 'device': disk_name}]
                 }
                ],
         'disks': [{'id': 'disk1', 'bootable': 'true', 'uuid': 'ABCD_1234',
                    'name': disk_name, 'size': '40G'}
                  ]
        }

        self._create_storage_profile_items(self.sp1,
                                           self.system1,
                                           storage_data)

        errors = self.plugin.validate_model(self.context)
        self.assertEqual(1, len(errors))

    def test_validate_model_09(self):
        self.setup_model()

        disk_name = 'primary'
        storage_data = \
        {'VGs': [{'id': 'vg1',
                  'name': 'root_vg',
                  # FS size is not multiple of Extent
                  'FSs': [{'id': 'fs1', 'type': 'ext4', 'mp': '/', 'size': '11M'}],
                  'PDs': [{'id': 'pd1', 'device': disk_name}]
                 }
                ],
         'disks': [{'id': 'disk1', 'bootable': 'true', 'uuid': 'ABCD_1234',
                    'name': disk_name, 'size': '40G'}
                  ]
        }

        self._create_storage_profile_items(self.sp1,
                                           self.system1,
                                           storage_data)

        errors = self.plugin.validate_model(self.context)
        self.assertEqual(1, len(errors))


    def test_create_configuration_01(self):
        self.setup_model()
        self._create_dataset1()
        tasks = self.plugin.create_configuration(self.context)
        self.assertEqual(3, len(tasks))

    def test_create_configuration_02(self):
        self.setup_model()
        self._create_dataset1()
        self._create_dataset2()
        tasks = self.plugin.create_configuration(self.context)
        self.assertEqual(3, len(tasks))

    def test_create_configuration_03(self):
        self.setup_model()
        self._create_dataset2()
        tasks = self.plugin.create_configuration(self.context)
        self.assertEqual(0, len(tasks))

    def test_create_configuration_04(self):
        # Do not link Node to a System
        self.setup_model(link_node_to_system=False)

        disk_name = 'primary'

        storage_data = \
        {'VGs': [{'id': 'vg1',
                  'name': 'root_vg',
                  'FSs': [{'id': 'fs1', 'type': 'ext4', 'mp': '/', 'size': '10G'}],
                  'PDs': [{'id': 'pd1', 'device': disk_name}]
                 }
                ],
         'disks': [{'id': 'disk1', 'bootable': 'true', 'uuid': 'ABCD_1234',
                    'name': disk_name, 'size': '15G'}
                  ]
        }

        self._create_storage_profile_items(self.sp1,
                                           self.system1,
                                           storage_data)

        tasks = self.plugin.create_configuration(self.context)
        # No linked System, so no Tasks exoected
        self.assertEqual(0, len(tasks))

    def test_create_configuration_05(self):
        self.setup_model()

        disk_name = 'primary'

        storage_data = \
        {'VGs': [{'id': 'vg1',
                  'name': 'root_vg',
                  'FSs': [{'id': 'fs1', 'type': 'ext4', 'mp': '/', 'size': '10G'}],
                  'PDs': [{'id': 'pd1', 'device': disk_name}],
                  'volume_driver': 'vxvm'
                 }
                ],
         'disks': [{'id': 'disk1', 'bootable': 'true', 'uuid': 'ABCD_1234',
                    'name': disk_name, 'size': '15G'}
                  ]
        }

        self._create_storage_profile_items(self.sp1,
                                           self.system1,
                                           storage_data)

        tasks = self.plugin.create_configuration(self.context)
        # No Tasks expected for VxVm VGs
        self.assertEqual(0, len(tasks))
