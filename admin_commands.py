import yadon, settings
from user_commands import custom_response

async def update_setting(context, setting_name, new_value, *args, **kwargs):
    result = context.koduck.update_setting(setting_name, new_value, context.koduck.get_user_level(context.message.author.id))
    if result is not None:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_update_setting_success.format(setting_name, result, new_value))
    else:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_update_setting_failed)

async def add_setting(context, setting_name, value, *args, **kwargs):
    result = context.koduck.add_setting(setting_name, value, context.koduck.get_user_level(context.message.author.id))
    if result is not None:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_add_setting_success)
    else:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_add_setting_failed)

async def remove_setting(context, setting_name, *args, **kwargs):
    result = context.koduck.remove_setting(setting_name, context.koduck.get_user_level(context.message.author.id))
    if result is not None:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_remove_setting_success)
    else:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_remove_setting_failed)

async def restrict_user(context, *args, **kwargs):
    #need exactly one mentioned user (the order in the mentioned list is unreliable)
    if len(context.message.raw_mentions) != 1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_no_mentioned_user)
    
    user_id = context.message.raw_mentions[0]
    user_level = context.koduck.get_user_level(user_id)
    
    #already restricted
    if user_level == 0:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_restrict_failed)
    #don't restrict high level users
    elif user_level >= 2:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_restrict_failed_2.format(settings.botname))
    else:
        context.koduck.update_user_level(user_id, 0)
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_restrict_success.format(user_id, settings.botname))

async def unrestrict_user(context, *args, **kwargs):
    #need exactly one mentioned user (the order in the mentioned list is unreliable)
    if len(context.message.raw_mentions) != 1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_no_mentioned_user)
    
    user_id = context.message.raw_mentions[0]
    user_level = context.koduck.get_user_level(user_id)
    
    if user_level != 0:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_unrestrict_failed)
    else:
        context.koduck.update_user_level(user_id, 1)
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_unrestrict_success.format(user_id, settings.botname))

async def add_response(context, trigger, response, *args, **kwargs):
    result = yadon.AppendRowToTable(settings.custom_responses_table_name, trigger, [response])
    if result == -1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_add_response_failed)
    else:
        yadon.WriteRowToTable(settings.commands_table_name, trigger, ["admin_commands", "custom_response", "match", "1"])
        context.koduck.add_command(trigger, custom_response, "match", 1)
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_add_response_success.format(trigger, response))

async def remove_response(context, trigger, *args, **kwargs):
    result = yadon.RemoveRowFromTable(settings.custom_responses_table_name, trigger)
    if result == -1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_remove_response_failed.format(trigger))
    else:
        yadon.RemoveRowFromTable(settings.commands_table_name, trigger)
        context.koduck.remove_command(trigger)
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_remove_response_success)

async def add_requestable_roles(context, *args, **kwargs):
    if not context.message.role_mentions:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_add_requestable_roles_no_role)
    
    role_ids = yadon.ReadRowFromTable(settings.requestable_roles_table_name, context.message.guild.id)
    if role_ids is None:
        role_ids = []
    role_ids = set(role_ids)
    for role in context.message.role_mentions:
        role_ids.add(str(role.id))
    yadon.WriteRowToTable(settings.requestable_roles_table_name, context.message.guild.id, list(role_ids))
    
    return await context.koduck.send_message(receive_message=context.message, content=settings.message_add_requestable_roles_success)

async def remove_requestable_roles(context, *args, **kwargs):
    if not context.message.role_mentions:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_remove_requestable_roles_no_role)
    
    role_ids = yadon.ReadRowFromTable(settings.requestable_roles_table_name, context.message.guild.id)
    if role_ids is None:
        role_ids = []
    role_ids = set(role_ids)
    for role in context.message.role_mentions:
        role_ids.remove(str(role.id))
    yadon.WriteRowToTable(settings.requestable_roles_table_name, context.message.guild.id, list(role_ids))
    
    return await context.koduck.send_message(receive_message=context.message, content=settings.message_remove_requestable_roles_success)