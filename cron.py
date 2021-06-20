from datetime import datetime
import aichi
import ichinomiya
import nagoya
import toyohashi
import toyota
import okazaki
import vaccination

vaccination.post()
# aichi.post_nagoya()
nagoya.post_nagoya()
# aichi.post_okazaki()
okazaki.post_okazaki()
# aichi.post_toyohashi()
toyohashi.post_toyohashi()
# aichi.post_toyota()
toyota.post_toyota()
ichinomiya.post_ichinomiya()
aichi.post_aichi()
aichi.post_zentai()

print(f"checked.. {datetime.today()}")
with open("checked.txt", mode="a", encoding="utf-8") as f:
    f.write(f"checked.. {datetime.today()}")
