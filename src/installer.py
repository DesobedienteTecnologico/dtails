import sys
import subprocess
import os
from src.commands import *
from src.apps import *

# Variables
bisq_url = "v1.9.21/Bisq-64bit-1.9.21"
bisq_v = bisq_url.split("/")[1]
briar_v = "briar-desktop-debian-bullseye"
simplex_url = "v6.4.0/simplex-desktop-ubuntu-22_04-x86_64"
simplex_v = simplex_url.split("/")[1]
mycitadel_url = "v1.5.0/mycitadel_1.5.0-1_debian11_amd64"
mycitadel_v = mycitadel_url.split("/")[1]
rana_v = "v0.5.5"
sparrow_url = "2.2.3/sparrowwallet-2.2.3-x86_64"
sparrow_v = sparrow_url.split("/")[1]
specter_url = "v2.1.1/specter_desktop-v2.1.1-x86_64-linux-gnu"
specter_v = specter_url.split("/")[1]
specterd_url = specter_url.replace("specter_desktop","specterd")
specterd_v = specterd_url.split("/")[1]
bitcoincore_url = "bitcoin-core-29.0/bitcoin-29.0-x86_64-linux-gnu"
bitcoincore_v = bitcoincore_url.split("/")[1]
feather_v = "feather-2.8.1"
cake_v = "v5.1.2"
liana_url = "v11.1/liana-11.1-x86_64-linux-gnu"
liana_v = liana_url.split("/")[1]
############################################

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
    subprocess.run("cp dotfiles/menu/Monero.menu shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/Bitcoin.menu /etc/xdg/menus/applications-merged/")
    add_script_config("\ncp /tmp/Nostr.menu /etc/xdg/menus/applications-merged/")
    add_script_config("\ncp /tmp/Monero.menu /etc/xdg/menus/applications-merged/")


############################################


def install_sparrow():
    add_script_config("\ntar -xvf /tmp/"+ sparrow_v +".tar.gz -C /opt")
    subprocess.run("cp dotfiles/dotdesktop/sparrow.desktop shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/sparrow.desktop /usr/share/applications/")


def install_bisq():
    add_script_config("\ndpkg -i /tmp/"+ bisq_v +".deb")
    subprocess.run("cp dotfiles/scripts/setup_bisq shared_with_chroot/", shell=True)
    add_script_config("\n/tmp/./setup_bisq")

def install_briar():
    add_script_config("\ndpkg -i /tmp/"+ briar_v +".deb")

def install_simplex():
    add_script_config("\ndpkg -i /tmp/"+ simplex_v +".deb")

def install_bip39_iancoleman():
    subprocess.run("cp dotfiles/dotdesktop/bip39ian.desktop shared_with_chroot/", shell=True)
    add_script_config("\nmkdir /etc/skel/Tor\\ Browser/")
    add_script_config("\ncp /tmp/bip39ian.desktop /usr/share/applications/")
    add_script_config("\ncp /tmp/bip39-standalone.html /etc/skel/Tor\\ Browser/")

def install_seedtool():
    subprocess.run("cp dotfiles/dotdesktop/seedtool.desktop shared_with_chroot/", shell=True)
    add_script_config("\nmkdir /etc/skel/Tor\\ Browser/")
    add_script_config("\nmkdir /opt/logos/")
    subprocess.run("cp dotfiles/logos/seedtool.png shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/seedtool.png /opt/logos/")
    add_script_config("\ncp /tmp/seedtool.desktop /usr/share/applications/")
    add_script_config("\ncp /tmp/seedtool.html /etc/skel/Tor\\ Browser/")

def install_border_wallets():
    subprocess.run("cp dotfiles/dotdesktop/borderwallet.desktop shared_with_chroot/", shell=True)
    add_script_config("\nmkdir /etc/skel/Tor\\ Browser/")
    add_script_config("\nmkdir /opt/logos/")
    subprocess.run("cp dotfiles/logos/borderwallet.svg shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/borderwallet.svg /opt/logos/")
    add_script_config("\ncp /tmp/borderwallet.desktop /usr/share/applications/")
    add_script_config("\ncp /tmp/borderwallet.html /etc/skel/Tor\\ Browser/")

def install_specter_desktop():
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


def install_mycitadel_desktop():
    add_script_config("\ndpkg -i /tmp/"+ mycitadel_v +".deb")
    subprocess.run("cp dotfiles/dotdesktop/io.mycitadel.Wallet.desktop shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/io.mycitadel.Wallet.desktop /usr/share/applications/")

def install_rana_nostr_pubkeys_mining_tool():
    add_script_config("\nmkdir -p /opt/rana/")
    add_script_config("\ntar xvf /tmp/rana.tar.gz -C /opt/rana/ --strip-components=1")
    subprocess.run("cp dotfiles/dotdesktop/rana.desktop shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/rana.desktop /usr/share/applications/")
    subprocess.run("cp dotfiles/logos/rana.png shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/rana.png /opt/rana/")
    add_script_config("\nln -s /opt/rana/rana /usr/bin")

def install_bitcoincore():
    add_script_config("\nmkdir -p /opt/bitcoin/")
    add_script_config("\ncp /tmp/bitcoin256.png /opt/bitcoin/bitcoin256.png")
    add_script_config("\ntar xzf /tmp/"+ bitcoincore_v +".tar.gz -C /opt/bitcoin --strip-components=1")
    subprocess.run("cp dotfiles/dotdesktop/bitcoincore.desktop shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/bitcoincore.desktop /usr/share/applications/")

def install_feather():
    add_script_config("\nmkdir -p /opt/feather/")
    add_script_config("\ncp /tmp/feather.png /opt/feather/feather.png")
    add_script_config("\ncp /tmp/"+ feather_v +".AppImage /opt/feather/feather.AppImage")
    subprocess.run("cp dotfiles/dotdesktop/featherwallet.desktop shared_with_chroot/", shell=True)
    add_script_config("\nchmod +x /opt/feather/feather.AppImage")
    add_script_config("\ncp /tmp/featherwallet.desktop /usr/share/applications/")

def install_cake():
    add_script_config("\nmkdir -p /opt/cakewallet/")
    add_script_config("\ntar xf /tmp/cake.tar.xz -C /opt/cakewallet --strip-components=1")
    subprocess.run("cp dotfiles/dotdesktop/cakewallet.desktop shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/cakewallet.desktop /usr/share/applications/")

