import traceback
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from android.permissions import request_permissions, Permission
from androidstorage import AndroidStorage
from kivy.clock import mainthread


class Logger:
    def __init__(self):
        self.entries = []

    def log(self, msg):
        entry = str(msg)
        self.entries.append(entry)
        print(entry)
        if hasattr(self, "callback"):
            self.callback(entry)

    def get_all(self):
        return "\n".join(self.entries)

    def set_callback(self, cb):
        self.callback = cb


logger = Logger()


class SAFWriter(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)

        self.log_display = TextInput(text="App started.\n", readonly=True, size_hint=(1, 0.7))
        self.add_widget(self.log_display)
        logger.set_callback(self.append_log)

        self.pick_btn = Button(text="Pick Folder (SAF)", size_hint=(1, 0.1))
        self.pick_btn.bind(on_press=self.pick_folder)
        self.add_widget(self.pick_btn)

        self.write_btn = Button(text="Write File to Picked Folder", size_hint=(1, 0.1))
        self.write_btn.bind(on_press=self.write_file)
        self.write_btn.disabled = True
        self.add_widget(self.write_btn)

        self.uri_label = Label(text="No folder selected", size_hint=(1, 0.1))
        self.add_widget(self.uri_label)

        self.saf = AndroidStorage()
        self.folder_uri = None

        self.ask_permissions()

    def ask_permissions(self):
        logger.log("Requesting storage permissions...")
        request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE,Permission.MANAGE_EXTERNAL_STORAGE])

    @mainthread
    def append_log(self, msg):
        self.log_display.text += msg + "\n"

    def pick_folder(self, _):
        logger.log("Opening SAF folder picker...")
        self.saf.choose_dir(self.on_folder_picked)

    def on_folder_picked(self, uri):
        if uri:
            self.folder_uri = uri
            self.uri_label.text = f"Selected URI: {uri[:40]}..."
            logger.log(f"Folder picked: {uri}")
            self.write_btn.disabled = False
        else:
            logger.log("[Warning] No folder selected.")

    def write_file(self, _):
        if not self.folder_uri:
            logger.log("[Error] No folder selected to write into.")
            return

        try:
            filename = "test_output.txt"
            content = "This is a test file written using SAF on Android."

            logger.log(f"Attempting to write '{filename}' to folder...")
            with self.saf.open_file(self.folder_uri, filename, "w") as f:
                f.write(content)
            logger.log("File written successfully using SAF.")
        except Exception as e:
            tb = traceback.format_exc()
            logger.log(f"[Exception] {e}\n{tb}")


class SAFApp(App):
    def build(self):
        return SAFWriter()


if __name__ == "__main__":
    SAFApp().run()
