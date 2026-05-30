import statistics, time, requests, urllib3, os, math
from osu_replay_parser import OsuReplayParser
from osu_map_parser import OsuBeatmapParser
#import time

class OsuReplayAnalyzer:
    def __init__(self, map_file_name=None, replay_file_name=None, map_details=None, replay_details=None, force_hr=False, force_ez=False, apikey=""):
        #debug_file = open("debug5.txt", "w")
        #start_time = time.time()
        if replay_file_name:
            replay_parser = OsuReplayParser()
            replay_file = open(replay_file_name, "rb")
            replay_details = replay_parser.parse_from_file(replay_file)
            self.replay_details = replay_details
        elif not replay_details:
            raise ValueError("I need either a replay file name or a OsuReplayDetails object")
        
        if map_file_name:
            map_parser = OsuBeatmapParser()
            map_file = open(map_file_name, encoding="utf-8")
            map_details = map_parser.parse_from_file(map_file)
            self.map_details = map_details
        elif not map_details:
            raise ValueError("I need either a beatmap file name or a OsuBeatmapDetails object")
            
            #fetch beatmap from API
            '''
            get_beatmaps_response = requests.get(url="https://osu.ppy.sh/api/get_beatmaps", params={"h": replay_details.map_md5hash, "k": apikey}).json()
            if len(get_beatmaps_response) == 0:
                raise ValueError("osu API did not return any results for this replay's beatmap hash")
            
            beatmap_id = get_beatmaps_response[0]["beatmap_id"]
            filename = "maps/{}.osu".format(beatmap_id)
            if not os.path.exists(filename):                
                http = urllib3.PoolManager()
                download_beatmap_response = http.request("GET", "https://osu.ppy.sh/osu/{}".format(beatmap_id))
                beatmap_data = download_beatmap_response.data
                open(filename, "wb").write(beatmap_data).close()
            
            map_parser = OsuBeatmapParser()
            map_details = map_parser.parse_from_filename(filename)
            self.map_details = map_details
            '''
        
        #print(details.hit_objects[0].__dict__)
        #print(details.hit_objects[150].slider_details().__dict__)
        #print(details.hit_objects[150].slider_pos_at(23232, details.slider_velocity_at(23103), details.beat_length_at(23103)))
        #print(details.beat_length_at(60000))
        #print(details.hit_objects[176].slider_pos_at(27327, details.slider_velocity_at(27241), details.beat_length_at(27241)))
        '''
        stacked_notes = map_details.get_stacked_notes()
        for stack, positive in stacked_notes:
            print([note.__dict__ for note in stack])
            for i in range(len(stack)):
                if positive:
                    print(stack[i].stack_pos(i+1, map_details.cs, positive))
                else:
                    print(stack[i].stack_pos(len(stack)-i-1, map_details.cs, positive))
        '''
        
        if "HR" in replay_details.mods() or force_hr:
            map_details.enable_hr()
        
        if "EZ" in replay_details.mods() or force_ez:
            map_details.enable_ez()
        
        if replay_details.game_mode == 0:
            map_details.enable_stacking()
        
        hit_objects = map_details.hit_objects
        
        if replay_details.game_mode == 1:
            #convert if convert
            if map_details.game_mode == 0:
                map_details.convert_to_taiko()
                hit_objects = map_details.hit_objects
                '''
                debug_file = open("debug7.txt", "w")
                for hit_object in hit_objects:
                    asdf = hit_object.hit_sound_raw
                    if hit_object.hit_sound_whistle and not hit_object.hit_sound_clap:
                        asdf += 6
                    elif hit_object.hit_sound_whistle and hit_object.hit_sound_clap:
                        asdf -= 2
                    debug_file.write("256,192,{},{},{},0:0:0:0:\n".format(int(hit_object.offset), 1 if hit_object.type == "Circle" else hit_object.type, asdf))
                debug_file.close()
                '''
            #ignore sliders and spinners for now
            hit_objects = [hit_object for hit_object in hit_objects if hit_object.type not in ["Slider", "Spinner"]]
        def initialize_finisher(hit_object):
            return False if replay_details.game_mode == 1 and hit_object.hit_sound_finish else None
        hit_object_results = {h:(None, 0, 0, initialize_finisher(h)) for h in hit_objects} #(score, hit_error, aim_error, taiko_finisher_hit)
        num_finishers = len([x for x in hit_object_results.values() if x[3] is not None])
        perfect_finishers = 0
        
        key_statuses = {"K1": False, "K2": False, "M1": False, "M2": False}
        hit_errors = []
        aim_errors = []
        empty_taps = []
        #print("replay analyzer setup took {} seconds".format(time.time() - start_time))
        #print("replay has {} replay actions".format(len(replay_details.replay_data())))
        #start_time = time.time()
        #debug_file = open("debug8.txt", "w")
        for replay_action in replay_details.replay_data():
            #print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
            #print(replay_action.__dict__)
            
            key_activated = False
            activated_keys = []
            keys_pressed = replay_action.keys_pressed()
            for key in key_statuses.keys():
                if key in keys_pressed and not key_statuses[key]:
                    key_activated = True
                    activated_keys.append(key)
                key_statuses[key] = key in keys_pressed
            #debug_file.write("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n")
            #debug_file.write("{} | {} | {}\n".format(replay_action.offset, key_statuses, activated_keys))
            
            if not key_activated:
                continue
            
            visible_hit_objects = map_details.visible_hit_objects_at(replay_action.offset, mode=replay_details.game_mode)
            #print([x.__dict__ for x in visible_hit_objects])
            #ignore sliders and spinners in taiko
            if replay_details.game_mode == 1:
                visible_hit_objects = [hit_object for hit_object in visible_hit_objects if hit_object.type not in ["Slider", "Spinner"]]
            
            empty_tap = True
            for hit_object in visible_hit_objects:
                #debug_file.write("Checking object {} with result {}\n".format(hit_object.__dict__, hit_object_results[hit_object]))
                is_taiko_finisher = replay_details.game_mode == 1 and hit_object.hit_sound_finish
                #If object has already been judged
                if hit_object_results[hit_object][0] is not None:
                    #If object is a taiko finisher that wasn't fully hit yet
                    if is_taiko_finisher and hit_object_results[hit_object][3] == False:
                        #print("this object is a finisher!")
                        pass
                    else:
                        #debug_file.write("Skipping\n")
                        continue
                
                #Ignore spinners for now
                if hit_object.type == "Spinner":
                    hit_object_results[hit_object] = (300, 0, 0, False)
                    continue
                
                if key_activated:
                    if replay_details.game_mode == 0:
                        is_hit, aim_error = hit_object.check_hit_by_pos(replay_action.x_pos, replay_action.y_pos, map_details.cs)
                        if not is_hit:
                            continue
                    
                    result = hit_object.check_hit_by_time(replay_action.offset, map_details.od, mode=replay_details.game_mode)
                    if result is not None:
                        #print("object at {} got result {}".format(hit_object.offset, result))
                        #print(key_statuses)
                        hit_error = replay_action.offset - hit_object.offset
                        if replay_details.game_mode == 0:
                            aim_errors.append(aim_error)
                            hit_object_results[hit_object] = (result, hit_error, aim_error, False)
                        if replay_details.game_mode == 1:
                            hit, finisher_hit = hit_object.check_hit_taiko(activated_keys)
                            if not hit:
                                result = 0
                            #finisher second hit case
                            if hit_object_results[hit_object][0] is not None:
                                previous_hit_error = hit_object_results[hit_object][1]
                                if hit_error - previous_hit_error < 30 and hit:
                                    hit_object_results[hit_object] = (hit_object_results[hit_object][0], (previous_hit_error, hit_error), 0, True)
                                else:
                                    #debug_file.write("Skipping\n")
                                    continue
                            else:
                                if is_taiko_finisher and finisher_hit:
                                    perfect_finishers += 1
                                hit_object_results[hit_object] = (result, hit_error, 0, finisher_hit if is_taiko_finisher else None)
                            #debug_file.write("hit object at offset {} has been updated to {}\n".format(hit_object.offset, hit_object_results[hit_object]))
                            #print(hit_object.offset, hit_object_results[hit_object])
                        #debug_file.write("--------------------------------------------------------------------------------------------------------------\n")
                        #debug_file.write(str(replay_action.__dict__) + "\n")
                        #debug_file.write(str(key_statuses) + "\n")
                        #debug_file.write(str(activated_keys) + "\n")
                        #debug_file.write(str(hit_object.__dict__) + "\n")
                        #debug_file.write(str(hit_error) + "\n")
                        #debug_file.write(str(hit_object_results[hit_object]) + "\n")
                        if result > 0:
                            hit_errors.append(hit_error)
                        empty_tap = False
                        break #One object at a time
            if empty_tap:
                empty_taps.append(replay_action)
        #print("processing replay actions took {} seconds".format(time.time() - start_time))
        #debug_file.close()
        
        self.mod_multiplier = 1
        mods = replay_details.mods()
        if "HR" in mods:
            self.mod_multiplier *= 1.06
        if "HD" in mods:
            self.mod_multiplier *= 1.06
        if "DT" in mods:
            self.mod_multiplier *= 1.12
        if "FL" in mods:
            self.mod_multiplier *= 1.12
        if "EZ" in mods:
            self.mod_multiplier *= 0.5
        if "HT" in mods:
            self.mod_multiplier *= 0.3
        
        player_raw_score = 0
        autoplay_raw_score = 0
        player_current_combo = 0
        autoplay_current_combo = 0
        current_combo_score_v2 = 0
        autoplay_combo_score_v2 = 0
        current_combo_score_v3 = 0
        autoplay_combo_score_v3 = 0
        self.combo_score_v2 = 0
        self.combo_score_v3 = 0
        self.accuracy_score = 0
        self.bonus_score = 0
        self.score_v1 = 0
        self.player_max_combo = 0
        #debug_file = open("debug9.txt", "w")
        if replay_details.game_mode == 1:
            for k,v in hit_object_results.items():
                autoplay_raw_score += 300
                if v[0] is not None and v[0] > 0:
                    actual_score = (300 + (min(math.floor(player_current_combo / 10), 10) * math.floor(80 * self.mod_multiplier))) * (1.2 if map_details.is_kiai_at(k.offset) else 1) * (v[0] / 300) * (2 if v[3] else 1)
                    self.score_v1 += actual_score
                    #print("offset {} raw_score {} actual_score {} score_v1 {}".format(k.offset, v[0], actual_score, self.score_v1))
                    player_raw_score += v[0]
                    player_current_combo += 1
                else:
                    player_current_combo = 0
                autoplay_current_combo += 1
                self.player_max_combo = max(self.player_max_combo, player_current_combo)
                
                finisher_multiplier = 7.9 if v[3] is not None else 1
                if v[0] is not None and v[0] > 0:
                    current_combo_score_v2 += v[0] * min(max(0.5, math.log(player_current_combo, 4)), math.log(400, 4)) * (finisher_multiplier if v[3] else 1)
                    current_combo_score_v3 += v[0] * min(max(0.5, math.log(player_current_combo, 4)), math.log(400, 4))
                    self.bonus_score += 350 if v[3] else 0
                autoplay_combo_score_v2 += 300 * min(max(0.5, math.log(autoplay_current_combo, 4)), math.log(400, 4)) * finisher_multiplier
                autoplay_combo_score_v3 += 300 * min(max(0.5, math.log(autoplay_current_combo, 4)), math.log(400, 4))
                
                #debug_file.write("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n")
                #debug_file.write(f"combo {player_current_combo} / {autoplay_current_combo}\n")
                #debug_file.write(f"combo score {current_combo_score} / {autoplay_combo_score}\n")
            #debug_file.close()
            
            self.combo_score_v2 = 250000 * (current_combo_score_v2 / autoplay_combo_score_v2)
            self.combo_score_v3 = 250000 * (current_combo_score_v3 / autoplay_combo_score_v3)
            self.accuracy_score = 750000 * pow(player_raw_score / autoplay_raw_score, 3.6)
            #print("player_raw_score {}".format(player_raw_score))
            #print("autoplay_raw_score {}".format(autoplay_raw_score))
            #print("player_max_combo {}".format(player_max_combo))
            #print("autoplay_max_combo {}".format(autoplay_current_combo))
            #print("current_combo_score {}".format(current_combo_score))
            #print("autoplay_combo_score {}".format(autoplay_combo_score))
            #print("v2_score {} + {} = {}".format(combo_score, accuracy_score, combo_score + accuracy_score))
        
        missed_objects = [x for x in hit_object_results.keys() if hit_object_results[x][0] is None or hit_object_results[x][0] == 0]
        #aaaa = [hit_object_results[x][0] for x in hit_object_results.keys() if hit_object_results[x][0] is None or hit_object_results[x][0] == 0]
        #print([x.__dict__ for x in missed_objects])
        #print(aaaa)
        #print([x.__dict__ for x in empty_taps])
        
        negative_errors = list(filter(lambda x: x < 0, hit_errors))
        positive_errors = list(filter(lambda x: x >= 0, hit_errors))
        
        '''
        print("Accuracy:")
        print("Error: {:0.2f}ms - {:0.2f}ms".format(statistics.mean(negative_errors), statistics.mean(positive_errors)))
        print("Unstable Rate: {:0.2f}".format(statistics.stdev(hit_errors) * 10))
        print("Aim Error: {:0.2f}px".format(statistics.mean(aim_errors)))
        '''
        #print("Perfect Finishers: {}/{}".format(perfect_finishers, num_finishers))
        
        self.hit_errors = hit_errors
        self.hit_error_negative = statistics.mean(negative_errors) if negative_errors else 0
        self.hit_error_positive = statistics.mean(positive_errors) if positive_errors else 0
        self.unstable_rate = statistics.pstdev(hit_errors) * 10
        self.aim_error = statistics.mean(aim_errors) if aim_errors else 0
        self.hit_object_results = hit_object_results
        
        #debug_file.close()