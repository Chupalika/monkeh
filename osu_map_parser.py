import math, bezier, struct, re

class OsuBeatmapDetails:
    def __init__(self):
        self.file_format_version = 0
        #General
        self.audio_file_name = ""
        self.audio_lead_in = 0
        self.preview_time = -1
        self.countdown = 0
        self.sample_set = "Normal"
        self.stack_leniency = 0
        self.game_mode = 0
        self.letterbox_in_breaks = 0
        self.widescreen_storyboard = 0
        #Editor
        self.bookmarks = []
        self.distance_spacing = 1
        self.beat_divisor = 4
        self.grid_size = 4
        self.timeline_zoom = 1
        #Metadata
        self.title = ""
        self.title_unicode = ""
        self.artist = ""
        self.artist_unicode = ""
        self.mapper_name = ""
        self.difficulty_name = ""
        self.source = ""
        self.tags = []
        self.beatmap_id = 0
        self.beatmap_set_id = 0
        #Difficulty
        self.hp = 0
        self.cs = 0
        self.od = 0
        self.ar = 0
        self.sv = 0
        self.str = 0
        #the rest
        self.events_string = ""
        self.timing_points = [] #List of OsuTimingPoint
        self.colors_string = ""
        self.hit_objects = [] #List of OsuHitObject
    
    def beat_length_at(self, offset):
        if len(self.timing_points) > 0:
            ans = self.timing_points[0].beat_length if self.timing_points[0].uninherited else 0
        else:
            return 0
        
        for timing_point in self.timing_points:
            if timing_point.offset > offset:
                return ans
            if timing_point.uninherited:
                ans = timing_point.beat_length
        return ans
    
    def bpm_at(self, offset):
        return 60000 / self.beat_length_at(offset)
    
    def slider_velocity_at(self, offset):
        sv_multiplier = 1
        for timing_point in self.timing_points:
            if timing_point.offset > offset:
                break
            if timing_point.uninherited:
                sv_multiplier = 1
            else:
                sv_multiplier = 1 / (timing_point.beat_length * -0.01)
        return sv_multiplier * self.sv
    
    #The time before a hit object's offset when the hit object is visible
    def get_approach_window(self):
        if self.ar < 5:
            return 1200 + (600 * (5 - self.ar) / 5)
        elif self.ar == 5:
            return 1200
        else:
            return 1200 - (750 * (self.ar - 5) / 5)
    
    def visible_hit_objects_at(self, offset, mode=0):
        preempt = self.get_approach_window()
        ans = []
        if mode == 0:
            miss_window = 400
        elif mode == 1:
            miss_window = 135 - (6.5 * self.od)
        else:
            raise ValueError("Unsupported or unknown game mode: {}".format(mode))
        for hit_object in self.hit_objects:
            if (hit_object.offset - preempt) <= offset and hit_object.offset + miss_window >= offset:
                ans.append(hit_object)
        return ans
    
    def is_kiai_at(self, offset):
        if len(self.timing_points) > 0:
            ans = self.timing_points[0].kiai if not self.timing_points[0].uninherited else False
        else:
            return False
        
        for timing_point in self.timing_points:
            if timing_point.offset > offset:
                return ans
            if not timing_point.uninherited:
                ans = timing_point.kiai
        return ans
    
    #I am not sure if I have the stacking logic completely correct
    def get_stacked_notes(self):
        approach_window = self.get_approach_window()
        sl_window = approach_window * self.stack_leniency
        
        stacks = []
        notes_by_pos = {}
        slider_ends = []
        
        for hit_object in self.hit_objects:
            if hit_object.type in ["Circle", "Slider"]:
                key = "{},{}".format(hit_object.x_pos, hit_object.y_pos)
                try:
                    notes_by_pos[key].append(hit_object)
                except KeyError:
                    notes_by_pos[key] = [hit_object]
                if hit_object.type == "Slider":
                    slider_ends.append(hit_object.slider_end(self.slider_velocity_at(hit_object.offset), self.beat_length_at(hit_object.offset)))
        for key in notes_by_pos.keys():
            notes = notes_by_pos[key]
            if len(notes) < 2:
                continue
            stack = []
            for i in range(len(notes) - 1):
                object1 = notes[i]
                object2 = notes[i+1]
                time_delta = object2.offset - object1.offset
                if time_delta <= sl_window:
                    stack.append(object1)
                    if i == len(notes) - 2:
                        stack.append(object2)
                        stacks.append(stack)
                elif stack:
                    stack.append(object1)
                    stacks.append(stack)
                    stack = []
        
        ans = []
        for stack in stacks:
            first_note = stack[0]
            found_slider_end = False
            for slider_end in slider_ends:
                x, y, offset = slider_end
                time_delta = first_note.offset - offset
                if int(x) == first_note.x_pos and int(y) == first_note.y_pos and time_delta <= sl_window:
                    ans.append((stack, True))
                    found_slider_end = True
                    break
            if not found_slider_end:
                ans.append((stack, False))
        return ans
    
    #Automatically calculates and sets all stacked objects altered positions
    #This should definitely be run if analyzing the beatmap from player perspective (i.e. a replay)
    def enable_stacking(self):
        if self.game_mode != 0:
            return
        stacked_notes = self.get_stacked_notes()
        for stack, positive in stacked_notes:
            for i in range(len(stack)):
                note = stack[i]
                stack_height = i+1 if positive else len(stack)-i-1
                new_x, new_y = note.stack_pos(stack_height, self.cs, positive)
                note.x_pos = new_x
                note.y_pos = new_y
    
    def enable_hr(self):
        self.hp = min(self.hp * 1.4, 10)
        self.cs = min(self.cs * 1.3, 10)
        self.od = min(self.od * 1.4, 10)
        self.ar = min(self.ar * 1.4, 10)
        for hit_object in self.hit_objects:
            hit_object.y_pos = hit_object.y_pos + ((192 - hit_object.y_pos) * 2)
    
    def enable_ez(self):
        self.hp = self.hp * 0.5
        self.cs = self.cs * 0.5
        self.od = self.od * 0.5
        self.ar = self.ar * 0.5
    
    def change_speed(self, multiplier, change_od=True, game_mode=None):
        self.preview_time = self.preview_time / multiplier
        if not game_mode:
            game_mode = self.game_mode
        
        for timing_point in self.timing_points:
            timing_point.offset = timing_point.offset / multiplier
            timing_point.beat_length = timing_point.beat_length / multiplier
        
        for hit_object in self.hit_objects:
            hit_object.offset = hit_object.offset / multiplier
            if hit_object.type == "Slider":
                hit_object.slider_details.length = hit_object.slider_details.length / multiplier
            if hit_object.type == "Spinner":
                hit_object.spinner_end_offset = hit_object.spinner_end_offset / multiplier
        
        #scaled to 300 hit window - will not be accurate for 100 hit window (to do this properly, the speed itself must be adjusted, not the od)
        if change_od and game_mode == 0:
            self.od = 26.5 - ((26.5 - self.od) / multiplier)
        if change_od and game_mode == 1:
            self.od = 16.5 - ((16.5 - self.od) / multiplier)
    
    def convert_to_taiko(self):
        if self.game_mode == 1:
            raise ValueError("This map is already a Taiko map!")
        elif self.game_mode != 0:
            raise ValueError("Cannot convert a non-standard map")
        
        # From osu's TaikoBeatmapConverter
        # Some numbers are converted to 32 bit float (intentional floating point error as done in osu)
        osu_base_scoring_distance = struct.unpack('f', struct.pack('f', 100))[0]
        velocity_multiplier = struct.unpack('f', struct.pack('f', 1.4))[0]
        ans = []
        for hit_object in self.hit_objects:
            if hit_object.type == "Slider":
                #print("@@@@@@@@@@@@@@@@@@@@@@@")
                #print("slider at offset {}".format(hit_object.offset))
                adjusted_length = hit_object.slider_details.length * hit_object.slider_details.num_slides * velocity_multiplier
                
                def clamp(n, min, max): 
                    if n < min:
                        return min
                    elif n > max:
                        return max
                    else:
                        return n
                
                sv = (self.slider_velocity_at(hit_object.offset) / self.sv)
                num = -100 / sv
                num2 = struct.unpack('f', struct.pack('f', 0 - num))[0]
                num3 = clamp(num2, 10, 10000) / 100 if num < 0 else 1;
                beat_length = self.beat_length_at(hit_object.offset) * num3
                #print("beat_length #1 {}".format(beat_length))
                
                slider_scoring_point_distance = osu_base_scoring_distance * (self.sv * velocity_multiplier) / self.str
                taiko_velocity = slider_scoring_point_distance * self.str
                taiko_duration = int(adjusted_length / taiko_velocity * beat_length)
                osu_velocity = taiko_velocity * (1000 / beat_length)
                if self.file_format_version >= 8:
                    beat_length = self.beat_length_at(hit_object.offset)
                tick_spacing = min(beat_length / self.str, taiko_duration / hit_object.slider_details.num_slides)
                
                #print("adjusted_length {}".format(adjusted_length))
                #print("beat_length #2 {}".format(beat_length))
                #print("taiko_velocity {}".format(taiko_velocity))
                #print("taiko_duration {}".format(taiko_duration))
                #print("tick_spacing {}".format(tick_spacing))
                #print("{} < {}".format(adjusted_length / osu_velocity * 1000, 2 * beat_length))
                if tick_spacing > 0 and adjusted_length / osu_velocity * 1000 < 2 * beat_length:
                    #print("THIS SLIDER GETS CONVERTED")
                    if hit_object.slider_details.edge_sounds_raw:
                        hit_sounds_raw = hit_object.slider_details.edge_sounds_raw.split("|")
                    else:
                        hit_sounds_raw = [0 for x in range(hit_object.slider_details.num_slides + 1)]
                    current_offset = hit_object.offset
                    i = 0
                    while current_offset < hit_object.offset + taiko_duration + tick_spacing / 8:
                        hit_sound_raw = int(hit_sounds_raw[i])
                        new_object = OsuHitObject()
                        new_object.x_pos = hit_object.x_pos
                        new_object.y_pos = hit_object.y_pos
                        new_object.offset = current_offset
                        new_object.type = "Circle"
                        new_object.type_raw &= ~(1 << 1)
                        new_object.type_raw |= 1
                        new_object.hit_sound_raw = hit_sound_raw
                        if hit_sound_raw & 8 == 8:
                            new_object.hit_sound_clap = True
                        if hit_sound_raw & 4 == 4:
                            new_object.hit_sound_finish = True
                        if hit_sound_raw & 2 == 2:
                            new_object.hit_sound_whistle = True
                        if hit_sound_raw & 1 == 1:
                            new_object.hit_sound_normal = True
                        #print("converted circle at offset {}".format(current_offset))
                        ans.append(new_object)
                        
                        i = (i + 1) % len(hit_sounds_raw)
                        current_offset += tick_spacing
                else:
                    ans.append(hit_object)
            else:
                ans.append(hit_object)
        self.hit_objects = ans
        self.game_mode = 1
    
    def normalize_sv(self, normal_bpm):
        new_timing_points = []
        current_bpm = None
        for timing_point in self.timing_points:
            new_timing_point = OsuTimingPoint()
            new_timing_point.offset = timing_point.offset
            new_timing_point.meter = timing_point.meter
            new_timing_point.sample_set = timing_point.sample_set
            new_timing_point.sample_index = timing_point.sample_index
            new_timing_point.volume = timing_point.volume
            new_timing_point.effects = timing_point.effects
            new_timing_point.kiai = timing_point.kiai

            # Adjust inheriting point SV to match the normal bpm
            if not timing_point.uninherited:
                ratio = normal_bpm / current_bpm
                if ratio > 1.001 or ratio < 0.999:
                    new_timing_point.beat_length = timing_point.beat_length / (ratio)
                else:
                    new_timing_point.beat_length = timing_point.beat_length
                new_timing_points.append(new_timing_point)
            # Create a new inheriting point at timing points with SV multiplier to match the normal bpm
            else:
                new_timing_points.append(timing_point)
                current_bpm = 60000 / timing_point.beat_length
                inheriting_point_exists = next((x for x in self.timing_points if x.offset == timing_point.offset and not x.uninherited), None)
                if inheriting_point_exists:
                    continue
                ratio = normal_bpm / current_bpm
                if ratio > 1.001 or ratio < 0.999:
                    new_timing_point.beat_length = -100 / (ratio)
                    new_timing_points.append(new_timing_point)
        
        self.timing_points = new_timing_points
    
    def export(self, file_name):
        output_file = open(file_name, "w", encoding="utf-8")
        output_file.write("osu file format v{}\n".format(self.file_format_version))
        
        output_file.write("\n[General]\n")
        output_file.write("AudioFilename: {}\n".format(self.audio_file_name))
        output_file.write("AudioLeadIn: {}\n".format(self.audio_lead_in))
        output_file.write("PreviewTime: {}\n".format(self.preview_time))
        output_file.write("Countdown: {}\n".format(self.countdown))
        output_file.write("SampleSet: {}\n".format(self.sample_set))
        output_file.write("StackLeniency: {}\n".format(self.stack_leniency))
        output_file.write("Mode: {}\n".format(self.game_mode))
        output_file.write("LetterboxInBreaks: {}\n".format(self.letterbox_in_breaks))
        output_file.write("WidescreenStoryboard: {}\n".format(self.widescreen_storyboard))
        
        output_file.write("\n[Editor]\n")
        output_file.write("Bookmarks: {}\n".format(",".join([str(x) for x in self.bookmarks])))
        output_file.write("DistanceSpacing: {}\n".format(self.distance_spacing))
        output_file.write("BeatDivisor: {}\n".format(self.beat_divisor))
        output_file.write("GridSize: {}\n".format(self.grid_size))
        output_file.write("TimelineZoom: {}\n".format(self.timeline_zoom))
        
        output_file.write("\n[Metadata]\n")
        output_file.write("Title: {}\n".format(self.title))
        output_file.write("TitleUnicode: {}\n".format(self.title_unicode))
        output_file.write("Artist: {}\n".format(self.artist))
        output_file.write("ArtistUnicode: {}\n".format(self.artist_unicode))
        output_file.write("Creator: {}\n".format(self.mapper_name))
        output_file.write("Version: {}\n".format(self.difficulty_name))
        output_file.write("Source: {}\n".format(self.source))
        output_file.write("Tags: {}\n".format(" ".join(self.tags)))
        output_file.write("BeatmapID: {}\n".format(self.beatmap_id))
        output_file.write("BeatmapSetID: {}\n".format(self.beatmap_set_id))
        
        output_file.write("\n[Difficulty]\n")
        output_file.write("HPDrainRate: {}\n".format(self.hp))
        output_file.write("CircleSize: {}\n".format(self.cs))
        output_file.write("OverallDifficulty: {}\n".format(self.od))
        output_file.write("ApproachRate: {}\n".format(self.ar))
        output_file.write("SliderMultiplier: {}\n".format(self.sv))
        output_file.write("SliderTickRate: {}\n".format(self.str))
        
        if self.events_string:
            output_file.write("\n[Events]\n{}".format(self.events_string))
        
        output_file.write("\n[TimingPoints]\n")
        for timing_point in self.timing_points:
            output_file.write("{},{},{},{},{},{},{},{}\n".format(int(timing_point.offset), timing_point.beat_length, timing_point.meter, timing_point.sample_set, timing_point.sample_index, timing_point.volume, "1" if timing_point.uninherited else "0", timing_point.effects))
        
        if self.colors_string:
            output_file.write("\n[Colours]\n{}".format(self.colors_string))
        
        output_file.write("\n[HitObjects]\n")
        for hit_object in self.hit_objects:
            line = "{},{},{},{},{}".format(hit_object.x_pos, hit_object.y_pos, hit_object.offset, hit_object.type_raw, hit_object.hit_sound_raw)
            if hit_object.type == "Slider":
                line += ",{}|{},{},{}".format(hit_object.slider_details.curve_type, "|".join(["{}:{}".format(curve_point[0], curve_point[1]) for curve_point in hit_object.slider_details.curve_points]), hit_object.slider_details.num_slides, hit_object.slider_details.length)
                if hit_object.slider_details.edge_sounds_raw:
                    line += ",{}".format(hit_object.slider_details.edge_sounds_raw)
                if hit_object.slider_details.edge_sets_raw:
                    line += ",{}".format(hit_object.slider_details.edge_sets_raw)
            if hit_object.type == "Spinner":
                line += ",{}".format(hit_object.spinner_end_offset)
            line += ",{}".format(hit_object.hit_sample_raw)
            output_file.write(line + "\n")
        output_file.close()
    
    def calc_taiko_scroll_speeds(self):
        if self.game_mode != 1:
            raise ValueError("This map isn't a Taiko map!")
        
        red_lines = [timing_point for timing_point in self.timing_points if timing_point.uninherited]
        if len(red_lines) == 0:
            raise ValueError("This map doesn't have a timing point!")
        
        if len(self.hit_objects) == 0:
            raise ValueError("This map doesn't have any hit objects!")
        
        default_sv = 1.4
        base_sv_multiplier = self.sv / default_sv
        
        first_object_offset = self.hit_objects[0].offset
        first_object_sv = self.bpm_at(first_object_offset) * self.slider_velocity_at(first_object_offset) / default_sv
        last_object_offset = self.hit_objects[-1].offset
        last_object_sv = self.bpm_at(last_object_offset) * self.slider_velocity_at(last_object_offset) / default_sv
        
        current_bpm = 60000 / red_lines[0].beat_length
        current_sv_multiplier = 1
        scroll_speeds = []
        previous_scroll_speed = first_object_sv
        for timing_point in self.timing_points:
            if timing_point.offset < first_object_offset or timing_point.offset > last_object_offset:
                continue
            
            if timing_point.uninherited:
                current_bpm = 60000 / timing_point.beat_length
                current_sv_multiplier = 1
                #Skip red line if there is a green line at the same offset
                if len([x for x in self.timing_points if x.offset == timing_point.offset and not x.uninherited]) > 0:
                    continue
            else:
                current_sv_multiplier = 1 / (timing_point.beat_length * -0.01)
            
            new_scroll_speed = current_bpm * base_sv_multiplier * current_sv_multiplier
            
            #Add a duplicate point here so the graph doesn't show a slope between two points
            scroll_speeds.append((timing_point.offset, previous_scroll_speed))
            scroll_speeds.append((timing_point.offset, new_scroll_speed))
            
            previous_scroll_speed = new_scroll_speed
            
        return [(first_object_offset, first_object_sv)] + scroll_speeds + [(last_object_offset, last_object_sv)]
    
    def calc_note_densities(self):
        last_object_offset = self.hit_objects[-1].offset
        interval_length = 500
        buckets = [[i * interval_length, 0] for i in range(math.ceil(last_object_offset / interval_length))]
        
        for hit_object in self.hit_objects:
            #adding the hit_object to the previous bucket makes the buckets two intervals in length and overlapping
            first_bucket_index = (hit_object.offset - interval_length) // interval_length
            second_bucket_index = (hit_object.offset) // interval_length
            if first_bucket_index >= 0:
                buckets[first_bucket_index][1] += 1
            if second_bucket_index < len(buckets):
                buckets[second_bucket_index][1] += 1
        
        return buckets
    
    def calc_taiko_pattern_complexities(self):
        if self.game_mode != 1:
            raise ValueError("This map isn't a Taiko map!")
        
        red_lines = [timing_point for timing_point in self.timing_points if timing_point.uninherited]
        if len(red_lines) == 0:
            raise ValueError("This map doesn't have a timing point!")
        
        if len(self.hit_objects) == 0:
            raise ValueError("This map doesn't have any hit objects!")
        
        first_object_offset = self.hit_objects[0].offset
        last_object_offset = self.hit_objects[-1].offset
        
        #create buckets based on beats rather than seconds to minimize correlation with note density
        buckets = []
        #beats_per_bucket = 4
        beats_per_interval = 2
        #min_bucket_interval = 240
        
        #in case there are objects before first timing point
        if first_object_offset < red_lines[0].offset:
            bucket_offset = red_lines[0].offset
            #bucket_length = red_lines[0].beat_length * beats_per_bucket
            interval_length = red_lines[0].beat_length * beats_per_interval
            while bucket_offset > first_object_offset:
                bucket_offset -= interval_length
            while bucket_offset < first_object_offset:
                buckets.append([math.floor(bucket_offset), 0])
                bucket_offset += interval_length
        
        for i in range(len(red_lines)):
            current_red_line = red_lines[i]
            next_red_line = red_lines[i+1] if i < len(red_lines) - 1 else None
            bucket_offset = current_red_line.offset
            #bucket_length = red_lines[0].beat_length * beats_per_bucket
            interval_length = current_red_line.beat_length * beats_per_interval
            while bucket_offset < last_object_offset:
                #skip until first object
                if bucket_offset + interval_length < first_object_offset:
                    bucket_offset += interval_length
                    continue
                if next_red_line and bucket_offset >= next_red_line.offset:
                    break
                #prevent multiple buckets in one spot in case of red line spam
                #if len(buckets) == 0 or bucket_offset - buckets[-1][0] >= min_bucket_interval:
                buckets.append([math.floor(bucket_offset), 0])
                bucket_offset += interval_length
        #print(buckets)
        
        #interval_length = math.ceil(self.beat_length_at(first_object_offset)) * 2
        #buckets = [[offset, 0] for offset in range(first_object_offset, last_object_offset, interval_length)]
        
        def get_bucket(offset):
            for i in range(len(buckets)):
                if i == len(buckets) - 1 or (buckets[i][0] <= offset and buckets[i+1][0] > offset):
                    return buckets[i]
        
        #def get_buckets(offset):
        #    return [bucket for bucket in buckets if bucket[0] <= offset and bucket[1] > offset]
        def get_buckets(start_offset, end_offset):
            ans = []
            for i in range(len(buckets)):
                bucket_start = buckets[i][0]
                bucket_end = buckets[i+1][0] if i < len(buckets) - 1 else None
                if not bucket_end:
                    if end_offset >= bucket_start:
                        ans.append(buckets[i])
                else:
                    if bucket_start >= start_offset and bucket_end <= end_offset:
                        ans.append(buckets[i])
            return ans
            #return [bucket for bucket in buckets if start_offset >= bucket[0] and start_offset < bucket[0]]
        
        pattern_separator_threshold = 120
        
        patterns = []
        previous_object_offset = 0
        current_pattern = []
        for hit_object in self.hit_objects:
            if hit_object.offset - previous_object_offset > pattern_separator_threshold:
                if len(current_pattern) > 0:
                    patterns.append(current_pattern)
                    current_pattern = []
            current_pattern.append(hit_object)
            previous_object_offset = hit_object.offset
        if len(current_pattern) > 0:
            patterns.append(current_pattern)
        
        def add_points(offset, points):
            get_bucket(offset)[1] += points
            #buckets = get_buckets(start_offset, end_offset)
            
            #for bucket in get_buckets(offset):
            #    bucket[2] += points
            #first_bucket_index = (offset - interval_length) // interval_length
            #second_bucket_index = (offset) // interval_length
            #if first_bucket_index >= 0:
            #    buckets[first_bucket_index][1] += points
            #if second_bucket_index < len(buckets):
            #    buckets[second_bucket_index][1] += points
        
        def add_points_evenly(group, points):
            for hit_object in group:
                add_points(hit_object.offset, points / len(group))
        
        for pattern in patterns:
            if len(pattern) == 1:
                add_points(pattern[0].offset, 1)
            else:
                #add points based on color swaps during pairs of notes
                pairs = [(pattern[i], pattern[i+1]) for i in range(0, len(pattern) - 1, 2)]
                for pair in pairs:
                    offset_average = (pair[0].offset + pair[1].offset) // 2
                    if pair[0].taiko_color() == pair[1].taiko_color():
                        add_points_evenly(pair, 1)
                    else:
                        add_points_evenly(pair, 2)
                
                #add points based on oddity of color groups
                color_splits = []
                current_color_split = []
                current_color = None
                for hit_object in pattern:
                    if hit_object.taiko_color() != current_color:
                        if len(current_color_split) > 0:
                            color_splits.append(current_color_split)
                            current_color_split = []
                            current_color = hit_object.taiko_color()
                    current_color_split.append(hit_object)
                if len(current_color_split) > 0:
                    color_splits.append(current_color_split)
                previous_length = 0
                for color_split in color_splits:
                    #color groups longer than 5 will have an average offset that's far from either end, so ignore them
                    if len(color_split) <= 5:
                        offset_average = sum([hit_object.offset for hit_object in color_split]) // len(color_split)
                        #scale based on length of group (to balance longer groups with shorter groups)
                        length_multiplier = len(color_split) / 2
                        
                        #add points based on oddity of current group
                        if len(color_split) % 2 == 0:
                            add_points_evenly(color_split, 1 * length_multiplier)
                        elif len(color_split) == 1:
                            add_points_evenly(color_split, 1 * length_multiplier)
                        else:
                            add_points_evenly(color_split, 2 * length_multiplier)
                        
                        #add points based on change in oddity from previous group
                        if len(color_split) == previous_length:
                            add_points_evenly(color_split, 2 * length_multiplier)
                        elif abs(len(color_split) - previous_length) % 2 == 1:
                            if len(color_split) + previous_length <= 3:
                                add_points_evenly(color_split, 4 * length_multiplier)
                            else:
                                add_points_evenly(color_split, 8 * length_multiplier)
                        elif len(color_split) % 2 == 0:
                            add_points_evenly(color_split, 4 * length_multiplier)
                        elif len(color_split) % 2 == 1:
                            add_points_evenly(color_split, 6 * length_multiplier)
                    
                    previous_length = len(color_split)
        print(buckets)
        return buckets

class OsuTimingPoint:
    def __init__(self):
        self.offset = 0
        self.beat_length = 0
        self.meter = 4
        self.sample_set = 0
        self.sample_index = 0
        self.volume = 100
        self.uninherited = False
        self.effects = 0
        self.kiai = False

class OsuHitObject:
    def __init__(self):
        self.x_pos = 0
        self.y_pos = 0
        self.offset = 0
        self.type_raw = 0
        self.type = ""
        self.hit_sound_raw = 0
        self.hit_sound_normal = False
        self.hit_sound_whistle = False
        self.hit_sound_finish = False
        self.hit_sound_clap = False
        self.hit_sample_raw = "0:0:0:0:"
        self.slider_details = None
        self.spinner_end_offset = None
    
    #Stacked notes are usually offset to the top left (negative), unless on a slider end (positive)
    def stack_pos(self, stack_height, cs, positive=False):
        scale = (1 - (0.7 * (cs - 5) / 5)) / 2
        direction = 1 if positive else -1
        return [self.x_pos + (stack_height * scale * 6.4 * direction), self.y_pos + (stack_height * scale * 6.4 * direction)]
    
    def check_hit_by_pos(self, hit_x, hit_y, cs):
        r = 54.4 - (4.48 * cs)
        error = math.sqrt(((hit_x - self.x_pos) ** 2) + ((hit_y - self.y_pos) ** 2))
        return (error <= r, error)
    
    #Note: Two keys can activate at the exact same time, so there is an added return variable to check if this specific case hits a finisher
    def check_hit_taiko(self, activated_keys):
        #miss if both red and blue are hit at the same time
        if ("M1" in activated_keys and "K2" in activated_keys) or ("M2" in activated_keys and "K1" in activated_keys) or ("M1" in activated_keys and "M2" in activated_keys) or ("K1" in activated_keys and "K2" in activated_keys):
            return False, False
        if (self.hit_sound_whistle or self.hit_sound_clap) and ("M2" in activated_keys or "K2" in activated_keys):
            if (self.hit_sound_finish) and ("M2" in activated_keys and "K2" in activated_keys):
                return True, True
            else:
                return True, False
        elif (not self.hit_sound_whistle and not self.hit_sound_clap) and ("M1" in activated_keys or "K1" in activated_keys):
            if (self.hit_sound_finish) and ("M1" in activated_keys and "K1" in activated_keys):
                return True, True
            else:
                return True, False
        else:
            return False, False
    
    def check_hit_by_time(self, offset, od, mode=0):
        if mode == 0:
            miss_window = 399.5
            hit_window_50 = int(200 - (10 * od)) - 0.5
            hit_window_100 = int(140 - (8 * od)) - 0.5
            hit_window_300 = int(80 - (6 * od)) - 0.5
            error = offset - self.offset
            if abs(error) <= hit_window_300:
                return 300
            elif abs(error) <= hit_window_100:
                return 100
            elif abs(error) <= hit_window_50:
                return 50
            elif abs(error) <= miss_window:
                return 0
            else:
                return None
        elif mode == 1:
            miss_window = int(95 + (8 * (5 - od))) - 0.5 if od < 5 else int(95 - (5 * (od - 5)))
            hit_window_100 = int(80 + (8 * (5 - od))) - 0.5 if od < 5 else int(80 - (6 * (od - 5))) - 0.5
            hit_window_300 = int(50 - (3 * od)) - 0.5
            #hit_window_300 = int(35 + (3 * (5 - od))) - 0.5 if od < 5 else int(35 - (3 * (od - 5))) - 0.5
            error = offset - self.offset
            if abs(error) <= hit_window_300:
                return 300
            elif abs(error) <= hit_window_100:
                return 150
            elif abs(error) <= miss_window:
                return 0
            else:
                return None
        else:
            raise ValueError("Unsupported or unknown game mode: {}".format(mode))
    
    #TODO: repeats
    def slider_pos_at(self, offset, sv, bl):
        if self.type != "Slider":
            raise TypeError("This ain't a slider")
        if self.offset > offset:
            raise ValueError("Given offset is before the beginning of this slider")
        
        if self.slider_details.curve_type == "C":
            raise TypeError("I don't support catmull sliders (yet)")
        
        slider_sections = []
        prev_curve_point = None
        cur_section = [[self.x_pos, self.y_pos]]
        for curve_point in self.slider_details.curve_points:
            if curve_point == prev_curve_point:
                slider_sections.append(cur_section)
                cur_section = []
            cur_section.append(curve_point)
            prev_curve_point = curve_point
        slider_sections.append(cur_section)
        
        duration = offset - self.offset
        beats = duration / bl
        target_distance = beats * 100 * sv
        if round(target_distance) > round(self.slider_details.length):
            raise ValueError("Given offset is past the end of this slider")
        
        if self.slider_details.curve_type == "L":
            point1 = [self.x_pos, self.y_pos]
            point2 = self.slider_details.curve_points[0] #Linear sliders should only have one curve point
            slope = (point2[1] - point1[1]) / (point2[0] - point1[0])
            angle = math.atan(slope)
            distance_x = math.cos(angle) * target_distance
            distance_y = math.sin(angle) * target_distance
            return [point1[0] + distance_x, point1[1] + distance_y]
        
        #I feel like I overcomplicated things here
        if self.slider_details.curve_type == "P":
            point1 = [self.x_pos, self.y_pos]
            #Perfect circle sliders should have exactly two curve points
            point2 = self.slider_details.curve_points[0]
            point3 = self.slider_details.curve_points[1]
            
            #Compute equation of circle and some of its properties
            A = (point1[0] * (point2[1] - point3[1])) - (point1[1] * (point2[0] - point3[0])) + (point2[0] * point3[1]) - (point3[0] * point2[1])
            B = (((point1[0] ** 2) + (point1[1] ** 2)) * (point3[1] - point2[1])) + (((point2[0] ** 2) + (point2[1] ** 2)) * (point1[1] - point3[1])) + (((point3[0] ** 2) + (point3[1] ** 2)) * (point2[1] - point1[1]))
            C = (((point1[0] ** 2) + (point1[1] ** 2)) * (point2[0] - point3[0])) + (((point2[0] ** 2) + (point2[1] ** 2)) * (point3[0] - point1[0])) + (((point3[0] ** 2) + (point3[1] ** 2)) * (point1[0] - point2[0]))
            D = (((point1[0] ** 2) + (point1[1] ** 2)) * ((point3[0] * point2[1]) - (point2[0] * point3[1]))) + (((point2[0] ** 2) + (point2[1] ** 2)) * ((point1[0] * point3[1]) - (point3[0] * point1[1]))) + (((point3[0] ** 2) + (point3[1] ** 2)) * ((point2[0] * point1[1]) - (point1[0] * point2[1])))
            r = math.sqrt(((B ** 2) + (C ** 2) - (4 * A * D)) / (4 * (A ** 2)))
            center = [-1 * (B / (2 * A)), -1 * (C / (2 * A))]
            perimeter = r * 2 * math.pi
            
            #Convert point to polar, traverse target distance, convert back to cartesian
            distance_angle = (target_distance / perimeter) * 2 * math.pi
            point1_polar_offset = [point1[0] - center[0], point1[1] - center[1]]
            point1_polar_angle = math.atan(point1_polar_offset[1] / point1_polar_offset[0])
            target_point_polar_angle = point1_polar_angle + distance_angle
            target_point_offset = [r * math.cos(target_point_polar_angle), r * math.sin(target_point_polar_angle)]
            target_point = [center[0] - target_point_offset[0], center[1] - target_point_offset[1]]
            
            return target_point
        
        #Use a library cause I'm too lazy to figure out bezier curves
        elif self.slider_details.curve_type == "B":
            curves = []
            for section in slider_sections:
                x_points = [p[0] for p in section]
                y_points = [p[1] for p in section]
                curves.append(bezier.curve.Curve([x_points, y_points], len(x_points) - 1))
            
            which_curve = None
            temp = 0
            for curve in curves:
                which_curve = curve
                temp += curve.length
                if temp > target_distance:
                    break
            
            temp -= which_curve.length #Distance from beginning to the beginning of current curve
            curve_distance = target_distance - temp
            eval = which_curve.evaluate(curve_distance / which_curve.length)
            return [eval[0][0], eval[1][0]]
                
        else:
            raise TypeError("Unrecognized slider type: {}".format(self.slider_details.curve_type))
    
    #Finds the position and offset of this slider's end
    def slider_end(self, sv, bl):
        beats = self.slider_details.length / 100 / sv
        duration = beats * bl
        offset = int(self.offset + duration)
        x, y = self.slider_pos_at(offset, sv, bl)
        return [x, y, offset]
    
    def taiko_color(self):
        if self.hit_sound_whistle or self.hit_sound_clap:
            return "K"
        else:
            return "D"

class OsuSliderDetails:
    def __init__(self):
        self.curve_type = "" #One of (L,P,B,C)
        self.curve_points = [] #List of [x,y]
        self.num_slides = 1
        self.length = 0
        self.edge_sounds_raw = ""
        self.edge_sets_raw = ""

class OsuBeatmapParser:
    def parse_from_filename(self, filename):
        file = open(filename, encoding="utf-8")
        return self.parse_from_file(file)
    
    def parse_from_file(self, file):
        if file.encoding != "utf-8":
            raise ValueError("File should be in 'utf-8' encoding")
        return self.parse(file.read())
    
    def parse(self, contents):
        map_details = OsuBeatmapDetails()
        lines = contents.split("\n")
        #regex because sometimes there's an unidentified character at the beginning of the file??
        map_details.file_format_version = int(re.findall(r"osu file format v\d+", lines[0])[0][17:])
        
        current_section = None
        for line in lines:
            if not line:
                continue
            
            if line.startswith("["):
                current_section = line[1:-1]
            
            elif current_section == "General":
                key = line.split(":")[0].strip()
                value = line.split(":")[1].strip()
                if key == "AudioFilename":
                    map_details.audio_file_name = value
                if key == "AudioLeadIn":
                    map_details.audio_lead_in = int(value)
                if key == "PreviewTime":
                    map_details.preview_time = int(value)
                if key == "Countdown":
                    map_details.countdown = int(value)
                if key == "SampleSet":
                    map_details.sample_set = value
                if key == "StackLeniency":
                    map_details.stack_leniency = float(value)
                if key == "Mode":
                    map_details.game_mode = int(value)
                if key == "LetterboxInBreaks":
                    map_details.letterbox_in_breaks = int(value)
                if key == "WidescreenStoryboard":
                    map_details.widescreen_storyboard = int(value)
            
            elif current_section == "Editor":
                key = line.split(":")[0].strip()
                value = line.split(":")[1].strip()
                if key == "Bookmarks":
                    map_details.bookmarks = [int(x) for x in value.split(",")]
                if key == "DistanceSpacing":
                    map_details.distance_spacing = float(value)
                if key == "BeatDivisor":
                    map_details.beat_divisor = int(value)
                if key == "GridSize":
                    map_details.grid_size = int(value)
                if key == "TimelineZoom":
                    map_details.timeline_zoom = float(value)
            
            elif current_section == "Metadata":
                key = line.split(":")[0].strip()
                value = line.split(":")[1].strip()
                if key == "Title":
                    map_details.title = value
                if key == "TitleUnicode":
                    map_details.title_unicode = value
                if key == "Artist":
                    map_details.artist = value
                if key == "ArtistUnicode":
                    map_details.artist_unicode = value
                if key == "Creator":
                    map_details.mapper_name = value
                if key == "Version":
                    map_details.difficulty_name = value
                if key == "Source":
                    map_details.source = value
                if key == "Tags":
                    map_details.tags = [x for x in value.split(" ")]
                if key == "BeatmapID":
                    map_details.beatmap_id = int(value)
                if key == "BeatmapSetID":
                    map_details.beatmap_set_id = int(value)
            
            elif current_section == "Difficulty":
                key = line.split(":")[0].strip()
                value = line.split(":")[1].strip()
                if key == "HPDrainRate":
                    map_details.hp = float(value)
                if key == "CircleSize":
                    map_details.cs = float(value)
                if key == "OverallDifficulty":
                    map_details.od = float(value)
                if key == "ApproachRate":
                    map_details.ar = float(value)
                if key == "SliderMultiplier":
                    map_details.sv = float(value)
                if key == "SliderTickRate":
                    map_details.str = float(value)
            
            elif current_section == "Events":
                map_details.events_string += line + "\n"
            
            elif current_section == "TimingPoints":
                timing_point = OsuTimingPoint()
                values = line.split(",")
                timing_point.offset = float(values[0])
                timing_point.beat_length = float(values[1])
                timing_point.meter = int(values[2])
                timing_point.sample_set = int(values[3])
                timing_point.sample_index = int(values[4])
                timing_point.volume = int(values[5])
                timing_point.uninherited = False if values[6] == "0" else True
                timing_point.effects = int(values[7])
                timing_point.kiai = timing_point.effects & 1 == 1
                
                map_details.timing_points.append(timing_point)
            
            elif current_section == "Colours":
                map_details.colors_string += line + "\n"
            
            elif current_section == "HitObjects":
                hit_object = OsuHitObject()
                values = line.split(",")
                hit_object.x_pos = int(values[0])
                hit_object.y_pos = int(values[1])
                hit_object.offset = int(values[2])
                hit_object.type_raw = int(values[3])
                hit_object.hit_sound_raw = int(values[4])
                
                if hit_object.type_raw & 128 == 128:
                    hit_object.type = "Hold"
                elif hit_object.type_raw & 8 == 8:
                    hit_object.type = "Spinner"
                elif hit_object.type_raw & 2 == 2:
                    hit_object.type = "Slider"
                elif hit_object.type_raw & 1 == 1:
                    hit_object.type = "Circle"
                else:
                    hit_object.type = "Unknown"
                
                if hit_object.hit_sound_raw & 8 == 8:
                    hit_object.hit_sound_clap = True
                if hit_object.hit_sound_raw & 4 == 4:
                    hit_object.hit_sound_finish = True
                if hit_object.hit_sound_raw & 2 == 2:
                    hit_object.hit_sound_whistle = True
                if hit_object.hit_sound_raw & 1 == 1:
                    hit_object.hit_sound_normal = True
                
                if hit_object.type == "Circle":
                    if len(values) > 5:
                        hit_object.hit_sample_raw = values[5]
                
                if hit_object.type == "Slider":
                    slider_details = OsuSliderDetails()
                    slider_details.curve_type = values[5].split("|")[0]
                    for curve_point in values[5].split("|")[1:]:
                        slider_details.curve_points.append([int(curve_point.split(":")[0]), int(curve_point.split(":")[1])])
                    slider_details.num_slides = int(values[6])
                    slider_details.length = float(values[7])
                    slider_details.edge_sounds_raw = values[8] if len(values) > 8 else ""
                    slider_details.edge_sets_raw = values[9] if len(values) > 9 else ""
                    hit_object.slider_details = slider_details
                    if len(values) > 10:
                        hit_object.hit_sample_raw = values[10]
                
                if hit_object.type == "Spinner":
                    hit_object.spinner_end_offset = int(values[5])
                    if len(values) > 6:
                        hit_object.hit_sample_raw = values[6]
                
                map_details.hit_objects.append(hit_object)
        
        return map_details