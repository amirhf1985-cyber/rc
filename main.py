from kivy.resources import resource_add_path, resource_find
from kivy.logger import Logger
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, ListProperty, BooleanProperty
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Rotate, PushMatrix, PopMatrix
from kivy.core.window import Window
from kivy.config import Config
from kivy.storage.jsonstore import JsonStore
from kivy.logger import Logger
from kivy.core.audio import SoundLoader
import os
import threading
import time
import math
import random
import socket
import json
import sys
import traceback
import subprocess
import ipaddress
from datetime import datetime
import re

class AssetsManager:
    def __init__(self, assets_dir='assets'):
        self.assets_dir = assets_dir
        self._setup_resources()
        self.files = {}

    def _setup_resources(self):
        try:
            base_path = os.path.dirname(os.path.abspath(__file__))
            assets_path = os.path.join(base_path, self.assets_dir)
            resource_add_path(assets_path)
            Logger.info(f"Added assets path: {assets_path}")
        except Exception as e:
            Logger.error(f"Error adding assets path: {e}")

    def get(self, filename):
        if filename in self.files:
            return self.files[filename]

        path = resource_find(filename)
        if path:
            Logger.info(f"Asset found: {filename} -> {path}")
            self.files[filename] = path
            return path

        Logger.warning(f"Asset NOT FOUND: {filename}")
        return None

    def list_available_assets(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        assets_path = os.path.join(base_path, self.assets_dir)

        if not os.path.isdir(assets_path):
            return []

        return [
            f for f in os.listdir(assets_path)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.wav', '.mp3'))
        ]

assets = AssetsManager()

Config.set('graphics', 'resizable', '0')
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '600')
Config.set('graphics', 'fullscreen', 'auto')
Config.set('graphics', 'borderless', '1')
Window.clearcolor = (1, 1, 1, 1)

HAS_ANDROID = False
try:
    from jnius import autoclass, cast, PythonJavaClass, java_method
    from android.permissions import request_permissions, Permission, check_permission
    HAS_ANDROID = True
except Exception as e:
    HAS_ANDROID = False
    print(f"Android components not available: {e}")

def setup_display():
    try:
        Window.fullscreen = 'auto'
        Window.borderless = True
        
        if HAS_ANDROID:
            try:
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                ActivityInfo = autoclass('android.content.pm.ActivityInfo')
                PythonActivity.mActivity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE)
                print("Forced landscape orientation")
            except Exception as e:
                print(f"Orientation error: {e}")
        
        print(f"Window configured: {Window.width}x{Window.height}")
        
    except Exception as e:
        print(f"Display setup error: {e}")

setup_display()

def get_required_permissions():
    permissions = [
        Permission.ACCESS_WIFI_STATE,
        Permission.ACCESS_NETWORK_STATE,
        Permission.CHANGE_WIFI_STATE,
        Permission.VIBRATE,
        Permission.ACCESS_FINE_LOCATION,
        Permission.ACCESS_COARSE_LOCATION,
        Permission.BLUETOOTH,
        Permission.BLUETOOTH_ADMIN,
    ]
    
    if HAS_ANDROID:
        try:
            from jnius import autoclass
            Build_VERSION = autoclass('android.os.Build$VERSION')
            if Build_VERSION.SDK_INT >= 31:
                permissions.extend([
                    Permission.BLUETOOTH_SCAN,
                    Permission.BLUETOOTH_CONNECT,
                    Permission.BLUETOOTH_ADVERTISE,
                ])
                print("Added Android 12+ BLE permissions")
        except Exception as e:
            print(f"Error checking Android version: {e}")
            
    return permissions

if HAS_ANDROID:
    def request_android_permissions():
        try:
            from android.permissions import request_permissions, Permission
            
            required_permissions = get_required_permissions()
            
            print(f"Requesting {len(required_permissions)} permissions...")
            for perm in required_permissions:
                print(f"  {perm}")
            
            try:
                request_permissions(required_permissions)
                print("Android permissions requested (simple method)")
            except Exception as simple_error:
                print(f"Simple permission request failed: {simple_error}")
                try:
                    request_permissions(required_permissions, lambda p, r: None)
                    print("Android permissions requested (fallback with empty callback)")
                except Exception as fallback_error:
                    print(f"Fallback permission request also failed: {fallback_error}")
            
        except Exception as e:
            print(f"Permission request error: {e}")

    Clock.schedule_once(lambda dt: request_android_permissions(), 5.0)

def check_vibration_permission():
    if not HAS_ANDROID:
        return True
        
    try:
        from android.permissions import check_permission, Permission
        return check_permission(Permission.VIBRATE)
    except Exception as e:
        print(f"Permission check error: {e}")
        return False

class SettingsManager:
    def __init__(self):
        self.store = JsonStore('rc_car_settings.json')
    
    def get(self, key, default=None):
        try:
            if self.store.exists(key):
                return self.store.get(key).get('value', default)
            return default
        except Exception as e:
            print(f"Settings read error for {key}: {e}")
            return default
    
    def set(self, key, value):
        try:
            self.store.put(key, value=value)
        except Exception as e:
            print(f"Settings write error for {key}: {e}")
    
    def get_all_settings(self):
        settings = {}
        try:
            for key in self.store.keys():
                settings[key] = self.get(key)
        except Exception as e:
            print(f"Error getting all settings: {e}")
        return settings
    
    def reset_to_defaults(self):
        default_settings = {
            'sensitivity': 1.0,
            'accelerometer_mode': False,
            'steering_sensitivity': 1.0,
            'battery_warning_level': 30,
            'last_connected_device': '',
            'connection_type': 'ble',
            'classic_device_address': '',
            'classic_device_port': '1',
            'wifi_ip': '192.168.4.1',
            'wifi_port': '80',
            'target_device_ip': '192.168.4.1',
            'target_device_port': '80',
            'button_vibration_intensity': 0.5,
            'steering_vibration_intensity': 0.5,
            'vibration_enabled': True,
            'pedal_min_vibration': 0.1,
            'pedal_max_vibration': 1.0,
        }
        
        try:
            for key, value in default_settings.items():
                self.set(key, value)
            
            print("All settings reset to default")
            return default_settings
        except Exception as e:
            print(f"Error resetting settings to default: {e}")
            return {}
    
    def add_saved_wifi_connection(self, ip, port, connection_name=""):
        try:
            saved_connections = self.get('saved_wifi_connections', [])
            
            new_connection = {
                "ip": ip,
                "port": int(port),
                "name": connection_name or f"RC_Car_{ip}",
                "timestamp": time.time(),
                "last_used": time.time()
            }
            
            saved_connections = [conn for conn in saved_connections 
                               if not (conn["ip"] == ip and conn["port"] == int(port))]
            
            saved_connections.insert(0, new_connection)
            
            if len(saved_connections) > 10:
                saved_connections = saved_connections[:10]
            
            self.store.put('saved_wifi_connections', value=saved_connections)
            print(f"WiFi connection saved: {ip}:{port}")
            
        except Exception as e:
            print(f"Error saving WiFi connection: {e}")
    
    def get_saved_wifi_connections(self):
        try:
            connections = self.get('saved_wifi_connections', [])
            connections.sort(key=lambda x: x.get('last_used', 0), reverse=True)
            return connections
        except Exception as e:
            print(f"Error getting saved WiFi connections: {e}")
            return []
    
    def update_connection_usage(self, ip, port):
        try:
            connections = self.get('saved_wifi_connections', [])
            for conn in connections:
                if conn["ip"] == ip and conn["port"] == int(port):
                    conn["last_used"] = time.time()
                    break
            
            self.store.put('saved_wifi_connections', value=connections)
        except Exception as e:
            print(f"Error updating connection usage: {e}")
    
    def clear_wifi_history(self):
        try:
            self.store.put('saved_wifi_connections', value=[])
            print("WiFi history cleared")
        except Exception as e:
            print(f"Error clearing WiFi history: {e}")
    
    def remove_wifi_connection(self, ip, port):
        try:
            connections = self.get('saved_wifi_connections', [])
            connections = [conn for conn in connections 
                          if not (conn["ip"] == ip and conn["port"] == int(port))]
            self.store.put('saved_wifi_connections', value=connections)
            print(f"Removed WiFi connection: {ip}:{port}")
        except Exception as e:
            print(f"Error removing WiFi connection: {e}")

def get_setting(key, default=None):
    try:
        app = App.get_running_app()
        if hasattr(app, 'settings_manager'):
            return app.settings_manager.get(key, default)
        return default
    except Exception as e:
        print(f"Error in get_setting for {key}: {e}")
        return default

def set_setting(key, value):
    try:
        app = App.get_running_app()
        if hasattr(app, 'settings_manager'):
            app.settings_manager.set(key, value)
    except Exception as e:
        print(f"Error in set_setting for {key}: {e}")

class VibrationManager:
    def __init__(self):
        self.enabled = bool(get_setting("vibration_enabled", False))
        self.button_intensity = float(get_setting("button_vibration_intensity", 0.5))
        self.steering_intensity = float(get_setting("steering_vibration_intensity", 0.5))
        self.pedal_min = float(get_setting("pedal_min_vibration", 0.1))
        self.pedal_max = float(get_setting("pedal_max_vibration", 1.0))

        self._vibrator = None
        self.has_vibrator = False
        
        if HAS_ANDROID:
            self.initialize_vibrator()

    def initialize_vibrator(self):
        try:
            Context = autoclass("android.content.Context")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            self._vibrator = cast("android.os.Vibrator", activity.getSystemService(Context.VIBRATOR_SERVICE))
            
            if self._vibrator:
                if hasattr(self._vibrator, 'hasVibrator'):
                    self.has_vibrator = self._vibrator.hasVibrator()
                else:
                    self.has_vibrator = True
                    
                print(f"Vibrator available: {self.has_vibrator}")
            else:
                self.has_vibrator = False
                print("Vibrator service not available")
                
        except Exception as e:
            print(f"Vibrator init error: {e}")
            self.has_vibrator = False

    def set_button_intensity(self, value):
        try:
            v = float(value)
            self.button_intensity = max(0.0, min(1.0, v))
            set_setting("button_vibration_intensity", self.button_intensity)
        except Exception as e:
            Logger.error(f"VibrationManager.set_button_intensity error: {e}")

    def set_steering_intensity(self, value):
        try:
            v = float(value)
            self.steering_intensity = max(0.0, min(1.0, v))
            set_setting("steering_vibration_intensity", self.steering_intensity)
        except Exception as e:
            Logger.error(f"VibrationManager.set_steering_intensity error: {e}")

    def set_pedal_vibration_range(self, min_v, max_v):
        try:
            self.pedal_min = float(min_v)
            self.pedal_max = float(max_v)
            set_setting("pedal_min_vibration", self.pedal_min)
            set_setting("pedal_max_vibration", self.pedal_max)
        except Exception as e:
            Logger.error(f"VibrationManager.set_pedal_range error: {e}")

    def vibrate_duration(self, ms=50, intensity=None):
        if not self.enabled:
            return
            
        try:
            if not self.has_vibrator:
                return
                
            if HAS_ANDROID:
                from android.permissions import check_permission, Permission
                if not check_permission(Permission.VIBRATE):
                    print("Missing VIBRATE permission")
                    self.has_vibrator = False
                    return
                
            intensity = self.button_intensity if intensity is None else intensity
            ms = max(1, int(ms))
            
            if self._vibrator and HAS_ANDROID:
                try:
                    VibrationEffect = autoclass("android.os.VibrationEffect")
                    amplitude = int(max(1, min(255, int(intensity * 255))))
                    effect = VibrationEffect.createOneShot(ms, amplitude)
                    self._vibrator.vibrate(effect)
                    return
                except Exception as e1:
                    try:
                        self._vibrator.vibrate(ms)
                        return
                    except Exception as e2:
                        Logger.warning(f"VibrationManager: Legacy vibrate also failed: {e2}")
                        self.has_vibrator = False
                        return
            
            Logger.info(f"VibrationManager: (mock) vibrate {ms}ms intensity={intensity}")
            
        except Exception as e:
            Logger.error(f"VibrationManager.vibrate_duration error: {e}")
            self.has_vibrator = False

    def button_vibrate(self):
        self.vibrate_duration(50, self.button_intensity)

    def steering_vibrate(self, angle_change):
        intensity = min(1.0, abs(angle_change) / 30.0) * self.steering_intensity
        self.vibrate_duration(150, intensity)

    def pedal_vibrate_dynamic(self, pedal_value, pedal_change):
        base_intensity = self.pedal_min + (pedal_value / 100.0) * (self.pedal_max - self.pedal_min)
        change_intensity = min(0.3, abs(pedal_change) / 50.0)
        total_intensity = min(1.0, base_intensity + change_intensity)
        duration = int(100 * total_intensity)
        self.vibrate_duration(duration, total_intensity)

    def connection_vibrate(self):
        self.vibrate_duration(300, 0.8)

    def disconnection_vibrate(self):
        self.vibrate_duration(500, 0.6)

    def signal_lost_vibrate(self):
        self.vibrate_duration(700, 0.9)

class AccelerometerManager:
    def __init__(self):
        self.is_active = False
        self._sensor_manager = None
        self._sensor = None
        self._listener = None
        self._last_values = (0.0, 0.0, 0.0)
        self._poll_event = None
        self.controller = None
        self.sensitivity = get_setting('sensitivity', 1.0)
        self.steering_angle = 0
        self._is_initialized = False
        self._start_attempted = False
        self._stop_requested = False

        if HAS_ANDROID:
            self.initialize_sensor()

    def initialize_sensor(self):
        if not HAS_ANDROID or self._is_initialized:
            return False
            
        try:
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Sensor = autoclass('android.hardware.Sensor')
            SensorManager = autoclass('android.hardware.SensorManager')
            Context = autoclass('android.content.Context')
            
            activity = PythonActivity.mActivity
            self._sensor_manager = activity.getSystemService(Context.SENSOR_SERVICE)
            if not self._sensor_manager:
                print("Sensor service not available")
                return False
                
            self._sensor = self._sensor_manager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
            
            if not self._sensor:
                print("Accelerometer not available on this device")
                return False
                
            self._is_initialized = True
            print("Accelerometer initialized successfully")
            return True
        except Exception as e:
            print(f"Sensor initialization error: {e}")
            return False

    def start(self):
        if self.is_active:
            print("Accelerometer already active")
            return True
        
        if self._start_attempted:
            print("Accelerometer start already attempted")
            return False
            
        self._stop_requested = False
        self._start_attempted = True
            
        if not HAS_ANDROID:
            self.is_active = True
            if not self._poll_event:
                self._poll_event = Clock.schedule_interval(self._poll_fake_accel, 0.1)
            print("Accelerometer simulation started")
            return True
            
        try:
            if not self._is_initialized:
                if not self.initialize_sensor():
                    self._start_attempted = False
                    return False

            if self._listener:
                try:
                    self._sensor_manager.unregisterListener(self._listener)
                    self._listener = None
                except Exception as e:
                    print(f"Error unregistering previous listener: {e}")

            class AccelerometerEventListener(PythonJavaClass):
                __javainterfaces__ = ['android/hardware/SensorEventListener']
                
                def __init__(self, callback):
                    super().__init__()
                    self.callback = callback
                    self.is_active = True

                @java_method('(Landroid/hardware/SensorEvent;)V')
                def onSensorChanged(self, event):
                    if not self.is_active:
                        return
                    try:
                        values = event.values
                        x = float(values[0])
                        y = float(values[1])
                        z = float(values[2])
                        self.callback(x, y, z)
                    except Exception as e:
                        print(f"Sensor data error: {e}")

                @java_method('(Landroid/hardware/Sensor;I)V')
                def onAccuracyChanged(self, sensor, accuracy):
                    pass
                
                def deactivate(self):
                    self.is_active = False

            self._listener = AccelerometerEventListener(self.update_values)
            
            SensorManager = autoclass('android.hardware.SensorManager')
            success = self._sensor_manager.registerListener(
                self._listener,
                self._sensor,
                SensorManager.SENSOR_DELAY_GAME
            )
            
            if success:
                self.is_active = True
                print("Accelerometer started successfully")
                return True
            else:
                print("Failed to register sensor listener")
                self._start_attempted = False
                return False
                
        except Exception as e:
            print(f"Error starting accelerometer: {e}")
            self._start_attempted = False
            return False

    def stop(self):
        if not self.is_active and not self._stop_requested:
            return True
            
        self.is_active = False
        self._start_attempted = False
        self._stop_requested = True
        
        # 1. توقف شبیه‌سازی در حالت غیر-Android
        if not HAS_ANDROID:
            if self._poll_event:
                try:
                    self._poll_event.cancel()
                    self._poll_event = None
                except Exception as e:
                    print(f"Error canceling poll event: {e}")
            print("Accelerometer simulation stopped")
            return True
        
        # 2. توقف سنسور در Android
        try:
            # توقف استراق‌سمع از سنسور با احتیاط
            if self._sensor_manager and self._listener:
                try:
                    # حذف listener با try/except
                    self._sensor_manager.unregisterListener(self._listener)
                    print("Sensor listener unregistered")
                except Exception as unreg_error:
                    print(f"Error unregistering listener: {unreg_error}")
                finally:
                    # غیرفعال کردن callback برای جلوگیری از صدا زدن متدهای از بین رفته
                    if hasattr(self._listener, 'deactivate'):
                        try:
                            self._listener.deactivate()
                        except:
                            pass
                    self._listener = None
            
            # 3. اضافه کردن تأخیر کوچک برای ثبات در برخی دستگاه‌ها
            import time
            time.sleep(0.05)
            
            # 4. ریست کردن متغیرها
            self._sensor_manager = None
            self._sensor = None
            self._is_initialized = False
            self._last_values = (0.0, 0.0, 0.0)
            self.steering_angle = 0
            
            print("Accelerometer stopped successfully")
            return True
            
        except Exception as e:
            print(f"Non-critical error stopping accelerometer: {e}")
            # حتی با خطا، متغیرها را ریست کن
            self._sensor_manager = None
            self._sensor = None
            self._listener = None
            self._is_initialized = False
            return True

    def set_sensitivity(self, s):
        self.sensitivity = max(0.5, min(2.5, s))
        set_setting('sensitivity', self.sensitivity)
        print(f"Sensitivity set to: {self.sensitivity}")

    def get_orientation_adjusted_values(self, x, y, z):
        if Window.width > Window.height:
            x_adj = -y
            y_adj = x
            return x_adj, y_adj, z
        else:
            return x, y, z

    def update_values(self, x, y, z):
        if not self.is_active or self._stop_requested:
            return
            
        self._last_values = [x, y, z]
        try:
            x_adj, y_adj, z_adj = self.get_orientation_adjusted_values(x, y, z)
            
            tilt_angle = math.degrees(math.atan2(x_adj, math.sqrt(y_adj*y_adj + z_adj*z_adj)))
            tilt_angle = -tilt_angle
            tilt_angle *= self.sensitivity
            
            self.steering_angle = max(-90, min(90, tilt_angle * 2))
            
            # بررسی وجود کنترلر قبل از فراخوانی
            if self.is_active and not self._stop_requested and self.controller:
                try:
                    self.controller.update_steering_from_accelerometer(self.steering_angle)
                except Exception as controller_error:
                    print(f"Controller callback error: {controller_error}")
                    
        except Exception as e:
            print(f"Steering calculation error: {e}")

    def _poll_fake_accel(self, dt):
        if self._stop_requested or not self.is_active:
            return
            
        try:
            # بررسی وجود کنترلر
            if not self.controller:
                if self._poll_event:
                    try:
                        self._poll_event.cancel()
                        self._poll_event = None
                    except:
                        pass
                self.is_active = False
                self._stop_requested = True
                return
                
            base_x = random.uniform(-0.5, 0.5)
            base_y = random.uniform(-0.5, 0.5)
            base_z = 9.8
            
            x = base_x + random.uniform(-0.1, 0.1)
            y = base_y + random.uniform(-0.1, 0.1)
            z = base_z + random.uniform(-0.05, 0.05)
            
            # فقط اگر هنوز active باشد
            if not self._stop_requested and self.is_active:
                self.update_values(x, y, z)

        except Exception as e:
            print(f"Accelerometer simulation error: {e}")
            # در صورت خطا، توقف ایمن
            if self._poll_event:
                try:
                    self._poll_event.cancel()
                except:
                    pass
            self.is_active = False
            self._stop_requested = True

    def get_last(self):
        return self._last_values

class RealWiFiScanner:
    def __init__(self):
        self.wifi_manager = None
        self._scanning = False
        self._scan_callback = None
        
        if HAS_ANDROID:
            self.initialize()

    def initialize(self):
        try:
            Context = autoclass('android.content.Context')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            self.wifi_manager = activity.getSystemService(Context.WIFI_SERVICE)
            
            if self.wifi_manager:
                print("Real WiFi Scanner initialized")
                return True
            else:
                print("Failed to get WiFi service")
                return False
                
        except Exception as e:
            print(f"WiFi Scanner init error: {e}")
            return False

    def start_scan(self, callback):
        self._scan_callback = callback
        
        if not HAS_ANDROID:
            Clock.schedule_once(lambda dt: callback([
                "WiFi scanning requires Android",
                "Simulated networks:",
                "RC Car: RC_Car_WiFi",
                "   Strong | 2.4GHz | -45dBm | Open",
                "WiFi: Home_WiFi",
                "   Medium | 5GHz | -65dBm | WPA2"
            ]))
            return ["Simulation mode"]
            
        try:
            from android.permissions import check_permission, Permission
            
            required_perms = [
                Permission.ACCESS_FINE_LOCATION,
                Permission.ACCESS_WIFI_STATE,
                Permission.CHANGE_WIFI_STATE
            ]
            
            for perm in required_perms:
                if not check_permission(perm):
                    Clock.schedule_once(lambda dt: callback([
                        
                    ]))
                    return ["Permissions missing"]
            
            if not self.wifi_manager.isWifiEnabled():
                Clock.schedule_once(lambda dt: callback([
                    "WiFi is disabled",
                    "Please enable WiFi first",
                    "",
                    "Then try scanning again"
                ]))
                return ["WiFi disabled"]
            
            print("Starting real WiFi scan...")
            
            IntentFilter = autoclass('android.content.IntentFilter')
            WiFiManager = autoclass('android.net.wifi.WifiManager')
            
            class WiFiScanReceiver(PythonJavaClass):
                __javainterfaces__ = ['android/content/BroadcastReceiver']
                
                def __init__(self, scanner, callback):
                    super().__init__()
                    self.scanner = scanner
                    self.callback = callback
                
                @java_method('(Landroid/content/Context;Landroid/content/Intent;)V')
                def onReceive(self, context, intent):
                    try:
                        action = intent.getAction()
                        if action == WiFiManager.SCAN_RESULTS_AVAILABLE_ACTION:
                            print("WiFi scan results available")
                            
                            results = self.scanner.wifi_manager.getScanResults()
                            found_networks = []
                            
                            if results and results.size() > 0:
                                for i in range(min(20, results.size())):
                                    result = results.get(i)
                                    ssid = result.SSID if hasattr(result, 'SSID') else str(result)
                                    ssid = ssid.replace('"', '')
                                    
                                    if not ssid or ssid.startswith("\\x00") or len(ssid.strip()) == 0:
                                        continue
                                    
                                    level = result.level if hasattr(result, 'level') else -100
                                    frequency = result.frequency if hasattr(result, 'frequency') else 0
                                    capabilities = result.capabilities if hasattr(result, 'capabilities') else ""
                                    
                                    if level >= -50:
                                        strength = "Strong"
                                    elif level >= -70:
                                        strength = "Medium"
                                    else:
                                        strength = "Weak"
                                    
                                    band = "5GHz" if frequency > 3000 else "2.4GHz"
                                    
                                    is_rc_network = any(keyword in ssid.upper() for keyword in 
                                                      ["RC", "CAR", "ESP32", "ARDUINO", "ROBOT", "DRONE"])
                                    
                                    network_type = "RC Car" if is_rc_network else "WiFi"
                                    
                                    network_info = f"{network_type}: {ssid}"
                                    network_info += f"\n   {strength} | {band} | {level}dBm"
                                    
                                    if capabilities:
                                        if "WEP" in capabilities:
                                            network_info += " | WEP"
                                        elif "WPA" in capabilities:
                                            network_info += " | WPA"
                                        elif "WPA2" in capabilities:
                                            network_info += " | WPA2"
                                        elif "WPA3" in capabilities:
                                            network_info += " | WPA3"
                                        elif "OPEN" in capabilities or not capabilities:
                                            network_info += " | Open"
                                    
                                    found_networks.append(network_info)
                                    
                                rc_networks = [n for n in found_networks if "RC Car" in n]
                                other_networks = [n for n in found_networks if "RC Car" not in n]
                                sorted_networks = rc_networks + other_networks
                                
                                if not sorted_networks:
                                    sorted_networks = [
                                        "No RC Car networks found",
                                        "",
                                        "Make sure:",
                                        "1. RC Car is powered ON",
                                        "2. Car WiFi is broadcasting",
                                        "3. You're within range",
                                        "",
                                        "Common RC Car WiFi names:",
                                        "RC_Car_WiFi",
                                        "ESP32_Car",
                                        "Arduino_RC",
                                        "Robot_Car"
                                    ]
                                else:
                                    sorted_networks.insert(0, "Found WiFi Networks:")
                                    sorted_networks.append("")
                                    sorted_networks.append("Tap on your RC Car's network to connect")
                                    
                            else:
                                sorted_networks = [
                                    "No WiFi networks found",
                                    "Try:",
                                    "1. Moving closer to RC Car",
                                    "2. Restarting RC Car",
                                    "3. Checking if WiFi is enabled on car"
                                ]
                            
                            Clock.schedule_once(lambda dt: self.callback(sorted_networks))
                            
                            try:
                                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                                activity.unregisterReceiver(self)
                            except:
                                pass
                                
                    except Exception as e:
                        print(f"WiFi scan receiver error: {e}")
                        Clock.schedule_once(lambda dt: self.callback([f"Scan error: {str(e)}"]))
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            
            receiver = WiFiScanReceiver(self, callback)
            intent_filter = IntentFilter(WiFiManager.SCAN_RESULTS_AVAILABLE_ACTION)
            activity.registerReceiver(receiver, intent_filter)
            
            success = self.wifi_manager.startScan()
            
            if success:
                print("WiFi scan started successfully")
                
                def stop_scan_and_cleanup(dt):
                    try:
                        activity.unregisterReceiver(receiver)
                    except:
                        pass
                    
                    if not hasattr(self, '_results_received'):
                        Clock.schedule_once(lambda dt: callback([
                            "Scan timed out",
                            "No WiFi networks found",
                            "Please try again"
                        ]))
                
                Clock.schedule_once(stop_scan_and_cleanup, 10)
                return ["Scanning WiFi networks..."]
            else:
                Clock.schedule_once(lambda dt: callback(["Failed to start WiFi scan"]))
                return ["Scan failed"]
                
        except Exception as e:
            print(f"Real WiFi scan error: {e}")
            import traceback
            traceback.print_exc()
            Clock.schedule_once(lambda dt: callback([f"Scan error: {str(e)}"]))
            return [f"Error: {str(e)}"]

class SimpleWiFiManager:
    def __init__(self):
        self.connected = False
        self.device_name = ""
        self.main_app = None
        self.socket = None
        self.host = ""
        self.port = 80
        self.battery_level = 85
        self.battery_update_callback = None
        self.receive_thread = None
        self.should_receive = False
        self.last_communication_time = 0
        self.signal_check_interval = 5
        self.scanner = RealWiFiScanner()
        self._network_callback = None
        self._connectivity_manager = None
        self._current_network = None
        
        if HAS_ANDROID:
            self._initialize_android_components()
    
    def _initialize_android_components(self):
        """مقداردهی اولیه کامپوننت‌های اندروید"""
        try:
            from jnius import autoclass
            self.Context = autoclass('android.content.Context')
            self.PythonActivity = autoclass('org.kivy.android.PythonActivity')
            self.WifiNetworkSpecifier = autoclass('android.net.wifi.WifiNetworkSpecifier$Builder')
            self.NetworkRequest = autoclass('android.net.NetworkRequest$Builder')
            self.NetworkCapabilities = autoclass('android.net.NetworkCapabilities')
            self.ConnectivityManager = autoclass('android.net.ConnectivityManager')
            
            print("Android WiFi components initialized")
            return True
        except Exception as e:
            print(f"Android WiFi components initialization error: {e}")
            return False
    
    def initialize(self):
        print("Simple WiFi manager initialized")
        return True
    
    def set_battery_callback(self, callback):
        self.battery_update_callback = callback
    
    def check_signal_strength(self):
        if not self.connected:
            return 0
            
        elapsed = time.time() - self.last_communication_time
        if elapsed > self.signal_check_interval * 3:
            if self.main_app:
                Clock.schedule_once(lambda dt: self.main_app.on_signal_lost())
            return 0
        elif elapsed > self.signal_check_interval:
            return 1
        else:
            return 2
    
    def extract_ssid_from_network_info(self, network_info):
        """
        استخراج خودکار SSID از اطلاعات شبکه
        """
        try:
            print(f"Extracting SSID from: {network_info[:50]}...")
            
            # حذف خطوط اضافی
            lines = network_info.strip().split('\n')
            first_line = lines[0].strip()
            
            ssid = ""
            
            # تشخیص نوع شبکه و استخراج SSID
            if "RC Car:" in first_line:
                # فرمت: "RC Car: SSID_NAME"
                ssid = first_line.split("RC Car:")[1].strip()
            
            elif "WiFi:" in first_line:
                # فرمت: "WiFi: SSID_NAME"
                ssid = first_line.split("WiFi:")[1].strip()
            
            elif "(" in first_line and ")" in first_line:
                # فرمت: "SSID_NAME (MAC_ADDRESS)"
                ssid = first_line.split("(")[0].strip()
            
            else:
                # اگر فرمت ناشناخته، کل خط را بگیر
                ssid = first_line
            
            # پاکسازی SSID
            ssid = self._clean_ssid(ssid)
            
            print(f"Auto-extracted SSID: '{ssid}'")
            return ssid
            
        except Exception as e:
            print(f"SSID extraction error: {e}")
            return ""
    
    def _clean_ssid(self, ssid):
        """پاکسازی SSID از کاراکترهای نامعتبر"""
        if not ssid:
            return ""
        
        # حذف کاراکترهای غیرقابل چاپ
        cleaned = re.sub(r'[^\x20-\x7E\u0600-\u06FF]', '', ssid)
        
        # حذف اسپیس اضافی
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _is_protected_network(self, network_info):
        """بررسی آیا شبکه رمزدار است"""
        return "WEP" in network_info or "WPA" in network_info or "WPA2" in network_info or "WPA3" in network_info
    
    def connect_to_network(self, network_info):
        """
        اتصال به شبکه WiFi (روش مدرن با WifiNetworkSpecifier)
        """
        try:
            print(f"Selected network: {network_info}")
            
            # استخراج خودکار SSID
            ssid = self.extract_ssid_from_network_info(network_info)
            
            if not ssid:
                print("Could not extract SSID from network info")
                return False
            
            # بررسی آیا شبکه رمزدار است
            if self._is_protected_network(network_info):
                # نمایش دیالوگ برای وارد کردن رمز
                if self.main_app:
                    Clock.schedule_once(
                        lambda dt: self.main_app.show_wifi_password_dialog(ssid)
                    )
                return True
            else:
                # شبکه باز - اتصال مستقیم
                return self.connect_with_password(ssid, None)
                
        except Exception as e:
            print(f"Error connecting to network: {e}")
            return False
    
    def connect_with_password(self, ssid, password, ip="192.168.4.1", port=80):
        """
        اتصال خودکار به WiFi با استفاده از SSID و رمز عبور
        """
        try:
            print(f"Starting connection to: {ssid}")
            
            if not HAS_ANDROID:
                print("WiFi auto-connect only available on Android")
                return False
            
            # بررسی مجوزهای لازم
            from android.permissions import check_permission, Permission
            
            required_perms = [
                Permission.ACCESS_FINE_LOCATION,
                Permission.CHANGE_WIFI_STATE,
                Permission.ACCESS_WIFI_STATE
            ]
            
            for perm in required_perms:
                if not check_permission(perm):
                    print(f"Missing permission: {perm}")
                    if self.main_app:
                        self.main_app.show_connection_message(
                            f"Permission required: {perm}", 
                            "error"
                        )
                    return False
            
            # بررسی نسخه اندروید (حداقل API 29 برای WifiNetworkSpecifier)
            from jnius import autoclass
            Build_VERSION = autoclass('android.os.Build$VERSION')
            
            if Build_VERSION.SDK_INT < 29:
                print(f"Android {Build_VERSION.SDK_INT} - Using legacy method")
                return self._connect_legacy(ssid, password, ip, port)
            
            # روش مدرن با WifiNetworkSpecifier (API 29+)
            print(f"Using WifiNetworkSpecifier (Android {Build_VERSION.SDK_INT}+)")
            return self._connect_with_specifier(ssid, password, ip, port)
            
        except Exception as e:
            print(f"WiFi auto-connect error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _connect_with_specifier(self, ssid, password, ip, port):
        """اتصال با استفاده از WifiNetworkSpecifier (Android 10+)"""
        from jnius import autoclass, PythonJavaClass, java_method, cast
        
        try:
            activity = self.PythonActivity.mActivity
            context = activity.getApplicationContext()
            
            # ساخت specifier برای شبکه WiFi
            specifier_builder = self.WifiNetworkSpecifier()
            
            # اضافه کردن SSID (می‌تواند به صورت String باشد)
            try:
                specifier_builder.setSsid(ssid)
            except Exception as e:
                print(f"Error setting SSID as string: {e}")
                # امتحان کردن به صورت بایت‌آرایه
                ssid_bytes = ssid.encode('utf-8')
                specifier_builder.setSsidPattern(None, ssid_bytes)
            
            # اگر رمز وجود دارد
            if password and password.strip():
                try:
                    # برای شبکه‌های WPA2
                    specifier_builder.setWpa2Passphrase(password.strip())
                except Exception as e:
                    print(f"WPA2 passphrase error: {e}")
                    # برای شبکه‌های WPA3
                    try:
                        specifier_builder.setWpa3Passphrase(password.strip())
                    except Exception as e2:
                        print(f"Could not set password: {e2}")
                        return False
            
            specifier = specifier_builder.build()
            
            # ساخت NetworkRequest
            request_builder = self.NetworkRequest()
            request_builder.addTransportType(self.NetworkCapabilities.TRANSPORT_WIFI)
            request_builder.setNetworkSpecifier(specifier)
            request = request_builder.build()
            
            # دریافت ConnectivityManager
            self._connectivity_manager = cast(
                self.ConnectivityManager,
                context.getSystemService(self.Context.CONNECTIVITY_SERVICE)
            )
            
            # تعریف NetworkCallback
            class WiFiNetworkCallback(PythonJavaClass):
                __javainterfaces__ = ['android/net/ConnectivityManager$NetworkCallback']
                
                def __init__(self, wifi_manager, ssid, ip, port):
                    super().__init__()
                    self.wifi_manager = wifi_manager
                    self.ssid = ssid
                    self.ip = ip
                    self.port = port
                    print(f"NetworkCallback created for: {ssid}")
                
                @java_method('(Landroid/net/Network;)V')
                def onAvailable(self, network):
                    print(f"WiFi CONNECTED to: {self.ssid}")
                    
                    # ذخیره شبکه
                    self.wifi_manager._current_network = network
                    
                    # اتصال TCP به ربات
                    Clock.schedule_once(
                        lambda dt: self.wifi_manager._connect_tcp_after_wifi(self.ip, self.port),
                        1.0  # کمی صبر کن
                    )
                
                @java_method('(Landroid/net/Network;)V')
                def onLost(self, network):
                    print(f"WiFi DISCONNECTED from: {self.ssid}")
                    self.wifi_manager._current_network = None
                    
                    if self.wifi_manager.main_app:
                        Clock.schedule_once(
                            lambda dt: self.wifi_manager.main_app.on_signal_lost()
                        )
                
                @java_method('(I)V')
                def onUnavailable(self):
                    print(f"WiFi UNAVAILABLE: {self.ssid}")
                    
                    if self.wifi_manager.main_app:
                        Clock.schedule_once(
                            lambda dt: self.wifi_manager.main_app.show_connection_message(
                                f"Could not connect to {self.ssid}", 
                                "error"
                            )
                        )
            
            # ایجاد callback و درخواست اتصال
            self._network_callback = WiFiNetworkCallback(self, ssid, ip, port)
            self._connectivity_manager.requestNetwork(request, self._network_callback)
            
            print(f"WiFi connection request sent for: {ssid}")
            
            if self.main_app:
                self.main_app.show_connection_message(
                    f"Connecting to {ssid}...", 
                    "info"
                )
            
            return True
            
        except Exception as e:
            print(f"Error creating WiFi specifier: {e}")
            # روش قدیمی را امتحان کن
            return self._connect_legacy(ssid, password, ip, port)
    
    def _connect_tcp_after_wifi(self, ip, port):
        """بعد از اتصال WiFi، به ربات TCP وصل شود"""
        try:
            print(f"Connecting TCP to {ip}:{port}...")
            
            if self.connected:
                self.disconnect()
                time.sleep(1)
            
            self.host = ip
            self.port = int(port)
            self.device_name = f"RC_Car_{ip}"
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            
            self.connected = True
            self.last_communication_time = time.time()
            self.should_receive = True
            self._start_receive_thread()
            
            print(f"Connected to {ip}:{port}")
            
            # ذخیره در تاریخچه
            self._save_connection_to_history(ip, port)
            
            if self.main_app:
                Clock.schedule_once(lambda dt: self._update_connection_ui())
                self.main_app.show_connection_message(
                    f"Connected to {self.device_name}!", 
                    "success"
                )
            
            return True
            
        except Exception as e:
            print(f"TCP connection failed: {e}")
            if self.main_app:
                self.main_app.show_connection_message(
                    f"TCP connection failed: {str(e)}", 
                    "error"
                )
            return False
    
    def _connect_legacy(self, ssid, password, ip, port):
        """روش قدیمی برای اندرویدهای قدیمی"""
        print(f"Using legacy method for SSID: {ssid}")
        
        # باز کردن تنظیمات WiFi
        return self._open_wifi_settings(ssid)
    
    def _open_wifi_settings(self, ssid):
        """باز کردن تنظیمات WiFi (روش قدیمی)"""
        try:
            from jnius import autoclass
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            Settings = autoclass('android.provider.Settings')
            
            activity = PythonActivity.mActivity
            
            intent = Intent(Settings.ACTION_WIFI_SETTINGS)
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            
            activity.startActivity(intent)
            print(f"Opening WiFi settings for network: {ssid}")
            
            if self.main_app:
                Clock.schedule_once(lambda dt: self.main_app.show_connection_message(
                    f"Please connect to:\n'{ssid}'\n\n" +
                    "1. Open WiFi settings\n" +
                    "2. Select the network\n" +
                    "3. Tap 'Connect'\n" +
                    "4. Return to this app\n\n" +
                    "After connecting, enter the car's IP address",
                    "info"
                ))
            
            return True
            
        except Exception as e:
            print(f"Error opening WiFi settings: {e}")
            if self.main_app:
                Clock.schedule_once(lambda dt: self.main_app.show_connection_message(
                    f"Could not open WiFi settings: {str(e)}\n\n" +
                    "Please manually connect to WiFi then enter IP",
                    "error"
                ))
            return False
    
    def _save_connection_to_history(self, ip, port):
        try:
            app = App.get_running_app()
            if hasattr(app, 'settings_manager'):
                app.settings_manager.add_saved_wifi_connection(
                    ip=ip,
                    port=port,
                    connection_name=self.device_name
                )
                print(f"Connection saved to history: {ip}:{port}")
        except Exception as e:
            print(f"Could not save connection to history: {e}")
    
    def _start_receive_thread(self):
        def receive_loop():
            try:
                while self.should_receive and self.connected and self.socket:
                    try:
                        self.socket.settimeout(0.5)
                        data = self.socket.recv(1024)
                        if data:
                            message = data.decode('utf-8').strip()
                            print(f"WiFi: {message}")
                            self.last_communication_time = time.time()
                            
                            if "BAT" in message or "battery" in message.lower():
                                try:
                                    numbers = [int(s) for s in message.split() if s.isdigit()]
                                    if numbers:
                                        level = max(0, min(100, numbers[0]))
                                        self.battery_level = level
                                        if self.battery_update_callback:
                                            Clock.schedule_once(lambda dt: self.battery_update_callback(level))
                                except:
                                    pass
                                    
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if self.connected:
                            print(f"WiFi receive error: {e}")
                            break
                        
            except Exception as e:
                print(f"WiFi receive thread error: {e}")
                if self.connected and self.main_app:
                    Clock.schedule_once(lambda dt: self.main_app.on_signal_lost())
        
        self.receive_thread = threading.Thread(target=receive_loop, daemon=True)
        self.receive_thread.start()
    
    def _update_connection_ui(self):
        if self.main_app:
            self.main_app.connected_device = f"Connected: {self.device_name}"
            self.main_app.battery_level = f"{self.battery_level}%"
            self.main_app.connection_status = "Connected (WiFi)"
    
    def send_command(self, command):
        if not self.connected:
            print(f"[WiFi NOT CONNECTED] {command}")
            return False
            
        try:
            if not self.socket:
                return False
                
            data = (command + '\n').encode('utf-8')
            self.socket.sendall(data)
            self.last_communication_time = time.time()
            
            print(f"WiFi Command: {command}")
            return True
            
        except Exception as e:
            print(f"WiFi send error: {e}")
            return False
    
    def disconnect(self):
        try:
            self.connected = False
            self.should_receive = False
            
            # قطع اتصال TCP
            if self.socket:
                self.socket.close()
                self.socket = None
            
            # قطع اتصال WiFi (در اندروید)
            if HAS_ANDROID and self._connectivity_manager and self._network_callback:
                try:
                    self._connectivity_manager.unregisterNetworkCallback(self._network_callback)
                    self._current_network = None
                except Exception as e:
                    print(f"Error unregistering network callback: {e}")
            
            print("WiFi and TCP disconnected")
            
        except Exception as e:
            print(f"WiFi disconnect error: {e}")

class AndroidBLE:
    def __init__(self):
        self.connected = False
        self.device_name = ""
        self.main_app = None
        self.battery_level = 85
        self.battery_update_callback = None
        self.ble_devices = []
        self.scan_callback = None
        self.gatt = None
        self.characteristics = {}
        self.last_communication_time = 0
        self.signal_check_interval = 5
        self._scanning = False
        self._scan_cb_obj = None
        self._adapter = None
        self._scanner = None
        
        if HAS_ANDROID:
            self.initialize()

    def initialize(self):
        if not HAS_ANDROID:
            print("BLE not available on desktop")
            return False
        try:
            BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
            self._adapter = BluetoothAdapter.getDefaultAdapter()
            if not self._adapter:
                print("Bluetooth adapter not available")
                return False
            
            if not self._adapter.isEnabled():
                print("Bluetooth is disabled")
                return False
                
            print("BLE initialized successfully")
            return True
        except Exception as e:
            print(f"BLE init error: {e}")
            return False

    def start_scan(self, callback, duration=6):
        self.scan_callback = callback
        
        if not HAS_ANDROID:
            Clock.schedule_once(lambda dt: callback(["BLE simulation - No real devices"]))
            return ["BLE simulation mode"]
            
        try:
            if not self._adapter or not self._adapter.isEnabled():
                Clock.schedule_once(lambda dt: callback(["Bluetooth is disabled - please enable Bluetooth"]))
                return ["Bluetooth disabled"]
            
            self._scanner = self._adapter.getBluetoothLeScanner()
            if not self._scanner:
                Clock.schedule_once(lambda dt: callback(["BLE scanner not available"]))
                return ["BLE scanner unavailable"]
            
            from jnius import PythonJavaClass, java_method
            
            class ScanCallback(PythonJavaClass):
                __javainterfaces__ = ['android/bluetooth/le/ScanCallback']
                
                def __init__(self, outer):
                    super().__init__()
                    self.outer = outer
                    self.found_devices = []

                @java_method('(ILandroid/bluetooth/le/ScanResult;)V')
                def onScanResult(self, callbackType, result):
                    try:
                        device = result.getDevice()
                        name = device.getName()
                        address = device.getAddress()
                        rssi = result.getRssi()
                        
                        if name:
                            device_info = f"{name} ({address}) - {rssi}dBm"
                        else:
                            device_info = f"Unknown Device ({address}) - {rssi}dBm"
                            
                        if device_info not in self.found_devices:
                            self.found_devices.append(device_info)
                            print(f"Found BLE device: {device_info}")
                                
                    except Exception as e:
                        print(f"BLE scan result error: {e}")

                @java_method('(I)V')
                def onScanFailed(self, errorCode):
                    error_messages = {
                        1: "SCAN_FAILED_ALREADY_STARTED",
                        2: "SCAN_FAILED_APPLICATION_REGISTRATION_FAILED", 
                        3: "SCAN_FAILED_INTERNAL_ERROR",
                        4: "SCAN_FAILED_FEATURE_UNSUPPORTED",
                        5: "SCAN_FAILED_OUT_OF_HARDWARE_RESOURCES"
                    }
                    error_msg = error_messages.get(errorCode, f"Unknown error: {errorCode}")
                    print(f"BLE scan failed: {error_msg}")
                    Clock.schedule_once(lambda dt: self.outer.scan_callback([f"Scan failed: {error_msg}"]))

            scan_callback = ScanCallback(self)
            self._scan_cb_obj = scan_callback
            
            ScanSettings = autoclass('android.bluetooth.le.ScanSettings')
            ScanSettingsBuilder = autoclass('android.bluetooth.le.ScanSettings$Builder')
            builder = ScanSettingsBuilder()
            builder.setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            scan_settings = builder.build()
            
            self._scanner.startScan(None, scan_settings, scan_callback)
            print("BLE scan started")
            
            def stop_scan(dt):
                try:
                    if self._scanner and self._scan_cb_obj:
                        self._scanner.stopScan(self._scan_cb_obj)
                    devices = getattr(scan_callback, 'found_devices', [])
                    
                    if not devices:
                        devices = ["No BLE devices found - Make sure devices are discoverable"]
                        
                    print(f"BLE scan completed: {len(devices)} devices found")
                    Clock.schedule_once(lambda dt: callback(devices))
                except Exception as e:
                    print(f"Error stopping BLE scan: {e}")
                    Clock.schedule_once(lambda dt: callback([f"Scan error: {str(e)}"]))
            
            Clock.schedule_once(stop_scan, duration)
            return ["BLE scan started..."]
            
        except Exception as e:
            print(f"BLE start_scan error: {e}")
            Clock.schedule_once(lambda dt: callback([f"BLE scan error: {str(e)}"]))
            return [f"BLE scan error: {str(e)}"]

    def connect(self, device_address):
        try:
            print(f"BLE connect to: {device_address}")
            if not HAS_ANDROID:
                print("BLE not available on desktop")
                return False
            
            if '(' in device_address and ')' in device_address:
                address = device_address.split('(')[-1].split(')')[0]
                self.device_name = device_address.split('(')[0].strip()
            else:
                address = device_address
                self.device_name = "BLE Device"
            
            device = self._adapter.getRemoteDevice(address)
            if not device:
                print(f"BLE device not found: {address}")
                return False
            
            BluetoothGatt = autoclass('android.bluetooth.BluetoothGatt')
            BluetoothGattCallback = autoclass('android.bluetooth.BluetoothGattCallback')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            
            class GattCallback(BluetoothGattCallback):
                def __init__(self, outer):
                    super().__init__()
                    self.outer = outer

                def onConnectionStateChange(self, gatt, status, newState):
                    try:
                        BluetoothProfile = autoclass('android.bluetooth.BluetoothProfile')
                        if newState == BluetoothProfile.STATE_CONNECTED:
                            self.outer.gatt = gatt
                            self.outer.connected = True
                            self.outer.last_communication_time = time.time()
                            print("BLE Connected")
                            
                            gatt.discoverServices()
                            
                            if self.outer.main_app:
                                Clock.schedule_once(lambda dt: setattr(self.outer.main_app, 'connection_status', 'Connected (BLE)'))
                                
                        elif newState == BluetoothProfile.STATE_DISCONNECTED:
                            self.outer.connected = False
                            print("BLE Disconnected")
                            if self.outer.main_app:
                                Clock.schedule_once(lambda dt: self.outer.main_app.on_signal_lost())
                    except Exception as e:
                        print(f"onConnectionStateChange error: {e}")

                def onServicesDiscovered(self, gatt, status):
                    try:
                        if status == BluetoothGatt.GATT_SUCCESS:
                            self.outer._discover_characteristics(gatt)
                            print("BLE Services discovered")
                        else:
                            print(f"Service discovery failed: {status}")
                    except Exception as e:
                        print(f"onServicesDiscovered error: {e}")

                def onCharacteristicRead(self, gatt, characteristic, status):
                    try:
                        if status == BluetoothGatt.GATT_SUCCESS:
                            val = characteristic.getValue()
                            if val:
                                data = ''.join([chr(b) for b in val])
                                self.outer.last_communication_time = time.time()
                                print(f"BLE Read: {data}")
                    except Exception as e:
                        print(f"onCharacteristicRead error: {e}")

                def onCharacteristicChanged(self, gatt, characteristic):
                    try:
                        val = characteristic.getValue()
                        if val:
                            data = ''.join([chr(b) for b in val])
                            self.outer.last_communication_time = time.time()
                            print(f"BLE Notification: {data}")
                            
                            if "BAT" in data or "battery" in data.lower():
                                try:
                                    numbers = [int(s) for s in data.split() if s.isdigit()]
                                    if numbers:
                                        level = max(0, min(100, numbers[0]))
                                        self.outer.battery_level = level
                                        if self.outer.battery_update_callback:
                                            Clock.schedule_once(lambda dt: self.outer.battery_update_callback(level))
                                except:
                                    pass
                    except Exception as e:
                        print(f"onCharacteristicChanged error: {e}")

            self.gatt_callback = GattCallback(self)
            self.gatt = device.connectGatt(PythonActivity.mActivity, False, self.gatt_callback)
            
            def check_connection(dt):
                if self.connected:
                    if self.main_app:
                        self.main_app.connected_device = f"Connected: {self.device_name}"
                        self.main_app.connection_status = "Connected (BLE)"
                    return False
                return True
            
            Clock.schedule_interval(check_connection, 0.5)
            return True
            
        except Exception as e:
            print(f"BLE connect error: {e}")
            return False

    def _discover_characteristics(self, gatt):
        try:
            services = gatt.getServices()
            print(f"Discovering characteristics for {services.size()} services...")
            
            for i in range(services.size()):
                service = services.get(i)
                service_uuid = service.getUuid().toString()
                print(f"Service: {service_uuid}")
                
                characteristics = service.getCharacteristics()
                for j in range(characteristics.size()):
                    char = characteristics.get(j)
                    props = char.getProperties()
                    uuid = char.getUuid().toString()
                    print(f"Characteristic: {uuid}, Properties: {props}")
                    
                    if props & 0x08 or props & 0x04:
                        self.characteristics['write'] = char
                        print(f"Found WRITE characteristic")
                    
                    if props & 0x10 or props & 0x20:
                        gatt.setCharacteristicNotification(char, True)
                        
                        descriptors = char.getDescriptors()
                        for k in range(descriptors.size()):
                            desc = descriptors.get(k)
                            desc_uuid = desc.getUuid().toString().lower()
                            if "2902" in desc_uuid:
                                desc.setValue([0x01, 0x00])
                                gatt.writeDescriptor(desc)
                                print(f"Enabled notifications")
                        
                        self.characteristics['notify'] = char
                        print(f"Found NOTIFY characteristic")
                    
                    if props & 0x02:
                        self.characteristics['read'] = char
                        print(f"Found READ characteristic")
            
            print(f"Characteristic discovery completed")
            
        except Exception as e:
            print(f"Characteristic discovery error: {e}")

    def send_command(self, command):
        if not self.connected:
            print(f"[BLE NOT CONNECTED] {command}")
            return False
        
        if not HAS_ANDROID:
            print(f"[BLE NOT CONNECTED] {command}")
            return False
            
        try:
            if not self.gatt or 'write' not in self.characteristics:
                print("[BLE NO WRITE CHARACTERISTIC]")
                return False
                
            char = self.characteristics['write']
            data = (command + '\n').encode('utf-8')
            char.setValue(data)
            success = self.gatt.writeCharacteristic(char)
            
            if success:
                self.last_communication_time = time.time()
                print(f"BLE Command sent: {command}")
            else:
                print(f"BLE Command failed: {command}")
                
            return success
            
        except Exception as e:
            print(f"BLE send error: {e}")
            return False

    def disconnect(self):
        try:
            if HAS_ANDROID and self.gatt:
                try:
                    self.gatt.disconnect()
                    self.gatt.close()
                except Exception as e:
                    print(f"gatt disconnect error: {e}")
                finally:
                    self.gatt = None
            self.connected = False
            self.characteristics = {}
            print("BLE disconnected")
        except Exception as e:
            print(f"BLE disconnect error: {e}")

    def set_battery_callback(self, cb):
        self.battery_update_callback = cb

    def check_signal_strength(self):
        if not self.connected:
            return 0
        elapsed = time.time() - self.last_communication_time
        if elapsed > self.signal_check_interval * 3:
            if self.main_app:
                Clock.schedule_once(lambda dt: self.main_app.on_signal_lost())
            return 0
        elif elapsed > self.signal_check_interval:
            return 1
        else:
            return 2

class ClassicBluetooth:
    def __init__(self):
        self.connected = False
        self.device_name = ""
        self.main_app = None
        self.socket = None
        self.battery_level = 85
        self.bluetooth_adapter = None
        self.last_communication_time = 0
        self.signal_check_interval = 5
        self._receive_thread = None
        self._should_receive = False
        self.battery_update_callback = None

    def initialize(self):
        if not HAS_ANDROID:
            return False
        try:
            BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
            self.bluetooth_adapter = BluetoothAdapter.getDefaultAdapter()
            if not self.bluetooth_adapter:
                return False
            return True
        except Exception as e:
            print(f"Classic init error: {e}")
            return False

    def start_scan(self, callback):
        self.scan_callback = callback
        
        if not HAS_ANDROID:
            Clock.schedule_once(lambda dt: callback(["Classic BT simulation - No real devices"]))
            return ["Classic BT simulation mode"]
        
        try:
            if not self.bluetooth_adapter or not self.bluetooth_adapter.isEnabled():
                Clock.schedule_once(lambda dt: callback(["Bluetooth is disabled - please enable Bluetooth"]))
                return ["Bluetooth disabled"]
            
            bonded_devices = self.bluetooth_adapter.getBondedDevices()
            devices = []
            
            if bonded_devices and bonded_devices.size() > 0:
                for i in range(bonded_devices.size()):
                    device = bonded_devices.get(i)
                    name = device.getName()
                    address = device.getAddress()
                    if name and address:
                        device_str = f"{name} ({address})"
                        devices.append(device_str)
                        print(f"Found Classic BT: {name} - {address}")
            
            if devices:
                Clock.schedule_once(lambda dt: callback(devices))
                return [f"Found {len(devices)} Classic BT devices"]
            else:
                Clock.schedule_once(lambda dt: callback(["No paired Classic BT devices found"]))
                return ["No paired devices - Please pair your device first"]
            
        except Exception as e:
            print(f"Classic Bluetooth scan error: {e}")
            return [f"Scan error: {str(e)}"]

    def connect(self, device_address):
        try:
            print(f"Classic BT connect to: {device_address}")
            
            if not HAS_ANDROID:
                print("Classic BT not available")
                return False
                
            if '(' in device_address and ')' in device_address:
                address = device_address.split('(')[-1].split(')')[0]
                self.device_name = device_address.split('(')[0].strip()
            else:
                address = device_address
                self.device_name = "Classic BT Device"
            
            print(f"Connecting to: {self.device_name} - {address}")
            
            if self.connected:
                self.disconnect()
                time.sleep(1)
            
            BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
            UUID = autoclass('java.util.UUID')
            
            device = self.bluetooth_adapter.getRemoteDevice(address)
            if not device:
                print(f"Device not found: {address}")
                return False
            
            uuid = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
            socket = device.createRfcommSocketToServiceRecord(uuid)
            
            socket.connect()
            self.socket = socket
            self.connected = True
            self.last_communication_time = time.time()
            
            print("Classic Bluetooth connected")
            self._start_receive_thread()
            
            return True
            
        except Exception as e:
            print(f"Classic Bluetooth connect error: {e}")
            return False

    def _start_receive_thread(self):
        def receive_loop():
            try:
                input_stream = self.socket.getInputStream()
                buffer = bytearray(1024)
                
                while self.connected and self.socket:
                    try:
                        bytes_read = input_stream.read(buffer)
                        if bytes_read > 0:
                            data = buffer[:bytes_read].decode('utf-8').strip()
                            print(f"Classic BT: {data}")
                            self.last_communication_time = time.time()
                            
                            if "BAT" in data or "battery" in data.lower():
                                try:
                                    numbers = [int(s) for s in data.split() if s.isdigit()]
                                    if numbers:
                                        level = max(0, min(100, numbers[0]))
                                        self.battery_level = level
                                        if self.battery_update_callback:
                                            Clock.schedule_once(lambda dt: self.battery_update_callback(level))
                                except:
                                    pass
                                
                    except Exception as e:
                        if self.connected:
                            print(f"Classic BT receive error: {e}")
                            break
                            
            except Exception as e:
                if self.connected:
                    print(f"Classic BT receive thread error: {e}")
                    if self.main_app:
                        Clock.schedule_once(lambda dt: self.main_app.on_signal_lost())
        
        self._receive_thread = threading.Thread(target=receive_loop, daemon=True)
        self._receive_thread.start()

    def send_command(self, command):
        if not self.connected:
            print(f"[Classic BT NOT CONNECTED] {command}")
            return False
            
        if not HAS_ANDROID:
            print(f"[Classic BT NOT CONNECTED] {command}")
            return False
            
        try:
            if not self.socket:
                return False
                
            output_stream = self.socket.getOutputStream()
            data = (command + '\n').encode('utf-8')
            output_stream.write(data)
            output_stream.flush()
            self.last_communication_time = time.time()
            
            print(f"Classic BT Command: {command}")
            return True
            
        except Exception as e:
            print(f"Classic BT send error: {e}")
            return False

    def disconnect(self):
        try:
            self.connected = False
            
            if HAS_ANDROID and self.socket:
                self.socket.close()
                self.socket = None
                
            print("Classic Bluetooth disconnected")
            
        except Exception as e:
            print(f"Classic Bluetooth disconnect error: {e}")

    def set_battery_callback(self, callback):
        self.battery_update_callback = callback

    def check_signal_strength(self):
        if not self.connected:
            return 0
            
        elapsed = time.time() - self.last_communication_time
        if elapsed > self.signal_check_interval * 3:
            if self.main_app:
                Clock.schedule_once(lambda dt: self.main_app.on_signal_lost())
            return 0
        elif elapsed > self.signal_check_interval:
            return 1
        else:
            return 2

class ConnectionManager:
    def __init__(self):
        self.connection_type = get_setting('connection_type', 'ble')
        self.ble = AndroidBLE()
        self.classic_bt = ClassicBluetooth()
        self.wifi = SimpleWiFiManager()
        
        self.ble.main_app = self
        self.classic_bt.main_app = self
        self.wifi.main_app = self
        
        self.connected = False
        self.device_name = ""
        self.battery_level = 85
        self.main_app = None
        self.signal_check_event = None
        
    def show_connection_message(self, message, msg_type):
        if self.main_app and hasattr(self.main_app, 'show_connection_message'):
            self.main_app.show_connection_message(message, msg_type)
        else:
            print(f"{msg_type.upper()}: {message}")
    
    def set_connection_type(self, conn_type):
        self.connection_type = conn_type
        set_setting('connection_type', conn_type)
        print(f"Connection type set to: {conn_type}")
        
        if self.connected:
            self.disconnect()
    
    def get_current_connection(self):
        if self.connection_type == 'ble':
            return self.ble
        elif self.connection_type == 'classic':
            return self.classic_bt
        else:
            return self.wifi
    
    def start_scan(self, callback):
        try:
            conn = self.get_current_connection()
            return conn.start_scan(callback)
        except Exception as e:
            print(f"ConnectionManager.start_scan error: {e}")
            return [f"Scan error: {str(e)}"]
    
    def connect(self, device_address):
        conn = self.get_current_connection()
        success = conn.connect(device_address)
        
        if success:
            self.connected = True
            self.device_name = conn.device_name
            
            self.start_signal_monitoring()
        
        return success
    
    def send_command(self, command):
        if not self.connected:
            print(f"[{self.connection_type.upper()} NOT CONNECTED] {command}")
            return False
            
        conn = self.get_current_connection()
        return conn.send_command(command)
    
    def disconnect(self):
        self.stop_signal_monitoring()
        self.ble.disconnect()
        self.classic_bt.disconnect()
        self.wifi.disconnect()
        self.connected = False
        self.device_name = ""
        print("All connections disconnected")
    
    def set_battery_callback(self, callback):
        self.ble.set_battery_callback(callback)
        self.classic_bt.set_battery_callback(callback)
        self.wifi.set_battery_callback(callback)
    
    def get_battery_level(self):
        conn = self.get_current_connection()
        return conn.battery_level
    
    def start_signal_monitoring(self):
        if self.signal_check_event:
            self.signal_check_event.cancel()
        
        self.signal_check_event = Clock.schedule_interval(self.check_signal, 3)
    
    def stop_signal_monitoring(self):
        if self.signal_check_event:
            self.signal_check_event.cancel()
            self.signal_check_event = None
    
    def check_signal(self, dt):
        if self.connected and self.main_app:
            conn = self.get_current_connection()
            signal_strength = conn.check_signal_strength()
            
            if self.main_app:
                signal_status = ["No Signal", "Weak Signal", "Strong Signal"]
                signal_colors = [(1, 0, 0, 1), (1, 0.5, 0, 1), (0, 0.8, 0, 1)]
                
                if hasattr(self.main_app, 'signal_status_label'):
                    self.main_app.signal_status_label.text = signal_status[signal_strength]
                    self.main_app.signal_status_label.color = signal_colors[signal_strength]

class BatteryIndicator(Widget):
    level = NumericProperty(85)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._update_canvas, size=self._update_canvas, level=self._update_canvas)
        Clock.schedule_once(self._update_canvas, 0.1)

    def _update_canvas(self, *args):
        self.canvas.clear()
        try:
            with self.canvas:
                if self.width == 0 or self.height == 0:
                    return
                    
                width, height = self.size
                padding = min(width, height) * 0.1
                body_width = width - padding * 3
                body_height = height - padding * 2
                
                if body_width <= 0 or body_height <= 0:
                    return
                
                Color(0.8, 0.8, 0.8, 1)
                Rectangle(
                    pos=(self.x + padding, self.y + padding),
                    size=(body_width, body_height)
                )
                
                tip_width = padding
                tip_height = body_height * 0.4
                tip_x = self.x + padding + body_width
                tip_y = self.y + padding + (body_height - tip_height) / 2
                Rectangle(
                    pos=(tip_x, tip_y),
                    size=(tip_width, tip_height)
                )
                
                charge_width = max(2, (body_width - 4) * self.level / 100)
                charge_height = body_height - 4
                
                if self.level <= 20:
                    Color(1, 0, 0, 1)
                elif self.level <= 50:
                    Color(1, 0.5, 0, 1)
                else:
                    Color(0, 0.8, 0, 1)
                
                if charge_width > 0 and charge_height > 0:
                    Rectangle(
                        pos=(self.x + padding + 2, self.y + padding + 2),
                        size=(charge_width, charge_height)
                    )
                    
        except Exception as e:
            print(f"Battery indicator drawing error: {e}")

class RotatableImage(Image):
    angle = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(angle=self._update_rotation)
        self._rotation = None
        with self.canvas.before:
            PushMatrix()
            self._rotation = Rotate(angle=self.angle, origin=self.center)
        with self.canvas.after:
            PopMatrix()

    def _update_rotation(self, *args):
        if self._rotation:
            self._rotation.angle = -self.angle
            self._rotation.origin = self.center

    def on_size(self, *args):
        if self._rotation:
            self._rotation.origin = self.center

    def on_pos(self, *args):
        if self._rotation:
            self._rotation.origin = self.center

class ImageButton(ButtonBehavior, Image):
    def __init__(self, normal_source, active_source=None, **kwargs):
        super().__init__(**kwargs)
        self.normal_source = normal_source
        self.active_source = active_source or normal_source
        
        self.source = self._find_image_path(normal_source)
        self.is_active = False
        self.controller = None
        self.command = ""
        self.normal_color = (1, 1, 1, 1)
        self.active_color = (0.2, 0.8, 1, 1)
        self.color = self.normal_color

    def _find_image_path(self, filename):
        path = assets.get(filename)
        if path and os.path.exists(path):
            return path
        else:
            print(f"Image not found: {filename}, using filename directly")
            return filename

    def on_press(self):
        if self.controller and hasattr(self.controller, 'vibration_manager'):
            self.controller.vibration_manager.button_vibrate()
        
        super().on_press()

    def toggle(self):
        self.is_active = not self.is_active
        self.color = self.active_color if self.is_active else self.normal_color

class MomentaryImageButton(ImageButton):
    def __init__(self, normal_source, active_source=None, press_command=None, release_command=None, **kwargs):
        super().__init__(normal_source, active_source, **kwargs)
        self.press_command = press_command or self.command
        self.release_command = release_command or self.command

    def on_press(self):
        if self.controller and hasattr(self.controller, 'vibration_manager'):
            self.controller.vibration_manager.button_vibrate()
        
        if self.controller and self.press_command:
            self.controller.send_command(self.press_command)
            self.color = self.active_color

    def on_release(self):
        if self.controller and self.release_command:
            self.controller.send_command(self.release_command)
            self.color = self.normal_color

class SteeringWidget(BoxLayout):
    controller = ObjectProperty(None)
    angle = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        steer_source = 'steer.png'
        self.steering_image = RotatableImage(
            source=steer_source,
            allow_stretch=True, 
            keep_ratio=True
        )
        self.add_widget(self.steering_image)
        self.bind(angle=self.update_steering_angle)
        self._touch_down = False
        self._touch_id = None
        self.last_angle = 0
        self.last_vibration_angle = 0
        self.vibration_threshold = 10

    def _get_touch_id(self, touch):
        return getattr(touch, 'id', getattr(touch, 'uid', hash(touch)))

    def update_steering_angle(self, instance, value):
        self.steering_image.angle = value
        
        angle_change = abs(value - self.last_vibration_angle)
        if angle_change > self.vibration_threshold:
            if self.controller and hasattr(self.controller, 'vibration_manager'):
                self.controller.vibration_manager.steering_vibrate(angle_change)
            self.last_vibration_angle = value

    def on_touch_down(self, touch):
        touch_id = self._get_touch_id(touch)
        if self.collide_point(*touch.pos) and not getattr(self.controller, 'accelerometer_mode', False) and not self._touch_down:
            self._touch_down = True
            self._touch_id = touch_id
            return self.process_touch(touch)
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        touch_id = self._get_touch_id(touch)
        if self._touch_down and touch_id == self._touch_id and not getattr(self.controller, 'accelerometer_mode', False):
            return self.process_touch(touch)
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        touch_id = self._get_touch_id(touch)
        if self._touch_down and touch_id == self._touch_id and not getattr(self.controller, 'accelerometer_mode', False):
            self._touch_down = False
            self._touch_id = None
            self.angle = 0
            self.last_angle = 0
            if self.controller:
                self.controller.send_command("S50")
            return True
        return super().on_touch_up(touch)

    def process_touch(self, touch):
        touch_id = self._get_touch_id(touch)
        if not self._touch_down or touch_id != self._touch_id:
            return False
            
        center_x = self.center_x
        center_y = self.center_y
        
        is_bottom_half = touch.y < center_y
        
        relative_x = (touch.x - center_x) / (self.width / 2)
        relative_x = max(-1, min(1, relative_x))
        
        if is_bottom_half:
            relative_x = -relative_x
            
        new_angle = relative_x * 90
        angle_change = abs(new_angle - self.last_angle)
        self.angle = new_angle
        self.last_angle = new_angle
        
        if self.angle >= 0:
            value = 50 + int((self.angle / 90) * 50)
            value = min(100, value)
        else:
            value = 50 + int((self.angle / 90) * 50)
            value = max(0, value)
            
        command = f"S{value:02d}"
        if self.controller:
            self.controller.send_command(command)
        return True

class PedalWidget(BoxLayout):
    controller = ObjectProperty(None)
    pedal_value = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        pedal_source = 'pedal.png'
        self.pedal_image = Image(
            source=pedal_source,
            allow_stretch=True,
            keep_ratio=True
        )
        self.add_widget(self.pedal_image)
        
        with self.canvas.after:
            self.overlay_color = Color(1, 0.2, 0.2, 0)
            self.overlay_rect = Rectangle(pos=self.pos, size=(0, 0))
            
        self.bind(pos=self.update_overlay, size=self.update_overlay, pedal_value=self.update_overlay)
        self._touch_down = False
        self._touch_id = None
        self.last_value = 0
        self.last_vibration_value = 0

    def _get_touch_id(self, touch):
        return getattr(touch, 'id', getattr(touch, 'uid', hash(touch)))

    def update_overlay(self, *args):
        if hasattr(self, 'overlay_color') and hasattr(self, 'overlay_rect'):
            if self.pedal_value > 0:
                overlay_height = self.height * (self.pedal_value / 100.0)
                
                self.overlay_rect.pos = (self.x, self.y)
                self.overlay_rect.size = (self.width, overlay_height)
                
                alpha = 0.3 + (self.pedal_value / 100.0) * 0.45
                self.overlay_color.a = alpha
            else:
                self.overlay_rect.size = (0, 0)
                self.overlay_color.a = 0

    def on_touch_down(self, touch):
        touch_id = self._get_touch_id(touch)
        if self.collide_point(*touch.pos) and not self._touch_down:
            self._touch_down = True
            self._touch_id = touch_id
            
            if self.controller and hasattr(self.controller, 'vibration_manager'):
                self.controller.vibration_manager.pedal_vibrate_dynamic(10, 10)
                
            return self.process_touch(touch)
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        touch_id = self._get_touch_id(touch)
        if self._touch_down and touch_id == self._touch_id:
            return self.process_touch(touch)
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        touch_id = self._get_touch_id(touch)
        if self._touch_down and touch_id == self._touch_id:
            self._touch_down = False
            self._touch_id = None
            self.pedal_value = 0
            self.last_value = 0
            if self.controller:
                self.controller.send_command("G00")
            return True
        return super().on_touch_up(touch)

    def process_touch(self, touch):
        touch_id = self._get_touch_id(touch)
        if not self._touch_down or touch_id != self._touch_id:
            return False
            
        relative_y = (touch.y - self.y) / self.height
        new_value = int(relative_y * 100)
        new_value = max(0, min(100, new_value))
        
        value_change = abs(new_value - self.last_value)
        self.pedal_value = new_value
        
        if self.controller and hasattr(self.controller, 'vibration_manager'):
            self.controller.vibration_manager.pedal_vibrate_dynamic(new_value, value_change)
        
        self.last_value = new_value
            
        command = f"G{self.pedal_value:02d}"
        if self.controller:
            self.controller.send_command(command)
        return True

class CommandLogBox(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = 40
        self.last_command_label = Label(text='--', halign='center', valign='middle')
        self.add_widget(Label(text='Last:', size_hint_x=0.2))
        self.add_widget(self.last_command_label)

    def update_command(self, cmd):
        self.last_command_label.text = cmd

FIGMA_WIDTH = 2340
FIGMA_HEIGHT = 1080

class IPTextInput(TextInput):
    """TextInput سفارشی برای ورود آدرس IP"""
    
    def insert_text(self, substring, from_undo=False):
        # فقط اعداد و نقطه مجاز هستند
        allowed_chars = "0123456789."
        
        # فیلتر کاراکترها - فقط کاراکترهای مجاز را نگه دار
        filtered = ""
        for char in substring:
            if char in allowed_chars:
                filtered += char
        
        # درج متن فیلتر شده
        return super().insert_text(filtered, from_undo=from_undo)
    
    def on_text_validate(self):
        """وقتی کاربر Enter می‌زند، فرمت IP را بررسی کنید"""
        text = self.text.strip()
        
        # اعتبارسنجی آدرس IP
        def is_valid_ip(ip):
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                if not part.isdigit():
                    return False
                if int(part) < 0 or int(part) > 255:
                    return False
            return True
        
        if text and not is_valid_ip(text):
            self.background_color = (1, 0.8, 0.8, 1)  # رنگ قرمز روشن برای خطا
            return False
        
        self.background_color = (1, 1, 1, 1)  # رنگ سفید برای موفقیت
        return True

class CombinedAppRoot(FloatLayout):
    battery_level = StringProperty("85%")
    connected_device = StringProperty("Not Connected")
    connection_status = StringProperty("Disconnected")
    accelerometer_mode = BooleanProperty(False)
    connection_type = StringProperty("ble")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        Window.fullscreen = 'auto'
        Window.borderless = True
        
        sys.excepthook = self.handle_exception
        
        self._in_connection_menu = False
        
        self.connection_manager = ConnectionManager()
        self.connection_manager.main_app = self
        self.connection_manager.set_battery_callback(self.update_battery_level)
        self.accelerometer_manager = AccelerometerManager()
        self.accelerometer_manager.controller = self
        self.vibration_manager = VibrationManager()

        self.connected_sound = None
        self.disconnected_sound = None
        self.signal_lost_sound = None
        self.load_connection_sounds()

        self.current_gear = 'N'
        self.current_turn_signal = None
        self._accelerometer_button_cooldown = False
        self._was_connected = False
        self.signal_check_event = None

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bgrect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.items = [
            ('pedal', 80, 160, 359, 967, 'pedal.png'),
            ('start', 664, 726, 170, 170, 'start.png'),
            ('r', 476, 886, 150, 150, 'r.png'),
            ('n', 477, 736, 150, 150, 'n.png'),
            ('d', 476, 587, 150, 150, 'd.png'),
            ('light', 1506, 544, 150, 150, 'light.png'),
            ('lightHorn', 1480, 721, 150, 150, 'light_horn.png'),
            ('left', 1642, 425, 150, 150, 'left.png'),
            ('hazard', 1842, 350, 150, 150, 'hazard.png'),
            ('horn', 2178, 544, 150, 150, 'horn.png'),
            ('rgb', 1518, 906, 150, 150, 'rgb.png'),
            ('right', 2042, 425, 150, 150, 'right.png'),
            ('bluetooth', 1270, 920, 150, 150, 'bluetooth_wifi.png'),
            ('accelerometer', 2016, 182, 150, 150, 'accelerometer.png'),
            ('battery_title', 1225, 346, 200, 100, ''),
            ('battery_indicator', 1230, 412, 170, 80, ''),
            ('battery_percent', 1235, 412, 170, 80, ''),
            ('command_display', 886, 380, 110, 110, ''),
            ('steer', 1650, 544, 530, 530, 'steer.png'),
            ('setting', 1860, 195, 115, 115, 'setting.png'),
            ('led', 2195, 720, 150, 150, 'led.png'),
            ('device_display', 900, 956, 200, 80, ''),
            ('signal_status', 900, 800, 200, 100, ''),
        ]

        self.command_log = CommandLogBox(pos_hint={'x': 0, 'y': 0})
        self.add_widget(self.command_log)

        Window.bind(size=self.on_window_size)

        self._ui_built = False
        Clock.schedule_once(self._build_ui, 0.5)
        
        Clock.schedule_once(self._load_saved_settings, 1.0)
        
        print("CombinedAppRoot initialized successfully")

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        print("Unhandled exception occurred!")
        traceback.print_exception(exc_type, exc_value, exc_traceback)

    def _update_bg(self, *args):
        self.bgrect.pos = self.pos
        self.bgrect.size = self.size

    def on_window_size(self, instance, value):
        if not self._ui_built:
            return
            
        print(f"Window size changed to: {value}")
        self._update_ui_positions()

    def load_connection_sounds(self):
        try:
            connected_path = assets.get('connected.wav')
            if connected_path:
                self.connected_sound = SoundLoader.load(connected_path)
                if self.connected_sound:
                    print("Connected sound loaded successfully")
            
            disconnected_path = assets.get('disconnected.wav')
            if disconnected_path:
                self.disconnected_sound = SoundLoader.load(disconnected_path)
                if self.disconnected_sound:
                    print("Disconnected sound loaded successfully")
            
            signal_lost_path = assets.get('signal_lost.wav')
            if signal_lost_path:
                self.signal_lost_sound = SoundLoader.load(signal_lost_path)
                if self.signal_lost_sound:
                    print("Signal lost sound loaded successfully")
                    
        except Exception as e:
            print(f"Error loading connection sounds: {e}")
    
    def play_connection_sound_and_vibrate(self):
        if self.connected_sound:
            try:
                self.connected_sound.play()
                print("Playing connection sound")
            except Exception as e:
                print(f"Error playing connection sound: {e}")
        
        if hasattr(self, 'vibration_manager'):
            try:
                self.vibration_manager.connection_vibrate()
                print("Connection vibration triggered")
            except Exception as e:
                print(f"Connection vibration error: {e}")
    
    def play_disconnection_sound_and_vibrate(self):
        if self.disconnected_sound:
            try:
                self.disconnected_sound.play()
                print("Playing disconnection sound")
            except Exception as e:
                print(f"Error playing disconnection sound: {e}")
        
        if hasattr(self, 'vibration_manager'):
            try:
                self.vibration_manager.disconnection_vibrate()
                print("Disconnection vibration triggered")
            except Exception as e:
                print(f"Disconnection vibration error: {e}")
    
    def play_signal_lost_sound_and_vibrate(self):
        if self.signal_lost_sound:
            try:
                self.signal_lost_sound.play()
                print("Playing signal lost sound")
            except Exception as e:
                print(f"Error playing signal lost sound: {e}")
        
        if hasattr(self, 'vibration_manager'):
            try:
                self.vibration_manager.signal_lost_vibrate()
                print("Signal lost vibration triggered")
            except Exception as e:
                print(f"Signal lost vibration error: {e}")

    def on_signal_lost(self):
        if self.connection_manager.connected:
            print("Signal lost - playing sound and vibration")
            self.play_signal_lost_sound_and_vibrate()
            
            self.connection_status = "Signal Lost"
            self.connected_device = "Signal Lost"
            
            self.show_connection_message("Signal lost! Trying to reconnect...", "warning")
            
            self.connection_manager.disconnect()

    def _load_saved_settings(self, dt=None):
        print("Loading saved settings...")
        
        connection_type = get_setting('connection_type', 'ble')
        self.connection_type = connection_type
        self.connection_manager.set_connection_type(connection_type)
        print(f"Connection type loaded: {connection_type}")
        
        sensitivity = get_setting('sensitivity', 1.0)
        self.accelerometer_manager.sensitivity = sensitivity
        print(f"Sensitivity loaded: {sensitivity}")
        
        button_vibration_intensity = get_setting('button_vibration_intensity', 0.5)
        steering_vibration_intensity = get_setting('steering_vibration_intensity', 0.5)
        pedal_min_vibration = get_setting('pedal_min_vibration', 0.1)
        pedal_max_vibration = get_setting('pedal_max_vibration', 1.0)
        
        self.vibration_manager.set_button_intensity(button_vibration_intensity)
        self.vibration_manager.set_steering_intensity(steering_vibration_intensity)
        self.vibration_manager.set_pedal_vibration_range(pedal_min_vibration, pedal_max_vibration)
        
        print(f"Vibration settings loaded")

    def _update_ui_positions(self):
        win_w, win_h = Window.size
        
        target_ratio = FIGMA_WIDTH / FIGMA_HEIGHT
        current_ratio = win_w / win_h
        
        safe_area_top = max(0, win_h * 0.03) if HAS_ANDROID else 0
        safe_area_bottom = max(0, win_h * 0.03) if HAS_ANDROID else 0
        usable_height = win_h - safe_area_top - safe_area_bottom
        
        if current_ratio > target_ratio:
            scale = usable_height / FIGMA_HEIGHT
            margin_x = (win_w - FIGMA_WIDTH * scale) / 2
            margin_y = safe_area_bottom
        else:
            scale = win_w / FIGMA_WIDTH
            margin_x = 0
            margin_y = (win_h - FIGMA_HEIGHT * scale) / 2

        for name, x, y, w, h, src in self.items:
            if name in self.widgets:
                y_corrected = FIGMA_HEIGHT - (y + h)
                x_scaled = x * scale + margin_x
                y_scaled = y_corrected * scale + margin_y
                w_scaled = w * scale
                h_scaled = h * scale
                
                widget = self.widgets[name]
                if hasattr(widget, 'pos'):
                    widget.pos = (x_scaled, y_scaled)
                if hasattr(widget, 'size'):
                    widget.size = (w_scaled, h_scaled)

        cmd_log_width = max(180, win_w * 0.18)
        cmd_log_height = max(35, win_h * 0.045)
        self.command_log.pos = (win_w - cmd_log_width - 10, 10 + safe_area_bottom)
        self.command_log.size = (cmd_log_width, cmd_log_height)

    def update_battery_level(self, level):
        def update_ui(dt):
            self.battery_level = f"{level}%"
            
            if 'battery_indicator' in self.widgets:
                self.widgets['battery_indicator'].level = level
                
        Clock.schedule_once(update_ui, 0)

    def _build_ui(self, dt):
        if self._ui_built:
            return
            
        win_w, win_h = Window.size
        print(f"Building UI for window size: {win_w}x{win_h}")
        
        target_ratio = FIGMA_WIDTH / FIGMA_HEIGHT
        current_ratio = win_w / win_h
        
        safe_area_top = 0
        safe_area_bottom = 0
        
        if HAS_ANDROID:
            safe_area_top = max(0, win_h * 0.03)
            safe_area_bottom = max(0, win_h * 0.03)
        
        usable_height = win_h - safe_area_top - safe_area_bottom
        
        if current_ratio > target_ratio:
            scale = usable_height / FIGMA_HEIGHT
            margin_x = (win_w - FIGMA_WIDTH * scale) / 2
            margin_y = safe_area_bottom
        else:
            scale = win_w / FIGMA_WIDTH
            margin_x = 0
            margin_y = (win_h - FIGMA_HEIGHT * scale) / 2

        self.widgets = {}

        for name, x, y, w, h, src in self.items:
            y_corrected = FIGMA_HEIGHT - (y + h)
            x_scaled = x * scale + margin_x
            y_scaled = y_corrected * scale + margin_y
            w_scaled = w * scale
            h_scaled = h * scale
            pos = (x_scaled, y_scaled)

            try:
                if name == 'battery_title':
                    battery_title_box = BoxLayout(
                        orientation='vertical',
                        size_hint=(None, None),
                        size=(w_scaled, h_scaled),
                        pos=pos
                    )
                    
                    battery_title = Label(
                        text='Battery',
                        size_hint_y=1,
                        font_size='14sp',
                        color=(0, 0, 0, 1),
                        halign='center',
                        valign='middle'
                    )
                    
                    battery_title_box.add_widget(battery_title)
                    self.add_widget(battery_title_box)
                    continue

                if name == 'battery_indicator':
                    battery_indicator = BatteryIndicator(
                        size_hint=(None, None),
                        size=(w_scaled, h_scaled),
                        pos=pos
                    )
                    
                    self.widgets['battery_indicator'] = battery_indicator
                    
                    def update_battery_indicator(instance, battery_text):
                        try:
                            level = int(''.join(filter(str.isdigit, battery_text)))
                            battery_indicator.level = level
                            battery_indicator._update_canvas()
                        except (ValueError, TypeError) as e:
                            print(f"Battery indicator update error: {e}")
                    
                    self.bind(battery_level=update_battery_indicator)
                    
                    battery_indicator.level = 85
                    
                    self.add_widget(battery_indicator)
                    continue

                if name == 'battery_percent':
                    battery_percent_box = BoxLayout(
                        orientation='vertical',
                        size_hint=(None, None),
                        size=(w_scaled, h_scaled),
                        pos=pos
                    )
                    
                    self.battery_percent_label = Label(
                        text=self.battery_level,
                        size_hint_y=1,
                        font_size='14sp',
                        color=(0, 0, 0, 1),
                        halign='center',
                        valign='middle',
                        bold=True
                    )
                    
                    battery_percent_box.add_widget(self.battery_percent_label)
                    self.add_widget(battery_percent_box)
                    
                    def update_battery_percent(instance, battery_text):
                        self.battery_percent_label.text = battery_text
                        try:
                            level = int(''.join(filter(str.isdigit, battery_text)))
                            if level <= 20:
                                self.battery_percent_label.color = (1, 0, 0, 1)
                            elif level <= 60:
                                self.battery_percent_label.color = (1, 0.5, 0, 1)
                            else:
                                self.battery_percent_label.color = (0, 0.5, 0, 1)
                        except (ValueError, TypeError) as e:
                            print(f"Battery percent update error: {e}")
                    
                    self.bind(battery_level=update_battery_percent)
                    continue

                if name == 'steer':
                    size = min(w_scaled, h_scaled)
                    steer = SteeringWidget(
                        size_hint=(None, None),
                        size=(size, size),
                        pos=(x_scaled + (w_scaled - size)/2, y_scaled + (h_scaled - size)/2)
                    )
                    steer.controller = self
                    self.add_widget(steer)
                    self.widgets['steer'] = steer
                    continue

                if name == 'pedal':
                    pedal = PedalWidget(
                        size_hint=(None, None),
                        size=(w_scaled, h_scaled),
                        pos=pos
                    )
                    pedal.controller = self
                    self.add_widget(pedal)
                    self.widgets['pedal'] = pedal
                    continue

                if name in ('n', 'r', 'd'):
                    btn = ImageButton(normal_source=src)
                    btn.controller = self
                    btn.command = name.upper()
                    btn.size_hint = (None, None)
                    btn.size = (w_scaled, h_scaled)
                    btn.pos = pos
                    btn.bind(on_press=self._on_gear_pressed)
                    
                    if name == 'n':
                        btn.is_active = True
                        btn.color = btn.active_color
                        self.current_gear = 'N'
                    else:
                        btn.is_active = False
                        btn.color = btn.normal_color
                        
                    self.add_widget(btn)
                    self.widgets[name] = btn
                    continue

                if name == 'bluetooth':
                    btn = ImageButton(normal_source=src)
                    btn.controller = self
                    btn.command = "BT"
                    btn.size_hint = (None, None)
                    btn.size = (w_scaled, h_scaled)
                    btn.pos = pos
                    
                    def safe_show_connection(instance):
                        try:
                            self.show_connection_devices()
                        except Exception as e:
                            print(f"Bluetooth button error: {e}")
                            import traceback
                            traceback.print_exc()
                            self.show_connection_message(f"Menu error: {str(e)}", "error")
                    
                    btn.bind(on_press=safe_show_connection)
                    self.add_widget(btn)
                    self.widgets['bluetooth'] = btn
                    continue

                if name == 'accelerometer':
                    btn = ImageButton(normal_source=src)
                    btn.controller = self
                    btn.command = "ACC"
                    btn.size_hint = (None, None)
                    btn.size = (w_scaled, h_scaled)
                    btn.pos = pos
                    btn.bind(on_press=self.on_accelerometer_toggle)
                    btn.is_active = False
                    btn.color = btn.normal_color
                    self.add_widget(btn)
                    self.widgets['accelerometer'] = btn
                    continue

                if name == 'setting':
                    btn = ImageButton(normal_source=src)
                    btn.controller = self
                    btn.size_hint = (None, None)
                    btn.size = (w_scaled, h_scaled)
                    btn.pos = pos
                    btn.bind(on_press=lambda inst: self.show_settings_menu())
                    self.add_widget(btn)
                    self.widgets['setting'] = btn
                    continue

                if name == 'command_display':
                    cmd_box = BoxLayout(
                        orientation='vertical',
                        size_hint=(None, None),
                        size=(w_scaled, h_scaled),
                        pos=pos
                    )
                    title_label = Label(
                        text='Last Command',
                        size_hint_y=0.3,
                        font_size='14sp',
                        color=(0, 0, 0, 1)
                    )
                    self.last_cmd_label = Label(
                        text='--',
                        size_hint_y=0.7,
                        font_size='14sp',
                        color=(0, 0.5, 0, 1)
                    )
                    
                    cmd_box.add_widget(title_label)
                    cmd_box.add_widget(self.last_cmd_label)
                    self.add_widget(cmd_box)
                    self.widgets['command_display'] = cmd_box
                    continue

                if name == 'device_display':
                    device_box = BoxLayout(
                        orientation='vertical',
                        size_hint=(None, None),
                        size=(w_scaled, h_scaled),
                        pos=pos
                    )
                    device_title = Label(
                        text='Device',
                        size_hint_y=0.3,
                        font_size='14sp',
                        color=(0, 0, 0, 1)
                    )
                    self.device_name_label = Label(
                        text='Not Connected',
                        size_hint_y=0.7,
                        font_size='14sp',
                        color=(0.2, 0.2, 0.8, 1)
                    )
                    
                    device_box.add_widget(device_title)
                    device_box.add_widget(self.device_name_label)
                    self.add_widget(device_box)
                    self.widgets['device_display'] = device_box
                    
                    self.bind(connected_device=lambda inst, val: setattr(self.device_name_label, 'text', val))
                    continue

                if name == 'signal_status':
                    signal_box = BoxLayout(
                        orientation='vertical',
                        size_hint=(None, None),
                        size=(w_scaled, h_scaled),
                        pos=pos,
                        spacing=15
                    )
                    signal_title = Label(
                        text='Signal',
                        size_hint_y=0.4,
                        font_size='12sp',
                        color=(0, 0, 0, 1),
                        padding=(0, 10, 0, 0)
                    )
                    self.signal_status_label = Label(
                        text='No Signal',
                        size_hint_y=0.6,
                        font_size='14sp',
                        color=(1, 0, 0, 1),
                        bold=True,
                        padding=(0, 0, 0, 10)
                    )
                    
                    signal_box.add_widget(signal_title)
                    signal_box.add_widget(self.signal_status_label)
                    self.add_widget(signal_box)
                    self.widgets['signal_status'] = signal_box
                    continue

                if name in ('left', 'right', 'hazard'):
                    cmd_map = {
                        'left': 'LTL', 'right': 'RTL', 'hazard': 'ALL'
                    }
                    cmd = cmd_map.get(name, name.upper())
                    btn = ImageButton(normal_source=src)
                    btn.controller = self
                    btn.command = cmd
                    btn.size_hint = (None, None)
                    btn.size = (w_scaled, h_scaled)
                    btn.pos = pos
                    btn.bind(on_press=self._on_turn_signal_pressed)
                    self.add_widget(btn)
                    self.widgets[name] = btn
                    continue

                if name in ('light', 'led', 'rgb', 'start'):
                    cmd_map = {
                        'light': 'LIT', 'led': 'LED', 'rgb': 'RGB', 
                        'start': 'STA'
                    }
                    cmd = cmd_map.get(name, name.upper())
                    btn = ImageButton(normal_source=src)
                    btn.controller = self
                    btn.command = cmd
                    btn.size_hint = (None, None)
                    btn.size = (w_scaled, h_scaled)
                    btn.pos = pos
                    btn.bind(on_press=self._on_toggle_control)
                    self.add_widget(btn)
                    self.widgets[name] = btn
                    continue

                if name == 'horn':
                    btn = MomentaryImageButton(
                        normal_source=src,
                        press_command='HOR',
                        release_command='HOF'
                    )
                    btn.controller = self
                    btn.size_hint = (None, None)
                    btn.size = (w_scaled, h_scaled)
                    btn.pos = pos
                    self.add_widget(btn)
                    self.widgets[name] = btn
                    continue

                if name == 'lightHorn':
                    btn = MomentaryImageButton(
                        normal_source=src,
                        press_command='LHO',
                        release_command='LHO'
                    )
                    btn.controller = self
                    btn.size_hint = (None, None)
                    btn.size = (w_scaled, h_scaled)
                    btn.pos = pos
                    self.add_widget(btn)
                    self.widgets[name] = btn
                    continue

                img_path = assets.get(src)
                if img_path and os.path.exists(img_path):
                    img = Image(
                        source=img_path,
                        size_hint=(None, None),
                        size=(w_scaled, h_scaled),
                        pos=pos,
                        allow_stretch=True,
                        keep_ratio=False
                    )
                    self.add_widget(img)
                    self.widgets[name] = img

            except Exception as e:
                print(f"Error placing {name}: {e}")

        cmd_log_width = max(180, win_w * 0.18)
        cmd_log_height = max(35, win_h * 0.045)
        self.command_log.pos = (win_w - cmd_log_width - 10, 10 + safe_area_bottom)
        self.command_log.size = (cmd_log_width, cmd_log_height)
        
        Clock.schedule_interval(self.check_connection_status, 2.0)
        self._was_connected = False
        
        self._ui_built = True
        print(f"UI built successfully for {win_w}x{win_h}")

    def check_connection_status(self, dt):
        if self._in_connection_menu:
            return
        
        if hasattr(self, 'connection_manager'):
            was_connected = getattr(self, '_was_connected', False)
            is_connected = self.connection_manager.connected
            
            if was_connected and not is_connected:
                print("Connection lost automatically")
                self.play_disconnection_sound_and_vibrate()
                self.connection_status = "Disconnected"
                self.connected_device = "Not Connected"
                self.signal_status_label.text = "No Signal"
                self.signal_status_label.color = (1, 0, 0, 1)
            
            self._was_connected = is_connected

    def send_command(self, command):
        print(f"Sending via {self.connection_type.upper()}: {command}")
        ok = self.connection_manager.send_command(command)
        self.command_log.update_command(command)
        
        if hasattr(self, 'last_cmd_label'):
            self.last_cmd_label.text = command
            
        return ok

    def _on_gear_pressed(self, instance):
        for key in ('n', 'r', 'd'):
            w = self.widgets.get(key)
            if isinstance(w, ImageButton) and w is not instance:
                w.is_active = False
                w.color = w.normal_color
                
        instance.is_active = True
        instance.color = instance.active_color
        self.current_gear = instance.command
        self.send_command(instance.command)
        print(f"Gear changed to: {instance.command}")

    def _on_turn_signal_pressed(self, instance):
        turn_signal_buttons = ['left', 'right', 'hazard']
        
        if instance.is_active:
            instance.is_active = False
            instance.color = instance.normal_color
            self.current_turn_signal = None
            self.send_command(instance.command)
            print(f"{instance.command} turned OFF")
        else:
            for signal_name in turn_signal_buttons:
                btn = self.widgets.get(signal_name)
                if btn and isinstance(btn, ImageButton) and btn is not instance:
                    btn.is_active = False
                    btn.color = btn.normal_color
            
            instance.is_active = True
            instance.color = instance.active_color
            self.current_turn_signal = instance.command
            self.send_command(instance.command)
            print(f"{instance.command} turned ON")

    def _on_toggle_control(self, instance):
        instance.toggle()
        self.send_command(instance.command)

    def on_accelerometer_toggle(self, instance):
        if self._accelerometer_button_cooldown:
            print("Accelerometer button cooldown - please wait")
            return
            
        self._accelerometer_button_cooldown = True
        Clock.schedule_once(lambda dt: setattr(self, '_accelerometer_button_cooldown', False), 1.0)
        
        try:
            if not self.accelerometer_mode:
                print("Activating accelerometer...")
                # بررسی قبل از فعال‌سازی
                if not hasattr(self, 'accelerometer_manager') or self.accelerometer_manager is None:
                    print("Accelerometer manager not available")
                    self.show_connection_message("Accelerometer not available", "error")
                    return
                    
                success = self.accelerometer_manager.start()
                
                if success:
                    self.accelerometer_mode = True
                    instance.is_active = True
                    instance.color = instance.active_color
                    self.send_command('ACC1')
                    print("Accelerometer activated - Tilt device to steer")
                    
                    steer_widget = self.widgets.get('steer')
                    if steer_widget:
                        steer_widget._touch_down = False
                        steer_widget._touch_id = None
                else:
                    self.accelerometer_mode = False
                    instance.is_active = False
                    instance.color = instance.normal_color
                    print("Failed to activate accelerometer")
                    self.show_connection_message("Accelerometer not available", "error")
            else:
                print("Deactivating accelerometer...")
                # بررسی قبل از غیرفعال‌سازی
                if not hasattr(self, 'accelerometer_manager') or self.accelerometer_manager is None:
                    print("Accelerometer manager not available")
                    self.accelerometer_mode = False
                    instance.is_active = False
                    instance.color = instance.normal_color
                    return
                    
                success = self.accelerometer_manager.stop()
                
                if success:
                    self.accelerometer_mode = False
                    instance.is_active = False
                    instance.color = instance.normal_color
                    self.send_command('ACC0')
                    
                    steer_widget = self.widgets.get('steer')
                    if steer_widget:
                        steer_widget.angle = 0
                        steer_widget.last_angle = 0
                    self.send_command("S50")
                    print("Accelerometer deactivated")
                else:
                    print("Accelerometer deactivation may have had issues")
                    # حتی اگر stop کامل نبود، وضعیت UI را به‌روزرسانی کن
                    self.accelerometer_mode = False
                    instance.is_active = False
                    instance.color = instance.normal_color
                    self.send_command('ACC0')
                    
        except Exception as e:
            print(f"Accelerometer toggle error: {e}")
            self.accelerometer_mode = False
            instance.is_active = False
            instance.color = instance.normal_color
            self.show_connection_message(f"Accelerometer error: {str(e)}", "error")

    def update_steering_from_accelerometer(self, angle):
        if self.accelerometer_mode:
            Clock.schedule_once(lambda dt: self._update_steer_angle(angle))

    def _update_steer_angle(self, angle):
        w = self.widgets.get('steer')
        if w:
            w.angle = angle
            
        if angle >= 0:
            value = 50 + int((angle / 90) * 50)
            value = min(100, value)
        else:
            value = 50 + int((angle / 90) * 50)
            value = max(0, value)
            
        self.send_command(f"S{value:02d}")

    def validate_ip_address(self, ip):
        """اعتبارسنجی آدرس IP"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                if not part.isdigit():
                    return False
                num = int(part)
                if num < 0 or num > 255:
                    return False
            return True
        except:
            return False

    def show_wifi_password_dialog(self, ssid):
        """نمایش دیالوگ برای وارد کردن رمز WiFi"""
        try:
            content = BoxLayout(orientation='vertical', spacing=15, padding=25)
            
            title = Label(
                text=f'Connect to:\n{ssid}',
                size_hint_y=0.15,
                font_size='18sp',
                bold=True,
                color=(0.2, 0.4, 0.8, 1),
                halign='center'
            )
            content.add_widget(title)
            
            # ورودی رمز عبور
            password_layout = BoxLayout(orientation='vertical', size_hint_y=0.3, spacing=10)
            password_label = Label(
                text='WiFi Password:',
                size_hint_y=0.4,
                font_size='16sp',
                halign='left'
            )
            password_label.bind(size=password_label.setter('text_size'))
            
            self.password_input = TextInput(
                multiline=False,
                size_hint_y=0.6,
                font_size='16sp',
                hint_text='Enter WiFi password',
                password=True,  # مخفی کردن رمز
                padding=(10, 10),
                background_color=(1, 1, 1, 1),
                foreground_color=(0, 0, 0, 1)
            )
            password_layout.add_widget(password_label)
            password_layout.add_widget(self.password_input)
            content.add_widget(password_layout)
            
            # ورودی IP ربات
            ip_layout = BoxLayout(orientation='horizontal', size_hint_y=0.2, spacing=10)
            ip_label = Label(
                text='Car IP:',
                size_hint_x=0.3,
                font_size='16sp',
                halign='right'
            )
            ip_label.bind(size=ip_label.setter('text_size'))
            
            self.car_ip_input = TextInput(
                text='192.168.4.1',
                multiline=False,
                size_hint_x=0.7,
                font_size='16sp',
                hint_text='192.168.4.1',
                padding=(10, 10),
                background_color=(1, 1, 1, 1),
                foreground_color=(0, 0, 0, 1)
            )
            ip_layout.add_widget(ip_label)
            ip_layout.add_widget(self.car_ip_input)
            content.add_widget(ip_layout)
            
            # دکمه‌ها
            btn_layout = BoxLayout(orientation='horizontal', size_hint_y=0.2, spacing=15)
            
            connect_btn = Button(
                text='Connect',
                size_hint_x=0.6,
                font_size='16sp',
                background_color=(0.2, 0.7, 0.3, 1),
                color=(1, 1, 1, 1)
            )
            
            def on_connect(instance):
                password = self.password_input.text.strip()
                car_ip = self.car_ip_input.text.strip()
                
                if not password:
                    self.show_connection_message("Please enter WiFi password", "error")
                    return
                
                if not self.validate_ip_address(car_ip):
                    self.show_connection_message("Invalid car IP address", "error")
                    return
                
                popup.dismiss()
                
                # اتصال خودکار با رمز
                success = self.connection_manager.wifi.connect_with_password(
                    ssid=ssid,
                    password=password,
                    ip=car_ip,
                    port=80
                )
                
                if success:
                    self.show_connection_message(
                        f"Connecting to {ssid}...\nPlease wait", 
                        "info"
                    )
                else:
                    self.show_connection_message("Connection failed", "error")
            
            connect_btn.bind(on_press=on_connect)
            
            cancel_btn = Button(
                text='Cancel',
                size_hint_x=0.4,
                font_size='16sp',
                background_color=(0.8, 0.2, 0.2, 1)
            )
            cancel_btn.bind(on_press=lambda x: popup.dismiss())
            
            btn_layout.add_widget(connect_btn)
            btn_layout.add_widget(cancel_btn)
            content.add_widget(btn_layout)
            
            popup = Popup(
                title='WiFi Connection',
                content=content,
                size_hint=(0.85, 0.6),
                auto_dismiss=False
            )
            
            popup.open()
            
        except Exception as e:
            print(f"Error showing WiFi password dialog: {e}")
            self.show_connection_message(f"Error: {str(e)}", "error")

    def show_wifi_history_manager(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=20)
        
        content.add_widget(Label(
            text='WiFi Connection History',
            size_hint_y=0.1,
            font_size='18sp',
            bold=True
        ))
        
        saved_connections = []
        try:
            app = App.get_running_app()
            if hasattr(app, 'settings_manager'):
                saved_connections = app.settings_manager.get_saved_wifi_connections()
        except Exception as e:
            print(f"Error loading connections: {e}")
        
        scroll = ScrollView(size_hint=(1, 0.7))
        list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        list_layout.bind(minimum_height=list_layout.setter('height'))
        
        if saved_connections:
            for conn in saved_connections:
                item = BoxLayout(
                    orientation='horizontal',
                    size_hint_y=None,
                    height=70,
                    spacing=10
                )
                
                info_label = Label(
                    text=f'[b]{conn.get("name", "RC Car")}[/b]\n{conn.get("ip")}:{conn.get("port")}',
                    size_hint_x=0.7,
                    markup=True,
                    halign='left',
                    valign='middle'
                )
                
                connect_btn = Button(
                    text='Connect',
                    size_hint_x=0.15,
                    font_size='12sp',
                    background_color=(0.2, 0.8, 0.2, 1)
                )
                
                def create_connect_callback(ip, port):
                    def callback(instance):
                        popup.dismiss()
                        self.connection_manager.wifi.connect_manually(ip, port)
                    return callback
                
                connect_btn.bind(on_press=create_connect_callback(
                    conn.get('ip'), 
                    conn.get('port')
                ))
                
                delete_btn = Button(
                    text='Delete',
                    size_hint_x=0.15,
                    font_size='12sp',
                    background_color=(0.8, 0.2, 0.2, 1)
                )
                
                def create_delete_callback(ip, port):
                    def callback(instance):
                        app.settings_manager.remove_wifi_connection(ip, port)
                        
                        popup.dismiss()
                        self.show_wifi_history_manager()
                    return callback
                
                delete_btn.bind(on_press=create_delete_callback(
                    conn.get('ip'), 
                    conn.get('port')
                ))
                
                item.add_widget(info_label)
                item.add_widget(connect_btn)
                item.add_widget(delete_btn)
                list_layout.add_widget(item)
        else:
            list_layout.add_widget(Label(
                text='No saved connections yet.',
                size_hint_y=None,
                height=60,
                font_size='14sp',
                color=(0.5, 0.5, 0.5, 1)
            ))
        
        scroll.add_widget(list_layout)
        content.add_widget(scroll)
        
        btn_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        
        clear_all_btn = Button(
            text='Clear All History',
            size_hint_x=0.5,
            background_color=(0.8, 0.2, 0.2, 1)
        )
        
        def clear_all_history(instance):
            app.settings_manager.clear_wifi_history()
            popup.dismiss()
            self.show_connection_message("All WiFi history cleared", "info")
        
        clear_all_btn.bind(on_press=clear_all_history)
        
        close_btn = Button(
            text='Close',
            size_hint_x=0.5
        )
        
        close_btn.bind(on_press=lambda x: popup.dismiss())
        
        btn_layout.add_widget(clear_all_btn)
        btn_layout.add_widget(close_btn)
        content.add_widget(btn_layout)
        
        popup = Popup(
            title='WiFi History',
            content=content,
            size_hint=(0.85, 0.8)
        )
        
        popup.open()

    def _on_wifi_selected(self, instance, network_info):
        """هنگام انتخاب شبکه WiFi"""
        try:
            print(f"WiFi network selected: {network_info}")
            
            if any(keyword in network_info for keyword in ["Scanning", "No WiFi", "Permissions", "WiFi is disabled"]):
                return
            
            # استخراج SSID به صورت خودکار
            ssid = self.connection_manager.wifi.extract_ssid_from_network_info(network_info)
            
            if not ssid:
                self.show_connection_message("Could not extract SSID", "error")
                return
            
            if hasattr(self, 'conn_popup'):
                self.conn_popup.dismiss()
                self._in_connection_menu = False
            
            # بررسی آیا شبکه رمزدار است
            if self.connection_manager.wifi._is_protected_network(network_info):
                # نمایش دیالوگ برای وارد کردن رمز
                self.show_wifi_password_dialog(ssid)
            else:
                # شبکه باز - اتصال مستقیم
                success = self.connection_manager.wifi.connect_with_password(
                    ssid=ssid,
                    password=None,
                    ip="192.168.4.1",
                    port=80
                )
                
                if not success:
                    self.show_connection_message("Failed to connect to open network", "error")
                    
        except Exception as e:
            print(f"WiFi selection error: {e}")
            self.show_connection_message(f"Selection error: {str(e)}", "error")

    def on_scan_results(self, devices):
        try:
            print(f"Scan results received: {len(devices)} devices")
            Clock.schedule_once(lambda dt: self._update_device_list(devices))
        except Exception as e:
            print(f"Error in on_scan_results: {e}")

    def _update_device_list(self, devices):
        try:
            if not hasattr(self, 'device_list'):
                print("device_list not available for update")
                return
                
            self.device_list.clear_widgets()
            
            if not devices:
                no_devices = Label(
                    text=f'No {self.connection_type.upper()} devices found', 
                    size_hint_y=None, 
                    height=200, 
                    halign='center',
                    font_size='16sp'
                )
                no_devices.bind(size=no_devices.setter('text_size'))
                self.device_list.add_widget(no_devices)
                
                scan_again_btn = Button(
                    text='Scan Again',
                    size_hint_y=None,
                    height=80,
                    font_size='16sp',
                    background_color=(0.2, 0.7, 0.3, 1)
                )
                
                def scan_again(instance):
                    loading = Label(
                        text=f'Scanning for {self.connection_type.upper()} devices...', 
                        size_hint_y=None, 
                        height=60, 
                        font_size='16sp'
                    )
                    self.device_list.clear_widgets()
                    self.device_list.add_widget(loading)
                    
                    def start_scan():
                        try:
                            if self.connection_type == 'wifi':
                                result = self.connection_manager.wifi.scanner.start_scan(self.on_scan_results)
                            else:
                                result = self.connection_manager.start_scan(self.on_scan_results)
                            print(f"Rescan started for {self.connection_type}: {result}")
                        except Exception as e:
                            print(f"Rescan start error for {self.connection_type}: {e}")
                            Clock.schedule_once(lambda dt: self._update_device_list([f"Scan error: {str(e)}"]))
                    
                    Clock.schedule_once(lambda dt: start_scan(), 0.1)
                
                scan_again_btn.bind(on_press=scan_again)
                self.device_list.add_widget(scan_again_btn)
                return
                
            for dev in devices:
                try:
                    btn = Button(
                        text=str(dev), 
                        size_hint_y=None, 
                        height=70,
                        text_size=(None, None),
                        halign='left',
                        valign='middle',
                        font_size='14sp',
                        padding=(10, 0)
                    )
                    
                    btn.bind(on_press=lambda instance, addr=dev: self._on_device_selected(instance, addr))
                    self.device_list.add_widget(btn)
                    
                except Exception as e:
                    print(f"Error adding device button: {e}")
            
            # اضافه کردن دکمه Scan Again در انتهای لیست
            scan_again_btn = Button(
                text='Scan Again',
                size_hint_y=None,
                height=80,
                font_size='16sp',
                background_color=(0.2, 0.7, 0.3, 1)
            )
            
            def scan_again(instance):
                loading = Label(
                    text=f'Scanning for {self.connection_type.upper()} devices...', 
                    size_hint_y=None, 
                    height=60, 
                    font_size='16sp'
                )
                self.device_list.clear_widgets()
                self.device_list.add_widget(loading)
                
                def start_scan():
                    try:
                        if self.connection_type == 'wifi':
                            result = self.connection_manager.wifi.scanner.start_scan(self.on_scan_results)
                        else:
                            result = self.connection_manager.start_scan(self.on_scan_results)
                        print(f"Rescan started for {self.connection_type}: {result}")
                    except Exception as e:
                        print(f"Rescan start error for {self.connection_type}: {e}")
                        Clock.schedule_once(lambda dt: self._update_device_list([f"Scan error: {str(e)}"]))
                
                Clock.schedule_once(lambda dt: start_scan(), 0.1)
            
            scan_again_btn.bind(on_press=scan_again)
            self.device_list.add_widget(scan_again_btn)
                    
        except Exception as e:
            print(f"Error in _update_device_list: {e}")

    def _on_device_selected(self, instance, addr):
        try:
            print(f"{self.connection_type.upper()} Device selected: {addr}")
            
            if self.connection_type == 'wifi':
                # برای WiFi، از SSID استخراج شده استفاده کن
                return self._on_wifi_selected(instance, addr)
            
            self._connect_and_close(addr)
            
        except Exception as e:
            print(f"Error in device selection: {e}")
            self.show_connection_message(f"Selection error: {str(e)}", "error")

    def _connect_and_close(self, addr):
        try:
            print(f"Connecting to: {addr} via {self.connection_type.upper()}")
            
            if hasattr(self, 'conn_popup'):
                self.conn_popup.dismiss()
                self._in_connection_menu = False
            
            self.connection_status = f"Connecting via {self.connection_type.upper()}..."
            self.connected_device = f"Connecting: {addr.split(' ')[0]}"
            
            success = self.connection_manager.connect(addr)
            
            if success:
                self.connection_status = "Connected"
                status_suffix = {
                    'ble': '(BLE)',
                    'classic': '(Classic BT)', 
                    'wifi': '(WiFi)'
                }
                self.connection_status = f"Connected {status_suffix.get(self.connection_type, '')}"
                self.connected_device = f"Connected: {addr.split(' ')[0]}"
                
                if hasattr(self, 'signal_status_label'):
                    self.signal_status_label.text = "Strong Signal"
                    self.signal_status_label.color = (0, 0.8, 0, 1)
                
                print(f"Connected to: {addr} via {self.connection_type.upper()}")
                
                self.play_connection_sound_and_vibrate()
                self.show_connection_message(
                    f"Connected successfully via {self.connection_type.upper()}!", 
                    "success"
                )
            else:
                self.connection_status = "Connection Failed"
                self.connected_device = "Not Connected"
                print(f"Failed to connect to: {addr} via {self.connection_type.upper()}")
                self.show_connection_message(
                    f"Connection failed via {self.connection_type.upper()}!", 
                    "error"
                )
                
        except Exception as e:
            print(f"Error in _connect_and_close: {e}")
            self.show_connection_message(f"Connection error: {str(e)}", "error")

    def disconnect_device(self):
        if self.connection_manager.connected:
            print("Disconnecting device...")
            
            self.play_disconnection_sound_and_vibrate()
            
            self.connection_manager.disconnect()
            
            self.connection_status = "Disconnected"
            self.connected_device = "Not Connected"
            self.battery_level = "85%"
            if hasattr(self, 'signal_status_label'):
                self.signal_status_label.text = "No Signal"
                self.signal_status_label.color = (1, 0, 0, 1)
            
            print("Device disconnected")
        else:
            print("No device connected to disconnect")

    def show_connection_message(self, message, msg_type):
        try:
            content = BoxLayout(orientation='vertical', spacing=15, padding=25)
            
            color = (0, 0.7, 0, 1) if msg_type == "success" else (1, 0, 0, 1) if msg_type == "error" else (1, 0.5, 0, 1)
            
            message_label = Label(
                text=message,
                text_size=(350, None),
                halign='center',
                valign='middle',
                font_size='16sp',
                color=color
            )
            message_label.bind(size=message_label.setter('text_size'))
            content.add_widget(message_label)
            
            ok_btn_layout = BoxLayout(size_hint_y=1, size_hint_x=1, padding=(50, 0))
            close_btn = Button(
                text='OK',
                size_hint_x=0.6,
                background_color=color,
                color=(1, 1, 1, 1),
                font_size='16sp'
            )
            
            popup = Popup(
                title='Connection Status',
                content=content,
                size_hint=(0.75, 0.4),
                auto_dismiss=False
            )
            
            close_btn.bind(on_press=popup.dismiss)
            ok_btn_layout.add_widget(close_btn)
            content.add_widget(ok_btn_layout)
            
            popup.open()
        except Exception as e:
            print(f"Error showing connection message: {e}")

    def show_connection_devices(self, instance=None):
        try:
            print("Opening connection devices popup")
            
            self._in_connection_menu = True
            
            content = BoxLayout(orientation='vertical', spacing=10, padding=10)
            
            type_layout = BoxLayout(orientation='horizontal', size_hint_y=0.15, spacing=10)
            type_label = Label(text='Connection Type:', size_hint_x=0.4, font_size='16sp')
            
            type_selector = BoxLayout(orientation='horizontal', size_hint_x=0.6, spacing=5)
            
            connection_types = [
                ('BLE', 'ble'),
                ('Classic', 'classic'), 
                ('WiFi', 'wifi')
            ]
            
            buttons = []
            for text, conn_type in connection_types:
                btn = ToggleButton(
                    text=text, 
                    group='conn_type',
                    state='down' if self.connection_type == conn_type else 'normal',
                    size_hint_x=0.33
                )
                buttons.append((btn, conn_type))
                type_selector.add_widget(btn)
            
            type_layout.add_widget(type_label)
            type_layout.add_widget(type_selector)
            content.add_widget(type_layout)
            
            self.conn_title = Label(
                text=f'{self.connection_type.upper()} Connection', 
                size_hint_y=0.1, 
                font_size='18sp'
            )
            content.add_widget(self.conn_title)
            
            self.dynamic_content = BoxLayout(orientation='vertical', size_hint_y=0.7)
            content.add_widget(self.dynamic_content)
            
            def update_dynamic_content(conn_type):
                self.dynamic_content.clear_widgets()
                
                if conn_type == 'wifi':
                    wifi_layout = BoxLayout(orientation='vertical', size_hint_y=1, spacing=15, padding=10)
                    
                    wifi_title = Label(
                        text='Available WiFi Networks',
                        size_hint_y=0.1,
                        font_size='16sp',
                        bold=True
                    )
                    wifi_layout.add_widget(wifi_title)
                    
                    # ایجاد لیست برای WiFi
                    self.device_list = BoxLayout(orientation='vertical', size_hint_y=0.9, spacing=5)
                    self.device_list.bind(minimum_height=self.device_list.setter('height'))
                    
                    scroll = ScrollView(size_hint=(1, 1))
                    scroll.add_widget(self.device_list)
                    wifi_layout.add_widget(scroll)
                    
                    # نمایش پیام اسکن
                    loading = Label(
                        text='Scanning for WiFi networks...',
                        size_hint_y=None,
                        height=60,
                        font_size='14sp'
                    )
                    self.device_list.add_widget(loading)
                    
                    # اسکن WiFi
                    def start_wifi_scan():
                        try:
                            result = self.connection_manager.wifi.scanner.start_scan(self.on_scan_results)
                            print(f"WiFi scan started: {result}")
                        except Exception as e:
                            print(f"WiFi scan start error: {e}")
                            Clock.schedule_once(lambda dt: self._update_device_list([f"Scan error: {str(e)}"]))
                    
                    Clock.schedule_once(lambda dt: start_wifi_scan(), 0.1)
                    
                    self.dynamic_content.add_widget(wifi_layout)
                    
                else:
                    # کد قبلی برای BLE و Classic Bluetooth
                    self.device_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
                    self.device_list.bind(minimum_height=self.device_list.setter('height'))
                    
                    scroll = ScrollView(size_hint=(1, 1))
                    scroll.add_widget(self.device_list)
                    self.dynamic_content.add_widget(scroll)
                    
                    loading = Label(
                        text=f'Scanning for {conn_type.upper()} devices...', 
                        size_hint_y=None, 
                        height=60, 
                        font_size='16sp'
                    )
                    self.device_list.add_widget(loading)
                    
                    def start_scan():
                        try:
                            result = self.connection_manager.start_scan(self.on_scan_results)
                            print(f"Scan started for {conn_type}: {result}")
                        except Exception as e:
                            print(f"Scan start error for {conn_type}: {e}")
                            Clock.schedule_once(lambda dt: self._update_device_list([f"Scan error: {str(e)}"]))
                    
                    Clock.schedule_once(lambda dt: start_scan(), 0.1)
            
            def on_connection_type_change(instance):
                try:
                    for btn, conn_type in buttons:
                        if btn.state == 'down':
                            self.connection_type = conn_type
                            self.connection_manager.set_connection_type(conn_type)
                            if hasattr(self, 'conn_title'):
                                self.conn_title.text = f'{btn.text} Connection'
                            
                            update_dynamic_content(conn_type)
                            print(f"Connection type changed to: {conn_type}")
                            break
                except Exception as e:
                    print(f"Error in connection type change: {e}")
        
            for btn, _ in buttons:
                btn.bind(on_press=on_connection_type_change)
        
            update_dynamic_content(self.connection_type)
                    
            btns = BoxLayout(size_hint_y=0.15, spacing=10)
            
            disconnect_btn = Button(
                text='Disconnect',
                size_hint_x=0.5,
                font_size='16sp',
                background_color=(0.9, 0.3, 0.3, 1)
            )
            
            def on_disconnect_press(instance):
                try:
                    if self.connection_manager.connected:
                        self.disconnect_device()
                        if hasattr(self, 'conn_popup'):
                            self.conn_popup.dismiss()
                        self.show_connection_message("Device disconnected successfully!", "success")
                    else:
                        self.show_connection_message("No device is connected!", "warning")
                except Exception as e:
                    print(f"Disconnect error: {e}")
        
            disconnect_btn.bind(on_press=on_disconnect_press)
            
            close_btn = Button(
                text='Close', 
                size_hint_x=0.5,
                font_size='16sp'
            )
            
            popup = Popup(
                title='Connection', 
                content=content, 
                size_hint=(0.9, 0.8),
                auto_dismiss=False
            )
            
            def on_close_press(instance):
                try:
                    popup.dismiss()
                    self._in_connection_menu = False
                    print("Connection popup closed")
                except Exception as e:
                    print(f"Close popup error: {e}")
        
            close_btn.bind(on_press=on_close_press)
            
            btns.add_widget(disconnect_btn)
            btns.add_widget(close_btn)
            content.add_widget(btns)
            
            self.conn_popup = popup
            popup.open()
            
            print("Connection popup opened successfully")
            
        except Exception as e:
            print(f"Critical error in show_connection_devices: {e}")
            import traceback
            traceback.print_exc()
            self.show_connection_message(f"Error opening connection menu: {str(e)}", "error")

    def show_settings_menu(self):
        try:
            saved_sensitivity = get_setting('sensitivity', 1.0)
            battery_warning = get_setting('battery_warning_level', 30)
            button_vibration_intensity = get_setting('button_vibration_intensity', 0.5)
            steering_vibration_intensity = get_setting('steering_vibration_intensity', 0.5)
            vibration_enabled = get_setting('vibration_enabled', False)
            pedal_min_vibration = get_setting('pedal_min_vibration', 0.1)
            pedal_max_vibration = get_setting('pedal_max_vibration', 1.0)
            
            content = BoxLayout(orientation='vertical', spacing=12, padding=15)
            content.add_widget(Label(text='Settings', size_hint_y=0.08, font_size='20sp', bold=True))
            
            main_layout = BoxLayout(orientation='horizontal', spacing=15, size_hint_y=0.8)
            
            left_column = BoxLayout(orientation='vertical', spacing=10, size_hint_x=0.5)
            vibration_title = Label(
                text='Vibration Settings', 
                size_hint_y=0.1, 
                font_size='16sp',
                bold=True,
                color=(0.2, 0.4, 0.8, 1)
            )
            left_column.add_widget(vibration_title)
            
            vibration_toggle_layout = BoxLayout(orientation='horizontal', size_hint_y=0.08, spacing=10)
            vibration_toggle_label = Label(
                text='Vibration Enabled:', 
                size_hint_x=0.7, 
                font_size='14sp'
            )
            vibration_toggle = ToggleButton(
                text='ON' if vibration_enabled else 'OFF',
                state='down' if vibration_enabled else 'normal',
                size_hint_x=0.3,
                background_color=(0.2, 0.8, 0.2, 1) if vibration_enabled else (0.8, 0.2, 0.2, 1)
            )
            
            def on_vibration_toggle(instance):
                enabled = instance.state == 'down'
                instance.text = 'ON' if enabled else 'OFF'
                instance.background_color = (0.2, 0.8, 0.2, 1) if enabled else (0.8, 0.2, 0.2, 1)
                set_setting('vibration_enabled', enabled)
                if not enabled:
                    self.vibration_manager.has_vibrator = False
                else:
                    self.vibration_manager.has_vibrator = True
            
            vibration_toggle.bind(on_press=on_vibration_toggle)
            vibration_toggle_layout.add_widget(vibration_toggle_label)
            vibration_toggle_layout.add_widget(vibration_toggle)
            left_column.add_widget(vibration_toggle_layout)
            
            button_vib_layout = BoxLayout(orientation='vertical', size_hint_y=0.15, spacing=5)
            button_vib_label = Label(
                text=f'Buttons: {button_vibration_intensity:.1f}', 
                size_hint_y=0.4, 
                font_size='13sp'
            )
            button_vib_layout.add_widget(button_vib_label)
            
            button_vib_slider = Slider(
                min=0.0,
                max=1.0,
                value=button_vibration_intensity,
                size_hint_y=0.6
            )
            
            def on_button_vibration_change(instance, value):
                self.vibration_manager.set_button_intensity(value)
                button_vib_label.text = f'Buttons: {value:.1f}'
                
            button_vib_slider.bind(value=on_button_vibration_change)
            button_vib_layout.add_widget(button_vib_slider)
            left_column.add_widget(button_vib_layout)
            
            steering_vib_layout = BoxLayout(orientation='vertical', size_hint_y=0.15, spacing=5)
            steering_vib_label = Label(
                text=f'Steering: {steering_vibration_intensity:.1f}', 
                size_hint_y=0.4, 
                font_size='13sp'
            )
            steering_vib_layout.add_widget(steering_vib_label)
            
            steering_vib_slider = Slider(
                min=0.0,
                max=1.0,
                value=steering_vibration_intensity,
                size_hint_y=0.6
            )
            
            def on_steering_vibration_change(instance, value):
                self.vibration_manager.set_steering_intensity(value)
                steering_vib_label.text = f'Steering: {value:.1f}'
                
            steering_vib_slider.bind(value=on_steering_vibration_change)
            steering_vib_layout.add_widget(steering_vib_slider)
            left_column.add_widget(steering_vib_layout)
            
            pedal_range_layout = BoxLayout(orientation='vertical', size_hint_y=0.25, spacing=5)
            pedal_range_title = Label(
                text='Pedal Vibration Range', 
                size_hint_y=0.3, 
                font_size='13sp',
                bold=True
            )
            pedal_range_layout.add_widget(pedal_range_title)
            
            pedal_min_layout = BoxLayout(orientation='horizontal', size_hint_y=0.35, spacing=8)
            pedal_min_label = Label(
                text=f'Min: {pedal_min_vibration:.1f}', 
                size_hint_x=0.3, 
                font_size='12sp'
            )
            self.pedal_min_slider = Slider(
                min=0.0,
                max=0.8,
                value=pedal_min_vibration,
                size_hint_x=0.7
            )
            
            def on_pedal_min_change(instance, value):
                current_max = self.pedal_max_slider.value
                if value > current_max:
                    value = current_max
                    self.pedal_min_slider.value = value
                self.vibration_manager.set_pedal_vibration_range(value, current_max)
                pedal_min_label.text = f'Min: {value:.1f}'
                
            self.pedal_min_slider.bind(value=on_pedal_min_change)
            pedal_min_layout.add_widget(pedal_min_label)
            pedal_min_layout.add_widget(self.pedal_min_slider)
            pedal_range_layout.add_widget(pedal_min_layout)
            
            pedal_max_layout = BoxLayout(orientation='horizontal', size_hint_y=0.35, spacing=8)
            pedal_max_label = Label(
                text=f'Max: {pedal_max_vibration:.1f}', 
                size_hint_x=0.3, 
                font_size='12sp'
            )
            self.pedal_max_slider = Slider(
                min=0.2,
                max=1.0,
                value=pedal_max_vibration,
                size_hint_x=0.7
            )
            
            def on_pedal_max_change(instance, value):
                current_min = self.pedal_min_slider.value
                if value < current_min:
                    value = current_min
                    self.pedal_max_slider.value = value
                self.vibration_manager.set_pedal_vibration_range(current_min, value)
                pedal_max_label.text = f'Max: {value:.1f}'
                
            self.pedal_max_slider.bind(value=on_pedal_max_change)
            pedal_max_layout.add_widget(pedal_max_label)
            pedal_max_layout.add_widget(self.pedal_max_slider)
            pedal_range_layout.add_widget(pedal_max_layout)
            
            left_column.add_widget(pedal_range_layout)
            
            right_column = BoxLayout(orientation='vertical', spacing=10, size_hint_x=0.5)
            other_title = Label(
                text='Other Settings', 
                size_hint_y=0.1, 
                font_size='16sp',
                bold=True,
                color=(0.2, 0.4, 0.8, 1)
            )
            right_column.add_widget(other_title)
            
            sens_layout = BoxLayout(orientation='vertical', size_hint_y=0.35, spacing=5)
            sens_label = Label(
                text=f'Sensitivity: {saved_sensitivity:.1f}', 
                size_hint_y=0.3, 
                font_size='14sp'
            )
            sens_layout.add_widget(sens_label)
            
            slider = Slider(
                min=0.5,
                max=2.5,
                value=saved_sensitivity,
                size_hint_y=0.7
            )
            
            def on_sensitivity_change(instance, value):
                self.accelerometer_manager.set_sensitivity(value)
                sens_label.text = f'Sensitivity: {value:.1f}'
                set_setting('sensitivity', value)
                
            slider.bind(value=on_sensitivity_change)
            sens_layout.add_widget(slider)
            right_column.add_widget(sens_layout)
            
            battery_layout = BoxLayout(orientation='vertical', size_hint_y=0.35, spacing=5)
            battery_label = Label(
                text=f'Battery Warning: {battery_warning}%', 
                size_hint_y=0.3, 
                font_size='14sp'
            )
            battery_layout.add_widget(battery_label)
            
            battery_slider = Slider(
                min=5,
                max=40,
                value=battery_warning,
                size_hint_y=0.7
            )
            
            def on_battery_warning_change(instance, value):
                warning_level = int(value)
                battery_label.text = f'Battery Warning: {warning_level}%'
                set_setting('battery_warning_level', warning_level)
                
            battery_slider.bind(value=on_battery_warning_change)
            battery_layout.add_widget(battery_slider)
            right_column.add_widget(battery_layout)
            
            main_layout.add_widget(left_column)
            main_layout.add_widget(right_column)
            content.add_widget(main_layout)
            
            btns = BoxLayout(size_hint_y=0.12, spacing=15, padding=(10, 0))
            
            reset_btn = Button(
                text='Reset to Default', 
                size_hint_x=0.5,
                font_size='16sp',
                background_color=(0.2, 0.6, 0.9, 1)
            )
            reset_btn.bind(on_press=lambda x: self._reset_settings(
                slider, sens_label, battery_slider, battery_label,
                button_vib_slider, steering_vib_slider,
                button_vib_label, steering_vib_label, vibration_toggle,
                self.pedal_min_slider, self.pedal_max_slider, pedal_min_label, pedal_max_label
            ))
            
            close_btn = Button(
                text='Close', 
                size_hint_x=0.5,
                font_size='16sp',
                background_color=(0.2, 0.6, 0.9, 1)
            )
            
            popup = Popup(
                title='Settings', 
                content=content, 
                size_hint=(0.9, 0.85),
                title_size='18sp'
            )
            close_btn.bind(on_press=lambda x: popup.dismiss())
            
            btns.add_widget(reset_btn)
            btns.add_widget(close_btn)
            content.add_widget(btns)
            
            popup.open()
        except Exception as e:
            print(f"Error in show_settings_menu: {e}")
            self.show_connection_message(f"Settings error: {str(e)}", "error")

    def _reset_settings(self, sensitivity_slider, sens_label, battery_slider, battery_label,
                       button_vib_slider, steering_vib_slider,
                       button_vib_label, steering_vib_label, vibration_toggle,
                       pedal_min_slider, pedal_max_slider, pedal_min_label, pedal_max_label):
        
        try:
            App.get_running_app().settings_manager.reset_to_defaults()
            
            sensitivity_slider.value = 1.0
            sens_label.text = 'Sensitivity: 1.0'
            
            battery_slider.value = 30
            battery_label.text = 'Battery Warning: 30%'
            
            button_vib_slider.value = 0.5
            button_vib_label.text = 'Buttons: 0.5'
            
            steering_vib_slider.value = 0.5
            steering_vib_label.text = 'Steering: 0.5'
            
            vibration_toggle.state = 'down'
            vibration_toggle.text = 'ON'
            vibration_toggle.background_color = (0.2, 0.8, 0.2, 1)
            
            pedal_min_slider.value = 0.1
            pedal_min_label.text = 'Min: 0.1'
            pedal_max_slider.value = 1.0
            pedal_max_label.text = 'Max: 1.0'
            
            self.accelerometer_manager.set_sensitivity(1.0)
            self.vibration_manager.set_button_intensity(0.5)
            self.vibration_manager.set_steering_intensity(0.5)
            self.vibration_manager.set_pedal_vibration_range(0.1, 1.0)
            self.vibration_manager.has_vibrator = True
            
            print("All settings reset to default")
        except Exception as e:
            print(f"Error resetting settings: {e}")

    def on_pause(self):
        print("App paused - keeping connections alive")
        return True

    def on_resume(self):
        print("App resumed")
        Window.fullscreen = 'auto'
        Window.borderless = True
        
        if hasattr(self, 'accelerometer_manager') and getattr(self, 'accelerometer_mode', False):
            self.accelerometer_manager.start()
        return

class BluetoothRC(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings_manager = SettingsManager()
    
    def build(self):
        self.title = "Bluetooth RC Car Controller"
        print("Starting Bluetooth RC Car Controller...")
        
        Window.fullscreen = 'auto'
        Window.borderless = True
        
        return CombinedAppRoot()

    def on_pause(self):
        return self.root.on_pause()

    def on_resume(self):
        self.root.on_resume()
        return True

    def on_stop(self):
        root = self.root
        if hasattr(root, 'accelerometer_manager'):
            try:
                root.accelerometer_manager.stop()
            except Exception as e:
                print(f"Error stopping accelerometer manager: {e}")
        if hasattr(root, 'connection_manager'):
            root.connection_manager.disconnect()
        print("App stopped - resources cleaned up")
        return True

if __name__ == '__main__':
    try:
        print("Starting Bluetooth RC Car Controller Application...")
        
        try:
            app = BluetoothRC()
            app.run()
        except Exception as app_error:
            print(f"Application runtime error: {app_error}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"Application failed to start: {e}")
        import traceback
        traceback.print_exc()
    except SystemExit:
        print("Application exited normally")
    except KeyboardInterrupt:
        print("Application interrupted by user")