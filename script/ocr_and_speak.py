#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pillow",
#     "pynput",
#     "pytesseract",
#     "requests",
#     "tesseract",
#     "mss",
# ]
# ///

# -*- coding: utf-8 -*-
"""
OCR自動読み上げスクリプト (macOS版 - GUI)
画面の指定領域を監視して、新しいテキストが表示されたら自動で読み上げます
"""

import time
import sys
import subprocess
import hashlib
import re
import os
from pathlib import Path
from typing import Optional, Tuple, Callable, List, Dict
from PIL import Image
import pytesseract
import requests
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, Toplevel, Label, Canvas
from mss import mss


class OCRReader:
    def __init__(self, gui_callback: Optional[Callable[[str], None]] = None):
        self.region: Optional[Tuple[int, int, int, int]] = None  # (x1, y1, x2, y2) 監視領域
        self.last_text_hash: Optional[str] = None  # 最後に読み上げたテキストのハッシュ
        self.is_running: bool = False
        self.is_paused: bool = False
        self.check_interval: float = 1.0  # チェック間隔（秒）
        self.voicevox_available: bool = False
        self.speaker_id: int = 3  # VOICEVOXの話者ID（3=ずんだもん ノーマル）
        self.speech_speed: float = 1.0  # 読み上げ速度（1.0が標準、0.5-2.0程度）
        self.gui_callback = gui_callback  # GUIへのコールバック
        self.ignore_patterns: List[re.Pattern[str]] = []  # 無視する正規表現パターンのリスト
        self.pronunciation_dict: Dict[str, str] = {}  # 読み方辞書 {単語: 読み方}

        # VOICEVOXが使えるかチェック
        self.check_voicevox()

    def load_pronunciation_dict(self, file_path: str = "~/system/yomi.txt") -> None:
        """読み方辞書ファイルを読み込み"""
        try:
            expanded_path = Path(file_path).expanduser()
            if not expanded_path.exists():
                self.log(f"読み方辞書が見つかりません: {expanded_path}")
                return

            with open(expanded_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:  # 空行をスキップ
                        continue
                    parts = line.split("\t")
                    if len(parts) == 2:
                        word, pronunciation = parts
                        self.pronunciation_dict[word] = pronunciation

            self.log(f"✓ 読み方辞書を読み込みました: {len(self.pronunciation_dict)}件")
        except Exception as e:
            self.log(f"読み方辞書の読み込みエラー: {e}")

    def apply_pronunciation_rules(self, text: str) -> str:
        """テキストに読み方ルールを適用"""
        result = text
        for word, pronunciation in self.pronunciation_dict.items():
            result = result.replace(word, pronunciation)
        return result

    def check_voicevox(self) -> bool:
        """VOICEVOXが起動しているかチェック"""
        try:
            response = requests.get("http://localhost:50021/speakers", timeout=1)
            if response.status_code == 200:
                self.voicevox_available = True
                return True
        except Exception:
            pass

        self.voicevox_available = False
        return False

    def get_voicevox_speakers(self) -> list:
        """利用可能な話者リストを取得"""
        try:
            response = requests.get("http://localhost:50021/speakers", timeout=1)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []

    def set_region(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """監視領域を設定"""
        try:
            self.region = (x1, y1, x2, y2)
            return True
        except Exception:
            return False

    def add_ignore_pattern(self, pattern: str) -> bool:
        """無視するパターンを追加"""
        try:
            compiled_pattern = re.compile(pattern)
            self.ignore_patterns.append(compiled_pattern)
            return True
        except re.error as e:
            self.log(f"正規表現エラー: {e}")
            return False

    def remove_ignore_pattern(self, index: int) -> bool:
        """指定したインデックスのパターンを削除"""
        try:
            if 0 <= index < len(self.ignore_patterns):
                self.ignore_patterns.pop(index)
                return True
            return False
        except Exception:
            return False

    def clear_ignore_patterns(self) -> None:
        """すべてのパターンをクリア"""
        self.ignore_patterns.clear()

    def should_ignore_text(self, text: str) -> bool:
        """テキストが無視パターンにマッチするかチェック（完全一致）"""
        for pattern in self.ignore_patterns:
            if pattern.fullmatch(text):
                return True
        return False

    def capture_all_displays_as_one(self) -> Optional[Image.Image]:
        """全ディスプレイを1つの画像としてキャプチャ"""
        try:
            with mss() as sct:
                # Monitor 0は全ディスプレイの組み合わせ
                monitor = sct.monitors[0]
                screenshot = sct.grab(monitor)
                # PIL Imageに変換
                return Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
        except Exception as e:
            self.log(f"キャプチャエラー: {e}")
            return None

    def capture_region(self) -> Optional[Image.Image]:
        """指定領域をキャプチャ（複数ディスプレイ対応）"""
        if not self.region:
            return None

        # 全ディスプレイをキャプチャ
        full_screen = self.capture_all_displays_as_one()
        if not full_screen:
            return None

        try:
            x1, y1, x2, y2 = self.region

            # 座標が画面内に収まっているか確認
            screen_width, screen_height = full_screen.size
            if x1 < 0 or y1 < 0 or x2 > screen_width or y2 > screen_height:
                self.log(f"警告: 座標が画面外です ({x1},{y1},{x2},{y2}) 画面サイズ: {screen_width}x{screen_height}")

            # 画像を切り出し
            cropped = full_screen.crop((x1, y1, x2, y2))
            return cropped
        except Exception as e:
            self.log(f"キャプチャエラー: {e}")
            return None

    def ocr_image(self, image: Image.Image) -> str:
        """画像からテキストを抽出"""
        try:
            # 日本語OCR
            text = pytesseract.image_to_string(image, lang='jpn')
            # クリーンアップ
            text = text.strip()
            text = ' '.join(text.split())  # 余分な空白を削除
            return text
        except Exception as e:
            self.log(f"OCRエラー: {e}")
            return ""

    def text_to_hash(self, text: str) -> str:
        """テキストをハッシュ化（重複チェック用）"""
        return hashlib.md5(text.encode()).hexdigest()

    def speak_voicevox(self, text: str) -> bool:
        """VOICEVOXで読み上げ"""
        try:
            # 音声合成用のクエリを作成
            query_response = requests.post(
                f"http://localhost:50021/audio_query?text={text}&speaker={self.speaker_id}",
                timeout=5
            )

            if query_response.status_code == 200:
                # クエリデータを取得して速度を調整
                query_data = query_response.json()
                query_data["speedScale"] = self.speech_speed

                # 音声を合成
                audio_response = requests.post(
                    f"http://localhost:50021/synthesis?speaker={self.speaker_id}",
                    json=query_data,
                    timeout=10
                )

                if audio_response.status_code == 200:
                    # 音声を一時ファイルに保存
                    audio_file = "/tmp/ocr_speak_audio.wav"
                    with open(audio_file, "wb") as f:
                        f.write(audio_response.content)

                    # afplayで再生
                    subprocess.run(["afplay", audio_file], check=True)
                    return True
        except Exception as e:
            self.log(f"VOICEVOX読み上げエラー: {e}")

        return False

    def speak_say(self, text: str) -> bool:
        """macOSのsayコマンドで読み上げ"""
        try:
            # 日本語音声を使用
            # sayコマンドの速度は words per minute (wpm)で指定
            # デフォルトは175wpm、速度倍率を適用
            wpm = int(175 * self.speech_speed)
            subprocess.run(["say", "-v", "Kyoko", "-r", str(wpm), text], check=True)
            return True
        except Exception as e:
            self.log(f"say読み上げエラー: {e}")
            return False

    def speak(self, text: str) -> None:
        """テキストを読み上げ"""
        if not text or len(text) < 3:  # 短すぎるテキストは無視
            return

        display_text = f"{text[:50]}{'...' if len(text) > 50 else ''}"
        self.log(f"📢 読み上げ: {display_text}")

        # 読み方ルールを適用
        pronunciation_text = self.apply_pronunciation_rules(text)
        if pronunciation_text != text:
            self.log(f"   → {pronunciation_text[:50]}{'...' if len(pronunciation_text) > 50 else ''}")

        # VOICEVOXが使える場合は優先
        if self.voicevox_available:
            if self.speak_voicevox(pronunciation_text):
                return
            # 失敗したらsayにフォールバック

        # macOSの標準音声で読み上げ
        self.speak_say(pronunciation_text)

    def monitor_loop(self) -> None:
        """監視ループ"""
        self.log("監視を開始しました")

        while self.is_running:
            if not self.is_paused:
                # 画面をキャプチャ
                image = self.capture_region()

                if image:
                    # OCR実行
                    text = self.ocr_image(image)

                    if text:
                        # 無視パターンチェック
                        if self.should_ignore_text(text):
                            self.log(f"🚫 無視: {text[:30]}{'...' if len(text) > 30 else ''}")
                        else:
                            # ハッシュを計算
                            text_hash = self.text_to_hash(text)

                            # 新しいテキストなら読み上げ
                            if text_hash != self.last_text_hash:
                                self.last_text_hash = text_hash
                                self.speak(text)

            # 指定間隔待機
            time.sleep(self.check_interval)

    def start(self) -> bool:
        """監視を開始"""
        if not self.region:
            self.log("✗ 監視領域が設定されていません")
            return False

        self.is_running = True
        self.is_paused = False

        # 監視ループをスレッドで実行
        monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        monitor_thread.start()

        return True

    def stop(self) -> None:
        """監視を停止"""
        self.is_running = False
        self.log("監視を停止しました")

    def pause(self) -> None:
        """監視を一時停止"""
        self.is_paused = True
        self.log("⏸️  一時停止")

    def resume(self) -> None:
        """監視を再開"""
        self.is_paused = False
        self.log("▶️  再開")

    def log(self, message: str) -> None:
        """ログメッセージを出力"""
        if self.gui_callback:
            self.gui_callback(message)
        else:
            print(message)


class OCRAndSpeakGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("OCR自動読み上げツール")
        self.root.geometry("700x600")

        self.reader = OCRReader(gui_callback=self.add_log)

        self.setup_ui()
        self.update_voicevox_status()

        # UIセットアップ後に読み方辞書を再読み込み（ログ表示のため）
        self.reader.load_pronunciation_dict()

    def setup_ui(self) -> None:
        """UIをセットアップ"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="wens")

        # 領域設定セクション
        region_frame = ttk.LabelFrame(main_frame, text="監視領域の設定", padding="10")
        region_frame.grid(row=0, column=0, columnspan=2, sticky="we", pady=5)

        ttk.Label(region_frame, text="左上X:").grid(row=0, column=0, sticky=tk.W)
        self.x1_entry = ttk.Entry(region_frame, width=10)
        self.x1_entry.grid(row=0, column=1, padx=5)

        ttk.Label(region_frame, text="左上Y:").grid(row=0, column=2, sticky=tk.W)
        self.y1_entry = ttk.Entry(region_frame, width=10)
        self.y1_entry.grid(row=0, column=3, padx=5)

        ttk.Label(region_frame, text="右下X:").grid(row=1, column=0, sticky=tk.W)
        self.x2_entry = ttk.Entry(region_frame, width=10)
        self.x2_entry.grid(row=1, column=1, padx=5)

        ttk.Label(region_frame, text="右下Y:").grid(row=1, column=2, sticky=tk.W)
        self.y2_entry = ttk.Entry(region_frame, width=10)
        self.y2_entry.grid(row=1, column=3, padx=5)

        ttk.Button(region_frame, text="領域を設定", command=self.set_region).grid(
            row=0, column=4, rowspan=2, padx=10, sticky="wens"
        )

        ttk.Button(region_frame, text="テストキャプチャ", command=self.test_capture).grid(
            row=0, column=5, rowspan=2, padx=5, sticky="wens"
        )

        ttk.Button(region_frame, text="クリックで選択", command=self.select_by_click).grid(
            row=0, column=6, rowspan=2, padx=5, sticky="wens"
        )

        # 設定セクション
        settings_frame = ttk.LabelFrame(main_frame, text="設定", padding="10")
        settings_frame.grid(row=1, column=0, columnspan=2, sticky="we", pady=5)

        ttk.Label(settings_frame, text="チェック間隔(秒):").grid(row=0, column=0, sticky=tk.W)
        self.interval_entry = ttk.Entry(settings_frame, width=10)
        self.interval_entry.insert(0, "1.0")
        self.interval_entry.grid(row=0, column=1, padx=5)

        ttk.Label(settings_frame, text="話者ID:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        self.speaker_entry = ttk.Entry(settings_frame, width=10)
        self.speaker_entry.insert(0, "3")
        self.speaker_entry.grid(row=0, column=3, padx=5)

        ttk.Label(settings_frame, text="速度:").grid(row=0, column=4, sticky=tk.W, padx=(20, 0))
        self.speed_entry = ttk.Entry(settings_frame, width=10)
        self.speed_entry.insert(0, "1.0")
        self.speed_entry.grid(row=0, column=5, padx=5)

        ttk.Button(settings_frame, text="設定を適用", command=self.apply_settings).grid(
            row=0, column=6, padx=10
        )

        # 無視パターンセクション
        ignore_frame = ttk.LabelFrame(main_frame, text="無視パターン (正規表現)", padding="10")
        ignore_frame.grid(row=2, column=0, columnspan=2, sticky="we", pady=5)

        pattern_input_frame = ttk.Frame(ignore_frame)
        pattern_input_frame.grid(row=0, column=0, columnspan=2, sticky="we", pady=5)

        ttk.Label(pattern_input_frame, text="パターン:").pack(side=tk.LEFT)
        self.pattern_entry = ttk.Entry(pattern_input_frame, width=40)
        self.pattern_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(pattern_input_frame, text="追加", command=self.add_pattern).pack(side=tk.LEFT, padx=5)
        ttk.Button(pattern_input_frame, text="クリア", command=self.clear_patterns).pack(side=tk.LEFT, padx=5)

        # パターンリスト表示
        list_frame = ttk.Frame(ignore_frame)
        list_frame.grid(row=1, column=0, columnspan=2, sticky="we", pady=5)

        self.pattern_listbox = tk.Listbox(list_frame, height=4, width=60)
        self.pattern_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.pattern_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.pattern_listbox.config(yscrollcommand=scrollbar.set)

        ttk.Button(ignore_frame, text="選択を削除", command=self.remove_selected_pattern).grid(
            row=2, column=0, columnspan=2, pady=5
        )

        # VOICEVOXステータス
        status_frame = ttk.Frame(settings_frame)
        status_frame.grid(row=1, column=0, columnspan=5, pady=5, sticky=tk.W)

        ttk.Label(status_frame, text="VOICEVOX:").pack(side=tk.LEFT)
        self.voicevox_status_label = ttk.Label(status_frame, text="確認中...")
        self.voicevox_status_label.pack(side=tk.LEFT, padx=5)

        ttk.Button(status_frame, text="再確認", command=self.update_voicevox_status).pack(
            side=tk.LEFT, padx=5
        )

        # コントロールボタン
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=3, column=0, columnspan=2, pady=10)

        self.start_button = ttk.Button(
            control_frame, text="▶️ 開始", command=self.start_monitoring, width=15
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.pause_button = ttk.Button(
            control_frame, text="⏸️  一時停止", command=self.pause_monitoring,
            width=15, state=tk.DISABLED
        )
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            control_frame, text="⏹️  停止", command=self.stop_monitoring,
            width=15, state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # ログ表示
        log_frame = ttk.LabelFrame(main_frame, text="ログ", padding="10")
        log_frame.grid(row=4, column=0, columnspan=2, sticky="wens", pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=70)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # グリッドの重みを設定（リサイズ対応）
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)

    def add_log(self, message: str) -> None:
        """ログを追加"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)  # 自動スクロール

    def set_region(self) -> None:
        """監視領域を設定"""
        try:
            x1 = int(self.x1_entry.get())
            y1 = int(self.y1_entry.get())
            x2 = int(self.x2_entry.get())
            y2 = int(self.y2_entry.get())

            if self.reader.set_region(x1, y1, x2, y2):
                self.add_log(f"✓ 監視領域を設定しました: ({x1}, {y1}, {x2}, {y2})")
            else:
                messagebox.showerror("エラー", "領域の設定に失敗しました")
        except ValueError:
            messagebox.showerror("エラー", "数値を入力してください")

    def select_by_click(self) -> None:
        """画面のスクリーンショットから領域を選択（複数ディスプレイ対応）"""
        self.add_log("画面全体をキャプチャしています...")

        # 全ディスプレイをキャプチャ
        full_screen = self.reader.capture_all_displays_as_one()

        if full_screen:
            self.add_log("✓ キャプチャ完了。プレビューウィンドウで領域を選択してください")
            self._show_region_selector(full_screen)
        else:
            self.add_log("✗ キャプチャに失敗しました")
            messagebox.showerror("エラー", "画面のキャプチャに失敗しました")

    def _update_coordinates(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """座標を受け取ってGUIを更新"""
        self.x1_entry.delete(0, tk.END)
        self.x1_entry.insert(0, str(x1))

        self.y1_entry.delete(0, tk.END)
        self.y1_entry.insert(0, str(y1))

        self.x2_entry.delete(0, tk.END)
        self.x2_entry.insert(0, str(x2))

        self.y2_entry.delete(0, tk.END)
        self.y2_entry.insert(0, str(y2))

        # 自動的に領域を設定
        if self.reader.set_region(x1, y1, x2, y2):
            self.add_log(f"✓ 監視領域を設定しました: ({x1}, {y1}, {x2}, {y2})")

    def test_capture(self) -> None:
        """テストキャプチャを実行して画像を表示"""
        try:
            x1 = int(self.x1_entry.get())
            y1 = int(self.y1_entry.get())
            x2 = int(self.x2_entry.get())
            y2 = int(self.y2_entry.get())

            self.reader.set_region(x1, y1, x2, y2)
            image = self.reader.capture_region()

            if image:
                self.add_log("✓ テスト画像をキャプチャしました")
                self._show_image_preview(image, "テストキャプチャ")
            else:
                messagebox.showerror("エラー", "キャプチャに失敗しました")
        except ValueError:
            messagebox.showerror("エラー", "数値を入力してください")

    def _pil_to_photoimage(self, pil_image: Image.Image) -> tk.PhotoImage:
        """PIL ImageをPhotoImageに変換（互換性の高い方法）"""
        # RGBモードに変換
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        # PPM形式の文字列に変換
        import io
        with io.BytesIO() as output:
            pil_image.save(output, format="PPM")
            data = output.getvalue()

        # tkinter.PhotoImageとして読み込む
        return tk.PhotoImage(data=data)

    def _show_image_preview(self, image: Image.Image, title: str = "画像プレビュー") -> None:
        """画像をプレビューウィンドウで表示"""
        preview_window = Toplevel(self.root)
        preview_window.title(title)

        # 画像をリサイズ（大きすぎる場合）
        max_width, max_height = 800, 600
        img_width, img_height = image.size

        if img_width > max_width or img_height > max_height:
            ratio = min(max_width / img_width, max_height / img_height)
            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)
            display_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            display_image = image

        # tkinter用の画像に変換
        photo = self._pil_to_photoimage(display_image)

        # ラベルに画像を表示
        label = Label(preview_window, image=photo)
        label._image = photo  # type: ignore  # 参照を保持（GC防止）
        label.pack()

        # 閉じるボタン
        close_button = ttk.Button(preview_window, text="閉じる", command=preview_window.destroy)
        close_button.pack(pady=10)

    def _show_region_selector(self, screen_image: Image.Image) -> None:
        """画面キャプチャから領域を選択するウィンドウを表示"""
        selector_window = Toplevel(self.root)
        selector_window.title("領域を選択")

        # 画面を縮小表示
        max_width, max_height = 1200, 800
        img_width, img_height = screen_image.size
        scale_ratio = min(max_width / img_width, max_height / img_height, 1.0)

        new_width = int(img_width * scale_ratio)
        new_height = int(img_height * scale_ratio)
        display_image = screen_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # キャンバスを作成
        canvas = Canvas(selector_window, width=new_width, height=new_height, cursor="cross")
        canvas.pack()

        # 画像をキャンバスに表示
        photo = self._pil_to_photoimage(display_image)
        canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        canvas._image = photo  # type: ignore  # 参照を保持

        # 選択状態を保持
        selection_data = {
            "start_x": None,
            "start_y": None,
            "rect_id": None,
            "scale_ratio": scale_ratio
        }

        def on_mouse_down(event: tk.Event) -> None:  # type: ignore
            """マウスボタン押下"""
            selection_data["start_x"] = event.x
            selection_data["start_y"] = event.y

        def on_mouse_drag(event: tk.Event) -> None:  # type: ignore
            """マウスドラッグ"""
            if selection_data["start_x"] is not None and selection_data["start_y"] is not None:
                # 既存の矩形を削除
                if selection_data["rect_id"]:
                    canvas.delete(selection_data["rect_id"])

                # 新しい矩形を描画
                selection_data["rect_id"] = canvas.create_rectangle(
                    selection_data["start_x"], selection_data["start_y"],
                    event.x, event.y,
                    outline="red", width=2
                )

        def on_mouse_up(event: tk.Event) -> None:  # type: ignore
            """マウスボタン解放"""
            if selection_data["start_x"] is not None and selection_data["start_y"] is not None:
                # 座標を正規化（元の画面サイズに変換）
                x1 = int(min(selection_data["start_x"], event.x) / scale_ratio)
                y1 = int(min(selection_data["start_y"], event.y) / scale_ratio)
                x2 = int(max(selection_data["start_x"], event.x) / scale_ratio)
                y2 = int(max(selection_data["start_y"], event.y) / scale_ratio)

                # 座標を設定
                self._update_coordinates(x1, y1, x2, y2)

                # ウィンドウを閉じる
                selector_window.destroy()

        # マウスイベントをバインド
        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)

        # 説明ラベル
        info_label = Label(
            selector_window,
            text="マウスでドラッグして領域を選択してください",
            bg="yellow"
        )
        info_label.pack(pady=5)

        # キャンセルボタン
        cancel_button = ttk.Button(
            selector_window,
            text="キャンセル",
            command=selector_window.destroy
        )
        cancel_button.pack(pady=5)

    def apply_settings(self) -> None:
        """設定を適用"""
        try:
            interval = float(self.interval_entry.get())
            speaker_id = int(self.speaker_entry.get())
            speed = float(self.speed_entry.get())

            # 速度の妥当性をチェック
            if speed < 0.3 or speed > 3.0:
                messagebox.showwarning("警告", "速度は0.3から3.0の範囲で指定してください")
                return

            self.reader.check_interval = interval
            self.reader.speaker_id = speaker_id
            self.reader.speech_speed = speed

            self.add_log(f"✓ チェック間隔: {interval}秒, 話者ID: {speaker_id}, 速度: {speed}x")
        except ValueError:
            messagebox.showerror("エラー", "正しい数値を入力してください")

    def add_pattern(self) -> None:
        """無視パターンを追加"""
        pattern = self.pattern_entry.get().strip()
        if not pattern:
            messagebox.showwarning("警告", "パターンを入力してください")
            return

        if self.reader.add_ignore_pattern(pattern):
            self.pattern_listbox.insert(tk.END, pattern)
            self.pattern_entry.delete(0, tk.END)
            self.add_log(f"✓ パターンを追加: {pattern}")
        else:
            messagebox.showerror("エラー", "正規表現が無効です")

    def remove_selected_pattern(self) -> None:
        """選択したパターンを削除"""
        selection = self.pattern_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "削除するパターンを選択してください")
            return

        index = selection[0]
        pattern = self.pattern_listbox.get(index)

        if self.reader.remove_ignore_pattern(index):
            self.pattern_listbox.delete(index)
            self.add_log(f"✓ パターンを削除: {pattern}")

    def clear_patterns(self) -> None:
        """すべてのパターンをクリア"""
        if self.pattern_listbox.size() == 0:
            messagebox.showinfo("情報", "パターンがありません")
            return

        if messagebox.askyesno("確認", "すべてのパターンをクリアしますか?"):
            self.reader.clear_ignore_patterns()
            self.pattern_listbox.delete(0, tk.END)
            self.add_log("✓ すべてのパターンをクリアしました")

    def update_voicevox_status(self) -> None:
        """VOICEVOXの状態を更新"""
        if self.reader.check_voicevox():
            self.voicevox_status_label.config(text="✓ 利用可能", foreground="green")
            self.add_log("✓ VOICEVOX が見つかりました")

            # 話者リストを表示
            speakers = self.reader.get_voicevox_speakers()
            if speakers:
                self.add_log("利用可能な話者:")
                for speaker in speakers[:5]:  # 最初の5人を表示
                    speaker_info = f"  - {speaker['name']} (ID: {speaker['styles'][0]['id']})"
                    self.add_log(speaker_info)
        else:
            self.voicevox_status_label.config(text="✗ 利用不可 (say使用)", foreground="orange")
            self.add_log("✗ VOICEVOX が見つかりません。macOS say コマンドを使用します")

    def start_monitoring(self) -> None:
        """監視を開始"""
        if not self.reader.region:
            messagebox.showwarning("警告", "監視領域を設定してください")
            return

        if self.reader.start():
            self.start_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.NORMAL, text="⏸️  一時停止")
            self.stop_button.config(state=tk.NORMAL)

    def pause_monitoring(self) -> None:
        """監視を一時停止/再開"""
        if self.reader.is_paused:
            self.reader.resume()
            self.pause_button.config(text="⏸️  一時停止")
        else:
            self.reader.pause()
            self.pause_button.config(text="▶️  再開")

    def stop_monitoring(self) -> None:
        """監視を停止"""
        self.reader.stop()
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED, text="⏸️  一時停止")
        self.stop_button.config(state=tk.DISABLED)


def main() -> None:
    root = tk.Tk()
    OCRAndSpeakGUI(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ 中断されました")
        sys.exit(0)
