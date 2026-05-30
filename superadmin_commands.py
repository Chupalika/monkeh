import discord
import yadon, settings
import random

async def shutdown(context, *args, **kwargs):
    return await context.koduck.client.close()

async def send_message(context, channel_id, message_content, *args, **kwargs):
    try:
        channel_id = int(channel_id)
    except ValueError:
        channel_id = -1
    the_channel = context.koduck.client.get_channel(channel_id)
    
    return await context.koduck.send_message(receive_message=context.message, channel=the_channel, content=message_content, ignore_cd=True)

#note: discord server prevents any user, including bots, from changing usernames more than twice per hour
async def change_name(context, username, *args, **kwargs):
    return await context.koduck.client.user.edit(username=username)

async def change_status(context, *args, **kwargs):
    if not context.param_line:
        return await context.koduck.client.change_presence(activity=discord.Game(name=""))
    else:
        return await context.koduck.client.change_presence(activity=discord.Game(name=context.param_line))

#Updates any manual changes to the settings table
async def refresh_settings(context, *args, **kwargs):
    context.koduck.refresh_settings()
    return await context.koduck.send_message(receive_message=context.message, content=settings.message_refresh_settings_success)

#Syncs the slash commands to Discord. This is not done automatically and should be done by running this command if changes were made to the slash commands.
async def refresh_app_commands(context, *args, **kwargs):
    await context.koduck.refresh_app_commands()
    await context.koduck.send_message(receive_message=context.message, content=settings.message_refresh_app_commands_success)

async def add_admin(context, *args, **kwargs):
    #need exactly one mentioned user (the order in the mentioned list is unreliable)
    if len(context.message.raw_mentions) != 1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_no_mentioned_user)
    
    user_id = context.message.raw_mentions[0]
    user_level = context.koduck.get_user_level(user_id)
    
    #already an admin
    if user_level == 2:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_add_admin_failed)
    else:
        context.koduck.update_user_level(user_id, 2)
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_add_admin_success.format(user_id))

async def remove_admin(context, *args, **kwargs):
    #need exactly one mentioned user (the order in the mentioned list is unreliable)
    if len(context.message.raw_mentions) != 1:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_no_mentioned_user)
    
    user_id = context.message.raw_mentions[0]
    user_level = context.koduck.get_user_level(user_id)
    
    #not an admin
    if user_level < 2:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_remove_admin_failed)
    else:
        context.koduck.update_user_level(user_id, 1)
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_remove_admin_success.format(user_id))

#Searches through the past settings.purge_search_limit number of messages in this channel and deletes given number of bot messages
async def purge(context, message_count, *args, **kwargs):
    try:
        limit = int(message_count)
    except (IndexError, ValueError):
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_purge_invalid_param)
    counter = 0
    async for message in context.message.channel.history(limit=settings.purge_search_limit):
        if counter >= limit:
            break
        if message.author.id == context.koduck.client.user.id:
            await message.delete()
            counter += 1