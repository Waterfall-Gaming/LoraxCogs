from datetime import datetime, timezone, timedelta

import calendar
import string
import random

import discord
from redbot.core import Config, commands
from redbot.core.commands.requires import PrivilegeLevel


class WaterfallVerification(commands.Cog):
  """Waterfall Custom Verification cog, idk how it'll work yet."""

  default_guild_settings = {
    "VERIFICATION_CHANNEL": None,
    "VERIFICATION_ROLE": None,
    "UNVERIFIED_ROLE": None,
    "VERIFICATION_CODE_LENGTH": 6,
    "VERIFICATION_CODE_TYPE": "alphanumeric",
    "VERIFICATION_CODE_EXPIRY": 300
  }

  default_global_settings = default_guild_settings

  default_member_settings = {
    "verified": False,
    "verification_code": None,
    "code_expires_at": None,
    "verified_at": None
  }

  default_user_settings = default_member_settings

  def __init__(self, bot):
    super().__init__()
    self.bot = bot

    self.config = Config.get_conf(self, 0x77672e766572696679)
    self.config.register_guild(**self.default_guild_settings)
    self.config.register_global(**self.default_global_settings)
    self.config.register_member(**self.default_member_settings)
    self.config.register_user(**self.default_user_settings)

  @commands.group(name="verifyset")
  @commands.admin()
  async def command_verifyset(self, ctx):
    """Settings for the verification cog."""
    pass

  @command_verifyset.command(name="channel")
  async def command_verifyset_channel(self, ctx, channel: discord.TextChannel):
    """Set the verification channel. This is where users must run the verification command."""
    await self.config.guild(ctx.guild).VERIFICATION_CHANNEL.set(channel.id)
    await ctx.send(f"Verification channel set to {channel.mention}.")

  @command_verifyset.command(name="role")
  async def command_verifyset_role(self, ctx, role: discord.Role):
    """Set the verification role. This role will be given to users who have successfully verified."""
    await self.config.guild(ctx.guild).VERIFICATION_ROLE.set(role.id)
    await ctx.send(f"Verification role set to {role.mention}.")

  @command_verifyset.command(name="unverifiedrole")
  async def command_verifyset_unverifiedrole(self, ctx, role: discord.Role):
    """Set the unverified role. This role will be given to users who have not verified."""
    await self.config.guild(ctx.guild).UNVERIFIED_ROLE.set(role.id)
    await ctx.send(f"Unverified role set to {role.mention}.")

  @command_verifyset.group(name="code")
  async def command_verifyset_code(self, ctx):
    """Settings for verification codes."""
    pass

  @command_verifyset_code.command(name="length")
  async def command_verifyset_code_length(self, ctx, length: int):
    """Set the length of the verification code."""
    if length < 1:
      await ctx.send("The verification code length must be at least 1.")
      return
    elif length > 32:
      await ctx.send("The verification code must not be longer than 32 characters.")
      return
    await self.config.guild(ctx.guild).VERIFICATION_CODE_LENGTH.set(length)
    await ctx.send(f"Verification code length set to {length}.")

  @command_verifyset_code.command(name="type")
  async def command_verifyset_code_type(self, ctx, code_type: str):
    """Set whether the verification code should be alphanumeric."""
    # Check if the code type is valid
    if code_type not in ["alphanumeric", "numeric", "alphabetical"]:
      await ctx.send("The verification code type must be either alphanumeric, numeric or alphabetical.")
      return
    # update the config
    await self.config.guild(ctx.guild).VERIFICATION_CODE_TYPE.set(code_type)
    await ctx.send(f"Verification codes will now be {code_type}.")

  @command_verifyset_code.command(name="expiry")
  async def command_verifyset_code_expiry(self, ctx, expiry: int):
    """Set the expiry time for verification codes (in seconds)."""
    if expiry < 60 and expiry != 0:
      await ctx.send("The expiry time for verification codes must be at least 60 seconds. (or 0 to disable expiry)")
      return

    if expiry > 86400:
      await ctx.send("The expiry time for verification codes must be less than 86400 seconds (24 hours).")
      return

    await self.config.guild(ctx.guild).VERIFICATION_CODE_EXPIRY.set(expiry)
    if expiry == 0:
      await ctx.send("Verification codes will no longer expire.")
    else:
      await ctx.send(f"Verification codes will now expire after {expiry} seconds.")

  @commands.group(name="unverify")
  @commands.admin()
  async def command_unverify(self, ctx, user: discord.Member):
    """Unverify a user/users."""
    pass

  @command_unverify.command(name="user")
  async def command_unverify_user(self, ctx, user: discord.Member):
    """Unverify a user."""
    # remove verified status
    await self.config.member(user).verified.set(False)
    # remove verification timestamp
    await self.config.member(user).verified_at.set(None)
    # remove verification code
    await self.config.member(user).verification_code.set(None)
    # remove verification code expiry
    await self.config.member(user).code_expires_at.set(None)
    # remove the verification role
    await user.remove_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).VERIFICATION_ROLE()))
    # add the unverified role if it exists
    if await self.config.guild(ctx.guild).UNVERIFIED_ROLE() is not None:
      await user.add_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).UNVERIFIED_ROLE()))

    info_embed = discord.Embed(
      title="User Unverified",
      description=f"{user.mention} has been unverified.",
      color=discord.Color.dark_red()
    )

    info_embed.set_footer(text=f"Action performed by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)

    await ctx.send(embed=info_embed)

  @command_unverify.command(name="inactive")
  async def command_unverify_inactive(self, ctx, days: int, dry_run: bool = False):
    """DANGEROUS: Unverify users who haven't sent messages in a certain number of days."""
    if days < 60:
      await ctx.send("The number of days must be at least 60.")
      return

    current_time = datetime.now(timezone.utc)
    inactive_time = current_time - timedelta(days=days)

    active_users = set()
    inactive_users = set()
    verified_role = ctx.guild.get_role(await self.config.guild(ctx.guild).VERIFICATION_ROLE())

    for channel in ctx.guild.text_channels:
      async for message in channel.history(after=inactive_time):
        if message.author.bot or message.author in active_users:
          continue
        active_users.add(message.author)

    for member in verified_role.members:
      if member not in active_users:
        if not dry_run:
          # unverify the user if it's not a dry run
          await self.config.member(member).verified.set(False)
          await self.config.member(member).verified_at.set(None)
          await self.config.member(member).verification_code.set(None)
          await self.config.member(member).code_expires_at.set(None)
          await member.remove_roles(verified_role)
          if await self.config.guild(ctx.guild).UNVERIFIED_ROLE() is not None:
            await member.add_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).UNVERIFIED_ROLE()))
        inactive_users.add(member)

    info_embed = discord.Embed(
      title="Inactive Users Unverified" + (" (Dry Run)" if dry_run else ""),
      description=f"{len(inactive_users)} users have been unverified.",
      color=discord.Color.dark_red()
    )

    info_embed.add_field(name="Users Flagged", value="\n".join([user.mention for user in inactive_users]), inline=False)

    info_embed.set_footer(text=f"Action performed by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)

    await ctx.send(embed=info_embed)

  @commands.group(name="syncverify")
  @commands.admin()
  async def command_syncverify(self, ctx):
    """Refresh the verification status of a user/users."""
    pass

  @command_syncverify.command(name="all")
  async def command_syncverify_all(self, ctx):
    """DANGEROUS COMMAND: Refresh the verification status of all users based on what the bot has configured."""
    ctx.send("This command is not yet implemented.")

  @command_syncverify.command(name="user")
  async def command_syncverify_user(self, ctx, user: discord.Member):
    """Refresh the verification status of a user."""
    verified = await self.config.member(user).verified()

    if verified:
      # give the user the verified role and remove the unverified role
      await user.add_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).VERIFICATION_ROLE()))
      if await self.config.guild(ctx.guild).UNVERIFIED_ROLE() is not None:
        await user.remove_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).UNVERIFIED_ROLE()))
    else:
      # remove the verified role and add the unverified role
      await user.remove_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).VERIFICATION_ROLE()))
      if await self.config.guild(ctx.guild).UNVERIFIED_ROLE() is not None:
        await user.add_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).UNVERIFIED_ROLE()))

  @commands.command(name="bypassverify")
  @commands.admin()
  async def command_bypassverify(self, ctx, user: discord.Member):
    """Bypass the verification process for a user."""
    if await self.config.member(user).verified():
      await ctx.send(embed=discord.Embed(
        title="Error",
        description=f"{user.mention} is already verified."
      ))
      return
    # set the user as verified
    await self.config.member(user).verified.set(True)
    # set the time the user was verified
    await self.config.member(user).verified_at.set(datetime.now().timestamp())
    # add the verification role and remove the unverified role
    await user.add_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).VERIFICATION_ROLE()))
    if await self.config.guild(ctx.guild).UNVERIFIED_ROLE() is not None:
      await user.remove_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).UNVERIFIED_ROLE()))

    info_embed = discord.Embed(
      title="Verification Bypassed",
      description=f"{user.mention} has been manually verified.",
      color=discord.Color.gold()
    )

    info_embed.set_footer(text=f"Action performed by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)

    await ctx.send(embed=info_embed)

  @commands.command(name="verify")
  async def command_verify(self, ctx):
    """Verify yourself to gain access to the server."""

    # Check if the verification channel has been set up
    if await self.config.guild(ctx.guild).VERIFICATION_CHANNEL() is None:
      await ctx.send(embed=discord.Embed(
        title="Error",
        description="The verification channel has not been set up. Please contact an administrator.",
        color=discord.Color.red()
      ))
      return

    # check if a verification role has been set up
    if await self.config.guild(ctx.guild).VERIFICATION_ROLE() is None:
      await ctx.send(embed=discord.Embed(
        title="Error",
        description="The verification role has not been set up. Please contact an administrator.",
        color=discord.Color.red()
      ))
      return

    # check if the user is already verified
    if await self.config.member(ctx.author).verified():
      await ctx.send(embed=discord.Embed(
        title="Error",
        description="You have already been verified.",
        color=discord.Color.red()
      ))
      return

    verification_channel = ctx.guild.get_channel(await self.config.guild(ctx.guild).VERIFICATION_CHANNEL())

    if ctx.message.channel.id != verification_channel.id:
      await ctx.send(embed=discord.Embed(
        title="Error",
        description=f"Please run the verification command in {verification_channel.mention}.",
        color=discord.Color.red()
      ))
      return

    current_time = calendar.timegm(ctx.message.created_at.utctimetuple())

    code_length = await self.config.guild(ctx.guild).VERIFICATION_CODE_LENGTH()
    code_type = await self.config.guild(ctx.guild).VERIFICATION_CODE_TYPE()
    code_expiry = await self.config.guild(ctx.guild).VERIFICATION_CODE_EXPIRY()
    expires_at = await self.config.member(ctx.author).code_expires_at()

    if code_type == "alphanumeric":
      char_pool = string.ascii_letters + string.digits
    elif code_type == "numeric":
      char_pool = string.digits
    elif code_type == "alphabetical":
      char_pool = string.ascii_letters
    else:
      # fallback if the code type is invalid
      char_pool = "!"

    code = await self.config.member(ctx.author).verification_code()
    # if the user doesn't have a code, generate a new one
    if code is None:
      code = "".join(random.choices(char_pool, k=code_length))
      await self.config.member(ctx.author).verification_code.set(code)
      await self.config.member(ctx.author).code_expires_at.set(ctx.message.created_at.timestamp() + code_expiry)

    # if the code has expired, generate a new one
    elif expires_at <= ctx.message.created_at.timestamp() and code_expiry != 0:
      code = "".join(random.choices(char_pool, k=code_length))
      await self.config.member(ctx.author).verification_code.set(code)
      await self.config.member(ctx.author).code_expires_at.set(ctx.message.created_at.timestamp() + code_expiry)

    expires_at = await self.config.member(ctx.author).code_expires_at()
    expires_at_timestamp = discord.utils.format_dt(
      datetime.now(timezone.utc) + timedelta(seconds=expires_at - current_time), "R"
    )

    message = f"Your verification code is: `{code}`\n\n" \
              + f"Please send a message containing __only__ this code in {verification_channel.mention}.\n\n" \
              + (f"This code will expire {expires_at_timestamp}, so make sure you verify quickly!" if code_expiry != 0 else '')

    verification_embed = discord.Embed(
      title="Verification Code",
      description=message,
      color=discord.Color.blue(),
      timestamp=ctx.message.created_at,
    )

    verification_embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url)

    await ctx.author.send(embed=verification_embed)
    await ctx.message.delete(delay=5.0)

  @commands.command(name="verifyinfo")
  async def command_verifyinfo(self, ctx, user: discord.Member = None):
    """Get information about a user's verification status."""

    if user is None:
      user = ctx.author

    if not ctx.author.guild_permissions.administrator and user.id != ctx.author.id:
      await ctx.send(embed=discord.Embed(
        title="Error",
        description="You must be an administrator to view another user's verification status.",
        color=discord.Color.red()
      ))
      return

    verified = await self.config.member(user).verified()
    verified_at = await self.config.member(user).verified_at()

    if verified:
      status = "✔ Verified"
    else:
      status = "❌ Unverified"

    if verified_at is not None:
      verified_at = "%s (%s)" % (
        discord.utils.format_dt(datetime.fromtimestamp(verified_at), "F"),
        discord.utils.format_dt(datetime.fromtimestamp(verified_at), "R")
      )

    embed = discord.Embed(
      title=f"{user.display_name}'s Verification Status",
      description=f"User: {user.mention}",
      color=discord.Color.dark_green() if verified else discord.Color.dark_red(),
    )

    embed.add_field(name="Status", value=status, inline=False)

    if verified_at is not None:
      embed.add_field(name="Verified At", value=verified_at, inline=False)

    if not verified:
      verification_code = await self.config.member(user).verification_code()
      code_expires_at = await self.config.member(user).code_expires_at()

      embed.add_field(name="Verification Code",
                      value=verification_code if verification_code is not None else "N/A",
                      inline=True
                      )

      embed.add_field(name="Code Expires At",
                      value=discord.utils.format_dt(
                        datetime.fromtimestamp(code_expires_at), "F"
                      ) if code_expires_at is not None else "N/A",
                      inline=True
                      )

    embed.set_thumbnail(url=user.avatar.url)

    await ctx.send(embed=embed)

  @commands.Cog.listener(name="on_message")
  async def listen_for_verification_codes(self, message):
    if message.author.bot:
      return

    if not message.guild:
      return

    if await self.config.guild(message.guild).VERIFICATION_CHANNEL() is None:
      return

    if message.channel.id != await self.config.guild(message.guild).VERIFICATION_CHANNEL():
      return

    author = message.author
    code = await self.config.member(author).verification_code()
    code_expiry = await self.config.guild(message.guild).VERIFICATION_CODE_EXPIRY()
    expires_at = await self.config.member(author).code_expires_at()

    if code is None:
      return

    if message.content.strip() == code:
      # check if the code has expired
      if expires_at <= message.created_at.timestamp() and code_expiry != 0:
        await message.channel.send(embed=discord.Embed(
          title="Error",
          description="That verification code has expired. Please run the verification command again to generate a "
                      "new code.",
          color=discord.Color.red()
        ))
        return
      # ok, the code matches now
      else:
        # set the user as verified
        await self.config.member(author).verified.set(True)
        # set the time the user was verified
        await self.config.member(author).verified_at.set(message.created_at.timestamp())
        # add the verification role and remove the unverified role
        await author.add_roles(message.guild.get_role(await self.config.guild(message.guild).VERIFICATION_ROLE()))
        if await self.config.guild(message.guild).UNVERIFIED_ROLE() is not None:
          await author.remove_roles(message.guild.get_role(await self.config.guild(message.guild).UNVERIFIED_ROLE()))

        verified_message = await message.reply(embed=discord.Embed(
          title="Verification Success",
          description=f"You have been verified! Welcome to **{message.guild.name}**!",
          color=discord.Color.green()
        ),
          mention_author=True
        )

        # delete the verification message after a few seconds
        await verified_message.delete(delay=5.0)
        await message.delete(delay=7.5)

  @commands.Cog.listener(name="on_member_join")
  async def unverifed_role_new_members(self, member):
    """Give new members the unverified role when they join the server."""
    if await self.config.member(member).verified():
      return

    if await self.config.guild(member.guild).UNVERIFIED_ROLE() is not None:
      await member.add_roles(member.guild.get_role(await self.config.guild(member.guild).UNVERIFIED_ROLE()))
