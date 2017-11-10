from netmiko import ConnectHandler
import sys


def showVerson(device):
    output = device.send_command('show version')
    print(output)


def getDevice(platform, host, username, password):
    device = ConnectHandler(device_type=platform, ip=host, username=username, password=password)
    return device


if __name__ == '__main__':
    platform = sys.argv[1]
    host = sys.argv[2]
    username = sys.argv[3]
    password = sys.argv[4]

    device = getDevice(platform, host, username, password)
    showVerson(device)