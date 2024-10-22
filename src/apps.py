import sys
import subprocess
import os
from src.commands import *
from src.installer import *


################## Print color functions ##################
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
################## End Print color functions ##################

################################################
#
# If a packaged is already under shared_with_chroot it will not download the file
# Please, take attention to the file version
#
################################################
################## START functions to install packages ##################

def sparrow_wallet():
    file = sparrow_v +".tar.gz"
    if os.path.exists("shared_with_chroot/"+ file):
        print_yellow(f"{file} already created. Skipping...\n")
        install_sparrow()
    else:
        print_green("Downloading...")
        subprocess.run("wget https://github.com/sparrowwallet/sparrow/releases/download/"+ sparrow_url +".tar.gz -P shared_with_chroot", shell=True)
        install_sparrow()

def bisq():
    file = bisq_v +".deb"
    if os.path.exists("shared_with_chroot/"+ file):
        print_yellow(f"{file} already created. Skipping...\n")
        install_bisq()
    else:
        subprocess.run("wget https://bisq.network/downloads/"+ bisq_url +".deb -P shared_with_chroot", shell=True)
        install_bisq()

def briar():
    file = briar_v +".deb"
    if os.path.exists("shared_with_chroot/"+ file):
        print_yellow(f"{file} already created. Skipping...\n")
        install_briar()
    else:
        subprocess.run("wget https://desktop.briarproject.org/debs/bullseye/"+ briar_v +".deb -P shared_with_chroot", shell=True)
        install_briar()

def simplex_chat():
    file = simplex_v +".deb"
    if os.path.exists("shared_with_chroot/"+ file):
        print_yellow(f"{file} already created. Skipping...\n")
        install_bisq()
    else:
        subprocess.run("wget https://github.com/simplex-chat/simplex-chat/releases/download/"+ simplex_url +".deb -P shared_with_chroot", shell=True)
        install_simplex()

def bip39_iancoleman():
    file = "bip39-standalone.html"
    if os.path.exists("shared_with_chroot/"+ file):
        install_bip39_iancoleman()
    else:
        subprocess.run("wget https://github.com/iancoleman/bip39/releases/download/0.5.4/bip39-standalone.html -P shared_with_chroot", shell=True)
        install_bip39_iancoleman()

def seedtool():
    file = "index.html"
    if os.path.exists("shared_with_chroot/"+ file):
        install_seedtool()
    else:
        subprocess.run("wget -O shared_with_chroot/seedtool.html https://github.com/BitcoinQnA/seedtool/releases/download/2.0.2/index.html", shell=True)
        install_seedtool()

def border_wallets():
    file = "borderwallets.html"
    if os.path.exists("shared_with_chroot/"+ file):
        install_border_wallets()
    else:
        subprocess.run("wget -O shared_with_chroot/borderwallet.html https://github.com/microchad/borderwallets/releases/download/1.0.5/borderwallets.html", shell=True)
        install_border_wallets()

def whirlpool_gui():
    file = whirlpool_url +".deb"
    if os.path.exists("shared_with_chroot/"+ file):
        install_whirlpool_gui()
    else:
        print_green("Downloading...")
        subprocess.run("wget https://code.samourai.io/whirlpool/whirlpool-gui/uploads/"+ whirlpool_url +".deb -P shared_with_chroot", shell=True)        
        install_whirlpool_gui()

def specter_desktop():
    file = specter_url +".tar.gz"
    if os.path.exists("shared_with_chroot/"+ file):
        print_green("Downloading specter-desktop...")
        install_specter_desktop()
    else:
        subprocess.run("wget https://github.com/cryptoadvance/specter-desktop/releases/download/"+ specter_url +".tar.gz -P shared_with_chroot", shell=True)
        install_specter_desktop()

def mycitadel_desktop():
    file = mycitadel_url +".deb"
    if os.path.exists("shared_with_chroot/"+ file):
        install_mycitadel_desktop()
    else:
        subprocess.run("wget https://github.com/mycitadel/mycitadel-desktop/releases/download/"+ mycitadel_url +".deb -P shared_with_chroot", shell=True)
        install_mycitadel_desktop()

def rana_nostr_pubkeys_mining_tool():
    file = mycitadel_url +".deb"
    if os.path.exists("shared_with_chroot/"+ file):
        install_rana_nostr_pubkeys_mining_tool()
    else:
        subprocess.run("wget -O shared_with_chroot/rana.tar.gz https://github.com/grunch/rana/releases/download/"+ rana_v +"/rana-x86_64-unknown-linux-musl.tar.gz", shell=True)
        install_rana_nostr_pubkeys_mining_tool()


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

def mempool_space():
    subprocess.run("cp dotfiles/dotdesktop/mempool_space.desktop shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/mempool_space.desktop /usr/share/applications/")
    add_script_config("\nmkdir /opt/logos/")
    subprocess.run("cp dotfiles/logos/mempool_space.png shared_with_chroot/", shell=True)
    add_script_config("\ncp /tmp/mempool_space.png /opt/logos/")

def bitcoin_core():
    file = bitcoincore_v +".tar.gz"
    if os.path.exists("shared_with_chroot/"+ file):
        print_yellow(f"{file} already created. Skipping...\n")
        install_bitcoincore()
    else:
        print_green("Downloading...")
        subprocess.run("wget https://bitcoincore.org/bin/"+ bitcoincore_url +".tar.gz https://raw.githubusercontent.com/bitcoin/bitcoin/master/share/pixmaps/bitcoin256.png -P shared_with_chroot", shell=True)
        install_bitcoincore()

def feather_wallet():
    file = feather_v +".AppImage"
    if os.path.exists("shared_with_chroot/"+ file):
        print_yellow(f"{file} already created. Skipping...\n")
        install_feather()
    else:
        print_green("Downloading...")
        subprocess.run("wget https://featherwallet.org/files/releases/linux-appimage-a/"+ feather_v +"-a.AppImage https://featherwallet.org/img/feather.png -P shared_with_chroot", shell=True)
        install_feather()

def cake_wallet():
    file = cake_v +".tar.xz"
    if os.path.exists("shared_with_chroot/"+ file):
        print_yellow(f"{file} already created. Skipping...\n")
        install_cake()
    else:
        print_green("Downloading...")
        subprocess.run("wget -O shared_with_chroot/cake.tar.xz https://github.com/cake-tech/cake_wallet/releases/download/"+ cake_v +"/Cake_Wallet_"+ cake_v +"_Linux.tar.xz", shell=True)
        install_cake()

def liana_wallet():
    file = liana_v +".tar.gz"
    if os.path.exists("shared_with_chroot/"+ file):
        print_yellow(f"{file} already created. Skipping...\n")
        add_script_config("\ntar -xvf /tmp/"+ liana_v +".tar.gz -C /opt")
        subprocess.run("cp dotfiles/dotdesktop/liana.desktop shared_with_chroot/", shell=True)
        add_script_config("\ncp /tmp/liana.desktop /usr/share/applications/")
    else:
        print_green("Downloading...")
        subprocess.run("wget https://github.com/wizardsardine/liana/releases/download/"+ liana_url +".tar.gz -P shared_with_chroot", shell=True)
        add_script_config("\nmkdir /opt/liana/ && tar -xvf /tmp/"+ liana_v +".tar.gz -C /opt/liana/ --strip-components 1")
        subprocess.run("cp dotfiles/logos/liana.svg shared_with_chroot/", shell=True)
        add_script_config("\ncp /tmp/liana.svg /opt/liana/")
        subprocess.run("cp dotfiles/dotdesktop/liana.desktop shared_with_chroot/", shell=True)
        add_script_config("\ncp /tmp/liana.desktop /usr/share/applications/")

################## END functions to install packages ##################
################## START functions to remove packages ##################
def thunderbird():
    add_script_config("\ndpkg -r --force-depends thunderbird")

def gimp():
    add_script_config("\ndpkg -r --force-depends gimp")

################## END functions to remove packages ##################

