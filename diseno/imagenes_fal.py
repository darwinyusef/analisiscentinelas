import os, json, sys, urllib.request, concurrent.futures as cf
KEY = os.environ["FAL_KEY"]
STYLE = "editorial photography, golden hour light, rich natural colors, shallow depth of field, Colombian Andes (Antioquia), no text, no logos, no people faces"
PROMPTS = {
 "bienvenida": "Vertical landscape of misty green Andean highland potato fields at sunrise, terraced rows, soft fog in the valley, warm light",
 "papa": "Close-up of freshly harvested Colombian papa criolla and papa capira potatoes in a wooden crate, soil still on them, farm background",
 "tomate": "Ripe red chonto tomatoes on the vine in a greenhouse, dew drops, glossy, deep green leaves",
 "cebolla": "Bundles of green junca spring onions freshly harvested on a rustic wooden market table, morning light",
 "mercado": "Colorful Colombian wholesale produce market stall with crates of vegetables and fruits, warm morning light, hands of a vendor only",
 "campesino": "Farmer's weathered hands holding a smartphone and a handful of fresh soil in a green crop field, close-up, out-of-focus fields behind",
}
def gen(item):
    k, p = item
    req = urllib.request.Request("https://fal.run/fal-ai/flux/dev",
        data=json.dumps({"prompt": p + ", " + STYLE, "image_size": {"width": 864, "height": 1536}, "num_images": 1, "num_inference_steps": 28}).encode(),
        headers={"Authorization": "Key " + KEY, "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=300))
    url = r["images"][0]["url"]
    urllib.request.urlretrieve(url, f"diseno/img/{k}.jpg")
    return k, "ok"
with cf.ThreadPoolExecutor(6) as ex:
    for f in [ex.submit(gen, i) for i in PROMPTS.items()]:
        try: print(f.result())
        except Exception as e: print("ERR", repr(e)[:300])
