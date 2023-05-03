<p align="center">
    <img alt="Dtails" src="img/dtails.png" width="200"/>
</p>
<h1 align="center">DTails</h1>

<p align="center">
  <a href="https://opensource.org/licenses/MIT" title="License: MIT">
    <img src="https://img.shields.io/badge/License-GPLv3-red">
  </a>
  <a href="https://twitter.com/DesobedienteTec" title="Twitter">
  <img src="https://img.shields.io/twitter/follow/DesobedienteTecnologico?style=social">
  </a>
  <a href="lnurlp:dt@getalby.com" title="Lightning">
  <img src="https://img.shields.io/badge/%E2%9A%A1-dt%40getalby.com-orange">
  </a>
  <a href="http://btcpay.desobedientetecnologico.com/" title="Bitcoin / BIP47">
  <img src="https://img.shields.io/badge/%20%F0%9F%A5%B7-btcpay.desobedientetecnologico.com-yellow?logo=bitcoin">
  </a>
  
</p>


# ℹ️ About

DTails is a tool that helps to add software in Debian based live images like Tails. DTails is not a distribution.

## 📦 Packages requirements

```bash
sudo apt-get install genisoimage parted squashfs-tools syslinux-utils build-essential python3-tk python3-pil.imagetk python3-pyudev
```

## 🛠 Getting started
Clone the repository with:

```bash
git clone https://github.com/DesobedienteTecnologico/dtails
```

Once you have clone the repository and you get inside the directory. Run this to start the GUI:


```bash
sudo ./dtails.py
```

#### Why sudo?
Sudo is needed to mount the <b>.iso / .img</b> into a directory, as well to use other software. Without it, we can't use those GNU/Linux tools.

### 1. 💿 Select the Tails image

<img alt="Dtails" src="https://user-images.githubusercontent.com/52879067/236019250-538e9353-053d-446e-ac89-c01fe824d51f.png" width="400"/>

### 2. 📥 / 📤 Add or remove packages
 1. Click on the checkboxes to add (Left) or remove (Right) the software you like.
 2. Click on "Build" once you are ready to build your image.

<img alt="Dtails" src="https://user-images.githubusercontent.com/52879067/236018996-e0e887e5-cae2-4c27-9621-2694b40b572d.png" width="400"/>

You can keep track in that is happening in your terminal.

<img alt="Dtails" src="https://user-images.githubusercontent.com/52879067/232882809-a968ec60-af05-4b01-9efd-be49760d76e2.png" width="700"/>


### 3. 💽 .iso vs .img
**❌ Persistence:** If you choose **.iso** image you will build an **DTail.iso** image in the same DTails directory.

**✅ Persistence:** In case you choose **.img**, you will be redirected to the 3º tab where you can choose the flash drive to install your modified OS into it.

<img alt="Dtails" src="https://user-images.githubusercontent.com/52879067/232884168-54e8653f-6262-41b0-9952-2845c62691bc.png" width="400"/>


Connect your flash drive and choose the right one. (Double check it once you select it!)

<img alt="Dtails" src="https://user-images.githubusercontent.com/52879067/232884954-36c62ea0-ac76-41a6-b6cc-6710ac90198b.png" width="400"/>

---
## 📦 List of software

To install  | To remove |
:----- | :----: |
Sparrow Wallet    | Thunderbird |
Bisq   | GIMP  |
BIP39 iancoleman
SeedTool
Border Wallets
Hodl Hodl and RoboSats
Mempool.space
Briar
Nostr web clients (Snort & Iris)


---

## **Video Spanish & English**

<a href="https://www.youtube.com/watch?v=QABz-GOeQ68"><img alt="Dtails" src="https://img.youtube.com/vi/QABz-GOeQ68/0.jpg" width="400"/></a>

