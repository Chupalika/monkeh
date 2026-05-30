import discord
import asyncio
import yadon, settings
import random

#When someone says a trigger message, respond with a custom response!
async def custom_response(context, *args, **kwargs):
    response = yadon.ReadRowFromTable(settings.custom_responses_table_name, context["command"])
    if response:
        return await context.koduck.send_message(receive_message=context.message, content=response[0])

async def oops(context, *args, **kwargs):
    try:
        the_message = context.koduck.output_history[context.message.author.id].pop()
    except (KeyError, IndexError):
        return settings.message_oops_failed
    try:
        if isinstance(the_message, discord.Interaction):
            await the_message.delete_original_response()
        else:
            await the_message.delete()
        return settings.message_oops_success
    except discord.errors.NotFound:
        return await oops(context)

async def slash_oops(interaction):
    try:
        the_message = interaction.command.koduck.output_history[interaction.user.id].pop()
    except (KeyError, IndexError):
        return await interaction.command.koduck.send_message(interaction, content=settings.message_oops_failed, ephemeral=True)
    try:
        if isinstance(the_message, discord.Interaction):
            await the_message.delete_original_response()
        else:
            await the_message.delete()
        return await interaction.command.koduck.send_message(interaction, content=settings.message_oops_success, ephemeral=True)
    except discord.errors.NotFound:
        return await oops(interaction.command)

async def list_commands(context, *args, **kwargs):
    #filter out the commands that the user doesn't have permission to run
    #group the commands by function, multiple aliases for one function will be put in parentheses to indicate that fact to the user
    current_level = context.koduck.get_user_level(context.message.author.id)
    available_commands = {}
    for command_name, command in context.koduck.commands.items():
        if command[2] <= current_level and command[1] == "prefix":
            try:
                available_commands[command[0]].append(command_name)
            except KeyError:
                available_commands[command[0]] = [command_name]
    output = ""
    for function, command_names in available_commands.items():
        if len(command_names) > 1:
            output += "({}), ".format(", ".join(command_names))
        else:
            output += "{}, ".format(command_names[0])
    output = output[:-2]
    return await context.koduck.send_message(receive_message=context.message, content=output)

async def help(context, query="", *args, **kwargs):
    help_message = get_help_message(query)
    if not help_message:
        help_message = get_help_message("unknown_command")
    if help_message:
        return await context.koduck.send_message(receive_message=context.message, content=help_message)

def get_help_message(message_name):
    if message_name:
        help_message = yadon.ReadRowFromTable(settings.help_messages_table_name, "message_help_" + message_name)
    #Default message if no parameter is given
    else:
        help_message = yadon.ReadRowFromTable(settings.help_messages_table_name, "message_help")
    
    #Use {cp} for command prefix and {pd} for parameter delimiter
    if help_message:
        return help_message[0].replace("{cp}", settings.command_prefix).replace("{pd}", settings.param_delim).replace("\\n", "\n").replace("\\t", "\t")
    else:
        return None

async def user_info(context, *args, **kwargs):
    #if there is no mentioned user, use the message sender instead
    if len(context.message.raw_mentions) == 0:
        if context.message.guild is None:
            user = context.message.author
        else:
            user = context.message.guild.get_member(context.message.author.id)
            if user is None:
                user = context.message.author
    elif len(context.message.raw_mentions) == 1:
        if context.message.guild is None:
            user = context.koduck.client.get_user(context.message.raw_mentions[0])
        else:
            user = context.message.guild.get_member(context.message.raw_mentions[0])
            if user is None:
                user = context.koduck.client.get_user(context.message.raw_mentions[0])
    else:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_no_mentioned_user_2)
    
    if user is None:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_userinfo_no_result)
    
    username = user.name
    discr = user.discriminator
    avatar = user.display_avatar
    creation_date = user.created_at
    
    #these properties only appear in Member object (subclass of User) which is only available from Servers
    if isinstance(user, discord.Member):
        activities = user.activities
        join_date = user.joined_at
        color = user.color
        if len(activities) == 0:
            embed = discord.Embed(title="{}#{}".format(username, discr), description=str(user.status), color=color)
        else:
            desc = ""
            for activity in activities:
                if isinstance(activity, discord.CustomActivity):
                    desc += "{}\n".format(activity)
                else:
                    type_string = {discord.ActivityType.playing: "Playing", discord.ActivityType.streaming: "Streaming", discord.ActivityType.listening: "Listening", discord.ActivityType.watching: "Watching", discord.ActivityType.unknown: "unknown"}[activity.type]
                    desc += "{} {}\n".format(type_string, activity.name)
            embed = discord.Embed(title="{}#{}".format(username, discr), description=desc, color=color)
        embed.add_field(name="Account creation date", value=creation_date.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
        embed.add_field(name="Server join date", value=join_date.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
        embed.set_thumbnail(url=avatar.url)
        return await context.koduck.send_message(receive_message=context.message, embed=embed)
    else:
        embed = discord.Embed(title="{}#{}".format(username, discr), description="Account creation date: {}".format(creation_date.strftime("%Y-%m-%d %H:%M:%S UTC")))
        embed.set_thumbnail(url=avatar.url)
        return await context.koduck.send_message(receive_message=context.message, embed=embed)

async def roll(context, max_value=None, *args, **kwargs):
    if max_value:
        try:
            max = int(max_value)
        except ValueError:
            max = settings.roll_default_max
    else:
        max = settings.roll_default_max
    
    if max >= 0:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_roll_result.format(context.message.author.mention, random.randint(0, max)))
    else:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_roll_result.format(context.message.author.mention, random.randint(max, 0)))

async def request_roles(context, *args, **kwargs):
    if context.message.guild is None:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_request_roles_no_guild)
    
    role_ids = yadon.ReadRowFromTable(settings.requestable_roles_table_name, context.message.guild.id)
    
    if role_ids is None or len(role_ids) == 0:
        return await context.koduck.send_message(receive_message=context.message, content=settings.message_request_roles_no_roles)
    
    requestable_roles = []    
    for role_id in role_ids:
        role = context.message.guild.get_role(int(role_id))
        if role is None:
            continue
        requestable_roles.append(role)
    
    async def add_role(member, role_id):
        role = context.message.guild.get_role(int(role_id))
        try:
            await member.add_roles(role)
            return True
        except discord.errors.Forbidden:
            return False
        
    async def remove_role(member, role_id):
        role = context.message.guild.get_role(int(role_id))
        try:
            await member.remove_roles(role)
            return True
        except discord.errors.Forbidden:
            return False
    
    class RoleButton(discord.ui.Button):
        async def callback(self, interaction):
            response_string = ""
            new_roles = context.message.author.roles
            
            #check user
            if interaction.user.id != context.message.author.id:
                response_string = interaction.user.mention + " " + settings.message_request_roles_wrong_user
            else:
                #toggle role and update view
                if self.style == discord.ButtonStyle.success:
                    succeeded = await add_role(interaction.user, self.role.id)
                    if succeeded:
                        response_string = interaction.user.mention + " " + settings.message_request_roles_add_role_success.format(self.label)
                        new_roles.append(self.role)
                    else:
                        response_string = interaction.user.mention + " " + settings.message_request_roles_add_role_failed.format(self.label)
                elif self.style == discord.ButtonStyle.danger:
                    succeeded = await remove_role(interaction.user, self.role.id)
                    if succeeded:
                        response_string = interaction.user.mention + " " + settings.message_request_roles_remove_role_success.format(self.label)
                        new_roles.remove(self.role)
                    else:
                        response_string = interaction.user.mention + " " + settings.message_request_roles_remove_role_failed.format(self.label)
            
            new_message_content = interaction.message.content + "\n" + response_string
            new_view = create_view(self.roles, new_roles)
            await interaction.response.edit_message(content=new_message_content, view=new_view)
    
    def create_view(requestable_roles, user_roles):
        the_view = discord.ui.View(timeout=60)
        for role in requestable_roles:
            has_role = role in user_roles
            style = discord.ButtonStyle.danger if has_role else discord.ButtonStyle.success
            #button labels have 80 character limit, while role names have 100 character limit
            the_button = RoleButton(style=style, label=role.name[:80])
            the_button.roles = requestable_roles
            the_button.role = role
            the_view.add_item(the_button)
        return the_view
    
    #set up initial view and send it
    the_view = create_view(requestable_roles, context.message.author.roles)
    message_content = context.message.author.mention + " " + settings.message_request_roles_start
    the_message = await context.koduck.send_message(receive_message=context.message, content=message_content, view=the_view)
    timed_out = await the_view.wait()
    if timed_out:
        #re-fetch the message to get the latest message content
        latest_message = await the_message.channel.fetch_message(the_message.id)
        message_content = latest_message.content + "\n" + settings.message_request_roles_finished
        await the_message.edit(content=message_content, view=None)

async def ping(interaction, delay: int):
    await interaction.response.defer(thinking=True)
    await asyncio.sleep(delay)
    await interaction.command.koduck.send_message(interaction, content="pong")