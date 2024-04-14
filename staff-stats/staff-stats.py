import asyncio
from discord.ext import commands
from core import checks
from core.models import PermissionLevel

class StaffStatsPlugin(commands.Cog):
    """
    Just a plugin which saves staff statistics in the database for frontend stuff.
    """

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.plugin_db.get_partition(self)
        if self.db is None:
            print("Failed to get database partition for the plugin. Plugin will not be loaded.")
            return  # Prevent further initialization if db is not available

        bot.loop.create_task(self._update_stats())

    async def _update_stats(self):
        while True:
            staff_list = []
            category_id = self.bot.config.get("main_category_id")
            if not category_id:
                print("No category ID specified.")
                await asyncio.sleep(86400)
                continue

            category = self.bot.get_channel(int(category_id))
            if not category:
                print("Category channel not found.")
                await asyncio.sleep(86400)
                continue

            for member in self.bot.modmail_guild.members:
                if category.permissions_for(member).read_messages and not member.bot:
                    responded = await self.bot.api.get_responded_logs(member.id)
                    closed = await self.bot.db.logs.find(
                        {
                            "guild_id": str(self.bot.guild_id),
                            "open": False,
                            "closer.id": str(member.id),
                        }
                    ).to_list(None)

                    staff_list.append({
                        "username": str(member),
                        "id": member.id,
                        "closed": len(closed),
                        "responded": len(responded),
                        "avatar": str(member.avatar.url if member.avatar else ""),
                    })

            await self.db.find_one_and_update(
                {"_id": "config"}, {"$set": {"staff": staff_list}}, upsert=True
            )

            await asyncio.sleep(86400)

    @commands.command()
    @checks.has_permissions(PermissionLevel.ADMIN)
    async def syncstaff(self, ctx):
        staff_list = []
        category_id = self.bot.config.get("main_category_id")
        if not category_id:
            await ctx.send("Configuration error: main category ID is missing.")
            return

        category = self.bot.get_channel(int(category_id))
        if not category:
            await ctx.send("Error: The specified channel does not exist.")
            return

        for member in self.bot.modmail_guild.members:
            if category.permissions_for(member).read_messages and not member.bot:
                responded = await self.bot.api.get_responded_logs(member.id)
                closed = await self.bot.db.logs.find(
                    {
                        "guild_id": str(self.bot.guild_id),
                        "open": False,
                        "closer.id": str(member.id),
                    }
                ).to_list(None)

                staff_list.append({
                    "username": str(member),
                    "id": member.id,
                    "closed": len(closed),
                    "responded": len(responded),
                    "avatar": str(member.avatar.url if member.avatar else ""),
                })

        await self.db.find_one_and_update(
            {"_id": "config"}, {"$set": {"staff": staff_list}}, upsert=True
        )

        await ctx.send("Done.")
        return

async def setup(bot):
    try:
        await bot.add_cog(StaffStatsPlugin(bot))
    except Exception as e:
        print(f"Failed to load StaffStatsPlugin: {str(e)}")
