import sys
import subprocess
import os
import re
from src.apps import *

################## START Functions to unpack and pack the final image ##################
def iso_work(iso):
    print_green("\nModifying the image and adding the new configurations...")
    
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
    subprocess.run("sudo mount --bind /proc/ system_to_edit/proc", shell=True)

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
    print_green("Cleaning everything...\nWait please...")
    # Umount from host to chroot
    subprocess.run("sudo umount system_to_edit/run", shell=True)
    subprocess.run("sudo umount system_to_edit/dev", shell=True)
    subprocess.run("sudo umount system_to_edit/tmp", shell=True)

    # Umount .iso
    subprocess.run("sudo umount iso_mounted", shell=True)
    print_green("Done!\nimage umounted.")

################## END Functions to unpack and pack the .iso ##################
################## START Function to build the .iso ##################

def build_iso(img):
    print_yellow("\n\nGetting -unrecognize xattr prefix system.posix_acl_access- message. IS NOT AN ISSUE.\nThat happen because we are running it by scripts.\nThat is kind of know bug :) \n\n")
    # Make squashfs
    subprocess.run("sudo umount system_to_edit/proc", shell=True)
    subprocess.run("sudo mksquashfs system_to_edit/ filesystem.squashfs", shell=True)
    subprocess.run("mv filesystem.squashfs future_iso/live/", shell=True)
    # Build the .iso
    print_green("\n\nBuilding the final .iso image...\n\n")
    # Check if image is .iso or .img
    if img.endswith('.iso'):
        subprocess.run(["sudo genisoimage -r -J -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -o dtails.iso future_iso/"], shell=True)
        subprocess.run(["isohybrid dtails.iso"], shell=True)
        print_yellow("dtails.iso image created")
    elif img.endswith('.img'):
        print_yellow("Please, follow the GUI instructions.")

################## END Function to build the .iso ##################



def chroot_script():    
    #Create a script in share_with_chroot which is going to be run when we get into chroot
    # Here I should put all the files needed to install o remove
    add_script_config("\n#!/bin/bash\n\n")   
    add_script_config("\nexport PATH=$PATH:/usr/local/sbin:/usr/sbin:/sbin\n")
    
def remove_directories():
    ending_chroot_and_cleaning_up()
    subprocess.run("sudo rm -rf shared_with_chroot/ system_to_edit/ iso_mounted/ future_iso/ squashfs-root/ mount_p/", shell=True)
    print_green("Removing directories. Done!")

def install_image_to_device(device):
    device = device.split(" - ")[1]
    if device != None:
        print_green("Formating device...")
        subprocess.run("sudo parted -s "+device+" mklabel gpt", shell=True)
        subprocess.run("sudo parted -s "+device+" mkpart primary fat32 0% 3GB name 1 Tails", shell=True)
        subprocess.run("sudo parted -s "+device+" set 1 boot on", shell=True)
        subprocess.run("sudo parted -s "+device+" set 1 hidden on", shell=True)
        subprocess.run("sudo parted -s "+device+" set 1 legacy_boot on", shell=True)
        subprocess.run("sudo parted -s "+device+" set 1 esp on", shell=True)
        subprocess.run("sudo mkfs.fat -F 32 -n TAILS "+device+"1", shell=True)
        print_green("Copying files to device...")
        subprocess.run("sudo mkdir mount_p ; sudo mount "+device+"1 mount_p", shell=True)
        subprocess.run("sudo cp -r future_iso/* mount_p ; sync ; sudo umount mount_p", shell=True)
        subprocess.run("", shell=True)
        print_green("Installed...\nDone!")
        print_yellow("\nNow you can safely remove the flash drive\nCheck the tab About before closing this! :)\nEnjoy! 🤙")
