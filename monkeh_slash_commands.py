import datetime, base64, math, hashlib
import discord
import perf_calc_wrapper, beatmap_graph_generator, osu_api_wrapper
from osu_replay_parser import OsuReplayDetails, OsuReplayParser
from osu_replay_analyzer import OsuReplayAnalyzer
from osu_map_parser import OsuBeatmapParser
import yadon
import settings
import constants
import utils
import embed_formatters

async def slash_set_osu(interaction, user:str):
    await interaction.response.defer(thinking=True)
    get_user_response = await osu_api_wrapper.get_user_v2_async(interaction.command.koduck.aiohttp_session, user)
    if not get_user_response:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_get_user_no_result)
    else:
        osu_user = yadon.ReadRowFromTable(settings.osu_users_table, interaction.user.id, named_columns=True)
        if not osu_user:
            osu_user = {}
        osu_user["osu_id"] = get_user_response["id"]
        osu_user["default_mode"] = constants.mode_aliases[get_user_response["playmode"]]
        yadon.WriteRowToTable(settings.osu_users_table, interaction.user.id, osu_user, named_columns=True)
        return await interaction.command.koduck.send_message(interaction, content=settings.message_set_osu_success.format(interaction.user.id, get_user_response["username"], get_user_response["playmode"]))

async def slash_set_default_mode(interaction, mode:constants.GameMode):
    osu_user = yadon.ReadRowFromTable(settings.osu_users_table, interaction.user.id, named_columns=True)
    if not osu_user:
        osu_user = {}
    osu_user["default_mode"] = constants.mode_aliases[mode]
    yadon.WriteRowToTable(settings.osu_users_table, interaction.user.id, osu_user, named_columns=True)
    return await interaction.command.koduck.send_message(interaction, content=settings.message_set_mode_success.format(interaction.user.id, mode))

async def slash_get_user(interaction, user: str=None, mode: constants.GameMode=None):
    await interaction.response.defer(thinking=True)
    osu_user = yadon.ReadRowFromTable(settings.osu_users_table, interaction.user.id, named_columns=True)
    if not user:
        if osu_user is None or osu_user["osu_id"] == "":
            return await interaction.command.koduck.send_message(interaction, content=settings.message_osu_not_linked)
        else:
            user = osu_user["osu_id"]
    if not mode:
        if osu_user is None or osu_user["default_mode"] == "":
            mode = "osu"
        else:
            mode = constants.mode_aliases_v2[osu_user["default_mode"]]
    
    get_user_response = await osu_api_wrapper.get_user_v2_async(interaction.command.koduck.aiohttp_session, user_id=user, mode=mode)
    if not get_user_response:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_get_user_no_result)
    else:
        return await interaction.command.koduck.send_message(interaction, embed=embed_formatters.format_user_embed_v2(get_user_response, mode))

async def slash_get_profile(interaction, user:str=None):
    await interaction.response.defer(thinking=True)
    osu_user = yadon.ReadRowFromTable(settings.osu_users_table, interaction.user.id, named_columns=True)
    if not user:
        if osu_user is None or osu_user["osu_id"] == "":
            return await interaction.command.koduck.send_message(interaction, content=settings.message_osu_not_linked)
        else:
            user = osu_user["osu_id"]
    
    get_user_response = await osu_api_wrapper.get_user_v2_async(interaction.command.koduck.aiohttp_session, user)
    
    if not get_user_response:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_get_user_no_result)
    else:
        return await interaction.command.koduck.send_message(interaction, embed=embed_formatters.format_profile_embed(get_user_response))

async def slash_get_user_recent(interaction, user:str=None, mode:constants.GameMode=None, exclude_fails:bool=False, result_number:int=0, use_calc:constants.Calculator=None):
    await interaction.response.defer(thinking=True)
    user_id = None
    osu_user = yadon.ReadRowFromTable(settings.osu_users_table, interaction.user.id, named_columns=True)
    if not user:
        if osu_user is None or osu_user["osu_id"] == "":
            return await interaction.command.koduck.send_message(interaction, content=settings.message_osu_not_linked)
        else:
            user_id = osu_user["osu_id"]
    if not mode:
        if osu_user is None or osu_user["default_mode"] == "":
            mode = "osu"
        else:
            mode = constants.mode_aliases_v2[osu_user["default_mode"]]
    
    if not user_id:
        get_user_response = await osu_api_wrapper.get_user_v2_async(interaction.command.koduck.aiohttp_session, user_id=user, mode=mode)
        if not get_user_response:
            return await interaction.command.koduck.send_message(interaction, content=settings.message_get_user_no_result)
        user_id = get_user_response["id"]
    
    get_user_scores_response = await osu_api_wrapper.get_user_scores_v2_async(interaction.command.koduck.aiohttp_session, user_id=user_id, type="recent", include_fails=not exclude_fails, mode=mode)
    if get_user_scores_response is None or len(get_user_scores_response) == 0:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_get_user_recent_no_result.format(mode))
    else:
        if result_number > 0:
            try:
                score_data = get_user_scores_response[result_number-1]
            except IndexError:
                return await interaction.command.koduck.send_message(interaction, content=settings.message_result_number_out_of_range.format(len(get_user_scores_response)))
        else:
            score_data = get_user_scores_response[0]
        
        embed = embed_formatters.format_single_score_embed_v2(score_data, score_data["user"], score_data["beatmap"], use_calc=use_calc)
        sent_message = await interaction.command.koduck.send_message(interaction, embed=embed)
        utils.channel_id_to_active_beatmap_id[interaction.channel_id] = score_data["beatmap"]["id"]
        return sent_message

async def slash_get_scores(interaction, beatmap_id:int, user:str=None, mode:constants.GameMode=None, mods:str=None, sort_by:constants.SortMethod=None, reverse:bool=False, result_number:int=0, use_calc:constants.Calculator=None):
    await interaction.response.defer(thinking=True)
    
    if not user:
        osu_user = yadon.ReadRowFromTable(settings.osu_users_table, interaction.user.id, named_columns=True)
        if osu_user is None or osu_user["osu_id"] == "":
            return await interaction.command.koduck.send_message(interaction, content=settings.message_osu_not_linked)
        else:
            user = osu_user["osu_id"]
    
    get_user_response = await osu_api_wrapper.get_user_v2_async(interaction.command.koduck.aiohttp_session, user_id=user, mode=mode)
    if not get_user_response:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_get_user_no_result)
    user_id = get_user_response["id"]
    
    get_beatmap_response = await osu_api_wrapper.get_beatmap_v2_async(interaction.command.koduck.aiohttp_session, beatmap_id)
    if not get_beatmap_response:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_get_beatmaps_no_result)
    beatmap_id = get_beatmap_response["id"]
    
    if not mode:
        mode = get_beatmap_response["mode"]
    
    #TODO: osu api v2 seems to not work properly when providing mods, so for now I will filter it manually
    get_beatmap_scores_response = await osu_api_wrapper.get_beatmap_scores_v2_async(interaction.command.koduck.aiohttp_session, beatmap_id, user_id, mode)
    if get_beatmap_scores_response is None or len(get_beatmap_scores_response) == 0:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_get_scores_no_result)
    
    filter_results = get_beatmap_scores_response["scores"]
    if mods:
        query_mods_list = utils.get_mods_from_string(mods.upper())
        filter_results = [score_data for score_data in get_beatmap_scores_response["scores"] if set(utils.convert_v2_mods_to_array(score_data["mods"], ignore_cl=True)) == set(query_mods_list)]
    
    #sort scores
    if sort_by == "Combo":
        filter_results = sorted(filter_results, key=lambda x: int(x["max_combo"]), reverse=(not reverse))
    elif sort_by == "Accuracy":
        filter_results = sorted(filter_results, key=lambda x: utils.calculate_accuracy_v2(x), reverse=(not reverse))
    elif sort_by == "Date":
        filter_results = sorted(filter_results, key=lambda x: datetime.datetime.strptime(x["ended_at"], settings.timestamp_format_v2), reverse=(not reverse))
    
    if len(filter_results) == 0:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_get_scores_no_result)
    elif result_number > 0:
            try:
                score_data = filter_results[result_number-1]
            except IndexError:
                return await interaction.command.koduck.send_message(interaction, content=settings.message_result_number_out_of_range.format(len(filter_results)))
            
            score_data["beatmap_id"] = beatmap_id
            embed = embed_formatters.format_single_score_embed_v2(score_data, get_user_response, get_beatmap_response, use_calc=use_calc)
            sent_message = await interaction.command.koduck.send_message(interaction, embed=embed)
    elif len(filter_results) == 1:
        score_data = filter_results[0]
        score_data["beatmap_id"] = beatmap_id
        embed = embed_formatters.format_single_score_embed_v2(score_data, get_user_response, get_beatmap_response, use_calc=use_calc)
        sent_message = await interaction.command.koduck.send_message(interaction, embed=embed)
    else:
        user_ids = []
        beatmap_ids = []
        for score_data in filter_results:
            score_data["beatmap_id"] = beatmap_id
            user_ids.append(score_data["user_id"])
            beatmap_ids.append(score_data["beatmap_id"])
        user_ids = utils.remove_duplicates(user_ids)
        beatmap_ids = utils.remove_duplicates(beatmap_ids)
        
        user_data = {}
        beatmap_data = {}
        beatmap_attributes_data = {}
        user_data[user_id] = get_user_response
        beatmap_data[beatmap_id] = get_beatmap_response
        for user_id in user_ids:
            if user_id not in user_data:
                user_data[user_id] = await osu_api_wrapper.get_user_v2_async(interaction.command.koduck.aiohttp_session, user_id, mode)
        for beatmap_id in beatmap_ids:
            if beatmap_id not in beatmap_data:
                beatmap_data[beatmap_id] = await osu_api_wrapper.get_beatmap_v2_async(interaction.command.koduck.aiohttp_session, beatmap_id)
            beatmap_attributes_data[beatmap_id] = (await osu_api_wrapper.get_beatmap_attributes_v2_async(interaction.command.koduck.aiohttp_session, beatmap_id, mode))["attributes"]
        
        sent_message = await interaction.command.koduck.send_message(interaction, embed=embed_formatters.format_multiple_scores_embed_v2(filter_results, user_data, beatmap_data, beatmap_attributes_data, desc="Scores", sort_by=sort_by, use_calc=use_calc))
    utils.channel_id_to_active_beatmap_id[interaction.channel_id] = beatmap_id
    return sent_message

async def slash_compare(interaction, user:str=None, mode:constants.GameMode=None, mods:str=None, use_calc:constants.Calculator=None):
    #use last beatmap linked in chat by the bot
    try:
        beatmap_id = utils.channel_id_to_active_beatmap_id[interaction.channel_id]
    except KeyError:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_no_active_beatmap)
    return await slash_get_scores(interaction, beatmap_id, user, mode, mods, use_calc)

async def slash_get_user_best(interaction, user:str=None, mode:constants.GameMode=None, sort_by:constants.SortMethod=None, reverse:bool=False, result_number:int=0, use_calc:constants.Calculator=None):
    await interaction.response.defer(thinking=True)
    
    osu_user = yadon.ReadRowFromTable(settings.osu_users_table, interaction.user.id, named_columns=True)
    if not user:
        if osu_user is None or osu_user["osu_id"] == "":
            return await interaction.command.koduck.send_message(interaction, content=settings.message_osu_not_linked)
        else:
            user = osu_user["osu_id"]
    if not mode:
        if osu_user is None or osu_user["default_mode"] == "":
            mode = "osu"
        else:
            mode = constants.mode_aliases_v2[osu_user["default_mode"]]
    
    get_user_response = await osu_api_wrapper.get_user_v2_async(interaction.command.koduck.aiohttp_session, user_id=user, mode=mode)
    if not get_user_response:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_get_user_no_result)
    user_id = get_user_response["id"]
    
    get_user_scores_response = await osu_api_wrapper.get_user_scores_v2_async(interaction.command.koduck.aiohttp_session, user_id=user_id, type="best", mode=mode)
    scores_with_index = [{**item, "index": i+1} for i, item in enumerate(get_user_scores_response)]
    
    #sort scores
    if sort_by == "Combo":
        scores_with_index = sorted(scores_with_index, key=lambda x: int(x["max_combo"]), reverse=(not reverse))
    elif sort_by == "Accuracy":
        scores_with_index = sorted(scores_with_index, key=lambda x: utils.calculate_accuracy_v2(x), reverse=reverse)
    elif sort_by == "Date":
        scores_with_index = sorted(scores_with_index, key=lambda x: datetime.datetime.strptime(x["ended_at"], settings.timestamp_format_v2), reverse=(not reverse))
    
    if scores_with_index is None or len(scores_with_index) == 0:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_get_user_recent_no_result.format(mode))
    else:
        if result_number > 0:
            try:
                score_data = scores_with_index[result_number-1]
            except IndexError:
                return await interaction.command.koduck.send_message(interaction, content=settings.message_result_number_out_of_range.format(len(scores_with_index)))
            
            embed = embed_formatters.format_single_score_embed_v2(score_data, score_data["user"], score_data["beatmap"], use_calc=use_calc)
            sent_message = await interaction.command.koduck.send_message(interaction, embed=embed)
            utils.channel_id_to_active_beatmap_id[interaction.channel_id] = score_data["beatmap"]["id"]
            return sent_message
        else:
            scores = scores_with_index[0:settings.default_num_scores]
            user_data = {}
            beatmap_data = {}
            beatmap_attributes_data = {}
            user_data[user_id] = get_user_response
            
            beatmap_ids = []
            for score_data in scores:
                score_data["beatmap_id"] = score_data["beatmap"]["id"]
                beatmap_ids.append(score_data["beatmap_id"])
            beatmap_ids = utils.remove_duplicates(beatmap_ids)
            
            for beatmap_id in beatmap_ids:
                beatmap_data[beatmap_id] = await osu_api_wrapper.get_beatmap_v2_async(interaction.command.koduck.aiohttp_session, beatmap_id)
                beatmap_attributes_data[beatmap_id] = (await osu_api_wrapper.get_beatmap_attributes_v2_async(interaction.command.koduck.aiohttp_session, beatmap_id, mode))["attributes"]
            
            return await interaction.command.koduck.send_message(interaction, embed=embed_formatters.format_multiple_scores_embed_v2(scores, user_data, beatmap_data, beatmap_attributes_data, desc="Top Scores", sort_by=sort_by, use_calc=use_calc))

async def slash_get_beatmap(interaction, beatmap_id:int=None):
    await interaction.response.defer(thinking=True)

    if not beatmap_id:
        try:
            beatmap_id = utils.channel_id_to_active_beatmap_id[interaction.channel_id]
        except KeyError:
            return await interaction.command.koduck.send_message(interaction, content=settings.message_no_active_beatmap)
    
    beatmap_data = await osu_api_wrapper.get_beatmap_v2_async(interaction.command.koduck.aiohttp_session, beatmap_id)
    if not beatmap_data:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_get_beatmaps_no_result)
    
    return await interaction.command.koduck.send_message(interaction, embed=embed_formatters.format_single_beatmap_embed_v2(beatmap_data))

async def slash_calculate_pp(interaction, beatmap_id:int=None, mode:constants.GameMode=None, mods:str=None, count_300:int=None, count_200:int=None, count_100:int=None, count_50:int=None, count_miss:int=None, combo:int=None, acc:float=None, score:int=None, use_calc:constants.Calculator=None):
    await interaction.response.defer(thinking=True)
    
    if not beatmap_id:
        try:
            beatmap_id = utils.channel_id_to_active_beatmap_id[interaction.channel_id]
        except KeyError:
            return await interaction.command.koduck.send_message(interaction, content=settings.message_no_active_beatmap)
    query_mods = utils.get_mods_from_string(mods) if mods else []
    
    beatmap_data = await osu_api_wrapper.get_beatmap_v2_async(interaction.command.koduck.aiohttp_session, beatmap_id)
    if not beatmap_data:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_get_beatmaps_no_result)
    
    if not mode:
        mode = beatmap_data["mode"]
    
    beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap_data["id"], beatmap_data["last_updated"])
    native_mode = utils.get_map_mode(beatmap_file_name)
    #Force native mode if not standard (because they're incompatible with each other)
    if native_mode != "0":
        mode = constants.modes[native_mode]
    
    #current calc bugged - it automatically splits 300 counts to perfects and greats which affects the pp calculation so I need to manually set greats to 0
    if use_calc is None and mode == "mania" and "300" not in kwargs:
        count_300 = 0
        result_fc = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=mode, mods=query_mods, n300=0, use_calc=use_calc)
    else:
        result_fc = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=mode, mods=query_mods, use_calc=use_calc)
    result = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=mode, mods=query_mods, acc=acc, combo=combo, n300=count_300, n200=count_200, n100=count_100, n50=count_50, n0=count_miss, score=score, use_calc=use_calc)
    
    embed = embed_formatters.format_pp_simulation(beatmap_data, mode, query_mods, result, result_fc, use_calc)
    sent_message = await interaction.command.koduck.send_message(interaction, embed=embed)
    utils.channel_id_to_active_beatmap_id[interaction.channel_id] = beatmap_data["id"]
    return sent_message

async def slash_graph(interaction, beatmap_id:int=None, mods:str=None, use_calc:constants.Calculator=None):
    await interaction.response.defer(thinking=True)
    
    if not beatmap_id:
        try:
            beatmap_id = utils.channel_id_to_active_beatmap_id[interaction.channel_id]
        except KeyError:
            return await interaction.command.koduck.send_message(interaction, content=settings.message_no_active_beatmap)
    
    beatmap_data = await osu_api_wrapper.get_beatmap_v2_async(interaction.command.koduck.aiohttp_session, beatmap_id)
    if not beatmap_data:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_get_beatmaps_no_result)
    
    beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap_data["id"], beatmap_data["last_updated"])
    times, difficulty_attributes = perf_calc_wrapper.calculate_sr(beatmap_file_name, mode=beatmap_data["mode"], mods=utils.get_mods_from_string(mods, ncpf=True) if mods else [], use_calc=use_calc)
    output_graph_file = "{}/{}_graph.png".format(settings.beatmaps_graphs_folder, beatmap_data["id"])
    title = "{} - {} ({}) [{}]".format(beatmap_data["beatmapset"]["artist"], beatmap_data["beatmapset"]["title"], beatmap_data["beatmapset"]["creator"], beatmap_data["version"])
    
    if use_calc in constants.legacy_calcs:
        if beatmap_data["mode"] == "osu":
            difficulty_attributes = [difficulty_attributes[0], difficulty_attributes[2], difficulty_attributes[3], difficulty_attributes[4], difficulty_attributes[5]]
            difficulty_labels = ["Star Rating", "Aim", "Speed", "Flashlight", "Slider"]
        # ignore "Hit Window" and "Approach Rate" attributes since they always stay the same, so it's pointless to graph it
        elif beatmap_data["mode"] == "taiko":
            if use_calc == "2021-11-09":
                difficulty_attributes = [difficulty_attributes[0], difficulty_attributes[2], difficulty_attributes[3], difficulty_attributes[4]]
                difficulty_labels = ["Star Rating", "Stamina", "Rhythm", "Colour"]
            elif use_calc == "taiko-loopy":
                # this is just max combo / 10, otherwise there's no real difficulty attributes yet since this is still using old osu-tools
                difficulty_attributes = [[x/10 for x in difficulty_attributes[1]]]
                difficulty_labels = ["Strain"]
            else:
                difficulty_attributes = [difficulty_attributes[0], difficulty_attributes[2], difficulty_attributes[3], difficulty_attributes[4], difficulty_attributes[5]]
                difficulty_labels = ["Star Rating", "Stamina", "Rhythm", "Colour", "Peaks"]
        elif beatmap_data["mode"] in ["fruits", "mania"]:
            difficulty_attributes = [difficulty_attributes[0]]
            difficulty_labels = ["Star Rating"]
        else:
            raise Exception("what")
    else:
        '''
        if beatmap_data["mode"] == "osu":
            difficulty_attributes = [[x["star_rating"] for x in difficulty_attributes],
                                    [x["aim_difficulty"] for x in difficulty_attributes],
                                    [x["speed_difficulty"] for x in difficulty_attributes],
                                    [(x["flashlight_difficulty"] if "flashlight_difficulty" in x else 0) for x in difficulty_attributes]]
            difficulty_labels = ["Star Rating", "Aim", "Speed", "Flashlight"]
        elif beatmap_data["mode"] == "taiko":
            difficulty_attributes = [[x["star_rating"] for x in difficulty_attributes],
                                    [x["stamina_difficulty"] for x in difficulty_attributes],
                                    [x["rhythm_difficulty"] for x in difficulty_attributes],
                                    [x["colour_difficulty"] for x in difficulty_attributes],
                                    [x["peak_difficulty"] for x in difficulty_attributes]]
            difficulty_labels = ["Star Rating", "Stamina", "Rhythm", "Colour", "Peak"]
        elif beatmap_data["mode"] in ["fruits", "mania"]:
            difficulty_attributes = [[x["star_rating"] for x in difficulty_attributes]]
            difficulty_labels = ["Star Rating"]
        else:
            raise Exception("what")
        '''
        difficulty_attributes = [[x["star_rating"] for x in difficulty_attributes]]
        difficulty_labels = ["Star Rating"]

    beatmap_graph_generator.generate_graph(times, difficulty_attributes, difficulty_labels, output_graph_file, title=title)
    
    return await interaction.command.koduck.send_message(interaction, file=discord.File(open(output_graph_file, 'rb')))

async def slash_analyze_replay(interaction, score_id:int=None, replay:discord.Attachment=None, beatmap:discord.Attachment=None, beatmap_id:int=None, user:str=None, mode:constants.GameMode=None, mods:str=None, hide_100s:bool=False, hide_50s:bool=False, hide_misses:bool=False, hide_taiko_finisher_misses:bool=False, use_calc:constants.Calculator=None):
    await interaction.response.defer(thinking=True)
    
    md5_match = True
    beatmap_data = None
    beatmap_details = None
    if not replay:
        username = ""
        if score_id:
            get_score_response = await osu_api_wrapper.get_score_v2_async(interaction.command.koduck.aiohttp_session, score_id=score_id)
            v1_score_id = get_score_response["id"]
            mode = get_score_response["mode"]
            user_id = get_score_response["user"]["id"]
            username = get_score_response["user"]["username"]
            beatmap_id = get_score_response["beatmap"]["id"]
        else:
            #return await interaction.command.koduck.send_message(interaction, content="fetching replays from osu api v2 is not implemented yet, use `/analyzereplay` text command instead")
            osu_user = yadon.ReadRowFromTable(settings.osu_users_table, interaction.user.id, named_columns=True)
            user_id = None
            if not user:
                if osu_user is None or osu_user["osu_id"] == "":
                    return await interaction.command.koduck.send_message(interaction, content=settings.message_osu_not_linked)
                else:
                    user = osu_user["osu_id"]
                    user_id = osu_user["osu_id"]
                    get_user_response = await osu_api_wrapper.get_user_v2_async(interaction.command.koduck.aiohttp_session, user_id=user, mode=mode)
                    if get_user_response:
                        username = get_user_response["username"]
            if not mode and osu_user and osu_user["default_mode"]:
                mode = constants.mode_aliases_v2[osu_user["default_mode"]]
            
            if not user_id:
                get_user_response = await osu_api_wrapper.get_user_v2_async(interaction.command.koduck.aiohttp_session, user_id=user, mode=mode)
                if not get_user_response:
                    return await interaction.command.koduck.send_message(interaction, content=settings.message_get_user_no_result)
                user_id = get_user_response["id"]
                username = get_user_response["username"]
            
            if not beatmap_id:
                return await interaction.command.koduck.send_message(interaction, content=settings.message_get_replay_no_param)
        
        await interaction.command.koduck.send_message(interaction, content="fetching beatmap...")
        progress_message = await interaction.original_response()
        
        beatmap_data = await osu_api_wrapper.get_beatmap_v2_async(interaction.command.koduck.aiohttp_session, beatmap_id)
        if not beatmap_data:
            return await progress_message.edit(content=settings.message_get_beatmaps_no_result)
        beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap_data["id"], beatmap_data["last_updated"])
        
        if not mode:
            mode = beatmap_data["mode"]
        
        #Parse mods
        if mods:
            mods_int = utils.mods_to_int(utils.get_mods_from_string(mods, ncpf=True))
        
        await progress_message.edit(content="fetching replay...")
        #TODO: osu api v2 seems to not work properly when providing mods, so for now I will filter it manually
        get_beatmap_scores_response = await osu_api_wrapper.get_beatmap_scores_v2_async(interaction.command.koduck.aiohttp_session, beatmap_id, user_id, mode)
        if get_beatmap_scores_response is None or len(get_beatmap_scores_response) == 0:
            return await progress_message.edit(content=settings.message_get_scores_no_result)
        
        filter_results = get_beatmap_scores_response["scores"]
        
        #filter out lazer scores
        filter_results = [score_data for score_data in filter_results if not utils.is_lazer_score(score_data)]
        #filter mods
        if mods:
            query_mods_list = utils.get_mods_from_string(mods.upper())
            filter_results = [score_data for score_data in filter_results if set(utils.convert_v2_mods_to_array(score_data["mods"], ignore_cl=True)) == set(query_mods_list)]
        
        if len(filter_results) == 0:
            return await progress_message.edit(content=settings.message_get_scores_no_result)
        if len(filter_results) > 1:
            #scores_mods = ["".join(utils.convert_v2_mods_to_array(score_data["mods"])) for score_data in filter_results]
            #return await progress_message.edit(content=settings.message_get_scores_multiple_results.format(str(scores_mods)))
            class ScoreButton(discord.ui.Button):
                index = None
                async def callback(self, interaction):
                    self.view.selected_index = self.index
                    self.view.stop()
            
            the_view = discord.ui.View(timeout=60)
            the_view.selected_index = None
            for index in range(len(filter_results)):
                score_data = filter_results[index]
                label = "".join(utils.convert_v2_mods_to_array(score_data["mods"], ignore_cl=True))
                if not label:
                    label = "NM"
                timestamp = datetime.datetime.strptime(score_data["ended_at"], settings.timestamp_format_v2)
                label += " ({:0.2f}%) [{}]".format(score_data["accuracy"] * 100, timestamp.strftime("%Y-%m-%d"))
                the_button = ScoreButton(style=discord.ButtonStyle.primary, label=label)
                the_button.index = index
                the_view.add_item(the_button)
            await progress_message.edit(content=settings.message_get_scores_choose, view=the_view)
            await the_view.wait()
            if the_view.selected_index is None:
                return await progress_message.edit(content=settings.message_get_scores_choose_none, view=None)
            else:
                await progress_message.edit(view=None)
                score_data = filter_results[the_view.selected_index]
        else:
            score_data = filter_results[0]
        enabled_mods = utils.convert_v2_mods_to_array(score_data["mods"])
        
        if not score_data["replay"]:
            return await progress_message.edit(content=settings.message_get_replay_not_available)
        if utils.is_lazer_score(score_data):
            return await progress_message.edit(content=settings.message_get_replay_lazer_score_error)
        
        #temporarily use v1 api
        replaysearch = osu_api_wrapper.get_replay(**{"s": score_data["legacy_score_id"], "m": constants.mode_aliases[mode]})
        if "error" in replaysearch:
            return await progress_message.edit(content=settings.message_get_replay_error.format(replaysearch["error"]))
        
        replay_lzma = replaysearch["content"]
        replay_details = OsuReplayDetails()
        replay_details.replay_data_raw = base64.b64decode(replay_lzma)
        replay_details.game_mode = int(constants.mode_aliases[mode])
        replay_details.mods_raw = utils.mods_to_int(enabled_mods)
        
        #Doesn't work right now
        '''
        replay_data_raw = await osu_api_wrapper.get_replay_v2_async(interaction.command.koduck.aiohttp_session, score_data["id"])
        replay_file_name = "{}/{}.osr".format(settings.replays_folder, score_data["id"])
        replay_parser = OsuReplayParser()
        replay_file = open(replay_file_name, "wb")
        replay_file.write(replay_data_raw)
        replay_file.close()
        replay_file = open(replay_file_name, "rb")
        replay_details = replay_parser.parse_from_file(replay_file)
        return await progress_message.edit(content="test")
        '''
        
        #Get SR adjusted by mods
        mods_raw = utils.mods_to_int(enabled_mods)
        beatmap_attributes = (await osu_api_wrapper.get_beatmap_attributes_v2_async(interaction.command.koduck.aiohttp_session, beatmap_id, mode, mods=utils.ignore_irrelevant_mods(mods_raw)))["attributes"]
    else:
        await interaction.command.koduck.send_message(interaction, content="reading replay...")
        progress_message = await interaction.original_response()
        replay_file_name = replay.filename
        await replay.save("{}/{}".format(settings.replays_folder, replay_file_name))
        
        replay_parser = OsuReplayParser()
        replay_file = open("{}/{}".format(settings.replays_folder, replay_file_name), "rb")
        replay_details = replay_parser.parse_from_file(replay_file)
        enabled_mods = utils.get_mods_from_int(replay_details.mods_raw)
        
        if not beatmap:
            await progress_message.edit(content="fetching beatmap...")
            
            beatmap_data = await osu_api_wrapper.lookup_beatmap_v2_async(interaction.command.koduck.aiohttp_session, checksum=replay_details.map_md5hash)
            if not beatmap_data:
                return await progress_message.edit(content=settings.message_get_beatmaps_no_result)
            beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap_data["id"], beatmap_data["last_updated"])
            
            #Get SR adjusted by mods
            beatmap_attributes = (await osu_api_wrapper.get_beatmap_attributes_v2_async(interaction.command.koduck.aiohttp_session, beatmap_data["id"], mode, mods=utils.ignore_irrelevant_mods(replay_details.mods_raw)))["attributes"]
        else:
            await progress_message.edit(content="reading beatmap...")
            beatmap_file_name = "{}/{}".format(settings.beatmaps_download_folder, beatmap.filename)
            await beatmap.save(beatmap_file_name)

            map_parser = OsuBeatmapParser()
            beatmap_details = map_parser.parse_from_filename(beatmap_file_name)

            beatmap_contents = open(beatmap_file_name, "rb").read()
            beatmap_md5 = hashlib.md5(beatmap_contents).hexdigest()
            if beatmap_md5 != replay_details.map_md5hash:
                md5_match = False
    
    if replay_details.game_mode in [2, 3]:
        return await progress_message.edit(content=settings.message_analyze_replay_unsupported_mode)
    
    await progress_message.edit(content="analyzing replay...")
    replay_analyzer = OsuReplayAnalyzer(map_file_name=beatmap_file_name, replay_details=replay_details, force_hr="HR" in enabled_mods, force_ez="EZ" in enabled_mods)
    DT_enabled = "DT" in enabled_mods or "NC" in enabled_mods
    converted_ur = replay_analyzer.unstable_rate / 1.5 if DT_enabled else replay_analyzer.unstable_rate
    output_string = "Accuracy:\nError: {:0.2f}ms - {:0.2f}ms\nUnstable Rate: {:0.2f}{}".format(replay_analyzer.hit_error_negative, replay_analyzer.hit_error_positive, replay_analyzer.unstable_rate, " ({:0.2f})".format(converted_ur) if DT_enabled else "")
    #note = "Notes: Currently ignores sliders and\nspinners. V1/V2/V3 scores are WIP."
    note = "Notes:\nCurrently ignores sliders and\nspinners."
    if not md5_match:
        note += "\nThe beatmap's md5 hash doesn't\nmatch the replay, so this result\nmay be inaccurate." if not md5_match else None
    convert_string = ""
    
    oranges = []
    greens = []
    blues = []
    misses = []
    finisher_misses = []
    finishers_hit = 0
    finishers_total = 0
    for k,v in replay_analyzer.hit_object_results.items():
        if v[0] is None or v[0] == 0:
            misses.append(k.offset / 1000)
        elif v[0] == 50:
            blues.append(k.offset / 1000)
        elif (replay_details.game_mode == 0 and v[0] == 100) or (replay_details.game_mode == 1 and v[0] == 150):
            greens.append(k.offset / 1000)
        elif v[0] == 300:
            oranges.append(k.offset / 1000)
        if v[3] is not None:
            finishers_total += 1
        if v[3] == True:
            finishers_hit += 1
        if v[3] == False:
            finisher_misses.append(k.offset / 1000)
    
    if replay_details.game_mode == 0:
        output_string += "\nMax Combo: {}".format(replay_analyzer.player_max_combo)
    if replay_details.game_mode == 1:
        #Loopy's stability index for taiko
        result_fc = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=constants.modes[str(replay_details.game_mode)], mods=[x for x in enabled_mods if x != "V2"], use_calc=use_calc)
        hit_count = len(greens) + len(oranges)
        if use_calc in constants.legacy_calcs:
            a = ((float(result_fc["rhythm difficulty"]) - 0.7) ** 3) / 3
            s = ((float(result_fc["stamina difficulty"]) - 2.2) ** 3) / 30
        elif use_calc == "2024-10-30":
            a = ((float(result_fc["difficulty_attributes"]["rhythm_difficulty"]) - 0.7) ** 3) / 3
            s = ((float(result_fc["difficulty_attributes"]["stamina_difficulty"]) - 2.2) ** 3) / 30
        else:
            a = 0
            s = 0
        c = math.log(hit_count / 1000, 1.5) / 5
        u = math.log(converted_ur / 150, 0.925)
        stability_index = (5 + a + s + c) * u
        #stability_index = (5 + (math.log(hit_count / 1000, 2) / 3)) * (math.log(converted_ur / 125, 0.93) + (22 * (math.pow(1.1, float(beatmap_attributes["star_rating"]) - 5) - 1)))
        extra = ""
        '''
        if stability_index > 100:
            extra = " " + settings.si_extra_100
        elif stability_index > 90:
            extra = " " + settings.si_extra_90
        elif stability_index > 80:
            extra = " " + settings.si_extra_80
        elif stability_index > 70:
            extra = " " + settings.si_extra_70
        elif stability_index > 60:
            extra = " " + settings.si_extra_60
        elif stability_index > 50:
            extra = " " + settings.si_extra_50
        if stability_index > converted_ur:
            extra += " " + settings.si_extra_elite
        '''
        output_string += "\nStability Index v4: {:0.2f}{}".format(stability_index, extra)
        
        #output_string += "\nV1 Score: {:0.0f}".format(replay_analyzer.score_v1)
        #output_string += "\nV2 Score: {:0.0f}".format((replay_analyzer.combo_score_v2 + replay_analyzer.accuracy_score) * replay_analyzer.mod_multiplier)
        #output_string += "\nV3 Score: {:0.0f}".format((replay_analyzer.combo_score_v3 + replay_analyzer.accuracy_score + replay_analyzer.bonus_score) * replay_analyzer.mod_multiplier)
        output_string += "\nMax Combo: {}".format(replay_analyzer.player_max_combo)
        
        if (beatmap_data and beatmap_data["mode"] == "osu") or (beatmap_details and beatmap_details.game_mode == 0):
            convert_string = " <Convert>"
            #note = "Note: converts are WIP so this is most likely incorrect"
    
    #accuracy data
    object_count = len(oranges) + len(greens) + len(blues) + len(misses)
    if replay_details.game_mode == 0:
        output_string += "\nAccuracy: {:0.2f}%".format(((len(oranges) * 300) + (len(greens) * 100) + (len(blues) * 50)) / (object_count * 3))
        output_string += "\n300s: {}\n100s: {}\n50s: {}\nMisses: {}".format(len(oranges), len(greens), len(blues), len(misses))
    if replay_details.game_mode == 1:
        output_string += "\nAccuracy: {:0.2f}%".format(((len(oranges) * 300) + (len(greens) * 150)) / (object_count * 3))
        output_string += "\n300s: {}\n150s: {}\nMisses: {}".format(len(oranges), len(greens), len(misses))
        output_string += "\nFinishers hit: {}/{}".format(finishers_hit, finishers_total)
    
    player_name = replay_details.player_name if replay else username
    replay_timestamp = datetime.datetime(1, 1, 1) + datetime.timedelta(microseconds=replay_details.timestamp // 10) if replay else datetime.datetime.strptime(score_data["ended_at"], settings.timestamp_format_v2).replace(tzinfo=datetime.timezone.utc)
    replay_date = replay_timestamp.strftime(settings.timestamp_format_v2) if replay else score_data["ended_at"]
    
    await progress_message.edit(content="generating graph...")
    times, difficulty_attributes = perf_calc_wrapper.calculate_sr(beatmap_file_name, mode=constants.modes[str(replay_details.game_mode)], mods=[x for x in enabled_mods if x != "V2"], use_calc=use_calc)
    if beatmap:
        output_graph_file = "{}/{}_graph_{}.png".format(settings.beatmaps_graphs_folder, beatmap_md5, int(replay_timestamp.timestamp()))
    else:
        output_graph_file = "{}/{}_graph_{}.png".format(settings.beatmaps_graphs_folder, beatmap_data["id"], int(replay_timestamp.timestamp()))
    if len(enabled_mods) == 0:
        enabled_mods.append("NM")
    
    mods2 = utils.get_mods_from_int(replay_details.mods_raw)
    pp_data_fc = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=constants.modes[str(replay_details.game_mode)], mods=mods2, use_calc=use_calc)
    pp_data = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=constants.modes[str(replay_details.game_mode)], mods=mods2, n100=len(greens), n0=len(misses), use_calc=use_calc)

    beatmap_artist = beatmap_data["beatmapset"]["artist"] if beatmap_data else beatmap_details.artist
    beatmap_title = beatmap_data["beatmapset"]["title"] if beatmap_data else beatmap_details.title
    beatmap_creator = beatmap_data["beatmapset"]["creator"] if beatmap_data else beatmap_details.mapper_name
    beatmap_version = beatmap_data["version"] if beatmap_data else beatmap_details.difficulty_name
    beatmap_sr = float(beatmap_attributes["star_rating"]) if beatmap_data else pp_data_fc["difficulty_attributes"]["star_rating"]
    title = "{} - {} ({}) [{}] ({:0.2f}☆){}\nPlayed by {} on {} with {}".format(beatmap_artist, beatmap_title, beatmap_creator, beatmap_version, beatmap_sr, convert_string, player_name, replay_date, "".join(enabled_mods))
    
    if replay_details.game_mode == 0:
        if use_calc in constants.legacy_calcs:
            #Flashlight difficulty attribute has inflated values for some reason
            #difficulty_attributes = [difficulty_attributes[0], difficulty_attributes[2], difficulty_attributes[3], [x/10 for x in difficulty_attributes[4]], difficulty_attributes[5]]
            #difficulty_labels = ["Star Rating", "Aim", "Speed", "Flashlight", "Slider"]
            difficulty_attributes = [difficulty_attributes[0]]
            difficulty_labels = ["Star Rating"]
            beatmap_graph_generator.generate_graph(times, difficulty_attributes, difficulty_labels, output_graph_file, title=title, greens=greens, blues=blues, misses=misses, footer_text=output_string, note=note)
        else:
            difficulty_attributes = [[x["star_rating"] for x in difficulty_attributes]]
            difficulty_labels = ["Star Rating"]
            beatmap_graph_generator.generate_graph(times, difficulty_attributes, difficulty_labels, output_graph_file, title=title, greens=greens, blues=blues, misses=misses, graph_title="Replay Graph", footer_text=output_string)
    # ignore "Hit Window" and "Approach Rate" attributes since they always stay the same, so it's pointless to graph it
    elif replay_details.game_mode == 1:
        if use_calc in constants.legacy_calcs:
            output_string += "\nPP: {:0.2f} / {:0.2f}".format(float(pp_data["pp"]), float(pp_data_fc["pp"]))
            if use_calc == "2021-11-09":
                #difficulty_attributes = [difficulty_attributes[0], difficulty_attributes[2], difficulty_attributes[3], difficulty_attributes[4]]
                #difficulty_labels = ["Star Rating", "Stamina", "Rhythm", "Colour"]
                difficulty_attributes = [difficulty_attributes[0]]
                difficulty_labels = ["Star Rating"]
            elif use_calc == "taiko-loopy":
                difficulty_attributes = [[x/10 for x in difficulty_attributes[1]]]
                difficulty_labels = ["Strain"]
            else:
                #difficulty_attributes = [difficulty_attributes[0], difficulty_attributes[2], difficulty_attributes[3], difficulty_attributes[4], difficulty_attributes[5]]
                #difficulty_labels = ["Star Rating", "Stamina", "Rhythm", "Colour", "Peaks"]
                difficulty_attributes = [difficulty_attributes[0]]
                difficulty_labels = ["Star Rating"]
        else:
            output_string += "\nPP: {:0.2f} / {:0.2f}".format(float(pp_data["performance_attributes"]["pp"]), float(pp_data_fc["performance_attributes"]["pp"]))
            difficulty_attributes = [[x["star_rating"] for x in difficulty_attributes]]
            difficulty_labels = ["Star Rating"]
        
        if hide_100s:
            greens = []
        if hide_50s:
            blues = []
        if hide_misses:
            misses = []
        if hide_taiko_finisher_misses:
            finisher_misses = []
        beatmap_graph_generator.generate_graph(times, difficulty_attributes, difficulty_labels, output_graph_file, title=title, greens=greens, blues=blues, misses=misses, finisher_misses=finisher_misses, footer_text=output_string, note=note)
    else:
        raise Exception("what")
    
    #return await progress_message.edit(content=output_string, attachments=[discord.File(open(output_graph_file, 'rb'))])
    return await progress_message.edit(content=None, attachments=[discord.File(open(output_graph_file, 'rb'))])

async def slash_convert_to_taiko(interaction, beatmap_id:int=None):
    await interaction.response.defer(thinking=True)
    await interaction.command.koduck.send_message(interaction, content="fetching beatmap...")
    progress_message = await interaction.original_response()
    
    beatmap_data = await osu_api_wrapper.get_beatmap_v2_async(interaction.command.koduck.aiohttp_session, beatmap_id)
    if not beatmap_data:
        return await progress_message.edit(content=settings.message_get_beatmaps_no_result)
    beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap_data["id"], beatmap_data["last_updated"])
    
    await progress_message.edit(content="converting beatmap...")
    beatmap_parser = OsuBeatmapParser()
    beatmap_file = open(beatmap_file_name, encoding="utf-8")
    beatmap_details = beatmap_parser.parse_from_file(beatmap_file)
    
    if beatmap_details.game_mode != 0:
        return await progress_message.edit(content="Cannot convert a non-standard map")
    beatmap_details.convert_to_taiko()
    beatmap_details.beatmap_id = 0
    beatmap_details.difficulty_name += " (Taiko Convert)"
    output_file_name = "{}/{}_taiko_convert.osu".format(settings.beatmaps_download_folder, beatmap_data["id"])
    beatmap_details.export(output_file_name)
    
    return await progress_message.edit(content=None, attachments=[discord.File(open(output_file_name, 'rb'))])

async def track(interaction, user: str=None, mode: constants.GameMode=None, num_scores: int=100):
    await interaction.response.defer(thinking=True)
    osu_user = yadon.ReadRowFromTable(settings.osu_users_table, interaction.user.id, named_columns=True)
    if not user:
        if osu_user is None or osu_user["osu_id"] == "":
            return await interaction.command.koduck.send_message(interaction, content=settings.message_osu_not_linked)
        else:
            user = osu_user["osu_id"]
    if not mode:
        if osu_user is None or osu_user["default_mode"] == "":
            mode = "osu"
        else:
            mode = constants.mode_aliases_v2[osu_user["default_mode"]]
    
    player = await osu_api_wrapper.get_user_v2_async(interaction.command.koduck.aiohttp_session, user_id=user, mode=mode)
    if not player:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_get_user_no_result)
    
    key = "{}/{}".format(player["id"], constants.mode_aliases[mode])
    channel_id = interaction.channel_id
    try:
        the_channel = await interaction.command.koduck.client.fetch_channel(channel_id)
    except (discord.NotFound, discord.Forbidden):
        return await interaction.command.koduck.send_message(interaction, content=settings.message_track_failure_2.format(channel_id))

    channel_ids_and_settings = []
    row = yadon.ReadRowFromTable(settings.track_table, key)
    if row is not None:
        channel_ids_and_settings = row[0].split("/")
        # format is `channelId1:numScores1/channelId2:numScores2/...`
        channel_ids = [x.split(":")[0] for x in row[0].split("/")]
        if str(channel_id) in channel_ids:
            return await interaction.command.koduck.send_message(interaction, content=settings.message_track_failure.format(player["username"], mode, channel_id))
    
    top_scores = await osu_api_wrapper.get_user_scores_v2_async(interaction.command.koduck.aiohttp_session, user_id=player["id"], type="best", mode=mode)
    score_ids = [score["id"] for score in top_scores]
    channel_ids_and_settings.append("{}:{}".format(str(channel_id), num_scores))
    yadon.WriteRowToTable(settings.track_table, key, ["/".join(channel_ids_and_settings), player["statistics"]["global_rank"], player["statistics"]["pp"]] + score_ids)
    global restart_background_task
    restart_background_task = True
    return await interaction.command.koduck.send_message(interaction, content=settings.message_track_success.format(num_scores, mode, player["username"], channel_id))

async def untrack(interaction, user: str=None, mode: constants.GameMode=None):
    await interaction.response.defer(thinking=True)
    osu_user = yadon.ReadRowFromTable(settings.osu_users_table, interaction.user.id, named_columns=True)
    if not user:
        if osu_user is None or osu_user["osu_id"] == "":
            return await interaction.command.koduck.send_message(interaction, content=settings.message_osu_not_linked)
        else:
            user = osu_user["osu_id"]
    if not mode:
        if osu_user is None or osu_user["default_mode"] == "":
            mode = "osu"
        else:
            mode = constants.mode_aliases_v2[osu_user["default_mode"]]
    
    player = await osu_api_wrapper.get_user_v2_async(interaction.command.koduck.aiohttp_session, user_id=user, mode=mode)
    if not player:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_get_user_no_result)
    
    key = "{}/{}".format(player["id"], constants.mode_aliases[mode])
    channel_id = interaction.channel_id
    channel_ids = []
    
    row = yadon.ReadRowFromTable(settings.track_table, key)
    if row is None:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_untrack_failure.format(player["username"], mode, channel_id))

    channel_ids_and_settings = row[0].split("/")
    channel_ids = [x.split(":")[0] for x in row[0].split("/")]
    if str(channel_id) not in channel_ids:
        return await interaction.command.koduck.send_message(interaction, content=settings.message_untrack_failure.format(player["username"], mode, channel_id))
    channel_ids.remove(str(channel_id))
    if len(channel_ids) == 0:
        yadon.RemoveRowFromTable(settings.track_table, key)
    else:
        yadon.WriteRowToTable(settings.track_table, key, [x for x in channel_ids_and_settings if x.split(":")[0] != str(channel_id)] + row[1:])
    global restart_background_task
    restart_background_task = True
    return await interaction.command.koduck.send_message(interaction, content=settings.message_untrack_success.format(mode, player["username"], channel_id))

async def match_cost(interaction, match_id:int):
    await interaction.response.defer(thinking=True)
    
    match = await osu_api_wrapper.get_match_v2_async(interaction.command.koduck.aiohttp_session, match_id=match_id)
    
    costs = {}
    num_games = 0
    
    for event in match["events"]:
        if "game" not in event:
            continue
        num_games += 1
        avg_score = sum([x["score"] for x in event["game"]["scores"]]) / len(event["game"]["scores"])
        for score in event["game"]["scores"]:
            if score["user_id"] not in costs:
                costs[score["user_id"]] = []
            costs[score["user_id"]].append(score["score"] / avg_score)
    
    get_users_response = await osu_api_wrapper.get_users_v2_async(interaction.command.koduck.aiohttp_session, [k for k,v in costs.items()])
    users = {user["id"]:user["username"] for user in get_users_response["users"]}
    
    costs = {users[k]:2*sum(v)/(len(v)+2) for k,v in costs.items()}
    sorted_costs = dict(sorted(costs.items(), key=lambda item: item[1], reverse=True))
    
    output = ""
    max_username_length = max([len(x) for x in users.values()])
    for k,v in sorted_costs.items():
        output += "\n`{}` `{:0.2f}`".format(k.ljust(max_username_length), v)
    
    return await interaction.command.koduck.send_message(interaction, content=output)