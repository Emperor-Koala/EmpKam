import usb

class FindDevices(object):
    def __init__(self, device_classes: list[int]):
        self.device_classes = device_classes
        pass

    def __call__(self, device):
        # first, let's check the device
        if device.bDeviceClass in self.device_classes:
            return True
        # ok, transverse all devices to find an
        # interface that matches our class
        for cfg in device:
            # find_descriptor: what's it?

            for device_class in self.device_classes:
                intf = usb.util.find_descriptor(cfg, bInterfaceClass=device_class)

                if intf is not None:
                    return True

        return False