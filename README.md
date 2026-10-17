<a href="../../"><img src="./images/badge.png?raw=true" width="128"></a><br>
<div align="left">
  
[![view - Documentation](https://img.shields.io/badge/view-Documentation-blue?style=for-the-badge)](../../wiki/ "Go to project documentation")

[![view - API](https://img.shields.io/badge/view-Developer_API-red?style=for-the-badge)](/_for_developers/README.md "Go to project documentation")

</div>

# CustomsCommands
A plugin for [Endstone](https://github.com/EndstoneMC/endstone) that allows you to setup your own slash commands without any programming!

> Based on [EasyAsCommands](https://github.com/palmmc/EasyAsCommands) by palm1.

## ⚠️ Integration Support
> Automatic discovery of integrations (scanning other plugins' `.whl` files) is **disabled by default**
> because it is invasive. Enable it with `"auto_discover_integrations": true` in `config.json`
> only if you trust your plugins.
> <br>Plugins can instead register themselves explicitly, see the [API Documentation](/_for_developers/README.md).

# Installation
> **Upgrading from EasyAsCommands?** Remove the old `endstone_easyascommands-*.whl` from your plugins folder first.
> Your `config/command_manager.json` is **moved automatically** into the plugin's data folder
> (`plugins/customscommands/`) the first time the plugin starts, and permissions named `easyas.command.*` are
> converted to `customscommands.command.*`. The old file is kept as `command_manager.json.migrated`.

1) Download the latest [release](../../releases).
2) Drag and drop both files ending with `.whl` into your Endstone plugin folder.
3) Restart or reload your server. Enjoy!

### Demo
<img src="./images/mdemo.png?raw=true">

# Data folder
Like any plugin, CustomsCommands keeps its files in `plugins/customscommands/`:

**File / folder**|**Content**
:-----:|:-----:
`config.json`|The settings (see below).
`commands.json`|Your commands and their executions.
`lang/`|Translations: every text of the plugin can be customised.
`exports/`|Files created by **Export** (and where **Import** reads from).
`backups/`|Automatic backups made before a reset or an import (the last 20 are kept).
`data/usage.json`|Usage counters for usage limits.

# Settings
Stored in `plugins/customscommands/config.json`:

**Setting**|**Default**|**Description**
:-----:|:-----:|:-----:
`language`|`"en_US"`|Language file used for every text (`lang/<language>.json`). See [Translations](../../wiki/Translations).
`page_size`|`8`|Commands shown per page in the manager (3 to 20).
`integrations`|see wiki|Turns StonePerms / MediaPlayer / PlaceholderAPI support on or off and holds the MediaPlayer command templates. See [Integrations](../../wiki/Integrations).
`allow_selectors`|`false`|Lets players pass target selectors (`@a`, `@e`...) as command arguments.
`auto_discover_integrations`|`false`|Scans other plugins' `.whl` files for integrations (invasive).
`custom_permission_default`|`"op"`|Who has the specific permissions (`customscommands.custom.<command>`) by default: `"op"` or `"everyone"`. Needs a reload.

# Specific permission per command
Every command can have its own permission, named `customscommands.custom.<command>` (for example `customscommands.custom.helloworld`).
- In the manager: **Manage Permissions → Add Specific Permission** (the command needs a name first).
- The plugin declares these permissions automatically. By default only operators have them (`custom_permission_default`), so you can grant them to groups or players with a permissions plugin. Use `"everyone"` to give them to all players.
- Renaming a command renames its specific permission and its usages too.

# Translations
Every message and every UI text is a key in `plugins/customscommands/lang/en_US.json`. Edit that file to change any wording, or
create another file (for example `fr_FR.json`) containing only the keys you translate, then set `"language": "fr_FR"` in
`config.json`. Missing keys fall back to English. Apply changes with `/ccreload`. See [Translations](../../wiki/Translations).

# Export / Import
In the manager, **Export / Import** saves all your commands in `exports/` and imports commands from a file (add new ones, overwrite
same-named ones, or replace everything). Every imported command is validated, and a backup is made first.
See [Export and Import](../../wiki/Export-and-Import).

# Argument rules and usage limits
- **Manage Arguments** limits what players may type: a list of allowed values or a number range. See [Argument Rules](../../wiki/Argument-Rules).
- **Set Usage Limit** limits how many times each player may use a command, for good or per period. See [Usage Limits](../../wiki/Usage-Limits).
- Each execution line can have its own **conditions** and the lines can be reordered.

# Integrations (optional dependencies)
CustomsCommands works with other plugins when they are installed. Their features are listed under **Dependencies** in the editor
(and **Command Manager → Dependencies** shows their state). See [Integrations](../../wiki/Integrations).

**Plugin**|**Adds**
:-----:|:-----:
[StonePerms](https://github.com/Daniel-Ric/StonePerms)|Executions to add/remove groups, set/unset permissions (also temporary) and promote players.
[MediaPlayer](https://github.com/ReallocAll/endstone-mediaplayer)|Executions to play, pause, resume and stop `.nbs` music. Its `/mpm` command templates are configurable.
[PlaceholderAPI for Endstone](https://pypi.org/project/endstone-papi/)|`{identifier:params}` placeholders in executions and conditions.

Each one can be turned off in `config.json` (`integrations`).

# Security
Custom commands run on the **console**, so player input is validated before it is placed in a command:
- Arguments can't contain quotes, backslashes, line breaks or other control characters, and are limited to 256 characters.
- Target selectors (`@a`, `@e`...) are refused unless `allow_selectors` is enabled.
- An argument containing spaces is only accepted when the placeholder is written between quotes in the command
  (e.g. `say "{0}"`). `{player}` is quoted automatically when needed.
- A placeholder can't be used as the command name itself (e.g. `{0}` alone).
- A missing argument stops the whole command before anything is executed.
- Names, aliases, usages and permissions are validated when saving a command, and every modification re-checks the manager permission.

# Features
- ## Manager UI
  - Create, remove, and edit slash commands using a simple UI.
  - Configure the name, description, arguments, aliases, and permissions.
  - Add functionality on command execution.
  - Set a cooldown and conditions for each command.

# Execution Types
Each command runs its **functionality** lines in order. Lines are checked before anything runs: if one of them is refused, none is executed.

**Type**|**What it does**|**Example content**
:-----:|:-----:|:-----:
`command`|Runs a server command as the console.|`give "{player}" diamond {1}`
`player_command`|Runs a command **as the player**, with their own permissions.|`spawn`
`message`|Sends a chat message to the player.|`§aHello {player}!`
`broadcast`|Sends a chat message to everyone.|`{player} used the command`
`title`|Shows a title (and optional subtitle after `\|`).|`Welcome\|{player}`
`popup`|Shows a popup above the hotbar.|`Hello {player}`
`delay`|Waits N seconds before the **following** lines (max 3600).|`5`

# Placeholders
**Placeholder**|**Value**
:-----:|:-----:
`{player}`|Name of the player running the command.
`{0}`, `{1}`...|The command's arguments.
`{score:objective}`|The player's scoreboard score.
`{x}` `{y}` `{z}`|The player's block coordinates.
`{dimension}`|Dimension name (e.g. `Overworld`).
`{gamemode}`|Game mode in lowercase (e.g. `survival`).
`{health}`|The player's health, rounded.
`{ping}`|The player's ping.
`{online}`|Number of players online.
`{uuid}`|The player's unique id.
`{time}` / `{date}`|Server time (`HH:MM`) / date (`YYYY-MM-DD`).
`{random:min:max}`|A random whole number between `min` and `max`.

> Some values (`{health}`, `{ping}`, `{gamemode}`, `{x}`...) depend on your Endstone version. If one isn't available,
> the player gets a clear error and nothing is executed.

# Conditions & Cooldowns
In the manager, use **Manage Conditions** and **Set Cooldown** when editing a command. They are saved in the JSON as
`"conditions"` and `"cooldown"` (seconds, per player).

- A command runs only if **every condition** is met. If one isn't, the player sees its message and nothing runs
  (the cooldown isn't consumed).
- **`expression`**: `<value> <operator> <value>` with `==`, `!=`, `>=`, `<=`, `>`, `<`. Placeholders are allowed
  (`{score:kills} >= 5`, `{health} > 10`, `{0} == yes`). Numbers are compared as numbers, text only with `==`/`!=`.
- **`permission`**: the player must have the given permission node.
- Operators are read from the condition itself, never from player input, so an argument can't change the test.
- Operators and other admins with `customscommands.cooldown.bypass` ignore cooldowns.

```json
"conditions": [
    { "type": "expression", "content": "{score:kills} >= 5", "message": "You need 5 kills first!" }
],
"cooldown": 60
```

# Commands
- `/commands` - `customscommands.command.manager`
- `/resetcommands` - `customscommands.command.reset`

# Tutorial
### *Using In-Game UI*
1) With **operator** or the `customscommands.command.manager` permission, run the `/commands` command.
2) This is where you can add, remove, and edit existing commands.
   - Next click 'Add Command'.
3) Here you can configure all of the different attributes of your command.
   - For more information, refer to the wiki page, [Command Attributes](../../wiki/Command-Attributes).
   - Try creating the following command:
     - Set the name to '`star`'.
     - Add a new usage '`/star`'.
     - Add the permission '`customscommands.command.all`'.
   - After that, scroll to the bottom and click **Functionality**.
4) This is where you can make the command *do* something when it is executed. Let's do a simple example.
   - Click 'Add Execution', select 'Command', and type '`give "{player}" nether_star 1`'.
   - If you want to learn more about functionality, see the wiki page [Execution Types](../../wiki/Execution-Types).
   - When you are finished, hit **Submit**, then back out again to the main editor.
5) Click **Submit**, and your server will reload to apply your new command.
6) Now run `/star`; you should be given a nether star.

### *Using JSON Editor*
1) For more advanced users, a more efficient approach is to edit the JSON directly.
To start, open the `plugins/customscommands/` folder of your server.
2) Open `commands.json` in your choice of text editor. You don't need anything fancy; Notepad will do.
3) Begin editing. Refer to the wiki page [Configuration](../../wiki/Configuration) for available keys.
Once done, save the file and reload/restart your server for the changes to take effect.

### 🥳 Congratulations!
You've created your first command!

I hope you find this plugin useful! Enjoy!

# Feature Roadmap
**Feature**|**Status**
:-----:|:-----:
Command Manager UI|✅
Reset command|✅
Documentation|✅
Placeholder Support|✅
More Execution Types|✅
Conditions & Cooldowns|✅
Developer API|✅
Translations|✅
Export / Import|✅
Argument rules & usage limits|✅
Addon Integration|✅

✅ - Complete
🔷 - Work in Progress
🔶 - Planned

## Feedback
If you experience any issues or have a suggestion, please create an [Issue](../../issues), and I'll try to get to it when I can!
