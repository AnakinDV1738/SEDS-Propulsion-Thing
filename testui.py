from tkinter import *
from tkinter import ttk
from tkinter.ttk import *
from typing import Tuple, Union
import customtkinter as ctk
import numpy as np
import re
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from enum import Enum
import tkinter as tk
# from daq import DAQ

class ui_states(Enum):
   CALIBRATION = 1
   TEST_FIRE = 2

class calibration_states(Enum):
   REMINDER = 1
   INTERFACE = 2

class test_fire_ui_states(Enum):
   START = 1
   DATA_ACQUISITION = 2
   RAW_LOAD_CELL = 3
   PRESSURE_TRANSDUCER = 4
   CALIBRATED_LOAD_CELL = 5
   SAVE_DATA = 6

ctk.set_default_color_theme("dark-blue")  
ctk.set_appearance_mode("dark")

class UI(ctk.CTk):
   def __init__(self, fg_color: Union[str, Tuple[str, str], None] = None, **kwargs):  
       super().__init__(fg_color, **kwargs)  

       self.ui_state = ui_states.CALIBRATION  # Initial state of UI
       self.calibration_state = calibration_states.REMINDER
       self.test_fire_state = None

       self.pressure_transducer_data = None
       self.load_cell_data = None
       # self.test_fire_daq = None

       self.title("UB SEDS Test Fire Interface")
       self.geometry("1000x600")

       self.data_table = Treeview(self, columns=('Weight', 'Voltage'), show="headings")
       self.data_table.heading('Weight', text='Weight (lb)')
       self.data_table.heading('Voltage', text='Voltage (mV)')
       self.data_table.column('Weight', anchor='center', width=115)
       self.data_table.column('Voltage', anchor='center', width=115)
       self.data_table['height'] = 0

       self.y_scroll = Scrollbar(self, orient=VERTICAL, command=self.data_table.yview)
       self.data_table.configure(yscrollcommand=self.y_scroll.set)

       self.fig, self.ax = plt.subplots(figsize=(6, 5))
       self.ax.set_ylabel("Weight (lbs)")
       self.ax.set_xlabel("Voltage (mV)")
       self.canvas = FigureCanvasTkAgg(self.fig, master=self)

       self.data_entry_submit_button = ctk.CTkButton(self, text="✔", command=self.get_input_calibration_datapoints)
       self.data_entry_submit_button.configure(height=25, width=20)

       self.data_entry_field = ctk.CTkEntry(self,
                                            placeholder_text="Enter Expression for Weight",
                                            height=25,
                                            width=200)

       self.remove_button = ctk.CTkButton(self, text="X", command=self.remove_entry)
       self.remove_button.configure(height=25, width=20)

       self.finish_calibration_button = ctk.CTkButton(self, text="FINISH CALIBRATION", command=self.finish_calibration)
       self.finish_calibration_button.configure(height=20)

       self.big_flashing_reminder_button = ctk.CTkButton(self, text="HI SCHOONER!!!\n"
                                                                    "PLEASE MAKE SURE\n"
                                                                    "TO PUT THE PRESSURE TRANSDUCER INTO CH0\n"
                                                                    "AND\n"
                                                                    "PUT THE LOAD CELL INTO CH1\n"
                                                                    "PLEASE CLICK THIS BUTTON\n"
                                                                    "IF AND ONLY IF YOU HAVE CORRECTLY\n"
                                                                    "SET UP THE DAQ!!! - PARTH",
                                                         command=self.schooner_has_been_reminded)
       self.big_flashing_reminder_button.configure(font=('Arial', 40), fg_color='red')

       self.begin_test_fire = ctk.CTkButton(self, text="Start Test Fire", command=self.start_test_fire_button)

       self.timer = 0
       self.timer_label = Label(self, text=f"{self.timer} ms", font=("arial", 24))

       self.terminate_button = ctk.CTkButton(self, text="TERMINATE TEST FIRE", command=self.terminate_test_fire_button)

       self.slope = None
       self.intercept = None

       self.linear_regression_parameters = Label(self)

       self.weights = []
       self.voltages = []

       self.date_label = tk.Label(self, text="Enter Date:")
       self.day_label = ttk.Label(self, text="Day:")
       self.day_combobox = ttk.Combobox(self, values=list(range(1, 32)))

       self.set_UI_visibility_based_on_state()

   def change_state(self, new_test_fire_state):
       self.test_fire_state = new_test_fire_state
       self.set_UI_visibility_based_on_state()

   def create_state_change_button_for_test_fire_ui(self, text, new_test_fire_state):
       button = ctk.CTkButton(self, text=text, command=lambda: self.change_state(new_test_fire_state))
       return button

   def test_fire_label_factory(self, text):
       return Label(self, text=text, justify="center")

   def graph_factory(self, x_label, y_label, data):
       fig, ax = plt.subplots(figsize=(6, 5))
       ax.set_ylabel(y_label)
       ax.set_xlabel(x_label)
       canvas = FigureCanvasTkAgg(fig, master=self)
       canvas.get_tk_widget().pack(expand=True)
       ax.plot(range(len(data)), data)
       return fig, ax, canvas

   def clear_screen(self):
       if self.winfo_children():
           for child in self.winfo_children():
               child.pack_forget()
               child.place_forget()

   def set_UI_visibility_based_on_state(self):
       print(self.ui_state, self.calibration_state, self.test_fire_state)
       self.clear_screen()
       if self.ui_state == ui_states.CALIBRATION:
           if self.calibration_state == calibration_states.REMINDER:
               self.big_flashing_reminder_button.pack(expand=True)
           elif self.calibration_state == calibration_states.INTERFACE:
               self.data_table.place(x=50, y=150)
               self.canvas.get_tk_widget().place(x=350, y=50)
               self.data_entry_submit_button.place(x=260, y=100)
               self.data_entry_field.place(x=50, y=100)
               self.remove_button.place(x=150, y=280)
               self.finish_calibration_button.place(x=90, y=330)
       else:
           if self.test_fire_state == test_fire_ui_states.START:
               self.begin_test_fire.pack(expand=True)
               self.linear_regression_parameters.place(x=400, y=10)
               self.linear_regression_parameters.config(text=f"Linear Regression Parameters\n"
                                                             f"Slope: {round(self.slope, 3)}\n"
                                                             f"Intercept: {round(self.intercept, 3)}",
                                                        justify="center")
           elif self.test_fire_state == test_fire_ui_states.DATA_ACQUISITION:
               self.terminate_button.pack(expand=True)
               self.timer_label.place(x=10, y=10)
               self.timer_update()
           elif self.test_fire_state == test_fire_ui_states.PRESSURE_TRANSDUCER:
               self.graph_factory("Time", "Voltage", self.pressure_transducer_data)
               self.test_fire_label_factory("Pressure Transducer Data").place(x=425, y=10)
               self.create_state_change_button_for_test_fire_ui("Next",
                                                                test_fire_ui_states.RAW_LOAD_CELL).place(x=850, y=10)
           elif self.test_fire_state == test_fire_ui_states.RAW_LOAD_CELL:
               self.graph_factory("Time", "Voltage", self.load_cell_data)
               self.test_fire_label_factory("Raw Load Cell Data").place(x=425, y=10)
               self.create_state_change_button_for_test_fire_ui("Next",
                                                                test_fire_ui_states.CALIBRATED_LOAD_CELL).place(x=850,
                                                                                                                y=10)
               self.create_state_change_button_for_test_fire_ui("Previous",
                                                                test_fire_ui_states.PRESSURE_TRANSDUCER).place(x=10,
                                                                                                               y=10)
           elif self.test_fire_state == test_fire_ui_states.CALIBRATED_LOAD_CELL:
               data = self.slope * self.load_cell_data + self.intercept
               self.graph_factory("Time", "Weight (lb)", data)
               self.test_fire_label_factory("Calibrated Load Cell Data").place(x=425, y=10)
               self.create_state_change_button_for_test_fire_ui("Next", test_fire_ui_states.SAVE_DATA).place(x=850,
                                                                                                             y=10)
               self.create_state_change_button_for_test_fire_ui("Previous",
                                                                test_fire_ui_states.RAW_LOAD_CELL).place(x=10, y=10)
           elif self.test_fire_state == test_fire_ui_states.SAVE_DATA:
               self.dropdown_menu.pack()

   def get_input_calibration_datapoints(self):
       if self.ui_state == ui_states.CALIBRATION:
           # load_cell_daq = DAQ()
           # load_cell_daq.connect()
           expression = self.data_entry_field.get()  
           conversions = {"kgs": 2.20462, "kg": 2.20462, "lb": 1, "lbs": 1}  
           matches = re.findall(r'(\d+(\.\d+)?)\s*([A-Za-z]+)?', expression)  

           total_pounds = 0
           for match in matches:
               value, _, unit = match
               value = float(value)
               if unit and unit.lower() in conversions:  
                   total_pounds += value * conversions[unit.lower()]
               else:
                   total_pounds += value 

           self.weights.append(total_pounds)
           self.voltages.append(np.random.randint(10000))
           # self.voltages.append(load_cell_daq.get_calibration_voltage())
           # load_cell_daq.disconnect()
           self.update_table()
           self.update_graph()
           self.data_entry_field.delete(0, END)

   def remove_entry(self):
       if self.ui_state == ui_states.CALIBRATION and self.calibration_state == calibration_states.INTERFACE:
           selected_item = self.data_table.selection()
           if selected_item:
               item = self.data_table.item(selected_item)
               self.weights.remove(float(item['values'][0]))
               self.voltages.remove(float(item['values'][1]))
               self.update_table()
               self.update_graph()

   def update_table(self):
       if self.ui_state == ui_states.CALIBRATION and self.calibration_state == calibration_states.INTERFACE:
           self.data_table.delete(*self.data_table.get_children())  

           for weight, voltage in zip(self.weights, self.voltages):
               self.data_table.insert('', 'end', values=(weight, voltage))  

           if len(self.weights) > 5:
               self.data_table['height'] = 5
               self.y_scroll.place(x=280, y=150, height=120)
           else:
               self.data_table['height'] = len(self.weights)
               self.y_scroll.place_forget()


   def update_graph(self):
       if self.ui_state == ui_states.CALIBRATION and self.calibration_state == calibration_states.INTERFACE:
           self.ax.clear()
           self.ax.scatter(self.voltages, self.weights, color='blue')
           self.ax.set_xlabel("Voltage (mV)")
           self.ax.set_ylabel("Weight (lbs)")

           if len(self.weights) >= 5:
               y = np.array(self.weights)  
               x = np.array(self.voltages)
               self.slope, self.intercept = np.polyfit(x, y, 1)  
               self.ax.plot(x, self.slope * x + self.intercept, color='red')

               equation = f'y = {self.slope:.2f}x + {self.intercept:.2f}'
               self.ax.text(0.05, 0.95, equation, transform=self.ax.transAxes, fontsize=12,
                            verticalalignment='top')

           self.canvas.draw()

   def finish_calibration(self):
       if (len(self.weights) >= 5 and
               self.ui_state == ui_states.CALIBRATION and
               self.calibration_state == calibration_states.INTERFACE):
           self.ui_state = ui_states.TEST_FIRE
           self.calibration_state = None
           self.test_fire_state = test_fire_ui_states.START
           self.set_UI_visibility_based_on_state()

   def schooner_has_been_reminded(self):
       if self.ui_state == ui_states.CALIBRATION and self.calibration_state == calibration_states.REMINDER:
           self.calibration_state = calibration_states.INTERFACE
           self.set_UI_visibility_based_on_state()

   def start_test_fire_button(self):
       if self.ui_state == ui_states.TEST_FIRE and self.test_fire_state == test_fire_ui_states.START:
           self.test_fire_state = test_fire_ui_states.DATA_ACQUISITION
           # self.test_fire_daq = DAQ()
           # self.test_fire_daq.connect()
           # self.test_fire_daq.start_scan()
           self.set_UI_visibility_based_on_state()

   def timer_update(self):
       self.timer += 1
       self.timer_label.config(text=f"{self.timer} s", font=("Arial", 24))
       self.after(1000, self.timer_update)


   def terminate_test_fire_button(self):
       if self.ui_state == ui_states.TEST_FIRE and self.test_fire_state == test_fire_ui_states.DATA_ACQUISITION:
           self.pressure_transducer_data, self.load_cell_data = np.random.randn(10000, 1), np.random.randn(10000, )
           # self.test_fire_daq.disconnect()
           # self.test_fire_daq.release()
           self.test_fire_state = test_fire_ui_states.PRESSURE_TRANSDUCER
           self.set_UI_visibility_based_on_state()

   def save_data_as_csv(self):
       np.savetxt("pressure_transducer.csv", self.pressure_transducer_data, delimiter=",")
       np.savetxt("raw_load_cell.csv", self.load_cell_data, delimiter=",")
       calibrated_data = self.slope * self.load_cell_data + self.intercept
       np.savetxt("calibrated_load_cell.csv", calibrated_data, delimiter=",")


if __name__ == "__main__":
   ui = UI()
   ui.mainloop()