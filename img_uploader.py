"""
圖片上傳模組
上傳到 catbox.moe（免費、不需帳號、永久保存）
備用：imgbb（需要設定 IMGBB_API_KEY）
"""
import os
import io
import requests
from PIL import Image


def upload_image(img_bytes: bytes, filename="travel.jpg") -> str:
    """上傳圖片 bytes，回傳公開 URL（依序嘗試多個服務）"""

    # 方案 1：imgbb（需設定 IMGBB_API_KEY，最穩定）
    api_key = os.getenv("IMGBB_API_KEY")
    if api_key:
        try:
            import base64
            b64 = base64.b64encode(img_bytes).decode()
            resp = requests.post(
                f"https://api.imgbb.com/1/upload?key={api_key}",
                data={"image": b64},
                timeout=30,
            )
            data = resp.json()
            if data.get("success"):
                url = data["data"]["url"]
                print(f"[上傳] imgbb 成功: {url}")
                return url
        except Exception as e:
            print(f"[上傳] imgbb 失敗: {e}")

    # 方案 2：litterbox.catbox.moe（免費、不需帳號、1小時有效，夠 IG 下載用）
    try:
        resp = requests.post(
            "https://litterbox.catbox.moe/resources/internals/api.php",
            data={"reqtype": "fileupload", "time": "1h"},
            files={"fileToUpload": (filename, img_bytes, "image/jpeg")},
            timeout=30,
        )
        url = resp.text.strip()
        if url.startswith("https://"):
            print(f"[上傳] litterbox 成功: {url}")
            return url
    except Exception as e:
        print(f"[上傳] litterbox 失敗: {e}")

    print("[上傳] 所有上傳方式都失敗")
    return None


def upload_pil_image(img: Image.Image, filename="travel.jpg") -> str:
    """上傳 PIL Image，回傳公開 URL"""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=92)
    return upload_image(buf.getvalue(), filename)
