#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
#     "pillow",
# ]
# ///

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import argparse
import base64
import os
import sys
import threading
from pathlib import Path
from typing import Optional
import requests
from io import BytesIO

from PIL import Image, ImageTk


# --- Constants ---
DEFAULT_MODEL = "gpt-image-1.5"
DEFAULT_SIZE = "1024x1024"
DEFAULT_TIMEOUT = 300
DEBUG = False  # Will be set by command line argument

VALID_SIZES = {
    "gpt-image-1.5": ["1024x1024", "1536x1024", "1024x1536"],
    "gpt-image-1": ["1024x1024", "1536x1024", "1024x1536"],
    "gpt-image-1-mini": ["1024x1024", "1536x1024", "1024x1536"],
    "dall-e-2": ["256x256", "512x512", "1024x1024"],
    "dall-e-3": ["1024x1024", "1792x1024", "1024x1792"],
}


def debug_print(msg: str) -> None:
    """Print debug message if DEBUG is enabled."""
    if DEBUG:
        print(f"[DEBUG] {msg}", file=sys.stderr)


class ImageGeneratorApp:
    """
    A Tkinter application to generate or edit images using OpenAI's image API.
    """

    def __init__(self, master: tk.Tk) -> None:
        """Initialize the application."""
        self.master = master
        self.master.title("AI Image Generator")
        self.master.geometry("900x800")

        # --- Application State ---
        self.current_images: list[bytes] = []
        self.current_pil_images: list[Image.Image] = []
        self.current_photo_images: list[ImageTk.PhotoImage] = []
        self.current_image_index = 0
        self.is_generating = False

        # Input image paths for edit mode
        self.input_image_paths: list[str] = []
        self.mask_image_path: Optional[str] = None

        # --- Setup GUI ---
        self.setup_gui()

        # --- Handle Closing ---
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # --- Load Test Image (after GUI is ready) ---
        # Schedule image loading after the main loop starts
        self.master.after(100, self.load_test_image)

    def setup_gui(self) -> None:
        """Creates the GUI elements."""
        # Create main container with two columns
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)

        # --- Left Panel: Controls ---
        controls_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        controls_frame.grid(row=0, column=0, rowspan=5, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        row = 0

        # Mode selection
        ttk.Label(controls_frame, text="Mode:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.mode_var = tk.StringVar(value="draw")
        mode_frame = ttk.Frame(controls_frame)
        mode_frame.grid(row=row, column=1, sticky=tk.W, pady=5)
        ttk.Radiobutton(mode_frame, text="Draw", variable=self.mode_var, value="draw",
                       command=self.on_mode_change).pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="Edit", variable=self.mode_var, value="edit",
                       command=self.on_mode_change).pack(side=tk.LEFT, padx=(10, 0))
        row += 1

        # Prompt
        ttk.Label(controls_frame, text="Prompt:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.prompt_text = tk.Text(controls_frame, height=4, width=40, wrap=tk.WORD)
        self.prompt_text.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # Model selection
        ttk.Label(controls_frame, text="Model:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.model_combo = ttk.Combobox(controls_frame, textvariable=self.model_var, state="readonly",
                                       values=list(VALID_SIZES.keys()))
        self.model_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        self.model_combo.bind("<<ComboboxSelected>>", self.on_model_change)
        row += 1

        # Size selection
        ttk.Label(controls_frame, text="Size:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.size_var = tk.StringVar(value=DEFAULT_SIZE)
        self.size_combo = ttk.Combobox(controls_frame, textvariable=self.size_var, state="readonly",
                                      values=VALID_SIZES[DEFAULT_MODEL])
        self.size_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # Background (for gpt-image models)
        ttk.Label(controls_frame, text="Background:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.background_var = tk.StringVar(value="auto")
        self.background_combo = ttk.Combobox(controls_frame, textvariable=self.background_var,
                                            state="readonly", values=["auto", "transparent", "opaque"])
        self.background_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # Number of images
        ttk.Label(controls_frame, text="Count:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.count_var = tk.IntVar(value=1)
        self.count_spin = ttk.Spinbox(controls_frame, from_=1, to=10, textvariable=self.count_var, width=10)
        self.count_spin.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Timeout
        ttk.Label(controls_frame, text="Timeout (s):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.timeout_var = tk.IntVar(value=DEFAULT_TIMEOUT)
        self.timeout_spin = ttk.Spinbox(controls_frame, from_=30, to=600, textvariable=self.timeout_var, width=10)
        self.timeout_spin.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Separator
        ttk.Separator(controls_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2,
                                                                  sticky=(tk.W, tk.E), pady=10)
        row += 1

        # Image input (edit mode)
        self.image_input_label = ttk.Label(controls_frame, text="Input Images:")
        self.image_input_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.image_input_button = ttk.Button(controls_frame, text="Select Images...",
                                            command=self.select_input_images)
        self.image_input_button.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        self.image_list_label = ttk.Label(controls_frame, text="No images selected", foreground="gray")
        self.image_list_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        row += 1

        # Mask input (edit mode)
        self.mask_input_label = ttk.Label(controls_frame, text="Mask Image:")
        self.mask_input_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.mask_input_button = ttk.Button(controls_frame, text="Select Mask...",
                                           command=self.select_mask_image)
        self.mask_input_button.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        self.mask_label = ttk.Label(controls_frame, text="No mask selected", foreground="gray")
        self.mask_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        row += 1

        # Separator
        ttk.Separator(controls_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2,
                                                                  sticky=(tk.W, tk.E), pady=10)
        row += 1

        # Generate button
        self.generate_button = ttk.Button(controls_frame, text="Generate Image",
                                         command=self.generate_image)
        self.generate_button.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        row += 1

        # Save button
        self.save_button = ttk.Button(controls_frame, text="Save Image(s)...",
                                     command=self.save_images, state=tk.DISABLED)
        self.save_button.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # Status label
        self.status_label = ttk.Label(controls_frame, text="Ready", foreground="green")
        self.status_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)

        # --- Right Panel: Image Display ---
        display_frame = ttk.LabelFrame(main_frame, text="Generated Image", padding="10")
        display_frame.grid(row=0, column=1, rowspan=4, sticky=(tk.W, tk.E, tk.N, tk.S))
        display_frame.columnconfigure(0, weight=1)
        display_frame.rowconfigure(0, weight=1)

        # Canvas for image display
        self.image_canvas = tk.Canvas(display_frame, bg="white", width=600, height=600)
        self.image_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Navigation frame (for multiple images)
        nav_frame = ttk.Frame(main_frame)
        nav_frame.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=(10, 0))

        self.prev_button = ttk.Button(nav_frame, text="< Previous", command=self.show_previous_image,
                                      state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.image_counter_label = ttk.Label(nav_frame, text="")
        self.image_counter_label.pack(side=tk.LEFT, expand=True)

        self.next_button = ttk.Button(nav_frame, text="Next >", command=self.show_next_image,
                                      state=tk.DISABLED)
        self.next_button.pack(side=tk.RIGHT, padx=5)

        # Initialize mode
        self.on_mode_change()

    def on_mode_change(self) -> None:
        """Handle mode change (draw/edit)."""
        mode = self.mode_var.get()
        if mode == "edit":
            # Show edit-specific controls
            self.image_input_label.grid()
            self.image_input_button.grid()
            self.image_list_label.grid()
            self.mask_input_label.grid()
            self.mask_input_button.grid()
            self.mask_label.grid()

            # Update model if dall-e-3 is selected
            if self.model_var.get() == "dall-e-3":
                self.model_var.set("dall-e-2")
                self.on_model_change()
        else:
            # Hide edit-specific controls
            self.image_input_label.grid_remove()
            self.image_input_button.grid_remove()
            self.image_list_label.grid_remove()
            self.mask_input_label.grid_remove()
            self.mask_input_button.grid_remove()
            self.mask_label.grid_remove()

    def on_model_change(self, event: Optional[tk.Event] = None) -> None:
        """Handle model change to update available sizes."""
        model = self.model_var.get()
        sizes = VALID_SIZES.get(model, [DEFAULT_SIZE])
        self.size_combo['values'] = sizes

        # Reset to first size if current size is not valid
        if self.size_var.get() not in sizes:
            self.size_var.set(sizes[0])

    def load_test_image(self) -> None:
        """Load and display a test image at startup."""
        test_image_path = Path.home() / "dotfiles" / "kcrt.png"
        debug_print(f"Attempting to load test image from: {test_image_path}")

        if not test_image_path.exists():
            debug_print(f"Test image not found at {test_image_path}")
            self.status_label.config(text="Ready (test image not found)", foreground="orange")
            return

        try:
            debug_print("Opening test image with PIL")
            pil_img = Image.open(test_image_path)
            debug_print(f"Test image loaded: size={pil_img.size}, mode={pil_img.mode}")

            # Store as current images
            self.current_pil_images = [pil_img]

            # Convert to bytes for consistency
            img_bytes = BytesIO()
            pil_img.save(img_bytes, format='PNG')
            self.current_images = [img_bytes.getvalue()]

            debug_print("Displaying test image")
            self.current_image_index = 0
            self.display_current_image()

            self.save_button.config(state=tk.NORMAL)
            self.status_label.config(text="Test image loaded", foreground="blue")
            debug_print("Test image loaded successfully")

        except Exception as e:
            debug_print(f"Error loading test image: {e}")
            import traceback
            if DEBUG:
                traceback.print_exc()
            self.status_label.config(text=f"Error loading test image: {e}", foreground="red")

    def select_input_images(self) -> None:
        """Open file dialog to select input images for edit mode."""
        files = filedialog.askopenfilenames(
            title="Select Input Images",
            filetypes=[("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")]
        )
        if files:
            self.input_image_paths = list(files)
            if len(self.input_image_paths) == 1:
                self.image_list_label.config(text=Path(self.input_image_paths[0]).name, foreground="black")
            else:
                self.image_list_label.config(text=f"{len(self.input_image_paths)} images selected",
                                            foreground="black")

    def select_mask_image(self) -> None:
        """Open file dialog to select mask image for edit mode."""
        file = filedialog.askopenfilename(
            title="Select Mask Image",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if file:
            self.mask_image_path = file
            self.mask_label.config(text=Path(file).name, foreground="black")

    def generate_image(self) -> None:
        """Start image generation in a background thread."""
        if self.is_generating:
            messagebox.showwarning("Busy", "Image generation is already in progress.")
            return

        # Validate inputs
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            messagebox.showerror("Error", "Please enter a prompt.")
            return

        mode = self.mode_var.get()
        if mode == "edit" and not self.input_image_paths:
            messagebox.showerror("Error", "Please select input image(s) for edit mode.")
            return

        # Disable controls
        self.is_generating = True
        self.generate_button.config(state=tk.DISABLED)
        self.save_button.config(state=tk.DISABLED)
        self.status_label.config(text="Generating...", foreground="orange")

        # Start generation in background thread
        thread = threading.Thread(target=self._generate_image_thread, args=(prompt, mode), daemon=True)
        thread.start()

    def _generate_image_thread(self, prompt: str, mode: str) -> None:
        """Background thread for image generation."""
        try:
            model = self.model_var.get()
            size = self.size_var.get()
            n = self.count_var.get()
            timeout = self.timeout_var.get()
            background = self.background_var.get() if model.startswith("gpt-image") else None

            debug_print(f"Starting generation: mode={mode}, model={model}, size={size}, n={n}")

            if mode == "draw":
                images = self._call_generate_api(prompt, model, size, n, background, timeout)
            else:
                images = self._call_edit_api(prompt, self.input_image_paths, model, size, n,
                                            background, self.mask_image_path, timeout)

            debug_print(f"Generation successful: received {len(images)} image(s)")

            # Update UI in main thread
            self.master.after(0, self._on_generation_success, images)

        except Exception as e:
            debug_print(f"Generation failed: {e}")
            import traceback
            if DEBUG:
                traceback.print_exc()
            # Update UI in main thread
            self.master.after(0, self._on_generation_error, str(e))

    def _call_generate_api(self, prompt: str, model: str, size: str, n: int,
                          background: Optional[str], timeout: int) -> list[bytes]:
        """Call the OpenAI image generation API."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        org_id = os.environ.get("OPENAI_ORG_ID")

        payload = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "size": size
        }

        if model.startswith("gpt-image"):
            payload["moderation"] = "low"
            if background:
                payload["background"] = background
        else:
            payload["response_format"] = "b64_json"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        if org_id:
            headers["OpenAI-Organization"] = org_id

        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=payload,
            timeout=timeout
        )

        # Enhanced error handling with detailed API response
        if not response.ok:
            error_detail = f"HTTP {response.status_code}: {response.reason}"
            try:
                error_json = response.json()
                if "error" in error_json:
                    error_info = error_json["error"]
                    if isinstance(error_info, dict):
                        error_msg = error_info.get("message", str(error_info))
                        error_type = error_info.get("type", "unknown")
                        error_detail = f"HTTP {response.status_code}: {error_msg} (type: {error_type})"
                    else:
                        error_detail = f"HTTP {response.status_code}: {error_info}"
            except Exception:
                # If we can't parse JSON, include raw response text
                error_detail = f"HTTP {response.status_code}: {response.reason}\n\nResponse: {response.text}"

            raise requests.exceptions.HTTPError(error_detail, response=response)

        data = response.json()
        if "data" not in data:
            raise ValueError(f"Unexpected API response: {data}")

        images = []
        for item in data["data"]:
            if "b64_json" not in item:
                raise ValueError(f"No b64_json in response item: {item}")
            image_data = base64.b64decode(item["b64_json"])
            images.append(image_data)

        return images

    def _call_edit_api(self, prompt: str, image_paths: list[str], model: str, size: str, n: int,
                      background: Optional[str], mask_path: Optional[str], timeout: int) -> list[bytes]:
        """Call the OpenAI image edit API."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        org_id = os.environ.get("OPENAI_ORG_ID")

        # Validate
        if model == "dall-e-2" and len(image_paths) > 1:
            raise ValueError("dall-e-2 only supports editing one image at a time")
        if model.startswith("gpt-image") and len(image_paths) > 16:
            raise ValueError("gpt-image models support up to 16 images")

        # Build multipart form data
        files = []
        for img_path in image_paths:
            files.append(('image[]' if model.startswith("gpt-image") else 'image',
                         (Path(img_path).name, open(img_path, 'rb'), 'image/png')))

        if mask_path:
            files.append(('mask', (Path(mask_path).name, open(mask_path, 'rb'), 'image/png')))

        data = {
            'prompt': prompt,
            'model': model,
            'n': str(n),
            'size': size
        }

        if model.startswith("gpt-image"):
            if background:
                data['background'] = background
        else:
            data['response_format'] = 'b64_json'

        headers = {"Authorization": f"Bearer {api_key}"}
        if org_id:
            headers["OpenAI-Organization"] = org_id

        try:
            response = requests.post(
                "https://api.openai.com/v1/images/edits",
                headers=headers,
                data=data,
                files=files,
                timeout=timeout
            )

            # Enhanced error handling with detailed API response
            if not response.ok:
                error_detail = f"HTTP {response.status_code}: {response.reason}"
                try:
                    error_json = response.json()
                    if "error" in error_json:
                        error_info = error_json["error"]
                        if isinstance(error_info, dict):
                            error_msg = error_info.get("message", str(error_info))
                            error_type = error_info.get("type", "unknown")
                            error_detail = f"HTTP {response.status_code}: {error_msg} (type: {error_type})"
                        else:
                            error_detail = f"HTTP {response.status_code}: {error_info}"
                except Exception:
                    # If we can't parse JSON, include raw response text
                    error_detail = f"HTTP {response.status_code}: {response.reason}\n\nResponse: {response.text}"

                raise requests.exceptions.HTTPError(error_detail, response=response)

        finally:
            for _, file_tuple in files:
                if hasattr(file_tuple[1], 'close'):
                    file_tuple[1].close()

        result_data = response.json()
        if "data" not in result_data:
            raise ValueError(f"Unexpected API response: {result_data}")

        images = []
        for item in result_data["data"]:
            if "b64_json" not in item:
                raise ValueError(f"No b64_json in response item: {item}")
            image_data = base64.b64decode(item["b64_json"])
            images.append(image_data)

        return images

    def _on_generation_success(self, images: list[bytes]) -> None:
        """Handle successful image generation (called in main thread)."""
        debug_print(f"_on_generation_success called with {len(images)} image(s)")
        self.current_images = images
        self.current_pil_images = []
        self.current_photo_images = []

        # Convert to PIL images
        for i, img_bytes in enumerate(images):
            debug_print(f"Converting image {i+1} to PIL (size: {len(img_bytes)} bytes)")
            pil_img = Image.open(BytesIO(img_bytes))
            debug_print(f"PIL image {i+1}: size={pil_img.size}, mode={pil_img.mode}")
            self.current_pil_images.append(pil_img)

        # Display first image
        self.current_image_index = 0
        debug_print("Calling display_current_image()")
        self.display_current_image()

        # Update UI
        self.is_generating = False
        self.generate_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.NORMAL)
        self.status_label.config(text=f"Generated {len(images)} image(s)", foreground="green")

        # Update navigation buttons
        if len(images) > 1:
            self.next_button.config(state=tk.NORMAL)
            self.image_counter_label.config(text=f"Image 1 of {len(images)}")
        else:
            self.image_counter_label.config(text="")

        debug_print("_on_generation_success completed")

    def _on_generation_error(self, error_msg: str) -> None:
        """Handle image generation error (called in main thread)."""
        self.is_generating = False
        self.generate_button.config(state=tk.NORMAL)
        self.status_label.config(text="Error", foreground="red")
        messagebox.showerror("Generation Error", f"Failed to generate image:\n\n{error_msg}")

    def display_current_image(self) -> None:
        """Display the current image on the canvas."""
        debug_print(f"display_current_image called, index={self.current_image_index}")

        if not self.current_pil_images:
            debug_print("No PIL images to display")
            return

        pil_img = self.current_pil_images[self.current_image_index]
        debug_print(f"PIL image: size={pil_img.size}, mode={pil_img.mode}")

        # Force GUI update to ensure canvas is rendered
        self.master.update_idletasks()

        # Resize image to fit canvas while maintaining aspect ratio
        canvas_width = self.image_canvas.winfo_width()
        canvas_height = self.image_canvas.winfo_height()
        debug_print(f"Canvas size: {canvas_width}x{canvas_height}")

        # Use default size if canvas hasn't been drawn yet
        if canvas_width <= 1:
            canvas_width = 600
        if canvas_height <= 1:
            canvas_height = 600

        img_width, img_height = pil_img.size
        scale = min(canvas_width / img_width, canvas_height / img_height)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        debug_print(f"Resizing to: {new_width}x{new_height} (scale={scale:.3f})")

        resized_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        debug_print(f"Image resized successfully")

        # Create PhotoImage - use workaround for Python 3.13 compatibility issue
        debug_print(f"Creating PhotoImage with master={self.master}")
        try:
            # Try the standard method first
            photo_img = ImageTk.PhotoImage(resized_img, master=self.master)
            debug_print("PhotoImage created successfully with ImageTk")
        except (TypeError, AttributeError) as e:
            debug_print(f"ImageTk.PhotoImage failed ({e}), trying PPM workaround")
            # Workaround for Python 3.13 + Pillow compatibility issue
            # Convert PIL image to PPM format which Tkinter supports natively
            try:
                # Convert to RGB if necessary (PPM doesn't support RGBA)
                if resized_img.mode == 'RGBA':
                    # Create white background
                    background = Image.new('RGB', resized_img.size, (255, 255, 255))
                    background.paste(resized_img, mask=resized_img.split()[3])  # Use alpha channel as mask
                    resized_img = background
                elif resized_img.mode != 'RGB':
                    resized_img = resized_img.convert('RGB')

                # Save to PPM format in memory
                ppm_data = BytesIO()
                resized_img.save(ppm_data, format='PPM')
                ppm_data.seek(0)

                # Create PhotoImage from PPM data
                photo_img = tk.PhotoImage(data=ppm_data.read(), master=self.master)
                debug_print("PhotoImage created successfully with PPM workaround")
            except Exception as e2:
                debug_print(f"ERROR with PPM workaround: {e2}")
                import traceback
                if DEBUG:
                    traceback.print_exc()
                raise

        # Store reference to prevent garbage collection
        if self.current_image_index >= len(self.current_photo_images):
            self.current_photo_images.append(photo_img)
        else:
            self.current_photo_images[self.current_image_index] = photo_img
        debug_print(f"PhotoImage stored, total stored: {len(self.current_photo_images)}")

        # Display on canvas
        self.image_canvas.delete("all")
        x = canvas_width // 2
        y = canvas_height // 2
        debug_print(f"Drawing on canvas at ({x}, {y})")
        self.image_canvas.create_image(x, y, image=photo_img, anchor=tk.CENTER)
        debug_print("Image displayed on canvas")

        # Update navigation
        total = len(self.current_pil_images)
        if total > 1:
            self.image_counter_label.config(text=f"Image {self.current_image_index + 1} of {total}")
            self.prev_button.config(state=tk.NORMAL if self.current_image_index > 0 else tk.DISABLED)
            self.next_button.config(state=tk.NORMAL if self.current_image_index < total - 1 else tk.DISABLED)

    def show_previous_image(self) -> None:
        """Show the previous image."""
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.display_current_image()

    def show_next_image(self) -> None:
        """Show the next image."""
        if self.current_image_index < len(self.current_pil_images) - 1:
            self.current_image_index += 1
            self.display_current_image()

    def save_images(self) -> None:
        """Save the generated images to files."""
        if not self.current_images:
            messagebox.showwarning("No Images", "No images to save.")
            return

        if len(self.current_images) == 1:
            # Save single image
            file_path = filedialog.asksaveasfilename(
                title="Save Image",
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
            )
            if file_path:
                with open(file_path, 'wb') as f:
                    f.write(self.current_images[0])
                messagebox.showinfo("Success", f"Image saved to:\n{file_path}")
        else:
            # Save multiple images
            directory = filedialog.askdirectory(title="Select Directory to Save Images")
            if directory:
                saved_files = []
                for i, img_data in enumerate(self.current_images):
                    file_path = Path(directory) / f"ai_image_{i+1}.png"
                    with open(file_path, 'wb') as f:
                        f.write(img_data)
                    saved_files.append(file_path.name)

                messagebox.showinfo("Success",
                                  f"Saved {len(saved_files)} images to:\n{directory}\n\n" +
                                  "\n".join(saved_files))

    def on_closing(self) -> None:
        """Handle window closing event."""
        self.master.destroy()


def main() -> None:
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="AI Image Generator GUI - Generate or edit images using OpenAI's image API"
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output'
    )
    args = parser.parse_args()

    # Set global DEBUG flag
    global DEBUG
    DEBUG = args.debug

    if DEBUG:
        print("[DEBUG] Debug mode enabled", file=sys.stderr)

    # Create and run GUI
    root = tk.Tk()
    app = ImageGeneratorApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()