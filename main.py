import json
import os
import re
import threading
import customtkinter as ctk
import requests as rq
from datetime import datetime, timedelta
from tkinter.messagebox import showerror, showinfo
from CTkListbox import CTkListbox
from typing import Callable


class GetMessages(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.console: ctk.CTkTextbox | None = None
        self.confirm_button: ctk.CTkButton | None = None
        self.loading_bar: ctk.CTkProgressBar | None = None
        self.in_process_flag: bool = False
        self.stop_flag: bool = False

        self.selected_channel = ctk.StringVar(value="Select channel")
        self.selected_mode = ctk.StringVar(value="Select mode")
        self.messages_count: str = ""
        self.streams_ago: str = ""
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
            data: dict = self.get_data()

            if selected_mode == "Select mode":
                self.console_print("Mode not selected!", is_error=True)
                stop()
                return

            if selected_channel == "Select channel":
                self.console_print("Channel not selected!", is_error=True)
                stop()
                return

            if data["user_id"] is None:
                self.console_print("User id not found!", is_error=True)
                stop()
                return

            if selected_mode == "All messages":
                self.loading_bar.configure(mode="indeterminate")
                self.loading_bar.start()
                threading.Thread(target=self.get_messages).start()
            elif selected_mode == "Last ... messages":
                try:
                    messages_count: int = int(self.messages_count)
                    if messages_count <= 0:
                        self.console_print("Invalid messages count!", is_error=True)
                        return

                    threading.Thread(target=self.get_messages, kwargs={"max_messages": messages_count}).start()
                except ValueError:
                    self.console_print("Invalid messages count!", is_error=True)
            elif selected_mode == "From ... stream ago":
                try:
                    last_stream: tuple = self.get_stream_ago(int(self.streams_ago))
                    if last_stream is not None:
                        threading.Thread(target=self.get_messages, kwargs={"last_stream": last_stream}).start()
                except ValueError:
                    self.console_print("Invalid streams ago!", is_error=True)

        def stop() -> None:
            if self.in_process_flag:
                self.stop_flag = True

        def update_messages_count(_) -> None:
            self.messages_count = messages_count.get()
        
        def update_streams_ago(_) -> None:
            self.streams_ago = streams_ago.get()

        self.clear_window()

        self.title("Get Messages History")
        self.geometry("700x400")
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

        messages_count = ctk.CTkEntry(left_side, placeholder_text="Messages count")
        messages_count.pack(pady=(10, 0))
        messages_count.bind("<KeyRelease>", update_messages_count)

        if self.messages_count != "":
            messages_count.insert(0, self.messages_count)

        streams_ago = ctk.CTkEntry(left_side, placeholder_text="... streams ago")
        streams_ago.pack(pady=(10, 0))
        streams_ago.bind("<KeyRelease>", update_streams_ago)

        if self.streams_ago != "":
            streams_ago.insert(0, self.streams_ago)

        ctk.CTkCheckBox(left_side, text="Save messages\nto file",
                        variable=self.save_messages_in_file).pack(pady=(10, 0), anchor=ctk.W, padx=5)
        ctk.CTkCheckBox(left_side, text="With stream\ntimecodes",
                        variable=self.with_timecodes).pack(pady=(10, 0), anchor=ctk.W, padx=5)

        self.confirm_button = ctk.CTkButton(left_side, text="Confirm", font=("times new roman", 16, "bold"),
                                            fg_color="#393939", border_color="#52514e", border_width=1,
                                            hover_color="#242424", command=on_confirm)
        self.confirm_button.pack(pady=10, side=ctk.BOTTOM)

        ctk.CTkButton(left_side, text="Settings", command=self.init_settings_menu).pack(pady=10, side=ctk.BOTTOM)

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
        if self.console.winfo_exists():
            self.console.configure(state=ctk.NORMAL)

            if is_error:
                self.console.insert("1.0", text + "\n", "error")
            else:
                self.console.insert("1.0", text + "\n")

            self.console.configure(state=ctk.DISABLED)
            self.console.see("1.0")
        else:
            if is_error:
                showerror("Error", text)
            else:
                showinfo("Info", text)

    def clear_console(self) -> None:
        self.console.configure(state=ctk.NORMAL)
        self.console.delete("1.0", ctk.END)
        self.console.configure(state=ctk.DISABLED)

    def init_settings_menu(self) -> None:
        self.clear_window()

        self.title("Get Messages History - Settings")
        self.minsize(300, 150)

        ctk.CTkButton(self, text="Back", command=self.init_main_menu, width=40).pack(pady=10, anchor=ctk.W, padx=10)

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack_propagate(False)
        frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=(0, 10))

        settings_frame = ctk.CTkFrame(frame, height=95)
        settings_frame.pack_propagate(False)
        settings_frame.place(relx=0.5, rely=0.5, anchor=ctk.CENTER)

        ctk.CTkButton(settings_frame, text="Manage channels",
                      command=self.init_manage_channels_menu).pack(pady=(15, 0), anchor=ctk.CENTER)

        ctk.CTkButton(settings_frame, text="Enter auth data",
                      command=self.init_auth_data_menu).pack(pady=(10, 15), anchor=ctk.CENTER)

    def init_manage_channels_menu(self) -> None:
        def add_channel(is_user_name: bool = False) -> None:
            text: str = "Enter channel name" if not is_user_name else "Enter user name"
            title: str = "Add channel" if not is_user_name else "Set username"

            channel_name: str = ctk.windows.CTkInputDialog(text=text, title=title).get_input()

            if channel_name:
                user_id: str | None = self.get_id_by_login(channel_name)

                if user_id:
                    if not is_user_name:
                        def write_new_channel(data: dict) -> dict:
                            data["channels"][channel_name] = user_id
                            return data

                        self.update_data(write_new_channel)
                        channels_list.insert(ctk.END, channel_name)
                    else:
                        def write_user_id(data: dict) -> dict:
                            data["user_id"] = [channel_name, user_id]
                            return data

                        self.update_data(write_user_id)
                        username_label.configure(text=f"Current user: {channel_name}")
                elif user_id is None:
                    self.console_print(f"Channel '{channel_name}' not found!", is_error=True)
                    return

        def delete_channel() -> None:
            selected_channel: str | None = channels_list.get()

            if selected_channel is not None and selected_channel:
                def delete_channel_from_data(data: dict) -> dict:
                    del data["channels"][selected_channel]
                    return data

                self.update_data(delete_channel_from_data)

                selected_index = channels_list.curselection()

                channels_list.deselect(selected_index)
                channels_list.delete(selected_index)
            else:
                self.console_print("No channel selected!", is_error=True)
                return

        self.clear_window()

        self.title("Get Messages History - Manage channels")
        self.minsize(400, 345)

        ctk.CTkButton(self, text="Back", command=self.init_settings_menu, width=40).pack(pady=(10, 0), anchor=ctk.W,
                                                                                         padx=10)

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack_propagate(False)
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)

        left_side = ctk.CTkFrame(main_frame, width=150)
        left_side.pack_propagate(False)
        left_side.pack(side=ctk.LEFT, fill=ctk.Y, padx=(0, 10))

        buttons_frame = ctk.CTkFrame(left_side, height=95, fg_color="transparent")
        buttons_frame.pack_propagate(False)
        buttons_frame.place(relx=0.5, rely=0.5, anchor=ctk.CENTER)

        ctk.CTkButton(buttons_frame, text="Add", width=105, command=add_channel).pack(pady=(15, 0), anchor=ctk.CENTER)
        ctk.CTkButton(buttons_frame, text="Remove", width=105, command=delete_channel).pack(pady=(10, 0),
                                                                                            anchor=ctk.CENTER)

        right_side = ctk.CTkFrame(main_frame, fg_color="transparent")
        right_side.pack_propagate(False)
        right_side.pack(side=ctk.RIGHT, fill=ctk.BOTH, expand=True, padx=10)

        channels_list = CTkListbox(right_side, border_width=2)
        channels_list.pack(fill=ctk.BOTH, expand=True)

        bottom_frame = ctk.CTkFrame(right_side, height=40, fg_color="transparent")
        bottom_frame.pack_propagate(False)
        bottom_frame.pack(fill=ctk.X, pady=(10, 0))

        data: dict = self.get_data()
        text: str = f"Current user: {data["user_id"][0] if data["user_id"] else None}"

        username_label = ctk.CTkLabel(bottom_frame, text=text)
        username_label.pack(side=ctk.LEFT)

        ctk.CTkButton(bottom_frame, text="Set username", command=lambda: add_channel(True)).pack(side=ctk.RIGHT)

        for channel in self.get_data()["channels"].keys():
            channels_list.insert(ctk.END, channel)

    def init_auth_data_menu(self) -> None:
        def parse() -> None:
            if self.parse_auth_data(user_data_entry.get("1.0", ctk.END)):
                self.console_print("Auth data parsed successfully!")
                self.init_main_menu()

        def show_explaining() -> None:
            self.console_print("You need to go to Twitch, press F12 -> Network, then find the gql "
                               "request there, right-click -> copy -> Copy as cURL (bash), and then paste this "
                               "text into the text field.")

        def paste_text(_=None):
            user_data_entry.insert(ctk.INSERT, self.clipboard_get())
            return "break"

        self.clear_window()

        self.title("Get Messages History - Parse auth data")
        self.minsize(400, 345)

        upper_frame = ctk.CTkFrame(self, height=29, fg_color="transparent")
        upper_frame.pack_propagate(False)
        upper_frame.pack(fill=ctk.X, pady=10, padx=10)

        ctk.CTkButton(upper_frame, text="Back", command=self.init_settings_menu,
                      width=40).pack(side=ctk.LEFT)

        ctk.CTkButton(upper_frame, text="?", font=("Arial", 17, "bold"), width=30,
                      command=show_explaining).pack(side=ctk.RIGHT)

        user_data_entry = ctk.CTkTextbox(self)
        user_data_entry.pack(padx=10, fill=ctk.BOTH, expand=True)

        user_data_entry.bind("<Control-v>", paste_text)

        ctk.CTkButton(self, text="Parse", command=parse).pack(padx=10, pady=10)

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
                    self.console_print(f"Header '{key}' not found in curl text!", is_error=True)
                    return False

            def write_auth_data(data: dict) -> dict:
                data["user_data"] = headers
                return data

            self.update_data(write_auth_data)

            return True
        else:
            self.console_print("Curl text is empty!", is_error=True)
            return False

    def do_request(self, sha256hash: str, operation_name: str, variables: dict) -> dict | None:
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

        try:
            response: rq.Response = rq.post("https://gql.twitch.tv/gql", headers=headers, json=payload)

            json_: dict = response.json()

            if "error" in json_ or ("errors" in json_ and json_["errors"][0]["message"] == "failed integrity check"):
                self.console_print("Failed integrity check! Auth data is probably out of date.", is_error=True)
                return None

            return json_
        except Exception as e:
            self.console_print(f"An error occurred: {type(e)} ({str(e)})", is_error=True)

            return None

    def get_id_by_login(self, login: str) -> str | None | bool:
        sha256hash: str = "bf6c594605caa0c63522f690156aa04bd434870bf963deb76668c381d16fcaa5"
        operation_name: str = "GetUserID"
        variables: dict = {
            "login": login,
            "lookupType": "ACTIVE"
        }

        response: dict | None = self.do_request(sha256hash, operation_name, variables)

        if response is None:
            return False

        try:
            user: dict | None = response["data"]["user"]

            return response["data"]["user"]["id"] if user else None
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
            "senderID": data["user_id"][1]
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
            json.dump({"channels": {}, "user_data": {}, "user_id": None}, file, indent=4)


if __name__ == '__main__':
    GetMessages().mainloop()
