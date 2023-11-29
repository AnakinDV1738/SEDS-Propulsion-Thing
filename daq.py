import threading

import numpy as np
from uldaq import (get_daq_device_inventory, DaqDevice, AInScanFlag,
                   AiInputMode, AiQueueElement, create_float_buffer,
                   ScanOption, InterfaceType)
from os import system


class DAQ:
    def __init__(self, interface_type=InterfaceType.ANY):
        self.daq_device = None  
        self.ai_device = None
        self.interface_type = interface_type
        self.scanning = True
        self.pressure_transducer = []
        self.load_cell = []

    def connect(self, descriptor_index=0):
        try:
            devices = get_daq_device_inventory(self.interface_type)
            if not devices:
                raise RuntimeError('Error: No DAQ devices found')

            if descriptor_index not in range(len(devices)):
                raise RuntimeError('Please add devices into CH0 or CH1 only')

            self.daq_device = DaqDevice(devices[descriptor_index])
            self.ai_device = self.daq_device.get_ai_device()

            if self.ai_device is None:
                raise RuntimeError('Error: The DAQ device does not support analog '
                                   'input')

            ai_info = self.ai_device.get_info()

            if not ai_info.has_pacer():
                raise RuntimeError('Error: The specified DAQ device does not '
                                   'support hardware paced analog input')

            descriptor = self.daq_device.get_descriptor()
            print('\nConnecting to', descriptor.dev_string, '- please wait...')
            self.daq_device.connect(connection_code=0)
        except Exception as e:
            print('\n', e)

    def disconnect(self):
        try:
            if self.daq_device and self.daq_device.is_connected():
                self.daq_device.disconnect()
        except Exception as e:
            print('\n', e)

    def release(self):
        try:
            if self.daq_device:
                self.daq_device.release()
        except Exception as e:
            print('\n', e)

    def setup_scan(self, channels, samples_per_channel, rate, scan_options, flags):
        try:
            ai_info = self.ai_device.get_info()
            input_mode = AiInputMode.SINGLE_ENDED

            if ai_info.get_num_chans_by_mode(AiInputMode.SINGLE_ENDED) <= 0:
                input_mode = AiInputMode.DIFFERENTIAL

            number_of_channels = ai_info.get_num_chans_by_mode(input_mode)
            if max(channels) >= number_of_channels:
                channels = [i for i in channels if i < number_of_channels]
            channel_count = len(channels)

            ranges = ai_info.get_ranges(input_mode)

            queue_types = ai_info.get_queue_types()
            if not queue_types:
                raise RuntimeError('Error: The device does not support a gain queue')

            range_index = 0
            queue_list = []
            for channel in channels:
                queue_element = AiQueueElement()
                queue_element.channel = channel
                queue_element.input_mode = input_mode
                queue_element.range = ranges[range_index]

                queue_list.append(queue_element)

                range_index += 1
                if range_index >= len(ranges):
                    range_index = 0

            self.ai_device.a_in_load_queue(queue_list)

            data = create_float_buffer(channel_count, samples_per_channel)

            return (channels, input_mode, ranges[0], samples_per_channel,
                    rate, scan_options, flags, data)

        except Exception as e:
            print('\n', e)

    def get_calibration_voltage(self):
        try:
            if self.daq_device is None or not self.daq_device.is_connected():
                print("Error: DAQ device is not connected.")
                return None

            scan_params = self.setup_scan(channels=[1], samples_per_channel=2500,
                                          rate=1000, scan_options=ScanOption.DEFAULTIO | ScanOption.CONTINUOUS,
                                          flags=AInScanFlag.DEFAULT)

            channels, input_mode, range_index, samples_per_channel, \
                rate, scan_options, flags, data = scan_params

            rate = self.ai_device.a_in_scan(channels[0], channels[-1], input_mode,
                                            range_index, samples_per_channel,
                                            rate, scan_options, flags, data)

            samples_acquired = 0
            data_list = []
            while samples_acquired < samples_per_channel:
                status, transfer_status = self.ai_device.get_scan_status()
                index = transfer_status.current_index
                data_list.append(data[index])
                samples_acquired += 1

            avg = np.mean(data_list)
            print(data_list)
            print(f"\nAverage of {samples_per_channel} samples: {avg}")
            return avg

        except Exception as e:
            print('\n', e)
            return None

        finally:
            self.daq_device.release()

    def start_scan(self):
        self.scanning = True

        def scan_thread():
            try:
                channels = [0, 1]  # Define the channels you want to scan
                samples_per_channel = 1000  # Define the number of samples per channel
                rate = 1000  # Define the scan rate in Hz
                scan_options = ScanOption.DEFAULTIO | ScanOption.CONTINUOUS  # Define the scan options
                flags = AInScanFlag.DEFAULT  # Define the flags

                channels, input_mode, range_index, samples_per_channel, rate, scan_options, flags, data = (
                    self.setup_scan(channels, samples_per_channel, rate, scan_options, flags))

                rate = self.ai_device.a_in_scan(channels[0], channels[-1], input_mode,
                                                range_index, samples_per_channel,
                                                rate, scan_options, flags, data)

                system('clear')

                while self.scanning:
                    try:
                        status, transfer_status = self.ai_device.get_scan_status()
                        index = transfer_status.current_index
                        for i in range(len(channels)):
                            if (index + i) % 2 == 0:
                                self.pressure_transducer.append(data[index + i])
                            else:
                                self.load_cell.append(data[index + i])
                            print(f'chan {channels[i]}: {data[index + i]}')

                    except Exception as e:
                        print('\n', e)

            except Exception as e:
                print('\n', e)

        scan_thread = threading.Thread(target=scan_thread)
        scan_thread.start()

    def stop_scan(self):
        self.scanning = False
        self.pressure_transducer = np.array(self.pressure_transducer)
        self.load_cell = np.array(self.load_cell)
        return self.pressure_transducer, self.load_cell
