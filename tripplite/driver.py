"""Driver for TrippLite UPS battery backups.   Only tested on SMART1500LCDXL(?)"""
import hid

vendor_id = 0x09ae

structure = {
    'config': {
        'voltage': {
            'address': 48,
            'bytes': 1,
            'format': 'i'
        },
        'frequency': {
            'address': 2,
            'bytes': 1,
            'format': 'i'
        },
        'power': {
            'address': 3,
            'bytes': 2,
            'format': 'i'
        }
    },
    'status': {
        'address': 50,
        'bytes': 1,
        'format': 'b',
        'keys': [
            'shutdown imminent',
            'ac present',
            'charging',
            'discharging',
            'needs replacement',
            'below remaining capacity',
            'fully charged',
            'fully discharged'
        ]
    },
    'input': {
        'voltage': {
            'address': 24,
            'bytes': 2,
            'format': 'f'
        },
        'frequency': {
            'address': 25,
            'bytes': 2,
            'format': 'f'
        }
    },
    'output': {
        'voltage': {
            'address': 27,
            'bytes': 2,
            'format': 'f'
        },
        'power': {
            'address': 71,
            'bytes': 2,
            'format': 'i'
        }
    },
    'health': {
        'address': 52,
        'bytes': 1,
        'format': 'i'
    },
    'time to empty': {
        'address': 53,
        'bytes': 2,
        'format': 'i'
    }
}


class Battery(object):
    """Driver for TrippLite UPS battery backups."""

    def __init__(self, product_id=None, serial=None):
        """Connect to the device.

        Args:
            product_id (Optional): The HID product ID of the UPS.  If omitted,
                all devices will be scanned and the first one will be selected.
            serial (Optional): The serial number of a specific UPS.  If used,
                product_id is not required.
        """
        self.device = hid.device()
        if (serial)
            self.product_id = self._get_product_id_by_serial(serial)
        elif (product_id)
            self.product_id = product_id
        else
            self.product_id = self._get_product_id_greedy()
        self.serial = serial

    def __enter__(self):
        """Provide entrance to context manager."""
        self.open()
        return self

    def __exit__(self, *args):
        """Provide exit to context manager."""
        self.close()

    def open(self):
        """Open connection to the device."""
        if (self.serial)
            self.device.open(vendor_id, self.product_id, self.serial)
        else
            self.device.open(vendor_id, self.product_id)

    def close(self):
        """Close connection to the device."""
        self.device.close()

    def _get_product_id_greedy(self):
        """Search through connected HID devices to find the TrippLite UPS.

        This will return the first TrippLite device found, regardless of how
        many are connected.
        """
        try:
            return next(d['product_id'] for d in hid.enumerate()
                        if d['vendor_id'] == vendor_id)
        except StopIteration:
            raise IOError("Could not find any connected TrippLite devices.")

    def _get_product_id_by_serial(self, serial):
        """Search through connected HID devices to find the TrippLite UPS with
        the specified serial number.
        """
        try:
            return next(d['product_id'] for d in hid.enumerate()
                        if d['vendor_id'] == vendor_id
                        and d['serial'] == serial)
        except StopIteration:
            raise IOError("Could not find TrippLite device with given serial.")
    def get(self):
        """Return an object containing all available data."""
        output = {}
        for category, data in structure.items():
            if 'address' in data:
                output[category] = self._read(data)
            else:
                output[category] = {}
                for subcategory, options in data.items():
                    output[category][subcategory] = self._read(options)
        return output

    def _read(self, options, retries=3):
        """Read a HID report from the TrippLite connection.

        This reads binary, one-byte ints, two-byte ints (little-endian),
        and floats (little-endian two-byte ints, divided by 10). See the
        TrippLite communication interface manual for more.
        """
        report = self.device.get_feature_report(options['address'],
                                                options['bytes'] + 1)
        if not report:
            if retries > 0:
                return self._read(options, retries - 1)
            raise IOError("Did not receive data.")
        if options['address'] != report[0]:
            raise IOError("Received unexpected data.")
        if options['format'] == 'b':
            bits = '{:08b}'.format(report[1])[::-1]
            return {k: bool(int(v)) for k, v in zip(options['keys'], bits)}
        elif options['format'] == 'i' and options['bytes'] == 2:
            return (report[2] << 8) + report[1]
        elif options['format'] == 'i' and options['bytes'] == 1:
            return report[1]
        elif options['format'] == 'f':
            return ((report[2] << 8) + report[1]) / 10.0
