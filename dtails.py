#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, filedialog, messagebox as msgbox
from PIL import ImageTk, Image
import os
from src.commands import *
from src.apps import *
import webbrowser
import pyudev
import threading
import asyncio

class MyApp(tk.Tk):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.file_path = tk.StringVar()
        self.checkboxes = []
        self.pendrives = {}
        self.setup_ui()
        self.start_pendrive_monitoring()

    def setup_ui(self):
        """Set up the main UI components."""
        style = ttk.Style(self)
        style.theme_use("clam")
        self.title("DTails")

        # Create tab views
        self.tab_control = ttk.Notebook(self)
        self.tab1 = ttk.Frame(self.tab_control)
        self.tab2 = ttk.Frame(self.tab_control)
        self.tab3 = ttk.Frame(self.tab_control)
        self.tab4 = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab1, text='Select Image', state="normal")
        self.tab_control.add(self.tab2, text='Modify and Build Image', state="disabled")
        self.tab_control.add(self.tab3, text='Live Install', state="disabled")
        self.tab_control.add(self.tab4, text='About', state="normal")
        self.tab_control.pack(expand=1, fill='both')

        self.setup_tab1()
        self.setup_tab2()
        self.setup_tab3()
        self.setup_tab4()

    def setup_tab1(self):
        """Set up the first tab: Select Image."""
        self.logo_img = Image.open("img/dtails.png")
        self.logo_img = self.logo_img.resize((150, 150))  # Resize image
        self.logo_photo = ImageTk.PhotoImage(self.logo_img)
        self.logo_label = tk.Label(self.tab1, image=self.logo_photo)
        self.logo_label.pack(pady=10)

        self.text_label = tk.Label(self.tab1, text="Remaster your Debian-based image with DTails! :)")
        self.text_label.pack(pady=2)

        if os.path.exists("shared_with_chroot"):
            self.clean_button = tk.Button(self.tab1, text="Clean Old Build", command=remove_directories)
            self.clean_button.pack()

        self.separator = ttk.Separator(self.tab1, orient="horizontal")
        self.separator.pack(fill="x", pady=20)

        self.select_file_button = tk.Button(self.tab1, text="Select Image", command=self.select_file)
        self.select_file_button.pack(pady=10)

        self.label = tk.Label(self.tab1, textvariable=self.file_path)
        self.label.pack()

    def setup_tab2(self):
        """Set up the second tab: Modify and Build Image."""
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

        # Left Frame
        self.left_frame = tk.Frame(self.middle_frame, cursor="plus")
        self.left_frame.pack(side="left", padx=20, fill="both", expand=True)

        self.left_text = tk.Label(self.left_frame, text="Add Software", font="bold")
        self.left_text.pack(pady=5)

        self.add_software_checkboxes()

        # Separator between Left and Right Frames
        self.middle_separator = ttk.Separator(self.middle_frame, orient="vertical")
        self.middle_separator.pack(side="left", fill="y", padx=10)

        # Right Frame
        self.right_frame = tk.Frame(self.middle_frame, cursor="X_cursor")
        self.right_frame.pack(side="right", padx=20, fill="both", expand=True)

        self.right_text = tk.Label(self.right_frame, text="Remove Software", font="bold")
        self.right_text.pack(pady=5)

        self.add_remove_software_checkboxes()

        # Separator between Middle Frame and Bottom Frame
        self.bottom_separator = ttk.Separator(self.tab2, orient="horizontal")
        self.bottom_separator.pack(fill="x", pady=10)

        # Bottom Frame
        self.bottom_frame = tk.Frame(self.tab2)
        self.bottom_frame.pack(side="bottom", pady=10)

        self.next_button2 = tk.Button(self.bottom_frame, text="Build", command=self.get_selected_options)
        self.next_button2.pack()

    def add_software_checkboxes(self):
        """Add checkboxes for software to be installed."""
        software_list = [
            "Sparrow Wallet (106MB)", "Liana Wallet (13.8MB)", "Bisq (222MB)",
            "BIP39 iancoleman (4.34MB)", "SeedTool (6.58MB)", "Border Wallets (1.59MB)",
            "Whirlpool GUI (327MB)", "Specter Desktop (197MB)", "MyCitadel Desktop (4.41MB)",
            "Hodl Hodl and RoboSats (~1MB)", "Mempool.space (~1MB)", "Briar (221MB)",
            "SimpleX Chat (249MB)", "Rana Nostr pubkeys mining tool (1.46MB)",
            "Nostr web clients (~1MB)", "Bitcoin Core (45MB)", "Feather Wallet (22MB)",
            "Cake Wallet (77.9MB)"
        ]
        for software in software_list:
            self.create_checkbox(self.left_frame, software, "")

    def add_remove_software_checkboxes(self):
        """Add checkboxes for software to be removed."""
        software_list = [
            "Thunderbird (219MB)", "GIMP (90MB)"
        ]
        for software in software_list:
            self.create_checkbox(self.right_frame, software, "")

    def setup_tab3(self):
        """Set up the third tab: Live Install."""
        self.disconnect_button = tk.Label(self.tab3, text="\nChoose the device name from the list.\nDrive will appear at the right. Please, double check it before continuing")
        self.disconnect_button.pack()

        self.separator_tab3 = ttk.Separator(self.tab3, orient="horizontal")
        self.separator_tab3.pack(fill="x", pady=40)

        self.pendrive_var = tk.StringVar(self.tab3)
        self.pendrive_dropdown = tk.OptionMenu(self.tab3, self.pendrive_var, "No Pendrives Found")
        self.pendrive_dropdown.pack()

        self.image_label = tk.Label(self.tab3, text="Please connect a pendrive")
        self.image_label.pack()

        self.connect_button = tk.Button(self.tab3, text="Install to Device", state=tk.DISABLED, command=lambda: self.install_image_to_device(self.pendrive_var.get()))
        self.connect_button.pack()

    def setup_tab4(self):
        """Set up the fourth tab: About."""
        self.label2_1 = tk.Label(self.tab4, text='DTails is a tool to remaster live Debian based images.\n\nTwitter (maintainer): @BangalaXMR', cursor="center_ptr")
        self.label2_1.pack(pady=1)
        self.label2_1.bind("<Button-1>", lambda e: self.copy_to_clipboard("https://x.com/BangalaXMR"))

        self.label2 = tk.Label(self.tab4, fg="blue", text='DTails tool - Made by DT and maintained by BangalaXMR with ♥', cursor="hand2")
        self.label2.pack(pady=10, side="bottom")
        self.label2.bind("<Button-1>", lambda e: self.callback("https://github.com/BangalaXMR/dtails"))

    def start_pendrive_monitoring(self):
        """Start monitoring for pendrive connections."""
        self.after(0, self.run_pendrive_monitoring)

    def run_pendrive_monitoring(self):
        """Run the pendrive monitoring in the event loop."""
        asyncio.run_coroutine_threadsafe(self.update_pendrives(), self.loop)

    async def update_pendrives(self):
        """Update the list of connected pendrives."""
        while True:
            context = pyudev.Context()
            devices = context.list_devices(subsystem='block', ID_BUS='usb')
            pendrives = {}
            for device in devices:
                if not device.get('ID_VENDOR'):
                    print_yellow("No USB Manufacturer found on internal database... Using idVendor instead.")
                    pendrives[device.get('ID_VENDOR_ID')] = device.device_node[:-1]
                else:
                    pendrives[device.get('ID_VENDOR')] = device.device_node[:-1]

            self.after(0, self.update_pendrive_ui, pendrives)
            await asyncio.sleep(1)  # Sleep for 1 second

    def update_pendrive_ui(self, pendrives):
        """Update the UI based on the connected pendrives."""
        if pendrives:
            if self.pendrive_var.get() == "":
                self.pendrive_var.set("Select Device")
            self.pendrive_dropdown['menu'].delete(0, 'end')
            for pendrive, route in pendrives.items():
                self.pendrive_dropdown['menu'].add_command(label=pendrive, command=tk._setit(self.pendrive_var, pendrive + " - " + route))
            self.image_label.config(text="Pendrive Connected", fg="green")
            self.connect_button.config(state=tk.NORMAL)
        else:
            self.pendrive_var.set("No Pendrives Found")
            self.pendrive_dropdown['menu'].delete(0, 'end')
            self.pendrive_dropdown['menu'].add_command(label="No Pendrives Found")
            self.image_label.config(text="Please Connect a Pendrive", fg="black")
            self.connect_button.config(state=tk.DISABLED)
        self.pendrives = pendrives

    def create_checkbox(self, side, text, x_cursor):
        """Create a checkbox with the given text and cursor."""
        checkbox_var = tk.IntVar()
        checkbox = tk.Checkbutton(side, text=text, variable=checkbox_var, cursor=x_cursor)
        checkbox.pack(pady=5, anchor="w")
        self.checkboxes.append((text, checkbox_var))

    def get_selected_options(self):
        """Get the selected options from the checkboxes."""
        selected_options = ["chroot_script", "add_menu"]
        for text, var in self.checkboxes:
            if var.get() == 1:
                selected_options.append(text.rsplit(' ', 1)[0].replace(" ", "_").lower())
        selected_options.append("iso_work")
        print_green(f"Starting...\n")
        asyncio.run_coroutine_threadsafe(self.execute_selected_options(selected_options), self.loop)

    async def execute_selected_options(self, selected_options):
        """Execute the selected options."""
        for function in selected_options:
            if function == "iso_work":
                iso_work_path = self.file_path.get()
                await asyncio.to_thread(iso_work, iso_work_path)
            elif '.' in function:
                function = function.replace(".", "_")
                await asyncio.to_thread(eval(function))
            else:
                await asyncio.to_thread(eval(function))
        self.after(0, self.update_ui_after_build, iso_work_path)

    def update_ui_after_build(self, iso_work_path):
        """Update the UI after the build process."""
        if iso_work_path.endswith('.iso'):
            self.tab_control.select(3)
        elif iso_work_path.endswith('.img'):
            self.tab_control.tab(2, state="normal")
            self.tab_control.select(2)

    def select_file(self):
        """Open a file dialog to select an image file."""
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.iso *.img")])
        if file_path:
            self.file_path.set(file_path)
            self.tab_control.tab(1, state="normal")
            self.after(100, lambda: self.tab_control.select(1))

    def copy_to_clipboard(self, texto):
        """Copy the given text to the clipboard."""
        self.clipboard_clear()
        self.clipboard_append(texto)
        msgbox.showinfo("Copied", "Copied to clipboard")

    def callback(self, url):
        """Open the given URL in a web browser."""
        webbrowser.open_new(url)

    async def install_image_to_device(self, device):
        """Install the image to the selected device."""
        await asyncio.to_thread(install_image_to_device, device)

def run_tk_app(loop):
    app = MyApp(loop)
    app.mainloop()

async def main():
    # Create the asyncio event loop
    loop = asyncio.get_running_loop()

    # Run the Tkinter app in a separate thread
    tk_thread = threading.Thread(target=run_tk_app, args=(loop,), daemon=True)
    tk_thread.start()

    # Run the asyncio event loop
    while tk_thread.is_alive():
        await asyncio.sleep(0.1)

if __name__ == '__main__':
    asyncio.run(main())
