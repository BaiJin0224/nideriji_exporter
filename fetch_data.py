# fetch_data.py
import os
import re
import time
import requests
from typing import List, Dict, Any, Tuple, Optional


LOGIN_URL = "https://nideriji.cn/api/login/"
SYNC_URL = "https://nideriji.cn/api/v2/sync/"
IMAGE_HOST = "https://f.nideriji.cn"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0.0.0 Safari/537.36"
)


def login_and_sync_index(
    email: Optional[str] = None,
    password: Optional[str] = None,
    sleep_s: float = 0.0,
) -> Tuple[requests.Session, str, int, List[int], List[int]]:
    """
    返回 (session, token, userid, diary_ids_sorted, image_ids_sorted)

    - email/password 若不传则读环境变量 NIDERIJI_EMAIL / NIDERIJI_PASSWORD
    """
    email = (email or os.getenv("NIDERIJI_EMAIL", "")).strip()
    password = (password or os.getenv("NIDERIJI_PASSWORD", "")).strip()
    if not email or not password:
        raise RuntimeError("Missing email/password. Set env NIDERIJI_EMAIL & NIDERIJI_PASSWORD or pass params.")

    s = requests.Session()
    s.headers.update({"accept-language": "zh-CN,zh;q=0.9,en;q=0.8"})

    # login
    login_headers = {
        "accept": "*/*",
        "origin": "https://nideriji.cn",
        "referer": "https://nideriji.cn/w/login",
        "user-agent": UA,
    }
    login_files = {"email": (None, email), "password": (None, password)}
    r = s.post(LOGIN_URL, headers=login_headers, files=login_files, timeout=30)
    r.raise_for_status()
    data = r.json()

    token = data.get("token")
    userid = data.get("userid") or (data.get("user_config") or {}).get("userid")
    if not token or not userid:
        s.close()
        raise RuntimeError(f"Login ok but missing token/userid: {data}")
    userid = int(userid)

    if sleep_s:
        time.sleep(sleep_s)

    # sync
    sync_headers = {
        "accept": "*/*",
        "origin": "https://nideriji.cn",
        "referer": "https://nideriji.cn/w/",
        "user-agent": UA,
        "auth": f"token {token}",
    }
    sync_files = {
        "user_config_ts": (None, "0"),
        "diaries_ts": (None, "0"),
        "readmark_ts": (None, "0"),
        "images_ts": (None, "0"),
    }
    r = s.post(SYNC_URL, headers=sync_headers, files=sync_files, timeout=30)
    r.raise_for_status()
    sync_data = r.json()

    diary_ids: List[int] = sorted({int(d["id"]) for d in (sync_data.get("diaries") or []) if "id" in d})
    image_ids: List[int] = sorted({int(img["image_id"]) for img in (sync_data.get("images") or []) if "image_id" in img})

    return s, token, userid, diary_ids, image_ids


def _all_by_ids(session: requests.Session, token: str, userid: int, diary_ids: List[int]) -> List[Dict[str, Any]]:
    url = f"https://nideriji.cn/api/diary/all_by_ids/{userid}/"
    headers = {
        "accept": "*/*",
        "origin": "https://nideriji.cn",
        "referer": "https://nideriji.cn/w/",
        "user-agent": UA,
        "auth": f"token {token}",
    }
    files = [("diary_ids", (None, str(did))) for did in diary_ids]
    r = session.post(url, headers=headers, files=files, timeout=60)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("error") not in (0, None):
        raise RuntimeError(f"all_by_ids error: {data}")
    return data.get("diaries", []) or []


def _supports_multi_ids(session: requests.Session, token: str, userid: int, test_ids: List[int]) -> bool:
    diaries = _all_by_ids(session, token, userid, test_ids)
    return len(diaries) >= 2


def _write_one_diary(f, d: Dict[str, Any]) -> None:
    did = d.get("id")
    createddate = d.get("createddate", "")
    ts = d.get("ts", "")
    title = (d.get("title") or "").strip()
    content = d.get("content") or ""

    f.write(f"=== DiaryID: {did} | Date: {createddate} | TS: {ts} ===\n")
    if title:
        f.write(f"Title: {title}\n")
    f.write(content)
    if not content.endswith("\n"):
        f.write("\n")
    f.write("\n")


def _chunked(lst: List[int], size: int) -> List[List[int]]:
    return [lst[i:i + size] for i in range(0, len(lst), size)]


def export_text_by_diary_ids(
    session: requests.Session,
    token: str,
    userid: int,
    diary_ids: List[int],
    out_path: str = "dairies.txt",
    batch_size: int = 50,
    sleep_s: float = 0.15,
) -> None:
    """
    抓取每个日记正文 content，写入 out_path（带日记ID+日期+TS）
    - 自动探测 all_by_ids 是否支持多ID
    - 不支持则逐条请求
    """
    diary_ids = sorted(diary_ids)
    if not diary_ids:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("No diary_ids provided.\n")
        return

    probe = diary_ids[:3] if len(diary_ids) >= 3 else diary_ids
    multi_ok = False
    if len(probe) >= 2:
        try:
            multi_ok = _supports_multi_ids(session, token, userid, probe)
        except Exception:
            multi_ok = False

    with open(out_path, "w", encoding="utf-8") as f:
        if multi_ok:
            for batch in _chunked(diary_ids, batch_size):
                diaries = _all_by_ids(session, token, userid, batch)
                diaries.sort(key=lambda x: int(x.get("id", 0)))
                for d in diaries:
                    _write_one_diary(f, d)
                time.sleep(sleep_s)
        else:
            for idx, did in enumerate(diary_ids, start=1):
                diaries = _all_by_ids(session, token, userid, [did])
                if diaries:
                    _write_one_diary(f, diaries[0])
                else:
                    f.write(f"=== DiaryID: {did} | (no data) ===\n\n")

                if idx % 20 == 0:
                    print(f"[export_text] fetched {idx}/{len(diary_ids)}")
                time.sleep(sleep_s)


def export_images_by_image_ids(
    session: requests.Session,
    token: str,
    userid: int,
    image_ids: List[int],
    out_dir: str = "images",
    sleep_s: float = 0.1,
) -> None:
    """
    下载图片：
      https://f.nideriji.cn/api/image/{userid}/{image_id}/
    """
    image_ids = sorted(set(image_ids))
    if not image_ids:
        print("[export_images] No image_ids provided.")
        return

    os.makedirs(out_dir, exist_ok=True)

    headers = {
        "accept": "*/*",
        "origin": "https://nideriji.cn",
        "referer": "https://nideriji.cn/w/",
        "user-agent": UA,
        "auth": f"token {token}",
    }

    for idx, image_id in enumerate(image_ids, start=1):
        url = f"{IMAGE_HOST}/api/image/{userid}/{image_id}/"
        r = session.get(url, headers=headers, stream=True, timeout=60)

        if r.status_code in (401, 403):
            raise RuntimeError(f"Unauthorized for image_id={image_id}, status={r.status_code}")

        r.raise_for_status()

        ctype = (r.headers.get("Content-Type") or "").lower()
        if "jpeg" in ctype or "jpg" in ctype:
            ext = ".jpg"
        elif "png" in ctype:
            ext = ".png"
        elif "webp" in ctype:
            ext = ".webp"
        elif "gif" in ctype:
            ext = ".gif"
        else:
            cd = r.headers.get("Content-Disposition") or ""
            m = re.search(r'filename="([^"]+)"', cd)
            if m:
                _, ext = os.path.splitext(m.group(1))
                if not ext:
                    ext = ".bin"
            else:
                ext = ".bin"

        out_path = os.path.join(out_dir, f"image_{image_id}{ext}")
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 128):
                if chunk:
                    f.write(chunk)

        if idx % 20 == 0 or idx == len(image_ids):
            print(f"[export_images] downloaded {idx}/{len(image_ids)}")

        time.sleep(sleep_s)
