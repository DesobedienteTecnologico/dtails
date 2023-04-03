#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from PIL import ImageTk, Image
import os
from commands import *
import webbrowser
import tkinter.messagebox as msgbox

class MyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DTails - Image Editor")

        # Create tab views
        self.tab_control = ttk.Notebook(self)
        self.tab1 = ttk.Frame(self.tab_control)
        self.tab2 = ttk.Frame(self.tab_control)
        self.tab3 = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab1, text='Select .iso')
        self.tab_control.add(self.tab2, text='Modify and Build the .iso')
        self.tab_control.add(self.tab3, text='About')
        self.tab_control.pack(expand=1, fill='both')
        self.file_path = tk.StringVar()
        self.checkboxes = []

        # Create widgets for Tab 1
        self.logo_img = Image.open("img/dtails.png")
        self.logo_img = self.logo_img.resize((150, 150))  # Resize image
        self.logo_photo = ImageTk.PhotoImage(self.logo_img)
        logo_label = tk.Label(self.tab1, image=self.logo_photo)
        logo_label.pack(pady=10)

        text_label = tk.Label(self.tab1, text="Customize your Tails image with DTails! :)")
        text_label.pack(pady=2)

        if os.path.exists("shared_with_chroot"):
            clean_button = tk.Button(self.tab1, text="Clean old build", command=remove_directories)
            clean_button.pack()

        separator = ttk.Separator(self.tab1, orient="horizontal")
        separator.pack(fill="x", pady=20)

        select_file_button = tk.Button(self.tab1, text="Select Tails image", command=self.select_file)
        select_file_button.pack(pady=10)

        self.label = tk.Label(self.tab1, textvariable=self.file_path)
        self.label.pack()

        # Create widgets for Tab 2
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
        self.create_checkbox(left_frame, "Bisq (222MB)", "")
        self.create_checkbox(left_frame, "BIP39 iancoleman (4.34MB)", "")
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

        # Create widgets for Tab 3
        label3 = tk.Label(self.tab3, fg="blue", text='DTails tool - Made by DT with ♥', cursor="hand2")
        label3.pack(pady=10, side="bottom")
        label3.bind("<Button-1>", lambda e: self.callback("http://desobedientetecnologico.com"))

        label3_1 = tk.Label(self.tab3, text='Visit: www.DesobedienteTecnologico.com\n\nTwitter: @DesobedienteTec', cursor="center_ptr")
        label3_1.pack(pady=1)
        label3_1.bind("<Button-1>", lambda e: self.copy_to_clipboard("https://twitter.com/DesobedienteTec"))

        label3_2 = tk.Label(self.tab3, text='nostr: npub1dtmp3wrkyqafghjgwyk88mxvulfncc9lg6ppv4laet5cun66jtwqqpgte6', cursor="plus")
        label3_2.pack(pady=1)
        label3_2.bind("<Button-1>", lambda e: self.copy_to_clipboard("npub1dtmp3wrkyqafghjgwyk88mxvulfncc9lg6ppv4laet5cun66jtwqqpgte6"))

        label3_3 = tk.Label(self.tab3, text='V4V: btcpay.desobedientetecnologico.com', cursor="plus")
        label3_3.pack(pady=1)
        label3_3.bind("<Button-1>", lambda e: self.copy_to_clipboard("http://btcpay.desobedientetecnologico.com/"))

        self.logo_img1 = Image.open("img/qrs.png")
        self.logo_img1 = self.logo_img1.resize((500, 200))  # Resize image
        self.logo_photo1 = ImageTk.PhotoImage(self.logo_img1)
        logo_label1 = tk.Label(self.tab3, image=self.logo_photo1)
        logo_label1.pack(pady=1)




        self.tab_control.tab(1, state="disabled")
        #self.tab_control.tab(2, state="disabled")


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
        print(selected_options)
        for function in selected_options:
            if function == "iso_work":
                iso_work_path = self.file_path.get()
                iso_work(iso_work_path)
            elif '.' in function:
                print(function)
                function = function.replace(".", "_")
                function = eval(function)
                function()
            else:
                print(function)
                function = eval(function)
                function()
        self.tab_control.select(self.tab3)

    def select_file(self):
        #print("Selected file: ", file_path)
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


