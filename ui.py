from tkinter import *
from tkinter.ttk import *
from typing import Tuple, Union
import customtkinter as ctk
import numpy as np
import re
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# from PIL import ImageTk, Image
from enum import Enum

from daq import DAQ

'''
UB SEDS Data Logger Interface
An Object-Oriented Approach
'''


# This is an enum: you can make your own custom datatype
# My datatypes are of type ui_states, and they have two possible values: CALIBRATION, and TEST_FIRE
# The values they are assigned are arbitrary
class ui_states(Enum):
    CALIBRATION = 1
    TEST_FIRE = 2


class calibration_states(Enum):
    REMINDER = 1
    INTERFACE = 2


# Enum for test fire states
class test_fire_ui_states(Enum):
    START = 1
    DATA_ACQUISITION = 2
    FINISHED = 3


ctk.set_default_color_theme("dark-blue")  # theme for the UI
ctk.set_appearance_mode("dark")


class UI(ctk.CTk):
    def __init__(self, fg_color: Union[str, Tuple[str, str], None] = None, **kwargs):  # inherits from CustomTkinter
        # "self." separates instance variables from regular variables
        # all variables with "self." will be created every time a new UI object is created
        super().__init__(fg_color, **kwargs)  # CustomTkinter has its own __init__ method which we are calling

        # Creating two DAQ objects: load cell and pressure transducer and connecting to them
        # self.pressure_transducer_daq = DAQ()
        # self.pressure_transducer_daq.connect(1)

        self.ui_state = ui_states.CALIBRATION  # Initial state of UI
        self.calibration_state = calibration_states.REMINDER
        self.test_fire_state = None

        # Title and size
        self.title("UB SEDS Test Fire Interface")
        self.geometry("1000x600")

        # Adding UB SEDS logo to the top-left corner
        # img = Image.open("ubseds_white.png")
        # img = img.resize((79, 25))
        # self.logo = ImageTk.PhotoImage(img)
        # self.logo_label = Label(image=self.logo)
        # self.logo_label.place(x=10, y=10)

        # Adding interactive table
        # note all the "self" which makes sures that all changes happen to the table instance variable
        self.data_table = Treeview(self, columns=('Voltage', 'Weight'), show="headings")
        self.data_table.heading('Voltage', text='Voltage (mV)')
        self.data_table.heading('Weight', text='Weight (lb)')
        self.data_table.column('Voltage', anchor='center', width=115)
        self.data_table.column('Weight', anchor='center', width=115)
        self.data_table['height'] = 0

        # Adding scrollbar to the table which will only appear when there are 5 or more entries
        self.y_scroll = Scrollbar(self, orient=VERTICAL, command=self.data_table.yview)
        self.data_table.configure(yscrollcommand=self.y_scroll.set)

        # Adding graph
        self.fig, self.ax = plt.subplots(figsize=(6, 5))
        self.ax.set_ylabel("Weight (lbs)")
        self.ax.set_xlabel("Voltage (mV)")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)

        # Adding check mark button
        # (Very important) Any CustomTkinter components take "self" as a parameter
        # Takes text to appear inside button (using emoji) and command which is what you want button to do
        self.data_entry_submit_button = ctk.CTkButton(self, text="✔", command=self.get_input_calibration_datapoints)
        self.data_entry_submit_button.configure(height=25, width=20)

        # Adding textbox to enter numbers into
        self.data_entry_field = ctk.CTkEntry(self,
                                             placeholder_text="Enter Expression for Weight",
                                             height=25,
                                             width=200)

        # Remove button to delete entries from table/graph
        self.remove_button = ctk.CTkButton(self, text="❌", command=self.remove_entry)
        self.remove_button.configure(height=25, width=20)

        # Finish Calibration button to transition UI from calibration to test fire
        self.finish_calibration_button = ctk.CTkButton(self, text="FINISH CALIBRATION", command=self.finish_calibration)
        self.finish_calibration_button.configure(height=20)

        # Adding BIG REMINDER BUTTON FOR PROPULSION -- IF THEY MESS THIS UP, NOT MY PROBLEM
        self.big_flashing_reminder_button = ctk.CTkButton(self, text="HI SCHOONER!!!\n"
                                                                     "PLEASE MAKE SURE\n"
                                                                     "TO PUT THE PRESSURE TRANSDUCER INTO CH0\n"
                                                                     "AND\n"
                                                                     "PUT THE LOAD CELL INTO CH1\n"
                                                                     "PLEASE CLICK THE BUTTON\n"
                                                                     "IF AND ONLY IF YOU HAVE CORRECTLY\n"
                                                                     "SET UP THE DAQ!!! - PARTH",
                                                          command=self.schooner_has_been_reminded)
        self.big_flashing_reminder_button.configure(font=('Arial', 40), fg_color='red')

        # Begin Test Fire button for the test fire UI
        self.begin_test_fire = ctk.CTkButton(self, text="Start Test Fire")  # Need to add command

        # Storing the linear regression parameters everytime we have 5 or more datapoints
        self.slope = None
        self.intercept = None

        # Displaying Linear Regressions Parameters
        self.linear_regression_parameters = Label(self)

        # Calibration weight and voltages stored here, gets updated every time datapoints get added or removed
        self.weights = []
        self.voltages = []

        self.set_UI_visibility_based_on_state()

    def clear_screen(self):
        if self.winfo_children():
            for child in self.winfo_children():
                child.pack_forget()
                child.place_forget()

    def set_UI_visibility_based_on_state(self):
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
                self.linear_regression_parameters.place(x=400, y=0)
                self.linear_regression_parameters.config(text=f"Linear Regression Parameters\n"
                                                              f"Slope: {round(self.slope, 3)}\n"
                                                              f"Intercept: {round(self.intercept, 3)}")

    # Function to get entries from the textbox
    # See "data_entry_submit_button" command, its this function
    def get_input_calibration_datapoints(self):
        if self.ui_state == ui_states.CALIBRATION:
            load_cell_daq = DAQ()
            load_cell_daq.connect()
            expression = self.data_entry_field.get()  # Method from CustomTkinter to get the values inside the textbox
            conversions = {"kgs": 2.20462, "kg": 2.20462, "lb": 1, "lbs": 1}  # Map of units to their conversions in lbs
            matches = re.findall(r'(\d+(\.\d+)?)\s*([A-Za-z]+)?', expression)  # regex to allow varied units input

            # Some logic to get number from expression such as "2 kgs + 3 lbs"
            total_pounds = 0
            for match in matches:
                value, _, unit = match
                value = float(value)
                if unit and unit.lower() in conversions:  # Check if unit is specified
                    total_pounds += value * conversions[unit.lower()]
                else:
                    total_pounds += value  # Default to pounds if no unit is specified

            # Adding weights from textbox into the weights list (INSTANCE VARIABLE)
            self.weights.append(total_pounds)
            # Adding calibration voltage, calling method on load_cell_daq object, check daq.py for implementation
            # self.voltages.append(np.random.randint(10000))
            self.voltages.append(load_cell_daq.get_calibration_voltage())
            # And I can't test this code if this line is in there because I don't have a DAQ connected
            load_cell_daq.disconnect()
            # Everytime there is a change to the weights/voltages, we update the table and graph
            self.update_table()
            self.update_graph()
            # After everything that we want to happen, happens, the textbox is cleared for the next entry
            self.data_entry_field.delete(0, END)

    # Removing entries, very basic: remove from the lists, and then update the table and graph
    def remove_entry(self):
        if self.ui_state == ui_states.CALIBRATION and self.calibration_state == calibration_states.INTERFACE:
            selected_item = self.data_table.selection()
            if selected_item:
                item = self.data_table.item(selected_item)
                self.weights.remove(float(item['values'][0]))
                self.voltages.remove(float(item['values'][1]))
                self.update_table()
                self.update_graph()

    # update_table and update_graph check the lists, erase what they have currently and generate a brand-new table
    def update_table(self):
        if self.ui_state == ui_states.CALIBRATION and self.calibration_state == calibration_states.INTERFACE:
            self.data_table.delete(*self.data_table.get_children())  # Clear the table

            for weight, voltage in zip(self.weights, self.voltages):
                self.data_table.insert('', 'end', values=(weight, voltage))  # Iterating through the current lists

            # If the number of entries exceeds 5, set height to 5 and activate scrollbar
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

            # If number of entries exceeds 5, generate a linear regression line and display the equation
            if len(self.weights) >= 5:
                y = np.array(self.weights)  # converting lists into numpy arrays, so we can do numpy function on them
                x = np.array(self.voltages)
                self.slope, self.intercept = np.polyfit(x, y, 1)  # np.polyfit to generate weight and bias
                self.ax.plot(x, self.slope * x + self.intercept, color='red')

                # Add the equation of the line as text
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


# Run the code with a __main__ function
# Equivalent to "public static void main(String[] args)" from Java
if __name__ == "__main__":
    ui = UI()
    ui.mainloop()

'''
Calibration interface is more or less complete
Next Steps
1. Add a "finish" button that concludes calibration and stores weight and bias in instance variables (finished)
2. Clear the screen and add "start test fire" button which should be pressed just before the switch is flipped
    a. maybe make this button the actual button that triggers the test fire (later update)
3. Live data reading will be hard
    a. Have a live counter of the data being collected
    b. Store all the data in pandas dataframe - easy to analyze (download necessary libraries on RaspberryPi)
    c. Display pressure transducer data, and raw load cell data (processed slightly)
    d. Display calibrated load cell data
    e. Ask Schooner what other data analysis needs to be done
- Parth
'''
