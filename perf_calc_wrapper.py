import sys, subprocess, os, json
#import time

legacy_calcs = ["taiko-loopy", "2021-11-09", "2022-10-10"]

def calculate_pp(file_name, mode="osu", mods=[], acc=None, combo=None, n300=None, n200=None, n100=None, n50=None, n0=None, score=1000000, partial=False, objects_progress=0, ctb_map_completion=0, use_calc=None):
    if partial:
        if mode in ["osu", "taiko"]:
            file_name, objects_total = __partial_beatmap__(file_name, objects_progress)
        elif mode == "catch":
            _, objects_total = __partial_beatmap__(file_name, objects_progress)
            objects_progress = int(ctb_map_completion * objects_total)
            file_name, objects_total = __partial_beatmap__(file_name, objects_progress)
        elif mode == "mania":
            _, objects_total = __partial_beatmap__(file_name, objects_progress)
        map_progress = objects_progress / objects_total
    
    cmd = "dotnet {}/PerformanceCalculator.dll simulate {} {}".format(__get_calc_name__(mode, use_calc), mode, file_name)
    if use_calc in ["2021-11-09", "2022-10-10"]:
        cmd += " -nc"
    if use_calc not in legacy_calcs:
        cmd += " -j"
    for mod in mods:
        cmd += " -m {}".format(mod.upper())
    if acc and mode != "mania":
        cmd += " -a {}".format(acc)
    if combo and mode != "mania":
        cmd += " -c {}".format(combo)
    if n300 is not None and mode == "mania":
        if use_calc is None:
            cmd += " -T {}".format(n300)
        elif use_calc != "2021-11-09":
            cmd += " -R {}".format(n300)
    if n200 is not None and mode == "mania" and use_calc != "2021-11-09":
        cmd += " -G {}".format(n200)
    if n100 is not None and mode not in ["catch", "mania"]:
        cmd += " -G {}".format(n100)
    if n100 is not None and mode == "catch":
        cmd += " -D {}".format(n100)
    if n100 is not None and mode == "mania" and use_calc != "2021-11-09":
        cmd += " -O {}".format(n100)
    if n50 is not None and mode in ["osu", "mania"] and use_calc != "2021-11-09":
        cmd += " -M {}".format(n50)
    if n50 is not None and mode == "catch":
        cmd += " -T {}".format(n50)
    if n0 is not None and use_calc != "2021-11-09":
        cmd += " -X {}".format(n0)
    if score and mode == "mania" and use_calc == "2021-11-09":
        cmd += " -s {}".format(score)
    
    #print(cmd)
    pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    output = pipe.communicate()
    if not output[0]:
        raise Exception("PerformanceCalculator did not run succesfully")
    output_string = output[0]

    if use_calc in legacy_calcs:
        output_string = str(output_string)
        #separator = "\\r\\n" if use_calc == "deltapp" else "\\n"
        separator = "\\n"
        lines = [x.split(":") for x in output_string.split(separator)[1:] if ":" in x]
        lines2 = [[x.strip(), y.strip()] for x,y in lines]
        ans = {}
        for line in lines2:
            key, value = line
            key = key.lower()
            
            '''
            if key == "Combo":
                # Removes the percentage
                value = value.split(" ")[0]
            '''
            
            # These aliases are from different versions of osu-tools
            '''
            if key == "aim":
                key = "aim pp"
            if key == "speed":
                key = "speed pp"
            if key == "tap":
                key = "tap pp"
            if key == "accuracy" and "%" not in value:
                key = "accuracy pp"
            if key == "strain":
                key = "strain pp"
            
            if key == "accuracy" and "%" in value:
                # Removes the %
                value = value.replace("%", "")
            
            if key == "difficulty pp":
                key = "strain pp"
            '''
            
            # LooPP still using old osu-tools keys
            if use_calc == "taiko-loopy":
                if key == "strain":
                    key = "difficulty pp"
                if key == "accuracy" and "%" not in value:
                    key = "accuracy pp"
                if key == "accuracy" and "%" in value:
                    value = value.replace("%", "")
            
            ans[key] = value
        if not ans.items():
            raise Exception("PerformanceCalculator did not run succesfully")
        if partial:
            ans["map_progress"] = map_progress
        return ans
    else:
        output_string = output_string.decode("utf-8")
        output_json = json.loads(output_string)
        if partial:
            output_json["map_progress"] = map_progress
        return output_json

def calculate_sr(file_name, mode="osu", mods=[], use_calc=None):
    cmd = "dotnet {}/PerformanceCalculator.dll difficulty {}".format(__get_calc_name__(mode, use_calc), file_name)
    for mod in mods:
        cmd += " -m {}".format(mod.upper())
    #print("running perfcalc")
    #start_time = time.time()
    pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    output = pipe.communicate()
    if not output[0]:
        raise Exception("PerformanceCalculator did not run succesfully")
    output_string = output[0]
    output_string = output_string.decode("utf-8")
    #output_string = str(output[0])[2:] #Get rid of the first two characters: b'
    #print("done")
    #print("took {} seconds".format(time.time() - start_time))
    
    if use_calc in legacy_calcs:
        times = []
        difficulty_attributes = [] # a list of lists, one list for each difficulty attribute
        
        for snippet in output_string.split("\r\n"):
            values = snippet.split(",")
            if (len(values)) <= 2:
                continue
            start_time = values[0]
            end_time = values[1]
            #time = float(start_time) + ((float(end_time) - float(start_time)) / 2)
            times.append(float(start_time) / 1000)
            for i in range(len(values[2:])):
                if len(difficulty_attributes) == i:
                    difficulty_attributes.append([])
                difficulty_attributes[i].append(float(values[2+i]))
        #print(len(times))
        
        return (times, difficulty_attributes)
    else:
        difficulty_attributes = [json.loads(line) for line in output_string.split("\n") if line]
        return ([float(attributes["start_time"]) / 1000 for attributes in difficulty_attributes], difficulty_attributes)

def __get_calc_name__(mode="osu", use_calc=None):
    '''
    if use_calc == "loopp" and mode == "taiko":
        calc_folder_name = "PerformanceCalculator-loopp"
    elif use_calc == "preltca" and mode == "taiko":
        calc_folder_name = "PerformanceCalculator-preltca"
    elif use_calc == "maniav1" and mode == "mania":
        calc_folder_name = "PerformanceCalculator-preltca"
    '''
    if use_calc:
        calc_folder_name = "PerformanceCalculator-" + use_calc
    else:
        calc_folder_name = "PerformanceCalculator"
    return calc_folder_name

#Returns (new file name, total object count)
def __partial_beatmap__(file_name, objects_progress):
    input_file = open(file_name, encoding="utf-8")
    output_file_name = file_name
    if objects_progress > 0:
        output_file_name = file_name[:-4] + "@{}".format(objects_progress) + file_name[-4:]
        output_file = open(output_file_name, "w", encoding="utf-8")
    lines = input_file.read().split("\n")
    input_file.close()
    current_section = None
    objects_counter = 0
    for line in lines:
        if not line:
            pass
        elif line.startswith("["):
            current_section = line[1:-1]
        elif current_section == "HitObjects":
            objects_counter += 1
            if objects_counter > objects_progress:
                continue
        if objects_progress > 0:
            output_file.write(line + "\n")
    if objects_progress > 0:
        output_file.close()
    return (output_file_name, objects_counter)