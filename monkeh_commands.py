import datetime, base64, asyncio, math
import discord
import perf_calc_wrapper, beatmap_graph_generator, osu_api_wrapper
from osu_map_parser import OsuBeatmapParser
from osu_replay_parser import OsuReplayDetails, OsuReplayParser
from osu_replay_analyzer import OsuReplayAnalyzer
import yadon
import settings
import constants
import utils
import embed_formatters

async def update_emojis(context, *args, **kwargs):
    utils.emojis = {}
    for server in context["koduck"].client.guilds:
        if server.name.startswith("osu! Icons"):
            for emoji in server.emojis:
                utils.emojis[emoji.name.lower()] = "<:{}:{}>".format(emoji.name, emoji.id)

async def set_osu(context, *args, **kwargs):
    if len(args) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_set_osu_no_param)
    
    response = await osu_api_wrapper.get_user_v2_async(context["koduck"].aiohttp_session, args[0])
    if not response:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_user_no_result)
    else:
        user = yadon.ReadRowFromTable(settings.osu_users_table, context["message"].author.id, named_columns=True)
        if not user:
            user = {}
        user["osu_id"] = response["id"]
        user["default_mode"] = constants.mode_aliases[response["playmode"]]
        yadon.WriteRowToTable(settings.osu_users_table, context["message"].author.id, user, named_columns=True)
        return await context["koduck"].send_message(context["message"], content=settings.message_set_osu_success.format(context["message"].author.id, response["username"], response["playmode"]))

async def set_default_mode(context, *args, **kwargs):
    if len(args) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_set_mode_no_param)
    
    THEmode = args[0].lower()
    if THEmode not in constants.mode_aliases.keys():
        return await context["koduck"].send_message(context["message"], content=settings.message_set_mode_no_param)
    
    user = yadon.ReadRowFromTable(settings.osu_users_table, context["message"].author.id, named_columns=True)
    if not user:
        user = {}
    user["default_mode"] = constants.mode_aliases[THEmode]
    yadon.WriteRowToTable(settings.osu_users_table, context["message"].author.id, user, named_columns=True)
    return await context["koduck"].send_message(context["message"], content=settings.message_set_mode_success.format(context["message"].author.id, THEmode))

async def get_user(context, *args, **kwargs):
    kwargs = utils.convert_kwargs(kwargs)
    user = yadon.ReadRowFromTable(settings.osu_users_table, context["message"].author.id, named_columns=True)
    if "m" not in kwargs:
        if user is None or user["default_mode"] == "":
            kwargs["m"] = "0"
        else:
            kwargs["m"] = user["default_mode"]
    if kwargs["m"] not in constants.mode_aliases.keys():
        return await context["koduck"].send_message(context["message"], content=settings.message_set_mode_no_param)
    
    #allow first arg to be used as "u" parameter if it's not provided in kwargs
    if len(args) >= 1 and "u" not in kwargs:
        kwargs["u"] = args[0]
    
    #if "u" not in args or kwargs, use user's linked account if any
    if "u" not in kwargs:
        if user is None or user["osu_id"] == "":
            return await context["koduck"].send_message(context["message"], content=settings.message_osu_not_linked)
        else:
            kwargs["u"] = user["osu_id"]
    
    if "v2" in kwargs:
        response = await osu_api_wrapper.get_user_v2_async(context["koduck"].aiohttp_session, kwargs["u"], mode=constants.mode_aliases_v2[kwargs["m"]])
        
        if not response:
            return await context["koduck"].send_message(context["message"], content=settings.message_get_user_no_result)
        else:
            return await context["koduck"].send_message(context["message"], embed=embed_formatters.format_user_embed_v2(response, constants.modes[kwargs["m"]]))
    else:
        response = await osu_api_wrapper.get_user_async(kwargs, context["koduck"].aiohttp_session)
        
        if len(response) == 0:
            return await context["koduck"].send_message(context["message"], content=settings.message_get_user_no_result)
        else:
            return await context["koduck"].send_message(context["message"], embed=embed_formatters.format_user_embed(response[0], constants.modes[kwargs["m"]]))

async def get_user_osu(context, *args, **kwargs):
    kwargs["m"] = "0"
    return await get_user(context, *args, **kwargs)

async def get_user_taiko(context, *args, **kwargs):
    kwargs["m"] = "1"
    return await get_user(context, *args, **kwargs)

async def get_user_ctb(context, *args, **kwargs):
    kwargs["m"] = "2"
    return await get_user(context, *args, **kwargs)

async def get_user_mania(context, *args, **kwargs):
    kwargs["m"] = "3"
    return await get_user(context, *args, **kwargs)

async def get_profile(context, *args, **kwargs):
    kwargs = utils.convert_kwargs(kwargs)
    user = yadon.ReadRowFromTable(settings.osu_users_table, context["message"].author.id, named_columns=True)
    
    #allow first arg to be used as "u" parameter if it's not provided in kwargs
    if len(args) >= 1 and "u" not in kwargs:
        kwargs["u"] = args[0]
    
    #if "u" not in args or kwargs, use user's linked account if any
    if "u" not in kwargs:
        if user is None or user["osu_id"] == "":
            return await context["koduck"].send_message(context["message"], content=settings.message_osu_not_linked)
        else:
            kwargs["u"] = user["osu_id"]
    
    response = await osu_api_wrapper.get_user_v2_async(context["koduck"].aiohttp_session, kwargs["u"])
    
    if not response:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_user_no_result)
    else:
        return await context["koduck"].send_message(context["message"], embed=embed_formatters.format_profile_embed(response))

async def get_user_recent(context, *args, **kwargs):
    kwargs = utils.convert_kwargs(kwargs)
    user = yadon.ReadRowFromTable(settings.osu_users_table, context["message"].author.id, named_columns=True)
    if "m" not in kwargs:
        if user is None or user["default_mode"] == "":
            kwargs["m"] = "0"
        else:
            kwargs["m"] = user["default_mode"]
    if kwargs["m"] not in constants.mode_aliases.keys():
        return await context["koduck"].send_message(context["message"], content=settings.message_set_mode_no_param)
    
    #if "u" not in args or kwargs, use user's linked account if any
    if "u" not in kwargs:
        if user is None or user["osu_id"] == "":
            return await context["koduck"].send_message(context["message"], content=settings.message_osu_not_linked)
        else:
            kwargs["u"] = user["osu_id"]
    
    try:
        result_number = int(kwargs["p"])
    except (KeyError, ValueError):
        result_number = 0
    
    include_fails = "nofail" not in args and "nofail" not in kwargs
    
    if "v2" in kwargs:
        progress_message = await context["koduck"].send_message(context["message"], content="fetching score...")
        response = await osu_api_wrapper.get_user_scores_v2_async(context["koduck"].aiohttp_session, kwargs["u"], "recent", include_fails=include_fails, mode=constants.mode_aliases_v2[kwargs["m"]])
        
        if len(response) == 0:
            await progress_message.delete()
            return await context["koduck"].send_message(context["message"], content=settings.message_get_user_recent_no_result.format(constants.modes[kwargs["m"]]))
        else:
            if result_number > 0:
                try:
                    score_data = response[result_number-1]
                except IndexError:
                    await progress_message.delete()
                    return await context["koduck"].send_message(context["message"], content=settings.message_result_number_out_of_range.format(len(response)))
            else:
                score_data = response[0]
            
            await progress_message.edit(content="fetching beatmap...")
            beatmap_file_name = osu_api_wrapper.download_beatmap(score_data["beatmap"]["id"], score_data["beatmap"]["last_updated"])
            use_calc = kwargs["usecalc"] if "usecalc" in kwargs else None
            await progress_message.edit(content="calculating score...")
            embed = embed_formatters.format_single_score_embed_v2(score_data, beatmap_file_name, use_calc=use_calc)
            await progress_message.delete()
            sent_message = await context["koduck"].send_message(context["message"], embed=embed)
            utils.channel_id_to_active_beatmap_id[context["message"].channel.id] = score_data["beatmap"]["id"]
            return sent_message
    
    else:
        response = osu_api_wrapper.get_user_recent(**kwargs)
        
        if not include_fails:
            response = list(filter(lambda x: x["rank"] != "F", response))
        
        if len(response) == 0:
            return await context["koduck"].send_message(context["message"], content=settings.message_get_user_recent_no_result.format(constants.modes[kwargs["m"]]))
        else:
            if result_number > 0:
                try:
                    score_data = response[result_number-1]
                except IndexError:
                    return await context["koduck"].send_message(context["message"], content=settings.message_result_number_out_of_range.format(len(response)))
            else:
                score_data = response[0]
            
            if "pp" not in score_data:
                score_data["pp"] = 0
                #try to get pp by calling the api's get_scores method (only works if this recent score is the user's best score)
                if score_data["rank"] != "F":
                    scores = osu_api_wrapper.get_scores(**{"b":score_data["beatmap_id"], "m":kwargs["m"], "u":kwargs["u"]})
                    for score in scores:
                        if score["enabled_mods"] == score_data["enabled_mods"] and score["date"] == score_data["date"]:
                            try:
                                score_data["pp"] = float(score["pp"])
                            except (KeyError, TypeError):
                                pass
                            break
            
            use_calc = kwargs["usecalc"] if "usecalc" in kwargs else None
            sent_message = await context["koduck"].send_message(context["message"], embed=embed_formatters.format_single_score_embed(score_data, constants.modes[kwargs["m"]], include_acc_data="acc" in args or "acc" in kwargs, use_calc=use_calc))
            utils.channel_id_to_active_beatmap_id[context["message"].channel.id] = score_data["beatmap_id"]
            return sent_message

async def rs(context, *args, **kwargs):
    kwargs["nofail"] = True
    return await get_user_recent(context, *args, **kwargs)

async def get_scores(context, *args, **kwargs):
    kwargs = utils.convert_kwargs(kwargs)
    
    if "b" not in kwargs:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_scores_no_param)
    
    if "m" not in kwargs:
        beatmaps = osu_api_wrapper.get_beatmaps(**{"b": kwargs["b"]})
        if len(beatmaps) == 0:
            return await context["koduck"].send_message(context["message"], content=settings.message_get_beatmaps_no_result)
        kwargs["m"] = beatmaps[0]["mode"]
    
    #if "u" and "top" not in kwargs or args, use user's linked account if any
    if "u" not in kwargs and "top" not in kwargs and "top" not in args:
        user = yadon.ReadRowFromTable(settings.osu_users_table, context["message"].author.id, named_columns=True)
        if user is None or user["osu_id"] == "":
            return await context["koduck"].send_message(context["message"], content=settings.message_osu_not_linked)
        else:
            kwargs["u"] = user["osu_id"]
    
    #Parse mods
    if "mods" in kwargs:
        kwargs["mods"] = utils.mods_to_int(utils.get_mods_from_string(kwargs["mods"], ncpf=True))
    
    use_calc = kwargs["usecalc"] if "usecalc" in kwargs else None
    
    response = osu_api_wrapper.get_scores(**kwargs)
    
    result_number = 0
    result_number_2 = 0
    
    if "p" in kwargs.keys():
        if kwargs["p"].isdigit():
            result_number = int(kwargs["p"])
        else:
            temp = kwargs["p"].split("-")
            if len(temp) == 2:
                try:
                    result_number = int(kwargs["p"].split("-")[0])
                    result_number_2 = int(kwargs["p"].split("-")[1])
                except ValueError:
                    pass
    
    if "sortby" in kwargs:
        sort_by = kwargs["sortby"]
    else:
        sort_by = None
    if "reverse" in args or "reverse" in kwargs:
        reverse_sort = False
    else:
        reverse_sort = True
    
    #sort scores
    if sort_by == "combo":
        response = sorted(response, key=lambda x: int(x["maxcombo"]), reverse=reverse_sort)
    elif sort_by == "acc" or sort_by == "accuracy":
        response = sorted(response, key=lambda x: utils.calculate_accuracy(x, constants.modes[kwargs["m"]]), reverse=reverse_sort)
    elif sort_by == "date":
        response = sorted(response, key=lambda x: datetime.datetime.strptime(x["date"], settings.timestamp_format), reverse=reverse_sort)
    elif not reverse_sort:
        response.reverse()
    
    if len(response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_scores_no_result)
    #if a range of result numbers was given
    elif result_number_2 > 0 and result_number > 0:
        for score_data in response:
            score_data["beatmap_id"] = kwargs["b"]
        sent_message = await context["koduck"].send_message(context["message"], embed=embed_formatters.format_multiple_scores_embed(response, constants.modes[kwargs["m"]], desc="Top Scores" if "u" not in kwargs else "Scores", result_range=(result_number-1, result_number_2), sort_by=sort_by, use_calc=use_calc))
    #if one result number was given
    elif result_number > 0:
        try:
            score_data = response[result_number-1]
        except IndexError:
            return await context["koduck"].send_message(context["message"], content=settings.message_result_number_out_of_range.format(len(response)))
        score_data["beatmap_id"] = kwargs["b"]
        sent_message = await context["koduck"].send_message(context["message"], embed=embed_formatters.format_single_score_embed(score_data, constants.modes[kwargs["m"]], include_acc_data="acc" in args or "acc" in kwargs, use_calc=use_calc))
    elif len(response) == 1:
        score_data = response[0]
        score_data["beatmap_id"] = kwargs["b"]
        sent_message = await context["koduck"].send_message(context["message"], embed=embed_formatters.format_single_score_embed(score_data, constants.modes[kwargs["m"]], include_acc_data="acc" in args or "acc" in kwargs, use_calc=use_calc))
    else:
        for score_data in response:
            score_data["beatmap_id"] = kwargs["b"]
        sent_message = await context["koduck"].send_message(context["message"], embed=embed_formatters.format_multiple_scores_embed(response, constants.modes[kwargs["m"]], desc="Top Scores" if "u" not in kwargs else "Scores", sort_by=sort_by, use_calc=use_calc))
    utils.channel_id_to_active_beatmap_id[context["message"].channel.id] = kwargs["b"]
    return sent_message

async def compare(context, *args, **kwargs):
    #use last beatmap linked in chat by the bot
    try:
        kwargs["b"] = utils.channel_id_to_active_beatmap_id[context["message"].channel.id]
    except KeyError:
        return await context["koduck"].send_message(context["message"], content=settings.message_no_active_beatmap)
    return await get_scores(context, *args, **kwargs)

async def get_user_best(context, *args, **kwargs):
    kwargs = utils.convert_kwargs(kwargs)
    user = yadon.ReadRowFromTable(settings.osu_users_table, context["message"].author.id, named_columns=True)
    if "m" not in kwargs:
        if user is None or user["default_mode"] == "":
            kwargs["m"] = "0"
        else:
            kwargs["m"] = user["default_mode"]
    if kwargs["m"] not in constants.mode_aliases.keys():
        return await context["koduck"].send_message(context["message"], content=settings.message_set_mode_no_param)
    
    #if "u" not in args or kwargs, use user's linked account if any
    if "u" not in kwargs:
        if user is None or user["osu_id"] == "":
            return await context["koduck"].send_message(context["message"], content=settings.message_osu_not_linked)
        else:
            kwargs["u"] = user["osu_id"]
    
    use_calc = kwargs["usecalc"] if "usecalc" in kwargs else None
    
    response = await osu_api_wrapper.get_user_best_async(kwargs, context["koduck"].aiohttp_session)
    
    result_number = 0
    result_number_2 = 0
    
    if "p" in kwargs.keys():
        if kwargs["p"].isdigit():
            result_number = int(kwargs["p"])
        else:
            temp = kwargs["p"].split("-")
            if len(temp) == 2:
                try:
                    result_number = int(kwargs["p"].split("-")[0])
                    result_number_2 = int(kwargs["p"].split("-")[1])
                except ValueError:
                    pass
    
    if "sortby" in kwargs:
        sort_by = kwargs["sortby"]
    else:
        sort_by = None
    if "reverse" in args or "reverse" in kwargs:
        reverse_sort = False
    else:
        reverse_sort = True
    
    #sort scores
    if sort_by == "combo":
        response = sorted(response, key=lambda x: int(x["maxcombo"]), reverse=reverse_sort)
    elif sort_by == "acc" or sort_by == "accuracy":
        response = sorted(response, key=lambda x: utils.calculate_accuracy(x, constants.modes[kwargs["m"]]), reverse=reverse_sort)
    elif sort_by == "date":
        response = sorted(response, key=lambda x: datetime.datetime.strptime(x["date"], settings.timestamp_format), reverse=reverse_sort)
    elif not reverse_sort:
        response.reverse()
    
    if len(response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_scores_no_result)
    #if a range of result numbers was given
    elif result_number_2 > 0 and result_number > 0:
        return await context["koduck"].send_message(context["message"], embed=embed_formatters.format_multiple_scores_embed(response, constants.modes[kwargs["m"]], desc="Top Scores", result_range=(result_number-1, result_number_2), use_calc=use_calc))
    #if one result number was given
    elif result_number > 0:
        try:
            score_data = response[result_number-1]
        except IndexError:
            return await context["koduck"].send_message(context["message"], content=settings.message_result_number_out_of_range.format(len(response)))
        sent_message = await context["koduck"].send_message(context["message"], embed=embed_formatters.format_single_score_embed(score_data, constants.modes[kwargs["m"]], include_acc_data="acc" in args or "acc" in kwargs, use_calc=use_calc))
        utils.channel_id_to_active_beatmap_id[context["message"].channel.id] = score_data["beatmap_id"]
        return sent_message
    elif len(response) == 1:
        score_data = response[0]
        sent_message = await context["koduck"].send_message(context["message"], embed=embed_formatters.format_single_score_embed(score_data, constants.modes[kwargs["m"]], include_acc_data="acc" in args or "acc" in kwargs, use_calc=use_calc))
        utils.channel_id_to_active_beatmap_id[context["message"].channel.id] = score_data["beatmap_id"]
        return sent_message
    else:
        return await context["koduck"].send_message(context["message"], embed=embed_formatters.format_multiple_scores_embed(response, constants.modes[kwargs["m"]], desc="Top Scores", use_calc=use_calc))

async def recent_best(context, *args, **kwargs):
    kwargs["sortby"] = "date"
    if len(args) < 1:
        args = ["1"]
    return await get_user_best(context, *args, **kwargs)

async def get_beatmaps(context, *args, **kwargs):
    kwargs = utils.convert_kwargs(kwargs)
    
    #use last beatmap linked in chat by the bot if b or s or u parameter not given
    if "b" not in kwargs and "s" not in kwargs and "u" not in kwargs:
        try:
            kwargs["b"] = utils.channel_id_to_active_beatmap_id[context["message"].channel.id]
        except KeyError:
            return await context["koduck"].send_message(context["message"], content=settings.message_no_active_beatmap)
    
    response = osu_api_wrapper.get_beatmaps(**kwargs)
    
    if len(response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_beatmaps_no_result)
    elif len(response) == 1:
        beatmap_data = response[0]
        sent_message = await context["koduck"].send_message(context["message"], embed=embed_formatters.format_single_beatmap_embed(beatmap_data, use_calc=kwargs["usecalc"] if "usecalc" in kwargs else None))
        utils.channel_id_to_active_beatmap_id[context["message"].channel.id] = beatmap_data["beatmap_id"]
        return sent_message
    else:
        def asdf(x):
            return int(x["beatmap_id"])
        response = sorted(response, key=asdf, reverse=True)
        return await context["koduck"].send_message(context["message"], embed=embed_formatters.format_multiple_beatmaps_embed(response[:settings.defaultnummaps]))

async def calculate_pp(context, *args, **kwargs):
    kwargs = utils.convert_kwargs(kwargs)
    if "m" in kwargs and kwargs["m"] in constants.mode_aliases.keys():
        mode = constants.modes[constants.mode_aliases[kwargs["m"]]]
    else:
        mode = "osu"
    use_calc = kwargs["usecalc"] if "usecalc" in kwargs else None
    
    #Parse mods
    if "mods" in kwargs:
        query_mods = utils.get_mods_from_string(kwargs["mods"])
    else:
        query_mods = []
    modsint = utils.mods_to_int(query_mods)
    
    if "b" in kwargs:
        response = osu_api_wrapper.get_beatmaps(**{"b":kwargs["b"], "mods":utils.ignore_irrelevant_mods(modsint)})
    elif context["message"].channel.id in utils.channel_id_to_active_beatmap_id:
        response = osu_api_wrapper.get_beatmaps(**{"b":utils.channel_id_to_active_beatmap_id[context["message"].channel.id], "mods":utils.ignore_irrelevant_mods(modsint)})
    else:
        return await context["koduck"].send_message(context["message"], content=settings.message_no_active_beatmap)
    
    if len(response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_beatmaps_no_result)
    else:
        beatmap_data = response[0]
        #Calculate pp info using third party library
        beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap_data["beatmap_id"], beatmap_data["last_update"])
        native_mode = utils.get_map_mode(beatmap_file_name)
        #Force native mode if not standard (because they're incompatible with each other)
        if native_mode != "0":
            mode = constants.modes[native_mode]
        #current calc bugged - it automatically splits 300 counts to perfects and greats which affects the pp calculation so I need to manually set greats to 0
        if use_calc is None and mode == "mania" and "300" not in kwargs:
            result_fc = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=mode, mods=query_mods, n300=0, use_calc=use_calc)
        else:
            result_fc = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=mode, mods=query_mods, use_calc=use_calc)
        
        #Parse args and calculate
        try:
            combo = int(kwargs["combo"]) if "combo" in kwargs else None
            n300 = int(kwargs["300"]) if "300" in kwargs else None
            n200 = int(kwargs["200"]) if "200" in kwargs else None
            n100 = int(kwargs["100"]) if "100" in kwargs else None
            n50 = int(kwargs["50"]) if "50" in kwargs else None
            n0 = int(kwargs["miss"]) if "miss" in kwargs else None
            acc = float(kwargs["acc"]) if "acc" in kwargs else None
            score = int(kwargs["score"]) if "score" in kwargs else None
        except ValueError:
            return await context["koduck"].send_message(context["message"], content=settings.message_calculate_pp_invalid_param)
        #current calc bugged - it automatically splits 300 counts to perfects and greats which affects the pp calculation so I need to manually set greats to 0
        if use_calc is None and mode == "mania" and "300" not in kwargs:
            n300 = 0
        result = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=mode, mods=query_mods, acc=acc, combo=combo, n300=n300, n200=n200, n100=n100, n50=n50, n0=n0, score=score, use_calc=use_calc)

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
            elif mode == "catch":
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
        
        embed = discord.Embed(
            title="{} {} - {} [{}] ({:0.2f}☆) {}".format(
                utils.emojify("[mode{}]".format(mode)),
                beatmap_data["artist"],
                beatmap_data["title"],
                beatmap_data["version"],
                star_rating,
                "(Converted)" if beatmap_data["mode"] != constants.mode_aliases[mode] else ""),
            description="Beatmap {} by [{}](https://osu.ppy.sh/u/{})\nMods: {}".format(
                beatmap_data["beatmap_id"],
                beatmap_data["creator"],
                beatmap_data["creator_id"],
                utils.emojify("[mod{}]".format("] [mod".join(query_mods)))),
            url="https://osu.ppy.sh/b/{}".format(beatmap_data["beatmap_id"]))
        
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
                name="Score: ??? ({:0.2f}%)\n{}".format(accuracy, hits),
                value="**Total pp: {:0.2f} / {:0.2f}**\nDifficulty pp: {:0.2f} / {:0.2f}".format(
                    float(result["pp"]) if use_calc in constants.legacy_calcs else float(result["performance_attributes"]["pp"]),
                    float(result_fc["pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["pp"]),
                    float(result["difficulty pp"]) if use_calc in constants.legacy_calcs else float(result["performance_attributes"]["difficulty"]),
                    float(result_fc["difficulty pp"]) if use_calc in constants.legacy_calcs else float(result_fc["performance_attributes"]["difficulty"])))
        
        embed.set_thumbnail(url="https://b.ppy.sh/thumb/{}l.jpg".format(beatmap_data["beatmapset_id"]))
        #if use_calc == "taiko-loopy" and mode == "taiko":
        #    embed.set_footer(text=settings.message_alt_calc_loopp)
        #if use_calc == "2021-11-09" and mode == "taiko":
        #    embed.set_footer(text=settings.message_alt_calc_preltca)
        if use_calc is not None:
            embed.set_footer(text=settings.message_alt_calc.format(use_calc))
        sent_message = await context["koduck"].send_message(context["message"], embed=embed)
        utils.channel_id_to_active_beatmap_id[context["message"].channel.id] = beatmap_data["beatmap_id"]
        return sent_message

async def graph(context, *args, **kwargs):
    if "b" in kwargs:
        response = osu_api_wrapper.get_beatmaps(**{"b":kwargs["b"]})
    elif context["message"].channel.id in utils.channel_id_to_active_beatmap_id:
        response = osu_api_wrapper.get_beatmaps(**{"b":utils.channel_id_to_active_beatmap_id[context["message"].channel.id]})
    else:
        return await context["koduck"].send_message(context["message"], content=settings.message_no_active_beatmap)
    use_calc = kwargs["usecalc"] if "usecalc" in kwargs else None
    
    if len(response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_beatmaps_no_result)
    else:
        beatmap_data = response[0]
        beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap_data["beatmap_id"], beatmap_data["last_update"])
        times, difficulty_attributes = perf_calc_wrapper.calculate_sr(beatmap_file_name, mode=constants.modes[beatmap_data["mode"]], mods=utils.get_mods_from_string(kwargs["mods"], ncpf=True) if "mods" in kwargs else [], use_calc=use_calc)
        output_graph_file = "{}/{}_graph.png".format(settings.beatmaps_graphs_folder, beatmap_data["beatmap_id"])
        title = "{} - {} ({}) [{}]".format(beatmap_data["artist"], beatmap_data["title"], beatmap_data["creator"], beatmap_data["version"])
        
        if use_calc in constants.legacy_calcs:
            if beatmap_data["mode"] == "0":
                difficulty_attributes = [difficulty_attributes[0], difficulty_attributes[2], difficulty_attributes[3], difficulty_attributes[4], difficulty_attributes[5]]
                difficulty_labels = ["Star Rating", "Aim", "Speed", "Flashlight", "Slider"]
            # ignore "Hit Window" and "Approach Rate" attributes since they always stay the same, so it's pointless to graph it
            elif beatmap_data["mode"] == "1":
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
            elif beatmap_data["mode"] in ["2", "3"]:
                difficulty_attributes = [difficulty_attributes[0]]
                difficulty_labels = ["Star Rating"]
            else:
                raise Exception("what")
        else:
            '''
            if beatmap_data["mode"] == "0":
                difficulty_attributes = [[x["star_rating"] for x in difficulty_attributes],
                                         [x["aim_difficulty"] for x in difficulty_attributes],
                                         [x["speed_difficulty"] for x in difficulty_attributes],
                                         [(x["flashlight_difficulty"] if "flashlight_difficulty" in x else 0) for x in difficulty_attributes]]
                difficulty_labels = ["Star Rating", "Aim", "Speed", "Flashlight"]
            elif beatmap_data["mode"] == "1":
                difficulty_attributes = [[x["star_rating"] for x in difficulty_attributes],
                                         [x["stamina_difficulty"] for x in difficulty_attributes],
                                         [x["rhythm_difficulty"] for x in difficulty_attributes],
                                         [x["colour_difficulty"] for x in difficulty_attributes],
                                         [x["peak_difficulty"] for x in difficulty_attributes]]
                difficulty_labels = ["Star Rating", "Stamina", "Rhythm", "Colour", "Peak"]
            elif beatmap_data["mode"] in ["2", "3"]:
                difficulty_attributes = [[x["star_rating"] for x in difficulty_attributes]]
                difficulty_labels = ["Star Rating"]
            else:
                raise Exception("what")
            '''
            difficulty_attributes = [[x["star_rating"] for x in difficulty_attributes]]
            difficulty_labels = ["Star Rating"]
        
        beatmap_graph_generator.generate_graph(times, difficulty_attributes, difficulty_labels, output_graph_file, title=title, graph_title="Difficulty Attributes Graph")
        utils.channel_id_to_active_beatmap_id[context["message"].channel.id] = beatmap_data["beatmap_id"]
        return await context["koduck"].send_message(context["message"], file=discord.File(open(output_graph_file, 'rb')))

async def loopp_recalc(context, *args, **kwargs):
    kwargs["m"] = "taiko"
    kwargs = utils.convert_kwargs(kwargs)
    user = yadon.ReadRowFromTable(settings.osu_users_table, context["message"].author.id, named_columns=True)
    
    #if "u" not in args or kwargs, use user's linked account if any
    if "u" not in kwargs:
        if user is None or user["osu_id"] == "":
            return await context["koduck"].send_message(context["message"], content=settings.message_osu_not_linked)
        else:
            kwargs["u"] = user["osu_id"]
    
    table_name = "{}/{}_taiko".format(settings.scoresfolder, kwargs["u"])
    stored_time_stamp = yadon.ReadRowFromTable(settings.scorestimestamptable, kwargs["u"])
    calculator_has_not_been_updated = stored_time_stamp is not None and datetime.datetime.strptime(settings.loopp_update_timestamp, settings.timestamp_format) < datetime.datetime.strptime(stored_time_stamp[0], settings.timestamp_format)
    existing_top_100 = yadon.ReadTable(table_name, named_columns=True)
    live_top_100 = await osu_api_wrapper.get_user_best_async(kwargs, context["koduck"].aiohttp_session)
    score_ids_to_calculate = []
    new_top_100 = []
    if calculator_has_not_been_updated and existing_top_100:
        existing_score_ids = [x for x in existing_top_100.keys()]
        for score_data in live_top_100:
            if score_data["score_id"] not in existing_score_ids:
                score_ids_to_calculate.append(score_data["score_id"])
            else:
                new_top_100.append((score_data["score_id"], existing_top_100[score_data["score_id"]]))
        if len(score_ids_to_calculate) == 0:
            return await context["koduck"].send_message(context["message"], content=settings.message_loopp_recalc_exists.format(stored_time_stamp[0], stored_time_stamp[1], stored_time_stamp[2], stored_time_stamp[3]), file=discord.File("{}.txt".format(table_name)))
    else:
        score_ids_to_calculate = [x["score_id"] for x in live_top_100]
    
    progress_message = await context["koduck"].send_message(context["message"], content=settings.message_loopp_recalc_progress.format(0, len(score_ids_to_calculate)))
    num_calculated = 0
    for score_data in live_top_100:
        if score_data["score_id"] not in score_ids_to_calculate:
            continue
        
        beatmap = osu_api_wrapper.get_beatmaps(**{"b":score_data["beatmap_id"], "m":1, "a":"1", "mods":utils.ignore_irrelevant_mods(int(score_data["enabled_mods"]))})[0]
        beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap["beatmap_id"], beatmap["last_update"])
        enabled_mods = utils.get_mods_from_int(score_data["enabled_mods"])
        accuracy = utils.calculate_accuracy(score_data, "taiko")
        
        loopp_result_score = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode="taiko", mods=enabled_mods, combo=score_data["maxcombo"], n100=score_data["count100"], n50=score_data["count50"], n0=score_data["countmiss"], score=score_data["score"], use_calc="loopp")
        new_top_100.append((score_data["score_id"], {
            "beatmap_id": score_data["beatmap_id"],
            "beatmap_artist": beatmap["artist"],
            "beatmap_title": beatmap["title"],
            "beatmap_version": beatmap["version"],
            "beatmap_sr": beatmap["difficultyrating"],
            "beatmap_creator": beatmap["creator"],
            "before_pp": score_data["pp"], #result_score["pp"],
            "after_pp": loopp_result_score["pp"],
            "pp_difference": float(loopp_result_score["pp"]) - float(score_data["pp"]), #float(result_score["pp"]),
            "enabled_mods": "".join(utils.get_mods_from_int(score_data["enabled_mods"])),
            "accuracy": accuracy,
            #"beatmap_creator_id": beatmap["creator_id"],
            #"score": score_data["score"],
            "combo": score_data["maxcombo"],
            #"maxcombo": beatmap["maxcombo"],
            #"rank": score_data["rank"],
            "count300": score_data["count300"],
            "count100": score_data["count100"],
            "countmiss": score_data["countmiss"],
            "date": score_data["date"]
            #"before_strain_pp": result_score["strain pp"],
            #"before_acc_pp": result_score["accuracy pp"],
            #"before_pp_fc": result_fc["pp"],
            #"before_strain_pp_fc": result_fc["strain pp"],
            #"before_acc_pp_fc": result_fc["accuracy pp"],
            #"after_strain_pp": loopp_result_score["strain pp"],
            #"after_acc_pp": loopp_result_score["accuracy pp"],
            #"after_pp_fc": loopp_result_fc["pp"],
            #"after_strain_pp_fc": loopp_result_fc["strain pp"],
            #"after_acc_pp_fc": loopp_result_fc["accuracy pp"]
        }))
        num_calculated += 1
        if num_calculated % 5 == 0:
            await progress_message.edit(content=settings.message_loopp_recalc_progress.format(num_calculated, len(score_ids_to_calculate)))
    
    new_top_100 = sorted(new_top_100, key=lambda x: float(x[1]["after_pp"]), reverse=True)
    before_pp_total = 0
    for i in range(len(live_top_100)):
        before_pp_total += float(live_top_100[i]["pp"]) * (0.95**i)
    after_pp_total = 0
    for i in range(len(new_top_100)):
        after_pp_total += float(new_top_100[i][1]["after_pp"]) * (0.95**i)
    yadon.WriteTable(table_name, {x[0]:x[1] for x in new_top_100}, named_columns=True)
    yadon.WriteRowToTable(settings.scorestimestamptable, kwargs["u"], [datetime.datetime.now().strftime(settings.timestamp_format), before_pp_total, after_pp_total])
    return await context["koduck"].send_message(context["message"], content=settings.message_loopp_recalc_done.format(before_pp_total, after_pp_total), file=discord.File("{}.txt".format(table_name)))

async def analyze_recent(context, *args, **kwargs):
    kwargs = utils.convert_kwargs(kwargs)
    user = yadon.ReadRowFromTable(settings.osu_users_table, context["message"].author.id, named_columns=True)
    if "m" not in kwargs:
        if user is None or user["default_mode"] == "":
            kwargs["m"] = "0"
        else:
            kwargs["m"] = user["default_mode"]
    if kwargs["m"] not in constants.mode_aliases.keys():
        return await context["koduck"].send_message(context["message"], content=settings.message_set_mode_no_param)
    
    #if "u" not in args or kwargs, use user's linked account if any
    if "u" not in kwargs:
        if user is None or user["osu_id"] == "":
            return await context["koduck"].send_message(context["message"], content=settings.message_osu_not_linked)
        else:
            kwargs["u"] = user["osu_id"]
    
    response = osu_api_wrapper.get_user_recent(**kwargs)
    response = list(filter(lambda x: x["rank"] != "F", response))
    
    if len(response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_user_recent_no_result.format(constants.modes[kwargs["m"]]))
    else:
        score_data = response[0]
    kwargs["b"] = score_data["beatmap_id"]
    kwargs["mods"] = "".join(utils.get_mods_from_int(score_data["enabled_mods"]))
    
    return await analyze_replay(context, *args, **kwargs)

async def analyze_replay(context, *args, **kwargs):
    kwargs = utils.convert_kwargs(kwargs)
    use_calc = kwargs["usecalc"] if "usecalc" in kwargs else None
    replay_attached = len(context["message"].attachments) > 0
    
    if not replay_attached:
        #if "u" not in kwargs, use user's linked account if any
        if "u" not in kwargs:
            user = yadon.ReadRowFromTable(settings.osu_users_table, context["message"].author.id, named_columns=True)
            if user is None or user["osu_id"] == "":
                return await context["koduck"].send_message(context["message"], content=settings.message_osu_not_linked)
            else:
                kwargs["u"] = user["osu_id"]
        
        progress_message = await context["koduck"].send_message(context["message"], content="fetching beatmap...")
        if "b" not in kwargs:
            return await progress_message.edit(content=settings.message_get_replay_no_param)
        
        beatmaps = osu_api_wrapper.get_beatmaps(**{"b": kwargs["b"]})
        if len(beatmaps) == 0:
            return await progress_message.edit(content=settings.message_get_beatmaps_no_result)
        beatmap_data = beatmaps[0]
        beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap_data["beatmap_id"], beatmap_data["last_update"])
        
        if "m" not in kwargs or kwargs["m"] not in constants.mode_aliases.keys():
            kwargs["m"] = beatmap_data["mode"]
        
        #Parse mods
        if "mods" in kwargs:
            kwargs["mods"] = utils.mods_to_int(utils.get_mods_from_string(kwargs["mods"], ncpf=True))
        
        await progress_message.edit(content="fetching replay...")
        get_scores_response = osu_api_wrapper.get_scores(**kwargs)
        if len(get_scores_response) == 0:
            return await progress_message.edit(content=settings.message_get_scores_no_result)
        elif len(get_scores_response) > 1:
            scores_mods = ["".join(utils.get_mods_from_int(score_data["enabled_mods"])) for score_data in get_scores_response]
            scores_mods = [x or "NM" for x in scores_mods]
            return await progress_message.edit(content=settings.message_get_scores_multiple_results.format(str(scores_mods)))
        else:
            score_data = get_scores_response[0]
        
        if score_data["replay_available"] != "1":
            return await progress_message.edit(content=settings.message_get_replay_not_available)
        enabled_mods = utils.get_mods_from_int(score_data["enabled_mods"])
        
        replaysearch = osu_api_wrapper.get_replay(**{"s": score_data["score_id"], "m":kwargs["m"]})
        if "error" in replaysearch:
            return await progress_message.edit(content=settings.message_get_replay_error.format(replaysearch["error"]))
        
        replay_lzma = replaysearch["content"]
        replay_details = OsuReplayDetails()
        replay_details.replay_data_raw = base64.b64decode(replay_lzma)
        replay_details.game_mode = int(kwargs["m"])
        replay_details.mods_raw = int(score_data["enabled_mods"])
        
        #Calling get_beatmaps a second time just to find out the mod-adjusted SR :skull:
        beatmaps = osu_api_wrapper.get_beatmaps(**{"b": kwargs["b"], "mods": utils.ignore_irrelevant_mods(int(score_data["enabled_mods"]))})
        if len(beatmaps) == 0:
            return await progress_message.edit(content=settings.message_get_beatmaps_no_result)
        beatmap_data = beatmaps[0]
    else:
        progress_message = await context["koduck"].send_message(context["message"], content="reading replay...")
        replay_file_name = context["message"].attachments[0].filename
        await context["message"].attachments[0].save("{}/{}".format(settings.replays_folder, replay_file_name))
        
        replay_parser = OsuReplayParser()
        replay_file = open("{}/{}".format(settings.replays_folder, replay_file_name), "rb")
        replay_details = replay_parser.parse_from_file(replay_file)
        enabled_mods = utils.get_mods_from_int(replay_details.mods_raw)
        
        await progress_message.edit(content="fetching beatmap...")
        beatmaps = osu_api_wrapper.get_beatmaps(**{"h": replay_details.map_md5hash})
        if len(beatmaps) == 0:
            return await progress_message.edit(content=settings.message_get_beatmaps_no_result)
        beatmap_data = beatmaps[0]
        beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap_data["beatmap_id"], beatmap_data["last_update"])
    
    if beatmap_data["mode"] in ["2", "3"]:
        return await progress_message.edit(content=settings.message_analyze_replay_unsupported_mode)
    
    await progress_message.edit(content="analyzing replay...")
    replay_analyzer = OsuReplayAnalyzer(map_file_name=beatmap_file_name, replay_details=replay_details, force_hr="HR" in enabled_mods, force_ez="EZ" in enabled_mods)
    DT_enabled = "DT" in enabled_mods or "NC" in enabled_mods
    converted_ur = replay_analyzer.unstable_rate / 1.5 if DT_enabled else replay_analyzer.unstable_rate
    output_string = "Hit Error: {:0.2f}ms - {:0.2f}ms\nUnstable Rate: {:0.2f}{}".format(replay_analyzer.hit_error_negative, replay_analyzer.hit_error_positive, replay_analyzer.unstable_rate, " ({:0.2f})".format(converted_ur) if DT_enabled else "")
    note = "Notes: Currently ignores sliders and\nspinners. V1/V2/V3 scores are WIP."
    convert_string = ""
    
    #with open("hit_errors_2.txt", "w", encoding="utf8") as file:
    #    file.write(str(replay_analyzer.hit_errors))
    #with open("hit_object_results.txt", "w", encoding="utf8") as file:
    #    for k,v in replay_analyzer.hit_object_results.items():
    #        file.write(f"{k.offset} | {v[0]} | {v[1]} | {v[3]}\n")
    
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
    
    if replay_details.game_mode == 1:
        #Loopy's stability index for taiko
        result_fc = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=constants.modes[str(replay_details.game_mode)], mods=[x for x in enabled_mods if x != "V2"], use_calc=use_calc)
        hit_count = len(greens) + len(oranges)
        if use_calc in constants.legacy_calcs:
            a = ((float(result_fc["rhythm difficulty"]) - 0.7) ** 3) / 3
            s = ((float(result_fc["stamina difficulty"]) - 2.2) ** 3) / 30
        else:
            a = ((float(result_fc["difficulty_attributes"]["rhythm_difficulty"]) - 0.7) ** 3) / 3
            s = ((float(result_fc["difficulty_attributes"]["stamina_difficulty"]) - 2.2) ** 3) / 30
        c = math.log(hit_count / 1000, 1.5) / 5
        u = math.log(converted_ur / 150, 0.925)
        stability_index = (5 + a + s + c) * u
        #stability_index = (5 + (math.log(hit_count / 1000, 2) / 3)) * (math.log(converted_ur / 125, 0.93) + (22 * (math.pow(1.1, float(beatmap_data["difficultyrating"]) - 5) - 1)))
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
        
        output_string += "\nV1 Score: {:0.0f}".format(replay_analyzer.score_v1)
        output_string += "\nV2 Score: {:0.0f}".format((replay_analyzer.combo_score_v2 + replay_analyzer.accuracy_score) * replay_analyzer.mod_multiplier)
        output_string += "\nV3 Score: {:0.0f}".format((replay_analyzer.combo_score_v3 + replay_analyzer.accuracy_score + replay_analyzer.bonus_score) * replay_analyzer.mod_multiplier)
        output_string += "\nMax Combo: {}".format(replay_analyzer.player_max_combo)
        
        if beatmap_data["mode"] == "0":
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
    
    player_name = replay_details.player_name if replay_attached else score_data["username"]
    replay_timestamp = datetime.datetime(1, 1, 1) + datetime.timedelta(microseconds=replay_details.timestamp // 10) if replay_attached else datetime.datetime.strptime(score_data["date"], settings.timestamp_format).replace(tzinfo=datetime.timezone.utc)
    replay_date = replay_timestamp.strftime(settings.timestamp_format) if replay_attached else score_data["date"]
    
    await progress_message.edit(content="generating graph...")
    times, difficulty_attributes = perf_calc_wrapper.calculate_sr(beatmap_file_name, mode=constants.modes[str(replay_details.game_mode)], mods=[x for x in enabled_mods if x != "V2"], use_calc=use_calc)
    output_graph_file = "{}/{}_graph_{}.png".format(settings.beatmaps_graphs_folder, beatmap_data["beatmap_id"], int(replay_timestamp.timestamp()))
    if len(enabled_mods) == 0:
        enabled_mods.append("NM")
    title = "{} - {} ({}) [{}] ({:0.2f}☆){}\nPlayed by {} on {} with {}".format(beatmap_data["artist"], beatmap_data["title"], beatmap_data["creator"], beatmap_data["version"], float(beatmap_data["difficultyrating"]), convert_string, player_name, replay_date, "".join(enabled_mods))
    
    if replay_details.game_mode == 0:
        if use_calc in constants.legacy_calcs:
            #Flashlight difficulty attribute has inflated values for some reason
            #difficulty_attributes = [difficulty_attributes[0], difficulty_attributes[2], difficulty_attributes[3], [x/10 for x in difficulty_attributes[4]], difficulty_attributes[5]]
            #difficulty_labels = ["Star Rating", "Aim", "Speed", "Flashlight", "Slider"]
            difficulty_attributes = [difficulty_attributes[0]]
            difficulty_labels = ["Star Rating"]
            beatmap_graph_generator.generate_graph(times, difficulty_attributes, difficulty_labels, output_graph_file, title=title, greens=greens, blues=blues, misses=misses, graph_title="Replay Graph", footer_text=output_string)
        else:
            #difficulty_attributes = [[x["star_rating"] for x in difficulty_attributes],
            #                         [x["aim_difficulty"] for x in difficulty_attributes],
            #                         [x["speed_difficulty"] for x in difficulty_attributes],
            #                         [(x["flashlight_difficulty"] if "flashlight_difficulty" in x else 0) for x in difficulty_attributes],
            #                         [x["slider_factor"] for x in difficulty_attributes]]
            #difficulty_labels = ["Star Rating", "Aim", "Speed", "Flashlight", "Slider"]
            difficulty_attributes = [[x["star_rating"] for x in difficulty_attributes]]
            difficulty_labels = ["Star Rating"]
            beatmap_graph_generator.generate_graph(times, difficulty_attributes, difficulty_labels, output_graph_file, title=title, greens=greens, blues=blues, misses=misses, graph_title="Replay Graph", footer_text=output_string)
    # ignore "Hit Window" and "Approach Rate" attributes since they always stay the same, so it's pointless to graph it
    elif replay_details.game_mode == 1:
        mods2 = utils.get_mods_from_int(replay_details.mods_raw)
        pp_data_fc = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=constants.modes[str(replay_details.game_mode)], mods=mods2, use_calc=use_calc)
        pp_data = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=constants.modes[str(replay_details.game_mode)], mods=mods2, n100=len(greens), n0=len(misses), use_calc=use_calc)
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
            #difficulty_attributes = [[x["star_rating"] for x in difficulty_attributes],
            #                         [x["stamina_difficulty"] for x in difficulty_attributes],
            #                         [x["rhythm_difficulty"] for x in difficulty_attributes],
            #                         [x["colour_difficulty"] for x in difficulty_attributes],
            #                         [x["peak_difficulty"] for x in difficulty_attributes]]
            #difficulty_labels = ["Star Rating", "Stamina", "Rhythm", "Colour", "Peak"]
            difficulty_attributes = [[x["star_rating"] for x in difficulty_attributes]]
            difficulty_labels = ["Star Rating"]
        
        if "hide_100s" in args or "hide_100s" in kwargs:
            greens = []
        if "hide_50s" in args or "hide_50s" in kwargs:
            blues = []
        if "hide_misses" in args or "hide_misses" in kwargs:
            misses = []
        if "hide_finisher_misses" in args or "hide_finisher_misses" in kwargs:
            finisher_misses = []
        beatmap_graph_generator.generate_graph(times, difficulty_attributes, difficulty_labels, output_graph_file, title=title, greens=greens, blues=blues, misses=misses, finisher_misses=finisher_misses, graph_title="Replay Graph", footer_text=output_string, note=note)
    else:
        raise Exception("what")
    
    await progress_message.delete()
    #return await context["koduck"].send_message(context["message"], content=output_string, file=discord.File(open(output_graph_file, 'rb')), ignore_cd=True)
    return await context["koduck"].send_message(context["message"], file=discord.File(open(output_graph_file, 'rb')), ignore_cd=True)

async def convert_to_taiko(context, *args, **kwargs):
    kwargs = utils.convert_kwargs(kwargs)
    progress_message = await context["koduck"].send_message(context["message"], content="fetching beatmap...")
    
    if "b" not in kwargs:
        return await progress_message.edit(content=settings.message_get_replay_no_param)
    
    beatmaps = osu_api_wrapper.get_beatmaps(**{"b": kwargs["b"]})
    if len(beatmaps) == 0:
        return await progress_message.edit(content=settings.message_get_beatmaps_no_result)
    beatmap_data = beatmaps[0]
    beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap_data["beatmap_id"], beatmap_data["last_update"])
    
    await progress_message.edit(content="converting beatmap...")
    beatmap_parser = OsuBeatmapParser()
    beatmap_file = open(beatmap_file_name, encoding="utf-8")
    beatmap_details = beatmap_parser.parse_from_file(beatmap_file)
    
    if beatmap_details.game_mode != 0:
        return await progress_message.edit(content="Cannot convert a non-standard map")
    beatmap_details.convert_to_taiko()
    beatmap_details.beatmap_id = 0
    beatmap_details.difficulty_name += " (Taiko Convert)"
    output_file_name = "{}/{}_taiko_convert.osu".format(settings.beatmaps_download_folder, beatmap_data["beatmap_id"])
    beatmap_details.export(output_file_name)
    
    await progress_message.delete()
    return await context["koduck"].send_message(context["message"], file=discord.File(open(output_file_name, 'rb')), ignore_cd=True)

async def normalize_sv(context, *args, **kwargs):
    replay_attached = len(context["message"].attachments) > 0
    if len(args) < 1:
        return await context["koduck"].send_message(context["message"], content="I need a bpm")
    
    the_bpm = float(args[0])

    if not replay_attached:
        return await context["koduck"].send_message(context["message"], content="I need a .osu file")

    beatmap_file_name = context["message"].attachments[0].filename
    await context["message"].attachments[0].save("{}/{}".format(settings.beatmaps_download_folder, beatmap_file_name))

    beatmap_parser = OsuBeatmapParser()
    beatmap_file = open("{}/{}".format(settings.beatmaps_download_folder, beatmap_file_name), encoding="utf-8")
    beatmap_details = beatmap_parser.parse_from_file(beatmap_file)
    beatmap_details.normalize_sv(the_bpm)
    beatmap_details.beatmap_id = 0
    beatmap_details.difficulty_name += " (SV Normalized to {} BPM)".format(the_bpm)
    output_file_name = "{}/{} - {} ({}) [{}].osu".format(
        settings.beatmaps_download_folder,
        beatmap_details.artist,
        beatmap_details.title,
        beatmap_details.mapper_name,
        beatmap_details.difficulty_name)
    beatmap_details.export(output_file_name)
    
    return await context["koduck"].send_message(context["message"], file=discord.File(open(output_file_name, 'rb')), ignore_cd=True)

'''
async def track(context, *args, **kwargs):
    kwargs = utils.convert_kwargs(kwargs)
    user = yadon.ReadRowFromTable(settings.osu_users_table, context["message"].author.id, named_columns=True)
    if "m" not in kwargs:
        if user is None or user["default_mode"] == "":
            kwargs["m"] = "0"
        else:
            kwargs["m"] = user["default_mode"]
    if kwargs["m"] not in constants.mode_aliases.keys():
        return await context["koduck"].send_message(context["message"], content=settings.message_set_mode_no_param)
    
    #if "u" not in args or kwargs, use user's linked account if any
    if "u" not in kwargs:
        if user is None or user["osu_id"] == "":
            return await context["koduck"].send_message(context["message"], content=settings.message_osu_not_linked)
        else:
            kwargs["u"] = user["osu_id"]
    
    get_user_response = await osu_api_wrapper.get_user_async(kwargs, context["koduck"].aiohttp_session)
    if len(get_user_response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_user_no_result)
    user = get_user_response[0]
    key = "{}_{}".format(user["user_id"], kwargs["m"])
    channel_id = context["message"].channel.id
    
    row = yadon.ReadRowFromTable(settings.track_table, key)
    if row and str(channel_id) in row[0].split("/"):
        return await context["koduck"].send_message(context["message"], content=settings.message_track_failure.format(user["username"], constants.modes[kwargs["m"]], context["message"].channel.id))
    
    top_scores = await osu_api_wrapper.get_user_best_async(kwargs, context["koduck"].aiohttp_session)
    score_ids = [score["score_id"] for score in top_scores]
    yadon.WriteRowToTable(settings.track_table, key, [context["message"].channel.id, user["pp_rank"], user["pp_raw"]] + score_ids)
    global restart_background_task
    restart_background_task = True
    return await context["koduck"].send_message(context["message"], content=settings.message_track_success.format(constants.modes[kwargs["m"]], user["username"], context["message"].channel.id))

async def untrack(context, *args, **kwargs):
    kwargs = utils.convert_kwargs(kwargs)
    user = yadon.ReadRowFromTable(settings.osu_users_table, context["message"].author.id, named_columns=True)
    if "m" not in kwargs:
        if user is None or user["default_mode"] == "":
            kwargs["m"] = "0"
        else:
            kwargs["m"] = user["default_mode"]
    if kwargs["m"] not in constants.mode_aliases.keys():
        return await context["koduck"].send_message(context["message"], content=settings.message_set_mode_no_param)
    
    #if "u" not in args or kwargs, use user's linked account if any
    if "u" not in kwargs:
        if user is None or user["osu_id"] == "":
            return await context["koduck"].send_message(context["message"], content=settings.message_osu_not_linked)
        else:
            kwargs["u"] = user["osu_id"]
    
    get_user_response = await osu_api_wrapper.get_user_async(kwargs, context["koduck"].aiohttp_session)
    if len(get_user_response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_user_no_result)
    user = get_user_response[0]
    key = "{}_{}_{}".format(user["user_id"], kwargs["m"], context["message"].channel.id)
    
    row = yadon.ReadRowFromTable(settings.track_table, key)
    if not row:
        return await context["koduck"].send_message(context["message"], content=settings.message_untrack_failure.format(user["username"], constants.modes[kwargs["m"]], context["message"].channel.id))
    yadon.RemoveRowFromTable(settings.track_table, key)
    global restart_background_task
    restart_background_task = True
    return await context["koduck"].send_message(context["message"], content=settings.message_untrack_success.format(constants.modes[kwargs["m"]], user["username"], context["message"].channel.id))
'''

async def mod_stats(context, *args, **kwargs):
    kwargs = utils.convert_kwargs(kwargs)
    user = yadon.ReadRowFromTable(settings.osu_users_table, context["message"].author.id, named_columns=True)
    if "m" not in kwargs:
        if user is None or user["default_mode"] == "":
            kwargs["m"] = "0"
        else:
            kwargs["m"] = user["default_mode"]
    if kwargs["m"] not in constants.mode_aliases.keys():
        return await context["koduck"].send_message(context["message"], content=settings.message_set_mode_no_param)
    mode = constants.modes[kwargs["m"]]
    
    #if "u" not in args or kwargs, use user's linked account if any
    if "u" not in kwargs:
        if user is None or user["osu_id"] == "":
            return await context["koduck"].send_message(context["message"], content=settings.message_osu_not_linked)
        else:
            kwargs["u"] = user["osu_id"]
    
    get_user_response = await osu_api_wrapper.get_user_async(kwargs, context["koduck"].aiohttp_session)
    if len(get_user_response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_user_no_result)
    user = get_user_response[0]
    
    get_user_best_response = await osu_api_wrapper.get_user_best_async(kwargs, context["koduck"].aiohttp_session)
    if len(get_user_best_response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_scores_no_result)
    
    score_count = len(get_user_best_response)
    total_pp = 0
    mod_pp = {}
    mod_pp_separated = {}
    mod_count = {}
    mod_count_separated = {}
    for i in range(score_count):
        score_data = get_user_best_response[i]
        mods = "".join(utils.get_mods_from_int(score_data["enabled_mods"]))
        mods_separated = utils.get_mods_from_int(score_data["enabled_mods"])
        
        if not mods:
            mods = "NM"
            mods_separated = ["NM"]
        scaled_pp = float(score_data["pp"]) * (0.95**i)
        total_pp += scaled_pp
        
        if mods not in mod_pp.keys():
            mod_pp[mods] = scaled_pp
            mod_count[mods] = 1
        else:
            mod_pp[mods] += scaled_pp
            mod_count[mods] += 1
        
        for mod in mods_separated:
            if mod not in mod_pp_separated.keys():
                mod_pp_separated[mod] = scaled_pp
                mod_count_separated[mod] = 1
            else:
                mod_pp_separated[mod] += scaled_pp
                mod_count_separated[mod] += 1
    
    favorite_mods = sorted([(x,y) for x,y in mod_count.items()], key=lambda z: z[1], reverse=True)
    favorite_mods_separated = sorted([(x,y) for x,y in mod_count_separated.items()], key=lambda z: z[1], reverse=True)
    pp_sources = sorted([(x,y) for x,y in mod_pp.items()], key=lambda z: z[1], reverse=True)
    pp_sources_separated = sorted([(x,y) for x,y in mod_pp_separated.items()], key=lambda z: z[1], reverse=True)
    
    favorite_mods_string = ""
    favorite_mods_separated_string = ""
    pp_sources_string = ""
    pp_sources_separated_string = ""
    for item in favorite_mods:
        favorite_mods_string += "{}: ``{:0.2f}%``\n".format(item[0], item[1]*100/score_count)
    for item in favorite_mods_separated:
        favorite_mods_separated_string += "{}: ``{:0.2f}%``\n".format(item[0], item[1]*100/score_count)
    for item in pp_sources:
        pp_sources_string += "{}: ``{:0.2f} ({:0.2f}%)``\n".format(item[0], item[1], item[1]*100/total_pp)
    for item in pp_sources_separated:
        pp_sources_separated_string += "{}: ``{:0.2f} ({:0.2f}%)``\n".format(item[0], item[1], item[1]*100/total_pp)
    
    embed = discord.Embed(
        title="{} {} mod stats for **{}**".format(
            utils.emojify("[mode{}]".format(mode)),
            mode,
            user["username"]),
        description="**Performance**: {}pp (#{}) :flag_{}: #{}".format(
            user["pp_raw"],
            user["pp_rank"],
            user["country"].lower(),
            user["pp_country_rank"]),
        url="https://osu.ppy.sh/u/{}".format(user["user_id"]))
    embed.add_field(name="Favorite Mods", value=favorite_mods_string)
    embed.add_field(name="Favorite Mods (separated)", value=favorite_mods_separated_string)
    embed.add_field(name="\u200B", value="\u200B")
    embed.add_field(name="pp sources", value=pp_sources_string)
    embed.add_field(name="pp sources (separated)", value=pp_sources_separated_string)
    embed.set_thumbnail(url="https://s.ppy.sh/a/{}".format(user["user_id"]))
    return await context["koduck"].send_message(context["message"], embed=embed)

async def mapper_stats(context, *args, **kwargs):
    kwargs = utils.convert_kwargs(kwargs)
    user = yadon.ReadRowFromTable(settings.osu_users_table, context["message"].author.id, named_columns=True)
    if "m" not in kwargs:
        if user is None or user["default_mode"] == "":
            kwargs["m"] = "0"
        else:
            kwargs["m"] = user["default_mode"]
    if kwargs["m"] not in constants.mode_aliases.keys():
        return await context["koduck"].send_message(context["message"], content=settings.message_set_mode_no_param)
    mode = constants.mode_aliases_v2[kwargs["m"]]
    
    #if "u" not in args or kwargs, use user's linked account if any
    if "u" not in kwargs:
        if user is None or user["osu_id"] == "":
            return await context["koduck"].send_message(context["message"], content=settings.message_osu_not_linked)
        else:
            kwargs["u"] = user["osu_id"]
    
    get_user_response = osu_api_wrapper.get_user_v2(kwargs["u"], mode)
    if "error" in get_user_response:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_user_no_result)
    
    #get_user_best_response = await osu_api_wrapper.get_user_best_async(kwargs, context["koduck"].aiohttp_session)
    get_user_best_response = osu_api_wrapper.get_user_scores_v2(get_user_response["id"], "best", mode)
    if len(get_user_best_response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_scores_no_result)
    
    score_count = len(get_user_best_response)
    total_pp = 0
    mapper_pp = {}
    mapper_count = {}
    for i in range(score_count):
        score_data = get_user_best_response[i]
        mapper = score_data["beatmapset"]["creator"]
        
        scaled_pp = float(score_data["pp"]) * (0.95**i)
        total_pp += scaled_pp
        
        if mapper not in mapper_pp.keys():
            mapper_pp[mapper] = scaled_pp
            mapper_count[mapper] = 1
        else:
            mapper_pp[mapper] += scaled_pp
            mapper_count[mapper] += 1
    
    favorite_mappers = sorted([(x,y) for x,y in mapper_count.items()], key=lambda z: z[1], reverse=True)
    pp_sources = sorted([(x,y) for x,y in mapper_pp.items()], key=lambda z: z[1], reverse=True)
    
    favorite_mappers_string = ""
    pp_sources_pp_string = ""
    for i in range(min(5, len(favorite_mappers))):
        item = favorite_mappers[i]
        favorite_mappers_string += "{}: ``{:0.2f}%``\n".format(item[0], item[1]*100/score_count)
    for i in range(min(5, len(pp_sources))):
        item = pp_sources[i]
        pp_sources_pp_string += "{}: ``{:0.2f} ({:0.2f}%)``\n".format(item[0], item[1], item[1]*100/total_pp)
    
    embed = discord.Embed(
        title="{} {} mapper stats for **{}**".format(
            utils.emojify("[mode{}]".format(mode)),
            mode,
            get_user_response["username"]),
        description="**Performance**: {}pp (#{}) :flag_{}: #{}".format(
            get_user_response["statistics"]["pp"],
            get_user_response["statistics"]["global_rank"],
            get_user_response["country_code"].lower(),
            get_user_response["statistics"]["country_rank"]),
        url="https://osu.ppy.sh/u/{}".format(get_user_response["id"]))
    embed.add_field(name="Favorite Mappers", value=favorite_mappers_string)
    embed.add_field(name="pp sources (pp)", value=pp_sources_pp_string)
    embed.set_thumbnail(url="https://s.ppy.sh/a/{}".format(get_user_response["id"]))
    return await context["koduck"].send_message(context["message"], embed=embed)

async def taiko_card(context, *args, **kwargs):
    user = yadon.ReadRowFromTable(settings.osu_users_table, context["message"].author.id, named_columns=True)
    
    #allow first arg to be used as "u" parameter if it's not provided in kwargs
    if len(args) >= 1 and "u" not in kwargs:
        kwargs["u"] = args[0]
    
    #if "u" not in args or kwargs, use user's linked account if any
    if "u" not in kwargs:
        if user is None or user["osu_id"] == "":
            return await context["koduck"].send_message(context["message"], content=settings.message_osu_not_linked)
        else:
            kwargs["u"] = user["osu_id"]
    
    get_user_response = osu_api_wrapper.get_user_v2(kwargs["u"])
    if len(get_user_response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_user_no_result)
    
    #get_user_best_response = await osu_api_wrapper.get_user_best_async(kwargs, context["koduck"].aiohttp_session)
    get_user_best_response = osu_api_wrapper.get_user_scores_v2(get_user_response["id"], "best", "taiko")
    if len(get_user_best_response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_scores_no_result)
    
    if len(get_user_best_response) < 50:
        return await context["koduck"].send_message(context["message"], content="need at least 50 top plays to calculate skill")
    
    star_sum = 0
    speed_sum = 0
    acc_sum = 0
    for i in range(50):
        score_data = get_user_best_response[i]
        stars = score_data["beatmap"]["difficulty_rating"]
        bpm = score_data["beatmap"]["bpm"]
        od = score_data["beatmap"]["accuracy"]
        hp = score_data["beatmap"]["drain"]
        acc = score_data["accuracy"] * 100
        
        if "HR" in score_data["mods"]:
            od = min(10, od * 1.4)
            hp = min(10, hp * 1.4)
        if "DT" in score_data["mods"] or "NC" in score_data["mods"]:
            stars *= 1.3
            bpm *= 1.5
            odms = 33.33 - (od * 2)
            od = (49.5 - odms) / 3
        if "HT" in score_data["mods"]:
            stars /= 1.2
            bpm /= 1.33
            odms = 66.66 - (od * 4)
            od = (49.5 - odms) / 3
        
        speed_skill = math.pow(stars/1.1, math.log(bpm)/math.log(stars*20))
        acc_skill = math.pow(stars, (math.pow(acc, 3)/math.pow(100, 3)) * 1.05) * (math.pow(od, 0.02) / math.pow(6, 0.02)) * (math.pow(hp, 0.02) / (math.pow(5, 0.02)))
        star_sum += stars
        speed_sum += speed_skill
        acc_sum += acc_skill
    star_avg = star_sum / 50
    speed_avg = speed_sum / 50 * 100 * 1.03
    acc_avg = acc_sum / 50 * 100
    return await context["koduck"].send_message(context["message"], content="player: {}\nstars: {:0.2f}\nspeed: {:0.2f}\nacc: {:0.2f}".format(get_user_response["username"], star_avg, speed_avg, acc_avg))

async def what_if(context, *args, **kwargs):
    kwargs = utils.convert_kwargs(kwargs)
    user = yadon.ReadRowFromTable(settings.osu_users_table, context["message"].author.id, named_columns=True)
    if "m" not in kwargs:
        if user is None or user["default_mode"] == "":
            kwargs["m"] = "0"
        else:
            kwargs["m"] = user["default_mode"]
    if kwargs["m"] not in constants.mode_aliases.keys():
        return await context["koduck"].send_message(context["message"], content=settings.message_set_mode_no_param)
    
    #if "u" not in args or kwargs, use user's linked account if any
    if "u" not in kwargs:
        if user is None or user["osu_id"] == "":
            return await context["koduck"].send_message(context["message"], content=settings.message_osu_not_linked)
        else:
            kwargs["u"] = user["osu_id"]
    
    if len(args) < 1:
        return await context["koduck"].send_message(context["message"], content="I need a number")
    try:
        new_top_pp = float(args[0])
    except ValueError:
        return await context["koduck"].send_message(context["message"], content="I need a number")
    if new_top_pp <= 0:
        return await context["koduck"].send_message(context["message"], content="I need a POSITIVE number")
    
    user_data = await osu_api_wrapper.get_user_v2_async(context["koduck"].aiohttp_session, kwargs["u"], mode=constants.mode_aliases_v2[kwargs["m"]])
    top_scores = await osu_api_wrapper.get_user_scores_v2_async(context["koduck"].aiohttp_session, kwargs["u"], "best", mode=constants.mode_aliases_v2[kwargs["m"]])
    #globalrankings = await osu_api_wrapper.get_rankings_v2_async(context["koduck"].aiohttp_session, mode=constants.mode_aliases_v2[kwargs["m"]], type="performance")
    
    if len(top_scores) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_user_recent_no_result.format(constants.modes[kwargs["m"]]))
    top_scores_pp = [x["pp"] for x in top_scores]
    
    old_pp_total = 0
    for i in range(len(top_scores_pp)):
        old_pp_total += float(top_scores_pp[i]) * (0.95**i)
    bonus_pp = float(user_data["statistics"]["pp"]) - old_pp_total
    
    top_scores_pp.append(int(args[0]))
    top_scores_pp = sorted(top_scores_pp, reverse=True)
    top_scores_pp = top_scores_pp[:100]
    new_pp_total = 0
    for i in range(len(top_scores_pp)):
        new_pp_total += float(top_scores_pp[i]) * (0.95**i)
    return await context["koduck"].send_message(context["message"], content="Before: {:0.2f}\nAfter: {:0.2f}".format(old_pp_total + bonus_pp, new_pp_total + bonus_pp))

async def calculate_difficulty(context, *args, **kwargs):
    kwargs = utils.convert_kwargs(kwargs)
    if "m" in kwargs and kwargs["m"] in constants.mode_aliases.keys():
        mode = constants.modes[constants.mode_aliases[kwargs["m"]]]
    else:
        mode = "osu"
    use_calc = kwargs["usecalc"] if "usecalc" in kwargs else None
    
    #Parse mods
    if "mods" in kwargs:
        query_mods = utils.get_mods_from_string(kwargs["mods"])
    else:
        query_mods = []
    modsint = utils.mods_to_int(query_mods)
    
    if "b" in kwargs:
        response = osu_api_wrapper.get_beatmaps(**{"b":kwargs["b"], "mods":utils.ignore_irrelevant_mods(modsint)})
    elif context["message"].channel.id in utils.channel_id_to_active_beatmap_id:
        response = osu_api_wrapper.get_beatmaps(**{"b":utils.channel_id_to_active_beatmap_id[context["message"].channel.id], "mods":utils.ignore_irrelevant_mods(modsint)})
    else:
        return await context["koduck"].send_message(context["message"], content=settings.message_no_active_beatmap)
    
    if len(response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_beatmaps_no_result)
    else:
        beatmap_data = response[0]
        beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap_data["beatmap_id"], beatmap_data["last_update"])
        native_mode = utils.get_map_mode(beatmap_file_name)
        #Force native mode if not standard (because they're incompatible with each other)
        if native_mode != "0":
            mode = constants.modes[native_mode]
        result_fc = perf_calc_wrapper.calculate_pp(beatmap_file_name, mode=mode, mods=query_mods, use_calc=use_calc)
        title = "{} - {} ({}) [{}]".format(beatmap_data["artist"], beatmap_data["title"], beatmap_data["creator"], beatmap_data["version"])
        output_string = title
        if use_calc in constants.legacy_calcs:
            output_string += "\nStar Rating: {}".format(result_fc["star rating"])
            if "aim difficulty" in result_fc:
                output_string += "\nAim Difficulty: {}".format(result_fc["aim difficulty"])
            if "speed difficulty" in result_fc:
                output_string += "\nSpeed Difficulty: {}".format(result_fc["speed difficulty"])
            if "flashlight difficulty" in result_fc:
                output_string += "\nFlashlight Difficulty: {}".format(result_fc["flashlight difficulty"])
            if "stamina difficulty" in result_fc:
                output_string += "\nStamina Difficulty: {}".format(result_fc["stamina difficulty"])
            if "rhythm difficulty" in result_fc:
                output_string += "\nRhythm Difficulty: {}".format(result_fc["rhythm difficulty"])
            if "colour difficulty" in result_fc:
                output_string += "\nColour Difficulty: {}".format(result_fc["colour difficulty"])
            if "peak difficulty" in result_fc:
                output_string += "\nPeak Difficulty: {}".format(result_fc["peak difficulty"])
        else:
            output_string += "\nStar Rating: {}".format(result_fc["difficulty_attributes"]["star_rating"])
            if "aim_difficulty" in result_fc["difficulty_attributes"]:
                output_string += "\nAim Difficulty: {}".format(result_fc["difficulty_attributes"]["aim_difficulty"])
            if "speed_difficulty" in result_fc["difficulty_attributes"]:
                output_string += "\nSpeed Difficulty: {}".format(result_fc["difficulty_attributes"]["speed_difficulty"])
            if "flashlight_difficulty" in result_fc["difficulty_attributes"]:
                output_string += "\nFlashlight Difficulty: {}".format(result_fc["difficulty_attributes"]["flashlight_difficulty"])
            if "stamina_difficulty" in result_fc["difficulty_attributes"]:
                output_string += "\nStamina Difficulty: {}".format(result_fc["difficulty_attributes"]["stamina_difficulty"])
            if "rhythm_difficulty" in result_fc["difficulty_attributes"]:
                output_string += "\nRhythm Difficulty: {}".format(result_fc["difficulty_attributes"]["rhythm_difficulty"])
            if "colour_difficulty" in result_fc["difficulty_attributes"]:
                output_string += "\nColour Difficulty: {}".format(result_fc["difficulty_attributes"]["colour_difficulty"])
            if "peak_difficulty" in result_fc["difficulty_attributes"]:
                output_string += "\nPeak Difficulty: {}".format(result_fc["difficulty_attributes"]["peak_difficulty"])
        
        return await context["koduck"].send_message(context["message"], content=output_string)

async def calc_scroll_speeds(context, *args, **kwargs):
    if "b" in kwargs:
        response = osu_api_wrapper.get_beatmaps(**{"b":kwargs["b"]})
    elif context["message"].channel.id in utils.channel_id_to_active_beatmap_id:
        response = osu_api_wrapper.get_beatmaps(**{"b":utils.channel_id_to_active_beatmap_id[context["message"].channel.id]})
    else:
        return await context["koduck"].send_message(context["message"], content=settings.message_no_active_beatmap)
    
    if len(response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_beatmaps_no_result)
    else:
        beatmap_data = response[0]
        beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap_data["beatmap_id"], beatmap_data["last_update"])
        output_graph_file = "{}/{}_graph.png".format(settings.beatmaps_graphs_folder, beatmap_data["beatmap_id"])
        title = "{} - {} ({}) [{}]".format(beatmap_data["artist"], beatmap_data["title"], beatmap_data["creator"], beatmap_data["version"])
        
        map_parser = OsuBeatmapParser()
        osu_beatmap = map_parser.parse_from_filename(beatmap_file_name)
        scroll_speeds = osu_beatmap.calc_taiko_scroll_speeds()
        times = [x[0] / 1000 for x in scroll_speeds]
        values = [x[1] for x in scroll_speeds]
        
        min_value = math.floor(min(values) / 50) * 50
        max_value = math.ceil(max(values) / 50) * 50
        
        beatmap_graph_generator.generate_graph(times, [values], ["Scroll Speed"], output_graph_file, title=title, graph_title="Scroll Speed Graph", value_label="Scroll Speed", min_value=min_value, max_value=max_value, value_interval=50)
        utils.channel_id_to_active_beatmap_id[context["message"].channel.id] = beatmap_data["beatmap_id"]
        return await context["koduck"].send_message(context["message"], file=discord.File(open(output_graph_file, 'rb')))

async def calc_note_densities(context, *args, **kwargs):
    if "b" in kwargs:
        response = osu_api_wrapper.get_beatmaps(**{"b":kwargs["b"]})
    elif context["message"].channel.id in utils.channel_id_to_active_beatmap_id:
        response = osu_api_wrapper.get_beatmaps(**{"b":utils.channel_id_to_active_beatmap_id[context["message"].channel.id]})
    else:
        return await context["koduck"].send_message(context["message"], content=settings.message_no_active_beatmap)
    
    if len(response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_beatmaps_no_result)
    else:
        beatmap_data = response[0]
        beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap_data["beatmap_id"], beatmap_data["last_update"])
        output_graph_file = "{}/{}_graph.png".format(settings.beatmaps_graphs_folder, beatmap_data["beatmap_id"])
        title = "{} - {} ({}) [{}]".format(beatmap_data["artist"], beatmap_data["title"], beatmap_data["creator"], beatmap_data["version"])
        
        map_parser = OsuBeatmapParser()
        osu_beatmap = map_parser.parse_from_filename(beatmap_file_name)
        note_densities = osu_beatmap.calc_note_densities()
        times = [x[0] / 1000 for x in note_densities]
        values = [x[1] for x in note_densities]
        
        beatmap_graph_generator.generate_graph(times, [values], ["Note Density"], output_graph_file, title=title, graph_title="Note Density Graph", value_label="Note Density", value_interval=5)
        utils.channel_id_to_active_beatmap_id[context["message"].channel.id] = beatmap_data["beatmap_id"]
        return await context["koduck"].send_message(context["message"], file=discord.File(open(output_graph_file, 'rb')))

async def calc_pattern_complexities(context, *args, **kwargs):
    if "b" in kwargs:
        response = osu_api_wrapper.get_beatmaps(**{"b":kwargs["b"]})
    elif context["message"].channel.id in utils.channel_id_to_active_beatmap_id:
        response = osu_api_wrapper.get_beatmaps(**{"b":utils.channel_id_to_active_beatmap_id[context["message"].channel.id]})
    else:
        return await context["koduck"].send_message(context["message"], content=settings.message_no_active_beatmap)
    
    if len(response) == 0:
        return await context["koduck"].send_message(context["message"], content=settings.message_get_beatmaps_no_result)
    else:
        beatmap_data = response[0]
        beatmap_file_name = osu_api_wrapper.download_beatmap(beatmap_data["beatmap_id"], beatmap_data["last_update"])
        output_graph_file = "{}/{}_graph.png".format(settings.beatmaps_graphs_folder, beatmap_data["beatmap_id"])
        title = "{} - {} ({}) [{}]".format(beatmap_data["artist"], beatmap_data["title"], beatmap_data["creator"], beatmap_data["version"])
        
        map_parser = OsuBeatmapParser()
        osu_beatmap = map_parser.parse_from_filename(beatmap_file_name)
        pattern_complexities = osu_beatmap.calc_taiko_pattern_complexities()
        times = [x[0] / 1000 for x in pattern_complexities]
        values = [x[1] for x in pattern_complexities]
        
        beatmap_graph_generator.generate_graph(times, [values], ["Pattern Complexities"], output_graph_file, title=title, graph_title="Pattern Complexity Graph", value_label="Pattern Complexity", value_interval=5)
        utils.channel_id_to_active_beatmap_id[context["message"].channel.id] = beatmap_data["beatmap_id"]
        return await context["koduck"].send_message(context["message"], file=discord.File(open(output_graph_file, 'rb')))

###################
# BACKGROUND TASK #
###################
background_task_running = False
restart_background_task = False
async def background_task(koduck_instance):
    global background_task_running
    global restart_background_task
    
    if not settings.track_enabled:
        return
    if background_task_running:
        return
    background_task_running = True
    
    trackers = yadon.ReadTable(settings.track_table)
    for key in trackers.keys():
        if restart_background_task:
            continue
        try:
            player_id, mode_id = key.split("/")
            if len(trackers[key]) <= 3:
                continue
            channel_ids_and_settings = trackers[key][0].split("/")
            cached_rank = trackers[key][1]
            cached_pp = trackers[key][2]
            cached_top_score_ids = trackers[key][3:]
            top_score_history = yadon.ReadRowFromTable(settings.top_score_history_table, player_id)
            if top_score_history is None:
                top_score_history = []
            
            player = await osu_api_wrapper.get_user_v2_async(koduck_instance.aiohttp_session, user_id=player_id, mode=constants.mode_aliases_v2[mode_id])
            if not player:
                print("player {} not found".format(player_id))
                continue
            
            top_scores = await osu_api_wrapper.get_user_scores_v2_async(koduck_instance.aiohttp_session, user_id=player_id, type="best", mode=constants.mode_aliases_v2[mode_id])
            score_ids = [str(score["id"]) for score in top_scores]
            for i in range(len(top_scores)):
                top_score = top_scores[i]
                score_id = str(top_score["id"])
                if score_id not in cached_top_score_ids and score_id not in top_score_history:
                    for channel_id_and_settings in channel_ids_and_settings:
                        channel_id = channel_id_and_settings.split(":")[0]
                        num_scores = int(channel_id_and_settings.split(":")[1])
                        if (i+1 > num_scores):
                            continue
                        try:
                            the_channel = await koduck_instance.client.fetch_channel(channel_id)
                            await koduck_instance.send_message(
                                channel=the_channel,
                                content=settings.message_track_new_top.format(
                                    i+1,
                                    player["username"],
                                    constants.mode_aliases_v2[mode_id],
                                    cached_rank,
                                    player["statistics"]["global_rank"],
                                    cached_pp,
                                    player["statistics"]["pp"]),
                                embed=embed_formatters.format_single_score_embed_v2(top_score, top_score["user"], top_score["beatmap"]))
                            utils.channel_id_to_active_beatmap_id[the_channel.id] = top_score["beatmap_id"]
                        except (discord.NotFound, discord.Forbidden):
                            continue
                        new_top_score_history = list(set(top_score_history + [score_id]))
                        yadon.WriteRowToTable(settings.top_score_history_table, player_id, new_top_score_history)
            
            yadon.WriteRowToTable(settings.track_table, key, ["/".join(channel_ids_and_settings), player["statistics"]["global_rank"], player["statistics"]["pp"]] + score_ids)
            
            await asyncio.sleep(settings.track_cooldown)
        except Exception as e:
            background_task_running = False
            raise e
    background_task_running = False
    restart_background_task = False

settings.background_task = background_task