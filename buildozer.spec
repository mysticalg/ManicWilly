[app]
title = ManicWilly
package.name = manicwilly
package.domain = org.manicwilly
source.dir = .
source.include_exts = py,png,jpg,jpeg,json,txt
version = 0.1.0
requirements = python3,pygame
orientation = landscape
fullscreen = 1

[buildozer]
log_level = 2
warn_on_root = 1

[android]
android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
android.permissions =
android.archs = arm64-v8a, armeabi-v7a
