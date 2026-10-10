from paddleocr import PaddleOCR

# NEW API (PaddleOCR 3.x)
ocr = PaddleOCR(use_textline_orientation=True)

img_path = "test.png"   # or jpg

result = ocr.predict(img_path)

for res in result:
    for line in res["rec_texts"]:
        print(line)