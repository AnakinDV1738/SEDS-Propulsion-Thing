from tkinter import *
from tkinter.ttk import *
from typing import Tuple
import customtkinter as ctk
import numpy as np
import re
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import ImageTk, Image
from daq import DAQ

'''
UB SEDS Data Logger Interface
An Object-Oriented Approach
'''

ctk.set_default_color_theme("dark-blue")  # theme for the UI
ctk.set_appearance_mode("dark")


class UI(ctk.CTk):
    def __init__(self, fg_color: str | Tuple[str, str] | None = None, **kwargs):  # inherits from CustomTkinter
        # "self." separates instance variables from regular variables
        # all variables with "self." will be created every time a new UI object is created
        super().__init__(fg_color, **kwargs)  # CustomTkinter has its own __init__ method which we are calling

        # Creating two DAQ objects: load cell and pressure transducer
        self.load_cell_daq = DAQ()
        self.pressure_transducer_daq = DAQ()
        self.load_cell_daq.connect(0)
        self.pressure_transducer_daq.connect(1)

        # Title and size
        self.title("UB SEDS Test Fire Interface")
        self.geometry("1000x600")

        # Adding UB SEDS logo to the top-right corner
        img = Image.open("ubseds_white.png")
        img = img.resize((79, 25))
        self.logo = ImageTk.PhotoImage(img)
        self.logo_label = Label(image=self.logo)
        self.logo_label.place(x=10, y=10)

        # Adding interactive table
        # note all the "self" which makes sures that all changes happen to the table instance variable
        self.table = Treeview(self, columns=('Weight', 'Voltage'), show="headings")
        self.table.heading('Weight', text='Weight (lb)')
        self.table.heading('Voltage', text='Voltage (mV)')
        self.table.column('Weight', anchor='center', width=115)
        self.table.column('Voltage', anchor='center', width=115)
        self.table.place(x=50, y=150)
        self.table['height'] = 0

        # Adding scrollbar to the table which will only appear when there are 5 or more entries
        self.y_scroll = Scrollbar(self, orient=VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=self.y_scroll.set)

        # Adding graph
        self.fig, self.ax = plt.subplots(figsize=(6, 5))
        self.ax.set_xlabel("Weight (lbs)")
        self.ax.set_ylabel("Voltage (mV)")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().place(x=350, y=50)

        # Adding check mark button
        # (Very important) Any CustomTkinter components take "self" as a parameter
        # Takes text to appear inside button (using emoji) and command which is what you want button to do
        self.data_entry_submit_button = ctk.CTkButton(self, text="✔", command=self.get_input_calibration_datapoints)
        self.data_entry_submit_button.configure(height=25, width=20)
        self.data_entry_submit_button.place(x=260, y=100)

        # Adding textbox to enter numbers into
        self.data_entry_field = ctk.CTkEntry(self,
                                             placeholder_text="Enter Expression for Weight",
                                             height=25,
                                             width=200)

        self.data_entry_field.place(x=50, y=100)

        # Remove button to delete entries from table/graph
        self.remove_button = ctk.CTkButton(self, text="❌", command=self.remove_entry)
        self.remove_button.configure(height=25, width=20)
        self.remove_button.place(x=150, y=280)

        # Calibration weight and voltages stored here, gets updated every time datapoints get added or removed
        self.weights = []
        self.voltages = []

    # Function to get entries from the textbox
    # See "data_entry_submit_button" command, its this function
    def get_input_calibration_datapoints(self):
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
        self.voltages.append(self.load_cell_daq.get_calibration_voltage())

        # Everytime there is a change to the weights/voltages, we update the table and graph
        self.update_table()
        self.update_graph()
        # After everything that we want to happen, happens, the textbox is cleared for the next entry
        self.data_entry_field.delete(0, END)

    # Removing entries, very basic: remove from the lists, and then update the table and graph
    def remove_entry(self):
        selected_item = self.table.selection()
        if selected_item:
            item = self.table.item(selected_item)
            self.weights.remove(float(item['values'][0]))
            self.voltages.remove(float(item['values'][1]))
            self.update_table()
            self.update_graph()

    # update_table and update_graph check the lists, erase what they have currently and generate a brand-new table
    def update_table(self):
        self.table.delete(*self.table.get_children())  # Clear the table

        for weight, voltage in zip(self.weights, self.voltages):
            self.table.insert('', 'end', values=(weight, voltage))  # Iterating through the current lists

        # If the number of entries exceeds 5, set height to 5 and activate scrollbar
        if len(self.weights) > 5:
            self.table['height'] = 5
            self.y_scroll.place(x=280, y=150, height=120)
        else:
            self.table['height'] = len(self.weights)
            self.y_scroll.place_forget()

    def update_graph(self):
        self.ax.clear()
        self.ax.scatter(self.weights, self.voltages, color='blue')
        self.ax.set_xlabel("Weight (lbs)")
        self.ax.set_ylabel("Voltage (mV)")

        # If number of entries exceeds 5, generate a linear regression line on top of the graph and display the equation
        if len(self.weights) >= 5:
            x = np.array(self.weights)  # converting lists into numpy arrays, so we can do numpy function on them
            y = np.array(self.voltages)
            slope, intercept = np.polyfit(x, y, 1)  # np.polyfit to generate weight and bias
            self.ax.plot(x, slope * x + intercept, color='red')

            # Add the equation of the line as text
            equation = f'y = {slope:.2f}x + {intercept:.2f}'
            self.ax.text(0.05, 0.95, equation, transform=self.ax.transAxes, fontsize=12,
                         verticalalignment='top')

        self.canvas.draw()


# Run the code with a __main__ function
# Equivalent to "public static void main(String[] args)" from Java
if __name__ == "__main__":
    ui = UI()
    ui.mainloop()

'''
Calibration interface is more or less complete

Next Steps
1. Add a "finish" button that concludes calibration and stores weight and bias in instance variables
2. Clear the screen and add "start test fire" button which should be pressed just before the switch is flipped
    a. maybe make this button the actual button that triggers the test fire (later update)
    b. add a secondary check to make sure that user intended to start test fire
3. Live data reading will be hard -- add animation that says test fire in progress dot dot dot (something fun!)
    a. When the secondary check is confirmed, replace start test fire button with "end test fire" button
    b. Store all the data in pandas dataframe - easy to analyze (download necessary libraries on RaspberryPi)
    c. Display pressure transducer data, and raw load cell data
    d. Display calibrated load cell data
    e. Ask Schooner what other data analysis needs to be done
    
- Parth
'''