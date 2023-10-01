from tkinter import *
from tkinter.ttk import *
import customtkinter as ctk
import numpy as np
import re

ctk.set_default_color_theme("dark-blue")
ctk.set_appearance_mode("dark")

app = ctk.CTk()
app.title("UB SEDS Test Fire Interface")
app.geometry("1000x600")


table = Treeview(app, columns=('Weight', 'Voltage'), show="headings")
table.heading('Weight', text='Weight (lb)')
table.heading('Voltage', text='Voltage (mV)')
table.column('Weight', anchor='center', width=115)
table.column('Voltage', anchor='center', width=115)
table.place(x=50, y=150)

table_height = 5
table['height'] = table_height

# Create vertical scrollbar
y_scroll = Scrollbar(app, orient=VERTICAL, command=table.yview)
table.configure(yscrollcommand=y_scroll.set)


def update_table():
    table.delete(*table.get_children())  # Clear the table

    for weight, voltage in zip(weights, voltages):
        table.insert('', 'end', values=(weight, voltage))

    # If the number of entries exceeds table_height, set height to 5 and activate scrollbar
    if len(weights) > table_height:
        table['height'] = table_height
        y_scroll.place(x=280, y=150, height=100)
    else:
        table['height'] = len(weights)
        y_scroll.place_forget()


def get_input_calibration_weight():
    expression = data_entry_field.get()
    conversions = {"kgs": 2.20462, "kg": 2.20462, "lb": 1, "lbs": 1}
    matches = re.findall(r'(\d+(\.\d+)?)\s*([A-Za-z]+)', expression)

    total_pounds = 0
    for match in matches:
        value, _, unit = match
        value = float(value)
        if unit.lower() in conversions:
            total_pounds += value * conversions[unit.lower()]

    weights.append(total_pounds)
    update_table()

    data_entry_field.delete(0, END)


def get_calibration_voltage():
    voltages.append(np.random.randint(10000))
    update_table()
    # This function will eventually be changed
    # to get the mean of 100 readings from the sensor everytime the button is pressed
    # if there is a way to do it natively with python, then great
    # if not, going to have to create a python wrapper


weights = []
voltages = []

data_entry_submit_button = ctk.CTkButton(app, text="✔", command=lambda: [get_input_calibration_weight(), get_calibration_voltage()])
data_entry_submit_button.configure(height=25, width=20)
data_entry_submit_button.place(x=260, y=100)


data_entry_field = ctk.CTkEntry(app,
                                placeholder_text="Enter Expression for Weight",
                                height=25,
                                width=200)

data_entry_field.place(x=50, y=100)


app.mainloop()
