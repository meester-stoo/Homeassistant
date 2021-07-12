#!/usr/bin/python3

from lync12 import *
from sys import argv
import json

htd = lync12()

# print(htd.query_zone(2, false, false))
# print(htd.query_zones())
# print(htd.query_zone_source_name(5, 11))
# print(htd.query_zone_name(1))
# print(htd.query_full_status())  # TODO Finish sources

# print(htd.extract_source(b'\x02\x00\x01\x0eSource 2\x00\x00\x00\x01\x00\xd5'))
# print(htd.extract_zone_name(b'\x02\x00\x03\rCraft Room\x00\x03\x00\xc2'))


def __usage():
    usage = 'Usage:\n\n\r'
    usage += 'Power off or on all zones: power off|on\n\r'
    usage += 'Power off or on a specific zone: power <zone index> off|on\n\r'
    usage += 'Toggle power against a specific zone: power <zone index> toggle\n\n\r'
    usage += 'Mute or unmute a specific zone: mute <zone index> off|on\n\r'
    usage += 'Toggle mute against a specific zone: mute <zone index> toggle\n\n\r'
    usage += 'Enable or disable dnd against a specific zone: dnd < zone index > off | on\n\r'
    usage += 'Toggle dnd against a specific zone: dnd <zone index> toggle\n\n\r'
    usage += 'Set zone input: input <zone index> <source index>\n\n\r'
    usage += 'Change volume for a specific zone: volume <zone index> up|down\n\r'
    usage += 'Set volume for a specific zone: volume <zone index> <volume 0 to 60>\n\n\r'
    usage += 'Query all information: query zones\n\r'
    usage += 'Query a specific zone: query zone <zone index>'

    return usage


def toJson(self):
    return json.dumps(self, default=lambda o: o.__dict__,
                      sort_keys=True, indent=4)


def __power(args):
    if len(args) == 3:
        if args[2] == 'off':
            return htd.all_power_off()
        elif args[2] == 'on':
            return htd.all_power_on()
        else:
            return __usage()
    elif len(args) == 4:
        if args[3] == 'off':
            return htd.zone_power_off(int(args[2]))
        elif args[3] == 'on':
            return htd.zone_power_on(int(args[2]))
        elif args[3] == 'toggle':
            return htd.zone_power_toggle(int(args[2]))
        else:
            return __usage()
    else:
        return __usage()


def __mute(args):
    if args[3] == 'off':
        return htd.zone_mute_off(int(args[2]))
    elif args[3] == 'on':
        return htd.zone_mute_on(int(args[2]))
    elif args[3] == 'toggle':
        return htd.zone_mute_toggle(int(args[2]))
    else:
        return __usage()


def __dnd(args):
    if args[3] == 'off':
        return htd.zone_dnd_off(int(args[2]))
    elif args[3] == 'on':
        return htd.zone_dnd_on(int(args[2]))
    elif args[3] == 'toggle':
        return htd.zone_dnd_toggle(int(args[2]))
    else:
        return __usage()


def __input(args):
    return htd.zone_set_input(int(args[2]), int(args[3]))


def __volume(args):
    if args[3] == 'up':
        return htd.zone_volume_up(int(args[2]))
    elif args[3] == 'down':
        return htd.zone_volume_down(int(args[2]))
    else:
        volume = int(args[3])
        return htd.zone_volume_set(int(args[2]), volume)


def __query(args):
    if args[2] == 'zones':
        return htd.query_full_status()
    elif args[2] == 'zone':
        zone_idx = int(args[3])
        return htd.query_zone(zone_idx)
    else:
        return __usage()


def __process_arguments(args):
    command = args[1]

    if command == 'query':
        return toJson(__query(args))
    elif command == 'power':
        return toJson(__power(args))
    elif command == 'mute':
        return toJson(__mute(args))
    elif command == 'volume':
        return toJson(__volume(args))
    elif command == 'dnd':
        return toJson(__dnd(args))
    elif command == 'input':
        return toJson(__input(args))


if len(argv) == 1:
    print(__usage())
else:
    print(__process_arguments(argv))
