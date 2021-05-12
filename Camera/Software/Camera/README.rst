
See the host side README.rst for detailed Linux Host side instructions.


What you will need:
Linux with a recent kernel. I reccommend 5.8.0 from a debian based distro,
as this seems to be tuned to have the lowest latency. I have tested this on
an Intel NUC(R) i5-5250U, and that seems to work the best. I have an AMD
system but the on-board Intel WiFi seems to delay packets too much. I'm not
sure if it is the WiFi, or the kernel causing the added delay, which can be
pretty high. Try a different WiFi USB or card, and you may find some
combination that works.

256MB or greater SDcard, one for each camera.

Raspberry Pi Zero W, one for each camera.

Arducam Auto Focus Pi Camera, Autofocus for Raspberry Pi Camera Module, 
Motorized Focus Lens, Software Precise Manual Focus, OV5647 5MP 1080P.
https://smile.amazon.com/gp/product/B07SN8GYGD

Arducam for Raspberry Pi Zero Camera Cable Set, 
1.5" 2.87" 5.9" Ribbon Flex Extension Cables for Pi Zero&W, Pack of 3 
https://smile.amazon.com/gp/product/B085RW9K13
The 1.5" cables are perfect for the 3d printed case. I reccommend these
cables because they can take a lot of abuse and don't fall apart.


Building the images:
./compile-head && compile_calibrate

This will download everything required, even buildroot.
head == down looking camera
calibrate == up looking camera

The head camera is _required_ even if it is only used as an uplooking camera,
since it contains the radvd magic to set up the IPv6 networking. See below
for Networking details.

Either use dd or whatever sd image writer you want. The sdcard images only
need 256MB. You can use larger, however will only use 256MB. 
This is OK, since this will increase wear leveling built-in to the SDcard. :-) 
Basically, get the smallest one you can, and it doesn't have to be an 
expensive one. We don't care about the write speed. Camera should be booted 
within 30 seconds, and camera should be running within 20 seconds after that 
because python is a little bit slow to start.

Default root password is picam, you should probabbly change it.

Default password can be changed in the config file for each camera.

PNP-head_defconfig:BR2_TARGET_GENERIC_ROOT_PASSWD="picam"

PNP-calibrate_defconfig:BR2_TARGET_GENERIC_ROOT_PASSWD="picam"

Networking:
Default network SSID is "PNP_Network_1", passphrase is OpenPNP_1

To adjust these, change BOTH files: 

board/PNP-head/wpa_supplicant.conf

and

board/PNP-calibrate/wpa_supplicant.conf

On the Linux host, enable DHCP, but only for IPv4. This is because the host
will get it's IPv6 address from the head camera. 

You can use SSH to access both cameras

head camera is at fd00:f00d:dead:beef::1

calibrate camera is at fd00:f00d:dead:beef::2

ssh -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" root@fd00:f00d:dead:beef::1

ssh -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" root@fd00:f00d:dead:beef::2

Wait! There's more!! 
GPIO is controlled by pipiod, meaning that you can controll the GPIO
directly from the host PC over the WiFi without adding any additional
software on the Pi.

Python:

Host can use pigpio for Python by installing it from Pypi:

Python3:

sudo pip3 install pigpio

Python2:

sudo pip2 install pigpio

More information on this is avilable at http://abyz.me.uk/rpi/pigpio/python.html
You can install it for both Python versions.

Java:
To access from Java (plans are to integrate this into OpenPNP at some point
anyway) is at http://knutejohnson.com/pi/
