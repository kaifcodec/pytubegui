import os
import traceback
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.core.window import Window
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

from pytubefix import YouTube
from android.permissions import request_permissions, Permission, check_permission
from android.storage import app_storage_path
from jnius import autoclass

# Logger singleton
class Logger:
    def __init__(self):
        self.entries = []
    def log(self, msg):
        entry = msg if isinstance(msg, str) else repr(msg)
        self.entries.append(entry)
        print(entry)
    def get_all(self):
        return "\n".join(self.entries)

logger = Logger()

# Fetch shared Download path using Android API
def get_download_dir():
    Environment = autoclass('android.os.Environment')
    return Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS).getAbsolutePath()

class YouTubeDownloader(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)

        self.url_input = TextInput(hint_text="Enter YouTube URL", size_hint_y=None, height="40dp", multiline=False)
        self.add_widget(self.url_input)

        btn_row = BoxLayout(size_hint_y=None, height="50dp", spacing=10)
        self.download_btn = Button(text="Download MP4")
        self.download_btn.bind(on_press=self.download_video)
        btn_row.add_widget(self.download_btn)

        self.view_logs_btn = Button(text="View Logs")
        self.view_logs_btn.bind(on_press=self.show_logs)
        btn_row.add_widget(self.view_logs_btn)
        self.add_widget(btn_row)

        self.status = TextInput(text="", readonly=True, size_hint=(1, 1), font_size="14sp",
                                background_color=(0,0,0,0.05), foreground_color=(0,0,0,1), cursor_width=0)
        self.add_widget(self.status)

        # Use Downloads folder via Android API
        try:
            self.download_dir = get_download_dir()
            if not os.path.exists(self.download_dir):
                os.makedirs(self.download_dir)
            logger.log(f"Download folder: {self.download_dir}")
        except Exception as e:
            logger.log(f"[Error] creating download folder: {e}\n{traceback.format_exc()}")
            # Fallback to app storage
            self.download_dir = app_storage_path()

    def update_status(self, msg):
        logger.log(msg)
        self.status.text += msg + "\n"

    def show_logs(self, _):
        popup = Popup(title="Download Logs", content=TextInput(text=logger.get_all(), readonly=True), size_hint=(0.9, 0.9))
        popup.open()

    def download_video(self, _):
        url = self.url_input.text.strip()
        if not url:
            self.update_status("[Error] URL is empty.")
            return

        self.download_btn.disabled = True
        self.update_status(f"Starting download: {url}")

        try:
            yt = YouTube(url)
            stream = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first()
            if not stream:
                self.update_status("[Error] No progressive MP4 stream found.")
            else:
                stream.download(output_path=self.download_dir)
                self.update_status(f"Downloaded ▶ {stream.title}")
        except Exception as e:
            tb = traceback.format_exc()
            self.update_status(f"[Exception] {e}\n{tb}")
        finally:
            self.download_btn.disabled = False

class YTApp(App):
    def build(self):
        request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
        return YouTubeDownloader()

if __name__ == "__main__":
    from kivy.utils import platform
    if platform == "android":
        Window.softinput_mode = "below_target"
    else:
        Window.size = (360, 640)
    YTApp().run()
