"""
Screenshot all chart HTML files to PNG using headless Chrome.

Usage:
    uv run python tools/screenshot_charts.py JPM_2025_10_K
"""

import argparse
import glob
import os
import subprocess
import sys

from helpers import get_project_dir

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def _screenshot_avatar_background():
    """Screenshot the generic avatar background template to PNG.

    This is a static RoboSystems-branded frame (no ticker) used as the
    avatar's permanent background in HeyGen. Only needs to be generated once.
    """
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(tools_dir)
    template_path = os.path.join(root_dir, "template", "charts", "html", "AVATAR_BG_TEMPLATE.html")
    output_path = os.path.join(root_dir, "template", "charts", "png", "avatar_bg.png")

    if not os.path.exists(template_path):
        return None

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ok, _ = _screenshot(template_path, output_path, width=1280, height=720)
    return output_path if ok else None


def _screenshot(html_path, png_path, width=1920, height=1080):
    """Screenshot a single HTML file to PNG at the given dimensions."""
    result = subprocess.run(
        [
            CHROME,
            "--headless",
            "--disable-gpu",
            f"--window-size={width},{height}",
            f"--screenshot={png_path}",
            f"file://{html_path}",
        ],
        capture_output=True,
        timeout=30,
    )
    return os.path.exists(png_path), result


def screenshot_charts(project_name):
    project_dir = get_project_dir(project_name)
    html_dir = os.path.join(project_dir, "charts", "html")
    png_dir = os.path.join(project_dir, "charts", "png")
    os.makedirs(png_dir, exist_ok=True)

    # Screenshot all chart HTMLs except templates and examples
    # INTRO_SLIDE and OUTRO_SLIDE ARE included — they're part of the video timeline
    html_files = [
        f for f in glob.glob(os.path.join(html_dir, "*.html"))
        if not os.path.basename(f).startswith(("CHART_TEMPLATE", "EXAMPLE_", "AVATAR_BG_TEMPLATE"))
    ]
    if not html_files:
        print(f"No chart HTML files found in {html_dir}")
        return

    print(f"Screenshotting {len(html_files)} charts...\n")

    for html_path in sorted(html_files):
        name = os.path.splitext(os.path.basename(html_path))[0]
        png_path = os.path.join(png_dir, f"{name}.png")

        print(f"  {name}.html -> {name}.png ...", end=" ")
        # Thumbnails are 1280x720, everything else is 1920x1080
        if "thumbnail" in name.lower():
            ok, result = _screenshot(html_path, png_path, width=1280, height=720)
            # Crop to exact dimensions — Chrome headless sometimes captures extra height
            if ok:
                subprocess.run(
                    ["sips", "--cropToHeightWidth", "720", "1280", png_path],
                    capture_output=True, timeout=10,
                )
        else:
            ok, result = _screenshot(html_path, png_path)

        if ok:
            size_kb = os.path.getsize(png_path) / 1024
            print(f"OK ({size_kb:.0f}K)")
        else:
            print("FAILED")
            if result.stderr:
                print(f"    {result.stderr.decode()[:200]}")

    print(f"\nDone. PNGs saved to {png_dir}")


def main():
    parser = argparse.ArgumentParser(description="Screenshot chart HTMLs to PNGs")
    parser.add_argument("project", help="Project name (e.g., JPM_2025_10_K)")
    args = parser.parse_args()
    screenshot_charts(args.project)


if __name__ == "__main__":
    main()
