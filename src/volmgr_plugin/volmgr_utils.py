##############################################################################
# COPYRIGHT Ericsson AB 2013
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

import re


class VolMgrUtils(object):
    '''
    Simple utilities for various file system requirements.
    '''

    @staticmethod
    def get_size_megabytes(size_units):
        '''
        Utility method to convert a combined size-and-unit string
        into a Numeric Megabytes value
        @param size_units: Combined size-and-unit string
        @type size_units: String
        @return: Numeric size in Megabytes
        @rtype: Integer
        '''

        pattern = r'^\s*(?P<size>[1-9][0-9]*)\s*(?P<unit>[MGT])\s*$'
        regexp = re.compile(pattern)

        match = regexp.search(size_units)

        if match:
            parts = match.groupdict()
            if parts:
                if 'size' in parts.keys():
                    size = int(parts['size'])

                    if 'unit' in parts.keys():
                        unit = parts['unit']
                        if unit == 'M':
                            size *= 1
                        elif unit == 'G':
                            size *= 1024
                        elif unit == 'T':
                            size *= 1024 * 1024
                        return size
        else:
            return 0
