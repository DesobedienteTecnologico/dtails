import sys
import subprocess
import os
from src.commands import *

# Variables
sparrow_url = "1.7.6/sparrow-1.7.6-x86_64"
sparrow_v = sparrow_url.split("/")[1]
bisq_url = "v1.9.9/Bisq-64bit-1.9.9"
bisq_v = bisq_url.split("/")[1]
briar_v = "briar-desktop-debian-bullseye"

################## Print functions ##################
def print_green(text):
    color_start = "\033[0;32m"
    color_end = "\033[00m"
    print(color_start, text, color_end)

def print_red(text):
    color_start = "\033[0;31m"
    color_end = "\033[00m"
    print(color_start, text, color_end)

def print_yellow(text):
    color_start = "\033[0;93m"
    color_end = "\033[00m"
    print(color_start, text, color_end)
################## End Print functions ##################


################## Functions to install or remove packages ##################

def add_script_config(text):
    if os.path.exists("shared_with_chroot"):
        pass
    else:
        subprocess.run("mkdir shared_with_chroot", shell=True)
    
    config_script_file = open("shared_with_chroot/script", "a")
    config_script_file.write(text)
    config_script_file.close()


def add_menu():
    subprocess.run("cp dotfiles/menu/Bitcoin.menu shared_with_chroot/", shell=True)
    subprocess.run("cp dotfiles/menu/Nostr.menu shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/Bitcoin.menu /etc/xdg/menus/applications-merged/")
    add_script_config("\ncp /tmp/Nostr.menu /etc/xdg/menus/applications-merged/")

################## Install packages ##################
def sparrow_wallet():
    file = sparrow_v +".tar.gz"
    if os.path.exists("shared_with_chroot/"+ sparrow_v +".tar.gz"):
        print_yellow(f"{file} already created. Skipping...\n")
        add_script_config("\ntar -xvf /tmp/"+ sparrow_v +".tar.gz -C /opt")
        subprocess.run("cp dotfiles/dotdesktop/sparrow.desktop shared_with_chroot/", shell=True)
        add_script_config("\ncp /tmp/sparrow.desktop /usr/share/applications/")
    else:
        print_green("Downloading...")
        subprocess.run("wget https://github.com/sparrowwallet/sparrow/releases/download/"+ sparrow_url +".tar.gz -P shared_with_chroot", shell=True)
        add_script_config("\ntar -xvf /tmp/"+ sparrow_v +".tar.gz -C /opt")
        subprocess.run("cp dotfiles/dotdesktop/sparrow.desktop shared_with_chroot/", shell=True)
        add_script_config("\ncp /tmp/sparrow.desktop /usr/share/applications/")

def bisq():
    file = bisq_v +".deb"
    if os.path.exists("shared_with_chroot/"+ bisq_v +".deb"):
        print_yellow(f"{file} already created. Skipping...\n")
        add_script_config("\ndpkg -i /tmp/"+ bisq_v +".deb")
        subprocess.run("cp dotfiles/scripts/setup_bisq shared_with_chroot/", shell=True)
        add_script_config("\n/tmp/./setup_bisq")
    else:
        subprocess.run("wget https://bisq.network/downloads/"+ bisq_url +".deb -P shared_with_chroot", shell=True)
        add_script_config("\ndpkg -i /tmp/"+ bisq_v +".deb")
        subprocess.run("cp dotfiles/scripts/setup_bisq shared_with_chroot/", shell=True)
        add_script_config("\n/tmp/./setup_bisq")

def briar():
    subprocess.run("wget https://desktop.briarproject.org/debs/bullseye/"+ briar_v +".deb -P shared_with_chroot", shell=True)
    add_script_config("\ndpkg -i /tmp/"+ briar_v +".deb")

def nostr_web_clients():
    subprocess.run("cp dotfiles/dotdesktop/snort.desktop shared_with_chroot/", shell=True)
    subprocess.run("cp dotfiles/dotdesktop/iris_to.desktop shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/snort.desktop /usr/share/applications/")
    add_script_config("\ncp /tmp/iris_to.desktop /usr/share/applications/")
    add_script_config("\nmkdir /opt/logos/")
    subprocess.run("cp dotfiles/logos/snort.png shared_with_chroot/", shell=True)
    subprocess.run("cp dotfiles/logos/iris_to.png shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/snort.png /opt/logos/")
    add_script_config("\ncp /tmp/iris_to.png /opt/logos/")

def bip39_iancoleman():
    subprocess.run("wget https://github.com/iancoleman/bip39/releases/download/0.5.4/bip39-standalone.html -P shared_with_chroot", shell=True)
    subprocess.run("cp dotfiles/dotdesktop/bip39ian.desktop shared_with_chroot/", shell=True)
    add_script_config("\nmkdir /etc/skel/Tor\ Browser/")
    add_script_config("\ncp /tmp/bip39ian.desktop /usr/share/applications/")
    add_script_config("\ncp /tmp/bip39-standalone.html /etc/skel/Tor\ Browser/")

def hodl_hodl_and_robosats():
    subprocess.run("cp dotfiles/dotdesktop/robosats.desktop shared_with_chroot/", shell=True)
    subprocess.run("cp dotfiles/dotdesktop/hodlhodl.desktop shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/robosats.desktop /usr/share/applications/")
    add_script_config("\ncp /tmp/hodlhodl.desktop /usr/share/applications/")
    add_script_config("\nmkdir /opt/logos/")
    subprocess.run("cp dotfiles/logos/robosats.png shared_with_chroot/", shell=True)
    subprocess.run("cp dotfiles/logos/hodlhodl.png shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/robosats.png /opt/logos/")
    add_script_config("\ncp /tmp/hodlhodl.png /opt/logos/")

def mempool_space():
    subprocess.run("cp dotfiles/dotdesktop/mempool_space.desktop shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/mempool_space.desktop /usr/share/applications/")
    add_script_config("\nmkdir /opt/logos/")
    subprocess.run("cp dotfiles/logos/mempool_space.png shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/mempool_space.png /opt/logos/")

################## Remove packages ##################
def thunderbird():
    add_script_config("\ndpkg -r --force-depends thunderbird")

def gimp():
    add_script_config("\ndpkg -r --force-depends gimp")

################## END Functions to install or remove packages ##################

