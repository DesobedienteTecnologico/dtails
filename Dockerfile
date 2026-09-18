# Pinned build toolchain for reproducible DTails images.
#
# Why this exists: DTails pins the *build inputs* (SOURCE_DATE_EPOCH, GPT/FAT
# GUIDs, package selection order, pristine log/machine-id/apt state) but the
# host tools that serialize those inputs into bytes — mksquashfs (and the
# zstd library it links), mtools, dosfstools — are not guaranteed to produce
# identical output across versions, even for byte-identical input. Building
# inside this fixed image removes that variable: anyone using it gets the
# same tool versions, and therefore the same final image hash, regardless of
# their host OS.
#
# Build once:
#   docker build -t dtails-build .
#
# Run a build (from the repo root, with your base .img/.iso present):
#   docker run --rm -it --privileged -v "$PWD":/work -w /work dtails-build \
#     python3 dtails_cli.py
#
# --privileged is required for the loop-device/mount/chroot steps the build
# performs (losetup, mount --bind, chroot). The container never touches
# anything outside the bind-mounted repo directory.

FROM debian:bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
      rsync=3.2.7-1+deb12u6 \
      squashfs-tools=1:4.5.1-1 \
      xorriso=1.5.4-4 \
      genisoimage=9:1.1.11-3.4 \
      syslinux-utils=3:6.04~git20190206.bf6db5b4+dfsg1-3+b1 \
      dosfstools=4.2-1 \
      mtools=4.0.33-1+really4.0.32-1 \
      parted=3.5-3 \
      gdisk=1.0.9-2.1 \
      kpartx \
      sudo=1.9.13p3-1+deb12u4 \
      wget=1.21.3-1+deb12u1 \
      ca-certificates=20250419~deb12u1 \
      gpg \
      python3 \
    && rm -rf /var/lib/apt/lists/* \
    && echo 'root ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
