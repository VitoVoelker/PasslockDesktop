# Can't get it to work in `encryption.py` file, while using .exe thus had to add it in main.py
import hashlib
#from Crypto import Random
#from Crypto.Cipher import AES
from base64 import urlsafe_b64encode, urlsafe_b64decode
from kivy.uix.relativelayout import RelativeLayout
import os
os.chdir(rf"{os.path.dirname(os.path.realpath(__file__))}")

from libs.utils import *
os.environ["KIVY_METRICS_DENSITY"] = get_scaling()

import threading
from colorsys import rgb_to_hls, hls_to_rgb

from libs.screens.root import Root
from libs.firebase import Firebase

from kivy.core.clipboard import Clipboard
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import (
    BooleanProperty,
    ColorProperty,
    get_color_from_hex,
    StringProperty,
)
from kivy.metrics import Metrics
from kivymd.toast import toast
from kivymd.app import MDApp
from kivy.core.text import LabelBase
from kivy import platform


if platform == 'linux':
    import subprocess
    output = subprocess.Popen(
        'xrandr | grep "\*" | cut -d" " -f4',
        shell=True,
        stdout=subprocess.PIPE).communicate()[0]
    screenx = int(output.replace(b'\n', b'').split(b'x')[0])
    screeny = int(output.replace(b'\n', b'').split(b'x')[1])
elif platform == 'win':
    from win32api import GetSystemMetrics
    screenx = GetSystemMetrics(0)
    screeny = GetSystemMetrics(1)
else:
    screenx = 0
    screeny = 0


fonts_path = f"./fonts/"
fonts = [
    {
        "name": "Poppins",
        "fn_regular": fonts_path + "Poppins-Regular.ttf",
        "fn_bold": fonts_path + "Poppins-Bold.ttf",
    },
    {
        "name": "Poppins-Bold",
        "fn_regular": fonts_path + "Poppins-Bold.ttf",
    },
    {
        "name": "BigCircleFont",
        "fn_regular": fonts_path + "DejavuSans.ttf",
    },
]

for font in fonts:
    LabelBase.register(**font)
dpi = Metrics.dpi
if dpi < 80:
    size_x, size_y = 770, 590
    Window.minimum_height = size_x
    Window.minimum_width = 500
else:
    size_x, size_y = 1100, 850
    Window.minimum_height = size_y
    Window.minimum_width = 700
    
Window.left = (screenx - size_x)/2
Window.top = (screeny - size_y)/2
Window.size = (size_x, size_y)

# TODO: Add support for chrome os and linux
# TODO: Make updated .exe file that fixes password not deleting

font_file = f"./fonts/Poppins-Regular.ttf"


class MainApp(MDApp):
    dark_mode = BooleanProperty(False)
    extra_security = BooleanProperty(False)
    text_color = ColorProperty()
    primary_accent = ColorProperty()
    primary_palette = StringProperty()
    bg_color = ColorProperty()
    entered_app = BooleanProperty(False)
    email = StringProperty("DemoMail")

    password_changed = False
    system_dark_mode = False
    auto_sync = False
    backup_failure = False

    encryption_class = None
    update_dialog = None
    exit_dialog = None
    sync_widget = None
    anim_sync = None

    passwords = {}
    encrypted_keys = {}
    screen_history = []

    path_to_live_ui = "backup_design.kv"

    def __init__(self):
        super().__init__()
        from libs.save_config import SaveConfig

        self.save_config = SaveConfig(
            "auto_sync",
            "dark_mode",
            "system_dark_mode",
            "backup_failure",
            "primary_palette",
            "ui_scaling"
        )
        self.theme_cls.font_styles.update(
            {
                "H1": [font_file, 96, False, -1.5],
                "H2": [font_file, 60, False, -0.5],
                "H3": [font_file, 48, False, 0],
                "H4": [font_file, 34, False, 0.25],
                "H5": [font_file, 24, False, 0],
                "H6": [font_file, 20, False, 0.15],
                "Button": [font_file, 14, True, 1.25],
                "Subtitle1": [font_file, 16, False, 0.15],
                "Body1": [font_file, 16, False, 0.5],
                "Body2": [font_file, 14, False, 0.25],
            }
        )
        self.primary_palette = get_primary_palette()
        self.signup = False if os.path.exists("./data/user_id.txt") else True
        self.auto_sync = check_auto_sync()
        self.ui_scaling = get_scaling()
        Window.on_minimize = lambda: self.backup_on_pause()
        self.firebase = Firebase()
        self.set_dark_mode()
        threading.Thread(target=self.set_user_mail, daemon=True).start()

    def build(self):
        self.root = Root()
        from libs.modules import CardTextField, Toolbar, List
        self.theme_cls.material_style = "M3"
        self.root.load_screen("SignupScreen" if self.signup else "LoginScreen")
        if not self.signup:
            self.root.LoginScreen.ids.password.focus = True
        Clock.schedule_once(lambda *args: self.print_pos(), 5)
            

    def on_primary_palette(self, instance, value):
        self.theme_cls.primary_palette = value
        self.set_theme_colors()

    def set_theme_colors(self):
        self.text_color = (
            self.generate_color(lightness=0.25)
            if not self.dark_mode
            else self.generate_color(lightness=0.91)
        )
        self.light_color = self.generate_color()
        self.bg_color_light = self.generate_color(lightness=0.98)
        self.bg_color_light_hex = self.generate_color(lightness=0.98, return_hex=True)
        self.bg_color_dark = self.generate_color(darkness=0.1)
        self.bg_color_dark_hex = self.generate_color(darkness=0.1, return_hex=True)
        self.bg_color = self.bg_color_dark if self.dark_mode else self.bg_color_light
        self.dark_color = self.generate_color(darkness=0.18)  # 262626
        self.login_circle_light = self.generate_color(lightness=0.85)
        self.primary_accent = self.dark_color if self.dark_mode else self.light_color
        self.light_hex = self.generate_color(return_hex=True)
        self.dark_hex = self.generate_color(darkness=0.18, return_hex=True)

    def set_user_mail(self, *args):
        self.email = get_email()

    def backup(self, sync_widget):
        def backup_success():
            toast("Backup Successful")
            self.backup_failure = False
            sync_widget.stop()
            self.password_changed = False

        def backup_failure(*args):
            print(*args)
            self.backup_failure = True
            toast("Couldn't backup :(, Check your internet connection")
            sync_widget.stop()

        sync_widget.icon = "cloud-upload"
        sync_widget.text = "Backing up.."
        sync_widget.start()
        self.firebase.backup_success = lambda *args: backup_success()
        self.firebase.backup_failure = lambda *args: backup_failure(*args)
        self.firebase.backup()

    def restore(self, sync_widget, user_id=None, decrypt=True):
        def restore_success(req, result):
            sync_widget.stop()
            if result is not None:
                from libs.utils import write_passwords

                write_passwords(result)
                if decrypt:
                    self.passwords = self.encryption_class.load_decrypted()
                toast("Restored successfully")
            else:
                toast("No passwords to restore.")

        def restore_failure(req, result):
            sync_widget.stop()
            toast("Restore Failed")

        sync_widget.icon = "cloud-download"
        sync_widget.text = "Restoring.."
        sync_widget.start()
        self.firebase.restore_success = lambda req, result: restore_success(req, result)
        self.firebase.restore_failure = lambda req, result: restore_failure(req, result)
        if user_id:
            self.firebase.restore(user_id)
        else:
            self.firebase.restore()

    def set_dark_mode(self):
        self.dark_mode = is_dark_mode()
        Clock.schedule_once(
            lambda x: exec("self.entered_app = True", {"self": self}), 1
        )

    def show_toast_copied(self, item):
        toast("Item copied")
        Clipboard.copy(item)

    def animate_signup(self, instance):

        """Animation to be shown when user enters the signup screen"""
        if instance:
            Animation(pos_hint={"top": 0.95}, opacity=1, d=0.5, t="out_back").start(
                instance
            )

    def generate_color(
            self,
            hex_color=False,
            color=None,
            return_hex=False,
            lightness=0.92,
            darkness=0,
            saturation=None,
    ):
        """
        :param hex_color:  Instead of passing color as list hexadecimal value can be passed.
        :param color: Takes color like [.5,.5,.5, 1] as Parameter
        :param return_hex: Boolean value if set true the function will return hexadecimal value.
        :param lightness: Value from 0-1. If set to 1 it will return white and 0 will return original color.
        :return:
        """
        if hex_color:
            color = get_color_from_hex(hex_color)
        elif not color:
            color = self.theme_cls.primary_color[:-1]

        h, l, s = rgb_to_hls(*color)
        l = lightness if not darkness else darkness
        if saturation is None:
            s = 0.7 if not darkness else 0.15
        else:
            s = saturation
        color = list(hls_to_rgb(h, l, s))

        if not return_hex:
            return color + [1]
        else:
            r, g, b = color
            _hex = (
                    hex(round(r * 255))[2:]
                    + hex(round(g * 255))[2:]
                    + hex(round(b * 255))[2:]
            )
            return _hex

    def back_button(self, home_screen=False, *args):
        if not home_screen:
            self.screen_history.pop()
        else:
            self.screen_history = ["HomeScreen"]
        self.root.transition.mode = "pop"
        self.root.transition.direction = "right"
        self.root.current = self.screen_history[-1]

    def on_dark_mode(self, instance, mode):
        if self.entered_app:
            current_screen = self.root.current
            if current_screen == "HomeScreen":
                primary_color = Animation(
                    primary_accent=self.dark_color
                    if self.dark_mode
                    else self.light_color,
                    bg_color=self.bg_color_dark
                    if self.dark_mode
                    else self.bg_color_light,
                    duration=0.3,
                )
                primary_color.start(self)
                primary_color.on_complete = self.set_theme_style
        else:
            self.set_theme_style()

    def set_theme_style(self, *args):
        print("theme_style set")
        self.text_color = (
            self.generate_color(lightness=0.25)  # get_color_from_hex("611c05")
            if not self.dark_mode
            else self.generate_color(lightness=0.91)  # get_color_from_hex("fde9e2")
        )
        self.bg_color = self.bg_color_dark if self.dark_mode else self.bg_color_light
        self.primary_accent = self.dark_color if self.dark_mode else self.light_color
        if self.dark_mode:
            self.theme_cls.theme_style = "Dark"
            self.theme_cls.primary_hue = "300"
        else:
            self.theme_cls.theme_style = "Light"
            self.theme_cls.primary_hue = "500"

    def toggle_mode(self, *args):
        self.dark_mode = not self.dark_mode

    def backup_on_pause(self):
        def success():
            toast("Backed up!")
            self.backup_failure = False

        def failure(*args):
            toast("Some Error occured couldn't backup!")
            self.backup_failure = True

        if self.auto_sync and self.password_changed:
            self.firebase.backup()
            self.firebase.backup_success = lambda *args: success()
            self.firebase.backup_failure = lambda *args: failure(*args)
            self.password_changed = False

    def on_stop(self, inst):
        self.save_config.save_settings()

    ## is called in the build function 5 seconds after the app has build
    def print_pos(self):
        import numpy as np
        import cv2 as cv2
        windowsizex = 1100
        windowsizey = 850

        ids = {self.root.SignupScreen.ids.signup, self.root.SignupScreen.ids.login, self.root.SignupScreen.ids.email, self.root.SignupScreen.ids.password}
        img = cv2.imread(r"screenshot_kivyapp.jpg")
        
        for id in ids:

            pos = id.pos
            size = id.size
            pos_x = int(pos[0])
            pos_y = int(pos[1])
            width = int(size[0])
            height = int(size[1])

            print(str(id))
            print("x:" + str(pos_x))
            print("y:"+ str(pos_y))
            print("width:"+str(width))
            print("height:"+str(height))
            print("--------")
            
            ## draws rectangle on image 
            cv2.rectangle(img,(pos_x,850-pos_y),(pos_x+width,850-pos_y+height),(0,255,0),1)

            ##statische Verschiebung nach oben um 15 35 pixel
            #cv2.rectangle(img,(pos_x,815-pos_y),(pos_x+width,815-pos_y+height),(255,0,0),1)  
            
            
        cv2.imshow("Bounding Box Preview", img)
        k = cv2.waitKey(0)    
        '''
        kivy
        y
        |
        |
        |
        |
        |__________x
    
        cv
        ___________x
        |
        |
        |
        |
        |
        y

        window 1100 x 850 

        x = x
        y = 850-y
        '''

        
if __name__ == "__main__":
    MainApp().run()
    
    
