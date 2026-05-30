import re
import datetime
import constants
import settings

emojis = {}
channel_id_to_active_beatmap_id = {}

def convert_kwargs(kwargs):
    #"mode" as an alias for "m"
    if "mode" in kwargs:
        kwargs["m"] = kwargs["mode"]
    #"user" as an alias for "u"
    if "user" in kwargs:
        kwargs["u"] = kwargs["user"]
    #convert mode aliases to 0-3 (as used by the api)
    if "m" in kwargs and kwargs["m"].lower() in constants.mode_aliases:
        kwargs["m"] = constants.mode_aliases[kwargs["m"].lower()]
    return kwargs

def calculate_accuracy(score_data, mode):
    #Hits and accuracy
    if mode == "osu":
        raw_score = (int(score_data["count300"]) * 300) + (int(score_data["count100"]) * 100) + (int(score_data["count50"]) * 50)
        total_hits = int(score_data["count300"]) + int(score_data["count100"]) + int(score_data["count50"]) + int(score_data["countmiss"])
        accuracy = (raw_score * 100) / (total_hits * 300)
    if mode == "taiko":
        raw_score = (int(score_data["count300"]) * 300) + (int(score_data["count100"]) * 150)
        total_hits = int(score_data["count300"]) + int(score_data["count100"]) + int(score_data["countmiss"])
        accuracy = (raw_score * 100) / (total_hits * 300)
    if mode == "catch":
        raw_score = int(score_data["count300"]) + int(score_data["count100"]) + int(score_data["count50"])
        total_hits = raw_score + int(score_data["countmiss"]) + int(score_data["countkatu"])
        accuracy = (raw_score * 100) / total_hits
    if mode == "mania":
        raw_score = (int(score_data["countgeki"]) * 300) + (int(score_data["count300"]) * 300) + (int(score_data["countkatu"]) * 200) + (int(score_data["count100"]) * 100) + (int(score_data["count50"]) * 50)
        total_hits = int(score_data["countgeki"]) + int(score_data["count300"]) + int(score_data["countkatu"]) + int(score_data["count100"]) + int(score_data["count50"]) + int(score_data["countmiss"])
        accuracy = (raw_score * 100) / (total_hits * 300)
    return accuracy

def calculate_accuracy_v2(score_data):
    statistics = score_data["statistics"]
    #for some reason the osu api just doesn't include the property if it's 0 ???
    perfect_count = int(statistics["perfect"]) if "perfect" in statistics else 0
    great_count = int(statistics["great"]) if "great" in statistics else 0
    good_count = int(statistics["good"]) if "good" in statistics else 0
    ok_count = int(statistics["ok"]) if "ok" in statistics else 0
    meh_count = int(statistics["meh"]) if "meh" in statistics else 0
    miss_count = int(statistics["miss"]) if "miss" in statistics else 0
    large_tick_hit_count = int(statistics["large_tick_hit"]) if "large_tick_hit" in statistics else 0
    small_tick_hit_count = int(statistics["small_tick_hit"]) if "small_tick_hit" in statistics else 0
    small_tick_miss_count = int(statistics["small_tick_miss"]) if "small_tick_miss" in statistics else 0

    #Hits and accuracy
    if score_data["ruleset_id"] == 0:
        raw_score = (great_count * 300) + (ok_count * 100) + (meh_count * 50)
        total_hits = great_count + ok_count + meh_count + miss_count
        accuracy = (raw_score * 100) / (total_hits * 300)
    if score_data["ruleset_id"] == 1:
        raw_score = (great_count * 300) + (ok_count * 150)
        total_hits = great_count + ok_count + miss_count
        accuracy = (raw_score * 100) / (total_hits * 300)
    if score_data["ruleset_id"] == 2:
        raw_score = great_count + large_tick_hit_count + small_tick_hit_count
        total_hits = raw_score + miss_count + small_tick_miss_count
        accuracy = (raw_score * 100) / total_hits
    if score_data["ruleset_id"] == 3:
        raw_score = (perfect_count * 300) + (great_count * 300) + (good_count * 200) + (ok_count * 100) + (meh_count * 50)
        total_hits = perfect_count + great_count + good_count + ok_count + meh_count + miss_count
        accuracy = (raw_score * 100) / (total_hits * 300)
    return accuracy

def get_emojified_hits(score_data, mode):
    if mode == "osu":
        hits = emojify("[hit300] x{:,} / [hit100] x{:,} / [hit50] x{:,} / [hit0] x{:,}".format(int(score_data["count300"]), int(score_data["count100"]), int(score_data["count50"]), int(score_data["countmiss"])))
    if mode == "taiko":
        hits = emojify("[thit300] x{:,} / [thit100] x{:,} / [thit0] x{:,}".format(int(score_data["count300"]), int(score_data["count100"]), int(score_data["countmiss"])))
    if mode == "catch":
        hits = emojify("[chit300] x{:,} / [chit100] x{:,} / [chit50] x{:,} / [chit0] x{:,} / [chit0d] x{:,}".format(int(score_data["count300"]), int(score_data["count100"]), int(score_data["count50"]), int(score_data["countmiss"]), int(score_data["countkatu"])))
    if mode == "mania":
        hits = emojify("[mhit300r] x{:,} / [mhit300] x{:,} / [mhit200] x{:,} / [mhit100] x{:,} / [mhit50] x{:,} / [mhit0] x{:,}".format(int(score_data["countgeki"]), int(score_data["count300"]), int(score_data["countkatu"]), int(score_data["count100"]), int(score_data["count50"]), int(score_data["countmiss"])))
    return hits

def get_emojified_hits_v2(score_data):
    statistics = get_v2_score_statistics(score_data)
    if score_data["ruleset_id"] == 0:
        hits = emojify("[hit300] x{:,} / [hit100] x{:,} / [hit50] x{:,} / [hit0] x{:,}".format(int(statistics["great"]), int(statistics["ok"]), int(statistics["meh"]), int(statistics["miss"])))
    if score_data["ruleset_id"] == 1:
        hits = emojify("[thit300] x{:,} / [thit100] x{:,} / [thit0] x{:,}".format(int(statistics["great"]), int(statistics["ok"]), int(statistics["miss"])))
    if score_data["ruleset_id"] == 2:
        hits = emojify("[chit300] x{:,} / [chit100] x{:,} / [chit50] x{:,} / [chit0] x{:,} / [chit0d] x{:,}".format(int(statistics["great"]), int(statistics["large_tick_hit"]), int(statistics["small_tick_hit"]), int(statistics["miss"]), int(statistics["small_tick_miss"])))
    if score_data["ruleset_id"] == 3:
        hits = emojify("[mhit300r] x{:,} / [mhit300] x{:,} / [mhit200] x{:,} / [mhit100] x{:,} / [mhit50] x{:,} / [mhit0] x{:,}".format(int(statistics["perfect"]), int(statistics["great"]), int(statistics["good"]), int(statistics["ok"]), int(statistics["meh"]), int(statistics["miss"])))
    return hits

def convert_v2_mods_to_array(mods, ignore_cl=False):
    return [x["acronym"] for x in mods if x["acronym"] != "CL" or not ignore_cl]

def get_v2_score_statistics(score_data):
    statistics = score_data["statistics"]
    if "perfect" not in statistics:
        statistics["perfect"] = 0
    if "great" not in statistics:
        statistics["great"] = 0
    if "good" not in statistics:
        statistics["good"] = 0
    if "ok" not in statistics:
        statistics["ok"] = 0
    if "meh" not in statistics:
        statistics["meh"] = 0
    if "miss" not in statistics:
        statistics["miss"] = 0
    if "large_tick_hit" not in statistics:
        statistics["large_tick_hit"] = 0
    if "small_tick_hit" not in statistics:
        statistics["small_tick_hit"] = 0
    if "small_tick_miss" not in statistics:
        statistics["small_tick_miss"] = 0
    return statistics

def is_lazer_score(score_data):
    return score_data["legacy_total_score"] == 0 or score_data["legacy_score_id"] is None

def get_max_combo(beatmap):
    #Determine max combo
    if beatmap["mode"] in ["0", "2", "osu", "fruits"]:
        if "maxcombo" in beatmap:
            max_combo = beatmap["maxcombo"]
        elif "max_combo" in beatmap:
            max_combo = beatmap["max_combo"]
        else:
            max_combo = "??"
    elif beatmap["mode"] == "1":
        max_combo = beatmap["count_normal"]
    elif beatmap["mode"] == "taiko":
        max_combo = beatmap["count_circles"]
    else:
        max_combo = "??"
    return max_combo

def get_delta_string(datestring="", timestamp=None):
    if not timestamp:
        timestamp = datetime.datetime.strptime(datestring, settings.timestamp_format).replace(tzinfo=datetime.timezone.utc)
    delta = datetime.datetime.now(datetime.timezone.utc) - timestamp
    if delta.total_seconds() >= 86400:
        days = int(delta.total_seconds() // 86400)
        delta_string = "{} day{}".format(days, "s" if days > 1 else "")
    elif delta.total_seconds() >= 3600:
        hours = int(delta.total_seconds() // 3600)
        delta_string = "{} hour{}".format(hours, "s" if hours > 1 else "")
    elif delta.total_seconds() >= 60:
        minutes = int(delta.total_seconds() // 60)
        delta_string = "{} minute{}".format(minutes, "s" if minutes > 1 else "")
    else:
        seconds = int(delta.total_seconds())
        delta_string = "{} second{}".format(seconds, "s" if seconds > 1 else "")
    return delta_string

def get_discord_timestamp(datestring="", timestamp=None):
    if not timestamp:
        timestamp = datetime.datetime.strptime(datestring, settings.timestamp_format).replace(tzinfo=datetime.timezone.utc)
    return "<t:{:0.0f}:R>".format(timestamp.timestamp())

def get_mods_from_int(flag):
    rawmods = "{0:032b}".format(int(flag))
    ans = []
    for i in range(32):
        if rawmods[i*-1-1] == "1":
            ans.append(constants.mods[i])
    if "NC" in ans:
        try:
            ans.remove("DT")
        except:
            pass
    if "PF" in ans:
        try:
            ans.remove("SD")
        except:
            pass
    return ans

def get_mods_from_string(the_string, ncpf=False):
    ans = []
    for i in range(0, len(the_string), 2):
        if the_string[i:i+2].upper() in constants.mods_v2.keys():
            ans.append(the_string[i:i+2].upper())
    if ncpf and "NC" in ans and "DT" not in ans:
        ans.append("DT")
    if ncpf and "PF" in ans and "SD" not in ans:
        ans.append("SD")
    return ans

def mods_to_int(the_list):
    ans = 0
    for item in the_list:
        if item in constants.mods:
            ans += 2**constants.mods.index(item)
    return ans

def get_map_mode(beatmap_file_name):
    lines = open(beatmap_file_name, encoding="utf8").read().split("\n")
    for line in lines:
        if line.startswith("Mode:"):
            return line.replace("Mode:", "").strip()

#Convert mods as an int to an int that works with get_beatmaps because it invalidates the difficulty values if any of the mods given were not difficulty related
def ignore_irrelevant_mods(flag):
    rawmods = "{0:032b}".format(int(flag))
    ans = 0
    if rawmods[-constants.mods.index("EZ")-1] == "1":
        ans += 2
    if rawmods[-constants.mods.index("HR")-1] == "1":
        ans += 16
    if rawmods[-constants.mods.index("DT")-1] == "1" or rawmods[-constants.mods.index("NC")-1] == "1":
        ans += 64
    if rawmods[-constants.mods.index("HT")-1] == "1":
        ans += 256
    return ans

def remove_duplicates(list):
    ans = []
    for item in list:
        if item not in ans:
            ans.append(item)
    return ans

def emojify(the_message):
    emojified_message = the_message
    
    possible_emojis = re.findall(r"\[[^\[\]]*\]", the_message)
    possible_emojis = remove_duplicates(possible_emojis)
    
    #for each of the strings that were in []
    for i in range(len(possible_emojis)):
        raw = possible_emojis[i][1:-1]
        #replace it with the emoji if it exists
        try:
            emojified_message = emojified_message.replace("[{}]".format(raw), emojis[raw.lower()])
        except KeyError:
            emojified_message = emojified_message.replace("[{}]".format(raw), raw)
    
    return emojified_message