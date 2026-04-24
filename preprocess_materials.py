"""
学习资料自动化预处理工具

需要安装的第三方库：
- Pillow
- opencv-python
- PyMuPDF
- tqdm
"""

from pathlib import Path

import cv2
import fitz
from PIL import Image, ImageOps
from tqdm import tqdm


DEFAULT_WEBP_QUALITY = 85
DEFAULT_SPLIT_MAX_PAGES = 10
DEFAULT_PDF_DPI = 200
DEFAULT_JOIN_CHUNK_SIZE = 10


def ensure_directory(path: Path) -> Path:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    return path


def convert_images_to_webp(input_dir: Path, output_dir: Path | None = None, quality: int = DEFAULT_WEBP_QUALITY) -> None:
    output_dir = ensure_directory(output_dir or input_dir / "webp_output")
    supported_exts = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}
    images = [p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in supported_exts]

    print(f"[INFO] Found {len(images)} image(s) in {input_dir}")
    if not images:
        print("[WARN] No supported image files found.")
        return

    success_count = 0
    for img_path in tqdm(images, desc="Converting to WebP", unit="image"):
        try:
            with Image.open(img_path) as im:
                im = im.convert("RGB")
                target_path = output_dir / (img_path.stem + ".webp")
                im.save(target_path, format="WEBP", quality=quality, method=6, optimize=True)
                success_count += 1
        except Exception as exc:
            print(f"[ERROR] Skipping {img_path.name}: {exc}")

    print(f"[INFO] Completed: {success_count}/{len(images)} image(s) converted to {output_dir}")


def enhance_images_for_ocr(input_dir: Path, output_dir: Path | None = None) -> None:
    output_dir = ensure_directory(output_dir or input_dir / "ocr_enhanced")
    supported_exts = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
    images = [p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in supported_exts]

    print(f"[INFO] Found {len(images)} image(s) for OCR enhancement in {input_dir}")
    if not images:
        print("[WARN] No supported image files found.")
        return

    success_count = 0
    for img_path in tqdm(images, desc="Enhancing images", unit="image"):
        try:
            src = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
            if src is None:
                raise ValueError("Unable to read image")

            gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
            gray = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
            enhanced = cv2.adaptiveThreshold(
                gray,
                maxValue=255,
                adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                thresholdType=cv2.THRESH_BINARY,
                blockSize=15,
                C=10,
            )
            enhanced = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
            target_path = output_dir / img_path.name
            cv2.imwrite(str(target_path), enhanced)
            success_count += 1
        except Exception as exc:
            print(f"[ERROR] Skipping {img_path.name}: {exc}")

    print(f"[INFO] Completed: {success_count}/{len(images)} image(s) enhanced into {output_dir}")


def split_pdf(input_path: Path, max_pages: int = DEFAULT_SPLIT_MAX_PAGES, output_dir: Path | None = None) -> None:
    output_dir = ensure_directory(output_dir or input_path.parent / "pdf_split")
    try:
        doc = fitz.open(str(input_path))
    except Exception as exc:
        print(f"[ERROR] Cannot open PDF {input_path.name}: {exc}")
        return

    try:
        page_count = doc.page_count
        print(f"[INFO] PDF {input_path.name} has {page_count} page(s)")
        if page_count <= max_pages:
            print(f"[WARN] PDF has {page_count} pages, which is not more than max_pages={max_pages}. No split needed.")
            return

        success_count = 0
        split_ranges = list(range(0, page_count, max_pages))
        for part_index, start in enumerate(tqdm(split_ranges, desc="Splitting PDF", unit="part"), start=1):
            end = min(start + max_pages, page_count)
            part = fitz.open()
            try:
                for page_num in tqdm(
                    range(start, end),
                    desc=f"Building part {part_index:02d}",
                    unit="page",
                    leave=False,
                ):
                    part.insert_pdf(doc, from_page=page_num, to_page=page_num)
                output_file = output_dir / f"{input_path.stem}_part{part_index:02d}.pdf"
                part.save(str(output_file))
                success_count += 1
            except Exception as exc:
                print(f"[ERROR] Failed to save part {part_index:02d} ({start + 1}-{end}): {exc}")
            finally:
                part.close()

        print(f"[INFO] Completed: {success_count}/{len(split_ranges)} split file(s) saved to {output_dir}")
    finally:
        doc.close()


def pdf_to_images(
    input_path: Path,
    output_dir: Path | None = None,
    dpi: int = DEFAULT_PDF_DPI,
    join_long_image: bool = False,
    join_chunk_size: int = DEFAULT_JOIN_CHUNK_SIZE,
) -> None:
    output_dir = ensure_directory(output_dir or input_path.parent / "pdf_images")
    try:
        doc = fitz.open(str(input_path))
    except Exception as exc:
        print(f"[ERROR] Cannot open PDF {input_path.name}: {exc}")
        return

    try:
        print(f"[INFO] Converting PDF {input_path.name} ({doc.page_count} page(s)) to images at {dpi} DPI")
        image_paths: list[Path] = []
        success_count = 0
        mat = fitz.Matrix(dpi / 72, dpi / 72)

        for page_index in tqdm(range(doc.page_count), desc="Rendering PDF pages", unit="page"):
            try:
                page = doc.load_page(page_index)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                image_name = f"{input_path.stem}_page{page_index + 1:03d}.png"
                image_path = output_dir / image_name
                pix.save(str(image_path))
                image_paths.append(image_path)
                success_count += 1
            except Exception as exc:
                print(f"[ERROR] Failed to render page {page_index + 1}: {exc}")

        print(f"[INFO] Completed: {success_count}/{doc.page_count} page image(s) saved to {output_dir}")

        if join_long_image and image_paths:
            join_images_vertically(
                image_paths=image_paths,
                output_dir=output_dir,
                base_name=input_path.stem,
                chunk_size=join_chunk_size,
            )
    finally:
        doc.close()


def join_images_vertically(
    image_paths: list[Path],
    output_dir: Path,
    base_name: str,
    chunk_size: int = DEFAULT_JOIN_CHUNK_SIZE,
) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")

    total_chunks = (len(image_paths) + chunk_size - 1) // chunk_size
    print(f"[INFO] Joining long images in batches of up to {chunk_size} page(s)")

    success_count = 0
    for chunk_index, start in enumerate(tqdm(range(0, len(image_paths), chunk_size), desc="Joining long images", unit="chunk"), start=1):
        chunk_paths = image_paths[start : start + chunk_size]
        output_path = output_dir / f"{base_name}_long_part{chunk_index:02d}.png"

        try:
            image_sizes: list[tuple[int, int]] = []
            max_width = 0
            total_height = 0

            for image_path in chunk_paths:
                with Image.open(image_path) as img:
                    width, height = img.size
                    image_sizes.append((width, height))
                    max_width = max(max_width, width)
                    total_height += height

            long_img = Image.new("RGB", (max_width, total_height), color="white")
            y_offset = 0

            for image_path, (width, height) in zip(chunk_paths, image_sizes):
                with Image.open(image_path) as img:
                    current = img.convert("RGB")
                    if width != max_width:
                        current = ImageOps.pad(current, (max_width, height), color="white")
                    long_img.paste(current, (0, y_offset))
                    y_offset += height
                    current.close()

            long_img.save(output_path, format="PNG")
            long_img.close()
            success_count += 1
        except Exception as exc:
            print(f"[ERROR] Failed to join pages {start + 1}-{start + len(chunk_paths)}: {exc}")

    print(f"[INFO] Completed: {success_count}/{total_chunks} long image(s) saved to {output_dir}")


def prompt_non_empty_input(prompt_text: str) -> str:
    while True:
        value = input(prompt_text).strip().strip('"').strip("'")
        if value:
            return value
        print("[WARN] Input cannot be empty. Please try again.")


def prompt_existing_directory(prompt_text: str) -> Path:
    while True:
        input_dir = Path(prompt_non_empty_input(prompt_text)).expanduser()
        if input_dir.is_dir():
            return input_dir
        print(f"[ERROR] Directory does not exist: {input_dir}")


def prompt_existing_pdf(prompt_text: str) -> Path:
    while True:
        input_path = Path(prompt_non_empty_input(prompt_text)).expanduser()
        if input_path.is_file() and input_path.suffix.lower() == ".pdf":
            return input_path
        print(f"[ERROR] Please provide an existing PDF file path: {input_path}")


def prompt_optional_output_dir(default_path: Path) -> Path:
    raw_value = input(f"输出目录（直接回车使用默认：{default_path}）: ").strip().strip('"').strip("'")
    return Path(raw_value).expanduser() if raw_value else default_path


def prompt_yes_no(prompt_text: str, default: bool = False) -> bool:
    default_hint = "Y/n" if default else "y/N"
    while True:
        value = input(f"{prompt_text} ({default_hint}): ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("[WARN] Please enter y or n.")


def prompt_int(prompt_text: str, default: int, minimum: int = 1, maximum: int | None = None) -> int:
    while True:
        raw_value = input(f"{prompt_text}（直接回车使用默认：{default}）: ").strip()
        if not raw_value:
            return default
        try:
            value = int(raw_value)
            if value < minimum or (maximum is not None and value > maximum):
                raise ValueError
            return value
        except ValueError:
            if maximum is None:
                print(f"[WARN] Please enter an integer greater than or equal to {minimum}.")
            else:
                print(f"[WARN] Please enter an integer between {minimum} and {maximum}.")


def wait_for_enter() -> None:
    input("\n按回车键返回主菜单...")


def print_menu() -> None:
    print("\n================ 学习资料预处理工具 ================")
    print("1. 批量转换图片为 WebP")
    print("2. 批量增强图片 (OCR 预处理)")
    print("3. 拆分长 PDF")
    print("4. PDF 转图片 (并可选拼接长图)")
    print("0. 退出")
    print("===================================================")


def run_convert_images_to_webp() -> None:
    input_dir = prompt_existing_directory("请输入图片文件夹路径: ")
    output_dir = prompt_optional_output_dir(input_dir / "webp_output")
    quality = prompt_int("WebP 质量", default=DEFAULT_WEBP_QUALITY, minimum=1, maximum=100)
    convert_images_to_webp(input_dir, output_dir=output_dir, quality=quality)


def run_enhance_images_for_ocr() -> None:
    input_dir = prompt_existing_directory("请输入图片文件夹路径: ")
    output_dir = prompt_optional_output_dir(input_dir / "ocr_enhanced")
    enhance_images_for_ocr(input_dir, output_dir=output_dir)


def run_split_pdf() -> None:
    input_path = prompt_existing_pdf("请输入 PDF 文件路径: ")
    output_dir = prompt_optional_output_dir(input_path.parent / "pdf_split")
    max_pages = prompt_int("每个拆分文件的最大页数", default=DEFAULT_SPLIT_MAX_PAGES, minimum=1)
    split_pdf(input_path, max_pages=max_pages, output_dir=output_dir)


def run_pdf_to_images() -> None:
    input_path = prompt_existing_pdf("请输入 PDF 文件路径: ")
    output_dir = prompt_optional_output_dir(input_path.parent / "pdf_images")
    dpi = prompt_int("导出图片 DPI", default=DEFAULT_PDF_DPI, minimum=72)
    join_long_image = prompt_yes_no("是否将导出的页面拼接成长图", default=False)
    join_chunk_size = DEFAULT_JOIN_CHUNK_SIZE

    if join_long_image:
        join_chunk_size = prompt_int("每张长图最多拼接页数", default=DEFAULT_JOIN_CHUNK_SIZE, minimum=1)

    pdf_to_images(
        input_path,
        output_dir=output_dir,
        dpi=dpi,
        join_long_image=join_long_image,
        join_chunk_size=join_chunk_size,
    )


def main() -> None:
    actions = {
        "1": run_convert_images_to_webp,
        "2": run_enhance_images_for_ocr,
        "3": run_split_pdf,
        "4": run_pdf_to_images,
    }

    while True:
        print_menu()
        choice = input("请输入功能编号: ").strip()

        if choice == "0":
            print("程序已退出。")
            break

        action = actions.get(choice)
        if action is None:
            print("[WARN] 无效的菜单编号，请重新输入。")
            continue

        try:
            action()
        except Exception as exc:
            print(f"[ERROR] Operation failed: {exc}")

        wait_for_enter()


if __name__ == "__main__":
    main()
