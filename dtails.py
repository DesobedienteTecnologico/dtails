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

        # Create tab views
        self.tab_control = ttk.Notebook(self)
        self.tab1 = ttk.Frame(self.tab_control)
        self.tab2 = ttk.Frame(self.tab_control)
        self.tab3 = ttk.Frame(self.tab_control)
        self.tab4 = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab1, text='Select image')
        self.tab_control.add(self.tab2, text='Modify and Build the image')
        self.tab_control.add(self.tab3, text='Live install')
        self.tab_control.add(self.tab4, text='About')
        self.tab_control.pack(expand=1, fill='both')
        self.file_path = tk.StringVar()
        self.checkboxes = []

        ################## Tab 1 ##################
        self.logo_img = Image.open("img/dtails.png")
        self.logo_img = self.logo_img.resize((150, 150))  # Resize image
        self.logo_photo = ImageTk.PhotoImage(self.logo_img)
        logo_label = tk.Label(self.tab1, image=self.logo_photo)
        logo_label.pack(pady=10)

        text_label = tk.Label(self.tab1, text="Remaster your Debian-based image with DTails! :)")
        text_label.pack(pady=2)

        if os.path.exists("shared_with_chroot"):
            clean_button = tk.Button(self.tab1, text="Clean old build", command=remove_directories)
            clean_button.pack()

        separator = ttk.Separator(self.tab1, orient="horizontal")
        separator.pack(fill="x", pady=20)

        select_file_button = tk.Button(self.tab1, text="Select image", command=self.select_file)
        select_file_button.pack(pady=10)

        self.label = tk.Label(self.tab1, textvariable=self.file_path)
        self.label.pack()

        ################## Tab 2 ##################
        text_label = tk.Label(self.tab2, text="Select the software you would like to install or remove.\nBinaries from the original image will still unmodified.")
        text_label.pack(pady=10)

        separator = ttk.Separator(self.tab2, orient="horizontal")
        separator.pack(fill="x", pady=10)

        left_frame = tk.Frame(self.tab2, cursor="plus")
        left_frame.pack(side="left", padx=20)

        right_frame = tk.Frame(self.tab2, cursor="X_cursor")
        right_frame.pack(side="right", padx=20)

        left_text = tk.Label(left_frame, text="Add software", font="bold")
        left_text.pack(pady=5)

        self.create_checkbox(left_frame, "Sparrow Wallet (106MB)", "")
        self.create_checkbox(left_frame, "Liana Wallet (13.8MB)", "")
        self.create_checkbox(left_frame, "Bisq (222MB)", "")
        self.create_checkbox(left_frame, "BIP39 iancoleman (4.34MB)", "")
        self.create_checkbox(left_frame, "SeedTool (6.58MB)", "")
        self.create_checkbox(left_frame, "Border Wallets (1.59MB)", "")
        self.create_checkbox(left_frame, "Hodl Hodl and RoboSats (~1MB)", "")
        self.create_checkbox(left_frame, "Mempool.space (~1MB)", "")
        self.create_checkbox(left_frame, "Briar (221MB)", "")
        self.create_checkbox(left_frame, "Nostr web clients (~1MB)", "gobbler")

        right_text = tk.Label(right_frame, text="Remove software", font="bold")
        right_text.pack(pady=5)

        self.create_checkbox(right_frame, "Thunderbird (219MB)", "")
        self.create_checkbox(right_frame, "GIMP (90MB)", "")


        next_button2 = tk.Button(self.tab2, text="Build", command=self.get_selected_options)
        next_button2.pack(side="bottom", pady=10)


        ################## Tab 3 ##################
        self.disconnect_button = tk.Label(self.tab3, text="\nChoose the device name from the list.\nDrive will appear at the right. Please, double check it before continuing")
        self.disconnect_button.pack()

        separator = ttk.Separator(self.tab3, orient="horizontal")
        separator.pack(fill="x", pady=40)

        self.pendrive_var = tk.StringVar(self.tab3)
        pendrive_dropdown = tk.OptionMenu(self.tab3, self.pendrive_var, "No pendrives found")
        pendrive_dropdown.pack()

        self.image_label = tk.Label(self.tab3, text="Please connect a pendrive")
        self.image_label.pack()

        #self.connect_button = tk.Button(self, text="Go to next tab", state=tk.DISABLED, command=self.master.select_next_tab)
        self.connect_button = tk.Button(self.tab3, text="Install to device", state=tk.DISABLED, command=lambda: install_image_to_device(self.pendrive_var.get()))

        self.connect_button.pack()
        def update_pendrives():
            context = pyudev.Context()
            devices = context.list_devices(subsystem='block', ID_BUS='usb')
            self.pendrives = {}
            for device in devices:
                if not device.get('ID_VENDOR'):
                    print_yellow("No USB Manufacturer found on internal database... Using idVendor instead.")
                    self.pendrives[device.get('ID_VENDOR_ID')] = device.device_node[:-1]
                else:
                    self.pendrives[device.get('ID_VENDOR')] = device.device_node[:-1]
            if self.pendrives:
                #self.pendrive_var.set(list(self.pendrives)[0])
                if self.pendrive_var.get() == "":
                    self.pendrive_var.set("Select device")
                pendrive_dropdown['menu'].delete(0, 'end')
                for pendrive, route in self.pendrives.items():
                    pendrive_dropdown['menu'].add_command(label=pendrive, command=tk._setit(self.pendrive_var, pendrive +" - "+ route))
                #self.pendrive_var.set("Select device")
                self.image_label.config(text="Pendrive connected", fg="green")
                self.connect_button.config(state=tk.NORMAL)
            else:
                self.pendrive_var.set("No pendrives found")
                pendrive_dropdown['menu'].delete(0, 'end')
                pendrive_dropdown['menu'].add_command(label="No pendrives found")
                self.image_label.config(text="Please connect a pendrive", fg="black")
                self.connect_button.config(state=tk.DISABLED)
            self.after(1000, update_pendrives)

        thread = threading.Thread(target=update_pendrives)
        thread.daemon = True
        thread.start()

        ################## Tab 4 ##################
        label4_1 = tk.Label(self.tab4, text='DTails is a tool to remaster live Debian based images.\n\nTwitter: @DesobedienteTec', cursor="center_ptr")
        label4_1.pack(pady=1)
        label4_1.bind("<Button-1>", lambda e: self.copy_to_clipboard("https://twitter.com/DesobedienteTec"))

        label4_2 = tk.Label(self.tab4, text='nostr: npub1dtmp3wrkyqafghjgwyk88mxvulfncc9lg6ppv4laet5cun66jtwqqpgte6', cursor="plus")
        label4_2.pack(pady=1)
        label4_2.bind("<Button-1>", lambda e: self.copy_to_clipboard("npub1dtmp3wrkyqafghjgwyk88mxvulfncc9lg6ppv4laet5cun66jtwqqpgte6"))

        label4_3 = tk.Label(self.tab4, text='V4V: btcpay.desobedientetecnologico.com', cursor="plus")
        label4_3.pack(pady=1)
        label4_3.bind("<Button-1>", lambda e: self.copy_to_clipboard("http://btcpay.desobedientetecnologico.com/"))

        self.logo_img1 = Image.open("img/qrs.png")
        self.logo_img1 = self.logo_img1.resize((500, 200))  # Resize image
        self.logo_photo1 = ImageTk.PhotoImage(self.logo_img1)
        logo_label1 = tk.Label(self.tab4, image=self.logo_photo1)
        logo_label1.pack(pady=1)

        label4 = tk.Label(self.tab4, fg="blue", text='DTails tool - Made by DT with ♥', cursor="hand2")
        label4.pack(pady=10, side="bottom")
        label4.bind("<Button-1>", lambda e: self.callback("http://desobedientetecnologico.com"))


        self.tab_control.tab(1, state="disabled")
        self.tab_control.tab(2, state="disabled")

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
            app.tab_control.select(3)
        elif iso_work_path.endswith('.img'):
            app.tab_control.tab(2, state="normal")
            app.tab_control.select(2)

    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image .iso", "*.iso *.img")])
    
        if file_path:
            iso_path = file_path
            self.file_path.set(file_path) 
            self.tab_control.tab(1, state="normal")
            self.tab_control.select(1)
    
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
