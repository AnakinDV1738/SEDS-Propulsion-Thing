from tkinter import *
from tkinter.ttk import *
from typing import Tuple
import customtkinter as ctk
import numpy as np
import re
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import ImageTk, Image

ctk.set_default_color_theme("dark-blue")
ctk.set_appearance_mode("dark")


class UI(ctk.CTk):
    def __init__(self, fg_color: str | Tuple[str, str] | None = None, **kwargs):
        super().__init__(fg_color, **kwargs)

        self.title("UB SEDS Test Fire Interface")
        self.geometry("1000x600")

        img = Image.open("ubseds_white.png")
        img = img.resize((79, 25))
        self.logo = ImageTk.PhotoImage(img)
        self.logo_label = Label(image=self.logo)
        self.logo_label.place(x=10, y=10)

        self.table = Treeview(self, columns=('Weight', 'Voltage'), show="headings")
        self.table.heading('Weight', text='Weight (lb)')
        self.table.heading('Voltage', text='Voltage (mV)')
        self.table.column('Weight', anchor='center', width=115)
        self.table.column('Voltage', anchor='center', width=115)
        self.table.place(x=50, y=150)
        self.table['height'] = 0

        self.y_scroll = Scrollbar(self, orient=VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=self.y_scroll.set)

        self.fig, self.ax = plt.subplots(figsize=(6, 5))
        self.ax.set_xlabel("Weight (lbs)")
        self.ax.set_ylabel("Voltage (mV)")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().place(x=350, y=50)

        self.data_entry_submit_button = ctk.CTkButton(self, text="✔", command=self.get_input_calibration_datapoints)
        self.data_entry_submit_button.configure(height=25, width=20)
        self.data_entry_submit_button.place(x=260, y=100)

        self.data_entry_field = ctk.CTkEntry(self,
                                             placeholder_text="Enter Expression for Weight",
                                             height=25,
                                             width=200)

        self.data_entry_field.place(x=50, y=100)

        self.remove_button = ctk.CTkButton(self, text="❌", command=self.remove_entry)
        self.remove_button.configure(height=25, width=20)
        self.remove_button.place(x=150, y=280)

        self.weights = []
        self.voltages = []

    def get_input_calibration_datapoints(self):
        expression = self.data_entry_field.get()
        conversions = {"kgs": 2.20462, "kg": 2.20462, "lb": 1, "lbs": 1}
        matches = re.findall(r'(\d+(\.\d+)?)\s*([A-Za-z]+)?', expression)  # regex to allow varied units input

        total_pounds = 0
        for match in matches:
            value, _, unit = match
            value = float(value)
            if unit and unit.lower() in conversions:  # Check if unit is specified
                total_pounds += value * conversions[unit.lower()]
            else:
                total_pounds += value  # Default to pounds if no unit is specified

        self.weights.append(total_pounds)
        self.voltages.append(np.random.randint(10000))

        self.update_table()
        self.update_graph()
        self.data_entry_field.delete(0, END)

    def update_table(self):
        self.table.delete(*self.table.get_children())  # Clear the table

        for weight, voltage in zip(self.weights, self.voltages):
            self.table.insert('', 'end', values=(weight, voltage))

        # If the number of entries exceeds table_height, set height to 5 and activate scrollbar
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

        if len(self.weights) >= 5:
            x = np.array(self.weights)
            y = np.array(self.voltages)
            slope, intercept = np.polyfit(x, y, 1)
            self.ax.plot(x, slope * x + intercept, color='red')

            # Add the equation of the line as text
            equation = f'y = {slope:.2f}x + {intercept:.2f}'
            self.ax.text(0.05, 0.95, equation, transform=self.ax.transAxes, fontsize=12,
                         verticalalignment='top')

        self.canvas.draw()

    def remove_entry(self):
        selected_item = self.table.selection()
        if selected_item:
            item = self.table.item(selected_item)
            self.weights.remove(float(item['values'][0]))
            self.voltages.remove(float(item['values'][1]))
            self.update_table()
            self.update_graph()


if __name__ == "__main__":
    ui = UI()
    ui.mainloop()

