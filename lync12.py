from __future__ import absolute_import, division, print_function
from dataclasses import dataclass, field
import socket
from socket import timeout
import logging
import time
from typing import List


@dataclass
class Source:
    idx: int = 0
    name: str = "Undefined"


@dataclass
class Zone:
    idx: int = 0
    name: str = "Undefined"
    power: bool = False
    source: int = -1
    source_name: str = "Undefined"
    volume: int = 0
    mute: bool = True
    dnd: bool = False
    sources: List[Source] = field(default_factory=list)


class lync12:

    __host_ip = '192.168.124.7'
    __host_port = 10006
    __timeout_sec = 1
    __volume_up_down_delta = 5

    __volume_max = 60
    __volume_min = 0

    def __init__(self):
        logging.debug("Init...")

    def __enter__(self):
        logging.debug("Enter...")
        self.open()
        return self

    def __exit__(self, type, value, traceback):
        logging.debug("Exit...")

    def __checksum(self, message):
        cs = 0
        for b in message:
            cs = cs+b
        csb = cs & 0xff
        return csb

    def __extract_string(self, data, start_idx=0):
        result = []

        index = 4
        while data[index] != 0x00 and index < 16:
            result.append(chr(data[index]))
            index += 1

        return ''.join(result)

    def __extract_zone(self, data, query_name, query_source_name):
        if (data[3] != 5):
            return None

        zone = Zone()

        zone.idx = data[2]
        if query_name:
            zone.name = self.query_zone_name(data[2])
        zone.source = data[8]+1
        if query_source_name:
            zone.source_name = self.query_zone_source_name(
                zone.idx, zone.source)
        zone.volume = data[9]-0xc4 if data[9] else self.__volume_min
        zone.power = True if (data[4] & 0b0000001) else False
        zone.mute = True if (data[4] & 0b0000010) else False
        zone.dnd = True if (data[4] & 0b0000100) else False

        return zone

    def __extract_zone_names(self, zones, data):
        zone_names = {}
        string = str(data)
        for zone in zones:
            start_search_string = '\\x{:02d}\\r'.format(zone.idx)
            end_search_string = '\\x00'
            start = string.find(start_search_string)
            if start == -1:
                continue
            end = string.find(end_search_string, start)

            zone_names[zone.idx] = string[start+len(start_search_string):end]

        return zone_names

    def __extract_zone_sources(self, zones, data):
        sources = {}
        for zone in zones:
            start_search_string = '\\x{:02d}\\x0e'.format(zone.idx)
            end_search_string = '\\x00'
            string = str(data).replace('\\t', '\\x09').replace('\\n', '\\x0a')
            start = 0
            end = 0
            while start != -1:
                start = string.find(start_search_string, end)
                if start == -1:
                    break
                end = string.find(end_search_string, start)
                source = Source()
                source.name = string[start+len(start_search_string):end]

                offset = (13 - len(source.name)) * 4 + len(source.name) + 2
                source.idx = int(
                    string[start + offset: start + offset + 2], 16) + 1

                if zone.idx not in sources:
                    sources[zone.idx] = []
                sources[zone.idx].append(source)

        return sources

    def __extract_zones(self, data, query_name=False, query_source_name=False, zone_idx=-1):
        zones = []
        zone_data_length = 14

        start = 0 if len(data) == zone_data_length else (
            zone_data_length if zone_idx == -1 else zone_idx * zone_data_length)
        end = start + zone_data_length

        while end <= len(data):
            zone_data = data[start:end]
            zone = self.__extract_zone(
                zone_data, query_name, query_source_name)
            if not zone:
                break
            zones.append(zone)
            start = end
            end = start + zone_data_length
            if zone_idx != -1:
                break
        return zones if zone_idx == -1 else zones[0]

    def query_full_status(self):
        cmd = bytearray([0x02, 0x00, 0x01, 0x0C, 0x00])
        data = self.__send_command(cmd, False)
        zones = self.__extract_zones(data)
        zone_names = self.__extract_zone_names(zones, data)
        zone_sources = self.__extract_zone_sources(zones, data)
        for zone in zones:
            zone.name = zone_names[zone.idx]
            zone.source_name = zone_sources[zone.idx][zone.source].name
            zone.sources = zone_sources[zone.idx]

        return zones

    def query_zone(self, zone_idx, query_name=True, query_source_name=True):
        cmd = bytearray([0x02, 0x00, 0x00, 0x05, 0x07])
        data = self.__send_command(cmd)
        zones = self.__extract_zones(
            data, query_name, query_source_name, zone_idx)
        return zones

    def query_zone_name(self, zone_idx):
        cmd = bytearray([0x02, 0x00, zone_idx, 0x0D, 0x00])
        data = self.__send_command(cmd)
        name = self.__extract_string(data)
        return name

    def query_zone_source_name(self, zone_idx, source_idx):
        cmd = bytearray([0x02, 0x00, zone_idx, 0x0E, source_idx - 1])
        data = self.__send_command(cmd)
        name = self.__extract_string(data)
        return name

    def zone_dnd_on(self, zone_idx):
        cmd = bytearray([0x02, 0x00, zone_idx, 0x04, 0x59])
        self.__send_command(cmd)
        data = self.query_zone(zone_idx)
        return data

    def zone_dnd_off(self, zone_idx):
        cmd = bytearray([0x02, 0x00, zone_idx, 0x04, 0x5A])
        self.__send_command(cmd)
        data = self.query_zone(zone_idx)
        return data

    def zone_dnd_toggle(self, zone_idx):
        zone = self.query_zone(zone_idx, False, False)
        if zone.dnd:
            self.zone_dnd_off(zone_idx)
        else:
            self.zone_dnd_on(zone_idx)
        data = self.query_zone(zone_idx)
        return data

    def zone_mute_on(self, zone_idx):
        cmd = bytearray([0x02, 0x00, zone_idx, 0x04, 0x1e])
        self.__send_command(cmd)
        data = self.query_zone(zone_idx)
        return data

    def zone_mute_off(self, zone_idx):
        cmd = bytearray([0x02, 0x00, zone_idx, 0x04, 0x1f])
        self.__send_command(cmd)
        data = self.query_zone(zone_idx)
        return data

    def zone_mute_toggle(self, zone_idx):
        zone = self.query_zone(zone_idx, False, False)
        if zone.mute:
            self.zone_mute_off(zone_idx)
        else:
            self.zone_mute_on(zone_idx)
        data = self.query_zone(zone_idx)
        return data

    def zone_power_on(self, zone_idx):
        cmd = bytearray([0x02, 0x00, zone_idx, 0x04, 0x57])
        self.__send_command(cmd)
        data = self.query_zone(zone_idx)
        return data

    def zone_power_off(self, zone_idx):
        cmd = bytearray([0x02, 0x00, zone_idx, 0x04, 0x58])
        self.__send_command(cmd)
        data = self.query_zone(zone_idx)
        return data

    def zone_power_toggle(self, zone_idx):
        zone = self.query_zone(zone_idx, False, False)
        if zone.power:
            self.zone_power_off(zone_idx)
        else:
            self.zone_power_on(zone_idx)
        data = self.query_zone(zone_idx)
        return data

    def zone_set_input(self, zone_idx, input_idx):
        cmd = bytearray([0x02, 0x00, zone_idx, 0x04, input_idx + 0x0f])
        self.__send_command(cmd)
        data = self.query_zone(zone_idx)
        return data

    def zone_volume_set(self, zone_idx, value):
        if (value > self.__volume_max):
            value = self.__volume_max
        if (value < self.__volume_min):
            value = self.__volume_min

        byte_value = (value + 0xc4) & 0xFF  # 60 is actually 0x00
        cmd = bytearray([0x02, 0x00, zone_idx, 0x15,
                        byte_value])
        self.__send_command(cmd)
        self.zone_power_on(zone_idx)
        data = self.query_zone(zone_idx)
        return data

    def zone_volume_up(self, zone_idx):
        zone = self.query_zone(zone_idx, False, False)[0]
        volume = zone.volume + self.__volume_up_down_delta
        self.zone_volume_set(zone_idx, volume)
        data = self.query_zone(zone_idx)
        return data

    def zone_volume_down(self, zone_idx):
        zone = self.query_zone(zone_idx, False, False)[0]
        volume = zone.volume - self.__volume_up_down_delta
        self.zone_volume_set(zone_idx, volume)
        data = self.query_zone(zone_idx)
        return data

    def all_power_on(self):
        cmd = bytearray([0x02, 0x00, 0x00, 0x04, 0x55])
        self.__send_command(cmd)
        data = self.query_full_status()
        return data

    def all_power_off(self):
        cmd = bytearray([0x02, 0x00, 0x00, 0x04, 0x56])
        self.__send_command(cmd)
        data = self.query_full_status()
        return data

    def __recv_single(self, sock):
        return sock.recv(1024)

    def __recv_all(self, sock):
        sock.setblocking(0)

        # total data partwise in an array
        all_data = bytes()
        data = ''

        # beginning time
        begin = time.time()
        while True:
            if all_data and time.time()-begin > self.__timeout_sec:
                break

            elif time.time()-begin > self.__timeout_sec*2:
                break

            try:
                data = sock.recv(8192)
                if data:
                    all_data += data
                    begin = time.time()
                else:
                    time.sleep(0.01)
            except:
                pass

        return all_data

    def __send_command(self, cmd, single_rcv=True):
        host = self.__host_ip
        port = self.__host_port
        cmd.append(self.__checksum(cmd))
        logging.debug('Command: {0}\n\r'.format(cmd))
        sock = socket.socket()
        sock.settimeout(self.__timeout_sec)

        try:
            sock.connect((host, port))
            sock.send(cmd)

            try:
                if (single_rcv):
                    data = self.__recv_single(sock)
                    logging.debug('Received data: {0}\n\r'.format(data))
                    return data
                else:
                    data = self.__recv_all(sock)
                    logging.debug('Received data: {0}\n\r'.format(data))
                    return data
            except IOError:
                pass
            finally:
                sock.close()

        except timeout:
            logging.critical('Timeout occurred')
            exit()
