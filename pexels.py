"""
Pexels API 工具模組
取得高畫質旅遊圖片和影片
"""
import os
import io
import random
import requests
from PIL import Image
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

PEXELS_KEY = os.getenv("PEXELS_API_KEY")
HEADERS = {"Authorization": PEXELS_KEY}


def search_photos(query: str, count: int = 5, orientation: str = "portrait") -> list:
    """搜尋 Pexels 圖片，回傳圖片 URL 清單（多抓隨機取，讓每次結果不同）"""
    fetch = max(count * 3, 15)  # 多抓幾張，隨機取以增加多樣性
    resp = requests.get(
        "https://api.pexels.com/v1/search",
        headers=HEADERS,
        params={"query": query, "per_page": min(fetch, 80), "orientation": orientation},
        timeout=15,
    )
    photos = resp.json().get("photos", [])
    urls = [p["src"]["large2x"] for p in photos]
    if len(urls) > count:
        # 偏向前面（品質較好），但加入隨機性
        pool = urls[:min(len(urls), count * 2)]
        random.shuffle(pool)
        return pool[:count]
    return urls


def get_curated_photos(count: int = 5) -> list:
    """取得 Pexels 精選熱門圖片（編輯精選，視覺效果佳）"""
    resp = requests.get(
        "https://api.pexels.com/v1/curated",
        headers=HEADERS,
        params={"per_page": min(count * 3, 80)},
        timeout=15,
    )
    photos = resp.json().get("photos", [])
    urls = [p["src"]["large2x"] for p in photos]
    random.shuffle(urls)
    return urls[:count]


def search_videos(query: str, count: int = 5, orientation: str = "portrait") -> list:
    """搜尋 Pexels 影片，回傳影片 URL 清單（選最高畫質）"""
    resp = requests.get(
        "https://api.pexels.com/videos/search",
        headers=HEADERS,
        params={"query": query, "per_page": count, "orientation": orientation},
        timeout=15,
    )
    results = []
    for v in resp.json().get("videos", []):
        # 選擇最高畫質的檔案
        files = sorted(v.get("video_files", []), key=lambda x: x.get("width", 0), reverse=True)
        if files:
            results.append(files[0]["link"])
    return results


def download_image(url: str, size=(1080, 1080)) -> Image.Image:
    """下載並裁切圖片為指定尺寸"""
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=20)
    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
    w, h = img.size
    target_w, target_h = size
    # 等比裁切置中
    ratio = max(target_w / w, target_h / h)
    new_w, new_h = int(w * ratio), int(h * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def download_video(url: str, save_path: str) -> str:
    """下載影片到本地"""
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=60, stream=True)
    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return save_path


def get_travel_photo(destination: str, theme: str = "", size=(1080, 1080)) -> Image.Image:
    """取得目的地旅遊圖片（自動組合搜尋詞）"""
    query = f"{destination} {theme} travel".strip()
    urls = search_photos(query, count=3)
    if not urls:
        urls = search_photos(destination, count=3)
    if not urls:
        # 備用純色
        return Image.new("RGB", size, (40, 15, 70))
    return download_image(urls[0], size)


def get_travel_video_path(destination: str, theme: str = "", save_dir: str = ".") -> str:
    """下載目的地影片到本地，回傳路徑"""
    query = f"{destination} {theme} travel".strip()
    urls = search_videos(query, count=3)
    if not urls:
        return None
    save_path = os.path.join(save_dir, f"pexels_{destination}_{theme}.mp4".replace(" ", "_"))
    return download_video(urls[0], save_path)
