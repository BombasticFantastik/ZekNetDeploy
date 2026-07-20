import hashlib
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
gui_path = os.path.join(BASE_DIR, "gui_test.jpg")
img_path = os.path.join(BASE_DIR, "test.jpg")

with open(gui_path, "rb") as f:
    print(hashlib.md5(f.read()).hexdigest())

with open(img_path, "rb") as f:
    print(hashlib.md5(f.read()).hexdigest())

from PIL import Image
import numpy as np

# img1 = np.array(Image.open(gui_path))
# img2 = np.array(Image.open(img_path))

# print(img1.shape)
# print(img2.shape)

# print(np.mean(abs(img1.astype(int)-img2.astype(int))))

img1 = np.array(Image.open(gui_path).convert("RGB"))
img2 = np.array(Image.open(img_path).convert("RGB"))

print(img1.shape)
print(img2.shape)

diff = np.mean(abs(img1.astype(int) - img2.astype(int)))

print(diff)