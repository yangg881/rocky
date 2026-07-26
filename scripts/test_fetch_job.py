import urllib.request

url = "https://m.gxrc.com/jobDetail/906ef9eb-b551-48a8-bbcd-c25f558979e3"
req = urllib.request.Request(
    url,
    headers={
        "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36"
    },
)

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print("Final URL:", resp.geturl())
        page = resp.read().decode("utf-8", errors="replace")
        print("Contains NoPosition in URL:", "NoPosition" in resp.geturl())
        print("Contains NoPosition in page:", "NoPosition" in page)
        print("Contains 已过期 in page:", "已过期" in page)
except Exception as e:
    print("Error:", e)
