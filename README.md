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
> because it is invasive. Enable it with `"auto_discover_integrations": true` in the `settings` of
> `command_manager.json` only if you trust your plugins.
> <br>Plugins can instead register themselves explicitly, see the [API Documentation](/_for_developers/README.md).

# Installation
> **Upgrading from EasyAsCommands?** Remove the old `endstone_easyascommands-*.whl` from your plugins folder first.
> Your `config/command_manager.json` is reused, and permissions named `easyas.command.*` are automatically
> converted to `customscommands.command.*`.

1) Download the latest [release](../../releases).
2) Drag and drop both files ending with `.whl` into your Endstone plugin folder.
3) Restart or reload your server. Enjoy!

### Demo
<img src="./images/mdemo.png?raw=true">

# Settings
Stored under `"settings"` in `config/command_manager.json`:

**Setting**|**Default**|**Description**
:-----:|:-----:|:-----:
`allow_selectors`|`false`|Lets players pass target selectors (`@a`, `@e`...) as command arguments.
`auto_discover_integrations`|`false`|Scans other plugins' `.whl` files for integrations (invasive).

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
   - If you want to learn more about functionality, see the wiki page [Functionality](../../wiki/Functionality).
   - When you are finished, hit **Submit**, then back out again to the main editor.
5) Click **Submit**, and your server will reload to apply your new command.
6) Now run `/star`; you should be given a nether star.

### *Using JSON Editor*
1) For more advanced users, a more efficient approach is to edit the JSON directly.
To start, navigate to your `/bedrock_server/config/` folder; the `/config/` folder should be in the same directory as your `/plugins/` folder.
2) Open `command_manager.json` in your choice of text editor. You don't need anything fancy; Notepad will do.
3) Begin editing. Refer to the wiki page [JSON Arguments](../../wiki/JSON-Arguments) for available arguments.
Once done, save the file and reload/restart your server for the changes to take effect.

### 🥳 Congratulations!
You've created your first command!

I hope you find this plugin useful! Enjoy!

# Feature Roadmap
**Feature**|**Status**
:-----:|:-----:
Command Manager UI|✅
Reset command|✅
Documentation|🔷
Placeholder Support|🔷
More Execution Types|🔶
Conditions|🔶
Developer API|🔶
Addon Integration|🔶

✅ - Complete
🔷 - Work in Progress
🔶 - Planned

## Feedback
If you experience any issues or have a suggestion, please create an [Issue](../../issues), and I'll try to get to it when I can!
