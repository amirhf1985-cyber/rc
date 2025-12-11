[app]
# اطلاعات اپلیکیشن
title = Bluetooth RC
package.name = bluetoothrc
package.domain = org.example

# فایل اصلی برنامه
source.dir = .
source.main = main.py

# فایل‌هایی که باید به APK اضافه شوند
source.include_exts = py,kv,json,ttf,atlas,wav,png,jpg,jpeg,mp3
source.include_patterns = images/*, *.png, *.jpg, *.jpeg, *.wav

# نسخه
version = 1.0
version.code = 1

# کتابخانه‌ها
requirements = python3,kivy==2.3.0,openssl,requests,pyjnius,pillow,android

# تنظیمات صفحه
orientation = landscape
fullscreen = 1

# مجوزهای اندروید
android.permissions = ACCESS_WIFI_STATE, ACCESS_NETWORK_STATE, CHANGE_WIFI_STATE, VIBRATE, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_SCAN, BLUETOOTH_CONNECT, BLUETOOTH_ADVERTISE, WAKE_LOCK

# نسخه‌های اندروید
android.api = 33
android.minapi = 21
android.ndk = 25b

icon.filename = icon.png
presplash.filename = presplash.png

# امنیت
android.allow_backup = true
android.usesCleartextTraffic = true

[buildozer]
log_level = 2