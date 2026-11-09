"""Image-only observation transport; never fetch client-supplied URLs or paths."""

import base64
import binascii
import io
from dataclasses import dataclass

import numpy as np
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 4_000_000
MAX_IMAGE_PIXELS = 1_048_576
MAX_BASE64_LENGTH = ((MAX_IMAGE_BYTES + 2) // 3) * 4 + 32


@dataclass(frozen=True)
class VisualState:
    text: str
    image: Image.Image


def validate_image(image):
    if image.width < 1 or image.height < 1 or image.width * image.height > MAX_IMAGE_PIXELS:
        raise ValueError(f"Image must contain 1–{MAX_IMAGE_PIXELS} pixels")


def encode_image(frame: np.ndarray) -> str:
    if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[-1] != 3:
        raise ValueError("Observation must be an H×W×3 uint8 RGB array")
    image = Image.fromarray(frame)
    validate_image(image)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    if buffer.tell() > MAX_IMAGE_BYTES:
        raise ValueError("Encoded image exceeds size limit")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def decode_image(encoded: str) -> Image.Image:
    if len(encoded) > MAX_BASE64_LENGTH:
        raise ValueError("Encoded image exceeds size limit")
    if encoded.startswith("data:"):
        header, separator, encoded = encoded.partition(",")
        if not separator or header not in {"data:image/png;base64", "data:image/jpeg;base64"}:
            raise ValueError("Only base64 PNG/JPEG images are accepted")
    try:
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > MAX_IMAGE_BYTES:
            raise ValueError("Image exceeds size limit")
        with Image.open(io.BytesIO(raw)) as image:
            if image.format not in {"PNG", "JPEG"}:
                raise ValueError("Only PNG/JPEG images are accepted")
            validate_image(image)
            return image.convert("RGB")
    except (binascii.Error, UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError("Invalid PNG/JPEG image") from error
