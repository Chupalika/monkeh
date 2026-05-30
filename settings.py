#BOT FILES
commands_table_name = "tables/commands"
settings_table_name = "tables/settings"
user_levels_table_name = "tables/user_levels"
log_file = "log.txt"
debug_log_file_name = "discord.log"

#BOT SETTINGS
token = ""
command_prefix = "/"
param_delim = " "
default_user_level = 1
max_user_level = 3
log_format = "{timestamp}\t{type}\t{server_id}\t{server_name}\t{channel_id}\t{channel_name}\t{user_id}\t{discord_tag}\t{nickname}\t{message_content}\t{data}\t{extra}"
channel_cooldown = 1000
ignore_cd_level = 2
user_cooldown_0 = 60000
user_cooldown_1 = 3000
output_history_size = 10
background_task = None
background_task_interval = 10
enable_debug_logger = False
enable_run_command = False
run_command_name = "run"
run_command_description = "Run a prefix command"
run_command_default_response = "Command ran successfully"

#MESSAGES
message_something_broke = "Something broke"
message_unknown_command = "Command not recognized"
message_unhandled_error = "Unhandled error ({})"
message_result_too_long = "Sorry, the result was too long to output ({}/{} characters)"
message_embed_too_long = "Sorry, the embed was too long to output ({} {}/{} characters)"
message_embed_empty_field = "The output embed was invalid ({} can't be empty)"
message_cooldown_active = "Cooldown active"
message_restricted_access = "You do not have permission to use this command"
message_missing_params = "Missing required parameters: {}"