from datetime import datetime
import aichi
import ichinomiya

aichi.post_nagoya()
aichi.post_okazaki()
aichi.post_toyohashi()
aichi.post_toyota()
ichinomiya.post_ichinomiya()
aichi.post_aichi()
aichi.post_zentai()

print(f"checked.. {datetime.today()}")
with open("checked.txt", mode="a", encoding="utf-8") as f:
    f.write(f"checked.. {datetime.today()}")
