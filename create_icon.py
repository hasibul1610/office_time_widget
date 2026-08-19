"""
Generates high-resolution icon assets (.ico and .png) for Office Time Widget.
"""

from pathlib import Path
from PIL import Image, ImageDraw


def generate_icons(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw circle clock face with gradient / deep blue
        pad = max(1, size // 16)
        draw.ellipse([pad, pad, size - pad, size - pad], fill=(15, 23, 42, 255), outline=(56, 189, 248, 255), width=max(1, size // 16))

        # Clock Hands
        cx, cy = size // 2, size // 2
        hand_w = max(1, size // 16)
        
        # Hour hand (12 o'clock)
        draw.line([(cx, cy), (cx, size // 4)], fill=(255, 255, 255, 255), width=hand_w)
        # Minute hand (3 o'clock)
        draw.line([(cx, cy), (size - size // 4, cy)], fill=(255, 255, 255, 255), width=hand_w)

        # Center dot
        dot_r = max(2, size // 16)
        draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=(56, 189, 248, 255))

        # Status badge (bottom right)
        b_r = max(2, size // 6)
        bx, by = size - pad - b_r, size - pad - b_r
        draw.ellipse([bx - b_r, by - b_r, bx + b_r, by + b_r], fill=(16, 185, 129, 255), outline=(15, 23, 42, 255), width=max(1, size // 24))

        images.append(img)

    # Save highest resolution PNG
    png_path = output_dir / "app_icon.png"
    images[-1].save(png_path, format="PNG")

    # Save multi-size ICO
    ico_path = output_dir / "app_icon.ico"
    images[-1].save(
        ico_path,
        format="ICO",
        sizes=[(s.width, s.height) for s in images],
    )
    print(f"Icons generated: {ico_path}, {png_path}")
    return ico_path, png_path


if __name__ == "__main__":
    generate_icons(Path(__file__).parent / "resources")
