import urllib.request
import re

url = "https://ps-myodoo-test-knowlage-piotr.odoo.com/web/login"
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req).read().decode("utf-8")  # nosec B310
    matches = re.findall(r'name="db" value="([^"]+)"', html)
    if matches:
        print("ZNALEZIONO DB w HTML:", matches)
    else:
        print("Nie znaleziono inputu name='db'.")

    session_info = re.findall(r'"db":\s*"([^"]+)"', html)
    if session_info:
        print("ZNALEZIONO DB w session_info:", session_info)
except Exception as e:
    print("Blad", e)
