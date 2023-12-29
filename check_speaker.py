import subprocess

def get_connected_devices():
    try:
        cmd = "bluetoothctl devices | cut -f2 -d' ' | while read uuid; do bluetoothctl info $uuid; done | grep -e 'Device\\|Connected\\|Name'"
        result = subprocess.check_output(cmd, shell=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        return ""

def is_device_connected(device_name):
    output = get_connected_devices()
    devices = output.split("Device ")

    for device in devices[1:]:  # Skip the first split as it's empty
        if device_name in device:
            return "Connected: yes" in device

    return False

# The name of your Bluetooth device
device_name = "Jabra Speak 710"

if is_device_connected(device_name):
    print(f"Device '{device_name}' is connected.")
else:
    print(f"Device '{device_name}' is not connected.")

