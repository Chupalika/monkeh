import lzma

mods_strings = ["NF", "EZ", "TD", "HD", "HR", "SD", "DT", "Relax", "HT", "NC", "FL", "Autoplay", "SO", "Autopilot", "PF", "K4", "K5", "K6", "K7", "K8", "FI", "RD", "Cinema", "Target", "K9", "KeyCoop", "K1", "K3", "K2", "V2", "LastMod"]
keys_strings = ["M1", "M2", "K1", "K2", "Smoke"]

class OsuReplayDetails:
    def __init__(self):
        self.game_mode = 0
        self.game_version = 0
        self.map_md5hash = ""
        self.player_name = ""
        self.replay_md5hash = ""
        self.num_300s = 0
        self.num_100s = 0
        self.num_50s = 0
        self.num_gekis = 0
        self.num_katus = 0
        self.num_misses = 0
        self.score = 0
        self.high_combo = 0
        self.perfect = False
        self.mods_raw = 0
        self.life_bar_graph = ""
        self.timestamp = 0
        self.replay_data_length = 0
        self.replay_data_raw = ""
        self.online_score_id = 0
    
    #Returns a list of OsuReplayAction objects
    def replay_data(self):
        ans = []
        data = lzma.decompress(self.replay_data_raw).decode("utf-8")
        current_offset = 0
        for action_raw in data.split(","):
            parts = action_raw.split("|")
            if len(parts) != 4:
                continue
            action = OsuReplayAction()
            action.ms_since_prev = int(parts[0])
            action.x_pos = float(parts[1])
            action.y_pos = float(parts[2])
            action.keys_pressed_raw = int(parts[3])
            current_offset += action.ms_since_prev
            action.offset = current_offset
            ans.append(action)
        return ans
    
    #Returns a list of strings indicating mods
    def mods(self):
        mods_b = "{0:032b}".format(self.mods_raw)
        ans = []
        for i in range(32):
            if mods_b[i*-1-1] == "1":
                ans.append(mods_strings[i])
        if "NC" in ans:
            try:
                ans.remove("DT")
            except ValueError:
                pass
        if "PF" in ans:
            try:
                ans.remove("SD")
            except ValueError:
                pass
        return ans

class OsuReplayAction:
    def __init__(self):
        self.ms_since_prev = 0
        self.x_pos = 0
        self.y_pos = 0
        self.keys_pressed_raw = 0
        self.offset = 0
    
    #Returns a list of strings indicating keys pressed
    def keys_pressed(self):
        keys_pressed_b = "{0:05b}".format(self.keys_pressed_raw)
        ans = []
        for i in range(5):
            if keys_pressed_b[i*-1-1] == "1":
                ans.append(keys_strings[i])
        return ans

class OsuReplayParser:
    def parse_from_filename(self, filename):
        file = open(filename, "rb")
        return self.parse(file)
    
    #Returns a OsuReplayDetails object
    def parse_from_file(self, file):
        if file.mode != "rb":
            raise ValueError("File should be in 'rb' mode")
        
        replay_details = OsuReplayDetails()
        replay_details.game_mode = self.__read_byte(file)
        replay_details.game_version = self.__read_int(file)
        replay_details.map_md5hash = self.__read_string(file)
        replay_details.player_name = self.__read_string(file)
        replay_details.replay_md5hash = self.__read_string(file)
        replay_details.num_300s = self.__read_short(file)
        replay_details.num_100s = self.__read_short(file)
        replay_details.num_50s = self.__read_short(file)
        replay_details.num_gekis = self.__read_short(file)
        replay_details.num_katus = self.__read_short(file)
        replay_details.num_misses = self.__read_short(file)
        replay_details.score = self.__read_int(file)
        replay_details.high_combo = self.__read_short(file)
        replay_details.perfect = self.__read_byte(file)
        replay_details.mods_raw = self.__read_int(file)
        replay_details.life_bar_graph = self.__read_string(file)
        replay_details.timestamp = self.__read_long(file)
        replay_details.replay_data_length = self.__read_int(file)
        replay_details.replay_data_raw = self.__read_bytes(file, replay_details.replay_data_length)
        replay_details.online_score_id = self.__read_long(file)
        return replay_details
    
    def __read_byte(self, file):
        return int.from_bytes(file.read(1), "little")
    
    def __read_short(self, file):
        return int.from_bytes(file.read(2), "little")   
    
    def __read_int(self, file):
        return int.from_bytes(file.read(4), "little")
    
    def __read_long(self, file):
        return int.from_bytes(file.read(8), "little")
    
    def __read_uleb128(self, file):
        ans = 0
        num_bytes = 0
        msb = False
        while not msb:
            byte = int.from_bytes(file.read(1), "little")
            msb = (byte & 128) == 0
            if not msb:
                value = byte & (byte - 128)
            else:
                value = byte
            ans += value * (128 ** num_bytes)
            num_bytes += 1
        return ans
    
    def __read_string(self, file):
        present = int.from_bytes(file.read(1), "little")
        
        #0x0b
        if present != 11:
            return ""
        
        string_length = self.__read_uleb128(file)
        return file.read(string_length).decode("utf-8")
    
    def __read_bytes(self, file, num_bytes):
        return file.read(num_bytes)