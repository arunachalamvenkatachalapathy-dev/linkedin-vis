import json

mem = json.load(open("content_memory.json", encoding="utf-8"))
print(f"Total posts in memory: {len(mem)}")
print()
for i, e in enumerate(mem[-20:]):
    print(f"[{i}]")
    print(f"  date        : {e.get('date', '?')}")
    print(f"  template    : {e.get('template', '?')}")
    print(f"  performed   : {e.get('performed_well', '?')}")
    print(f"  engagement  : {e.get('engagement_score', 'NOT SET')}")
    print(f"  post_id     : {str(e.get('post_id', None))[:50]}")
    print(f"  hook        : {str(e.get('hook', ''))[:80]}")
    print(f"  title       : {e.get('title', '')[:80]}")
    print()
