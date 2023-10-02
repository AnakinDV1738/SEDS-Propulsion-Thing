from tkinter import *
from tkinter.ttk import *
import customtkinter as ctk
import numpy as np
import re
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import ImageTk, Image

ctk.set_default_color_theme("dark-blue")
ctk.set_appearance_mode("dark")

app = ctk.CTk()
app.title("UB SEDS Test Fire Interface")
app.geometry("1000x600")

seds_logo = (Image.open("ubseds_white.png"))
resized_seds_logo = seds_logo.resize((79, 25))
logo = ImageTk.PhotoImage(resized_seds_logo)

table = Treeview(app, columns=('Weight', 'Voltage'), show="headings")
table.heading('Weight', text='Weight (lb)')
table.heading('Voltage', text='Voltage (mV)')
table.column('Weight', anchor='center', width=115)
table.column('Voltage', anchor='center', width=115)
table.place(x=50, y=150)

table_height = 5
table['height'] = table_height

y_scroll = Scrollbar(app, orient=VERTICAL, command=table.yview)
table.configure(yscrollcommand=y_scroll.set)

fig, ax = plt.subplots(figsize=(6, 5))
ax.set_xlabel("Weight (lbs)")
ax.set_ylabel("Voltage (mV)")
canvas = FigureCanvasTkAgg(fig, master=app)
canvas.get_tk_widget().place(x=350, y=50)

weights = []
voltages = []


def remove_entry():
    selected_item = table.selection()
    if selected_item:
        item = table.item(selected_item)
        weights.remove(float(item['values'][0]))
        voltages.remove(float(item['values'][1]))
        update_table()
        update_graph()


def update_graph():
    ax.clear()
    ax.scatter(weights, voltages, color='blue')
    ax.set_xlabel("Weight (lbs)")
    ax.set_ylabel("Voltage (mV)")
    canvas.draw()


def update_table():
    table.delete(*table.get_children())  # Clear the table

    for weight, voltage in zip(weights, voltages):
        table.insert('', 'end', values=(weight, voltage))

    # If the number of entries exceeds table_height, set height to 5 and activate scrollbar
    if len(weights) > table_height:
        table['height'] = table_height
        y_scroll.place(x=280, y=150, height=120)
    else:
        table['height'] = len(weights)
        y_scroll.place_forget()


def get_input_calibration_datapoints():
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
    voltages.append(np.random.randint(10000))

    # This function will eventually be changed
    # to get the mean of 100 readings from the sensor everytime the button is pressed
    # if there is a way to do it natively with python, then great
    # if not, going to have to create a python wrapper

    update_table()
    update_graph()
    data_entry_field.delete(0, END)


def generate_calibration_curve():
    if len(weights) >= 5:
        x = np.array(weights)
        y = np.array(voltages)
        slope, intercept = np.polyfit(x, y, 1)

        plt.figure(figsize=(6, 5))
        plt.scatter(x, y, color='blue')
        plt.plot(x, slope * x + intercept, color='red')
        plt.xlabel("Weight (lbs)")
        plt.ylabel("Voltage (mV)")
        plt.title(f"Linear Regression: y = {slope:.2f}x + {intercept:.2f}")

        canvas_button = FigureCanvasTkAgg(plt.gcf(), master=app)
        canvas_button.get_tk_widget().place(x=350, y=50)


data_entry_submit_button = ctk.CTkButton(app, text="✔", command=get_input_calibration_datapoints)
data_entry_submit_button.configure(height=25, width=20)
data_entry_submit_button.place(x=260, y=100)

data_entry_field = ctk.CTkEntry(app,
                                placeholder_text="Enter Expression for Weight",
                                height=25,
                                width=200)

data_entry_field.place(x=50, y=100)

logo_label = Label(image=logo)
logo_label.place(x=10, y=10)

remove_button = ctk.CTkButton(app, text="❌", command=remove_entry)
remove_button.configure(height=25, width=20)
remove_button.place(x=150, y=280)

generate_curve_button = ctk.CTkButton(app, text="Generate Calibration Curve", command=generate_calibration_curve)
generate_curve_button.place(x=75, y=320)

app.mainloop()
