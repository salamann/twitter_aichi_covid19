from datetime import datetime
# from post_number_cloud import post_cities
# import aichi
# import ichinomiya
# import nagoya
# import toyohashi
# import toyota
# import okazaki
# import vaccination

# vaccination.post()
# aichi.post_nagoya()
# aichi.post_okazaki()
# aichi.post_toyohashi()
# aichi.post_toyota()


# nagoya.post_nagoya()
# okazaki.post_okazaki()
# toyohashi.post_toyohashi()
# toyota.post_toyota()
# ichinomiya.post_ichinomiya()
# aichi.post_aichi()
# aichi.post_zentai()

# post_cities()

print(f"checked.. {datetime.today()}")
with open("checked.txt", mode="a", encoding="utf-8") as f:
    f.write(f"checked.. {datetime.today()}")
