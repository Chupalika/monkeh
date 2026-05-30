# monkeh
Discord bot built from [Koduck](https://github.com/Chupalika/Koduck)!

## About
Most of the features were actually implemented like 5+ years ago. I wanted to clean up the code before uploading but I got lazy and never got around to it. So um, please don't judge my code :) 

`koduck.py`, `main.py`, `superadmin_commands.py`, `admin_commands.py`, `user_commands.py`, `settings.py`, and `yadon.py` are all from Koduck and (should be) unmodified, and can be ignored.

## Setup
1. Get Python 3.9+
2. This bot uses PerformanceCalculator for a lot of its functions. You can find the repository [here](https://github.com/ppy/osu-tools). You will need to build it, and put the files in a folder called `PerformanceCalculator`. This should account for most of the functions, however I do believe I had modified it for a few functions. I may update the details here later.
3. Go to `tables/settings.txt`, fill in your Discord bot token, osu api v1 key, osu api v2 client id and secret
4. Create `tables/user_levels.txt`, and input your Discord user ID, followed by a tab, followed by a `3`
5. Run the bot with `python main.py`
6. The bot starts up successfully when it prints the ID and username in the console without any other error messages
  * You might get some error like `No module named <something>`, in which case you can install it by running `python -m pip install <something>`, then try running the bot again
7. Once it's up and running, run this command once in a Discord channel or DM where your bot can see: `/refreshappcommands`. This will register all the slash commands to Discord, and only needs to be run once, until you add, edit, or remove commands.
