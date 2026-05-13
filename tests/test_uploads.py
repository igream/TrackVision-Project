import requests
import os

url_process = "http://127.0.0.1:8000/api/process"

session = requests.Session()
data = {"username": "testuser99", "password": "password123"}
r_reg = session.post("http://127.0.0.1:8000/login", data=data)

def upload_file(path):
    with open(path, "rb") as f:
        files = {"plate_image": f}
        data = {"mode": "ocr"}
        r = session.post(url_process, files=files, data=data)
        print(f"Process {os.path.basename(path)}:", r.status_code)
        if r.status_code != 200:
            print(r.text)

for i in range(0, 10):
    p = f"C:\\Users\\Fer\\Desktop\\OCR Placas\\datasets\\car_plate_detection\\images\\Cars{i}.png"
    if os.path.exists(p):
        upload_file(p)
