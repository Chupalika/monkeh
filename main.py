from koduck import Koduck 
import sys, importlib, logging
import yadon
import settings

#Required method to setup Koduck. Can also be run as a comamnd after startup to update any manual changes to the commands table.
async def refresh_commands(context, *args, **kwargs):
    errors = []
    table_items = yadon.ReadTable(settings.commands_table_name, named_columns=True).items()
    if table_items is not None:
        context.koduck.clear_commands()
        for command_name, details in table_items:
            if details["Module Name"] != "main":
                if details["Module Name"] not in sys.modules:
                    try:
                        importlib.import_module(details["Module Name"])
                    except Exception as e:
                        errors.append("Failed to import module '{}': `{}`".format(details["Module Name"], str(e)))
                try:
                    context.koduck.add_command(command_name, getattr(sys.modules[details["Module Name"]], details["Method Name"]), details["Command Type"], int(details["Command Tier"]), details["Description"])
                except Exception as e:
                    errors.append("Failed to import command '{}': `{}`".format(details, str(e)))
            else:
                try:
                    context.koduck.add_command(command_name, globals()[details["Method Name"]], details["Command Type"], int(details["Command Tier"]), details["Description"])
                except Exception as e:
                    errors.append("Failed to import command '{}': `{}`".format(details, str(e)))
    if settings.enable_run_command:
        context.koduck.add_run_slash_command()
    
    errors = "\n".join(errors)
    if context.message is not None:
        if errors:
            await context.koduck.send_message(context.message, content=settings.message_refresh_commands_errors + "\n" + errors)
        else:
            await context.koduck.send_message(context.message, content=settings.message_refresh_commands_success)
    elif errors:
        print(errors)

#Background task is run every set interval while bot is running (by default every 10 seconds)
async def background_task(koduck_instance):
    pass
settings.background_task = background_task

koduck = Koduck()
koduck.add_command("refreshcommands", refresh_commands, "prefix", 3)
if settings.enable_debug_logger:
    log_handler = logging.FileHandler(filename=settings.debug_log_file_name, encoding='utf-8', mode='w')
    koduck.client.run(settings.token, log_handler=log_handler, log_level=logging.DEBUG)
else:
    koduck.client.run(settings.token, log_handler=None)