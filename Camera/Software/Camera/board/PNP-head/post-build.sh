#!/bin/sh

set -u
set -e

# Add a console on tty1
if [ -e ${TARGET_DIR}/etc/inittab ]; then
    grep -qE '^tty1::' ${TARGET_DIR}/etc/inittab || \
	sed -i '/GENERIC_SERIAL/a\
tty1::respawn:/sbin/getty -L  tty1 0 vt100 # HDMI console' ${TARGET_DIR}/etc/inittab
fi

cp package/busybox/S10mdev ${TARGET_DIR}/etc/init.d/S10mdev
chmod 755 ${TARGET_DIR}/etc/init.d/S10mdev
cp package/busybox/mdev.conf ${TARGET_DIR}/etc/mdev.conf

cp ${BR2_EXTERNAL_PNPCAM_PATH}/board/PNP-head/interfaces ${TARGET_DIR}/etc/network/interfaces
cp ${BR2_EXTERNAL_PNPCAM_PATH}/board/PNP-head/wpa_supplicant.conf ${TARGET_DIR}/etc/wpa_supplicant.conf
cp ${BR2_EXTERNAL_PNPCAM_PATH}/board/PNP-head/radvd.conf ${TARGET_DIR}/etc/radvd.conf
cp ${BR2_EXTERNAL_PNPCAM_PATH}/board/PNP-head/S99zzzlocal ${TARGET_DIR}/etc/init.d/S99zzzlocal
chmod 755 ${TARGET_DIR}/etc/init.d/S99zzzlocal

#
# *** TO-DO: move to the proper place, and run it.
#
cp ${BR2_EXTERNAL_PNPCAM_PATH}/board/PNP-head/stream.py ${TARGET_DIR}/sbin/stream
chmod 755 ${TARGET_DIR}/sbin/stream



if ! grep -qE 'OpenPNP' "${BINARIES_DIR}/rpi-firmware/config.txt"; then
	echo configing for OpenPNP
 	cat ${BR2_EXTERNAL_PNPCAM_PATH}/board/PNP-head/config.txt > "${BINARIES_DIR}/rpi-firmware/config.txt"
fi


