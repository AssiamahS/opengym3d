"""Install the audited Windows Blender/MPFB toolchain inside work/, hash checked."""
import hashlib
import subprocess
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = [
    ('blender-4.5.11-windows-x64.zip',
     'https://download.blender.org/release/Blender4.5/blender-4.5.11-windows-x64.zip',
     'e11d3a8e4d4249be5a7db4a9325c1f670037d4233467c3b0bda181001efe44d3', '',
     'blender-4.5.11-windows-x64/blender.exe'),
    ('mpfb-2.0.16.zip',
     'https://extensions.blender.org/download/sha256:b5cdc8b08147e0c6463e4faa01147491b13a0b062f73415363f029debd11c934/add-on-mpfb-v2.0.16.zip?repository=%2Fapi%2Fv1%2Fextensions%2F&blender_version_min=4.2.0',
     'b5cdc8b08147e0c6463e4faa01147491b13a0b062f73415363f029debd11c934', 'addons/mpfb',
     'addons/mpfb/blender_manifest.toml'),
]


def main():
    folder = ROOT / 'work/toolchain'
    folder.mkdir(parents=True, exist_ok=True)
    for name, url, expected, dest, marker in PACKAGES:
        path = folder / name
        if not path.exists():
            print('Downloading', name, flush=True)
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, path.open('wb') as stream:
                import shutil
                shutil.copyfileobj(response, stream)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Wrong SHA256 for {path}; remove the corrupt download and retry')
        if not (folder / marker).exists():
            with zipfile.ZipFile(path) as archive:
                archive.extractall(folder / dest)
    subprocess.run(['npm.cmd', 'ci', '--ignore-scripts'], cwd=ROOT, check=True)
    subprocess.run(['npx.cmd', 'playwright', 'install', 'chromium'], cwd=ROOT, check=True)
    print('Pinned toolchain ready. FFmpeg and ffprobe must be on PATH.')


if __name__ == '__main__':
    main()
