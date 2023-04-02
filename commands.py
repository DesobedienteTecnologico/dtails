import sys
import subprocess
import os

# Variables
sparrow_v = "sparrow-1.7.3-x86_64"
bisq_v = "Bisq-64bit-1.9.9"
briar_v = "briar-desktop-debian-bullseye"

# Functions to install or remove packages

def add_script_config(text):
    if os.path.exists("shared_with_chroot"):
        print("Directory already created")
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

def sparrow_wallet():
    file = sparrow_v +".tar.gz"
    if os.path.exists("shared_with_chroot/"+ sparrow_v +".tar.gz"):
        print(f"{file} already created. Skipping...\n")
        add_script_config("\ntar -xvf /tmp/"+ sparrow_v +".tar.gz -C /opt")
        subprocess.run("cp dotfiles/dotdesktop/sparrow.desktop shared_with_chroot/", shell=True)
        add_script_config("\ncp /tmp/sparrow.desktop /usr/share/applications/")
    else:
        subprocess.run("wget https://github.com/sparrowwallet/sparrow/releases/download/1.7.3/"+ sparrow_v +".tar.gz -P shared_with_chroot", shell=True)
        add_script_config("\ntar -xvf /tmp/"+ sparrow_v +".tar.gz -C /opt")
        subprocess.run("cp dotfiles/dotdesktop/sparrow.desktop shared_with_chroot/", shell=True)
        add_script_config("\ncp /tmp/sparrow.desktop /usr/share/applications/")

def bisq():
    file = bisq_v +".deb"
    if os.path.exists("shared_with_chroot/"+ bisq_v +".deb"):
        print(f"{file} already created. Skipping...\n")
        add_script_config("\ndpkg -i /tmp/"+ bisq_v +".deb")
        subprocess.run("cp dotfiles/scripts/setup_bisq shared_with_chroot/", shell=True)
        add_script_config("\n/tmp/./setup_bisq")
    else:
        subprocess.run("wget https://bisq.network/downloads/v1.9.9/Bisq-64bit-1.9.9.deb -P shared_with_chroot", shell=True)
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



def thunderbird():
    add_script_config("\ndpkg -r --force-depends thunderbird")

def gimp():
    add_script_config("\ndpkg -r --force-depends gimp")




# END Functions to install or remove packages



def chroot_script():    
    #Create a script in share_with_chroot which is going to be run when we get into chroot
    # Here I should put all the files needed to install o remove
    add_script_config("\n#!/bin/bash\n\n")   
    add_script_config("\nexport PATH=$PATH:/usr/local/sbin:/usr/sbin:/sbin\n")
    
# START Functions to unpack and pack the .iso

def iso_work(iso):
    print("\nModifying the .iso and adding the new configurations...")
    
    # Create directories needed to work on
    subprocess.run("mkdir iso_mounted future_iso", shell=True) 
    
    # Check if image is .iso or .img
    if iso.endswith('.iso'):
        # Mount the .iso and mount in iso_mounted
        subprocess.run(["sudo", "mount", "-o", "loop", iso ,"iso_mounted"])
    elif iso.endswith('.img'):
        # Mount the .img and mount in iso_mounted
        subprocess.run(["sudo", "mount", "-o", "loop,offset=1048576", iso ,"iso_mounted"])
  
    # Syncronize from iso_mounted to future_iso:
    subprocess.run("rsync --exclude=/live/filesystem.squashfs -a iso_mounted/ future_iso", shell=True)
    
    # Uncompress unsquashfs. Here is located all the system... Software, Packages...
    subprocess.run("unsquashfs iso_mounted/live/filesystem.squashfs", shell=True)
    
    # Rename the uncompress unsquashfs directory
    subprocess.run("mv squashfs-root/ system_to_edit", shell=True)
    
    # Mount from Host to Chroot to get chroot working fine
    subprocess.run("sudo mount --bind /run/ system_to_edit/run", shell=True)
    subprocess.run("sudo mount --bind /dev/ system_to_edit/dev", shell=True)

    # Mount shared_with_chroot. This will allow us to exchange data to/from chroot
    subprocess.run("sudo mount --bind shared_with_chroot system_to_edit/tmp", shell=True)
    
    # Add config into script to clean up the history after all commands have run
    add_script_config("\nrm -rf ~/.bash_history\n")
    
    # Add Exit from chroot as last command to run in chroot
    add_script_config("\nexit")

    # Get into the chroot and run the script to install or remove packages
    subprocess.run("sudo chroot system_to_edit/ /bin/bash -c 'bash /tmp/script'", shell=True)

    # Build the final image
    build_iso(iso)

    # Cleaning everything
    ending_chroot_and_cleaning_up()

def ending_chroot_and_cleaning_up():
    print("Cleaning everything...\nWait please...")
    # Umount from host to chroot
    subprocess.run("sudo umount system_to_edit/run", shell=True)
    subprocess.run("sudo umount system_to_edit/dev", shell=True)
    subprocess.run("sudo umount system_to_edit/tmp", shell=True)

    # Umount .iso
    subprocess.run("sudo umount iso_mounted", shell=True)
    print("Done!\nEnjoy! :)")

def remove_directories():
    ending_chroot_and_cleaning_up()
    subprocess.run("sudo rm -rf shared_with_chroot/ system_to_edit/ iso_mounted/ future_iso/", shell=True)
    print("Remove directories. Done!")

# END Functions to unpack and pack the .iso

# START Function to build the .iso

def build_iso(img):
    print("\n\nGetting -unrecognize xattr prefix system.posix_acl_access- message. IS NOT AN ISSUE.\nThat happen because we are running it by scripts.\nThat is kind of know bug :) \n\n")
    # Make squashfs
    subprocess.run("sudo mksquashfs system_to_edit/ filesystem.squashfs", shell=True)
    subprocess.run("mv filesystem.squashfs future_iso/live/", shell=True)
    # Build the .iso
    print("\n\nBuilding the final .iso image...\n\n")
    # Check if image is .iso or .img
    if img.endswith('.iso'):
        subprocess.run(["sudo genisoimage -r -J -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -o dtails.iso future_iso/"], shell=True)
    elif img.endswith('.img'):
        subprocess.run(["sudo genisoimage -r -J -b syslinux/isolinux.bin -c syslinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -o dtails.iso future_iso/"], shell=True)
    print("\n\Image created!")

# END Function to build the .iso
