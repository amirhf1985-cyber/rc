from kivy.storage.jsonstore import JsonStore
from kivy.app import App
import json
import os
import time
from datetime import datetime

class SettingsManager:
    def __init__(self):
        self.store = JsonStore('rc_car_settings.json')
        self._initialize_defaults()
    
    def _initialize_defaults(self):
        """مطمئن شویم که حداقل تنظیمات پیش‌فرض وجود دارند"""
        default_settings = {
            'sensitivity': 1.0,
            'accelerometer_mode': False,
            'auto_connect': True,
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
            'saved_wifi_connections': []
        }
        
        for key, value in default_settings.items():
            if not self.store.exists(key):
                self.set(key, value)
    
    def get(self, key, default=None):
        """دریافت مقدار یک تنظیم"""
        try:
            if self.store.exists(key):
                data = self.store.get(key)
                return data.get('value', default)
            return default
        except Exception as e:
            print(f"❌ Settings read error for {key}: {e}")
            return default
    
    def set(self, key, value):
        """ذخیره یا به‌روزرسانی یک تنظیم"""
        try:
            self.store.put(key, value=value)
            print(f"✅ Setting '{key}' saved: {value}")
            return True
        except Exception as e:
            print(f"❌ Settings write error for {key}: {e}")
            return False
    
    def delete(self, key):
        """حذف یک تنظیم"""
        try:
            if self.store.exists(key):
                self.store.delete(key)
                print(f"✅ Setting '{key}' deleted")
                return True
            return False
        except Exception as e:
            print(f"❌ Settings delete error for {key}: {e}")
            return False
    
    def exists(self, key):
        """بررسی وجود یک تنظیم"""
        try:
            return self.store.exists(key)
        except Exception as e:
            print(f"❌ Settings exists check error for {key}: {e}")
            return False
    
    def get_all_settings(self):
        """دریافت تمام تنظیمات"""
        settings = {}
        try:
            for key in self.store.keys():
                settings[key] = self.get(key)
            return settings
        except Exception as e:
            print(f"❌ Error getting all settings: {e}")
            return {}
    
    def reset_to_defaults(self):
        """بازنشانی تمام تنظیمات به حالت پیش‌فرض"""
        default_settings = {
            'sensitivity': 1.0,
            'accelerometer_mode': False,
            'auto_connect': True,
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
            'saved_wifi_connections': []
        }
        
        try:
            for key, value in default_settings.items():
                self.set(key, value)
            
            print("✅ All settings reset to default")
            return True
        except Exception as e:
            print(f"❌ Error resetting settings to default: {e}")
            return False
    
    def get_float(self, key, default=0.0):
        """دریافت مقدار float"""
        try:
            value = self.get(key, default)
            return float(value)
        except (ValueError, TypeError) as e:
            print(f"❌ Error converting {key} to float: {e}")
            return float(default)
    
    def get_int(self, key, default=0):
        """دریافت مقدار integer"""
        try:
            value = self.get(key, default)
            return int(value)
        except (ValueError, TypeError) as e:
            print(f"❌ Error converting {key} to int: {e}")
            return int(default)
    
    def get_bool(self, key, default=False):
        """دریافت مقدار boolean"""
        try:
            value = self.get(key, default)
            if isinstance(value, bool):
                return value
            elif isinstance(value, str):
                return value.lower() in ['true', '1', 'yes', 'on']
            elif isinstance(value, (int, float)):
                return bool(value)
            return bool(default)
        except Exception as e:
            print(f"❌ Error converting {key} to bool: {e}")
            return bool(default)
    
    def get_string(self, key, default=''):
        """دریافت مقدار string"""
        try:
            value = self.get(key, default)
            return str(value)
        except Exception as e:
            print(f"❌ Error converting {key} to string: {e}")
            return str(default)
    
    def backup_settings(self, backup_file='rc_car_settings_backup.json'):
        """پشتیبان‌گیری از تنظیمات"""
        try:
            settings = self.get_all_settings()
            with open(backup_file, 'w') as f:
                json.dump(settings, f, indent=2)
            print(f"✅ Settings backed up to {backup_file}")
            return True
        except Exception as e:
            print(f"❌ Error backing up settings: {e}")
            return False
    
    def restore_settings(self, backup_file='rc_car_settings_backup.json'):
        """بازیابی تنظیمات از پشتیبان"""
        try:
            if not os.path.exists(backup_file):
                print(f"❌ Backup file not found: {backup_file}")
                return False
            
            with open(backup_file, 'r') as f:
                settings = json.load(f)
            
            for key, value in settings.items():
                self.set(key, value)
            
            print(f"✅ Settings restored from {backup_file}")
            return True
        except Exception as e:
            print(f"❌ Error restoring settings: {e}")
            return False
    
    def clear_all_settings(self):
        """پاک کردن تمام تنظیمات"""
        try:
            self.backup_settings()
            
            keys = list(self.store.keys())
            for key in keys:
                self.delete(key)
            
            print("✅ All settings cleared")
            return True
        except Exception as e:
            print(f"❌ Error clearing all settings: {e}")
            return False
    
    # ===== متدهای مربوط به saved_wifi_connections =====
    
    def add_saved_wifi_connection(self, ip, port, connection_name=""):
        """افزودن اتصال وای‌فای به تاریخچه"""
        try:
            saved_connections = self.get('saved_wifi_connections', [])
            
            new_connection = {
                "ip": ip,
                "port": int(port),
                "name": connection_name or f"RC_Car_{ip}",
                "timestamp": time.time(),
                "last_used": time.time()
            }
            
            # حذف اگر قبلاً وجود دارد
            saved_connections = [conn for conn in saved_connections 
                               if not (conn.get("ip") == ip and conn.get("port") == int(port))]
            
            # اضافه کردن به ابتدای لیست
            saved_connections.insert(0, new_connection)
            
            # محدود کردن تعداد (مثلاً ۱۰ تا)
            if len(saved_connections) > 10:
                saved_connections = saved_connections[:10]
            
            self.set('saved_wifi_connections', saved_connections)
            print(f"✅ WiFi connection saved: {ip}:{port}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving WiFi connection: {e}")
            return False
    
    def get_saved_wifi_connections(self):
        """دریافت لیست اتصالات وای‌فای ذخیره شده"""
        try:
            connections = self.get('saved_wifi_connections', [])
            # مرتب کردن بر اساس last_used (جدیدترین اول)
            connections.sort(key=lambda x: x.get('last_used', 0), reverse=True)
            return connections
        except Exception as e:
            print(f"❌ Error getting saved WiFi connections: {e}")
            return []
    
    def update_connection_usage(self, ip, port):
        """به‌روزرسانی زمان استفاده یک اتصال"""
        try:
            connections = self.get('saved_wifi_connections', [])
            for conn in connections:
                if conn.get("ip") == ip and conn.get("port") == int(port):
                    conn["last_used"] = time.time()
                    break
            
            self.set('saved_wifi_connections', connections)
            return True
        except Exception as e:
            print(f"❌ Error updating connection usage: {e}")
            return False
    
    def clear_wifi_history(self):
        """پاک کردن تاریخچه وای‌فای"""
        try:
            self.set('saved_wifi_connections', [])
            print("✅ WiFi history cleared")
            return True
        except Exception as e:
            print(f"❌ Error clearing WiFi history: {e}")
            return False
    
    def remove_wifi_connection(self, ip, port):
        """حذف یک اتصال وای‌فای از تاریخچه"""
        try:
            connections = self.get('saved_wifi_connections', [])
            connections = [conn for conn in connections 
                          if not (conn.get("ip") == ip and conn.get("port") == int(port))]
            self.set('saved_wifi_connections', connections)
            print(f"✅ Removed WiFi connection: {ip}:{port}")
            return True
        except Exception as e:
            print(f"❌ Error removing WiFi connection: {e}")
            return False
    
    def format_connection_time(self, timestamp):
        """فرمت‌دهی زمان برای نمایش به کاربر"""
        try:
            if not timestamp:
                return "Never"
            
            dt = datetime.fromtimestamp(timestamp)
            now = datetime.now()
            
            # اگر امروز است
            if dt.date() == now.date():
                return dt.strftime("Today %H:%M")
            
            # اگر دیروز است
            elif dt.date() == now.replace(day=now.day-1).date():
                return dt.strftime("Yesterday %H:%M")
            
            # در غیر این صورت
            else:
                return dt.strftime("%Y-%m-%d %H:%M")
        except Exception as e:
            print(f"❌ Error formatting connection time: {e}")
            return "Unknown"


# توابع کمکی برای دسترسی سریع
def get_setting(key, default=None):
    """دریافت مقدار یک تنظیم"""
    try:
        app = App.get_running_app()
        if hasattr(app, 'settings_manager'):
            return app.settings_manager.get(key, default)
        return default
    except Exception as e:
        print(f"❌ Error in get_setting for {key}: {e}")
        return default


def set_setting(key, value):
    """ذخیره یا به‌روزرسانی یک تنظیم"""
    try:
        app = App.get_running_app()
        if hasattr(app, 'settings_manager'):
            return app.settings_manager.set(key, value)
        return False
    except Exception as e:
        print(f"❌ Error in set_setting for {key}: {e}")
        return False


def get_setting_float(key, default=0.0):
    """دریافت مقدار float یک تنظیم"""
    try:
        app = App.get_running_app()
        if hasattr(app, 'settings_manager'):
            return app.settings_manager.get_float(key, default)
        return float(default)
    except Exception as e:
        print(f"❌ Error in get_setting_float for {key}: {e}")
        return float(default)


def get_setting_int(key, default=0):
    """دریافت مقدار integer یک تنظیم"""
    try:
        app = App.get_running_app()
        if hasattr(app, 'settings_manager'):
            return app.settings_manager.get_int(key, default)
        return int(default)
    except Exception as e:
        print(f"❌ Error in get_setting_int for {key}: {e}")
        return int(default)


def get_setting_bool(key, default=False):
    """دریافت مقدار boolean یک تنظیم"""
    try:
        app = App.get_running_app()
        if hasattr(app, 'settings_manager'):
            return app.settings_manager.get_bool(key, default)
        return bool(default)
    except Exception as e:
        print(f"❌ Error in get_setting_bool for {key}: {e}")
        return bool(default)


def get_setting_string(key, default=''):
    """دریافت مقدار string یک تنظیم"""
    try:
        app = App.get_running_app()
        if hasattr(app, 'settings_manager'):
            return app.settings_manager.get_string(key, default)
        return str(default)
    except Exception as e:
        print(f"❌ Error in get_setting_string for {key}: {e}")
        return str(default)