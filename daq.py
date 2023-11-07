import threading

import numpy as np
from uldaq import (get_daq_device_inventory, DaqDevice, AInScanFlag,
                   AiInputMode, AiQueueElement, create_float_buffer,
                   ScanOption, InterfaceType)
from time import sleep
from os import system
from sys import stdout


class DAQ:
    def __init__(self, interface_type=InterfaceType.ANY):
        self.data = None
        self.scan_thread = None
        self.rate = None
        self.daq_device = None
        self.ai_device = None
        self.interface_type = interface_type
        self.isTerminated = False
        self.channels = [1,2]

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
        try:
            samples_per_channel = 1000  # Define the number of samples per channel
            rate = 1000  # Define the scan rate in Hz
            scan_options = ScanOption.DEFAULTIO | ScanOption.CONTINUOUS  # Define the scan options
            flags = AInScanFlag.DEFAULT  # Define the flags

            channels, input_mode, range_index, samples_per_channel, rate, scan_options, flags, data = (
                self.setup_scan(self.channels, samples_per_channel, rate, scan_options, flags))

            self.rate = rate  # Store rate as an instance variable for future reference
            self.data = data  # Store data buffer as an instance variable for future reference

            self.scan_thread = threading.Thread(target=self._perform_scan,
                                                args=(channels,))  # Pass channels as argument
            self.scan_thread.daemon = True
            self.scan_thread.start()

        except Exception as e:
            print('\n', e)

    def _perform_scan(self, channels):
        try:
            system('clear')
            while not self.isTerminated:
                status, transfer_status = self.ai_device.get_scan_status()
                index = transfer_status.current_index

                self.reset_cursor()
                print('Please enter CTRL + C to terminate the process\n')
                descriptor = self.daq_device.get_descriptor()
                print('Active DAQ device: ', descriptor.dev_string, ' (',
                      descriptor.unique_id, ')\n', sep='')

                print('actual scan rate = ', '{:.6f}'.format(self.rate), 'Hz\n')

                index = transfer_status.current_index
                print('currentTotalCount = ',
                      transfer_status.current_total_count)
                print('currentScanCount = ',
                      transfer_status.current_scan_count)
                print('currentIndex = ', index, '\n')

                for i, channel in enumerate(channels):
                    # Calculate the index for the data corresponding to the current channel
                    data_index = index + i
                    voltage = self.data[data_index]
                    print(f'chan {channel}: {voltage} V')

                sleep(0.1)

        except Exception as e:
            print('\n', e)

        finally:
            self.daq_device.release()

    def get_scan_data(self):
        channel_data = []

        if self.data is not None and self.channels is not None:
            for channel in self.channels:
                start_index = channel * 1000
                end_index = start_index + self.samples_per_channel
                channel_data.append(self.data[start_index:end_index])

        return channel_data

    def terminate_scan(self):
        try:
            self.isTerminated = True

        except Exception as e:
            print('\n', e)

    @staticmethod
    def display_scan_options(bit_mask):
        options = []
        if bit_mask == ScanOption.DEFAULTIO:
            options.append(ScanOption.DEFAULTIO.name)
        for option in ScanOption:
            if option & bit_mask:
                options.append(option.name)
        return ', '.join(options)

    @staticmethod
    def reset_cursor():
        stdout.write('\033[1;1H')

    @staticmethod
    def clear_eol():
        stdout.write('\x1b[2K')


if __name__ == "__main__":
    daq = DAQ()
    daq.connect()


