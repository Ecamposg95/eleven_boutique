"""Image pipeline: everything uploaded is decoded and re-encoded; nothing is stored as received."""

import io
import re
import unicodedata
import uuid
from dataclasses import dataclass

from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 60_000_000
MAX_SIDE = 2400

# Pillow format -> (extension, content type). Restricting the decoders also rules out SVG,
# GIF, TIFF and every other format Pillow could otherwise parse.
FORMATS = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
}
_SAVE_OPTIONS = {
    "JPEG": {"quality": 88, "optimize": True, "progressive": True},
    "PNG": {"optimize": True},
    "WEBP": {"quality": 88, "method": 4},
}


class ImageRejected(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ProcessedImage:
    key: str
    data: bytes
    content_type: str
    width: int
    height: int


def sanitize_filename(raw: str | None) -> str:
    """Display-only name: no directories, control characters or leading dots."""
    name = unicodedata.normalize("NFC", raw or "")
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[^\w .()+-]", "_", name, flags=re.UNICODE)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[-200:].lstrip(" .") or "imagen"


def _to_srgb(image: Image.Image) -> Image.Image:
    """Dropping the profile without converting would shift colors in wide-gamut phone photos."""
    profile = image.info.get("icc_profile")
    if not profile or image.mode not in ("RGB", "RGBA"):
        return image
    try:
        source = ImageCms.ImageCmsProfile(io.BytesIO(profile))
        return ImageCms.profileToProfile(image, source, ImageCms.createProfile("sRGB"))
    except (ImageCms.PyCMSError, OSError, ValueError):
        return image


_INVALID = ("invalid_image", "Solo se aceptan imágenes JPEG, PNG o WebP válidas")
_DECODE_ERRORS = (UnidentifiedImageError, OSError, ValueError, SyntaxError, EOFError, TypeError)


def _decode(data: bytes) -> tuple[Image.Image, str]:
    too_big = ImageRejected(413, "image_too_large", "La imagen supera los 60 megapíxeles")
    try:
        image = Image.open(io.BytesIO(data), formats=list(FORMATS))
        # Dimensions come from the header: checked before any pixel is decoded.
        if image.width * image.height > MAX_PIXELS:
            raise too_big
        # Multi-picture JPEGs, common from some cameras, open as MPO: they are still JPEG files.
        image_format = "JPEG" if image.format == "MPO" else image.format
        image.load()
    except Image.DecompressionBombError as error:
        raise too_big from error
    except _DECODE_ERRORS as error:
        raise ImageRejected(422, *_INVALID) from error
    return image, image_format


def process_image(data: bytes) -> ProcessedImage:
    if len(data) > MAX_FILE_BYTES:
        raise ImageRejected(413, "file_too_large", "El archivo supera los 20 MB")
    image, image_format = _decode(data)

    try:
        # Orientation first: the color conversion returns an image without EXIF.
        image = ImageOps.exif_transpose(image)
        image = _to_srgb(image)
        if image_format == "JPEG" or image.mode not in ("RGB", "RGBA", "L", "LA"):
            has_alpha = image_format != "JPEG" and (
                image.mode in ("PA", "RGBa") or "transparency" in image.info
            )
            image = image.convert("RGBA" if has_alpha else "RGB")
        image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)

        # A fresh image carries over pixels only: no EXIF, XMP, ICC or text chunks.
        clean = Image.new(image.mode, image.size)
        clean.paste(image)
        output = io.BytesIO()
        clean.save(output, format=image_format, **_SAVE_OPTIONS[image_format])
    except _DECODE_ERRORS as error:  # Malformed metadata can fail after the pixels decoded.
        raise ImageRejected(422, *_INVALID) from error

    extension, content_type = FORMATS[image_format]
    return ProcessedImage(
        key=f"{uuid.uuid4().hex}.{extension}",
        data=output.getvalue(),
        content_type=content_type,
        width=clean.width,
        height=clean.height,
    )
