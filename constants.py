import typing

mode_aliases = {"0":"0", "osu":"0", "std":"0", "o":"0", "1":"1", "taiko":"1", "t":"1", "2":"2", "catch":"2", "ctb":"2", "c":"2", "fruits": "2", "3":"3", "mania":"3", "m":"3"}
mode_aliases_v2 = {"0":"osu", "osu":"osu", "std":"osu", "o":"osu", "1":"taiko", "taiko":"taiko", "t":"taiko", "2":"fruits", "catch":"fruits", "ctb":"fruits", "c":"fruits", "fruits": "fruits", "3":"mania", "mania":"mania", "m":"mania"}
modes = {"0":"osu", "1":"taiko", "2":"catch", "3":"mania"}
modes2 = ["osu", "taiko", "catch", "mania"]
mods = ["NF", "EZ", "TD", "HD", "HR", "SD", "DT", "RX", "HT", "NC", "FL", "AT", "SO", "AP", "PF", "K4", "K5", "K6", "K7", "K8", "FI", "RD", "CN", "TP", "K9", "KeyCoop", "K1", "K3", "K2", "V2", "MR"]
mods_v2 = {"EZ": "Easy", "NF": "No Fail", "HT": "Half Time", "DC": "Daycore", "HR": "Hard Rock", "SD": "Sudden Death", "PF": "Perfect", "DT": "Double Time", "NC": "Nightcore", "HD": "Hidden", "FL": "Flashlight",
           "BL": "Blinds", "ST": "Strict Tracking", "AC": "Accuracy Challenge", "TP": "Target Practice", "DA": "Difficulty Adjust", "CL": "Classic", "RD": "Random", "MR": "Mirror", "AL": "Alternate", "SG": "Single Tap",
           "AT": "Autoplay", "CN": "Cinema", "RX": "Relax", "AP": "Autopilot", "SO": "Spun Out", "TR": "Transform", "WG": "Wiggle", "SI": "Spun In", "GR": "Grow", "DF": "Deflate", "WU": "Wind Up", "WD": "Wind Down",
           "TC": "Traceable", "BR": "Barrel Roll", "AD": "Approach Different", "MU": "Muted", "NS": "No Scope", "MG": "Magnetized", "RP": "Repel", "AS": "Adaptive Speed", "FR": "Freeze Frame", "BU": "Bubbles",
           "SY": "Synesthesia", "DP": "Depth", "TD": "Touch Device", "SV2": "Score V2", "SW": "Swap", "FF": "Floating Fruits", "FI": "Fade In", "CO": "Cover", "DS": "Dual Stages", "IN": "Invert", "CS": "Constant Speed",
           "HO": "Hold Off", "1K": "One Key", "2K": "Two Keys", "3K": "Three Keys", "4K": "Four Keys", "5K": "Five Keys", "6K": "Six Keys", "7K": "Seven Keys", "8K": "Eight Keys", "9K": "Nine Keys", "10K": "Ten Keys"}
rank_colors = {"F":0x800080, "D":0xff1e00, "C":0xff008c, "B":0x003cff, "A":0x3cff00, "S":0xffe100, "SH":0xf4f4f4, "X":0xffe100, "XH":0xf4f4f4}
GameMode = typing.Literal["osu", "taiko", "fruits", "mania"]
SortMethod = typing.Literal["Date", "Accuracy", "Combo"]
Calculator = typing.Literal["taiko-loopy", "2021-11-09", "2022-10-10", "2024-10-30", "2025-02-27"]
legacy_calcs = ["taiko-loopy", "2021-11-09", "2022-10-10"]