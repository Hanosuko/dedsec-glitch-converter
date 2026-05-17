#!/bin/zsh
set -e

cd "$(dirname "$0")"

if [ ! -x ".venv39/bin/python" ]; then
  /usr/bin/python3 -m venv .venv39
fi

if ! .venv39/bin/python -c "import cv2, numpy, PIL" >/dev/null 2>&1; then
  .venv39/bin/python -m pip install opencv-python numpy pillow
fi

.venv39/bin/python dedsec_converter.py --gui
