import logging
from maubot import Plugin, MessageEvent
from maubot.handlers import command
from sqlitedict import SqliteDict
from plugins.handle_notes import add_to_db, remove_from_db
from plugins.refresh import refresh, verify_and_add_rooms, add_invited_room
from plugins.run_command import get_by_command
from plugins.perms import has_permissions, add_user, remove_user
import nio

# Set up logging
logger = logging.getLogger(__name__)

try:
    db = SqliteDict("db/db.sqlite")
except Exception as e:
    logger.error(f"Failed to connect to the database: {e}")
    raise

class MyBot(Plugin):
    async def start(self) -> None:
        try:
            self.rooms = refresh()
        except Exception as e:
            logger.error(f"Failed to refresh rooms: {e}")
            raise

    @command.new("help")
    async def help_command(self, evt: MessageEvent) -> None:
        try:
            with open('resources/help_text.txt', 'r') as test:
                await evt.reply(test.read())
        except FileNotFoundError:
            logger.error("Help text file not found")
            await evt.reply("Error! Help text file not found.")
        except Exception as e:
            logger.error(f"Failed to read help text file: {e}")
            await evt.reply("Error! Failed to read help text file.")

    @command.new("add")
    async def add_command(self, evt: MessageEvent) -> None:
        try:
            if has_permissions(evt.room_id, evt.sender, self.rooms):
                add_msg = add_to_db(evt.content.body, evt.room_id)
                self.rooms = refresh()
                await evt.reply(add_msg)
            else:
                await evt.reply('Error! You do not have permission to add notes!')
        except Exception as e:
            logger.error(f"Failed to add note: {e}")
            await evt.reply("Error! Failed to add note.")

    @command.new("remove")
    async def remove_command(self, evt: MessageEvent) -> None:
        try:
            if has_permissions(evt.room_id, evt.sender, self.rooms):
                args = evt.args
                if len(args) != 1:
                    await evt.reply('Error! Please input a valid command to remove! Check `!help` for usage examples')
                elif not args[0] in self.rooms[evt.room_id]['messages']:
                    await evt.reply(f'Error! Command `{args[0]}` not found')
                else:
                    remove_msg = remove_from_db(args[0], evt.room_id)
                    self.rooms = refresh()
                    await evt.reply(remove_msg)
            else:
                await evt.reply('Error! You do not have permission to remove notes!')
        except Exception as e:
            logger.error(f"Failed to remove note: {e}")
            await evt.reply("Error! Failed to remove note.")

    @command.new("list")
    async def list_command(self, evt: MessageEvent) -> None:
        try:
            if len(self.rooms[evt.room_id]['messages']) == 0:
                await evt.reply('No saved notes found!')
            else:
                await evt.reply('**Saved Notes** \n' + "\n".join('- ' + str(item) for item in self.rooms[evt.room_id]['messages']))
        except Exception as e:
            logger.error(f"Failed to list notes: {e}")
            await evt.reply("Error! Failed to list notes.")

    @command.new("sync")
    async def sync_db_command(self, evt: MessageEvent) -> None:
        try:
            if evt.sender == '@matchstick:beeper.com':
                joined_rooms = self.client.rooms
                verify_and_add_rooms(joined_rooms)
                self.rooms = refresh()
        except Exception as e:
            logger.error(f"Failed to sync database: {e}")
            await evt.reply("Error! Failed to sync database.")

    @command.new("add_user")
    async def add_allowed_user_command(self, evt: MessageEvent) -> None:
        try:
            if has_permissions(evt.room_id, evt.sender, self.rooms):
                response = add_user(evt.content.formatted_body, evt.room_id)
                self.rooms = refresh()
                await evt.reply(response)
            else:
                await evt.reply('Error! You do not have permission to add users to the allowlist!')
        except Exception as e:
            logger.error(f"Failed to add user: {e}")
            await evt.reply("Error! Failed to add user.")

    @command.new("remove_user")
    async def remove_allowed_user_command(self, evt: MessageEvent) -> None:
        try:
            if has_permissions(evt.room_id, evt.sender, self.rooms):
                response = remove_user(evt.content.formatted_body, evt.room_id)
                self.rooms = refresh()
                await evt.reply(response)
            else:
                await evt.reply('Error! You do not have permission to remove users from the allowlist!')
        except Exception as e:
            logger.error(f"Failed to remove user: {e}")
            await evt.reply("Error! Failed to remove user.")

    @command.passive(regex=r"^!(?P<command>\w+)$")
    async def send_command(self, evt: MessageEvent, match) -> None:
        try:
            if match.group('command') not in ['add', 'remove', 'add_user', 'list', 'sync', 'help'] and match.group('command') in self.rooms[evt.room_id]['messages']:
                message_text = get_by_command(match.group('command'), evt.room_id)
                await evt.reply(message_text)
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            await evt.reply("Error! Failed to send command.")