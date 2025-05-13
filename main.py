from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.core.window import Window

from pytubefix import YouTube
import os
import traceback

# Set default window size for testing
Window.size = (360, 640)

# Output directory
DOWNLOAD_DIR = "/sdcard/Download"

class Logger:
    def __init__(self):
        self.logs = []

    def log(self, message):
        self.logs.append(message)
        print(message)

    def get_logs(self):
        return "\n".join(self.logs)

logger = Logger()

class YouTubeDownloader(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)

        self.url_input = TextInput(hint_text='Enter YouTube URL', multiline=False, size_hint_y=0.1)
        self.add_widget(self.url_input)

        self.download_btn = Button(text='Download Video', size_hint_y=0.1)
        self.download_btn.bind(on_press=self.download_video)
        self.add_widget(self.download_btn)

        self.view_log_btn = Button(text='View Logs', size_hint_y=0.1)
        self.view_log_btn.bind(on_press=self.show_logs)
        self.add_widget(self.view_log_btn)

        self.status_label = Label(text='', size_hint_y=0.7)
        self.add_widget(self.status_label)

    def update_status(self, message):
        self.status_label.text = message
        logger.log(message)

    def show_logs(self, instance):
        popup = Popup(
            title='Download Logs',
            content=TextInput(text=logger.get_logs(), readonly=True),
            size_hint=(0.9, 0.9)
        )
        popup.open()

    def download_video(self, instance):
        url = self.url_input.text.strip()
        if not url:
            self.update_status("Please enter a valid URL.")
            return

        self.update_status("Starting download...")

        try:
            yt = YouTube(url)
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()

            if not stream:
                self.update_status("No compatible video stream found.")
                return

            stream.download(output_path=DOWNLOAD_DIR)
            self.update_status(f"Download completed: {stream.title}")

        except Exception as e:
            error_message = f"[ERROR] {str(e)}\n{traceback.format_exc()}"
            self.update_status("An error occurred.")
            logger.log(error_message)

class YTApp(App):
    def build(self):
        return YouTubeDownloader()

if __name__ == '__main__':
    YTApp().run()
