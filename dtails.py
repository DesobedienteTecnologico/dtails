#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import tkinter.messagebox as msgbox
from PIL import ImageTk, Image
import os
from src.commands import *
from src.apps import *
import webbrowser
import pyudev
import threading

class MyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DTails")
        style = ttk.Style()
        style.theme_use("clam")
        self.tab_control = ttk.Notebook(self)
        self.tab1 = ttk.Frame(self.tab_control)
        self.tab2 = ttk.Frame(self.tab_control)
        self.tab3 = ttk.Frame(self.tab_control)
        self.tab4 = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab1, text='Select image 💽', state='normal')
        self.tab_control.add(self.tab2, text='Modify and Build the image ⚒️', state='disabled')
        self.tab_control.add(self.tab3, text='Live install 👨‍🔧', state='disabled')
        self.tab_control.add(self.tab4, text='ℹ️', state='normal')
        self.tab_control.pack(expand=1, fill='both')
        self.file_path = tk.StringVar()
        self.checkboxes = []

        ################## Tab 1 ##################
        self.logo_img = Image.open("img/dtails.png")
        self.logo_img = self.logo_img.resize((150, 150))  # Resize image
        self.logo_photo = ImageTk.PhotoImage(self.logo_img)
        logo_label = tk.Label(self.tab1, image=self.logo_photo)
        logo_label.pack(pady=10)

        text_label = tk.Label(self.tab1, text="Remaster your Debian-based image with DTails! 👨‍💻")
        text_label.pack(pady=2)

        if os.path.exists("shared_with_chroot"):
            clean_button = tk.Button(self.tab1, text="Clean old build 🚮", command=remove_directories)
            clean_button.pack()

        separator = ttk.Separator(self.tab1, orient="horizontal")
        separator.pack(fill="x", pady=20)

        select_file_button = tk.Button(self.tab1, text="Select image 💽", command=self.select_file)
        select_file_button.pack(pady=10)

        self.label = tk.Label(self.tab1, textvariable=self.file_path)
        self.label.pack()

        ################## Tab 2 ##################

        # Top Frame
        self.top_frame = tk.Frame(self.tab2)
        self.top_frame.pack(side="top", fill="x", pady=10)
        self.text_label_tab2 = tk.Label(self.top_frame, text="Select the software you would like to install or remove.\nBinaries from the original image will remain unmodified.")
        self.text_label_tab2.pack()

        # Separator between Top Frame and Middle Frame
        self.top_separator = ttk.Separator(self.tab2, orient="horizontal")
        self.top_separator.pack(fill="x", pady=10)

        # Middle Frame containing Left and Right Frames
        self.middle_frame = tk.Frame(self.tab2)
        self.middle_frame.pack(fill="both", expand=True)

        # Left Frame (add software)
        self.left_frame = tk.Frame(self.middle_frame, cursor="plus")
        self.left_frame.pack(side="left", padx=20, fill="both", expand=True)
        self.left_text = tk.Label(self.left_frame, text="Add Software ✅", font="bold")
        self.left_text.pack(pady=5)

        # Now you can use self.left_frame
        self.create_checkbox(self.left_frame, "Sparrow Wallet (106MB)", "")
        self.create_checkbox(self.left_frame, "Liana Wallet (13.8MB)", "")
        self.create_checkbox(self.left_frame, "Bisq (222MB)", "")
        self.create_checkbox(self.left_frame, "BIP39 iancoleman (4.34MB)", "")
        self.create_checkbox(self.left_frame, "SeedTool (6.58MB)", "")
        self.create_checkbox(self.left_frame, "Border Wallets (1.59MB)", "")
        self.create_checkbox(self.left_frame, "Whirlpool GUI (327MB)", "")
        self.create_checkbox(self.left_frame, "Specter Desktop (197MB)", "")
        self.create_checkbox(self.left_frame, "MyCitadel Desktop (4.41MB)", "")
        self.create_checkbox(self.left_frame, "Hodl Hodl and RoboSats (~1MB)", "")
        self.create_checkbox(self.left_frame, "Mempool.space (~1MB)", "")
        self.create_checkbox(self.left_frame, "Briar (221MB)", "")
        self.create_checkbox(self.left_frame, "SimpleX Chat (249MB)", "")
        self.create_checkbox(self.left_frame, "Rana Nostr pubkeys mining tool (1.46MB)", "")
        self.create_checkbox(self.left_frame, "Nostr web clients (~1MB)", "gobbler")
        self.create_checkbox(self.left_frame, "Bitcoin Core (45MB)", "")
        self.create_checkbox(self.left_frame, "Feather Wallet (22MB)", "")
        self.create_checkbox(self.left_frame, "Cake Wallet (77.9MB)", "")

        # Separator between Left and Right Frames
        self.middle_separator = ttk.Separator(self.middle_frame, orient="vertical")
        self.middle_separator.pack(side="left", fill="y", padx=10)

        # Right Frame (Remove Software)
        self.right_frame = tk.Frame(self.middle_frame, cursor="X_cursor")
        self.right_frame.pack(side="right", padx=20, fill="both", expand=True)
        self.right_text = tk.Label(self.right_frame, text="Remove Software ❌", font="bold")
        self.right_text.pack(pady=5)

        # Now you can use self.right_frame
        self.create_checkbox(self.right_frame, "Thunderbird (219MB)", "")
        self.create_checkbox(self.right_frame, "GIMP (90MB)", "")

        # Separator between Middle Frame and Bottom Frame
        self.bottom_separator = ttk.Separator(self.tab2, orient="horizontal")
        self.bottom_separator.pack(fill="x", pady=10)

        # Bottom Frame
        self.bottom_frame = tk.Frame(self.tab2)
        self.bottom_frame.pack(side="bottom", pady=10)
        self.next_button2 = tk.Button(self.bottom_frame, text="Build ⚒️", command=self.get_selected_options)
        self.next_button2.pack()

        ################## Tab 3 ##################
        self.disconnect_button = tk.Label(self.tab3, text="\nChoose the device name from the list.\nDrive will appear at the right. Please, double check it before continuing")
        self.disconnect_button.pack()

        separator = ttk.Separator(self.tab3, orient="horizontal")
        separator.pack(fill="x", pady=40)

        self.pendrive_var = tk.StringVar(self.tab3)
        self.pendrive_dropdown = tk.OptionMenu(self.tab3, self.pendrive_var, "No pendrives found")
        self.pendrive_dropdown.pack()

        self.image_label = tk.Label(self.tab3, text="Please connect a pendrive")
        self.image_label.pack()

        self.connect_button = tk.Button(self.tab3, text="Install to device", state=tk.DISABLED, command=lambda: install_image_to_device(self.pendrive_var.get()))
        self.connect_button.pack()

        def update_pendrives():
            context = pyudev.Context()
            devices = context.list_devices(subsystem='block', ID_BUS='usb')
            self.pendrives = {}
            for device in devices:
                if not device.get('ID_VENDOR'):
                    print_yellow("No USB Manufacturer found on internal database... Using idVendor instead.")
                    self.pendrives[device.get('ID_VENDOR_ID')] = device.device_node
                else:
                    self.pendrives[device.get('ID_VENDOR')] = device.device_node

            self.after(0, self.update_pendrive_ui, self.pendrives, self.pendrive_dropdown)
            self.after(1000, update_pendrives)

        thread = threading.Thread(target=update_pendrives)
        thread.daemon = True
        thread.start()

        ################## Tab 4 ##################
        label2_1 = tk.Label(self.tab4, text='DTails is a tool to remaster live Debian based images.\n\nTwitter (maintainer): @BangalaXMR', cursor="center_ptr")
        label2_1.pack(pady=1)
        label2_1.bind("<Button-1>", lambda e: self.copy_to_clipboard("https://x.com/BangalaXMR"))

        label2 = tk.Label(self.tab4, fg="blue", text='DTails tool - Made by DT and maintained by BangalaXMR with ♥', cursor="hand2")
        label2.pack(pady=10, side="bottom")
        label2.bind("<Button-1>", lambda e: self.callback("https://github.com/BangalaXMR/dtails"))

        self.tab_control.tab(1, state="disabled")
        self.tab_control.tab(2, state="disabled")

    def update_pendrive_ui(self, pendrives, pendrive_dropdown):
        if pendrives:
            if self.pendrive_var.get() == "":
                self.pendrive_var.set("Select device")
            pendrive_dropdown['menu'].delete(0, 'end')
            for pendrive, route in pendrives.items():
                pendrive_dropdown['menu'].add_command(label=pendrive, command=tk._setit(self.pendrive_var, pendrive + " - " + route))
            self.image_label.config(text="Pendrive connected", fg="green")
            self.connect_button.config(state=tk.NORMAL)
        else:
            self.pendrive_var.set("No pendrives found")
            pendrive_dropdown['menu'].delete(0, 'end')
            pendrive_dropdown['menu'].add_command(label="No pendrives found")
            self.image_label.config(text="Please connect a pendrive", fg="black")
            self.connect_button.config(state=tk.DISABLED)

    def print_device_node(self):
        vendor = self.pendrive_var.get()
        device_node = self.pendrives.get(vendor)
        print(device_node)
        # Go to next tab code here

    def disconnect_pendrives(self):
        context = pyudev.Context()
        devices = context.list_devices(subsystem='block', ID_BUS='usb')
        for device in devices:
            device.unmount()
            device.detach()

    def create_checkbox(self, side, text, x_cursor):
        checkbox_var = tk.IntVar()  # create an IntVar to hold the state of the check-box
        checkbox = tk.Checkbutton(side, text=text, variable=checkbox_var, cursor=x_cursor)
        checkbox.pack(pady=5, anchor="w")
        self.checkboxes.append((text, checkbox_var))

    def get_selected_options(self):
        selected_options = []
        selected_options.append("chroot_script") # Add it to be the first executed function
        selected_options.append("add_menu")
        for text, var in self.checkboxes:
            if var.get() == 1:
                selected_options.append(text.rsplit(' ',1)[0].replace(" ", "_").lower())
        selected_options.append("iso_work") # Added to be the last executed function
        print_green(f"Starting...\n")
        for function in selected_options:
            if function == "iso_work":
                iso_work_path = self.file_path.get()
                iso_work(iso_work_path)
            elif '.' in function:
                #print_green(f"Doing: {function}")
                function = function.replace(".", "_")
                function = eval(function)
                function()
            else:
                #print_green(f"Doing: {function}")
                function = eval(function)
                function()
        if iso_work_path.endswith('.iso'):
            self.tab_control.tab(self.tab3, state="normal")
            self.tab_control.select(self.tab3)
        elif iso_work_path.endswith('.img'):
            self.tab_control.tab(self.tab3, state="normal")
            self.tab_control.select(self.tab3)

    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image .iso", "*.iso *.img")])

        if file_path:
            iso_path = file_path
            self.file_path.set(file_path)
            self.tab_control.tab(self.tab2, state="normal")
            self.tab_control.select(self.tab2)

    def copy_to_clipboard(self, texto):
        text = texto
        self.clipboard_clear()
        self.clipboard_append(text)
        msgbox.showinfo("Copied", "Copied to clipboard")

    def callback(self, url):
        webbrowser.open_new(url)

if __name__ == '__main__':
    app = MyApp()
    app.mainloop()
