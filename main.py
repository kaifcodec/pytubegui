import os
import traceback
import threading
import ssl
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.core.window import Window
from jnius import autoclass, cast

ssl._create_default_https_context = ssl._create_unverified_context
from pytubefix import YouTube
from android.permissions import request_permissions, Permission
from android.storage import app_storage_path

# Java classes for SAF
Intent = autoclass('android.content.Intent')
Uri = autoclass('android.net.Uri')
PythonActivity = autoclass('org.kivy.android.PythonActivity')
Settings = autoclass('android.provider.Settings')

# Logger singleton (unchanged)
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

class YouTubeDownloader(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)

        # URL input
        self.url_input = TextInput(hint_text="Enter YouTube URL",
                                   size_hint_y=None, height="40dp", multiline=False)
        self.add_widget(self.url_input)

        # Buttons row
        btn_row = BoxLayout(size_hint_y=None, height="50dp", spacing=10)
        self.select_folder_btn = Button(text="Select Folder")
        self.select_folder_btn.bind(on_press=self.select_folder)
        btn_row.add_widget(self.select_folder_btn)

        self.download_btn = Button(text="Download MP4")
        self.download_btn.bind(on_press=self.download_video)
        btn_row.add_widget(self.download_btn)

        self.view_logs_btn = Button(text="View Logs")
        self.view_logs_btn.bind(on_press=self.show_logs)
        btn_row.add_widget(self.view_logs_btn)
        self.add_widget(btn_row)

        # Progress bar
        self.progress = ProgressBar(max=100, value=0, size_hint_y=None, height="20dp")
        self.add_widget(self.progress)

        # Status / log area
        self.status = TextInput(text="", readonly=True, size_hint=(1, 1),
                                font_size="14sp", background_color=(0,0,0,0.05),
                                foreground_color=(0,0,0,1), cursor_width=0)
        self.add_widget(self.status)

        # default download folder (app storage)
        self.download_dir = app_storage_path()
        logger.log(f"[App storage] Download folder: {self.download_dir}")

    def select_folder(self, _):
        """ Launch SAF folder picker """
        intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)
        currentActivity = cast('android.app.Activity', PythonActivity.mActivity)
        currentActivity.startActivityForResult(intent, 42)
        # result will come back to on_activity_result in your PythonActivity

    def on_activity_result(self, requestCode, resultCode, data):
        """ Called by PythonActivity when SAF returns """
        if requestCode == 42 and data:
            tree_uri = data.getData()
            # Persist permission
            PythonActivity.mActivity.getContentResolver().takePersistableUriPermission(
                tree_uri, Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
            )
            # Store it
            self.download_uri = tree_uri.toString()
            # Show path for user
            logger.log(f"📁 Selected folder URI: {self.download_uri}")

    def update_status(self, msg):
        logger.log(msg)
        self.status.text += msg + "\n"

    def show_logs(self, _):
        popup = Popup(title="Download Logs",
                      content=TextInput(text=logger.get_all(), readonly=True),
                      size_hint=(0.9, 0.9))
        popup.open()

    def download_video(self, _):
        url = self.url_input.text.strip()
        if not url:
            self.update_status("[Error] URL is empty.")
            return

        def _worker():
            self.download_btn.disabled = True
            self.update_status(f"Starting download: {url}")
            try:
                yt = YouTube(url)
                stream = (yt.streams
                          .filter(progressive=True, file_extension="mp4")
                          .order_by("resolution").desc().first())
                if not stream:
                    self.update_status("[Error] No progressive MP4 stream found.")
                else:
                    # if SAF folder chosen, use URI; else fallback to path
                    if hasattr(self, 'download_uri'):
                        # save to temp app storage then copy via SAF...
                        temp_path = stream.download(output_path=app_storage_path())
                        # TODO: use ContentResolver+stream to write `temp_path` into `download_uri`
                        self.update_status(f"Downloaded temp ▶ {temp_path}")
                        self.update_status("⚠️ SAF copy not yet implemented.")
                    else:
                        final = stream.download(output_path=self.download_dir)
                        self.update_status(f"Downloaded ▶ {final}")
            except Exception as e:
                tb = traceback.format_exc()
                self.update_status(f"[Exception] {e}\n{tb}")
            finally:
                self.progress.value = 0
                self.download_btn.disabled = False

        # reset progress bar and run
        self.progress.value = 0
        threading.Thread(target=_worker, daemon=True).start()

class YTApp(App):
    def build(self):
        Window.softinput_mode = "below_target"
        request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
        # Hook PythonActivity to receive onActivityResult
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        PythonActivity.addActivityResultListener(YouTubeDownloader.on_activity_result)
        return YouTubeDownloader()

if __name__ == "__main__":
    from kivy.utils import platform
    if platform != "android":
        Window.size = (360, 640)
    YTApp().run()
