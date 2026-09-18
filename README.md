<p align="center">
    <img alt="Dtails" src="img/dtails.png" width="200"/>
</p>

<p align="center">
  <a href="https://opensource.org/license/gpl-3-0/" title="License: GPLv3">
    <img src="https://img.shields.io/badge/License-GPLv3-red">
  </a>
  <a href="https://nostr.com/npub1dtmp3wrkyqafghjgwyk88mxvulfncc9lg6ppv4laet5cun66jtwqqpgte6" title="Nostr">
  <img src="https://img.shields.io/badge/%E2%9C%89%EF%B8%8F-Nostr-purple">
  </a>
<a href="https://t.me/DesobedientesTecnologicos" title="Telegram">
  <img src="https://img.shields.io/badge/📨-Telegram-blue">
  </a>
  <a href="https://twitter.com/DesobedienteTec" title="Twitter">
  <img src="https://img.shields.io/twitter/url?url=https%3A%2F%2Ftwitter.com%2FDesobedienteTec&label=Follow">
  </a>
  <a href="http://btcpay.desobedientetecnologico.com/" title="Bitcoin / BIP47">
  <img src="https://img.shields.io/badge/⚡️-btcpay-yellow?logo=bitcoin">
  </a>

</p>


# About

DTails tool lets you take a base Debian Live image, add or remove carefully curated tools, and build a new image you can independently verify. No hidden network or opaque calls — just explicit scripts and logs.

[DTailsOS](https://dtails.gitlab.io) is the fork of Tails.

## Packages requirements


```bash
sudo apt install rsync squashfs-tools xorriso genisoimage syslinux-utils dosfstools mtools parted gdisk build-essential python3-pyqt5 gpg docker.io
```

> ℹ️ You don't need to build the Docker image yourself: before writing the image, the GUI's Summary screen offers a **Build Docker Image** button that creates it for you if it isn't built yet.

If Docker gives you a "permission denied" error instead of building, add your user to the `docker` group rather than running DTails as root:

```bash
sudo usermod -aG docker $USER
```

Then log out and back in (or run `newgrp docker` in your current shell) for it to take effect.

## Getting started
Clone the repository with:

```bash
git clone https://github.com/DesobedienteTecnologico/dtails
```

Once you have clone the repository and you get inside the directory. Run this to start the GUI:


```bash
python3 dtails.py
```

#### 1. Select the image file
<img width="500" src="https://github.com/user-attachments/assets/84845e35-1c3f-493c-b624-816caf1b4559" />

#### 2. Select storage device
<img width="500" src="https://github.com/user-attachments/assets/3ba8a2bd-5952-4df7-b35b-915244b080f0" />

#### 3. Add or remove packages
You can also modify the version manually.

<img width="500" src="https://github.com/user-attachments/assets/caebd2bc-16b6-470a-960d-d7d7f16121f3" />

#### 4. Monitor the Live Log while remastering the image
* ℹ️ You will need to type the sudo password in your terminal
<img width="500" src="https://github.com/user-attachments/assets/37f61098-a33a-44e6-9b54-1916a75750c5" />


## Reproducibility

DTails aims for **bit-for-bit reproducible** images: the same base image + the
same software selection should produce the same output hash on any machine.

### Verifying

Build the same image twice and compare:

```bash
sha256sum DTails.img     # or DTails.iso — the two runs must produce the same hash
```

You can also check/share the file **DTails.img.manifest.txt** created after every build.

For a content-level check (file-by-file inside the live filesystem), use the
**Compare Images** dialog in the GUI, which mounts both inputs, unsquashes them
and reports any differing/missing files.

### Verifying a flashed device

The **Compare Images** dialog also accepts a **device** on either side (pick
"All files" and select the node, e.g. `/dev/sdb`). It mounts the device's FAT
partition **read-only** — so verification never alters the device — and compares
its live filesystem against the source `.iso`/`.img`. This works for both a
`dd`-flashed image and a directly-flashed device, and across USB sticks of
different sizes (it compares filesystem *content*, not raw bytes).

If you flashed with `dd` and want a raw byte check of the whole image, compare
the first *image-sized* bytes of the device against the source:

```bash
sz=$(stat -c%s DTails.img)
sudo cmp -n "$sz" DTails.img /dev/sdX && echo "device matches image"
```

## Compare two images by hashing every file in the live filesystem
<img width="500" src="https://github.com/user-attachments/assets/2038d9e7-6870-4572-8861-33ce51e4c977" />
<br><br>
<img width="600" alt="Screenshot_2025-12-03_21-08-20" src="https://github.com/user-attachments/assets/11807492-086b-4c62-8ad1-4e778802c128" />


## <a href="https://iris.to/note1v84se28tgghf78c3gn7qtflywgau9atcwva4fvgnu33mpxhq2jgs28lhuw">GPG Key</a>

Fingerprint: 86E32C4CE645DE81DD0F31E24559764E14109E7F  
64-bit: 4559 764E 1410 9E7F


