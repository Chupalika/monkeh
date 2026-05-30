import datetime, os, requests, urllib3, json
import settings, yadon

# Nothing special, just logging api calls
def log(endpoint, params):
    timestamp = timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    with open("osu_api_log.txt", "a", encoding="utf8") as file:
        file.write("\n{}\t{}\t".format(timestamp, endpoint, params))

############
# OSU! API #
############
async def get_user_async(params, aiohttp_session):
    #log("get_user", params)
    params["k"] = settings.osu_api_key
    async with aiohttp_session.get(settings.osu_api_url + "get_user", params=params) as response:
        if response.status > 400:
            raise Exception("get_user failed with {} error".format(response.status))
        else:
            return await response.json()

async def get_user_best_async(params, aiohttp_session):
    #log("get_user_best", params)
    params["k"] = settings.osu_api_key
    params["limit"] = 100
    async with aiohttp_session.get(settings.osu_api_url + "get_user_best", params=params) as response:
        if response.status > 400:
            raise Exception("get_user_best failed with {} error".format(response.status))
        else:
            return await response.json()

def get_user(**kwargs):
    #log("get_user", kwargs)
    kwargs["k"] = settings.osu_api_key
    response = requests.get(url=settings.osu_api_url + "get_user", params=kwargs)
    if not response.ok:
        raise Exception("get_user failed with {} error".format(response.status_code))
    else:
        return response.json()

def get_user_recent(**kwargs):
    #log("get_user_recent", kwargs)
    kwargs["k"] = settings.osu_api_key
    kwargs["limit"] = 50
    response = requests.get(url=settings.osu_api_url + "get_user_recent", params=kwargs)
    if not response.ok:
        raise Exception("get_user_recent failed with {} error".format(response.status_code))
    else:
        return response.json()

def get_beatmaps(**kwargs):
    #log("get_beatmaps", kwargs)
    kwargs["k"] = settings.osu_api_key
    response = requests.get(url=settings.osu_api_url + "get_beatmaps", params=kwargs)
    if not response.ok:
        raise Exception("get_beatmaps failed with {} error".format(response.status_code))
    else:
        return response.json()

def get_scores(**kwargs):
    #log("get_scores", kwargs)
    kwargs["k"] = settings.osu_api_key
    kwargs["limit"] = 100
    response = requests.get(url=settings.osu_api_url + "get_scores", params=kwargs)
    if not response.ok:
        raise Exception("get_scores failed with {} error".format(response.status_code))
    else:
        return response.json()

def get_user_best(**kwargs):
    #log("get_user_best", kwargs)
    kwargs["k"] = settings.osu_api_key
    kwargs["limit"] = 100
    response = requests.get(url=settings.osu_api_url + "get_user_best", params=kwargs)
    if not response.ok:
        raise Exception("get_user_best failed with {} error".format(response.status_code))
    else:
        return response.json()

def get_replay(**kwargs):
    #log("get_replay", kwargs)
    kwargs["k"] = settings.osu_api_key
    response = requests.get(url=settings.osu_api_url + "get_replay", params=kwargs)
    if not response.ok:
        raise Exception("get_replay failed with {} error".format(response.status_code))
    else:
        return response.json()

###############
# OSU! API v2 #
###############
oauth_token = ""
expire_time = None

def oauth_refresh():
    global oauth_token
    global expire_time
    if not expire_time or expire_time <= datetime.datetime.utcnow():
        token_response = requests.post(url=settings.osu_api_v2_token_url, data={"grant_type": "client_credentials", "client_id": settings.client_id, "client_secret": settings.client_secret, "scope": "public"}).json()
        oauth_token = token_response["access_token"]
        expire_time = datetime.datetime.utcnow() + datetime.timedelta(0, token_response["expires_in"])

def get_user_v2(user_id, mode=None):
    global oauth_token
    oauth_refresh()
    url = settings.osu_api_v2_url + "users/{}{}".format(user_id, "/{}".format(mode) if mode else "")
    #log(url, "")
    return requests.get(url=url, headers={"Authorization": "Bearer {}".format(oauth_token)}).json()

async def get_user_v2_async(aiohttp_session, user_id, mode=None):
    global oauth_token
    oauth_refresh()
    url = settings.osu_api_v2_url + "users/{}{}".format(user_id, "/{}".format(mode) if mode else "")
    #log(url, "")
    async with aiohttp_session.get(url, headers={"Authorization": "Bearer {}".format(oauth_token)}) as response:
        if response.status == 404:
            return None
        elif response.status > 400:
            raise Exception("get_user failed with {} error".format(response.status))
        else:
            return await response.json()

async def get_users_v2_async(aiohttp_session, user_ids):
    global oauth_token
    oauth_refresh()
    url = settings.osu_api_v2_url + "users?"
    query_parameters = ""
    for user_id in user_ids:
        query_parameters += "&ids[]={}".format(user_id)
    url += query_parameters[1:]
    #log(url, "")
    async with aiohttp_session.get(url, headers={"Authorization": "Bearer {}".format(oauth_token)}) as response:
        if response.status == 404:
            return None
        elif response.status > 400:
            raise Exception("get_users failed with {} error".format(response.status))
        else:
            return await response.json()

def get_user_scores_v2(user_id, type, include_fails=False, mode=None, limit=settings.query_result_limit):
    global oauth_token
    oauth_refresh()
    url = settings.osu_api_v2_url + "users/{}/scores/{}?limit={}{}{}".format(user_id, type, limit, "&mode={}".format(mode) if mode else "", "&include_fails=1" if include_fails else "")
    #log(url, "")
    response = requests.get(url=url, headers={"Authorization": "Bearer {}".format(oauth_token)}).json()
    if "error" in response:
        raise Exception("get_user_scores failed with {} error".format(response["error"]))
    else:
        return response

async def get_user_scores_v2_async(aiohttp_session, user_id, type, include_fails=False, mode=None, limit=settings.query_result_limit):
    global oauth_token
    oauth_refresh()
    url = settings.osu_api_v2_url + "users/{}/scores/{}?limit={}{}{}".format(user_id, type, limit, "&mode={}".format(mode) if mode else "", "&include_fails=1" if include_fails else "")
    #log(url, "")
    async with aiohttp_session.get(url, headers={"Authorization": "Bearer {}".format(oauth_token), "x-api-version": "20220705"}) as response:
    #async with aiohttp_session.get(url, headers={"Authorization": "Bearer {}".format(oauth_token)}) as response:
        if response.status == 404:
            return None
        elif response.status > 400:
            raise Exception("get_user_scores failed with {} error".format(response.status))
        else:
            #print(await response.json())
            return await response.json()

def get_beatmap_v2(beatmap_id):
    global oauth_token
    oauth_refresh()
    url = settings.osu_api_v2_url + "beatmaps/{}".format(beatmap_id)
    #log(url, "")
    response = requests.get(url=url, headers={"Authorization": "Bearer {}".format(oauth_token)}).json()
    if "error" in response:
        raise Exception("get_beatmap failed with {} error".format(response["error"]))
    else:
        return response

async def get_beatmap_v2_async(aiohttp_session, beatmap_id):
    global oauth_token
    oauth_refresh()
    url = settings.osu_api_v2_url + "beatmaps/{}".format(beatmap_id)
    #log(url, "")
    async with aiohttp_session.get(url, headers={"Authorization": "Bearer {}".format(oauth_token)}) as response:
        if response.status == 404:
            return None
        elif response.status > 400:
            raise Exception("get_beatmap failed with {} error".format(response.status))
        else:
            return await response.json()

async def lookup_beatmap_v2_async(aiohttp_session, checksum=None, filename=None, beatmap_id=None):
    global oauth_token
    oauth_refresh()
    url = settings.osu_api_v2_url + "beatmaps/lookup?{}{}{}".format("&checksum={}".format(checksum) if checksum else "", "&filename={}".format(filename) if filename else "", "&id={}".format(beatmap_id) if beatmap_id else "")
    #log(url, "")
    async with aiohttp_session.get(url, headers={"Authorization": "Bearer {}".format(oauth_token)}) as response:
        if response.status == 404:
            return None
        elif response.status > 400:
            raise Exception("lookup_beatmap failed with {} error".format(response.status))
        else:
            return await response.json()

def get_beatmap_attributes_v2(beatmap_id, mode=None, mods=None):
    global oauth_token
    oauth_refresh()
    url = settings.osu_api_v2_url + "beatmaps/{}/attributes?{}{}".format(beatmap_id, "&ruleset={}".format(mode) if mode else "", "&mods={}".format(mods) if mods else "")
    #log(url, "")
    response = requests.get(url=url, headers={"Authorization": "Bearer {}".format(oauth_token)}).json()
    if "error" in response:
        raise Exception("get_beatmap_attributes failed with {} error".format(response["error"]))
    else:
        return response

async def get_beatmap_attributes_v2_async(aiohttp_session, beatmap_id, mode=None, mods=None):
    global oauth_token
    oauth_refresh()
    url = settings.osu_api_v2_url + "beatmaps/{}/attributes".format(beatmap_id)
    body = {}
    if mode:
        body["ruleset"] = mode
    if mods:
        body["mods"] = mods
    #log(url, "")
    async with aiohttp_session.post(url, data=body, headers={"Authorization": "Bearer {}".format(oauth_token)}) as response:
        if response.status == 404:
            return None
        elif response.status > 400:
            raise Exception("get_beatmap_attributes failed with {} error".format(response.status))
        else:
            return await response.json()

async def get_beatmap_score_v2_async(aiohttp_session, beatmap_id, user_id, mode=None, mods=None):
    global oauth_token
    oauth_refresh()
    url = settings.osu_api_v2_url + "beatmaps/{}/scores/users/{}?{}{}".format(beatmap_id, user_id, "&mode={}".format(mode) if mode else "", "&mods={}".format(mods) if mods else "")
    #log(url, "")
    async with aiohttp_session.get(url, headers={"Authorization": "Bearer {}".format(oauth_token), "x-api-version": "20220705"}) as response:
    #async with aiohttp_session.get(url, headers={"Authorization": "Bearer {}".format(oauth_token)}) as response:
        if response.status == 404:
            return None
        elif response.status > 400:
            raise Exception("get_beatmap_score failed with {} error".format(response.status))
        else:
            return await response.json()

async def get_beatmap_scores_v2_async(aiohttp_session, beatmap_id, user_id, mode=None):
    global oauth_token
    oauth_refresh()
    url = settings.osu_api_v2_url + "beatmaps/{}/scores/users/{}/all?{}".format(beatmap_id, user_id, "&mode={}".format(mode) if mode else "")
    #log(url, "")
    async with aiohttp_session.get(url, headers={"Authorization": "Bearer {}".format(oauth_token), "x-api-version": "20220705"}) as response:
    #async with aiohttp_session.get(url, headers={"Authorization": "Bearer {}".format(oauth_token)}) as response:
        if response.status == 404:
            return None
        elif response.status > 400:
            raise Exception("get_beatmap_scores failed with {} error".format(response.status))
        else:
            #print(await response.json())
            return await response.json()

async def get_rankings_v2_async(aiohttp_session, mode, type):
    global oauth_token
    oauth_refresh()
    url = settings.osu_api_v2_url + "rankings/{}/{}".format(mode, type)
    #log(url, "")
    response = requests.get(url=url, headers={"Authorization": "Bearer {}".format(oauth_token)}).json()
    if "error" in response:
        raise Exception("get_rankings failed with {} error".format(response["error"]))
    else:
        return response

async def get_score_v2_async(aiohttp_session, score_id):
    global oauth_token
    oauth_refresh()
    url = settings.osu_api_v2_url + "scores/{}".format(score_id)
    response = requests.get(url=url, headers={"Authorization": "Bearer {}".format(oauth_token)}).json()
    if "error" in response:
        raise Exception("get_score failed with {} error".format(response["error"]))
    else:
        return response

#Doesn't work right now
async def get_replay_v2_async(aiohttp_session, score_id):
    global oauth_token
    oauth_refresh()
    url = settings.osu_api_v2_url + "scores/{}/download".format(score_id)
    try:
        response = requests.get(url=url, headers={"Authorization": "Bearer {}".format(oauth_token)})
        response = response.json()
        raise Exception("get_replay failed with {} error".format(response["error"]))
    except json.JSONDecodeError:
        pass
    return response.content

async def get_match_v2_async(aiohttp_session, match_id):
    global oauth_token
    oauth_refresh()
    url = settings.osu_api_v2_url + "matches/{}".format(match_id)
    async with aiohttp_session.get(url, headers={"Authorization": "Bearer {}".format(oauth_token), "x-api-version": "20220705"}) as response:
        if response.status == 404:
            return None
        elif response.status > 400:
            raise Exception("get_match failed with {} error".format(response.status))
        else:
            #print(await response.json())
            return await response.json()

########
# MISC #
########
#Checks if beatmap is already downloaded and checks if last_updated is not more recent than stored last_updated, downloads beatmap if these checks fail
def download_beatmap(id, last_updated=None):
    file_name = "{}/{}.osu".format(settings.beatmaps_download_folder, id)
    stored_timestamp = yadon.ReadRowFromTable(settings.beatmaps_timestamp_table, id)
    stored_timestamp_datetime = datetime.datetime.strptime(stored_timestamp[0], settings.timestamp_format) if stored_timestamp else None
    #make everything utc
    if stored_timestamp_datetime:
        stored_timestamp_datetime = stored_timestamp_datetime.replace(tzinfo=datetime.timezone.utc)
    #iso format (from v2 api)
    try:
        last_updated_datetime = datetime.datetime.strptime(last_updated, settings.timestamp_format_v2) if last_updated else None
    #weird format (from v1 api, assumed to be utc timezone)
    except ValueError:
        last_updated_datetime = datetime.datetime.strptime(last_updated, settings.timestamp_format) if last_updated else None
        if last_updated_datetime:
            last_updated_datetime = last_updated_datetime.replace(tzinfo=datetime.timezone.utc)
    
    #sometimes an empty file gets downloaded. no clue why that happens but just redownload
    if (stored_timestamp_datetime is None) or (last_updated_datetime is None) or (last_updated_datetime > stored_timestamp_datetime or not os.path.exists(file_name)) or os.path.getsize(file_name) == 0:
        url = "https://osu.ppy.sh/osu/{}".format(id)
        #log(url, "")
        http = urllib3.PoolManager()
        
        response = http.request("GET", url)
        with open(file_name, "wb") as file:
            file.write(response.data)
        
        #retry once if empty file got downloaded
        if os.path.getsize(file_name) == 0:
            response = http.request("GET", url)
            with open(file_name, "wb") as file:
                file.write(response.data)
        
        if last_updated_datetime is not None:
            yadon.WriteRowToTable(settings.beatmaps_timestamp_table, id, [last_updated_datetime.strftime(settings.timestamp_format)])
    return file_name
    #return str(response.data).replace("\\r\\n", "\n")

#doesn't work for now (returns an html document instead of a replay)
def download_replay(id):
    file_name = "{}/{}.osr".format(settings.replays_folder, id)
    if not os.path.exists(file_name):
        url = "https://osu.ppy.sh/scores/{}/download".format(id)
        #log(url, "")
        http = urllib3.PoolManager()
        response = http.request("GET", url)
        open(file_name, "wb").write(response.data)
    return file_name