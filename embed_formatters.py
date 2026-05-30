import datetime, copy
import base64
import discord
import perf_calc_wrapper, osu_api_wrapper
from osu_map_parser import OsuBeatmapParser
from osu_replay_analyzer import OsuReplayAnalyzer
from osu_replay_parser import OsuReplayDetails
import settings
import constants
import utils

def format_user_embed(user_data, mode):
    total_hits = int(user_data["count300"] or 0) + int(user_data["count100"] or 0) + int(user_data["count50"] or 0)
    embed = discord.Embed(
        title="{} {} stats for **{}**".format(
            utils.emojify("[mode{}]".format(mode)),
            mode,
            user_data["username"]),
        description="**Performance**: {}pp (#{}) :flag_{}: #{}".format(
            user_data["pp_raw"] or 0,
            user_data["pp_rank"] or 0,
            user_data["country"].lower(),
            user_data["pp_country_rank"] or 0),
        url="https://osu.ppy.sh/u/{}".format(user_data["user_id"]))
    embed.add_field(
        name="**Detailed Stats**",
        value="**Ranked Score**: {:,}\n**Hit Accuracy**: {:0.3f}%\n**Play Count**: {:,}\n**Play Time**: {}\n**Total Score**: {:,}\n**Current Level**: {}\n**Hits**: {}\n**Ranks**: {}".format(
            int(user_data["ranked_score"] or 0),
            float(user_data["accuracy"] or 0),
            int(user_data["playcount"] or 0),
            str(datetime.timedelta(0, int(user_data["total_seconds_played"] or 0))),
            int(user_data["total_score"] or 0),
            user_data["level"] or 0,
            utils.emojify("[hit300] x{:,} ({:0.1f}%) / [hit100] x{:,} ({:0.1f}%) / [hit50] x{:,} ({:0.1f}%)".format(
                int(user_data["count300"] or 0),
                0 if total_hits == 0 else 100 * int(user_data["count300"] or 0) / total_hits,
                int(user_data["count100"] or 0),
                0 if total_hits == 0 else 100 * int(user_data["count100"] or 0) / total_hits,
                int(user_data["count50"] or 0),
                0 if total_hits == 0 else 100 * int(user_data["count50"] or 0) / total_hits)),
            utils.emojify("[rankingXH] x{:,} / [rankingX] x{:,} / [rankingSH] x{:,} / [rankingS] x{:,} / [rankingA] x{:,}".format(
                int(user_data["count_rank_ssh"] or 0),
                int(user_data["count_rank_ss"] or 0),
                int(user_data["count_rank_sh"] or 0),
                int(user_data["count_rank_s"] or 0),
                int(user_data["count_rank_a"] or 0)))),
        inline=False)
    embed.set_thumbnail(url="https://s.ppy.sh/a/{}".format(user_data["user_id"]))
    return embed

def format_user_embed_v2(user_data, mode):
    embed = discord.Embed(
        title="{} {} stats for **{}**".format(
            utils.emojify("[mode{}]".format(mode)),
            mode,
            user_data["username"]),
        description="**Performance**: {}pp (#{}) :flag_{}: #{}".format(
            user_data["statistics"]["pp"],
            user_data["statistics"]["global_rank"],
            user_data["country_code"].lower(),
            user_data["statistics"]["country_rank"]),
        url="https://osu.ppy.sh/u/{}".format(user_data["id"]))
    embed.add_field(
        name="**Detailed Stats**",
        value="**Ranked Score**: {:,}\n**Hit Accuracy**: {:0.3f}%\n**Play Count**: {:,}\n**Play Time**: {}\n**Total Score**: {:,}\n**Current Level**: {}\n**Total Hits**: {:,}\n**Ranks**: {}".format(
            user_data["statistics"]["ranked_score"],
            user_data["statistics"]["hit_accuracy"],
            user_data["statistics"]["play_count"],
            str(datetime.timedelta(0, user_data["statistics"]["play_time"])),
            user_data["statistics"]["total_score"],
            user_data["statistics"]["level"]["current"] + (user_data["statistics"]["level"]["progress"] / 100),
            user_data["statistics"]["total_hits"],
            utils.emojify("[rankingXH] x{:,} / [rankingX] x{:,} / [rankingSH] x{:,} / [rankingS] x{:,} / [rankingA] x{:,}".format(
                user_data["statistics"]["grade_counts"]["ssh"],
                user_data["statistics"]["grade_counts"]["ss"],
                user_data["statistics"]["grade_counts"]["sh"],
                user_data["statistics"]["grade_counts"]["s"],
                user_data["statistics"]["grade_counts"]["a"]))),
        inline=False)
    embed.set_thumbnail(url=user_data["avatar_url"])
    return embed

def format_profile_embed(profile_data):
    join_date = datetime.datetime.fromisoformat(profile_data["join_date"])
    try:
        last_visit_date = datetime.datetime.fromisoformat(profile_data["last_visit"])
    except TypeError:
        last_visit_date = None
    
    supporter_status = "None"
    if profile_data["has_supported"]:
        supporter_status = "Expired"
        if profile_data["is_supporter"]:
            supporter_status = ":heart:"
    if "support_level" in profile_data:
        supporter_status = ""
        for i in range(profile_data["support_level"]):
            supporter_status += ":heart:"
    
    badges = []
    if "badges" in profile_data:
        for badge in profile_data["badges"]:
            badges.append(badge["description"])
    
    if "monthly_playcounts" in profile_data:
        highest_play_count = 0
        highest_play_month = ""
        current_play_count = 0
        for entry in profile_data["monthly_playcounts"]:
            if entry["count"] > highest_play_count:
                highest_play_count = entry["count"]
                highest_play_month = entry["start_date"][:-3]
            current_play_count = entry["count"]
    
    if "replays_watched_counts" in profile_data:
        highest_replay_count = 0
        highest_replay_month = ""
        current_replay_count = 0
        for entry in profile_data["replays_watched_counts"]:
            if entry["count"] > highest_replay_count:
                highest_replay_count = entry["count"]
                highest_replay_month = entry["start_date"][:-3]
            current_replay_count = entry["count"]
    
    embed = discord.Embed(
        title="**{}**'s Osu! Profile".format(profile_data["username"]),
        description="{}**Country**: :flag_{}:\n**Join Date**: {} ({} ago)\n**Last Visit**: {}{}\n{}**Supporter Status**: {}\n**Main Game Mode**: {}\n**Play Style**: {}\n{}{}**Follower Count**: {}\n**Mapping Follower Count**: {}\n**Ranked/Loved/Pending/Graveyarded Maps**: {}/{}/{}/{}\n**Kudosu Recieved**: {}\n**Achievements**: {}\n**Badges{}**: {}".format(
            "**Title**: {}\n".format(profile_data["title"]) if "title" in profile_data and profile_data["title"] else "",
            profile_data["country_code"].lower(),
            join_date.strftime(settings.timestamp_format),
            utils.get_delta_string(timestamp=join_date),
            last_visit_date.strftime(settings.timestamp_format) if last_visit_date else "Unknown",
            " ({} ago)".format(utils.get_delta_string(timestamp=last_visit_date)) if last_visit_date else "",
            "**Previous Usernames**: {}\n".format(", ".join(profile_data["previous_usernames"])) if profile_data["previous_usernames"] else "",
            supporter_status,
            profile_data["playmode"],
            ", ".join(profile_data["playstyle"]) if profile_data["playstyle"] else "Unknown",
            "**Plays**: This month: {} | Highest: {} ({})\n".format(current_play_count, highest_play_count, highest_play_month) if "monthly_playcounts" in profile_data else "",
            "**Replays Watched**: This month: {} | Highest: {} ({})\n".format(current_replay_count, highest_replay_count, highest_replay_month) if "replays_watched_counts" in profile_data else "",
            profile_data["follower_count"] if "follower_count" in profile_data else "Unknown",
            profile_data["mapping_follower_count"] if "mapping_follower_count" in profile_data else "Unknown",
            profile_data["ranked_and_approved_beatmapset_count"],
            profile_data["loved_beatmapset_count"],
            profile_data["unranked_beatmapset_count"],
            profile_data["graveyard_beatmapset_count"],
            profile_data["kudosu"]["total"],
            len(profile_data["user_achievements"]),
            " ({})".format(len(badges)) if badges else "",
            ", ".join(badges) if badges else "None"),
        url="https://osu.ppy.sh/u/{}".format(profile_data["id"]))
    embed.set_thumbnail(url=profile_data["avatar_url"])
    embed.set_image(url=profile_data["cover_url"])
    return embed

def format_single_score_embed(score_data, mode, include_acc_data=False, use_calc=None):
    #Grab some other info
    user = osu_api_wrapper.get_user(**{"u":score_data["user_id"], "m":constants.mode_aliases[mode]})[0]
    beatmap = osu_api_wrapper.get_beatmaps(**{"b":score_data["beatmap_id"], "m":constants.mode_aliases[mode], "a":"1", "mods":utils.ignore_irrelevant_mods(int(score_data["enabled_mods"]))})[0]
    
    #Hits and accuracy
    accuracy = utils.calculate_accuracy(score_data, mode)
    hits = utils.get_emojified_hits(score_data, mode)
    
    #Determine max combo
    max_combo = utils.get_max_combo(beatmap)
    
    #How long ago?
    delta_string = utils.get_delta_string(score_data["date"])

    #Determine mods
    enabled_mods = utils.get_mods_from_int(score_data["enabled_mods"])
    
    beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap["beatmap_id"], beatmap["last_update"])
    
    #Calculate pp info using PerformanceCalculator
    objects_progress = 0
    ctb_map_completion = 0
    if score_data["rank"] == "F":
        if mode in ["osu", "taiko"]:
            objects_progress += int(score_data["count300"]) + int(score_data["count100"]) + int(score_data["count50"]) + int(score_data["countmiss"])
        elif mode == "catch":
            ctb_map_completion = (int(score_data["count300"]) + int(score_data["count100"]) + int(score_data["countmiss"])) / int(beatmap["maxcombo"])
        elif mode == "mania":
            objects_progress += int(score_data["countgeki"]) + int(score_data["count300"]) + int(score_data["countkatu"]) + int(score_data["count100"]) + int(score_data["count50"]) + int(score_data["countmiss"])
    result_score = perf_calc_wrapper.calculate_pp(
        beatmap_file_name,
        mode=mode,
        mods=enabled_mods,
        combo=score_data["maxcombo"],
        n300=int(score_data["count300"]),
        n200=int(score_data["countkatu"]),
        n100=score_data["count100"],
        n50=score_data["count50"],
        n0=score_data["countmiss"],
        score=score_data["score"],
        partial=score_data["rank"] == "F",
        objects_progress=objects_progress,
        ctb_map_completion=ctb_map_completion,
        use_calc=use_calc)
    result_fc = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=mode, mods=enabled_mods, use_calc=use_calc)
    
    #verify pp
    if (score_data["pp"]):
        if use_calc in constants.legacy_calcs:
            pp_error = abs(float(result_score["pp"]) - float(score_data["pp"]))
        else:
            pp_error = abs(float(result_score["performance_attributes"]["pp"]) - float(score_data["pp"]))
    
    #For the NM emoji
    if not enabled_mods:
        enabled_mods.append("None")
    
    if include_acc_data and mode == "osu":
        replaysearch = osu_api_wrapper.get_replay(**{"s": score_data["score_id"]})
        if "error" not in replaysearch:
            replay_lzma = replaysearch["content"]
            replay_details = OsuReplayDetails()
            replay_details.replay_data_raw = base64.b64decode(replay_lzma)
            replay_analyzer = OsuReplayAnalyzer(map_file_name=beatmap_file_name, replay_details=replay_details, force_hr="HR" in enabled_mods, force_ez="EZ" in enabled_mods)
            extra_acc_data = "Unstable Rate: {:0.2f}".format(replay_analyzer.unstable_rate)
        else:
            extra_acc_data = "Unstable Rate: Replay not available"
    else:
        extra_acc_data = ""
    
    if use_calc in constants.legacy_calcs:
        star_rating = float(result_fc["star rating"]) if "star rating" in result_fc else float(beatmap["difficultyrating"])
    else:
        star_rating = float(result_fc["difficulty_attributes"]["star_rating"])
    
    #Format embed!
    embed = discord.Embed(
        title="{} {} - {} [{}] ({:0.2f}☆) {}".format(
            utils.emojify("[mode{}]".format(mode)),
            beatmap["artist"],
            beatmap["title"],
            beatmap["version"],
            star_rating,
            "(Converted)" if beatmap["mode"] != constants.mode_aliases[mode] else ""),
        description="{} Beatmap {} by [{}](https://osu.ppy.sh/u/{})\nPlayed by [{}](https://osu.ppy.sh/u/{}) {} ago with {}".format(
            ["Pending", "Ranked", "Qualified", "Loved", "Graveyard", "WIP"][int(beatmap["approved"])],
            beatmap["beatmap_id"],
            beatmap["creator"],
            beatmap["creator_id"],
            user["username"],
            user["user_id"],
            delta_string,
            utils.emojify("[mod{}]".format("] [mod".join(enabled_mods)))),
        url="https://osu.ppy.sh/b/{}".format(beatmap["beatmap_id"]),
        color=constants.rank_colors[score_data["rank"]])
    embed.add_field(
        name="{} {:,} ({:0.2f}%) {}x / {}x".format(
            utils.emojify("[ranking{}]".format(score_data["rank"])),
            int(score_data["score"]),
            accuracy,
            score_data["maxcombo"],
            max_combo),
        value="{}\n{}".format(hits, extra_acc_data),
        inline=False)
    if mode == "osu":
        embed.add_field(
            name="**Total pp**: {:0.2f}{} / {:0.2f}".format(
                float(result_score["pp"]) if use_calc in constants.legacy_calcs else result_score["performance_attributes"]["pp"],
                " (@{:0.2f}%)".format(result_score["map_progress"] * 100) if score_data["rank"] == "F" else "",
                float(result_fc["pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["pp"]),
            value="Aim pp: {:0.2f} / {:0.2f}\nSpeed pp: {:0.2f} / {:0.2f}\nAccuracy pp: {:0.2f} / {:0.2f}".format(
                float(result_score["aim pp"]) if use_calc in constants.legacy_calcs else result_score["performance_attributes"]["aim"],
                float(result_fc["aim pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["aim"],
                float(result_score["speed pp"]) if use_calc in constants.legacy_calcs else result_score["performance_attributes"]["speed"],
                float(result_fc["speed pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["speed"],
                float(result_score["accuracy pp"]) if use_calc in constants.legacy_calcs else result_score["performance_attributes"]["accuracy"],
                float(result_fc["accuracy pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["accuracy"]),
            inline=False)
    elif mode == "taiko" or (mode == "mania" and use_calc == "2021-11-09"):
        embed.add_field(
            name="**Total pp**: {:0.2f}{} / {:0.2f}".format(
                float(result_score["pp"]) if use_calc in constants.legacy_calcs else result_score["performance_attributes"]["pp"],
                " (@{:0.2f}%)".format(result_score["map_progress"] * 100) if score_data["rank"] == "F" else "",
                float(result_fc["pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["pp"]),
            value="Difficulty pp: {:0.2f} / {:0.2f}\nAccuracy pp: {:0.2f} / {:0.2f}".format(
                float(result_score["difficulty pp"]) if use_calc in constants.legacy_calcs else result_score["performance_attributes"]["difficulty"],
                float(result_fc["difficulty pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["difficulty"],
                float(result_score["accuracy pp"]) if use_calc in constants.legacy_calcs else result_score["performance_attributes"]["accuracy"],
                float(result_fc["accuracy pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["accuracy"]),
            inline=False)
    elif mode == "catch":
        embed.add_field(
            name="**Total pp**: {:0.2f}{} / {:0.2f}".format(
                float(result_score["pp"]) if use_calc in constants.legacy_calcs else result_score["performance_attributes"]["pp"],
                " (@{:0.2f}%)".format((int(score_data["count300"]) + int(score_data["count100"]) + int(score_data["countmiss"])) * 100 / int(beatmap["maxcombo"])) if score_data["rank"] == "F" else "",
                float(result_fc["pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["pp"]),
            value=".",
            inline=False)
    elif mode == "mania":
        embed.add_field(
            name="**Total pp**: {:0.2f}{} / {:0.2f}".format(
                float(result_score["pp"]) if use_calc in constants.legacy_calcs else result_score["performance_attributes"]["pp"],
                " (@{:0.2f}%)".format(result_score["map_progress"] * 100) if score_data["rank"] == "F" else "",
                float(result_fc["pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["pp"]),
            value="Difficulty pp: {:0.2f} / {:0.2f}".format(
                float(result_score["difficulty pp"]) if use_calc in constants.legacy_calcs else result_score["performance_attributes"]["difficulty"],
                float(result_fc["difficulty pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["difficulty"]),
            inline=False)
    
    embed.set_thumbnail(url="https://b.ppy.sh/thumb/{}l.jpg".format(beatmap["beatmapset_id"]))
    if score_data["rank"] == "F" and mode == "catch":
        embed.set_footer(text="disclaimer: partially completed map pp for ctb is not completely accurate")
    elif score_data["rank"] != "F" and (score_data["pp"] and score_data["pp"] != 0) and pp_error >= settings.pp_error:
        embed.set_footer(text=settings.message_perf_calc_discrepancy.format(float(score_data["pp"])))
    #if use_calc == "loopp" and mode == "taiko":
    #    embed.set_footer(text=settings.message_alt_calc_loopp)
    #if use_calc == "preltca" and mode == "taiko":
    #    embed.set_footer(text=settings.message_alt_calc_preltca)
    if use_calc is not None:
        embed.set_footer(text=settings.message_alt_calc.format(use_calc))

    return embed

def format_single_score_embed_v2(score_data, user, beatmap, use_calc=None):
    discord_timestamp = utils.get_discord_timestamp(timestamp=datetime.datetime.strptime(score_data["ended_at"], settings.timestamp_format_v2))
    enabled_mods = utils.convert_v2_mods_to_array(score_data["mods"])
    #max_combo = utils.get_max_combo(beatmap)
    hits = utils.get_emojified_hits_v2(score_data)
    statistics = utils.get_v2_score_statistics(score_data)

    beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap["id"], beatmap["last_updated"])
    map_parser = OsuBeatmapParser()
    osu_beatmap = map_parser.parse_from_filename(beatmap_file_name)
    
    if "beatmapset" not in beatmap:
        beatmap_artist = osu_beatmap.artist
        beatmap_title = osu_beatmap.title
        beatmap_creator = osu_beatmap.mapper_name
    else:
        beatmap_artist = beatmap["beatmapset"]["artist"]
        beatmap_title = beatmap["beatmapset"]["title"]
        beatmap_creator = beatmap["beatmapset"]["creator"]
    
    for mod in score_data["mods"]:
        if mod["acronym"] == "DA" and "settings" in mod:
            if "circle_size" in mod["settings"]:
                osu_beatmap.cs = mod["settings"]["circle_size"]
            if "approach_rate" in mod["settings"]:
                osu_beatmap.ar = mod["settings"]["approach_rate"]
            if "drain_rate" in mod["settings"]:
                osu_beatmap.hp = mod["settings"]["drain_rate"]
            if "overall_difficulty" in mod["settings"]:
                osu_beatmap.od = mod["settings"]["overall_difficulty"]
        if mod["acronym"] == "HR":
            osu_beatmap.enable_hr()
        if mod["acronym"] == "EZ":
            osu_beatmap.enable_ez()
        if mod["acronym"] in ["DT", "NC", "HT", "DC"] and "settings" in mod and "speed_change" in mod["settings"]:
            #create a temp clone for exporting for perf calc since I need to account for 1.5x from perf calc dt
            osu_beatmap_temp = copy.deepcopy(osu_beatmap)
            osu_beatmap_temp.change_speed(mod["settings"]["speed_change"] / 1.5, False)
            beatmap_file_name = "{}/{}_temp.osu".format(settings.beatmaps_download_folder, beatmap["id"])
            osu_beatmap_temp.export(beatmap_file_name)
    
    #Calculate pp info using PerformanceCalculator
    objects_progress = 0
    ctb_map_completion = 0
    if not score_data["passed"]:
        if score_data["ruleset_id"] == 0:
            objects_progress += statistics["great"] + statistics["ok"] + statistics["meh"] + statistics["miss"]
        elif score_data["ruleset_id"] == 1:
            objects_progress += statistics["great"] + statistics["ok"] + statistics["miss"]
        elif score_data["ruleset_id"] == 2:
            #FIX
            ctb_map_completion = (statistics["great"] + statistics["large_tick_hit"] + statistics["miss"]) / score_data["statistics"]["beatmap"]["max_combo"]
        elif score_data["ruleset_id"] == 3:
            objects_progress += statistics["perfect"] + statistics["great"] + statistics["good"] + statistics["ok"] + statistics["meh"] + statistics["miss"]
    n100 = 0
    if score_data["ruleset_id"] == 2:
        n100 = statistics["large_tick_hit"]
    else:
        n100 = statistics["ok"]
    n50 = 0
    if score_data["ruleset_id"] == 2:
        n50 = statistics["small_tick_hit"]
    elif score_data["ruleset_id"] in [0,3]:
        n50 = statistics["meh"]
    result_score = perf_calc_wrapper.calculate_pp(
        beatmap_file_name,
        mode=constants.modes2[score_data["ruleset_id"]],
        mods=enabled_mods,
        combo=score_data["max_combo"],
        n300=statistics["great"],
        n200=statistics["good"],
        n100=n100,
        n50=n50,
        n0=statistics["miss"],
        score=score_data["total_score"] if utils.is_lazer_score(score_data) else score_data["legacy_total_score"],
        partial=score_data["passed"] == False,
        objects_progress=objects_progress,
        ctb_map_completion=ctb_map_completion,
        use_calc=use_calc)
    result_fc = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=constants.modes2[score_data["ruleset_id"]], mods=enabled_mods, use_calc=use_calc)
    
    #verify pp
    if (score_data["pp"]):
        if use_calc in constants.legacy_calcs:
            pp_error = abs(float(result_score["pp"]) - float(score_data["pp"]))
        else:
            pp_error = abs(float(result_score["performance_attributes"]["pp"]) - float(score_data["pp"]))
    
    #if max_combo == "??":
    #    max_combo = float(result_fc["max combo"].replace(",", ""))
    max_combo = float(result_fc["max combo"].replace(",", "")) if use_calc in constants.legacy_calcs else float(result_fc["difficulty_attributes"]["max_combo"])

    beatmap_length = beatmap["hit_length"]
    beatmap_bpm = beatmap["bpm"]
    
    mods_string = ""
    for mod in score_data["mods"]:
        if not utils.is_lazer_score(score_data) and mod["acronym"] == "CL":
            continue
        mods_string += "[mod{}]".format(mod["acronym"])
        if mod["acronym"] in ["DT", "NC", "HT", "DC"]:
            if "settings" in mod and "speed_change" in mod["settings"]:
                mods_string += "(x{})".format(mod["settings"]["speed_change"])
                beatmap_length = int(beatmap_length / mod["settings"]["speed_change"])
                beatmap_bpm = beatmap_bpm * mod["settings"]["speed_change"]
                osu_beatmap.change_speed(mod["settings"]["speed_change"], True, score_data["ruleset_id"])
            else:
                if mod["acronym"] in ["DT", "NC"]:
                    beatmap_length = int(beatmap_length / 1.5)
                    beatmap_bpm *= 1.5
                    osu_beatmap.change_speed(1.5, True, score_data["ruleset_id"])
                if mod["acronym"] in ["HT", "DC"]:
                    beatmap_length = int(beatmap_length / 0.75)
                    beatmap_bpm *= 0.75
                    osu_beatmap.change_speed(0.75, True, score_data["ruleset_id"])
        if mod["acronym"] == "DA" and "settings" in mod:
            mod_settings = []
            if "circle_size" in mod["settings"]:
                mod_settings.append("CS{}".format(mod["settings"]["circle_size"]))
            if "approach_rate" in mod["settings"]:
                mod_settings.append("AR{}".format(mod["settings"]["approach_rate"]))
            if "scroll_speed" in mod["settings"]:
                mod_settings.append("SS{}".format(mod["settings"]["scroll_speed"]))
            if "drain_rate" in mod["settings"]:
                mod_settings.append("HP{}".format(mod["settings"]["drain_rate"]))
            if "overall_difficulty" in mod["settings"]:
                mod_settings.append("OD{}".format(mod["settings"]["overall_difficulty"]))
            mods_string += "({})".format("/".join(mod_settings))
    if not mods_string:
        mods_string = "[modNone]"
    
    the_mode = constants.modes2[score_data["ruleset_id"]]
    embed = discord.Embed(
        title="{} {} - {} [{}] ({:0.2f}☆) {}".format(
            utils.emojify("[mode{}]".format(the_mode)),
            beatmap_artist,
            beatmap_title,
            beatmap["version"],
            float(result_fc["star rating"]) if use_calc in constants.legacy_calcs else float(result_fc["difficulty_attributes"]["star_rating"]),
            "(Converted)" if beatmap["mode"] != the_mode else ""),
        description="{} Beatmap {} by [{}](https://osu.ppy.sh/u/{})\nPlayed in {} by [{}](https://osu.ppy.sh/u/{}) {} with {}\n{} {:02d}:{:02d} {} {} {} {} {} {} {} {} {} {}".format(
            beatmap['status'].capitalize(),
            beatmap["id"],
            beatmap_creator,
            beatmap["user_id"],
            "Lazer" if utils.is_lazer_score(score_data) else "Stable",
            user["username"],
            user["id"],
            discord_timestamp,
            utils.emojify(mods_string),
            utils.emojify("[total_length]"),
            beatmap_length // 60,
            beatmap_length % 60,
            utils.emojify("[bpm]"),
            round(beatmap_bpm, 2) if beatmap_bpm != int(beatmap_bpm) else int(beatmap_bpm),
            utils.emojify("[cs]"),
            round(osu_beatmap.cs, 2) if osu_beatmap.cs != int(osu_beatmap.cs) else int(osu_beatmap.cs),
            utils.emojify("[ar]"),
            round(osu_beatmap.ar, 2) if osu_beatmap.ar != int(osu_beatmap.ar) else int(osu_beatmap.ar),
            utils.emojify("[od]"),
            round(osu_beatmap.od, 2) if osu_beatmap.od != int(osu_beatmap.od) else int(osu_beatmap.od),
            utils.emojify("[hp]"),
            round(osu_beatmap.hp, 2) if osu_beatmap.hp != int(osu_beatmap.hp) else int(osu_beatmap.hp)),
        url="https://osu.ppy.sh/b/{}".format(beatmap["id"]),
        color=constants.rank_colors[score_data["rank"]])
    embed.add_field(
        name="{} {:,} ({:0.2f}%) {}x / {:0.0f}x".format(
            utils.emojify("[ranking{}]".format(score_data["rank"])),
            score_data["total_score"] if utils.is_lazer_score(score_data) else score_data["legacy_total_score"],
            score_data["accuracy"] * 100,
            score_data["max_combo"],
            max_combo),
        value="{}".format(hits),
        inline=False)
    if score_data["ruleset_id"] == 0:
        embed.add_field(
            name="**Total pp**: {:0.2f}{} / {:0.2f}".format(
                float(result_score["pp"]) if use_calc in constants.legacy_calcs else float(result_score["performance_attributes"]["pp"]),
                " (@{:0.2f}%)".format(result_score["map_progress"] * 100) if score_data["passed"] == False else "",
                float(result_fc["pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["pp"])),
            value="Aim pp: {:0.2f} / {:0.2f}\nSpeed pp: {:0.2f} / {:0.2f}\nAccuracy pp: {:0.2f} / {:0.2f}".format(
                float(result_score["aim pp"]) if use_calc in constants.legacy_calcs else float(result_score["performance_attributes"]["aim"]),
                float(result_fc["aim pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["aim"]),
                float(result_score["speed pp"]) if use_calc in constants.legacy_calcs else float(result_score["performance_attributes"]["speed"]),
                float(result_fc["speed pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["speed"]),
                float(result_score["accuracy pp"]) if use_calc in constants.legacy_calcs else float(result_score["performance_attributes"]["accuracy"]),
                float(result_fc["accuracy pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["accuracy"])),
            inline=False)
    elif score_data["ruleset_id"] == 1 or (score_data["ruleset_id"] == 3 and use_calc == "2021-11-09"):
        embed.add_field(
            name="**Total pp**: {:0.2f}{} / {:0.2f}".format(
                float(result_score["pp"]) if use_calc in constants.legacy_calcs else float(result_score["performance_attributes"]["pp"]),
                " (@{:0.2f}%)".format(result_score["map_progress"] * 100) if score_data["passed"] == False else "",
                float(result_fc["pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["pp"])),
            value="Difficulty pp: {:0.2f} / {:0.2f}\nAccuracy pp: {:0.2f} / {:0.2f}".format(
                float(result_score["difficulty pp"]) if use_calc in constants.legacy_calcs else float(result_score["performance_attributes"]["difficulty"]),
                float(result_fc["difficulty pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["difficulty"]),
                float(result_score["accuracy pp"]) if use_calc in constants.legacy_calcs else float(result_score["performance_attributes"]["accuracy"]),
                float(result_fc["accuracy pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["accuracy"])),
            inline=False)
    elif score_data["ruleset_id"] == 2:
        embed.add_field(
            name="**Total pp**: {:0.2f}{} / {:0.2f}".format(
                float(result_score["pp"]) if use_calc in constants.legacy_calcs else float(result_score["performance_attributes"]["pp"]),
                " (@{:0.2f}%)".format(ctb_map_completion * 100) if score_data["passed"] == False else "",
                float(result_fc["pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["pp"])),
            value=".",
            inline=False)
    elif score_data["ruleset_id"] == 3:
        embed.add_field(
            name="**Total pp**: {:0.2f}{} / {:0.2f}".format(
                float(result_score["pp"]) if use_calc in constants.legacy_calcs else float(result_score["performance_attributes"]["pp"]),
                " (@{:0.2f}%)".format(result_score["map_progress"] * 100) if score_data["passed"] == False else "",
                float(result_fc["pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["pp"])),
            value="Difficulty pp: {:0.2f} / {:0.2f}".format(
                float(result_score["difficulty pp"]) if use_calc in constants.legacy_calcs else float(result_score["performance_attributes"]["difficulty"]),
                float(result_fc["difficulty pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["difficulty"])),
            inline=False)
    
    embed.set_thumbnail(url="https://b.ppy.sh/thumb/{}l.jpg".format(beatmap["beatmapset_id"]))
    if score_data["passed"] == False and score_data["ruleset_id"] == 2:
        embed.set_footer(text="disclaimer: partially completed map pp for ctb is not completely accurate")
    elif score_data["passed"] != False and (score_data["pp"] and score_data["pp"] != 0) and pp_error >= settings.pp_error:
        embed.set_footer(text=settings.message_perf_calc_discrepancy.format(float(score_data["pp"])))
    #if use_calc == "loopp" and score_data["ruleset_id"] == 1:
    #    embed.set_footer(text=settings.message_alt_calc_loopp)
    #if use_calc == "preltca" and score_data["ruleset_id"] == 1:
    #    embed.set_footer(text=settings.message_alt_calc_preltca)
    if use_calc is not None:
        embed.set_footer(text=settings.message_alt_calc.format(use_calc))
    return embed

def format_multiple_scores_embed(score_list, mode, desc="Scores", result_range=None, sort_by="", use_calc=None):
    if mode == "catch":
        return discord.Embed(title=settings.message_ctb_score_unsupported)
    
    for i in range(len(score_list)):
        score_list[i]["number"] = i+1
    
    if result_range is None:
        result_range = (0, settings.default_num_scores)
    #result_range should be a tuple of two positive integers which are within the length of score_list
    try:
        score_list = score_list[result_range[0]:result_range[1]]
    except (TypeError, IndexError):
        result_range = (0, settings.default_num_scores)
        score_list = score_list[result_range[0]:result_range[1]]
    
    user_list = []
    beatmap_list = []
    for score_data in score_list:
        user_list.append(score_data["user_id"])
        beatmap_list.append(score_data["beatmap_id"])
    user_list = utils.remove_duplicates(user_list)
    beatmap_list = utils.remove_duplicates(beatmap_list)
    
    description = ""
    #One player, multiple beatmaps
    if len(user_list) == 1 and len(beatmap_list) > 1:
        user = osu_api_wrapper.get_user(**{"u":user_list[0], "m":constants.mode_aliases[mode]})[0]
        sort_desc = " (Sorted by {})".format(sort_by) if sort_by else ""
        embed = discord.Embed(title="{} {} for {}{}".format(utils.emojify("[mode{}]".format(mode)), desc, user["username"], sort_desc), url="https://osu.ppy.sh/u/{}".format(user["user_id"]))
    #Multiple players, one beatmap
    elif len(user_list) > 1 and len(beatmap_list) == 1:
        beatmap = osu_api_wrapper.get_beatmaps(**{"b":score_data["beatmap_id"], "m":constants.mode_aliases[mode], "a":"1"})[0]
        beatmap_title = "{} - {} [{}] ({:0.2f}☆) {}".format(beatmap["artist"], beatmap["title"], beatmap["version"], float(beatmap["difficultyrating"]), "(Converted)" if beatmap["mode"] != constants.mode_aliases[mode] else "")
        beatmap_status = ["Pending", "Ranked", "Qualified", "Loved", "Graveyard", "WIP"][int(beatmap["approved"])]
        embed = discord.Embed(title="{} {}".format(utils.emojify("[mode{}]".format(mode)), desc))
        description += "**[{}]({})**\n{} Beatmap {} mapped by **{}**\n".format(beatmap_title, "https://osu.ppy.sh/b/{}".format(beatmap["beatmap_id"]), beatmap_status, beatmap["beatmap_id"], beatmap["creator"])
    #One player, one beatmap
    else:
        user = osu_api_wrapper.get_user(**{"u":user_list[0], "m":constants.mode_aliases[mode]})[0]
        beatmap = osu_api_wrapper.get_beatmaps(**{"b":score_data["beatmap_id"], "m":constants.mode_aliases[mode], "a":"1"})[0]
        beatmap_title = "{} - {} [{}] ({:0.2f}☆) {}".format(beatmap["artist"], beatmap["title"], beatmap["version"], float(beatmap["difficultyrating"]), "(Converted)" if beatmap["mode"] != constants.mode_aliases[mode] else "")
        beatmap_status = ["Pending", "Ranked", "Qualified", "Loved", "Graveyard", "WIP"][int(beatmap["approved"])]
        embed = discord.Embed(title="{} {}'s {}".format(utils.emojify("[mode{}]".format(mode)), user["username"], desc), url="https://osu.ppy.sh/u/{}".format(user["user_id"]))
        description += "**[{}]({})**\n{} Beatmap {} mapped by **{}**\n".format(beatmap_title, "https://osu.ppy.sh/b/{}".format(beatmap["beatmap_id"]), beatmap_status, beatmap["beatmap_id"], beatmap["creator"])
    
    beatmap_file_name = None
    for i in range(len(score_list)):
        score_data = score_list[i]
        
        #Grab some other info
        #Multiple players, one beatmap
        if len(user_list) > 1 and len(beatmap_list) == 1:
            user = osu_api_wrapper.get_user(**{"u":score_data["user_id"], "m":constants.mode_aliases[mode]})[0]
            description += "**{}. [{}](https://osu.ppy.sh/u/{})**\n".format(score_data["number"], user["username"], user["user_id"])
        #One player, multiple beatmaps
        elif len(user_list) == 1 and len(beatmap_list) > 1:
            beatmap = osu_api_wrapper.get_beatmaps(**{"b":score_data["beatmap_id"], "m":constants.mode_aliases[mode], "a":"1", "mods":utils.ignore_irrelevant_mods(int(score_data["enabled_mods"]))})[0]
            beatmap_title = "{} - {} [{}] ({:0.2f}☆) {}".format(beatmap["artist"], beatmap["title"], beatmap["version"], float(beatmap["difficultyrating"]), "(Converted)" if beatmap["mode"] != constants.mode_aliases[mode] else "")
            beatmap_status = ["Pending", "Ranked", "Qualified", "Loved", "Graveyard", "WIP"][int(beatmap["approved"])]
            description += "**{}. [{}](https://osu.ppy.sh/b/{})**\n{} Beatmap (id: {}) mapped by **{}**\n".format(score_data["number"], beatmap_title, beatmap["beatmap_id"], beatmap_status, beatmap["beatmap_id"], beatmap["creator"])
        #One player, one beatmap
        else:
            description += "**{}. **".format(i+1)
        
        #Hits and accuracy
        accuracy = utils.calculate_accuracy(score_data, mode)
        hits = utils.get_emojified_hits(score_data, mode)
        
        #Determine max combo
        max_combo = utils.get_max_combo(beatmap)
        
        #How long ago?
        delta_string = utils.get_delta_string(score_data["date"])
    
        #Determine mods
        enabled_mods = utils.get_mods_from_int(score_data["enabled_mods"])
        
        #Calculate pp info using PerformanceCalculator
        if beatmap_file_name is None or len(beatmap_list) > 1:
            beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap["beatmap_id"], beatmap["last_update"])
        result_score = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=mode, mods=enabled_mods, combo=score_data["maxcombo"], n100=score_data["count100"], n50=score_data["count50"], n0=score_data["countmiss"], partial=score_data["rank"]=="F", use_calc=use_calc)
        pp = float(result_score["pp"]) if use_calc in constants.legacy_calcs else float(result_score["performance_attributes"]["pp"])
        result_fc = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=mode, mods=enabled_mods, use_calc=use_calc)
        max_pp = float(result_fc["pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["pp"])

        #verify pp
        '''
        pp_error = None
        if use_calc is not None and score_data["pp"]:
            if use_calc in constants.legacy_calcs:
                pp_error = abs(pp - float(score_data["pp"]))
            else:
                pp_error = abs(max_pp - float(score_data["pp"]))
        '''
        
        #For the NM emoji
        if not enabled_mods:
            enabled_mods.append("None")
        
        description += "Played {} ago with {}\n{} {:,} (**{:0.2f}%**) **{}x** / {}x [**{:0.2f}pp** / {:0.2f}pp]\n{}\n".format(
            delta_string,
            utils.emojify("[mod{}]".format("] [mod".join(enabled_mods))),
            utils.emojify("[ranking{}]".format(score_data["rank"])),
            int(score_data["score"]),
            accuracy,
            score_data["maxcombo"],
            max_combo,
            pp,
            max_pp,
            hits)
    
    embed.description = description
    if use_calc is not None:
        embed.set_footer(text=settings.message_alt_calc.format(use_calc))
    return embed

def format_multiple_scores_embed_v2(score_list, user_data, beatmap_data, beatmap_attributes_data, desc="Scores", sort_by="", use_calc=None):
    mode = constants.modes2[score_list[0]["ruleset_id"]]
    #for i in range(len(score_list)):
    #    score_list[i]["number"] = i+1
    
    description = ""
    #One player, multiple beatmaps
    if len(user_data.keys()) == 1 and len(beatmap_data.keys()) > 1:
        user = list(user_data.values())[0]
        sort_desc = " (Sorted by {})".format(sort_by) if sort_by else ""
        embed = discord.Embed(title="{} {} for {}{}".format(utils.emojify("[mode{}]".format(mode)), desc, user["username"], sort_desc), url="https://osu.ppy.sh/u/{}".format(user["id"]))
    #Multiple players, one beatmap
    elif len(user_data.keys()) > 1 and len(beatmap_data.keys()) == 1:
        beatmap = list(beatmap_data.values())[0]
        beatmapset = beatmap["beatmapset"]
        beatmap_attributes = beatmap_attributes_data[beatmap["beatmap_id"]]
        beatmap_title = "{} - {} [{}] ({:0.2f}☆){}".format(beatmapset["artist"], beatmapset["title"], beatmap["version"], float(beatmap_attributes["star_rating"]), " (Converted)" if beatmap["mode"] != mode else "")
        embed = discord.Embed(title="{} {}".format(utils.emojify("[mode{}]".format(mode)), desc))
        description += "**[{}]({})**\n{} Beatmap {} mapped by **{}**\n".format(beatmap_title, "https://osu.ppy.sh/b/{}".format(beatmap["beatmap_id"]), beatmap['status'].capitalize(), beatmap["beatmap_id"], beatmapset["creator"])
    #One player, one beatmap
    else:
        user = list(user_data.values())[0]
        beatmap = list(beatmap_data.values())[0]
        beatmapset = beatmap["beatmapset"]
        beatmap_attributes = beatmap_attributes_data[beatmap["id"]]
        beatmap_title = "{} - {} [{}] ({:0.2f}☆){}".format(beatmapset["artist"], beatmapset["title"], beatmap["version"], float(beatmap_attributes["star_rating"]), " (Converted)" if beatmap["mode"] != mode else "")
        embed = discord.Embed(title="{} {}'s {}".format(utils.emojify("[mode{}]".format(mode)), user["username"], desc), url="https://osu.ppy.sh/u/{}".format(user["id"]))
        description += "**[{}]({})**\n{} Beatmap {} mapped by **{}**\n".format(beatmap_title, "https://osu.ppy.sh/b/{}".format(beatmap["id"]), beatmap['status'].capitalize(), beatmap["id"], beatmapset["creator"])
    
    beatmap_file_name = None
    for i in range(len(score_list)):
        score_data = score_list[i]
        user_id = score_data["user_id"]
        beatmap_id = score_data["beatmap_id"]
        user = user_data[user_id]
        beatmap = beatmap_data[beatmap_id]
        beatmapset = beatmap["beatmapset"]
        
        delta_string = utils.get_discord_timestamp(timestamp=datetime.datetime.strptime(score_data["ended_at"], settings.timestamp_format_v2))
        enabled_mods = utils.convert_v2_mods_to_array(score_data["mods"])
        max_combo = utils.get_max_combo(beatmap)
        hits = utils.get_emojified_hits_v2(score_data)
        statistics = utils.get_v2_score_statistics(score_data)
        
        #if beatmap_file_name is None or len(beatmap_data.keys()) > 1:
        beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap["id"], beatmap["last_updated"])
        map_parser = OsuBeatmapParser()
        osu_beatmap = map_parser.parse_from_filename(beatmap_file_name)
        
        for mod in score_data["mods"]:
            if mod["acronym"] in ["DT", "NC", "HT", "DC"] and "settings" in mod and "speed_change" in mod["settings"]:
                #accounting for the 1.5x multiplier from perf calc
                osu_beatmap.change_speed(mod["settings"]["speed_change"] / 1.5)
                beatmap_file_name = "{}/{}_temp.osu".format(settings.beatmaps_download_folder, beatmap["id"])
                osu_beatmap.export(beatmap_file_name)
        
        #Calculate pp info using PerformanceCalculator
        objects_progress = 0
        ctb_map_completion = 0
        if not score_data["passed"]:
            if score_data["ruleset_id"] in [0,1]:
                objects_progress += statistics["great"] + statistics["ok"] + statistics["meh"] + statistics["miss"]
            elif score_data["ruleset_id"] == 2:
                #FIX
                ctb_map_completion = (statistics["great"] + statistics["large_tick_hit"] + statistics["miss"]) / statistics["beatmap"]["max_combo"]
            elif score_data["ruleset_id"] == 3:
                objects_progress += statistics["perfect"] + statistics["great"] + statistics["good"] + statistics["ok"] + statistics["meh"] + statistics["miss"]
        
        n100 = 0
        if score_data["ruleset_id"] == 2:
            n100 = statistics["large_tick_hit"]
        else:
            n100 = statistics["ok"]
        n50 = 0
        if score_data["ruleset_id"] == 2:
            n50 = statistics["small_tick_hit"]
        elif score_data["ruleset_id"] in [0,3]:
            n50 = statistics["meh"]
        result_score = perf_calc_wrapper.calculate_pp(
            beatmap_file_name,
            mode=mode,
            mods=enabled_mods,
            combo=score_data["max_combo"],
            n200=statistics["good"],
            n100=n100,
            n50=n50,
            n0=statistics["miss"],
            partial=score_data["rank"]=="F",
            objects_progress=objects_progress,
            ctb_map_completion=ctb_map_completion,
            use_calc=use_calc)
        pp = float(result_score["pp"]) if use_calc in constants.legacy_calcs else result_score["performance_attributes"]["pp"]
        result_fc = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=mode, mods=enabled_mods, use_calc=use_calc)
        max_pp = float(result_fc["pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["pp"]
        star_rating = float(result_fc["star rating"]) if use_calc in constants.legacy_calcs else float(result_fc["difficulty_attributes"]["star_rating"])
        
        if max_combo == "??":
            max_combo = float(result_fc["max combo"].replace(",", ""))
        
        mods_string = ""
        for mod in score_data["mods"]:
            if not utils.is_lazer_score(score_data) and mod["acronym"] == "CL":
                continue
            mods_string += "[mod{}]".format(mod["acronym"])
            if mod["acronym"] in ["DT", "NC", "HT", "DC"] and "settings" in mod and "speed_change" in mod["settings"]:
                mods_string += "(x{})".format(mod["settings"]["speed_change"])
            if mod["acronym"] == "DA" and "settings" in mod:
                mod_settings = []
                if "circle_size" in mod["settings"]:
                    mod_settings.append("CS{}".format(mod["settings"]["circle_size"]))
                if "approach_rate" in mod["settings"]:
                    mod_settings.append("AR{}".format(mod["settings"]["approach_rate"]))
                if "scroll_speed" in mod["settings"]:
                    mod_settings.append("SS{}".format(mod["settings"]["scroll_speed"]))
                if "drain_rate" in mod["settings"]:
                    mod_settings.append("HP{}".format(mod["settings"]["drain_rate"]))
                if "overall_difficulty" in mod["settings"]:
                    mod_settings.append("OD{}".format(mod["settings"]["overall_difficulty"]))
                mods_string += "({})".format("/".join(mod_settings))
        if not mods_string:
            mods_string = "[modNone]"
        
        #Multiple players, one beatmap
        if len(user_data.keys()) > 1 and len(beatmap_data.keys()) == 1:
            description += "**{}\. [{}](https://osu.ppy.sh/u/{})**\n".format(score_data["index"], user["username"], user["user_id"])
        #One player, multiple beatmaps
        elif len(user_data.keys()) == 1 and len(beatmap_data.keys()) > 1:
            beatmap_title = "{} - {} [{}] ({:0.2f}☆){}".format(beatmapset["artist"], beatmapset["title"], beatmap["version"], star_rating, " (Converted)" if beatmap["mode"] != mode else "")
            description += "**{}\. [{}](https://osu.ppy.sh/b/{})**\n{} Beatmap (id: {}) mapped by **{}**\n".format(score_data["index"], beatmap_title, beatmap_id, beatmap['status'].capitalize(), beatmap_id, beatmapset["creator"])
        #One player, one beatmap
        else:
            description += "**{}\. **".format(i+1)
        
        description += "Played in {} {} {}\n{} {:,} (**{:0.2f}%**) **{}x** / {}x [**{:0.2f}pp** / {:0.2f}pp]\n{}\n".format(
            "Lazer" if utils.is_lazer_score(score_data) else "Stable",
            delta_string,
            utils.emojify(mods_string),
            utils.emojify("[ranking{}]".format(score_data["rank"])),
            score_data["total_score"] if utils.is_lazer_score(score_data) else score_data["legacy_total_score"],
            score_data["accuracy"] * 100,
            score_data["max_combo"],
            max_combo,
            pp,
            max_pp,
            hits)
    
    embed.description = description
    if use_calc is not None:
        embed.set_footer(text=settings.message_alt_calc.format(use_calc))
    return embed

def format_single_beatmap_embed(beatmap_data, use_calc=None):
    mode = constants.modes[beatmap_data["mode"]]
    if mode == "catch":
        return discord.Embed(title=settings.message_ctb_map_unsupported)
    
    #Format dates
    date_string = "**Submitted**: {} ago\n**{}**: {} ago".format(
        utils.get_delta_string(beatmap_data["submit_date"]),
        "Last Updated" if beatmap_data["approved"] in ["0", "-1", "-2"] else {"1":"Ranked", "2":"Approved", "3":"Qualified", "4":"Loved"}[beatmap_data["approved"]],
        utils.get_delta_string(beatmap_data["approved_date"] or beatmap_data["last_update"]))
    
    #Determine max combo
    max_combo = utils.get_max_combo(beatmap_data)
    if max_combo != "??":
        max_combo_string = " / **Max Combo**: {}".format(max_combo)
    else:
        max_combo_string = ""
    
    #Calculate pp info using PerformanceCalculator
    beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap_data["beatmap_id"], beatmap_data["last_update"])
    result_fc = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=mode, use_calc=use_calc)
    if mode == "osu":
        ppstring = "\n**Max PP**: {:0.2f} (**Aim**: {:0.2f} / **Speed**: {:0.2f} / **Accuracy**: {:0.2f})".format(
            float(result_fc["pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["pp"],
            float(result_fc["aim pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["aim"],
            float(result_fc["speed pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["speed"],
            float(result_fc["accuracy pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["accuracy"])
    elif mode == "taiko" or (mode == "mania" and use_calc == "2021-11-09"):
        ppstring = "\n**Max PP**: {:0.2f} (**Difficulty PP**: {:0.2f} / **Accuracy PP**: {:0.2f})".format(
            float(result_fc["pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["pp"],
            float(result_fc["difficulty pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["difficulty"],
            float(result_fc["accuracy pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["accuracy"])
    elif mode == "mania":
        ppstring = "\n**Max PP**: {:0.2f} (**Difficulty PP**: {:0.2f})".format(
            float(result_fc["pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["pp"],
            float(result_fc["difficulty pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["difficulty"])
    
    #Calculate pass rate (decided not to show it though because it seems pretty useless)
    if beatmap_data["playcount"] != "0":
        pass_rate_string = "\n**Pass rate**: {:,} / {:,} ({:0.2f}%)".format(int(beatmap_data["passcount"]), int(beatmap_data["playcount"]), int(beatmap_data["passcount"]) / int(beatmap_data["playcount"]) * 100)
    else:
        pass_rate_string = ""
    
    beatmap_title = "{} {} - {} [{}] ({:0.2f}☆)".format(
        utils.emojify("[mode{}]".format(mode)),
        beatmap_data["artist"],
        beatmap_data["title"],
        beatmap_data["version"],
        float(result_fc["star rating"]) if "star rating" in result_fc else float(beatmap_data["difficultyrating"]))
    
    description = "**Beatmap {} (set {}) mapped by** [{}](https://osu.ppy.sh/u/{})\n▶️ {} ❤️ {}\n{}\n{} {:02d}:{:02d} ({:02d}:{:02d}) {} {} {} {} {} {}\n**CS**: {} / **AR**: {} / **OD**: {} / **HP**: {}{}{}".format(
        beatmap_data["beatmap_id"],
        beatmap_data["beatmapset_id"],
        beatmap_data["creator"],
        beatmap_data["creator_id"],
        beatmap_data["playcount"],
        beatmap_data["favourite_count"],
        date_string,
        utils.emojify("[total_length]"),
        int(beatmap_data["total_length"]) // 60,
        int(beatmap_data["total_length"]) % 60,
        int(beatmap_data["hit_length"]) // 60,
        int(beatmap_data["hit_length"]) % 60,
        utils.emojify("[bpm]"),
        beatmap_data["bpm"],
        utils.emojify("[count_circles]"),
        beatmap_data["count_normal"],
        utils.emojify("[count_sliders]"),
        beatmap_data["count_slider"],
        beatmap_data["diff_size"],
        beatmap_data["diff_approach"],
        beatmap_data["diff_overall"],
        beatmap_data["diff_drain"],
        max_combo_string,
        ppstring)
    
    embed = discord.Embed(title=beatmap_title, description=description, url="https://osu.ppy.sh/b/{}".format(beatmap_data["beatmap_id"]))
    embed.set_thumbnail(url="https://b.ppy.sh/thumb/{}l.jpg".format(beatmap_data["beatmapset_id"]))
    return embed

def format_single_beatmap_embed_v2(beatmap_data, use_calc=None):
    mode = beatmap_data["mode"]

    #Format dates
    date_string = "**Submitted**: {}\n**{}**: {}".format(
        utils.get_discord_timestamp(timestamp=datetime.datetime.strptime(beatmap_data["beatmapset"]["submitted_date"], settings.timestamp_format_v2)),
        "Last Updated" if beatmap_data["ranked"] <= 0 else ["", "Ranked", "Approved", "Qualified", "Loved"][beatmap_data["ranked"]],
        utils.get_discord_timestamp(timestamp=datetime.datetime.strptime(beatmap_data["beatmapset"]["ranked_date"], settings.timestamp_format_v2)) if beatmap_data["ranked"] > 0 else utils.get_discord_timestamp(timestamp=datetime.datetime.strptime(beatmap_data["beatmapset"]["last_updated"], settings.timestamp_format_v2)))
    
    #Determine max combo
    max_combo = utils.get_max_combo(beatmap_data)
    if max_combo != "??":
        max_combo_string = " / **Max Combo**: {}".format(max_combo)
    else:
        max_combo_string = ""
    
    #Calculate pp info using PerformanceCalculator
    beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap_data["id"], beatmap_data["last_updated"])
    result_fc = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=mode, use_calc=use_calc)
    if mode == "osu":
        ppstring = "\n**Max PP**: {:0.2f} (**Aim**: {:0.2f} / **Speed**: {:0.2f} / **Accuracy**: {:0.2f})".format(
            float(result_fc["pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["pp"],
            float(result_fc["aim pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["aim"],
            float(result_fc["speed pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["speed"],
            float(result_fc["accuracy pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["accuracy"])
    elif mode == "taiko" or (mode == "mania" and use_calc == "2021-11-09"):
        ppstring = "\n**Max PP**: {:0.2f} (**Difficulty PP**: {:0.2f} / **Accuracy PP**: {:0.2f})".format(
            float(result_fc["pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["pp"],
            float(result_fc["difficulty pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["difficulty"],
            float(result_fc["accuracy pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["accuracy"])
    elif mode == "mania":
        ppstring = "\n**Max PP**: {:0.2f} (**Difficulty PP**: {:0.2f})".format(
            float(result_fc["pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["pp"],
            float(result_fc["difficulty pp"]) if use_calc in constants.legacy_calcs else result_fc["performance_attributes"]["difficulty"])
    
    #Calculate pass rate (decided not to show it though because it seems pretty useless)
    if beatmap_data["playcount"] != 0:
        pass_rate_string = "\n**Pass rate**: {:,} / {:,} ({:0.2f}%)".format(int(beatmap_data["passcount"]), int(beatmap_data["playcount"]), int(beatmap_data["passcount"]) / int(beatmap_data["playcount"]) * 100)
    else:
        pass_rate_string = ""
    
    mappers_string = ""
    if len(beatmap_data["owners"]) < 4:
        mappers_string = ", ".join(["[{}](https://osu.ppy.sh/u/{})".format(mapper["username"], mapper["id"]) for mapper in beatmap_data["owners"]])
        if beatmap_data["beatmapset"]["user_id"] not in [mapper["id"] for mapper in beatmap_data["owners"]]:
            mappers_string += "(set owner: [{}](https://osu.ppy.sh/u/{}))".format(beatmap_data["beatmapset"]["creator"], beatmap_data["beatmapset"]["user_id"])
    else:
        mappers_string = "{} mappers (set owner: [{}](https://osu.ppy.sh/u/{}))".format(
            len(beatmap_data["owners"]), beatmap_data["beatmapset"]["creator"], beatmap_data["beatmapset"]["user_id"])
    
    beatmap_title = "{} {} - {} [{}] ({:0.2f}☆)".format(
        utils.emojify("[mode{}]".format(mode)),
        beatmap_data["beatmapset"]["artist"],
        beatmap_data["beatmapset"]["title"],
        beatmap_data["version"],
        float(result_fc["star rating"]) if "star rating" in result_fc else float(beatmap_data["difficulty_rating"]))
    
    description = "**Beatmap {} (set {}) mapped by** {}\n▶️ {} ❤️ {}\n{}\n{} {:02d}:{:02d} ({:02d}:{:02d}) {} {} {} {} {} {} {} {}\n**CS**: {} / **AR**: {} / **OD**: {} / **HP**: {}{}{}".format(
        beatmap_data["id"],
        beatmap_data["beatmapset_id"],
        mappers_string,
        beatmap_data["beatmapset"]["play_count"],
        beatmap_data["beatmapset"]["favourite_count"],
        date_string,
        utils.emojify("[total_length]"),
        int(beatmap_data["total_length"]) // 60,
        int(beatmap_data["total_length"]) % 60,
        int(beatmap_data["hit_length"]) // 60,
        int(beatmap_data["hit_length"]) % 60,
        utils.emojify("[bpm]"),
        beatmap_data["bpm"],
        utils.emojify("[count_circles]"),
        beatmap_data["count_circles"],
        utils.emojify("[count_sliders]"),
        beatmap_data["count_sliders"],
        utils.emojify("[count_spinners]"),
        beatmap_data["count_spinners"],
        beatmap_data["cs"],
        beatmap_data["ar"],
        beatmap_data["accuracy"],
        beatmap_data["drain"],
        max_combo_string,
        ppstring)
    
    embed = discord.Embed(title=beatmap_title, description=description, url="https://osu.ppy.sh/b/{}".format(beatmap_data["id"]))
    embed.set_thumbnail(url="https://b.ppy.sh/thumb/{}l.jpg".format(beatmap_data["beatmapset_id"]))
    return embed

def format_multiple_beatmaps_embed(beatmap_list):
    beatmap_set_list = []
    for beatmap_data in beatmap_list:
        beatmap_set_list.append(beatmap_data["beatmapset_id"])
    beatmap_set_list = utils.remove_duplicates(beatmap_set_list)
    
    if len(beatmap_set_list) == 1:
        description = "Beatmap set {} mapped by [{}](https://osu.ppy.sh/u/{})\n".format(beatmap_list[0]["beatmapset_id"], beatmap_list[0]["creator"], beatmap_list[0]["creator_id"])
    else:
        description = ""
    for beatmap_data in beatmap_list:
        mode = constants.modes[beatmap_data["mode"]]
        if mode == "catch":
            continue
        
        if len(beatmap_set_list) == 1:
            description += "{} [[{}] ({:0.2f}☆)](https://osu.ppy.sh/b/{})\n".format(
                utils.emojify("[mode{}]".format(mode)),
                beatmap_data["version"],
                float(beatmap_data["difficultyrating"]),
                beatmap_data["beatmap_id"])
        else:
            description += "{} [{} - {} [{}] ({:0.2f}☆)](https://osu.ppy.sh/b/{})\nBeatmap {} mapped by [{}](https://osu.ppy.sh/u/{})\n".format(
                utils.emojify("[mode{}]".format(mode)),
                beatmap_data["artist"],
                beatmap_data["title"],
                beatmap_data["version"],
                float(beatmap_data["difficultyrating"]),
                beatmap_data["beatmap_id"],
                beatmap_data["beatmap_id"],
                beatmap_data["creator"],
                beatmap_data["creator_id"])
        
        description += "**Length**: {:02d}:{:02d} (**Drain**: {:02d}:{:02d}) / **BPM**: {}{}\n**CS**: {} / **AR**: {} / **OD**: {} / **HP**: {}\n".format(
            int(beatmap_data["total_length"]) // 60,
            int(beatmap_data["total_length"]) % 60,
            int(beatmap_data["hit_length"]) // 60,
            int(beatmap_data["hit_length"]) % 60,
            beatmap_data["bpm"],
            " / **Max Combo**: {}".format(beatmap_data["maxcombo"]) if beatmap_data["maxcombo"] else "",
            beatmap_data["diff_size"],
            beatmap_data["diff_approach"],
            beatmap_data["diff_overall"],
            beatmap_data["diff_drain"])
    
    if len(beatmap_set_list) == 1:
        title = "{} - {}".format(beatmap_list[0]["artist"], beatmap_list[0]["title"])
        url = "https://osu.ppy.sh/s/{}".format(beatmap_list[0]["beatmapset_id"])
    else:
        title = "Various Beatmaps"
        url = ""
    embed = discord.Embed(title=title, description=description, url=url)
    if len(beatmap_set_list) == 1:
        embed.set_thumbnail(url="https://b.ppy.sh/thumb/{}l.jpg".format(beatmap_list[0]["beatmapset_id"]))
    return embed

def format_pp_simulation(beatmap_data, mode, query_mods, result, result_fc, use_calc=None):
    if use_calc in constants.legacy_calcs:
        if mode == "osu":
            hits = utils.emojify("[hit300] x{:,} / [hit100] x{:,} / [hit50] x{:,} / [hit0] x{:,}".format(
                int(result["great"]),
                int(result["ok"]),
                int(result["meh"]),
                int(result["miss"])))
        elif mode == "taiko":
            hits = utils.emojify("[thit300] x{:,} / [thit100] x{:,} / [thit0] x{:,}".format(
                int(result["great"]),
                int(result["ok"]),
                int(result["miss"])))
        elif mode == "fruits":
            hits = utils.emojify("[chit300] x{:,} / [chit100] x{:,} / [chit50] x{:,} / [chit0] x{:,} / [chit0d] x{:,}".format(
                int(result["great"]),
                int(result["largetickhit"]),
                int(result["smalltickhit"]),
                int(result["miss"]),
                int(result["smalltickmiss"])))
        elif mode == "mania":
            hits = utils.emojify("[mhit300r] x{:,} / [mhit300] x{:,} / [mhit200] x{:,} / [mhit100] x{:,} / [mhit50] x{:,} / [mhit0] x{:,}".format(
                int(result["perfect"]),
                int(result["great"]),
                int(result["good"]),
                int(result["ok"]),
                int(result["meh"]),
                int(result["miss"])))
    else:
        if mode == "osu":
            hits = utils.emojify("[hit300] x{:,} / [hit100] x{:,} / [hit50] x{:,} / [hit0] x{:,}".format(
                int(result["score"]["statistics"]["great"]),
                int(result["score"]["statistics"]["ok"]),
                int(result["score"]["statistics"]["meh"]),
                int(result["score"]["statistics"]["miss"])))
        elif mode == "taiko":
            hits = utils.emojify("[thit300] x{:,} / [thit100] x{:,} / [thit0] x{:,}".format(
                int(result["score"]["statistics"]["great"]),
                int(result["score"]["statistics"]["ok"]),
                int(result["score"]["statistics"]["miss"])))
        elif mode == "catch":
            hits = utils.emojify("[chit300] x{:,} / [chit100] x{:,} / [chit50] x{:,} / [chit0] x{:,} / [chit0d] x{:,}".format(
                int(result["score"]["statistics"]["great"]),
                int(result["score"]["statistics"]["large_tick_hit"]),
                int(result["score"]["statistics"]["small_tick_hit"]),
                int(result["score"]["statistics"]["miss"]),
                int(result["score"]["statistics"]["small_tick_miss"])))
        elif mode == "mania":
            hits = utils.emojify("[mhit300r] x{:,} / [mhit300] x{:,} / [mhit200] x{:,} / [mhit100] x{:,} / [mhit50] x{:,} / [mhit0] x{:,}".format(
                int(result["score"]["statistics"]["perfect"]),
                int(result["score"]["statistics"]["great"]),
                int(result["score"]["statistics"]["good"]),
                int(result["score"]["statistics"]["ok"]),
                int(result["score"]["statistics"]["meh"]),
                int(result["score"]["statistics"]["miss"])))
    
    #For the NM emoji
    if not query_mods:
        query_mods.append("None")
    
    if use_calc in constants.legacy_calcs:
        star_rating = float(result_fc["star rating"]) if "star rating" in result_fc else float(beatmap_data["difficultyrating"])
    else:
        star_rating = float(result_fc["difficulty_attributes"]["star_rating"])
    
    beatmap_length = beatmap_data["hit_length"]
    beatmap_bpm = beatmap_data["bpm"]
    beatmap_cs = beatmap_data["cs"]
    beatmap_ar = beatmap_data["ar"]
    beatmap_od = beatmap_data["accuracy"]
    beatmap_hp = beatmap_data["drain"]

    for mod in query_mods:
        if mod.startswith("DT") or mod.startswith("NC"):
            beatmap_length = int(beatmap_length / 1.5)
            beatmap_bpm = int(beatmap_bpm * 1.5)
        elif mod.startswith("HT"):
            beatmap_length = int(beatmap_length / 0.75)
            beatmap_bpm = int(beatmap_bpm * 0.75)
        elif mod.startswith("HR"):
            beatmap_cs = min(10, beatmap_cs * 1.3)
            beatmap_ar = min(10, beatmap_ar * 1.4)
            beatmap_od = min(10, beatmap_od * 1.4)
            beatmap_hp = min(10, beatmap_hp * 1.4)
        elif mod.startswith("EZ"):
            beatmap_cs *= 0.5
            beatmap_ar *= 0.5
            beatmap_od *= 0.5
            beatmap_hp *= 0.5

    embed = discord.Embed(
        title="{} {} - {} [{}] ({:0.2f}☆) {}".format(
            utils.emojify("[mode{}]".format(mode)),
            beatmap_data["beatmapset"]["artist"],
            beatmap_data["beatmapset"]["title"],
            beatmap_data["version"],
            star_rating,
            "(Converted)" if beatmap_data["mode"] != mode else ""),
        description="Beatmap {} by [{}](https://osu.ppy.sh/u/{})\nMods: {}\n{} {:02d}:{:02d} {} {} {} {} {} {} {} {} {} {}".format(
            beatmap_data["id"],
            beatmap_data["beatmapset"]["creator"],
            beatmap_data["user_id"],
            utils.emojify("[mod{}]".format("] [mod".join(query_mods))),
            utils.emojify("[total_length]"),
            beatmap_length // 60,
            beatmap_length % 60,
            utils.emojify("[bpm]"),
            round(beatmap_bpm, 2) if beatmap_bpm != int(beatmap_bpm) else int(beatmap_bpm),
            utils.emojify("[cs]"),
            round(beatmap_cs, 2) if beatmap_cs != int(beatmap_cs) else int(beatmap_cs),
            utils.emojify("[ar]"),
            round(beatmap_ar, 2) if beatmap_ar != int(beatmap_ar) else int(beatmap_ar),
            utils.emojify("[od]"),
            round(beatmap_od, 2) if beatmap_od != int(beatmap_od) else int(beatmap_od),
            utils.emojify("[hp]"),
            round(beatmap_hp, 2) if beatmap_hp != int(beatmap_hp) else int(beatmap_hp)),
        url="https://osu.ppy.sh/b/{}".format(beatmap_data["id"]))
    if mode == "osu":
        embed.add_field(
            name="({:0.2f}%) {}x / {}x\n{}".format(
                float(result["accuracy"]) if use_calc in constants.legacy_calcs else float(result["score"]["accuracy"]),
                result["combo"] if use_calc in constants.legacy_calcs else result["score"]["combo"],
                result_fc["max combo"] if use_calc in constants.legacy_calcs else result_fc["difficulty_attributes"]["max_combo"],
                hits),
            value="**Total pp: {:0.2f} / {:0.2f}**\nAim pp: {:0.2f} / {:0.2f}\nSpeed pp: {:0.2f} / {:0.2f}\nAccuracy pp: {:0.2f} / {:0.2f}".format(
                float(result["pp"]) if use_calc in constants.legacy_calcs else float(result["performance_attributes"]["pp"]),
                float(result_fc["pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["pp"]),
                float(result["aim pp"]) if use_calc in constants.legacy_calcs else float(result["performance_attributes"]["aim"]),
                float(result_fc["aim pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["aim"]),
                float(result["speed pp"]) if use_calc in constants.legacy_calcs else float(result["performance_attributes"]["speed"]),
                float(result_fc["speed pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["speed"]),
                float(result["accuracy pp"]) if use_calc in constants.legacy_calcs else float(result["performance_attributes"]["accuracy"]),
                float(result_fc["accuracy pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["accuracy"])))
    elif mode == "taiko":
        embed.add_field(
            name="({:0.2f}%) {}x / {}x\n{}".format(
                float(result["accuracy"]) if use_calc in constants.legacy_calcs else float(result["score"]["accuracy"]),
                result["combo"] if use_calc in constants.legacy_calcs else result["score"]["combo"],
                result_fc["great"] if use_calc in constants.legacy_calcs else result_fc["difficulty_attributes"]["max_combo"],
                hits),
            value="**Total pp: {:0.2f} / {:0.2f}**\nDifficulty pp: {:0.2f} / {:0.2f}\nAccuracy pp: {:0.2f} / {:0.2f}".format(
                float(result["pp"]) if use_calc in constants.legacy_calcs else float(result["performance_attributes"]["pp"]),
                float(result_fc["pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["pp"]),
                float(result["difficulty pp"]) if use_calc in constants.legacy_calcs else float(result["performance_attributes"]["difficulty"]),
                float(result_fc["difficulty pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["difficulty"]),
                float(result["accuracy pp"]) if use_calc in constants.legacy_calcs else float(result["performance_attributes"]["accuracy"]),
                float(result_fc["accuracy pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["accuracy"])))
    elif mode == "catch":
        if use_calc in constants.legacy_calcs:
            raw_score = int(result["great"]) + int(result["largetickhit"]) + int(result["smalltickhit"])
            total_hits = raw_score + int(result["miss"]) + int(result["smalltickmiss"])
        else:
            raw_score = int(result["score"]["statistics"]["great"]) + int(result["score"]["statistics"]["large_tick_hit"]) + int(result["score"]["statistics"]["small_tick_hit"])
            total_hits = raw_score + int(result["score"]["statistics"]["miss"]) + int(result["score"]["statistics"]["small_tick_miss"])
        accuracy = (raw_score * 100) / total_hits
        embed.add_field(
            name="({:0.2f}%) {}x / {}x\n{}".format(
                accuracy,
                result["combo"] if use_calc in constants.legacy_calcs else result["score"]["combo"],
                result_fc["max combo"] if use_calc in constants.legacy_calcs else result_fc["difficulty_attributes"]["max_combo"],
                hits),
            value="**Total pp: {:0.2f} / {:0.2f}**".format(
                float(result["pp"]) if use_calc in constants.legacy_calcs else float(result["performance_attributes"]["pp"]),
                float(result_fc["pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["pp"])))
    elif mode == "mania" and use_calc == "2021-11-09":
        embed.add_field(
            name="Score: {:,}".format(int(result["score"])),
            value="**Total pp: {:0.2f} / {:0.2f}**\nDifficulty pp: {:0.2f} / {:0.2f}\nAccuracy pp: {:0.2f} / {:0.2f}".format(
                float(result["pp"]),
                float(result_fc["pp"]),
                float(result["difficulty pp"]),
                float(result_fc["difficulty pp"]),
                float(result["accuracy pp"]),
                float(result_fc["accuracy pp"])))
    elif mode == "mania":
        #Current calc is bugged and doesn't calculate accuracy
        if use_calc is None:
            raw_score = (int(result["score"]["statistics"]["perfect"]) * 300) + (int(result["score"]["statistics"]["great"]) * 300) + (int(result["score"]["statistics"]["good"]) * 200) + (int(result["score"]["statistics"]["ok"]) * 100) + (int(result["score"]["statistics"]["meh"]) * 50)
            total_hits = int(result["score"]["statistics"]["perfect"]) + int(result["score"]["statistics"]["great"]) + int(result["score"]["statistics"]["good"]) + int(result["score"]["statistics"]["ok"]) + int(result["score"]["statistics"]["meh"]) + int(result["score"]["statistics"]["miss"])
            accuracy = (raw_score * 100) / (total_hits * 300)
        else:
            accuracy = float(result["accuracy"]) if use_calc in constants.legacy_calcs else float(result["score"]["accuracy"])
        embed.add_field(
            name="({:0.2f}%)\n{}".format(accuracy, hits),
            value="**Total pp: {:0.2f} / {:0.2f}**\nDifficulty pp: {:0.2f} / {:0.2f}".format(
                float(result["pp"]) if use_calc in constants.legacy_calcs else float(result["performance_attributes"]["pp"]),
                float(result_fc["pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["pp"]),
                float(result["difficulty pp"]) if use_calc in constants.legacy_calcs else float(result["performance_attributes"]["difficulty"]),
                float(result_fc["difficulty pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["difficulty"])))
    embed.set_thumbnail(url="https://b.ppy.sh/thumb/{}l.jpg".format(beatmap_data["beatmapset_id"]))
    #if use_calc == "loopp" and mode == "taiko":
    #    embed.set_footer(text=settings.message_alt_calc_loopp)
    #if use_calc == "preltca" and mode == "taiko":
    #    embed.set_footer(text=settings.message_alt_calc_preltca)
    if use_calc is not None:
        embed.set_footer(text=settings.message_alt_calc.format(use_calc))
    
    return embed