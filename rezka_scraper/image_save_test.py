import requests

image_url = "http://static.hdrezka.sx/i/2014/4/26/x193c8f9da1f0oc95p70m.jpg"
news_id = 0
try:
    image_extension = image_url.split(".")[-1]
    img_data = requests.get(image_url).content
    with open(f"posters/{news_id}.{image_extension}", "wb") as handler:
        handler.write(img_data)
        print(f"Poster saved to posters/{news_id}.{image_extension}")
except:
    print("Poster not found")
