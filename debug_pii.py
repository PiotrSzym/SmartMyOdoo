import json
from smartmyodoo.mcp.pii_middleware import PiiMiddleware

m = PiiMiddleware()
text = '{"records": [{"id": 1, "name": "Jan Kowalski", "vat": "1234563218"}], "count": 1}'
print("ORIGINAL:", text)
results = m.analyzer.analyze(text=text, language="pl")
print("RESULTS:")
for r in results:
    print(r.entity_type, r.start, r.end, r.score)

anon = m.anonymize(text)
print("ANONYMIZED:", anon)
