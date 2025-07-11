import json
import os
import re
import threading
import customtkinter as ctk
import requests as rq
from datetime import datetime, timedelta
from tkinter.messagebox import showerror, showinfo
from typing import Callable


class GetMessages(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.geometry("700x400")

        self.console: ctk.CTkTextbox | None = None
        self.confirm_button: ctk.CTkButton | None = None
        self.loading_bar: ctk.CTkProgressBar | None = None
        self.in_process_flag: bool = False
        self.stop_flag: bool = False

        self.selected_channel = ctk.StringVar(value="Select channel")
        self.selected_mode = ctk.StringVar(value="Select mode")
        self.messages_count = ctk.StringVar(value="Messages count")
        self.streams_ago = ctk.StringVar(value="... streams ago")
        self.with_timecodes = ctk.BooleanVar(value=False)
        self.save_messages_in_file = ctk.BooleanVar(value=False)

        self.init_main_menu()

    def clear_window(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()

    def init_main_menu(self) -> None:
        def on_confirm() -> None:
            selected_mode: str = self.selected_mode.get()
            selected_channel: str = self.selected_channel.get()

            if selected_mode == "Select mode":
                self.console_print("Mode not selected!", is_error=True)
                return

            if selected_channel == "Select channel":
                self.console_print("Channel not selected!", is_error=True)
                stop()
                return

            if selected_mode == "All messages":
                self.loading_bar.configure(mode="indeterminate")
                self.loading_bar.start()
                threading.Thread(target=self.get_messages).start()
            elif selected_mode == "Last ... messages":
                try:
                    messages_count: int = int(self.messages_count.get())
                    if messages_count <= 0:
                        self.console_print("Invalid messages count!", is_error=True)
                        return

                    threading.Thread(target=self.get_messages, kwargs={"max_messages": messages_count}).start()
                except ValueError:
                    self.console_print("Invalid messages count!", is_error=True)
            elif selected_mode == "From ... stream ago":
                try:
                    last_stream: tuple = self.get_stream_ago(int(self.streams_ago.get()))
                    if last_stream is not None:
                        threading.Thread(target=self.get_messages, kwargs={"last_stream": last_stream}).start()
                except ValueError:
                    self.console_print("Invalid streams ago!", is_error=True)

        def stop() -> None:
            if self.in_process_flag:
                self.stop_flag = True

        self.clear_window()

        self.title("Get Messages History")
        self.minsize(700, 400)

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack_propagate(False)
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)

        left_side = ctk.CTkFrame(main_frame, width=150)
        left_side.pack_propagate(False)
        left_side.pack(side=ctk.LEFT, fill=ctk.Y, padx=(0, 10))

        channels: dict = self.get_data()["channels"]

        select_channel = ctk.CTkOptionMenu(left_side, values=list(channels.keys()) if channels != {} else [],
                                           variable=self.selected_channel)
        select_channel.pack(pady=(10, 0))

        select_mode = ctk.CTkOptionMenu(left_side, values=["All messages", "Last ... messages", "From ... stream ago"],
                                        variable=self.selected_mode)
        select_mode.pack(pady=(10, 0))

        ctk.CTkEntry(left_side, textvariable=self.messages_count).pack(pady=(10, 0))

        ctk.CTkEntry(left_side, textvariable=self.streams_ago).pack(pady=(10, 0))

        ctk.CTkCheckBox(left_side, text="Save messages\nto file",
                        variable=self.save_messages_in_file).pack(pady=(10, 0), anchor=ctk.W, padx=5)
        ctk.CTkCheckBox(left_side, text="With stream\ntimecodes",
                        variable=self.with_timecodes).pack(pady=(10, 0), anchor=ctk.W, padx=5)

        self.confirm_button = ctk.CTkButton(left_side, text="Confirm", font=("times new roman", 16, "bold"),
                                            fg_color="#393939", border_color="#52514e", border_width=1,
                                            hover_color="#242424", command=on_confirm)
        self.confirm_button.pack(pady=10, side=ctk.BOTTOM)

        ctk.CTkButton(left_side, text="Enter auth data",
                      command=self.open_auth_data_window).pack(pady=10, side=ctk.BOTTOM)

        right_side = ctk.CTkFrame(main_frame, width=300, fg_color="transparent")
        right_side.pack_propagate(False)
        right_side.pack(side=ctk.RIGHT, fill=ctk.BOTH, expand=True, padx=(10, 0))

        console_frame = ctk.CTkFrame(right_side, fg_color="transparent")
        console_frame.pack_propagate(False)
        console_frame.pack(fill=ctk.BOTH, expand=True, side=ctk.TOP)

        self.loading_bar = ctk.CTkProgressBar(console_frame, height=20, corner_radius=7)
        self.loading_bar.set(1)
        self.loading_bar.pack(fill=ctk.X, side=ctk.TOP, pady=(0, 10))

        self.console = ctk.CTkTextbox(console_frame, state=ctk.DISABLED)
        self.console.tag_config("error", foreground="#bf2a2f")
        self.console.pack(fill=ctk.BOTH, expand=True, side=ctk.BOTTOM)

        console_buttons_frame = ctk.CTkFrame(right_side, height=40)
        console_buttons_frame.pack_propagate(False)
        console_buttons_frame.pack(fill=ctk.X, side=ctk.BOTTOM, pady=(10, 0))

        ctk.CTkButton(console_buttons_frame, text="Stop", font=("times new roman", 16, "bold"),
                      width=50, command=stop).pack(side=ctk.LEFT, padx=5)
        ctk.CTkButton(console_buttons_frame, text="Clear", font=("times new roman", 16, "bold"),
                      width=50, command=self.clear_console).pack(side=ctk.LEFT, padx=5)

    def console_print(self, text: str, is_error: bool = False) -> None:
        self.console.configure(state=ctk.NORMAL)

        if is_error:
            self.console.insert("1.0", text + "\n", "error")
        else:
            self.console.insert("1.0", text + "\n")

        self.console.configure(state=ctk.DISABLED)
        self.console.see("1.0")

    def clear_console(self) -> None:
        self.console.configure(state=ctk.NORMAL)
        self.console.delete("1.0", ctk.END)
        self.console.configure(state=ctk.DISABLED)

    def open_auth_data_window(self) -> None:
        def parse() -> None:
            if self.parse_auth_data(user_data_entry.get("1.0", ctk.END)):
                showinfo("Info", "Auth data parsed successfully!")
                self.init_main_menu()

        def show_explaining() -> None:
            showinfo("Info", "You need to go to Twitch, press F12 -> Network, then find the gql "
                             "request there, right-click -> copy -> Copy as cURL (bash), and then paste this "
                             "text into the text field.")

        def paste_text(_=None):
            user_data_entry.insert(ctk.INSERT, self.clipboard_get())
            return "break"

        self.clear_window()

        self.title("Get Messages History - Parse auth data")
        self.minsize(400, 345)

        ctk.CTkButton(self, text="?", font=("Arial", 17, "bold"), width=30,
                      command=show_explaining).pack(anchor=ctk.W, padx=10, pady=10)

        user_data_entry = ctk.CTkTextbox(self)
        user_data_entry.pack(padx=10, fill=ctk.BOTH, expand=True)

        user_data_entry.bind("<Control-v>", paste_text)

        bottom_frame = ctk.CTkFrame(self, height=45)
        bottom_frame.pack_propagate(False)
        bottom_frame.pack(fill=ctk.X, pady=10, padx=10)

        ctk.CTkButton(bottom_frame, text="Parse", command=parse).pack(padx=5, pady=5, side=ctk.LEFT)
        ctk.CTkButton(bottom_frame, text="Cancel", command=self.init_main_menu).pack(padx=5, pady=5, side=ctk.RIGHT)

    def parse_auth_data(self, curl_text: str) -> bool:
        if curl_text != "\n":
            wanted_headers: dict = {
                "x-device-id",
                "authorization",
                "client-version",
                "client-id",
                "client-session-id",
                "client-integrity"
            }

            headers: dict = {}

            for match in re.finditer(r"-H '([^:]+): ([^']+)'", curl_text):
                key, value = match.group(1).lower(), match.group(2)
                if key in wanted_headers:
                    headers[key] = value

            for key in wanted_headers:
                if key not in headers:
                    showerror("Error", f"Header '{key}' not found in curl text!")
                    return False

            def write_auth_data(data: dict) -> dict:
                data["user_data"] = headers
                return data

            self.update_data(write_auth_data)

            return True
        else:
            showerror("Error", "Curl text is empty!")
            return False

    def do_request(self, sha256hash: str, operation_name: str, variables: dict) -> dict | None:
        try:
            payload: dict = {
                "extensions": {
                    "persistedQuery": {
                        "sha256Hash": sha256hash,
                        "version": 1
                    }
                },
                "operationName": operation_name,
                "variables": variables
            }

            data: dict = self.get_data()
            headers: dict = data["user_data"]

            if headers == {}:
                self.console_print("Auth data not found!", is_error=True)
                return None

            response: rq.Response = rq.post("https://gql.twitch.tv/gql", headers=headers, json=payload)

            json_: dict = response.json()

            if "error" in json_ or ("errors" in json_ and json_["errors"][0]["message"] == "failed integrity check"):
                self.console_print("Failed integrity check! Auth data is probably out of date.", is_error=True)
                return None

            return json_
        except Exception as e:
            self.console_print(f"An error occurred: {type(e)} ({str(e)})", is_error=True)
            return None

    def get_stream_ago(self, stream_ago: int) -> str | None:
        sha256hash: str = "acea7539a293dfd30f0b0b81a263134bb5d9a7175592e14ac3f7c77b192de416"
        operation_name: str = "FilterableVideoTower_Videos"
        variables: dict = {
            "broadcastType": "ARCHIVE",
            "channelOwnerLogin": self.selected_channel.get(),
            "limit": stream_ago,
            "videoSort": "TIME"
        }

        response: dict | None = self.do_request(sha256hash, operation_name, variables)

        if response is None:
            return None

        try:
            node: dict = response["data"]["user"]["videos"]["edges"][-1]["node"]
            last_stream_date: str = node["publishedAt"]
            stream_length: int = node["lengthSeconds"]
            return last_stream_date, stream_length
        except Exception as e:
            self.console_print(f"An error occurred: {type(e)} ({str(e)})", is_error=True)
            return None

    def get_messages(self, cursor: str = "", messages_count: int = 0, max_messages: int = 0,
                     last_stream: tuple | None = None, all_messages: list | None = None) -> None:
        def stop(with_save: bool = False) -> None:
            if max_messages == 0:
                self.loading_bar.stop()
                self.loading_bar.configure(mode="determinate")

            if with_save:
                if self.save_messages_in_file.get() and all_messages:
                    self.save_messages_to_file(all_messages)

            self.loading_bar.set(1)
            self.confirm_button.configure(state=ctk.NORMAL)

            self.in_process_flag = False
            self.stop_flag = False

        if all_messages is None:
            all_messages = []

        self.in_process_flag = True
        self.confirm_button.configure(state=ctk.DISABLED)

        data: dict = self.get_data()
        selected_channel: str = self.selected_channel.get()

        sha256hash: str = "eaa9b16f4d95346050e99889df096a51ffa142e49d9e2ce1ae5fae39ac7a8076"
        operation_name: str = "ViewerCardModLogsMessagesBySender"
        variables: dict = {
            "channelID": data["channels"][selected_channel],
            "cursor": cursor,
            "senderID": data["user_id"]
        }

        response: dict | None = self.do_request(sha256hash, operation_name, variables)

        if response is None:
            stop()
            return

        try:
            messages: dict = response["data"]["logs"]["messages"]
            edges: dict = messages["edges"]

            for edge in edges:
                if self.stop_flag:
                    stop(with_save=True)
                    return

                node: dict = edge["node"]
                message_date_obj = datetime.fromisoformat(node["sentAt"].replace("Z", "+03:00"))

                stream_timecode: str = ""

                if last_stream is not None:
                    stream_date, stream_length = last_stream

                    last_stream_date_obj = datetime.fromisoformat(stream_date.replace("Z", "+03:00"))
                    end_stream_date_obj = last_stream_date_obj + timedelta(seconds=stream_length)

                    if end_stream_date_obj < message_date_obj:
                        continue
                    elif end_stream_date_obj >= message_date_obj >= last_stream_date_obj:
                        seconds_diff = (message_date_obj - last_stream_date_obj).total_seconds()

                        if self.with_timecodes.get():
                            stream_timecode_obj = datetime(1, 1, 1) + timedelta(seconds=seconds_diff)

                            stream_timecode = f"[{stream_timecode_obj.strftime('%H:%M:%S')}] "

                        self.loading_bar.set((stream_length - seconds_diff) / stream_length)
                    else:
                        stop(with_save=True)
                        return

                redacted_date: str = (message_date_obj + timedelta(hours=3)).strftime("%d.%m.%Y %H:%M:%S")
                sender: str = node["sender"]
                message: str = node["content"]["text"]

                output_message: str = stream_timecode + f"({redacted_date}) {sender['displayName']}: {message}"

                self.console_print(output_message)
                all_messages.append(output_message + "\n")

                messages_count += 1

                if max_messages != 0:
                    self.loading_bar.set(messages_count / max_messages)

                if messages_count >= max_messages != 0:
                    stop(with_save=True)
                    return

            if messages["pageInfo"]["hasNextPage"]:
                self.get_messages(edges[-1]["cursor"], messages_count, max_messages, last_stream, all_messages)
            else:
                stop(with_save=True)
        except Exception as e:
            self.console_print(f"An error occurred: {type(e)} ({str(e)})", is_error=True)
            stop()
            return

    def get_data(self) -> dict:
        self.check_data()

        with open("data.json", "r", encoding="UTF-8") as file:
            return json.load(file)

    def update_data(self, update: Callable) -> None:
        data: dict = self.get_data()

        with open("data.json", "w", encoding="UTF-8") as file:
            json.dump(update(data), file, indent=4)

    @staticmethod
    def save_messages_to_file(messages: list) -> None:
        if not os.path.exists("messages") or not os.path.isdir("messages"):
            os.mkdir("messages")

        i: int = 0

        while True:
            if not os.path.exists(f"messages/messages{i if i != 0 else ""}.txt"):
                with open(f"messages/messages{i if i != 0 else ""}.txt", "w", encoding="UTF-8") as file:
                    file.writelines(reversed(messages))

                return

            i += 1

    @staticmethod
    def check_data() -> None:
        if os.path.exists("data.json"):
            try:
                with open("data.json", "r", encoding="UTF-8") as file:
                    data = json.load(file)

                if "channels" in data and "user_data" in data and "user_id" in data:
                    return
            except json.decoder.JSONDecodeError:
                pass

        with open("data.json", "w", encoding="UTF-8") as file:
            json.dump({"channels": {}, "user_data": {}}, file, indent=4)


if __name__ == '__main__':
    GetMessages().mainloop()
