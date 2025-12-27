# recovery_image_ext.py
import os
import shutil
from typing import Optional, Tuple


def _sniff_image_ext(header: bytes) -> Optional[str]:
    if len(header) < 12:
        return None

    if header.startswith(b"\xFF\xD8\xFF"):
        return ".jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return ".gif"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return ".webp"
    if header.startswith(b"BM"):
        return ".bmp"
    if header.startswith(b"II*\x00") or header.startswith(b"MM\x00*"):
        return ".tiff"
    if header.startswith(b"\x00\x00\x01\x00"):
        return ".ico"

    return None


def _looks_like_text(header: bytes) -> bool:
    sample = header.lstrip()[:64].lower()
    return (
        sample.startswith(b"{")
        or sample.startswith(b"[")
        or sample.startswith(b"<!doctype html")
        or sample.startswith(b"<html")
        or sample.startswith(b"<?xml")
        or sample.startswith(b"error")
        or sample.startswith(b"forbidden")
        or sample.startswith(b"unauthorized")
    )


def recover_images_from_bin(
    src_dir: str = "images",
    dst_dir: str = "recovery_images",
    non_image_subdir: str = "_non_image",
    read_bytes: int = 64,
) -> Tuple[int, int, int]:
    """
    识别 src_dir 下的 .bin 文件真实图片格式，复制到 dst_dir 并改后缀。
    返回 (processed, recovered_images, non_images)
    """
    if not os.path.isdir(src_dir):
        raise FileNotFoundError(f"src_dir not found: {src_dir}")

    os.makedirs(dst_dir, exist_ok=True)
    non_img_dir = os.path.join(dst_dir, non_image_subdir)
    os.makedirs(non_img_dir, exist_ok=True)

    processed = 0
    recovered = 0
    non_images = 0

    for name in os.listdir(src_dir):
        if not name.lower().endswith(".bin"):
            continue

        processed += 1
        src_path = os.path.join(src_dir, name)

        try:
            with open(src_path, "rb") as f:
                header = f.read(read_bytes)
        except OSError:
            non_images += 1
            shutil.copy2(src_path, os.path.join(non_img_dir, name))
            continue

        ext = _sniff_image_ext(header)

        if ext is None or _looks_like_text(header):
            non_images += 1
            shutil.copy2(src_path, os.path.join(non_img_dir, name))
            continue

        base = os.path.splitext(name)[0]
        dst_path = os.path.join(dst_dir, base + ext)

        if os.path.exists(dst_path):
            i = 2
            while True:
                dst_path2 = os.path.join(dst_dir, f"{base}_{i}{ext}")
                if not os.path.exists(dst_path2):
                    dst_path = dst_path2
                    break
                i += 1

        shutil.copy2(src_path, dst_path)
        recovered += 1

    return processed, recovered, non_images
