from loader import config_loader

SETTING = config_loader.load_config()

def check_file(size):
    ok = True
    need_to_split = False
    msg = None
    if size > SETTING["video_max_size"]:
        msg = "file is larger than limite"
        ok = False
    elif size > SETTING["video_part_size"]:
        need_to_split = True
    
    return ok, msg, need_to_split