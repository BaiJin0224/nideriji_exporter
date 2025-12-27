# main.py
from __future__ import annotations

from typing import Optional
import sys

from fetch_data import login_and_sync_index, export_text_by_diary_ids, export_images_by_image_ids
from recovery_image_ext import recover_images_from_bin
from export_as_html import export_as_html


# =========================
# 可选：在代码里写死账号密码（优先于环境变量）
# 如果不想写死，保持为 None 即可
# =========================
EMAIL: Optional[str] = None
PASSWORD: Optional[str] = None


def main() -> int:
    try:
        session, token, userid, diary_ids, image_ids = login_and_sync_index(
            email=EMAIL,
            password=PASSWORD,
        )

        print("[index] userid:", userid)
        print("[index] diary_ids:", len(diary_ids))
        print("[index] image_ids:", len(image_ids))

        # 1) 导出日记文本
        export_text_by_diary_ids(
            session=session,
            token=token,
            userid=userid,
            diary_ids=diary_ids,
            out_path="dairies.txt",
            batch_size=50,
            sleep_s=0.15,
        )

        # 2) 下载图片（原始）
        export_images_by_image_ids(
            session=session,
            token=token,
            userid=userid,
            image_ids=image_ids,
            out_dir="images",
            sleep_s=0.10,
        )

        session.close()

        # 3) 恢复 .bin 图片后缀到 recovery_images
        processed, recovered, non_images = recover_images_from_bin(
            src_dir="images",
            dst_dir="recovery_images",
        )
        print(f"[recover] processed={processed} recovered={recovered} non_images={non_images}")

        # 4) 导出 HTML（合并文本 + 图片）
        export_as_html(
            dairies_txt="dairies.txt",
            images_dir="recovery_images",
            out_html="dairies.html",
        )

        print("All done. Output: dairies.html")
        return 0

    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
