import sys
import subprocess
import os
from src.commands import *

# Variables
sparrow_url = "1.7.6/sparrow-1.7.6-x86_64"
sparrow_v = sparrow_url.split("/")[1]
bisq_url = "v1.9.10/Bisq-64bit-1.9.10"
bisq_v = bisq_url.split("/")[1]
briar_v = "briar-desktop-debian-bullseye"
whirlpool_url = "fda2da816431c25598f532486ac0da09/whirlpool-gui_0.10.3_amd64"
whirlpool_v = whirlpool_url.split("/")[1]
specter_url = "v2.0.1/specter_desktop-v2.0.1-x86_64-linux-gnu"
specter_v = specter_url.split("/")[1]
specterd_url = specter_url.replace("specter_desktop","specterd")
specterd_v = specterd_url.split("/")[1]

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

def seedtool():
    subprocess.run("wget -O shared_with_chroot/seedtool.html https://github.com/BitcoinQnA/seedtool/releases/download/2.0.2/index.html", shell=True)
    subprocess.run("cp dotfiles/dotdesktop/seedtool.desktop shared_with_chroot/", shell=True)
    add_script_config("\nmkdir /etc/skel/Tor\ Browser/")
    add_script_config("\nmkdir /opt/logos/")
    subprocess.run("cp dotfiles/logos/seedtool.png shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/seedtool.png /opt/logos/")
    add_script_config("\ncp /tmp/seedtool.desktop /usr/share/applications/")
    add_script_config("\ncp /tmp/seedtool.html /etc/skel/Tor\ Browser/")

def border_wallets():
    subprocess.run("wget -O shared_with_chroot/borderwallet.html https://github.com/microchad/borderwallets/releases/download/1.0.5/borderwallets.html", shell=True)
    subprocess.run("cp dotfiles/dotdesktop/borderwallet.desktop shared_with_chroot/", shell=True)
    add_script_config("\nmkdir /etc/skel/Tor\ Browser/")
    add_script_config("\nmkdir /opt/logos/")
    subprocess.run("cp dotfiles/logos/borderwallet.svg shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/borderwallet.svg /opt/logos/")
    add_script_config("\ncp /tmp/borderwallet.desktop /usr/share/applications/")
    add_script_config("\ncp /tmp/borderwallet.html /etc/skel/Tor\ Browser/")

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

def whirlpool_gui():
    print_green("Downloading...")
    subprocess.run("wget https://code.samourai.io/whirlpool/whirlpool-gui/uploads/"+ whirlpool_url +".deb -P shared_with_chroot", shell=True)
    print_yellow("Chroot connecting to the internet to download openjdk...")
    subprocess.run("chmod 777 shared_with_chroot", shell=True)
    add_script_config("\necho 'nameserver 1.1.1.1' > /etc/resolv.conf")
    add_script_config("\necho 'deb http://security.debian.org/debian-security bullseye-security main' >> /etc/apt/sources.list")
    add_script_config("\necho 'deb http://ftp.de.debian.org/debian bullseye main' >> /etc/apt/sources.list")
    add_script_config("\nsed -i 's/^/#/' /etc/apt/apt.conf.d/80tails-additional-software")
    add_script_config("\nsed -i 's/^/#/' /etc/apt/apt.conf.d/70debconf")
    add_script_config("\napt update ; apt install -y openjdk-17-jdk")
    add_script_config("\ndpkg -i /tmp/"+ whirlpool_v +".deb")
    subprocess.run("cp dotfiles/dotconf/ferm.conf shared_with_chroot/", shell=True)
    subprocess.run("cp dotfiles/dotconf/9000-hosts-file-samourai shared_with_chroot/9000-hosts-file", shell=True)
    add_script_config("\nmv /tmp/9000-hosts-file /lib/live/config/")
    add_script_config("\nmv /tmp/ferm.conf /etc/ferm/ferm.conf")

    # Tails config files as default
    add_script_config("\necho "" > /etc/resolv.conf")
    add_script_config("\nsed -i 's/^#//' /etc/apt/apt.conf.d/80tails-additional-software")
    add_script_config("\nsed -i 's/^#//' /etc/apt/apt.conf.d/70debconf")
    add_script_config("\nhead -n -2 /etc/apt/sources.list > /etc/apt/sources.list")

    # Cleaning logs and unnecessary Java certificates
    add_script_config("\nrm -rf /var/log/apt/term.log /var/log/alternatives.log /var/cache/man/* /var/cache/apt/pkgcache.bin /etc/ssl/certs/java")
    add_script_config("\necho '' | tee /var/log/dpkg.log | tee /var/log/apt/history.log")

def specter_desktop():
    print_green("Downloading specter-desktop...")
    subprocess.run("wget https://github.com/cryptoadvance/specter-desktop/releases/download/"+ specter_url +".tar.gz -P shared_with_chroot", shell=True)
    #subprocess.run("sudo tar -zxvf shared_with_chroot/"+ specter_v +".tar.gz Specter-*.AppImage -C shared_with_chroot/", shell=True)
    add_script_config("\ncd /tmp/ ; tar -zxvf "+ specter_v +".tar.gz --wildcards *.AppImage")
    add_script_config("\nmkdir /opt/specter/")
    subprocess.run("wget -O shared_with_chroot/specter_logo.png https://raw.githubusercontent.com/cryptoadvance/specter-desktop/72fed92dd5d00e3164adcc97decf5ae03328538a/src/cryptoadvance/specter/static/img/v1-icons/icon.png", shell=True)
    add_script_config("\ncp /tmp/specter_logo.png /opt/specter/logo.png")
    add_script_config("\ncp /tmp/Specter-*.AppImage /opt/specter/Specter.AppImage")
    add_script_config("\ncp /tmp/udev/*.rules /etc/udev/rules.d/")
    print_green("Downloading specterd...")
    subprocess.run("wget https://github.com/cryptoadvance/specter-desktop/releases/download/"+ specterd_url +".zip -P shared_with_chroot", shell=True)
    add_script_config("\nmkdir -p /etc/skel/.specter/specterd-binaries/")
    subprocess.run("sudo unzip shared_with_chroot/"+ specterd_v +".zip -d shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/specterd /etc/skel/.specter/specterd-binaries/")
    add_script_config("\nmkdir /etc/skel/.fonts/")
    subprocess.run("wget -O shared_with_chroot/NotoColorEmoji.ttf https://raw.githubusercontent.com/googlefonts/noto-emoji/main/fonts/NotoColorEmoji.ttf", shell=True)
    add_script_config("\ncp /tmp/NotoColorEmoji.ttf /etc/skel/.fonts/NotoColorEmoji.ttf")
    subprocess.run("cp dotfiles/dotconf/ferm_specter.conf shared_with_chroot/", shell=True)
    add_script_config("\nmv /tmp/ferm_specter.conf /etc/ferm/ferm.conf")
    subprocess.run("cp dotfiles/dotdesktop/specter.desktop shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/specter.desktop /usr/share/applications/")
################## Remove packages ##################
def thunderbird():
    add_script_config("\ndpkg -r --force-depends thunderbird")

def gimp():
    add_script_config("\ndpkg -r --force-depends gimp")

################## END Functions to install or remove packages ##################

